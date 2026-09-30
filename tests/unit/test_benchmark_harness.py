import json
from datetime import UTC, datetime

import pytest

from tom.benchmarks.compaction_cliff import FullContextMemory, TruncatedFullContextMemory
from tom.benchmarks.harness import (
    BenchmarkCase,
    LoCoMoAdapter,
    LongMemEvalAdapter,
    exact_match,
    load_cases,
    run_benchmark_async,
    substring_match,
)
from tom.benchmarks.pilot import create_pilot_manifests, summarize_results
from tom.models import Event, EventType


class FakeMemory:
    async def ingest(self, session_id, events):
        self.events = events

    async def compact(self, session_id, budget):
        pass

    async def context(self, session_id, query, budget):
        return self.events[0].content


class FakeAnswerer:
    async def answer(self, question, context):
        return context


def test_longmemeval_adapter_preserves_sessions_and_evidence(tmp_path):
    path = tmp_path / "long.json"
    path.write_text(json.dumps([{
        "question_id": "q1", "question_type": "knowledge-update", "question": "Where?",
        "answer": "Paris", "haystack_session_ids": ["s1"], "haystack_dates": ["2025-01-01"],
        "haystack_sessions": [[{"role": "user", "content": "Paris"}]],
        "answer_session_ids": ["s1"],
    }]))

    case = LongMemEvalAdapter().load(path)[0]

    assert case.id == "q1"
    assert case.events[0].id == "q1:s1:0"
    assert case.events[0].type is EventType.USER
    assert case.evidence_ids == ("s1",)


def test_locomo_adapter_loads_dialogue_ids_without_using_adversarial_answer(tmp_path):
    path = tmp_path / "locomo.json"
    path.write_text(json.dumps([{
        "sample_id": "conv-1",
        "conversation": {"D1": [{"dia_id": "D1:1", "speaker": "Caroline", "text": "hello"}]},
        "qa": [{"question": "Q", "answer": "wrong", "adversarial_answer": "unknown", "evidence": [], "category": 5}],
    }]))

    case = LoCoMoAdapter().load(path)[0]

    assert case.answer == "wrong"
    assert case.metadata["adversarial_answer"] == "unknown"
    assert case.metadata["is_adversarial"] is True
    assert case.events[0].id == "D1:1"
    assert case.events[0].content == "Caroline: hello"
    assert case.events[0].metadata["speaker"] == "Caroline"
    assert case.category == "5"


def test_full_context_is_not_silently_truncated():
    event = Event(id="e1", type=EventType.USER, content="one two three", timestamp=datetime.now(UTC))
    import asyncio

    full = FullContextMemory()
    truncated = TruncatedFullContextMemory()
    asyncio.run(full.ingest("s", [event]))
    asyncio.run(truncated.ingest("s", [event]))

    assert asyncio.run(full.context("s", "", 1)) == "one two three"
    assert truncated.context_policy == "full_context_fixed_budget"


def test_exact_match_accepts_answer_alternatives_without_substrings():
    event = Event(id="e1", type=EventType.USER, content="answer", timestamp=datetime.now(UTC))
    case = BenchmarkCase("q", "Q", ["Paris", "Lutetia"], (event,), "single")

    assert exact_match(case, "Lutetia") is True
    assert exact_match(case, "Paris is the answer") is False


def test_exact_match_does_not_accept_substrings():
    event = Event(id="e1", type=EventType.USER, content="answer", timestamp=datetime.now(UTC))
    case = BenchmarkCase("q", "Q", "Paris", (event,), "single")

    assert exact_match(case, "Paris is the answer") is False
    assert substring_match(case, "Paris is the answer") is True
    assert exact_match.version == "normalized-equality-v1"


def test_cost_cap_stops_before_next_case_and_resumes_without_duplicate_rows(tmp_path):
    from tom.metrics import CostRates

    event = Event(id="e1", type=EventType.USER, content="Paris", timestamp=datetime.now(UTC))
    cases = [BenchmarkCase(f"q{i}", "Where?", "Paris", (event,), "single") for i in range(3)]

    class MeteredAnswerer(FakeAnswerer):
        async def answer(self, question, context):
            self.last_usage = {"prompt_tokens": 200_000, "completion_tokens": 0}
            return await super().answer(question, context)

    kwargs = {"output_dir": tmp_path, "budget": 4096, "dataset": "test",
              "max_cost_usd": 0.13, "answer_cost_rates": CostRates(input_per_million=0.1)}
    first = __import__("asyncio").run(run_benchmark_async(
        cases, {"fake": FakeMemory}, MeteredAnswerer(), **kwargs))
    assert len(first) == 2
    assert sum(row["billed_estimated_cost_usd"] for row in first) == 0.04
    second = __import__("asyncio").run(run_benchmark_async(
        cases, {"fake": FakeMemory}, MeteredAnswerer(), resume=True, **kwargs))
    assert len(second) == 2
    assert len((tmp_path / "raw/fake.jsonl").read_text().splitlines()) == 2


def test_full_context_over_budget_is_reported_not_scored(tmp_path):
    event = Event(id="e1", type=EventType.USER, content="one two three", timestamp=datetime.now(UTC))
    case = BenchmarkCase("q", "Where?", "Paris", (event,), "single")

    rows = __import__("asyncio").run(run_benchmark_async(
        [case], {"full": FullContextMemory}, FakeAnswerer(),
        output_dir=tmp_path / "out", budget=1, dataset="test", scorer=exact_match,
    ))

    assert rows[0]["comparison_valid"] is False
    assert rows[0]["failure"] == "context_over_budget"
    assert rows[0]["score"] is None


def test_harness_writes_one_row_per_strategy_and_case(tmp_path):
    event = Event(id="e1", type=EventType.USER, content="Paris", timestamp=datetime.now(UTC))
    case = BenchmarkCase("q", "Where?", "Paris", (event,), "single")

    rows = __import__("asyncio").run(run_benchmark_async(
        [case], {"fake": FakeMemory}, FakeAnswerer(),
        output_dir=tmp_path / "out", dataset="test", scorer=exact_match,
    ))

    assert rows[0]["score"] is True
    assert (tmp_path / "out/raw/fake.jsonl").exists()
    assert (tmp_path / "out/tables/test.csv").exists()


def test_runner_observes_shared_history_once(tmp_path):
    event = Event(id="e1", type=EventType.USER, content="Paris", timestamp=datetime.now(UTC))
    cases = [
        BenchmarkCase("q1", "Where?", "Paris", (event,), "single"),
        BenchmarkCase("q2", "Which city?", "Paris", (event,), "single"),
    ]
    created = 0

    def factory():
        nonlocal created
        created += 1
        return FakeMemory()

    rows = __import__("asyncio").run(run_benchmark_async(
        cases, {"fake": factory}, FakeAnswerer(), output_dir=tmp_path / "out",
        dataset="test", scorer=exact_match,
    ))

    assert created == 1
    assert len(rows) == 2
    assert all(row["score"] is True for row in rows)


def test_pilot_manifests_split_histories_and_are_reproducible():
    cases = [
        BenchmarkCase("a1", "Q", "A", (Event(id="a", type=EventType.USER, content="a", timestamp=datetime.now(UTC)),), "one"),
        BenchmarkCase("a2", "Q", "A", (Event(id="a", type=EventType.USER, content="a", timestamp=datetime.now(UTC)),), "two"),
        BenchmarkCase("b1", "Q", "A", (Event(id="b", type=EventType.USER, content="b", timestamp=datetime.now(UTC)),), "one"),
        BenchmarkCase("b2", "Q", "A", (Event(id="b", type=EventType.USER, content="b", timestamp=datetime.now(UTC)),), "two"),
    ]
    first = create_pilot_manifests(cases, benchmark="json", max_cases=4)
    second = create_pilot_manifests(cases, benchmark="json", max_cases=4)
    assert first == second
    assert set(first["development"]["case_ids"]).isdisjoint(first["evaluation"]["case_ids"]) 
    assert set(first["development"]["history_ids"]).isdisjoint(first["evaluation"]["history_ids"])


def test_pilot_summary_excludes_invalid_rows(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "tom.jsonl").write_text("\n".join([
        json.dumps({"strategy": "tom", "category": "one", "case_id": "a", "score": True,
                    "comparison_valid": True, "latency_ms": 10, "input_tokens": 2,
                    "output_tokens": 1, "llm_calls": 1, "evidence_count": 1}),
        json.dumps({"strategy": "tom", "category": "one", "case_id": "b", "score": False,
                    "comparison_valid": False, "latency_ms": 20, "input_tokens": 3,
                    "output_tokens": 1, "llm_calls": 1, "evidence_count": 1}),
    ]))
    summary = summarize_results(tmp_path)
    assert summary[0]["quality"] == 1.0
    assert summary[0]["failure_rate"] == 0.5


def test_load_cases_rejects_unknown_benchmark(tmp_path):
    with pytest.raises(ValueError, match="Unknown benchmark"):
        load_cases(tmp_path / "missing.json", "unknown")
