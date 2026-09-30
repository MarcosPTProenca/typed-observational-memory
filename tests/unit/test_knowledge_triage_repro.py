"""Deterministic coverage for the Knowledge Triage reproduction module.

LLM-backed paths (vanilla_llm_compact, tom_compact) are exercised elsewhere
via a live run (see docs/benchmark-next-steps.md); this suite only covers
the deterministic parts: config loading, TypeCompact scoring parity with the
upstream reference, and the unsafe-budget fallback for TOM.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from knowledge_triage.classifier import KnowledgeType as KTType
from knowledge_triage.kb import Item as KTItem
from knowledge_triage.kb import KnowledgeBase as KTKnowledgeBase
from knowledge_triage.operators import type_compact

from tom.benchmarks.aac_report import report
from tom.benchmarks.knowledge_triage_repro import (
    AACConfig,
    BudgetSchedule,
    ControlledScenario,
    OpenAIBenchmarkBridge,
    ResumeManifestMismatch,
    TypedTOMCompactor,
    _c_recall,
    _clean_line,
    controlled_budgets,
    load_configs,
    make_controlled_manifest,
    per_type_preservation,
    run_controlled_deterministic,
    run_controlled_llm,
    split_configs,
    truncate_to_tokens,
    type_compact_token_aligned,
    write_or_validate_manifest,
)
from tom.context import ContextProjector, SelectionPolicy
from tom.models import Event, EventType, Importance, KnowledgeType, MemoryItem, RetentionPolicy
from tom.observer import DeterministicObserver, ObservedMemories, TypedObserver
from tom.observer.tokenizer import count_tokens
from tom.providers.jev import JevClassifier
from tom.providers.mock import MockStructuredLLM


def _write_config(tmp_path, name: str, lines: list[str]) -> None:
    text = "\n".join(lines)
    assert 800 <= len(text) <= 30_000, "keep fixtures inside the E2 stratum for a realistic test"
    (tmp_path / name).write_text(text)


def test_aac_report_excludes_pilot_and_pairs_only_valid_constraint_recall(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    for name in ("a.md", "b.md"):
        _write_config(data, name, ["Background prose about a project history."] * 40 +
                      ["Never delete production data."])
    configs = load_configs(data, n_configs=2, seed=11)
    selected = configs[1].label
    root = tmp_path / "records"
    root.mkdir()
    for arm, valid in (("tom", False), ("tom_jev", True)):
        (root / f"{arm}-{selected}-round-1.json").write_text(json.dumps({
            "strategy": arm, "config": selected, "round": 1,
            "comparison_valid": valid, "output_text": "Never delete production data.",
            "budget": 100, "output_tokens": 6,
        }))
    result = report(root, data, n=2, seed=11, exclude_first=1)
    summary = result["by_round"]["1"]
    assert result["n_evaluation"] == 1
    assert result["excluded_development_configs"] == [configs[0].label]
    assert summary["tom"]["full_constraint_recall_and_valid"] == 0
    assert summary["tom_jev"]["full_constraint_recall_and_valid"] == 1
    assert summary["paired_tom_jev_vs_tom"]["joint_full_recall"]["paired_bootstrap_95"] == [1.0, 1.0]


def test_load_configs_only_keeps_e2_stratum_with_a_constraint(tmp_path):
    filler = ["This is background prose about the project history."] * 40
    with_constraint = [*filler, "Never commit secrets to .env files."]
    _write_config(tmp_path, "good.md", with_constraint)

    no_constraint = [*filler, "The app prefers dark mode."]
    _write_config(tmp_path, "no_constraint.md", no_constraint)

    (tmp_path / "too_short.md").write_text("Never commit secrets.")

    configs = load_configs(tmp_path, n_configs=10, seed=1)

    assert [c.label for c in configs] == ["good.md"]
    assert any(item.type == KTType.CONSTRAINT for item in configs[0].kb.items)


def test_load_configs_is_deterministic_for_a_fixed_seed(tmp_path):
    filler = ["Background line about the project."] * 40
    for i in range(5):
        _write_config(tmp_path, f"config{i}.md", [*filler, "Never delete production data."])

    first = [c.label for c in load_configs(tmp_path, n_configs=3, seed=7)]
    second = [c.label for c in load_configs(tmp_path, n_configs=3, seed=7)]

    assert first == second
    assert len(first) == 3


def test_clean_line_strips_markdown_noise():
    assert _clean_line("# Heading") == ""
    assert _clean_line("```bash") == ""
    assert _clean_line("---") == ""
    assert _clean_line("- Never commit secrets.") == "Never commit secrets."
    assert _clean_line("ok") == ""  # fewer than 3 alphabetic runs


def test_split_configs_is_deterministic_and_disjoint():
    configs = [AACConfig(label=label, kb=KTKnowledgeBase(items=[]), text=label)
               for label in ("c.md", "a.md", "b.md", "d.md", "e.md")]
    development, holdout = split_configs(configs, holdout_fraction=0.2)
    assert [config.label for config in development] == ["a.md", "b.md", "c.md", "d.md"]
    assert [config.label for config in holdout] == ["e.md"]
    assert not {config.label for config in development} & {config.label for config in holdout}


def test_controlled_budgets_are_output_independent():
    assert controlled_budgets(1000, ratio=0.5, rounds=3, schedule=BudgetSchedule.FIXED) == [500, 500, 500]
    assert controlled_budgets(1000, ratio=0.5, rounds=3, schedule=BudgetSchedule.PROGRESSIVE) == [500, 250, 125]


def test_resume_rejects_an_incompatible_manifest(tmp_path):
    config = AACConfig(label="a", kb=KTKnowledgeBase(items=[]), text="input")
    manifest = make_controlled_manifest(
        [config], scenario=ControlledScenario.RECURSIVE_TEXT,
        budget_schedule=BudgetSchedule.FIXED, budgets=[64], seed=1, rounds=1,
    )
    write_or_validate_manifest(manifest, tmp_path, resume=False)
    incompatible = make_controlled_manifest(
        [config], scenario=ControlledScenario.PERSISTENT_STATE,
        budget_schedule=BudgetSchedule.FIXED, budgets=[64], seed=1, rounds=1,
    )
    with pytest.raises(ResumeManifestMismatch):
        write_or_validate_manifest(incompatible, tmp_path, resume=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", [ControlledScenario.RECURSIVE_TEXT, ControlledScenario.PERSISTENT_STATE])
async def test_controlled_llm_uses_jev_on_same_events_as_tom(tmp_path, scenario):
    from types import SimpleNamespace

    text = "Never delete production data.\nThe app runs on PostgreSQL."
    config = AACConfig(label="a", text=text, kb=KTKnowledgeBase(items=[
        KTItem(text="Never delete production data.", type=KTType.CONSTRAINT, topic="root"),
    ]))
    observed = MemoryItem(
        id="m", content="Do not delete data", knowledge_type=KnowledgeType.EPISODIC,
        retention=RetentionPolicy.COMPRESSIBLE, importance=Importance.LOW, confidence=0.9,
        source_ids=["e0"], created_at=datetime.now(UTC),
    )
    llm = MockStructuredLLM(ObservedMemories(items=[observed]))

    class FakeBridge(OpenAIBenchmarkBridge):
        def __init__(self):
            pass

        model = "gpt-6-luna-test"
        structured_llm = llm
        last_usage = None

        async def prompt(self, text):
            self.last_usage = {"prompt_tokens": 100, "completion_tokens": 20}
            return "Never delete production data."

    class FakeJev:
        async def system_one(self, *, state, questions):
            return SimpleNamespace(
                choices={k: SimpleNamespace(choice=v) for k, v in {
                    "knowledge_type": "constraint", "retention": "exact", "importance": "high",
                }.items()},
                nouls={"confidence": SimpleNamespace(noul=0.99)},
                usage=SimpleNamespace(input_tokens=729, output_tokens=20), model="jev-test",
            )

    rows = await run_controlled_llm(
        [config], tmp_path, FakeBridge(), scenario=scenario, rounds=1, ratio=1.0,
        jev=JevClassifier(client=FakeJev()),
    )
    by_strategy = {row["strategy"]: row for row in rows}
    assert set(by_strategy) == {"TypeCompact", "vanilla_llm", "tom", "tom_jev", "tom_jev_lines"}
    assert by_strategy["tom"]["input_sha256"] == by_strategy["tom_jev"]["input_sha256"]
    assert by_strategy["tom_jev"]["jev_calls"] == 1
    assert by_strategy["tom_jev_lines"]["jev_calls"] == 2
    assert by_strategy["tom_jev_lines"]["llm_calls"] == 0
    assert by_strategy["tom_jev"]["jev_input_tokens"] == 729
    assert by_strategy["tom_jev"]["jev_model"] == "jev-test"
    assert "Never delete production data." in by_strategy["tom_jev"]["output_text"]
    assert "The app runs on PostgreSQL." in by_strategy["tom_jev_lines"]["output_text"]
    manifest = json.loads((tmp_path / "controlled_manifest.json").read_text())
    assert manifest["observer_model"] == "gpt-6-luna-test" and manifest["jev_enabled"] is True
    if scenario == ControlledScenario.PERSISTENT_STATE:
        (tmp_path / "tom_jev-a-round-1.json").unlink()
        with pytest.raises(ResumeManifestMismatch, match="partial persistent-state"):
            await run_controlled_llm(
                [config], tmp_path, FakeBridge(), scenario=scenario, rounds=1, ratio=1.0,
                jev=JevClassifier(client=FakeJev()), resume=True,
            )
    else:
        cap_rows = await run_controlled_llm(
            [config], tmp_path / "capped", FakeBridge(), scenario=scenario,
            rounds=1, ratio=1.0, jev=JevClassifier(client=FakeJev()), max_cost_usd=0.05001,
        )
        assert [row["strategy"] for row in cap_rows] == ["TypeCompact", "vanilla_llm"]
        assert cap_rows[1]["billed_estimated_cost_usd"] > 0


@pytest.mark.asyncio
async def test_resume_restores_recursive_state_from_prior_round(tmp_path):
    config = AACConfig(label="a", text="Never delete production data.\nExtra prose.", kb=KTKnowledgeBase(
        items=[KTItem(text="Never delete production data.", type=KTType.CONSTRAINT, topic="root")]
    ))
    item = MemoryItem(
        id="m", content="Never delete production data.", knowledge_type=KnowledgeType.CONSTRAINT,
        retention=RetentionPolicy.EXACT, importance=Importance.HIGH, confidence=0.9,
        source_ids=["e0"], created_at=datetime.now(UTC),
    )

    class FakeBridge(OpenAIBenchmarkBridge):
        def __init__(self):
            pass

        model = "test"
        last_usage = None
        structured_llm = MockStructuredLLM(ObservedMemories(items=[item]))

        async def prompt(self, text):
            self.last_usage = {"prompt_tokens": 100, "completion_tokens": 20}
            return "Never delete production data."

    kwargs = {"scenario": ControlledScenario.RECURSIVE_TEXT, "rounds": 2, "ratio": 1.0}
    initial = await run_controlled_llm([config], tmp_path, FakeBridge(), **kwargs)
    first = next(r for r in initial if r["strategy"] == "tom" and r["round"] == 1)
    assert first["output_sha256"] != first["input_sha256"]
    (tmp_path / "tom-a-round-2.json").unlink()
    resumed = await run_controlled_llm([config], tmp_path, FakeBridge(), resume=True, **kwargs)
    second = next(r for r in resumed if r["strategy"] == "tom" and r["round"] == 2)
    assert second["input_sha256"] == first["output_sha256"]


@pytest.mark.asyncio
async def test_controlled_deterministic_run_makes_no_llm_calls(tmp_path):
    items = [
        KTItem(text="Never delete production data.", type=KTType.CONSTRAINT, topic="root"),
        KTItem(text="Run tests before deployment.", type=KTType.PROCEDURAL, topic="root"),
    ]
    config = AACConfig(label="a", kb=KTKnowledgeBase(items=items), text="\n".join(i.text for i in items))
    rows = await run_controlled_deterministic(
        [config], tmp_path, scenario=ControlledScenario.RECURSIVE_TEXT,
        ratio=1.0, rounds=1,
    )
    assert rows and all(row["llm_calls"] == 0 for row in rows)
    assert all(row["protocol_version"] == "controlled-v2" for row in rows)
    assert all(row["input_contract"] == "same_original_text_then_previous_output_only" for row in rows)
    assert all("selected_item_ids" in row and "dropped_item_ids" in row for row in rows)
    assert (tmp_path / "controlled_manifest.json").exists()


@pytest.mark.asyncio
async def test_recursive_unsafe_stops_that_arm_without_reusing_over_budget_output(tmp_path):
    text = "Never " + ("delete production data " * 80)
    items = [KTItem(text=text, type=KTType.CONSTRAINT, topic="root")]
    config = AACConfig(label="a", kb=KTKnowledgeBase(items=items), text=text)
    rows = await run_controlled_deterministic(
        [config], tmp_path, scenario=ControlledScenario.RECURSIVE_TEXT,
        ratio=0.01, rounds=2,
    )
    tom_rows = [row for row in rows if row["strategy"] == "tom_deterministic"]
    assert tom_rows[0]["status"] == "COMPACTION_UNSAFE"
    assert tom_rows[1]["status"] == "not_run_after_unsafe"
    assert tom_rows[1]["output_text"] == ""


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_controlled_renderer_and_selection_are_manifested(tmp_path):
    items = [KTItem(text="Never delete production data.", type=KTType.CONSTRAINT, topic="root")]
    config = AACConfig(label="a", kb=KTKnowledgeBase(items=items), text=items[0].text)
    await run_controlled_deterministic(
        [config], tmp_path, scenario=ControlledScenario.RECURSIVE_TEXT,
        ratio=1.0, rounds=1, renderer="compact", selection=SelectionPolicy.COVERAGE,
    )
    manifest = json.loads((tmp_path / "controlled_manifest.json").read_text())
    assert manifest["policies"]["renderer"] == "compact"
    assert manifest["policies"]["selection"] == "coverage"


@pytest.mark.asyncio
async def test_persistent_controlled_protocol_records_identical_event_batches(tmp_path):
    items = [
        KTItem(text="Never delete production data.", type=KTType.CONSTRAINT, topic="root"),
        KTItem(text="Run tests before deployment.", type=KTType.PROCEDURAL, topic="root"),
    ]
    config = AACConfig(label="a", kb=KTKnowledgeBase(items=items), text="\n".join(i.text for i in items))
    rows = await run_controlled_deterministic(
        [config], tmp_path, scenario=ControlledScenario.PERSISTENT_STATE,
        ratio=1.0, rounds=2,
    )
    by_round = {(row["round"], row["strategy"]): row for row in rows}
    for round_number in (1, 2):
        assert by_round[(round_number, "TypeCompact")]["input_event_ids"] == by_round[(round_number, "tom_deterministic")]["input_event_ids"]
        assert by_round[(round_number, "TypeCompact")]["received_event_ids"] == by_round[(round_number, "tom_deterministic")]["received_event_ids"]


@pytest.mark.asyncio
async def test_controlled_resume_reuses_completed_text_records(tmp_path):
    items = [KTItem(text="Never delete production data.", type=KTType.CONSTRAINT, topic="root")]
    config = AACConfig(label="a", kb=KTKnowledgeBase(items=items), text=items[0].text)
    first = await run_controlled_deterministic(
        [config], tmp_path, scenario=ControlledScenario.RECURSIVE_TEXT,
        ratio=1.0, rounds=1,
    )
    second = await run_controlled_deterministic(
        [config], tmp_path, scenario=ControlledScenario.RECURSIVE_TEXT,
        ratio=1.0, rounds=1, resume=True,
    )
    assert second == first


def test_token_aligned_type_compact_respects_budget_or_reports_unsafe():
    text = "Never delete production data.\nRun tests before deployment.\nThe app uses PostgreSQL."
    output, status, required = type_compact_token_aligned(text, 100)
    assert status == "ok"
    assert required <= 100
    assert count_tokens(output) <= 100

    output, status, required = type_compact_token_aligned(text, 1)
    assert status == "COMPACTION_UNSAFE"
    assert required > 1
    assert "Never delete production data." in output


def test_truncate_to_tokens_uses_four_chars_per_token():
    text = "a" * 100
    assert truncate_to_tokens(text, 10) == "a" * 40


def test_type_compact_reproduces_upstream_constraint_recall_at_high_ratio():
    """Sanity check that the vendored ``type_compact`` behaves exactly like the
    upstream paper describes: constraints survive fully at a generous budget."""
    items = [
        KTItem(text="Never commit secrets to .env files.", type=KTType.CONSTRAINT, topic="root"),
        KTItem(text="Run npm test before deploy.", type=KTType.PROCEDURAL, topic="root"),
        KTItem(text="The app prefers dark mode.", type=KTType.PREFERENCE, topic="root"),
        KTItem(text="Users like fast responses.", type=KTType.BELIEF, topic="root"),
    ]
    kb = KTKnowledgeBase(items=items)
    compacted, status = type_compact(kb, budget=kb.total_tokens)

    assert status == "ok"
    text = "\n".join(item.text for item in compacted.items)
    preservation = per_type_preservation(kb, text)
    assert preservation["constraint"] == 1.0


def test_type_compact_signals_unsafe_below_b_min():
    items = [
        KTItem(text="Never commit secrets to .env files under any circumstance.",
               type=KTType.CONSTRAINT, topic="root"),
    ]
    kb = KTKnowledgeBase(items=items)
    _compacted, status = type_compact(kb, budget=1)
    assert status == "COMPACTION_UNSAFE"


def test_c_recall_matches_constraint_preserved_semantics():
    original = ["Never commit secrets to .env files."]
    assert _c_recall(original, "You must never commit secrets to .env files. right now") == 1.0
    assert _c_recall(original, "The app prefers dark mode.") == 0.0
    assert _c_recall([], "anything") != _c_recall([], "anything")  # NaN != NaN


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_typed_memory_background_has_a_compaction_barrier():
    from tom.benchmarks.typed_strategy import TypedTOMMemory

    memory = TypedTOMMemory(DeterministicObserver(), ContextProjector(),
                            background=True, max_pending_chunks=1)
    event = Event(id="e0", type=EventType.USER, content="Never lose this event.", timestamp=datetime.now(UTC))
    await memory.ingest("session", [event])
    assert await memory.context("session", "", 100) == ""
    await memory.compact("session", 100)
    assert "Never lose this event." in await memory.context("session", "", 100)
    assert memory.background_metrics["barrier_wait_ms"] >= 0
    await memory.aclose()


@pytest.mark.asyncio
async def test_typed_memory_background_surfaces_worker_errors():
    from tom.benchmarks.typed_strategy import TypedTOMMemory

    class FailingObserver(DeterministicObserver):
        async def observe_chunks(self, chunks):
            raise RuntimeError("worker failure")

    memory = TypedTOMMemory(FailingObserver(), ContextProjector(), background=True)
    event = Event(id="e0", type=EventType.USER, content="Never lose this event.", timestamp=datetime.now(UTC))
    await memory.ingest("session", [event])
    with pytest.raises(RuntimeError, match="worker failure"):
        await memory.compact("session", 100)
    await memory.aclose()


@pytest.mark.asyncio
async def test_typed_memory_persists_incremental_state_and_recovers(tmp_path):
    from tom.benchmarks.typed_strategy import TypedTOMMemory
    from tom.memory import SQLiteMemoryStore

    store = SQLiteMemoryStore(tmp_path / "memory.db")
    memory = TypedTOMMemory(DeterministicObserver(), ContextProjector(), store=store,
                            observation_tokens=100)
    first = Event(id="e0", type=EventType.USER, content="Never delete evidence.", timestamp=datetime.now(UTC))
    second = Event(id="e1", type=EventType.USER, content="Run tests before deploy.", timestamp=datetime.now(UTC))
    await memory.ingest("session", [first])
    await memory.compact("session", 100)
    await memory.ingest("session", [second])
    await memory.compact("session", 100)
    await memory.compact("session", 100)

    assert len(memory.memories["session"]) == 2
    assert len({item.id for item in memory.memories["session"]}) == 2
    assert len({source for item in memory.memories["session"] for source in item.source_ids}) == 2
    assert memory.observer._counter == 2

    restarted = TypedTOMMemory(DeterministicObserver(), ContextProjector(), store=store)
    text = await restarted.context("session", "", 100)
    assert "Never delete evidence." in text
    assert "Run tests before deploy." in text
    assert len(restarted.memories["session"]) == 2


@pytest.mark.asyncio
async def test_typed_memory_retry_does_not_duplicate_after_observation_failure():
    from tom.benchmarks.typed_strategy import TypedTOMMemory

    class FailingObserver(DeterministicObserver):
        def __init__(self):
            super().__init__()
            self.fail = True

        async def observe_chunks(self, chunks):
            if self.fail:
                self.fail = False
                raise RuntimeError("temporary observer failure")
            return await super().observe_chunks(chunks)

    observer = FailingObserver()
    memory = TypedTOMMemory(observer, ContextProjector())
    event = Event(id="e0", type=EventType.USER, content="Never lose this event.", timestamp=datetime.now(UTC))
    await memory.ingest("session", [event])
    with pytest.raises(RuntimeError):
        await memory.compact("session", 100)
    await memory.compact("session", 100)
    await memory.compact("session", 100)
    assert len(memory.memories["session"]) == 1


@pytest.mark.asyncio
async def test_typed_tom_compactor_falls_back_to_protected_text_when_over_budget():
    """Below B_min, TOM's ContextProjector raises rather than silently dropping
    protected memory; the benchmark's unsafe fallback should still surface the
    protected content, matching type_compact's best-effort COMPACTION_UNSAFE."""
    now = datetime.now(UTC)
    events = [
        Event(id="e0", type=EventType.USER, content="Never commit secrets to .env files.", timestamp=now),
        Event(id="e1", type=EventType.USER, content="Run npm test before every deploy step.", timestamp=now),
    ]

    def respond(_messages, _response_model):
        now_iso = now.isoformat()
        return {
            "items": [
                {
                    "id": "constraint-0", "content": events[0].content, "knowledge_type": "constraint",
                    "retention": "exact", "importance": "critical", "confidence": 1.0,
                    "source_ids": ["e0"], "scope": [], "created_at": now_iso,
                },
                {
                    "id": "procedure-1", "content": events[1].content, "knowledge_type": "procedure",
                    "retention": "high_fidelity", "importance": "high", "confidence": 1.0,
                    "source_ids": ["e1"], "scope": [], "created_at": now_iso,
                },
            ]
        }

    llm = MockStructuredLLM(respond)
    observer = TypedObserver(llm)
    compactor = TypedTOMCompactor(observer, ContextProjector())

    await compactor.ingest("s", events)
    await compactor.compact("s", budget=1)  # far below B_min for these two protected items

    text = compactor.unsafe_protected_text("s")
    assert "Never commit secrets to .env files." in text
    assert "Run npm test before every deploy step." in text
