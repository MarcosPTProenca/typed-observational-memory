"""Reproduce the CIKM'26 Knowledge Triage compaction benchmarks and add a TOM column.

Upstream paper/repo: https://github.com/searchsim-org/cikm26-knowledge-triage
(installed here as the ``knowledge-triage`` dependency). This module reuses
the paper's own reference implementations (``type_compact``, preservation
scoring, the AAC config loader convention) so TypeCompact numbers here should
match ``docs/reference-knowledge-triage-*.json`` within sampling variance.
It adds two comparison arms the upstream repo does not have: a vanilla LLM
compactor run through this project's own provider (instead of GPT-5.4/Sonnet),
and TOM's own ingest/compact/context cycle used as a text -> text compressor.

Two tables, matching the upstream repo's paper tables:
  - compression curves (Table 7): one shot compaction at several ratios.
  - multi-round stability (Table 6): the "Compaction Cliff", 5 sequential
    rounds at 50% each, C-recall measured against the ORIGINAL constraint set.

LLM-backed strategies (vanilla_llm, tom) run concurrently across a small pool
of CodexBridge processes, since each bridge serializes its own calls.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import math
import random
import re
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

from knowledge_triage.classifier import KnowledgeType as KTType
from knowledge_triage.classifier import classify_instruction
from knowledge_triage.kb import Item as KTItem
from knowledge_triage.kb import KnowledgeBase as KTKnowledgeBase
from knowledge_triage.operators import type_compact
from knowledge_triage.preservation import PRESERVED_FN, constraint_preserved

from tom.context import ContextProjector, ProjectionPolicy, Renderer, SelectionPolicy
from tom.context.budget import UnsafeContextBudget
from tom.models import Event, EventType, RetentionPolicy
from tom.observer import DeterministicObserver, JevLineObserver, JevRelabeler, TypedObserver
from tom.observer.tokenizer import count_tokens
from tom.providers import CodexBridge, JevClassifier, OpenAIStructuredLLM

CHAR_MIN, CHAR_MAX = 800, 30_000
CHARS_PER_TOKEN = 4


class ControlledScenario(StrEnum):
    RECURSIVE_TEXT = "recursive_text"
    PERSISTENT_STATE = "persistent_state"


class BudgetSchedule(StrEnum):
    FIXED = "fixed"
    PROGRESSIVE = "progressive"


class ResumeManifestMismatch(ValueError):
    """Raised instead of mixing records from incompatible experiments."""


@dataclass(frozen=True)
class ControlledManifest:
    protocol_version: str
    scenario: str
    input_contract: str
    budget_schedule: str
    corpus_sha256: str
    config_sha256: str
    config_labels: tuple[str, ...]
    chunk_order: tuple[tuple[str, ...], ...]
    event_batches: tuple[tuple[tuple[str, ...], ...], ...]
    budgets: tuple[tuple[int, ...], ...]
    seed: int
    code_sha256: str
    dependency_version: str
    classifier: str
    observer_model: str | None
    jev_enabled: bool
    renderer: str
    policies: dict[str, str]


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _config_digest(config: AACConfig) -> str:
    return _sha256(json.dumps(
        [(item.text, item.type.value, item.topic) for item in config.kb.items],
        ensure_ascii=False, separators=(",", ":"),
    ).encode())


def make_controlled_manifest(
    configs: list[AACConfig], *, scenario: ControlledScenario,
    budget_schedule: BudgetSchedule, budgets: list[list[int]], seed: int,
    rounds: int,
    renderer: str = "original", selection: SelectionPolicy = SelectionPolicy.GREEDY,
    observer_model: str | None = None, jev_enabled: bool = False,
) -> ControlledManifest:
    """Freeze every input that can change a controlled result."""
    if rounds < 1:
        raise ValueError("rounds must be positive")
    event_batches = []
    for config in configs:
        lines = [line for line in config.text.splitlines() if line.strip()]
        event_batches.append(tuple(
            tuple(lines[i * len(lines) // rounds:(i + 1) * len(lines) // rounds])
            for i in range(rounds)
        ))
    normalized_budgets = tuple(
        (entry,) if isinstance(entry, int) else tuple(entry) for entry in budgets
    )
    input_contract = (
        "same_original_text_then_previous_output_only"
        if scenario == ControlledScenario.RECURSIVE_TEXT
        else "same_incremental_event_batches_and_prefix_state"
    )
    return ControlledManifest(
        protocol_version="controlled-v2",
        scenario=scenario.value, input_contract=input_contract,
        budget_schedule=budget_schedule.value,
        corpus_sha256=_sha256("\n".join(c.text for c in configs).encode()),
        config_sha256=_sha256("\n".join(_config_digest(c) for c in configs).encode()),
        config_labels=tuple(c.label for c in configs),
        chunk_order=tuple(tuple(i.text for i in c.kb.items) for c in configs),
        event_batches=tuple(event_batches), budgets=normalized_budgets, seed=seed,
        code_sha256=_sha256(Path(__file__).read_bytes()),
        dependency_version=importlib.metadata.version("knowledge-triage"),
        classifier="knowledge_triage.classifier.classify_instruction",
        observer_model=observer_model,
        jev_enabled=jev_enabled,
        renderer="tom.context.renderer.Renderer",
        policies={"min_budget": "64", "controlled_truncation": "false", "llm_calls": "0",
                  "renderer": renderer, "selection": selection.value},
    )


def write_or_validate_manifest(manifest: ControlledManifest, output: str | Path, *, resume: bool) -> None:
    path = Path(output) / "controlled_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(asdict(manifest), indent=2, ensure_ascii=False, sort_keys=True)
    if resume and path.exists() and path.read_text(encoding="utf-8").rstrip() != encoded:
        raise ResumeManifestMismatch(f"incompatible controlled manifest: {path}")
    if not resume or not path.exists():
        path.write_text(encoded + "\n", encoding="utf-8")


def _controlled_record_path(output: Path, record: dict[str, Any]) -> Path:
    return output / f"{record['strategy']}-{record['config']}-round-{record['round']}.json"


def _trace_text_items(input_text: str, output_text: str) -> dict[str, list[str]]:
    items = [(f"line-{index}", line) for index, line in enumerate(input_text.splitlines()) if line.strip()]
    selected = [ident for ident, line in items if line in output_text]
    return {"input_item_ids": [ident for ident, _ in items],
            "selected_item_ids": selected,
            "dropped_item_ids": [ident for ident, _ in items if ident not in selected]}


def _write_controlled_record(output: Path, record: dict[str, Any]) -> None:
    path = _controlled_record_path(output, record)
    if path.exists():
        return
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


@dataclass
class AACConfig:
    label: str
    kb: KTKnowledgeBase
    text: str


def split_configs(configs: list[AACConfig], *, holdout_fraction: float = 0.2) -> tuple[list[AACConfig], list[AACConfig]]:
    """Create a deterministic, label-sorted development/holdout split."""
    if not 0 < holdout_fraction < 1:
        raise ValueError("holdout_fraction must be between 0 and 1")
    ordered = sorted(configs, key=lambda config: config.label)
    split_at = max(1, int(len(ordered) * (1 - holdout_fraction)))
    return ordered[:split_at], ordered[split_at:]


def load_configs(data_dir: str | Path, *, n_configs: int = 20, seed: int = 11) -> list[AACConfig]:
    """Load AgentArtifactCorpus-sample configs, matching the upstream E2 stratum:
    800-30000 chars, at least one constraint item, typed by the paper's regex
    classifier (deterministic, so results are directly comparable)."""
    paths = sorted(Path(data_dir).glob("*.md"))
    random.Random(seed).shuffle(paths)
    configs: list[AACConfig] = []
    for path in paths:
        text = path.read_text(errors="ignore")
        if not (CHAR_MIN <= len(text) <= CHAR_MAX):
            continue
        lines = [_clean_line(line) for line in text.splitlines()]
        lines = [line for line in lines if line]
        if len(lines) < 10:
            continue
        items = [KTItem(text=line, type=classify_instruction(line), topic="root") for line in lines]
        if not any(item.type == KTType.CONSTRAINT for item in items):
            continue
        configs.append(AACConfig(label=path.name, kb=KTKnowledgeBase(items=items), text="\n".join(lines)))
        if len(configs) >= n_configs:
            break
    return configs


def _clean_line(line: str) -> str:
    line = line.strip()
    if not line or line.startswith(("#", "```")):
        return ""
    if re.fullmatch(r"[-=*_~`|]{2,}", line):
        return ""
    if line.startswith(("- ", "* ")):
        line = line[2:].strip()
    return line if len(re.findall(r"[A-Za-z]{2,}", line)) >= 3 else ""


def truncate_to_tokens(text: str, target_tokens: int) -> str:
    """Same 4-chars/token heuristic the upstream repo enforces on every baseline."""
    return text[: target_tokens * CHARS_PER_TOKEN]


def _kb_from_text(text: str) -> KTKnowledgeBase:
    return KTKnowledgeBase(items=[
        KTItem(text=line, type=classify_instruction(line), topic="root")
        for line in text.splitlines() if line.strip()
    ])


def type_compact_token_aligned(text: str, budget: int) -> tuple[str, str, int]:
    """Adapter-only TypeCompact selection using the shared exact tokenizer."""
    if budget < 1:
        raise ValueError("budget must be positive")
    items = _kb_from_text(text).items
    protected = [item for item in items if item.type in (KTType.CONSTRAINT, KTType.PROCEDURAL)]
    protected_text = "\n".join(item.text for item in protected)
    required_tokens = count_tokens(protected_text)
    if required_tokens > budget:
        return protected_text, "COMPACTION_UNSAFE", required_tokens

    selected = list(protected)
    remaining = budget - count_tokens("\n".join(item.text for item in selected))
    quotas = {
        KTType.BELIEF: int(remaining * 0.50),
        KTType.PREFERENCE: int(remaining * 0.20),
    }
    used = {kind: 0 for kind in quotas}
    episodic_budget = remaining
    for kind in (KTType.BELIEF, KTType.PREFERENCE):
        for item in (candidate for candidate in items if candidate.type == kind):
            candidate_text = "\n".join([*(entry.text for entry in selected), item.text])
            cost = count_tokens(candidate_text) - count_tokens(
                "\n".join(entry.text for entry in selected)
            )
            if used[kind] + cost <= quotas[kind]:
                selected.append(item)
                used[kind] += cost
                episodic_budget -= cost
    for item in (candidate for candidate in items if candidate.type == KTType.EPISODIC):
        candidate_text = "\n".join([*(entry.text for entry in selected), item.text])
        cost = count_tokens(candidate_text) - count_tokens(
            "\n".join(entry.text for entry in selected)
        )
        if cost <= episodic_budget:
            selected.append(item)
            episodic_budget -= cost
    return "\n".join(item.text for item in selected), "ok", required_tokens


def controlled_budgets(original_tokens: int, *, ratio: float, rounds: int,
                       schedule: BudgetSchedule) -> list[int]:
    """Derive both arms' budgets from the original input, never their output."""
    if not 0 < ratio <= 1 or rounds < 1:
        raise ValueError("ratio must be in (0, 1] and rounds must be positive")
    return [max(64, int(original_tokens * ratio * (ratio ** r
                    if schedule == BudgetSchedule.PROGRESSIVE else 1)))
            for r in range(rounds)]


async def run_controlled_deterministic(
    configs: list[AACConfig], output: str | Path, *, scenario: ControlledScenario,
    ratio: float = 0.5, rounds: int = 5, schedule: BudgetSchedule = BudgetSchedule.FIXED,
    seed: int = 11, resume: bool = False,
    renderer: str = "original", selection: SelectionPolicy = SelectionPolicy.GREEDY,
) -> list[dict[str, Any]]:
    """Run only TypeCompact and deterministic TOM under a frozen contract.

    The old CLI remains the upstream-compatibility protocol. This function is
    deliberately separate: it uses tiktoken for both arms, never truncates
    protected output, and makes no bridge/LLM calls.
    """
    if not configs:
        return []
    budgets_by_config = [controlled_budgets(c.kb.total_tokens, ratio=ratio,
                                             rounds=rounds, schedule=schedule)
                         for c in configs]
    if renderer not in {"original", "compact"}:
        raise ValueError("renderer must be 'original' or 'compact'")
    projector = ContextProjector(
        Renderer(compact=renderer == "compact"),
        policy=ProjectionPolicy.PAPER, selection=selection,
    )
    manifest = make_controlled_manifest(configs, scenario=scenario,
                                        budget_schedule=schedule, budgets=budgets_by_config,
                                        seed=seed, rounds=rounds,
                                        renderer=renderer, selection=selection)
    root = Path(output)
    write_or_validate_manifest(manifest, root, resume=resume)
    rows: list[dict[str, Any]] = []
    for config_index, config in enumerate(configs):
        budgets = budgets_by_config[config_index]
        if scenario == ControlledScenario.RECURSIVE_TEXT:
            states = {"TypeCompact": config.text, "tom_deterministic": config.text}
            blocked: set[str] = set()
            for round_number, budget in enumerate(budgets, 1):
                for strategy in ("TypeCompact", "tom_deterministic"):
                    record_key = {"strategy": strategy, "config": config.label, "round": round_number}
                    existing_path = _controlled_record_path(root, record_key)
                    if resume and existing_path.exists():
                        existing = json.loads(existing_path.read_text(encoding="utf-8"))
                        rows.append(existing)
                        if existing.get("status") != "ok":
                            blocked.add(strategy)
                        continue
                    if strategy in blocked:
                        row = {"protocol_version": "controlled-v2",
                               "protocol": scenario.value,
                               "input_contract": "same_original_text_then_previous_output_only",
                               "strategy": strategy, "config": config.label,
                               "round": round_number, "budget": budget,
                               "input_tokens": count_tokens(states[strategy]),
                               "output_sha256": None, "output_text": "",
                               "output_tokens": 0, "required_tokens": None,
                               "unsafe": True, "status": "not_run_after_unsafe",
                               "comparison_valid": False, "llm_calls": 0}
                        _write_controlled_record(root, row)
                        rows.append(row)
                        continue
                    input_text = states[strategy]
                    if strategy == "TypeCompact":
                        output_text, status, required_tokens = type_compact_token_aligned(input_text, budget)
                    else:
                        output_text = await _tom_compact_with(
                            DeterministicObserver(), input_text, budget, projector
                        )
                        status = "ok"
                        required_tokens = 0
                    output_tokens = count_tokens(output_text)
                    if strategy == "tom_deterministic" and output_tokens > budget:
                        status = "COMPACTION_UNSAFE"
                        required_tokens = output_tokens
                    valid = status == "ok" and output_tokens <= budget
                    row = {"protocol_version": "controlled-v2",
                           "protocol": scenario.value, "input_contract": "same_original_text_then_previous_output_only",
                           "renderer": renderer, "selection": selection.value,
                           "strategy": strategy, "config": config.label, "round": round_number,
                           "budget": budget, "input_sha256": _sha256(input_text.encode()),
                           "output_sha256": _sha256(output_text.encode()),
                           "output_text": output_text,
                           "input_tokens": count_tokens(input_text),
                           "output_tokens": output_tokens,
                           "required_tokens": required_tokens,
                           "unsafe": status == "COMPACTION_UNSAFE",
                           "status": status, "comparison_valid": valid,
                           "llm_calls": 0}
                    row.update(_trace_text_items(input_text, output_text))
                    _write_controlled_record(root, row)
                    rows.append(row)
                    if valid:
                        states[strategy] = output_text
                    else:
                        blocked.add(strategy)
        else:
            events = _events_from_text(config.text)
            # Exactly the same incremental event batches feed both arms; no
            # output-dependent re-chunking is allowed in the controlled protocol.
            chunks = [events[i * len(events) // rounds:(i + 1) * len(events) // rounds]
                       for i in range(rounds)]
            tom = TypedTOMCompactor(
                DeterministicObserver(), projector
            )
            typed_kb = KTKnowledgeBase(items=[])
            for round_number, budget in enumerate(budgets, 1):
                chunk = chunks[round_number - 1] if round_number <= len(chunks) else []
                typed_kb = KTKnowledgeBase(items=[*typed_kb.items, *[
                    KTItem(text=e.content, type=classify_instruction(e.content), topic="root")
                    for e in chunk]])
                await tom.ingest(config.label, chunk)
                typecompact_text, status, required_tokens = type_compact_token_aligned(
                    "\n".join(i.text for i in typed_kb.items), budget
                )
                outputs = {"TypeCompact": typecompact_text}
                await tom.compact(config.label, budget)
                tom_required_tokens = 0
                try:
                    outputs["tom_deterministic"] = await tom.context(config.label, "", budget)
                    tom_status = "ok"
                except UnsafeContextBudget:
                    outputs["tom_deterministic"] = tom.unsafe_protected_text(config.label)
                    tom_status = "COMPACTION_UNSAFE"
                    tom_required_tokens = count_tokens(outputs["tom_deterministic"])
                for strategy, output_text in outputs.items():
                    record_key = {"strategy": strategy, "config": config.label, "round": round_number}
                    existing_path = _controlled_record_path(root, record_key)
                    if resume and existing_path.exists():
                        rows.append(json.loads(existing_path.read_text(encoding="utf-8")))
                        continue
                    row = {"protocol_version": "controlled-v2",
                           "protocol": scenario.value,
                           "input_contract": "same_incremental_event_batches_and_prefix_state",
                           "renderer": renderer, "selection": selection.value,
                           "strategy": strategy, "config": config.label, "round": round_number,
                           "input_event_ids": [e.id for e in chunk],
                           "received_event_ids": [e.id for e in events[:round_number * len(events) // rounds]],
                           "output_sha256": _sha256(output_text.encode()),
                           "output_text": output_text,
                           "output_tokens": count_tokens(output_text),
                           "required_tokens": required_tokens if strategy == "TypeCompact" else tom_required_tokens,
                           "unsafe": (status == "COMPACTION_UNSAFE") if strategy == "TypeCompact" else (tom_status == "COMPACTION_UNSAFE"),
                           "status": status if strategy == "TypeCompact" else tom_status,
                           "comparison_valid": count_tokens(output_text) <= budget and
                           (status == "ok" if strategy == "TypeCompact" else tom_status == "ok"),
                           "llm_calls": 0}
                    row.update(_trace_text_items(
                        "\n".join(e.content for e in events[:round_number * len(events) // rounds]),
                        output_text,
                    ))
                    _write_controlled_record(root, row)
                    rows.append(row)
    return rows


VANILLA_PROMPT = """Compress the agent configuration below to AT MOST {target_tokens} tokens.

REQUIREMENTS:
- Keep every safety rule, prohibition, "must/never/do not" instruction VERBATIM.
- Keep every procedural command (build/test/deploy commands, exact tool names, file paths) VERBATIM.
- Compress descriptive prose, background information, history as needed.
- HARD LIMIT: output {target_tokens} tokens or fewer.
- Output ONLY the compressed configuration text.

CONFIGURATION:
{config_text}
"""


class OpenAIBenchmarkBridge:
    """One OpenAI model for all generative arms of the controlled experiment."""

    def __init__(self, model: str) -> None:
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI()
        self.model = model
        self.structured_llm = OpenAIStructuredLLM(self.client, model=model)
        self.last_usage: dict[str, Any] | None = None

    async def prompt(self, text: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model, messages=[{"role": "user", "content": text}],
        )
        self.last_usage = response.usage.model_dump(mode="json") if response.usage else None
        return response.choices[0].message.content or ""

    async def aclose(self) -> None:
        await self.client.close()


def _structured_llm(bridge: CodexBridge | OpenAIBenchmarkBridge):
    from tom.providers.pi import PiStructuredLLM

    llm = getattr(bridge, "structured_llm", None)
    return llm if llm is not None else PiStructuredLLM(bridge=cast(CodexBridge, bridge))


async def run_controlled_llm(
    configs: list[AACConfig], output: str | Path, bridge: CodexBridge | OpenAIBenchmarkBridge, *,
    scenario: ControlledScenario, ratio: float = 0.5, rounds: int = 5,
    schedule: BudgetSchedule = BudgetSchedule.FIXED, seed: int = 11,
    resume: bool = False, renderer: str = "original",
    selection: SelectionPolicy = SelectionPolicy.GREEDY,
    jev: JevClassifier | None = None, max_cost_usd: float | None = None,
) -> list[dict[str, Any]]:
    """Run TypeCompact and TOM with/without Jev against identical inputs."""
    if not configs:
        return []
    if scenario not in ControlledScenario:
        raise ValueError("unknown controlled scenario")
    if max_cost_usd is not None and (max_cost_usd <= 0.05 or not isinstance(bridge, OpenAIBenchmarkBridge)):
        raise ValueError("cost cap requires OpenAI provider and must exceed $0.05 reserve")
    budgets_by_config = [controlled_budgets(c.kb.total_tokens, ratio=ratio,
                                             rounds=rounds, schedule=schedule)
                         for c in configs]
    projector = ContextProjector(Renderer(compact=renderer == "compact"),
                                 policy=ProjectionPolicy.PAPER, selection=selection)
    manifest = make_controlled_manifest(
        configs, scenario=scenario, budget_schedule=schedule, budgets=budgets_by_config,
        seed=seed, rounds=rounds, renderer=renderer, selection=selection,
        observer_model=getattr(bridge, "model", None), jev_enabled=jev is not None,
    )
    root = Path(output)
    write_or_validate_manifest(manifest, root, resume=resume)
    strategies = ("TypeCompact", "vanilla_llm", "tom", "tom_jev", "tom_jev_lines") if jev else (
        "TypeCompact", "vanilla_llm", "tom"
    )
    if resume and scenario == ControlledScenario.PERSISTENT_STATE:
        for config in configs:
            paths = [_controlled_record_path(root, {
                "strategy": strategy, "config": config.label, "round": round_number,
            }) for strategy in strategies for round_number in range(1, rounds + 1)]
            if any(path.exists() for path in paths) and not all(path.exists() for path in paths):
                raise ResumeManifestMismatch("cannot resume partial persistent-state config")
    rows: list[dict[str, Any]] = []
    saved = [json.loads(path.read_text(encoding="utf-8")) for path in root.glob("*-round-*.json")]
    if max_cost_usd is not None and resume and any(
        "billed_estimated_cost_usd" not in row and row.get("strategy") != "TypeCompact"
        for row in saved
    ):
        raise ResumeManifestMismatch("cannot enforce a cost cap on unmetered records")
    spent = sum(row.get("billed_estimated_cost_usd", 0.0) for row in saved) if resume else 0.0
    for index, config in enumerate(configs):
        budgets = budgets_by_config[index]
        def observer_for(strategy: str):
            if strategy == "tom_jev_lines":
                assert jev is not None
                return JevLineObserver(jev)
            return TypedObserver(
                _structured_llm(bridge),
                relabeler=JevRelabeler(jev) if jev is not None and strategy == "tom_jev" else None,
            )

        toms = {strategy: TypedTOMCompactor(observer_for(strategy), projector)
                for strategy in strategies if strategy in ("tom", "tom_jev", "tom_jev_lines")}
        states = {strategy: config.text for strategy in strategies}
        events = _events_from_text(config.text)
        typed_text = ""
        blocked: set[str] = set()
        for round_number, budget in enumerate(budgets, 1):
            if scenario == ControlledScenario.PERSISTENT_STATE:
                chunk = events[(round_number - 1) * len(events) // rounds:
                               round_number * len(events) // rounds]
                for memory in toms.values():
                    await memory.ingest(config.label, chunk)
                typed_text = "\n".join([typed_text, *(event.content for event in chunk)]).strip()
            for strategy in strategies:
                key = {"strategy": strategy, "config": config.label, "round": round_number}
                path = _controlled_record_path(root, key)
                if resume and path.exists():
                    row = json.loads(path.read_text(encoding="utf-8"))
                    rows.append(row)
                    if row.get("comparison_valid"):
                        states[strategy] = row["output_text"]
                    if row.get("status") != "ok":
                        blocked.add(strategy)
                    continue
                input_text = (states[strategy] if scenario == ControlledScenario.RECURSIVE_TEXT
                              else typed_text)
                row: dict[str, Any]
                if strategy in blocked:
                    row = {"protocol_version": "controlled-v2-llm", "protocol": scenario.value,
                           "strategy": strategy, "config": config.label, "round": round_number,
                           "budget": budget, "input_text": input_text, "output_text": "",
                           "input_tokens": count_tokens(input_text), "output_tokens": 0,
                           "status": "not_run_after_unsafe", "unsafe": True,
                           "comparison_valid": False, "llm_calls": 0}
                elif strategy == "TypeCompact":
                    output_text, status, required = type_compact_token_aligned(input_text, budget)
                    row = {"required_tokens": required, "llm_calls": 0}
                    row.update({"output_text": output_text, "status": status})
                elif strategy == "vanilla_llm":
                    if max_cost_usd is not None and spent >= max_cost_usd - 0.05:
                        return rows
                    output_text = await vanilla_llm_compact(bridge, input_text, budget)
                    usage = bridge.last_usage or {}
                    billed = ((0.125 * usage.get("prompt_tokens", 0) +
                               0.50 * usage.get("completion_tokens", 0)) / 1_000_000
                              if isinstance(bridge, OpenAIBenchmarkBridge) else 0.0)
                    spent += billed
                    status = "ok" if count_tokens(output_text) <= budget else "COMPACTION_UNSAFE"
                    row = {"required_tokens": count_tokens(output_text) if status != "ok" else 0,
                           "llm_calls": 1, "provider_usage": usage,
                           "billed_estimated_cost_usd": billed,
                           "output_text": output_text, "status": status}
                else:
                    if max_cost_usd is not None and spent >= max_cost_usd - 0.05:
                        return rows
                    memory = toms[strategy] if scenario == ControlledScenario.PERSISTENT_STATE else (
                        TypedTOMCompactor(observer_for(strategy), projector)
                    )
                    if scenario == ControlledScenario.RECURSIVE_TEXT:
                        await memory.ingest(config.label, _events_from_text(input_text))
                    previous = memory._impl.last_metrics
                    await memory.compact(config.label, budget)
                    try:
                        output_text = await memory.context(config.label, "", budget)
                        status = "ok"
                    except UnsafeContextBudget:
                        output_text = memory.unsafe_protected_text(config.label)
                        status = "COMPACTION_UNSAFE"
                    metrics = memory._impl.last_metrics
                    input_delta = metrics.observer_input_tokens - previous.observer_input_tokens
                    output_delta = metrics.observer_output_tokens - previous.observer_output_tokens
                    jev_delta = metrics.jev_input_tokens - previous.jev_input_tokens
                    billed = ((0.125 * input_delta + 0.50 * output_delta + 0.042 * jev_delta)
                              / 1_000_000) if isinstance(bridge, OpenAIBenchmarkBridge) else 0.0
                    spent += billed
                    usage = {"prompt_tokens": input_delta, "completion_tokens": output_delta}
                    row = {"required_tokens": count_tokens(output_text) if status != "ok" else 0,
                           "llm_calls": metrics.llm_calls - previous.llm_calls,
                           "provider_usage": usage,
                           "jev_model": jev.model if jev is not None and strategy in ("tom_jev", "tom_jev_lines") else None,
                           "jev_calls": metrics.jev_calls - previous.jev_calls,
                           "jev_input_tokens": jev_delta,
                           "jev_output_tokens": metrics.jev_output_tokens - previous.jev_output_tokens,
                           "billed_estimated_cost_usd": billed,
                           "output_text": output_text, "status": status}
                output_text = row["output_text"]
                output_tokens = count_tokens(output_text)
                row.update({"protocol_version": "controlled-v2-llm", "protocol": scenario.value,
                            "renderer": renderer, "selection": selection.value,
                            "strategy": strategy, "config": config.label, "round": round_number,
                            "budget": budget, "input_sha256": _sha256(input_text.encode()),
                            "output_sha256": _sha256(output_text.encode()),
                            "input_tokens": count_tokens(input_text), "output_tokens": output_tokens,
                            "unsafe": row["status"] != "ok",
                            "comparison_valid": row["status"] == "ok" and output_tokens <= budget})
                row.update(_trace_text_items(input_text, output_text))
                _write_controlled_record(root, row)
                rows.append(row)
                if row["comparison_valid"]:
                    states[strategy] = output_text
                else:
                    blocked.add(strategy)
    return rows


async def vanilla_llm_compact(
    bridge: CodexBridge | OpenAIBenchmarkBridge, text: str, target_tokens: int
) -> str:
    prompt = VANILLA_PROMPT.format(target_tokens=target_tokens, config_text=text[:30_000])
    return await bridge.prompt(prompt)


def _events_from_text(text: str) -> list[Event]:
    lines = [line for line in text.splitlines() if line.strip()]
    base_time = datetime.now(UTC)
    return [
        Event(id=f"e{i}", type=EventType.USER, content=line, timestamp=base_time + timedelta(seconds=i))
        for i, line in enumerate(lines)
    ]


async def _tom_compact_with(observer, text: str, target_tokens: int,
                             projector: ContextProjector | None = None) -> str:
    """Shared ingest -> compact -> project cycle for any Observer implementation
    (LLM-backed TypedObserver or the regex-backed DeterministicObserver)."""
    memory = TypedTOMCompactor(observer, projector or ContextProjector())
    await memory.ingest("kt-repro", _events_from_text(text))
    await memory.compact("kt-repro", target_tokens)
    try:
        return await memory.context("kt-repro", "constraints and procedures", target_tokens)
    except UnsafeContextBudget:
        # Budget below B_min (sum of EXACT/HIGH_FIDELITY tokens): TOM refuses to
        # silently drop protected memory. type_compact instead returns
        # "COMPACTION_UNSAFE" with the protected items included regardless of
        # budget, so best-effort match that here for a fair comparison rather
        # than scoring TOM as a hard failure on every under-budget config.
        return memory.unsafe_protected_text("kt-repro")


async def tom_compact(bridge: CodexBridge, text: str, target_tokens: int) -> str:
    """Use TOM's real ingest -> observe -> compact -> project cycle as a
    text -> text compressor, directly comparable to the paper's baselines."""
    from tom.providers.pi import PiStructuredLLM

    observer = TypedObserver(PiStructuredLLM(bridge=bridge))
    return await _tom_compact_with(observer, text, target_tokens)


async def tom_deterministic_compact(_bridge: CodexBridge, text: str, target_tokens: int) -> str:
    """Same TypedTOMMemory pipeline as ``tom_compact``, but classification comes
    from Knowledge Triage's own regex classifier instead of an LLM. Isolates
    whether TOM's remaining recall gap against TypeCompact is caused by LLM
    classification noise or by the observe/compact/project mechanism itself.
    Takes an unused ``_bridge`` argument only to share the same call signature
    as the LLM-backed strategies for the runner's dispatch loop.
    """
    return await _tom_compact_with(DeterministicObserver(), text, target_tokens)


async def tom_deterministic_compact_paper(
    _bridge: CodexBridge, text: str, target_tokens: int,
) -> str:
    return await _tom_compact_with(
        DeterministicObserver(), text, target_tokens,
        ContextProjector(policy=ProjectionPolicy.PAPER),
    )


class TypedTOMCompactor:
    """Thin wrapper matching tom.benchmarks.typed_strategy.TypedTOMMemory, but with
    query-conditioned retrieval disabled.

    ``TypeAwareRetriever`` gates non-global-scope constraints behind a query match
    (correct for domain-conditional rules such as "for payments only, never..."),
    but this benchmark task has no query at all -- it is a pure budget-constrained
    compaction, exactly like ``type_compact``. Using ``use_retrieval=True`` here
    would silently drop scoped constraints whenever the fixed probe query does not
    happen to name their domain, which is not a TOM limitation this benchmark is
    meant to measure. ``use_retrieval=False`` falls back to ``ContextProjector``,
    which pins every EXACT/HIGH_FIDELITY item unconditionally -- the same task
    ``type_compact`` performs.
    """

    def __init__(self, observer, projector: ContextProjector) -> None:
        from tom.benchmarks.typed_strategy import TypedTOMMemory

        self._impl = TypedTOMMemory(observer, projector, use_retrieval=False)

    async def ingest(self, session_id: str, events: list[Event]) -> None:
        await self._impl.ingest(session_id, events)

    async def compact(self, session_id: str, budget: int) -> None:
        await self._impl.compact(session_id, budget)

    async def context(self, session_id: str, query: str, budget: int) -> str:
        return await self._impl.context(session_id, query, budget)

    def unsafe_protected_text(self, session_id: str) -> str:
        """Render every protected (EXACT/HIGH_FIDELITY) item unconditionally,
        ignoring the budget -- the same best-effort output type_compact returns
        under ``COMPACTION_UNSAFE``."""
        memories = self._impl.memories.get(session_id, [])
        protected = [m for m in memories if self._impl.projector._is_protected(m)
                     or m.retention == RetentionPolicy.HIGH_FIDELITY]
        return self._impl.projector.renderer.render(protected)


def per_type_preservation(kb: KTKnowledgeBase, output_text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for ktype in KTType:
        items = kb.by_type(ktype)
        if not items:
            out[ktype.value] = float("nan")
            continue
        preserved = sum(1 for item in items if PRESERVED_FN[ktype](item.text, output_text))
        out[ktype.value] = preserved / len(items)
    return out


def _macro(per_type: dict[str, float]) -> float | None:
    valid = [v for v in per_type.values() if not (isinstance(v, float) and math.isnan(v))]
    return round(statistics.mean(valid), 4) if valid else None


@dataclass
class _CompactionResult:
    name: str
    per_type: dict[str, float]
    elapsed_sec: float


async def _run_llm_compaction(
    name: str, compact_fn: Any, bridge: CodexBridge, config: AACConfig, budget: int,
) -> _CompactionResult | None:
    started = time.perf_counter()
    try:
        text = await compact_fn(bridge, config.text, budget)
    except Exception as exc:  # noqa: BLE001 - one config's failure must not abort the batch
        print(f"  {name} failed on {config.label}: {type(exc).__name__}: {exc}")
        return None
    elapsed_sec = time.perf_counter() - started
    text = truncate_to_tokens(text, budget)
    return _CompactionResult(name=name, per_type=per_type_preservation(config.kb, text), elapsed_sec=elapsed_sec)


async def run_compression_curves(
    configs: list[AACConfig], bridges: list[CodexBridge], *, ratios: tuple[float, ...] = (0.5, 0.25, 0.1),
) -> dict[str, Any]:
    out: dict[str, Any] = {"name": "tom_compression_curves", "n": len(configs), "ratios": list(ratios)}
    per_ratio: dict[str, Any] = {}
    for ratio in ratios:
        strategies: dict[str, dict[str, list[float]]] = {
            "TypeCompact": {ktype.value: [] for ktype in KTType},
            "vanilla_llm": {ktype.value: [] for ktype in KTType},
            "tom": {ktype.value: [] for ktype in KTType},
            "tom_deterministic": {ktype.value: [] for ktype in KTType},
        }
        elapsed: dict[str, list[float]] = {name: [] for name in strategies}
        n_completed: dict[str, int] = {name: 0 for name in strategies}

        for config in configs:
            budget = max(64, int(config.kb.total_tokens * ratio))
            started = time.perf_counter()
            compacted_kb, _status = type_compact(config.kb, budget)
            tc_text = truncate_to_tokens("\n".join(item.text for item in compacted_kb.items), budget)
            elapsed["TypeCompact"].append(time.perf_counter() - started)
            for ktype, value in per_type_preservation(config.kb, tc_text).items():
                if not math.isnan(value):
                    strategies["TypeCompact"][ktype].append(value)
            n_completed["TypeCompact"] += 1

        for name, compact_fn in (
            ("vanilla_llm", vanilla_llm_compact),
            ("tom", tom_compact),
            ("tom_deterministic", tom_deterministic_compact),
        ):
            tasks = [
                _run_llm_compaction(
                    name, compact_fn, bridges[index % len(bridges)], config,
                    max(64, int(config.kb.total_tokens * ratio)),
                )
                for index, config in enumerate(configs)
            ]
            for result in await asyncio.gather(*tasks):
                if result is None:
                    continue
                elapsed[result.name].append(result.elapsed_sec)
                for ktype, value in result.per_type.items():
                    if not math.isnan(value):
                        strategies[result.name][ktype].append(value)
                n_completed[result.name] += 1

        per_ratio[str(ratio)] = {
            "strategies": {
                name: {
                    "per_type_mean": {
                        ktype: round(statistics.mean(vals), 4) if vals else None
                        for ktype, vals in per_type.items()
                    },
                    "overall_macro": _macro({
                        ktype: (statistics.mean(vals) if vals else float("nan"))
                        for ktype, vals in per_type.items()
                    }),
                    "elapsed_mean": round(statistics.mean(elapsed[name]), 3) if elapsed[name] else 0.0,
                    "n_completed": n_completed[name],
                }
                for name, per_type in strategies.items()
            }
        }
    out["per_ratio"] = per_ratio
    return out


@dataclass
class _StabilityResult:
    completed: bool
    recalls: dict[int, float]


async def _run_stability_one(
    compact_fn: Any, bridge: CodexBridge, config: AACConfig, original_constraints: list[str],
    *, n_rounds: int, ratio: float, name: str,
) -> _StabilityResult:
    current_text = config.text
    budget = max(64, int(config.kb.total_tokens * ratio))
    recalls: dict[int, float] = {}
    try:
        for r in range(1, n_rounds + 1):
            current_text = await compact_fn(bridge, current_text, budget)
            current_text = truncate_to_tokens(current_text, budget)
            recalls[r] = _c_recall(original_constraints, current_text)
            budget = max(64, int(len(current_text) // CHARS_PER_TOKEN * ratio))
    except Exception as exc:  # noqa: BLE001 - one config's failure must not abort the batch
        print(f"  {name} failed on {config.label}: {type(exc).__name__}: {exc}")
        return _StabilityResult(completed=False, recalls=recalls)
    return _StabilityResult(completed=True, recalls=recalls)


async def run_multiturn_stability(
    configs: list[AACConfig], bridges: list[CodexBridge], *, n_rounds: int = 5, ratio: float = 0.5,
) -> dict[str, Any]:
    out: dict[str, Any] = {"name": "tom_multiturn_stability", "n_configs": len(configs),
                            "n_rounds": n_rounds, "ratio": ratio}
    original_constraints = [[item.text for item in c.kb.by_type(KTType.CONSTRAINT)] for c in configs]

    per_strategy: dict[str, Any] = {}

    tc_rounds: dict[int, list[float]] = {r: [] for r in range(1, n_rounds + 1)}
    for index, config in enumerate(configs):
        current_kb = config.kb
        budget = max(64, int(current_kb.total_tokens * ratio))
        for r in range(1, n_rounds + 1):
            compacted_kb, _status = type_compact(current_kb, budget)
            text = truncate_to_tokens("\n".join(item.text for item in compacted_kb.items), budget)
            tc_rounds[r].append(_c_recall(original_constraints[index], text))
            current_kb = compacted_kb
            budget = max(64, int(current_kb.total_tokens * ratio))
    per_strategy["TypeCompact"] = {f"round_{r}_c_recall": round(statistics.mean(v), 4) for r, v in tc_rounds.items()}

    for name, compact_fn in (
        ("vanilla_llm", vanilla_llm_compact),
        ("tom", tom_compact),
        ("tom_deterministic", tom_deterministic_compact),
    ):
        tasks = [
            _run_stability_one(
                compact_fn, bridges[index % len(bridges)], config, original_constraints[index],
                n_rounds=n_rounds, ratio=ratio, name=name,
            )
            for index, config in enumerate(configs)
        ]
        results = await asyncio.gather(*tasks)
        rounds: dict[int, list[float]] = {r: [] for r in range(1, n_rounds + 1)}
        completed = 0
        for result in results:
            completed += int(result.completed)
            for r, value in result.recalls.items():
                rounds[r].append(value)
        per_strategy[name] = {
            f"round_{r}_c_recall": (round(statistics.mean(v), 4) if v else None) for r, v in rounds.items()
        }
        per_strategy[name]["n_completed"] = completed
    out["per_strategy"] = per_strategy
    return out


def _c_recall(original_constraints: list[str], output_text: str) -> float:
    if not original_constraints:
        return float("nan")
    return sum(1 for c in original_constraints if constraint_preserved(c, output_text)) / len(original_constraints)


async def main_async(args: argparse.Namespace) -> None:
    if args.jev and not (args.protocol and args.llm_controlled and args.provider == "openai"):
        raise SystemExit("--jev requires --protocol, --llm-controlled and --provider openai")
    if args.provider == "openai" and (args.max_cost_usd is None or args.model != "gpt-6-luna"):
        raise SystemExit("--provider openai requires --model gpt-6-luna and --max-cost-usd")
    if args.provider == "openai" and not (args.protocol and args.llm_controlled):
        raise SystemExit("--provider openai requires --protocol and --llm-controlled")
    configs = load_configs(args.data_dir, n_configs=args.n, seed=args.seed)
    if not configs:
        raise SystemExit(f"No eligible configs found under {args.data_dir}")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if args.protocol and args.llm_controlled:
        scenario = ControlledScenario(args.protocol)
        bridge = (OpenAIBenchmarkBridge(args.model) if args.provider == "openai"
                  else CodexBridge(model=args.model))
        jev = JevClassifier() if args.jev else None
        try:
            rows = await run_controlled_llm(
                configs, output / scenario.value, bridge, scenario=scenario,
                ratio=args.ratio, rounds=args.rounds,
                schedule=BudgetSchedule(args.schedule), seed=args.seed, resume=args.resume,
                renderer=args.renderer, selection=SelectionPolicy(args.selection), jev=jev,
                max_cost_usd=args.max_cost_usd,
            )
        finally:
            if jev is not None:
                await jev.aclose()
            if isinstance(bridge, OpenAIBenchmarkBridge):
                await bridge.aclose()
            else:
                bridge.close()
        expected = len(configs) * args.rounds * (5 if args.jev else 3)
        print(f"Wrote {len(rows)}/{expected} controlled LLM records to {output / scenario.value}")
        if len(rows) < expected:
            print("INCOMPLETE: cost cap reached; resume only with an explicitly approved higher cap")
        return
    if args.protocol:
        scenario = ControlledScenario(args.protocol)
        rows = await run_controlled_deterministic(
            configs, output / scenario.value, scenario=scenario,
            ratio=args.ratio, rounds=args.rounds,
            schedule=BudgetSchedule(args.schedule), seed=args.seed, resume=args.resume,
            renderer=args.renderer, selection=SelectionPolicy(args.selection),
        )
        print(f"Wrote {len(rows)} controlled records to {output / scenario.value}")
        return
    bridges = [CodexBridge(model=args.model) for _ in range(args.parallel)]
    try:
        if args.table in ("curves", "both"):
            curves = await run_compression_curves(
                configs, bridges, ratios=tuple(float(x) for x in args.ratios.split(","))
            )
            (output / "compression_curves.json").write_text(json.dumps(curves, indent=2))
            print(f"Wrote {output / 'compression_curves.json'}")
        if args.table in ("stability", "both"):
            stability = await run_multiturn_stability(configs, bridges, n_rounds=args.rounds, ratio=args.ratio)
            (output / "multiturn_stability.json").write_text(json.dumps(stability, indent=2))
            print(f"Wrote {output / 'multiturn_stability.json'}")
    finally:
        for bridge in bridges:
            bridge.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reproduce Knowledge Triage compaction tables with a TOM comparison arm."
    )
    parser.add_argument("--data-dir", default="data/aac/sample")
    parser.add_argument("--table", choices=("curves", "stability", "both"), default="both")
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--ratios", default="0.50,0.25,0.10")
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--ratio", type=float, default=0.50)
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--provider", choices=("codex", "openai"), default="codex")
    parser.add_argument("--jev", action="store_true", help="classify every TOM item with Jev")
    parser.add_argument("--max-cost-usd", type=float, help="estimated cap for this run, including Jev")
    parser.add_argument("--parallel", type=int, default=4, help="concurrent Codex bridges")
    parser.add_argument("--output", default="results/knowledge-triage-repro")
    parser.add_argument("--protocol", choices=[scenario.value for scenario in ControlledScenario],
                        help="run a controlled protocol")
    parser.add_argument("--llm-controlled", action="store_true",
                        help="use the Pi/Codex observer in the controlled protocol")
    parser.add_argument("--schedule", choices=[schedule.value for schedule in BudgetSchedule],
                        default=BudgetSchedule.FIXED.value)
    parser.add_argument("--resume", action="store_true",
                        help="resume controlled records only when the manifest matches")
    parser.add_argument("--renderer", choices=("original", "compact"), default="original",
                        help="controlled TOM renderer")
    parser.add_argument("--selection", choices=[policy.value for policy in SelectionPolicy],
                        default=SelectionPolicy.GREEDY.value,
                        help="controlled TOM selection policy")
    asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
