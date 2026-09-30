import asyncio
import json
from time import perf_counter
from typing import Any

from tom.metrics import CostRates, RunMetrics, estimate_cost_usd
from tom.models import KnowledgeType, RetentionPolicy
from tom.models.event import Event
from tom.models.memory import MemoryItem
from tom.providers.base import StructuredLLM

from .jev_relabeler import JevRelabeler
from .prompts import SYSTEM_PROMPT
from .schemas import ObservedMemories
from .tokenizer import count_tokens

_VERBATIM_RETENTION = {RetentionPolicy.EXACT, RetentionPolicy.HIGH_FIDELITY}


def enforce_verbatim_content(items: list[MemoryItem], events: list[Event]) -> None:
    """For EXACT/HIGH_FIDELITY items, replace the LLM's content with the source
    event text it cites. RetentionPolicy only ever gated eviction priority at
    projection time; it never constrained what the observer LLM writes into
    ``content``, so "exact" items still went through LLM paraphrasing. The LLM
    stays responsible for classification (type/retention/importance/scope) --
    the one thing it is good at -- while the words that must survive compaction
    come straight from the source, not from a rewrite.
    """
    by_id = {event.id: event.content for event in events}
    for item in items:
        if item.retention in _VERBATIM_RETENTION:
            item.content = "\n".join(by_id[source_id] for source_id in item.source_ids)


class TypedObserver:
    def __init__(
        self, llm: StructuredLLM, *, cost_rates: CostRates | None = None,
        relabeler: JevRelabeler | None = None,
    ) -> None:
        self.llm = llm
        self.cost_rates = cost_rates
        self.relabeler = relabeler
        self._lock = asyncio.Lock()
        self.last_input_tokens = 0
        self.last_output_tokens = 0
        self.last_llm_calls = 0
        self.last_metrics = RunMetrics()

    async def observe(self, events: list[Event]) -> list[MemoryItem]:
        async with self._lock:
            return await self._observe(events)

    async def _observe(self, events: list[Event]) -> list[MemoryItem]:
        started = perf_counter()
        self._reset_metrics()
        if not events:
            self.last_metrics.latency_ms = (perf_counter() - started) * 1000
            return []

        payload = [event.model_dump(mode="json") for event in events]
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Observe these events:\n" + json.dumps(payload, ensure_ascii=False),
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
        # Relabel before restoring source text: Jev decides which items require verbatim retention.
        jev_calls = jev_tokens = jev_output_tokens = 0
        if self.relabeler is not None:
            jev = self.relabeler.jev
            before_calls, before_tokens = jev.last_calls, jev.last_input_tokens
            before_output = jev.last_output_tokens
            await self.relabeler.relabel(observed.items)
            jev_calls = jev.last_calls - before_calls
            jev_tokens = jev.last_input_tokens - before_tokens
            jev_output_tokens = jev.last_output_tokens - before_output
        enforce_verbatim_content(observed.items, events)

        self.last_input_tokens = getattr(self.llm, "last_input_tokens", 0) or sum(
            count_tokens(str(message["content"])) for message in messages
        )
        self.last_output_tokens = getattr(self.llm, "last_output_tokens", 0) or count_tokens(
            observed.model_dump_json()
        )
        self.last_llm_calls = 1
        self.last_metrics = RunMetrics(
            observer_input_tokens=self.last_input_tokens,
            observer_output_tokens=self.last_output_tokens,
            memory_items_created=len(observed.items),
            constraints_created=sum(
                item.knowledge_type == KnowledgeType.CONSTRAINT for item in observed.items
            ),
            procedures_created=sum(
                item.knowledge_type == KnowledgeType.PROCEDURE for item in observed.items
            ),
            llm_calls=1,
            jev_calls=jev_calls,
            jev_input_tokens=jev_tokens,
            jev_output_tokens=jev_output_tokens,
            estimated_cost_usd=self._cost(self.last_input_tokens, self.last_output_tokens)
            + (self.relabeler.jev.cost_rates.input_per_million * jev_tokens / 1_000_000
               if self.relabeler else 0),
            latency_ms=(perf_counter() - started) * 1000,
        )
        return observed.items

    async def observe_chunks(self, chunks: list[list[Event]]) -> list[MemoryItem]:
        async with self._lock:
            items: list[MemoryItem] = []
            input_tokens = output_tokens = llm_calls = 0
            latency_ms = 0.0
            jev_calls = jev_tokens = jev_output_tokens = 0
            estimated_cost_usd = 0.0
            for chunk in chunks:
                items.extend(await self._observe(chunk))
                input_tokens += self.last_input_tokens
                output_tokens += self.last_output_tokens
                llm_calls += self.last_llm_calls
                latency_ms += self.last_metrics.latency_ms
                jev_calls += self.last_metrics.jev_calls
                jev_tokens += self.last_metrics.jev_input_tokens
                jev_output_tokens += self.last_metrics.jev_output_tokens
                estimated_cost_usd += self.last_metrics.estimated_cost_usd

            self.last_input_tokens = input_tokens
            self.last_output_tokens = output_tokens
            self.last_llm_calls = llm_calls
            self.last_metrics = RunMetrics(
                observer_input_tokens=input_tokens,
                observer_output_tokens=output_tokens,
                memory_items_created=len(items),
                constraints_created=sum(
                    item.knowledge_type == KnowledgeType.CONSTRAINT for item in items
                ),
                procedures_created=sum(
                    item.knowledge_type == KnowledgeType.PROCEDURE for item in items
                ),
                llm_calls=llm_calls,
                jev_calls=jev_calls,
                jev_input_tokens=jev_tokens,
                jev_output_tokens=jev_output_tokens,
                estimated_cost_usd=estimated_cost_usd,
                latency_ms=latency_ms,
            )
            return items

    def _cost(self, input_tokens: int, output_tokens: int) -> float:
        if self.cost_rates is None:
            return 0.0
        return estimate_cost_usd(input_tokens, output_tokens, self.cost_rates)

    def _reset_metrics(self) -> None:
        self.last_input_tokens = 0
        self.last_output_tokens = 0
        self.last_llm_calls = 0
        self.last_metrics = RunMetrics()
