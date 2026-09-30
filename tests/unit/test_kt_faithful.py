import asyncio
from pathlib import Path

import pytest

from tom.benchmarks.knowledge_triage_repro import load_configs
from tom.benchmarks.kt_cascade import CostCapExceeded, Meter
from tom.benchmarks.kt_faithful import run_curves, run_stability, summarize

DATA = Path("data/aac/sample")


async def _verbatim(text: str, budget: int) -> tuple[str, float]:
    return text, 0.01


@pytest.mark.skipif(not DATA.exists(), reason="AAC sample not present")
def test_overshoot_is_truncated_not_invalidated_and_resume_is_free(tmp_path):
    configs = load_configs(str(DATA), n_configs=3, seed=11)
    meter = Meter(1.0)
    asyncio.run(run_curves(configs, tmp_path / "c", {"echo": _verbatim}, meter, ratios=(0.5,)))
    asyncio.run(run_stability(configs, tmp_path / "s", {"echo": _verbatim}, meter, rounds=2))
    spent = meter.spent
    asyncio.run(run_curves(configs, tmp_path / "c", {"echo": _verbatim}, meter, ratios=(0.5,)))
    assert meter.spent == spent
    summary = summarize(configs, tmp_path / "c", tmp_path / "s", ratios=(0.5,), rounds=2)
    assert summary["per_ratio"]["0.5"]["echo"]["overshoot_rate"] == 1.0
    assert summary["per_strategy"]["echo"]["round_1_c_recall"] <= 1.0
    assert summary["per_ratio"]["0.5"]["echo"]["latency_s_mean"] >= 0


def test_meter_cap_raises():
    with pytest.raises(CostCapExceeded):
        Meter(0.01).charge("gpt-6-luna", 10_000_000, 0)


@pytest.mark.skipif(not DATA.exists(), reason="AAC sample not present")
def test_structural_arms_are_free_label_blind_and_within_budget(tmp_path):
    from tom.benchmarks.kt_faithful import STRUCTURAL, structural_compactor

    config = load_configs(str(DATA), n_configs=1, seed=11)[0]
    budget = max(64, int(config.kb.total_tokens * 0.25))
    for name, select in STRUCTURAL.items():
        text, cost = asyncio.run(structural_compactor(select)(config.text, budget))
        assert cost == 0.0 and len(text) <= budget * 4 + 400, name


def test_failed_record_is_retried_on_resume(tmp_path):
    from tom.benchmarks.kt_faithful import _load, _write

    _write(tmp_path, "a", {"error": "boom"})
    assert _load(tmp_path, "a") is None
