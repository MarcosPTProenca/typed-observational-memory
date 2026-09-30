"""Deterministic drop-in for TypedObserver: same Observer protocol, but
classification comes from the paper's own regex classifier instead of an LLM.

This isolates the hypothesis that matters for the Knowledge Triage comparison:
is TOM's remaining recall gap against TypeCompact caused by (a) LLM
classification being less reliable than the paper's regex, or (b) the
observe-then-compact/project mechanism itself? Swapping only the classifier
while keeping TypedTOMMemory's async per-chunk ingest and ContextProjector's
budgeted selection answers that directly, with zero LLM calls and full
determinism/reproducibility -- no sampling variance across runs.

Every item is stored verbatim (the classifier only labels a whole line/event;
it never rewrites text), so there is no paraphrasing to correct here, unlike
TypedObserver before ``enforce_verbatim_content``.
"""

from __future__ import annotations

from time import perf_counter

from knowledge_triage.classifier import KnowledgeType as KTType
from knowledge_triage.classifier import classify_instruction

from tom.metrics import RunMetrics
from tom.models import Importance, KnowledgeType, RetentionPolicy
from tom.models.event import Event
from tom.models.memory import MemoryItem

# type_compact pins constraints and procedures unconditionally, then allocates
# the remaining budget across belief (50%), preference (20%), episodic (30%).
# ContextProjector has no such proportional split -- it greedily fills by
# (retention, importance) rank -- so approximate the paper's priority order
# with importance: belief > preference > episodic, all COMPRESSIBLE.
_TYPE_MAP: dict[KTType, tuple[KnowledgeType, RetentionPolicy, Importance]] = {
    KTType.CONSTRAINT: (KnowledgeType.CONSTRAINT, RetentionPolicy.EXACT, Importance.CRITICAL),
    KTType.PROCEDURAL: (KnowledgeType.PROCEDURE, RetentionPolicy.HIGH_FIDELITY, Importance.HIGH),
    KTType.BELIEF: (KnowledgeType.BELIEF, RetentionPolicy.COMPRESSIBLE, Importance.MEDIUM),
    KTType.PREFERENCE: (KnowledgeType.PREFERENCE, RetentionPolicy.COMPRESSIBLE, Importance.MEDIUM),
    KTType.EPISODIC: (KnowledgeType.EPISODIC, RetentionPolicy.COMPRESSIBLE, Importance.LOW),
}


class DeterministicObserver:
    """Observer protocol implementation with the paper's regex classifier."""

    def __init__(self) -> None:
        self.last_metrics = RunMetrics()
        self._counter = 0

    async def observe(self, events: list[Event]) -> list[MemoryItem]:
        started = perf_counter()
        items = [self._classify(event) for event in events]
        self.last_metrics = RunMetrics(
            memory_items_created=len(items),
            constraints_created=sum(item.knowledge_type == KnowledgeType.CONSTRAINT for item in items),
            procedures_created=sum(item.knowledge_type == KnowledgeType.PROCEDURE for item in items),
            llm_calls=0,
            latency_ms=(perf_counter() - started) * 1000,
        )
        return items

    async def observe_chunks(self, chunks: list[list[Event]]) -> list[MemoryItem]:
        started = perf_counter()
        items = [self._classify(event) for chunk in chunks for event in chunk]
        self.last_metrics = RunMetrics(
            memory_items_created=len(items),
            constraints_created=sum(item.knowledge_type == KnowledgeType.CONSTRAINT for item in items),
            procedures_created=sum(item.knowledge_type == KnowledgeType.PROCEDURE for item in items),
            llm_calls=0,
            latency_ms=(perf_counter() - started) * 1000,
        )
        return items

    def _classify(self, event: Event) -> MemoryItem:
        knowledge_type, retention, importance = _TYPE_MAP[classify_instruction(event.content)]
        self._counter += 1
        return MemoryItem(
            id=f"det-{self._counter}",
            content=event.content,
            knowledge_type=knowledge_type,
            retention=retention,
            importance=importance,
            confidence=1.0,
            source_ids=[event.id],
            created_at=event.timestamp,
            event_time=event.timestamp,
        )
