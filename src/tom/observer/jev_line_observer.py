"""Verbatim line observer for the AAC classifier ablation (no generative extraction)."""

from time import perf_counter

from tom.metrics import RunMetrics
from tom.models import Importance, KnowledgeType, RetentionPolicy
from tom.models.event import Event
from tom.models.memory import MemoryItem
from tom.providers.jev import JevClassifier

from .jev_relabeler import JevRelabeler


class JevLineObserver:
    def __init__(self, jev: JevClassifier) -> None:
        self.jev = jev
        self.last_metrics = RunMetrics()

    async def observe(self, events: list[Event]) -> list[MemoryItem]:
        return await self.observe_chunks([events])

    async def observe_chunks(self, chunks: list[list[Event]]) -> list[MemoryItem]:
        started = perf_counter()
        events = [event for chunk in chunks for event in chunk]
        items = [MemoryItem(
            id=f"jev-line-{event.id}", content=event.content,
            knowledge_type=KnowledgeType.EPISODIC, retention=RetentionPolicy.COMPRESSIBLE,
            importance=Importance.LOW, confidence=0.0,
            source_ids=[event.id], created_at=event.timestamp, event_time=event.timestamp,
        ) for event in events]
        calls, input_tokens, output_tokens = (
            self.jev.last_calls, self.jev.last_input_tokens, self.jev.last_output_tokens
        )
        await JevRelabeler(self.jev).relabel(items)
        # Match TypeCompact's task policy: only constraints/procedures are protected.
        # Jev still supplies every label; its general-purpose retention alone can
        # pin facts/paths unrelated to this paper's constraint-preservation metric.
        for item in items:
            if item.knowledge_type == KnowledgeType.CONSTRAINT:
                item.retention = RetentionPolicy.EXACT
            elif item.knowledge_type == KnowledgeType.PROCEDURE:
                item.retention = RetentionPolicy.HIGH_FIDELITY
            else:
                item.retention = RetentionPolicy.COMPRESSIBLE
        jev_input = self.jev.last_input_tokens - input_tokens
        self.last_metrics = RunMetrics(
            memory_items_created=len(items),
            constraints_created=sum(item.knowledge_type == KnowledgeType.CONSTRAINT for item in items),
            procedures_created=sum(item.knowledge_type == KnowledgeType.PROCEDURE for item in items),
            jev_calls=self.jev.last_calls - calls, jev_input_tokens=jev_input,
            jev_output_tokens=self.jev.last_output_tokens - output_tokens,
            estimated_cost_usd=self.jev.cost_rates.input_per_million * jev_input / 1_000_000,
            latency_ms=(perf_counter() - started) * 1000,
        )
        return items
