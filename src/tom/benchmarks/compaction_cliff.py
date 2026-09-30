"""Reproducible, dependency-free compaction-cliff benchmark."""

from __future__ import annotations

import asyncio
import csv
import json
import struct
import time
import zlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol, cast

from pydantic import BaseModel

from tom.context import ContextProjector
from tom.metrics import RunMetrics
from tom.models import Event, Importance, KnowledgeType, MemoryItem, RetentionPolicy
from tom.observer.tokenizer import count_tokens

CYCLES = (1, 2, 4, 8, 16, 32)


class MemorySystem(Protocol):
    async def ingest(self, session_id: str, events: list[Event]) -> None: ...
    async def compact(self, session_id: str, budget: int) -> None: ...
    async def context(self, session_id: str, query: str, budget: int) -> str: ...


class FullContextMemory:
    """Genuine full-context control; ``budget`` is not a silent truncation knob."""

    comparison_label = "full_context"
    context_policy = "full_context"
    context_truncated = False

    def __init__(self) -> None:
        self.events: dict[str, list[Event]] = {}
        self.context_truncated = False
        self.context_over_budget = False

    async def ingest(self, session_id: str, events: list[Event]) -> None:
        self.events.setdefault(session_id, []).extend(events)

    async def compact(self, session_id: str, budget: int) -> None:
        return None

    async def context(self, session_id: str, query: str, budget: int) -> str:
        result = "\\n".join(e.content for e in self.events.get(session_id, []))
        self.context_truncated = False
        self.context_over_budget = count_tokens(result) > budget
        return result


class TruncatedFullContextMemory(FullContextMemory):
    """Explicit fixed-budget full-context control, separate from full context."""

    comparison_label = "full_context_fixed_budget"
    context_policy = "full_context_fixed_budget"

    async def context(self, session_id: str, query: str, budget: int) -> str:
        all_content = [e.content for e in self.events.get(session_id, [])]
        full = "\\n".join(all_content)
        result = _fit(all_content, budget)
        self.context_truncated = count_tokens(result) < count_tokens(full)
        self.context_over_budget = False
        return result


class SummaryResponse(BaseModel):
    summary: str


class StructuredSummarizer:
    """LLM summarizer adapter with usage exposed to the benchmark harness."""

    def __init__(self, llm: Any) -> None:
        self.llm = llm
        self.last_metrics = RunMetrics()

    async def __call__(self, previous: str, events: list[str], prompt: str, budget: int) -> str:
        started = time.perf_counter()
        source = "\n".join(filter(None, [previous, *events]))
        response = await self.llm.generate(
            messages=[{"role": "system", "content": prompt},
                      {"role": "user", "content": f"Budget: {budget} tokens\\n{source}"}],
            response_model=SummaryResponse,
        )
        input_tokens = getattr(self.llm, "last_input_tokens", 0) or count_tokens(source)
        output_tokens = getattr(self.llm, "last_output_tokens", 0) or count_tokens(response.summary)
        self.last_metrics = RunMetrics(
            observer_input_tokens=input_tokens, observer_output_tokens=output_tokens,
            llm_calls=1, latency_ms=(time.perf_counter() - started) * 1000,
        )
        return response.summary


class RecursiveSummaryMemory(FullContextMemory):
    """Recursive LLM summary baseline.

    The summarizer is injected so benchmark runs can use the same provider and
    its calls can be measured. It is intentionally not disguised as a recent-
    event selector like the deterministic smoke baselines.
    """

    def __init__(self, summarizer: Any) -> None:
        super().__init__()
        self.summarizer = summarizer
        self.summaries: dict[str, str] = {}

    comparison_label = "recursive_summary"
    context_policy = "recursive_summary"

    async def compact(self, session_id: str, budget: int) -> None:
        events = self.events.get(session_id, [])
        source = self.summaries.get(session_id, "")
        prompt = "Summarize the memory faithfully, preserving constraints, procedures, and state updates."
        result = self.summarizer(source, [event.content for event in events], prompt, budget)
        self.summaries[session_id] = await result if hasattr(result, "__await__") else str(result)
        self.events[session_id] = []
        self.last_metrics = getattr(self.summarizer, "last_metrics", RunMetrics())

    async def context(self, session_id: str, query: str, budget: int) -> str:
        result = self.summaries.get(session_id, "")
        self.context_over_budget = count_tokens(result) > budget
        self.context_truncated = False
        return result


class VanillaCompactionMemory(FullContextMemory):
    """A deterministic vanilla baseline: retain the newest content that fits."""

    async def compact(self, session_id: str, budget: int) -> None:
        events = self.events.get(session_id, [])
        self.events[session_id] = list(reversed(_fit_events(events, budget)))

    async def context(self, session_id: str, query: str, budget: int) -> str:
        return _fit((e.content for e in reversed(self.events.get(session_id, []))), budget, reverse=True)


class ObservationalMemory(FullContextMemory):
    """Smoke baseline, not the original Observational Memory implementation."""

    comparison_label = "observational_smoke"

    async def ingest(self, session_id: str, events: list[Event]) -> None:
        observations = self.events.setdefault(session_id, [])
        observations.extend(
            Event(id=e.id, type=e.type, content=f"Observation: {e.content}", timestamp=e.timestamp)
            for e in events
        )


class KnowledgeTriageMemory(FullContextMemory):
    """Smoke baseline, not a reproduction of the Knowledge Triage paper."""

    comparison_label = "knowledge_triage_smoke"

    async def ingest(self, session_id: str, events: list[Event]) -> None:
        observations = self.events.setdefault(session_id, [])
        observations.extend(events)
        observations.sort(key=lambda e: (not _is_high_signal(e), e.timestamp, e.id))


class TypedObservationalMemory(FullContextMemory):
    """Typed baseline using the project's deterministic context semantics."""

    comparison_label = "typed_observational_smoke"

    def __init__(self) -> None:
        super().__init__()
        self.memories: dict[str, list[MemoryItem]] = {}

    async def ingest(self, session_id: str, events: list[Event]) -> None:
        self.events.setdefault(session_id, []).extend(events)
        items = self.memories.setdefault(session_id, [])
        for event in events:
            kind = event.metadata.get("knowledge_type", _infer_type(event.content))
            try:
                knowledge_type = KnowledgeType(kind)
            except ValueError:
                knowledge_type = KnowledgeType.EPISODIC
            retention = _enum_metadata(
                event.metadata.get("retention"), RetentionPolicy,
                RetentionPolicy.EXACT if knowledge_type == KnowledgeType.CONSTRAINT else RetentionPolicy.COMPRESSIBLE,
            )
            importance = _enum_metadata(
                event.metadata.get("importance"), Importance,
                Importance.CRITICAL if retention == RetentionPolicy.EXACT else Importance.MEDIUM,
            )
            items.append(MemoryItem(
                id=f"memory-{event.id}", content=event.content, knowledge_type=knowledge_type,
                retention=retention, importance=importance,
                confidence=1.0, source_ids=[event.id], created_at=event.timestamp, event_time=event.timestamp,
            ))

    async def context(self, session_id: str, query: str, budget: int) -> str:
        return ContextProjector().project(self.memories.get(session_id, []), budget).text


async def run_compaction_cliff(
    events: list[Event],
    *,
    output_dir: str | Path = "results",
    strategies: dict[str, type[MemorySystem]] | None = None,
    cycles: Iterable[int] = CYCLES,
    budget: int = 512,
) -> list[dict[str, object]]:
    """Run all strategies and write raw JSONL, CSV tables, and a PNG plot.

    Events may identify gold answers through ``metadata.gold`` and are otherwise
    scored using the event text.  No provider or plotting dependency is needed.
    """
    output = Path(output_dir)
    raw_dir, table_dir, figure_dir = output / "raw", output / "tables", output / "figures"
    for directory in (raw_dir, table_dir, figure_dir):
        directory.mkdir(parents=True, exist_ok=True)
    factories = strategies or {name: cls for name, cls in (
        ("full_context", FullContextMemory), ("vanilla_compaction", VanillaCompactionMemory),
        ("observational", ObservationalMemory), ("knowledge_triage", KnowledgeTriageMemory),
        ("typed_observational", TypedObservationalMemory),
    )}
    rows: list[dict[str, object]] = []
    for name, factory in factories.items():
        strategy_rows = []
        for cycle_count in cycles:
            strategy = factory()
            started = time.perf_counter()
            for batch in _batches(events, cycle_count):
                await strategy.ingest("benchmark", batch)
                await strategy.compact("benchmark", budget)
            text = await strategy.context("benchmark", "constraints and procedures", budget)
            constraints = [e.content for e in events if e.metadata.get("knowledge_type") == KnowledgeType.CONSTRAINT]
            procedures = [e.content for e in events if e.metadata.get("knowledge_type") == KnowledgeType.PROCEDURE]
            row = {
                "strategy": name,
                "strategy_implementation": getattr(strategy, "comparison_label", name),
                "cycles": cycle_count,
                "constraint_recall": _recall(constraints, text), "procedure_recall": _recall(procedures, text),
                "memory_tokens": count_tokens(text), "total_input_tokens": sum(count_tokens(e.content) for e in events),
                "total_output_tokens": 0, "llm_calls": 0, "estimated_cost_usd": 0.0,
                "latency_ms": (time.perf_counter() - started) * 1000,
            }
            rows.append(row)
            strategy_rows.append(row)
        with (raw_dir / f"{name}.jsonl").open("w", encoding="utf-8") as handle:
            for row in strategy_rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    fields = list(rows[0]) if rows else []
    with (table_dir / "compaction_cliff.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    _plot(rows, figure_dir / "compaction_cliff.png")
    return rows


def _batches(events: list[Event], count: int) -> list[list[Event]]:
    count = max(1, count)
    width = max(1, (len(events) + count - 1) // count)
    return [events[start:start + width] for start in range(0, len(events), width)]


def _fit_events(events: list[Event], budget: int) -> list[Event]:
    selected: list[Event] = []
    for event in reversed(events):
        candidate = [event, *selected]
        if count_tokens("\n".join(item.content for item in candidate)) <= budget:
            selected = candidate
    return selected


def _fit(contents: Iterable[str], budget: int, *, reverse: bool = False) -> str:
    selected: list[str] = []
    for content in contents:
        candidate = selected + [content]
        if count_tokens("\n".join(candidate)) <= budget:
            selected = candidate
    if reverse:
        selected.reverse()
    return "\n".join(selected)


def _recall(gold: list[str], text: str) -> float:
    return sum(item in text for item in gold) / len(gold) if gold else 1.0


def _is_high_signal(event: Event) -> bool:
    return event.metadata.get("knowledge_type") in {KnowledgeType.CONSTRAINT, KnowledgeType.PROCEDURE, "constraint", "procedure"}


def _infer_type(content: str) -> KnowledgeType:
    return KnowledgeType.CONSTRAINT if any(word in content.lower() for word in ("never", "must", "do not")) else KnowledgeType.EPISODIC


def _enum_metadata[EnumT](value: object, enum_type: Any, default: EnumT) -> EnumT:
    try:
        return cast(EnumT, enum_type(value)) if value is not None else default
    except (TypeError, ValueError):
        return default


def _plot(rows: list[dict[str, object]], path: Path) -> None:
    width, height = 800, 450
    colors = [b"\x00\x00\x7f\xff", b"\xff\x00\x00\xff", b"\x00\x80\x00\xff", b"\xff\x80\x00\xff", b"\x80\x00\x80\xff"]
    pixels = bytearray(b"\xff\xff\xff\xff" * width * height)
    names = list(dict.fromkeys(str(row["strategy"]) for row in rows))
    for index, name in enumerate(names):
        points = [r for r in rows if r["strategy"] == name]
        for point_index, point in enumerate(points):
            x = 40 + int(point_index / max(1, len(points) - 1) * (width - 60))
            y = height - 30 - int(float(cast(float, point["constraint_recall"])) * (height - 50))
            color = colors[index % len(colors)]
            for yy in range(max(0, y - 3), min(height, y + 4)):
                for xx in range(max(0, x - 3), min(width, x + 4)):
                    pixels[(yy * width + xx) * 4:(yy * width + xx + 1) * 4] = color
    raw = b"".join(b"\x00" + pixels[y * width * 4:(y + 1) * width * 4] for y in range(height))
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def run_sync(*args: Any, **kwargs: Any) -> list[dict[str, object]]:
    return asyncio.run(run_compaction_cliff(*args, **kwargs))
