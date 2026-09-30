from datetime import UTC, datetime

from tom.benchmarks import (
    RecursiveSummaryMemory,
    StructuredSummarizer,
    TypedObservationalMemory,
    default_scenarios,
    run_behavioral_benchmark,
    run_sync,
)
from tom.models import Event, EventType, KnowledgeType


def event(number: int, kind: KnowledgeType, text: str) -> Event:
    return Event(
        id=f"e{number}", type=EventType.USER,
        content=text, timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        metadata={"knowledge_type": kind.value},
    )


def test_recursive_summary_is_a_real_llm_baseline():
    import asyncio

    from tom.benchmarks.compaction_cliff import SummaryResponse
    from tom.providers.mock import MockStructuredLLM

    llm = MockStructuredLLM(SummaryResponse(summary="preserve this fact"))
    strategy = RecursiveSummaryMemory(StructuredSummarizer(llm))
    asyncio.run(strategy.ingest("s", [event(1, KnowledgeType.BELIEF, "this fact")]))
    asyncio.run(strategy.compact("s", 100))
    assert asyncio.run(strategy.context("s", "fact", 100)) == "preserve this fact"
    assert strategy.last_metrics.llm_calls == 1


def test_typed_memory_preserves_constraints(tmp_path):
    import asyncio

    strategy = TypedObservationalMemory()
    events = [event(1, KnowledgeType.CONSTRAINT, "Never change the public API")]
    asyncio.run(strategy.ingest("s", events))
    assert "Never change the public API" in asyncio.run(strategy.context("s", "API", 100))


def test_compaction_rounds_are_chronological() -> None:
    from tom.benchmarks.compaction_cliff import _batches

    batches = _batches([event(i, KnowledgeType.BELIEF, str(i)) for i in range(5)], 2)

    assert [[item.id for item in batch] for batch in batches] == [["e0", "e1", "e2"], ["e3", "e4"]]


def test_behavioral_benchmark_checks_actions_and_writes_outputs(tmp_path):
    rows = run_behavioral_benchmark(output_dir=tmp_path)

    assert len(rows) == 5 * len(default_scenarios())
    assert all(row["behavior_correct"] for row in rows[:3])
    assert (tmp_path / "tables/behavioral_agent.csv").exists()
    assert (tmp_path / "raw/typed_observational.jsonl").exists()


def test_compaction_cliff_writes_reproducible_outputs(tmp_path):
    rows = run_sync(
        [
            event(1, KnowledgeType.CONSTRAINT, "Never change the public API"),
            event(2, KnowledgeType.PROCEDURE, "Run tests before committing"),
        ], output_dir=tmp_path, cycles=(1, 2), budget=100,
    )
    assert len(rows) == 10
    assert (tmp_path / "tables/compaction_cliff.csv").exists()
    assert (tmp_path / "figures/compaction_cliff.png").read_bytes().startswith(b"\x89PNG")
    assert {row["cycles"] for row in rows} == {1, 2}
