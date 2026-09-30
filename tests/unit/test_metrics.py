import json
from datetime import UTC, datetime

import pytest
from pydantic import BaseModel

from tom.metrics import CostRates, ExperimentLogger, RunMetrics, estimate_cost_usd
from tom.models import Event, EventType, Importance, KnowledgeType, MemoryItem, RetentionPolicy
from tom.observer import ObservedMemories, TypedObserver
from tom.providers import MockStructuredLLM


def test_cost_estimate_uses_per_million_rates() -> None:
    assert estimate_cost_usd(
        1_000_000, 500_000, CostRates(input_per_million=2, output_per_million=4)
    ) == 4


def test_run_metrics_has_stable_id_and_totals() -> None:
    metrics = RunMetrics(observer_input_tokens=3, scanner_input_tokens=2, observer_output_tokens=4)

    assert len(metrics.run_id) == 32
    assert metrics.total_input_tokens == 5
    assert metrics.total_output_tokens == 4


@pytest.mark.asyncio
async def test_observer_records_estimated_cost() -> None:
    event = Event(id="e1", type=EventType.USER, content="fact", timestamp=datetime.now(UTC))
    item = MemoryItem(
        id="m1", content="fact", knowledge_type=KnowledgeType.BELIEF,
        retention=RetentionPolicy.COMPRESSIBLE, importance=Importance.MEDIUM,
        confidence=1, source_ids=["e1"], created_at=datetime.now(UTC),
    )
    observer = TypedObserver(
        MockStructuredLLM(ObservedMemories(items=[item])),
        cost_rates=CostRates(input_per_million=2, output_per_million=4),
    )

    await observer.observe([event])

    assert observer.last_metrics.estimated_cost_usd > 0


def test_logger_appends_jsonl_and_snapshots_pydantic_config(tmp_path) -> None:
    class Config(BaseModel):
        budget: int

    path = tmp_path / "results" / "runs.jsonl"
    ExperimentLogger(path).log(RunMetrics(run_id="run-1"), config=Config(budget=100))
    ExperimentLogger(path).log(RunMetrics(run_id="run-2"), config={"budget": 200})

    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert [record["run_id"] for record in records] == ["run-1", "run-2"]
    assert records[0]["config"] == {"budget": 100}
