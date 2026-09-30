"""Common, reproducible runner for public memory benchmarks."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import re
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

from tom.metrics import CostRates, estimate_cost_usd
from tom.models import Event, EventType
from tom.observer.tokenizer import count_tokens
from tom.providers import CodexBridge
from tom.providers.openrouter import OpenRouterClient


@dataclass(frozen=True)
class BenchmarkCase:
    """One public-benchmark question and the history available to memory."""

    id: str
    question: str
    answer: Any
    events: tuple[Event, ...]
    category: str
    evidence_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class MemorySystem(Protocol):
    async def ingest(self, session_id: str, events: list[Event]) -> None: ...
    async def compact(self, session_id: str, budget: int) -> None: ...
    async def context(self, session_id: str, query: str, budget: int) -> str: ...


class Answerer(Protocol):
    async def answer(self, question: str, context: str) -> str: ...


class PiAnswerer:
    """Answer through pi-ai's authenticated Codex provider, without running pi."""

    def __init__(self, *, model: str | None = None, bridge: CodexBridge | None = None) -> None:
        self.bridge = bridge or CodexBridge(model=model)

    async def answer(self, question: str, context: str) -> str:
        answer = await self.bridge.prompt(
            f"Answer only from this memory. Be concise.\nMemory:\n{context}\n\nQuestion: {question}"
        )
        self.last_usage = self.bridge.last_usage
        self.model = self.bridge.model
        return answer


class OpenAIAnswerer:
    """Shared answerer for fair strategy comparisons; requires the optional openai package."""

    def __init__(self, client: Any | None = None, *, model: str = "gpt-5-mini") -> None:
        if client is None:
            try:
                module = __import__("openai", fromlist=["AsyncOpenAI"])
                client = module.AsyncOpenAI()
            except ImportError as exc:
                raise ImportError("Install the optional 'openai' package to run public benchmarks") from exc
        self.client: Any = client
        self.model = model
        self.last_usage: dict[str, Any] | None = None

    async def answer(self, question: str, context: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Answer only from the provided memory. Be concise."},
                {"role": "user", "content": f"Memory:\n{context}\n\nQuestion: {question}"},
            ],
        )
        self.last_usage = getattr(response, "usage", None)
        return response.choices[0].message.content or ""


class OpenRouterAnswerer:
    """Answer through OpenRouter; usage comes straight from the API response."""

    def __init__(self, client: OpenRouterClient | None = None, *, model: str = OpenRouterClient.DEFAULT_MODEL) -> None:
        self.client = client or OpenRouterClient(model=model)
        self.model = self.client.model
        self.last_usage: dict[str, Any] | None = None

    async def answer(self, question: str, context: str) -> str:
        response = await self.client.complete(messages=[
            {"role": "system", "content": "Answer only from the provided memory. Be concise."},
            {"role": "user", "content": f"Memory:\n{context}\n\nQuestion: {question}"},
        ])
        self.last_usage = self.client.last_usage
        self.model = self.client.last_model or self.model
        choices = response.get("choices") or []
        return (choices[0].get("message", {}).get("content") or "") if choices else ""


Strategy = Callable[[], MemorySystem]
Scorer = Callable[[BenchmarkCase, str], bool | float]


class LongMemEvalAdapter:
    """Load the official LongMemEval JSON/JSONL format."""

    def load(self, path: str | Path) -> list[BenchmarkCase]:
        records = _read_records(path)
        cases: list[BenchmarkCase] = []
        for record in records:
            question_id = str(record["question_id"])
            events: list[Event] = []
            session_ids = record.get("haystack_session_ids", [])
            dates = record.get("haystack_dates", [])
            for session_index, session in enumerate(record.get("haystack_sessions", [])):
                session_id = str(session_ids[session_index]) if session_index < len(session_ids) else str(session_index)
                timestamp = _timestamp(dates[session_index] if session_index < len(dates) else None)
                for turn_index, turn in enumerate(session):
                    events.append(Event(
                        id=f"{question_id}:{session_id}:{turn_index}",
                        type=_event_type(turn.get("role")),
                        content=str(turn.get("content", "")),
                        timestamp=timestamp,
                        metadata={"benchmark": "longmemeval", "session_id": session_id},
                    ))
            cases.append(BenchmarkCase(
                id=question_id,
                question=str(record["question"]),
                answer=record.get("answer"),
                events=tuple(events),
                category=str(record.get("question_type", "unknown")),
                evidence_ids=tuple(str(item) for item in record.get("answer_session_ids", [])),
                metadata={"question_date": record.get("question_date")},
            ))
        return cases


class LoCoMoAdapter:
    """Load the public ``locomo10.json`` conversation and QA format."""

    def load(self, path: str | Path) -> list[BenchmarkCase]:
        samples = _read_records(path)
        cases: list[BenchmarkCase] = []
        for sample in samples:
            sample_id = str(sample.get("sample_id", sample.get("conversation_id", "conversation")))
            events = tuple(_locomo_events(sample.get("conversation", {}), sample_id))
            for index, qa in enumerate(sample.get("qa", [])):
                answer = qa.get("answer")
                metadata = {
                    "sample_id": sample_id,
                    "adversarial_answer": qa.get("adversarial_answer"),
                    "is_adversarial": "adversarial_answer" in qa,
                }
                cases.append(BenchmarkCase(
                    id=f"{sample_id}:{index}",
                    question=str(qa["question"]),
                    answer=answer,
                    events=events,
                    category=str(qa.get("category", "unknown")),
                    evidence_ids=tuple(str(item) for item in qa.get("evidence", [])),
                    metadata=metadata,
                ))
        return cases


class JsonBenchmarkAdapter:
    """Load already-normalized cases for local experiments and adapter tests."""

    def load(self, path: str | Path) -> list[BenchmarkCase]:
        records = _read_records(path)
        return [BenchmarkCase(
            id=str(record["id"]), question=str(record["question"]), answer=record.get("answer"),
            events=tuple(Event.model_validate(event) for event in record.get("events", [])),
            category=str(record.get("category", "unknown")),
            evidence_ids=tuple(str(item) for item in record.get("evidence_ids", [])),
            metadata=dict(record.get("metadata", {})),
        ) for record in records]


def load_cases(path: str | Path, benchmark: str) -> list[BenchmarkCase]:
    adapters = {
        "longmemeval": LongMemEvalAdapter(),
        "locomo": LoCoMoAdapter(),
        "json": JsonBenchmarkAdapter(),
    }
    try:
        return adapters[benchmark.lower()].load(path)
    except KeyError as exc:
        raise ValueError(f"Unknown benchmark {benchmark!r}; use longmemeval, locomo, or json") from exc


async def run_benchmark_async(
    cases: Sequence[BenchmarkCase],
    strategies: dict[str, Strategy],
    answerer: Answerer,
    *,
    output_dir: str | Path = "results",
    budget: int = 16_000,
    dataset: str = "custom",
    scorer: Scorer | None = None,
    run_config: dict[str, Any] | None = None,
    dataset_hash: str | None = None,
    resume: bool = False,
    max_calls: int | None = None,
    max_cost_usd: float | None = None,
    answer_cost_rates: CostRates | None = None,
) -> list[dict[str, Any]]:
    """Run every case independently and write raw rows plus an aggregate CSV.

    The answerer is deliberately injected: public benchmark judge models and costs
    must be identical across TOM, OM, and Knowledge Triage comparisons.
    """
    if budget <= 0:
        raise ValueError("budget must be positive")
    output = Path(output_dir)
    (output / "raw").mkdir(parents=True, exist_ok=True)
    (output / "tables").mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    calls = 0
    spent = 0.0
    for strategy_name, factory in strategies.items():
        strategy_rows = _read_jsonl(output / "raw" / f"{strategy_name}.jsonl") if resume else []
        if not resume:
            _write_jsonl(output / "raw" / f"{strategy_name}.jsonl", [])
            _write_jsonl(output / "raw" / f"{strategy_name}.diagnostics.jsonl", [])
        completed = {str(row.get("case_id")) for row in strategy_rows}
        rows.extend(strategy_rows)
        if max_cost_usd is not None and resume and any(
            "billed_estimated_cost_usd" not in row for row in strategy_rows
        ):
            raise ValueError("Cannot enforce a cost cap when resuming unmetered rows")
        spent += sum(row.get("billed_estimated_cost_usd", 0.0) for row in strategy_rows)
        sessions: dict[str, tuple[MemorySystem, str]] = {}
        for case in cases:
            if case.id in completed:
                continue
            if (max_calls is not None and calls >= max_calls) or (
                max_cost_usd is not None and spent >= max_cost_usd - 0.10
            ):
                break
            started = time.perf_counter()
            history_key = _history_key(case.events)
            if history_key not in sessions:
                strategy = factory()
                session_id = f"history:{history_key}"
                phase = time.perf_counter()
                await strategy.ingest(session_id, list(case.events))
                ingestion_ms = (time.perf_counter() - phase) * 1000
                phase = time.perf_counter()
                await strategy.compact(session_id, budget)
                compaction_ms = (time.perf_counter() - phase) * 1000
                sessions[history_key] = (strategy, session_id)
            else:
                strategy, session_id = sessions[history_key]
                ingestion_ms = 0.0
                compaction_ms = 0.0
            phase = time.perf_counter()
            context = await strategy.context(session_id, case.question, budget)
            projection_ms = (time.perf_counter() - phase) * 1000
            context_over_budget = bool(getattr(strategy, "context_over_budget", False))
            phase = time.perf_counter()
            if hasattr(answerer, "last_usage"):
                cast(Any, answerer).last_usage = None
            if context_over_budget:
                # A genuine full-context control is valid only when it fits the
                # declared answer budget. Keep the failure visible instead of
                # silently turning it into a different truncated baseline.
                hypothesis = ""
                answer_ms = 0.0
                score = None
                failure = "context_over_budget"
            else:
                hypothesis = await answerer.answer(_question_for_answerer(case), context)
                calls += 1
                answer_ms = (time.perf_counter() - phase) * 1000
                score = scorer(case, hypothesis) if scorer else None
                failure = None
            metrics = _system_metrics(strategy)
            answer_usage = getattr(answerer, "last_usage", None)
            answer_model = getattr(answerer, "model", None)
            usage = _json_value(answer_usage)
            answer_cost = (
                estimate_cost_usd(usage.get("prompt_tokens", 0),
                                  usage.get("completion_tokens", 0), answer_cost_rates)
                if answer_cost_rates and isinstance(usage, dict) else 0.0
            )
            billed = answer_cost + (metrics["estimated_cost_usd"] if compaction_ms else 0.0)
            spent += billed
            relabeler = getattr(getattr(strategy, "observer", None), "relabeler", None)
            row = {
                "dataset": dataset, "strategy": strategy_name,
                "strategy_implementation": getattr(strategy, "comparison_label", strategy_name),
                "case_id": case.id,
                "category": case.category, "answer": case.answer, "hypothesis": hypothesis,
                "score": score, "substring_match": substring_match(case, hypothesis),
                "evaluator_version": getattr(scorer, "version", None) if scorer else None,
                "comparison_valid": failure is None,
                "failure": failure,
                "event_count": len(case.events),
                "evidence_count": len(case.evidence_ids),
                "evidence_preserved": _evidence_preserved(case, strategy),
                "context_tokens": count_tokens(context),
                "latency_ms": (time.perf_counter() - started) * 1000,
                "ingestion_ms": ingestion_ms, "compaction_ms": compaction_ms,
                "projection_ms": projection_ms, "answer_ms": answer_ms,
                "config": run_config or {}, "dataset_hash": dataset_hash,
                "model": answer_model, "answer_usage": usage,
                "jev_model": relabeler.jev.model if relabeler else None,
                "billed_estimated_cost_usd": billed,
                "context_policy": getattr(strategy, "context_policy", "fixed_budget"),
                "context_truncated": getattr(strategy, "context_truncated", None),
                "context_over_budget": context_over_budget,
                **metrics,
            }
            rows.append(row)
            strategy_rows.append(row)
            diagnostic_row = {
                "case_id": case.id,
                "evidence_ids": case.evidence_ids,
                "events": [event.model_dump(mode="json") for event in case.events],
                "memory_items": _memory_items(strategy),
                "context": context,
                "hypothesis": hypothesis,
                "evaluation": {
                    "score": score,
                    "substring_match": substring_match(case, hypothesis),
                    "comparison_valid": failure is None,
                    "failure": failure,
                    "scorer": getattr(scorer, "__name__", None),
                    "version": getattr(scorer, "version", None) if scorer else None,
                },
                "config": run_config or {}, "dataset_hash": dataset_hash,
            }
            _append_jsonl(output / "raw" / f"{strategy_name}.jsonl", row)
            _append_jsonl(output / "raw" / f"{strategy_name}.diagnostics.jsonl", diagnostic_row)
    _write_csv(output / "tables" / f"{dataset}.csv", rows)
    return rows


def run_benchmark(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    """Synchronous entry point for CLI/scripts."""
    if _running_loop():
        raise RuntimeError("run_benchmark() cannot run inside an event loop; use run_benchmark_async()")
    return asyncio.run(run_benchmark_async(*args, **kwargs))


def exact_match(case: BenchmarkCase, hypothesis: str) -> bool:
    """Strict normalized equality, accepting datasets with answer alternatives."""
    if case.answer is None:
        return False
    answers = case.answer if isinstance(case.answer, (list, tuple, set)) else (case.answer,)
    return any(_normalize(str(answer)) == _normalize(hypothesis) for answer in answers)


exact_match.version = "normalized-equality-v1"


def substring_match(case: BenchmarkCase, hypothesis: str) -> bool:
    """Diagnostic only; never use this as benchmark accuracy."""
    if case.answer is None:
        return False
    answers = case.answer if isinstance(case.answer, (list, tuple, set)) else (case.answer,)
    normalized = _normalize(hypothesis)
    return any((answer := _normalize(str(value))) and answer in normalized for value in answers)


substring_match.version = "substring-diagnostic-v1"


def file_sha256(path: str | Path) -> str:
    """Return a stable dataset identity without storing its contents in results."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_records(path: str | Path) -> list[dict[str, Any]]:
    raw = Path(path).read_text(encoding="utf-8")
    if Path(path).suffix == ".jsonl":
        return [json.loads(line) for line in raw.splitlines() if line.strip()]
    value = json.loads(raw)
    return value if isinstance(value, list) else [value]


def _timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if value:
        try:
            parsed = datetime.fromisoformat(str(value))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except (TypeError, ValueError):
            pass
    # Event currently requires a datetime. Keep invalid/missing values out of the
    # Unix epoch and preserve the original value in the event metadata.
    return datetime.min.replace(tzinfo=UTC)


def _event_type(role: Any) -> EventType:
    return {"user": EventType.USER, "assistant": EventType.ASSISTANT}.get(role, EventType.USER)


def _locomo_events(conversation: dict[str, Any], sample_id: str) -> Iterable[Event]:
    for session_id, turns in conversation.items():
        if not (re.fullmatch(r"D\d+", str(session_id)) or re.fullmatch(r"session_\d+", str(session_id))):
            continue
        if not isinstance(turns, list):
            continue
        date = conversation.get(f"{session_id}_date_time")
        for index, turn in enumerate(turns):
            if not isinstance(turn, dict):
                continue
            yield Event(
                id=str(turn.get("dia_id", f"{sample_id}:{session_id}:{index}")),
                type=_event_type(turn.get("speaker", "user").lower()),
                content=f"{turn.get('speaker', 'unknown')}: {turn.get('text', turn.get('content', ''))}",
                timestamp=_timestamp(turn.get("timestamp", turn.get("date", date))),
                metadata={
                    "benchmark": "locomo", "session_id": str(session_id),
                    "speaker": str(turn.get("speaker", "unknown")),
                },
            )


def _question_for_answerer(case: BenchmarkCase) -> str:
    question_date = case.metadata.get("question_date")
    if question_date:
        return f"Reference date: {question_date}\nQuestion: {case.question}"
    return case.question


def _evidence_preserved(case: BenchmarkCase, strategy: MemorySystem) -> bool | None:
    """Post-hoc retention diagnostic; never influences context selection."""
    if not case.evidence_ids:
        return None
    evidence_events = {
        event.id for event in case.events
        if event.id in case.evidence_ids or event.metadata.get("session_id") in case.evidence_ids
    }
    selected = set(getattr(strategy, "selected_memory_source_ids", ()))
    return bool(evidence_events & selected)


def _memory_items(strategy: MemorySystem) -> list[dict[str, Any]]:
    memories = getattr(strategy, "memories", {})
    if isinstance(memories, dict):
        items = [item for values in memories.values() for item in values]
    else:
        items = []
    return [item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item) for item in items]


def _system_metrics(strategy: MemorySystem) -> dict[str, Any]:
    metrics = getattr(strategy, "last_metrics", None)
    if metrics is None:
        return {
            "input_tokens": 0, "output_tokens": 0, "llm_calls": 0,
            "jev_calls": 0, "jev_input_tokens": 0, "jev_output_tokens": 0,
            "estimated_cost_usd": 0.0,
        }
    return {
        "input_tokens": metrics.total_input_tokens,
        "output_tokens": metrics.total_output_tokens,
        "llm_calls": metrics.llm_calls,
        "jev_calls": metrics.jev_calls,
        "jev_input_tokens": metrics.jev_input_tokens,
        "jev_output_tokens": metrics.jev_output_tokens,
        "estimated_cost_usd": metrics.estimated_cost_usd,
    }


def _history_key(events: Sequence[Event]) -> str:
    """Identify an immutable history without including the question or answer."""
    payload = "\n".join(
        f"{event.id}\0{event.type.value}\0{event.timestamp.isoformat()}\0{event.content}"
        for event in events
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool, dict, list)):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "__dict__"):
        return vars(value)
    return str(value)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else ["dataset", "strategy", "case_id", "score"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _running_loop() -> bool:
    try:
        return asyncio.get_running_loop().is_running()
    except RuntimeError:
        return False
