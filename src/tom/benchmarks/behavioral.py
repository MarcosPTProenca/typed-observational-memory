"""Deterministic long-horizon behavioral-memory benchmark."""

from __future__ import annotations

import asyncio
import csv
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tom.models import Event, EventType, Importance, KnowledgeType, RetentionPolicy

from .compaction_cliff import (
    FullContextMemory,
    KnowledgeTriageMemory,
    MemorySystem,
    ObservationalMemory,
    TypedObservationalMemory,
    VanillaCompactionMemory,
)


@dataclass(frozen=True)
class BehavioralScenario:
    """A behavior test: memory must enable the right action, not just a recall answer."""

    id: str
    category: str
    events: tuple[Event, ...]
    action: str
    required: tuple[str, ...]
    forbidden: tuple[str, ...] = ()

    def evaluate(self, context: str) -> bool:
        return all(term in context for term in self.required) and not any(
            term in context for term in self.forbidden
        )


def default_scenarios() -> tuple[BehavioralScenario, ...]:
    """Small synthetic suite covering the five PR-11 behavior categories."""
    return (
        _scenario(
            "public-api", "constraint_retention", "Never change the public API", "preserve API",
            "Never change the public API",
        ),
        _scenario(
            "tests-first", "procedure_compliance", "Run integration tests before merging", "run tests",
            "Run integration tests before merging",
        ),
        _scenario(
            "generated-file", "implicit_constraint", "Generated files are overwritten by CI", "edit source",
            "Generated files are overwritten by CI",
        ),
        _scenario(
            "backend-migration", "state_update", ("Backend uses MySQL", "Backend uses PostgreSQL"), "migrate", "migrate",
            required=("Backend uses PostgreSQL",), forbidden=("Backend uses MySQL",),
        ),
        _scenario(
            "production-migration", "temporal_fact", "Migration 184 already ran in production", "do not rerun",
            "Migration 184 already ran in production",
        ),
    )


def run_behavioral_benchmark(
    scenarios: tuple[BehavioralScenario, ...] | list[BehavioralScenario] | None = None,
    *,
    output_dir: str | Path = "results",
    strategies: dict[str, type[MemorySystem]] | None = None,
    budget: int = 64,
) -> list[dict[str, object]]:
    """Run scenarios through memory systems and write raw JSONL plus a CSV table."""
    cases = tuple(scenarios or default_scenarios())
    factories = strategies or {
        "full_context": FullContextMemory,
        "vanilla_compaction": VanillaCompactionMemory,
        "observational": ObservationalMemory,
        "knowledge_triage": KnowledgeTriageMemory,
        "typed_observational": TypedObservationalMemory,
    }
    output = Path(output_dir)
    (output / "raw").mkdir(parents=True, exist_ok=True)
    (output / "tables").mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []

    for name, factory in factories.items():
        strategy_rows: list[dict[str, object]] = []
        for scenario in cases:
            started = time.perf_counter()
            strategy = factory()
            for event in scenario.events:
                awaitable = strategy.ingest("benchmark", [event])
                asyncio.run(awaitable)
                asyncio.run(strategy.compact("benchmark", budget))
            context = asyncio.run(strategy.context("benchmark", scenario.action, budget))
            row = {
                "strategy": name,
                "scenario": scenario.id,
                "category": scenario.category,
                "action": scenario.action,
                "behavior_correct": scenario.evaluate(context),
                "constraint_violation": scenario.category in {"constraint_retention", "implicit_constraint"}
                and not scenario.evaluate(context),
                "procedure_compliant": scenario.category == "procedure_compliance"
                and scenario.evaluate(context),
                "state_update_correct": scenario.category == "state_update" and scenario.evaluate(context),
                "temporal_fact_correct": scenario.category == "temporal_fact" and scenario.evaluate(context),
                "context_tokens": _token_count(context),
                "latency_ms": (time.perf_counter() - started) * 1000,
            }
            rows.append(row)
            strategy_rows.append(row)
        _write_jsonl(output / "raw" / f"{name}.jsonl", strategy_rows)

    fields = list(rows[0]) if rows else []
    with (output / "tables" / "behavioral_agent.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def run_sync(*args: Any, **kwargs: Any) -> list[dict[str, object]]:
    """Synchronous entry point for scripts and tests."""
    return run_behavioral_benchmark(*args, **kwargs)


def _scenario(
    ident: str,
    category: str,
    content: str | tuple[str, ...],
    action: str,
    kind_or_required: str | tuple[str, ...],
    *,
    required: tuple[str, ...] | None = None,
    forbidden: tuple[str, ...] = (),
) -> BehavioralScenario:
    if required is None:
        required = (kind_or_required,) if isinstance(kind_or_required, str) else kind_or_required
    kind = KnowledgeType.CONSTRAINT if category in {"constraint_retention", "implicit_constraint"} else KnowledgeType.EPISODIC
    if category == "procedure_compliance":
        kind = KnowledgeType.PROCEDURE
    values = (content,) if isinstance(content, str) else content
    values = (*values, *(f"Unrelated event {index} for {ident}" for index in range(24)))
    protected = category in {"constraint_retention", "implicit_constraint"}
    high_fidelity = category in {"procedure_compliance", "temporal_fact"}
    events = [
        Event(
            id=f"{ident}-{index}", type=EventType.USER, content=value,
            timestamp=datetime(2025, 1, index + 1, tzinfo=UTC),
            metadata={
                "knowledge_type": (kind if index < len(values) - 24 else KnowledgeType.EPISODIC).value,
                "retention": (RetentionPolicy.EXACT if protected and index < len(values) - 24
                              else RetentionPolicy.HIGH_FIDELITY if high_fidelity and index < len(values) - 24
                              else RetentionPolicy.COMPRESSIBLE).value,
                "importance": (Importance.CRITICAL.value
                               if (protected or high_fidelity) and index < len(values) - 24
                               else Importance.MEDIUM.value),
            },
        )
        for index, value in enumerate(values)
    ]
    return BehavioralScenario(ident, category, tuple(events), action, required, forbidden)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _token_count(text: str) -> int:
    from tom.observer.tokenizer import count_tokens

    return count_tokens(text)
