import asyncio
import json
from time import perf_counter
from typing import TYPE_CHECKING, Any

from tom.metrics import CostRates, RunMetrics, estimate_cost_usd
from tom.models import Importance, KnowledgeType, RetentionPolicy
from tom.models.event import Event
from tom.models.memory import MemoryItem
from tom.providers.base import StructuredLLM

from .prompts import SAFETY_SCANNER_PROMPT
from .schemas import ObservedMemories
from .tokenizer import count_tokens
from .typed_observer import enforce_verbatim_content

if TYPE_CHECKING:
    from tom.providers.jev import JevClassifier


class SafetyScanner:
    """High-recall second pass for information whose loss could change behavior."""

    def __init__(
        self,
        llm: StructuredLLM,
        *,
        cost_rates: CostRates | None = None,
        gate: "JevClassifier | None" = None,
        gate_threshold: float = 0.5,
    ) -> None:
        self.llm = llm
        self.cost_rates = cost_rates
        self.gate = gate
        self.gate_threshold = gate_threshold
        self._lock = asyncio.Lock()
        self.last_input_tokens = 0
        self.last_output_tokens = 0
        self.last_llm_calls = 0
        self.last_metrics = RunMetrics()

    async def scan(self, events: list[Event]) -> list[MemoryItem]:
        async with self._lock:
            return await self._scan(events)

    async def _scan(self, events: list[Event]) -> list[MemoryItem]:
        started = perf_counter()
        self._reset_metrics()
        if not events:
            self.last_metrics.latency_ms = (perf_counter() - started) * 1000
            return []

        payload = [event.model_dump(mode="json") for event in events]
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SAFETY_SCANNER_PROMPT},
            {
                "role": "user",
                "content": "Scan these events:\n" + json.dumps(payload, ensure_ascii=False),
            },
        ]
        response = await self.llm.generate(messages=messages, response_model=ObservedMemories)
        observed = ObservedMemories.model_validate(response)
        event_ids = {event.id for event in events}
        for item in observed.items:
            unknown = set(item.source_ids) - event_ids
            if unknown:
                raise ValueError(
                    f"Memory {item.id} references unknown event IDs: {sorted(unknown)}"
                )
        enforce_verbatim_content(observed.items, events)
        if self.gate is not None:
            await self._apply_gate(observed.items)

        self.last_input_tokens = getattr(self.llm, "last_input_tokens", 0) or sum(
            count_tokens(str(message["content"])) for message in messages
        )
        self.last_output_tokens = getattr(self.llm, "last_output_tokens", 0) or count_tokens(
            observed.model_dump_json()
        )
        self.last_llm_calls = 1
        self.last_metrics = self._metrics(
            observed.items,
            (perf_counter() - started) * 1000,
        )
        return observed.items

    async def observe(self, events: list[Event]) -> list[MemoryItem]:
        """Observer-compatible alias."""
        return await self.scan(events)

    async def _apply_gate(self, items: list[MemoryItem]) -> None:
        """Confirm behavior-altering items via a Jev Noul and pin them to EXACT retention."""
        gate = self.gate
        assert gate is not None
        probs = await asyncio.gather(*(gate.confirm_critical(item.content) for item in items))
        for item, prob in zip(items, probs, strict=True):
            if prob >= self.gate_threshold:
                item.retention = RetentionPolicy.EXACT
                item.confidence = max(item.confidence, prob)

    def _metrics(self, items: list[MemoryItem], latency_ms: float) -> RunMetrics:
        return RunMetrics(
            scanner_input_tokens=self.last_input_tokens,
            scanner_output_tokens=self.last_output_tokens,
            memory_items_created=len(items),
            constraints_created=sum(
                item.knowledge_type == KnowledgeType.CONSTRAINT for item in items
            ),
            procedures_created=sum(
                item.knowledge_type == KnowledgeType.PROCEDURE for item in items
            ),
            llm_calls=self.last_llm_calls,
            estimated_cost_usd=self._cost(),
            latency_ms=latency_ms,
        )

    def _cost(self) -> float:
        if self.cost_rates is None:
            return 0.0
        return estimate_cost_usd(self.last_input_tokens, self.last_output_tokens, self.cost_rates)

    def _reset_metrics(self) -> None:
        self.last_input_tokens = 0
        self.last_output_tokens = 0
        self.last_llm_calls = 0
        self.last_metrics = RunMetrics()


def merge_observations(
    observer_items: list[MemoryItem], scanner_items: list[MemoryItem]
) -> list[MemoryItem]:
    """Merge scanner output, keeping one item per equivalent fact and all evidence."""
    merged: list[MemoryItem] = []
    by_key: dict[tuple[str, KnowledgeType], MemoryItem] = {}
    for item in [*observer_items, *scanner_items]:
        key = (" ".join(item.content.split()).casefold(), item.knowledge_type)
        current = by_key.get(key)
        if current is None:
            current = item.model_copy(deep=True)
            by_key[key] = current
            merged.append(current)
            continue
        current.source_ids = list(dict.fromkeys([*current.source_ids, *item.source_ids]))
        current.scope = list(dict.fromkeys([*current.scope, *item.scope]))
        current.supersedes = list(dict.fromkeys([*current.supersedes, *item.supersedes]))
        if current.topic is None:
            current.topic = item.topic
        current.confidence = max(current.confidence, item.confidence)
        if _rank(item.importance, Importance) > _rank(current.importance, Importance):
            current.importance = item.importance
        if _rank(item.retention, RetentionPolicy) > _rank(current.retention, RetentionPolicy):
            current.retention = item.retention
    return merged


def _rank(value: Any, enum_type: type[Any]) -> int:
    order = {
        Importance: [Importance.LOW, Importance.MEDIUM, Importance.HIGH, Importance.CRITICAL],
        RetentionPolicy: [
            RetentionPolicy.DISCARDABLE,
            RetentionPolicy.COMPRESSIBLE,
            RetentionPolicy.HIGH_FIDELITY,
            RetentionPolicy.EXACT,
        ],
    }
    return order[enum_type].index(value)
