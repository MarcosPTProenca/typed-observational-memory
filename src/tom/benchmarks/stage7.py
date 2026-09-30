"""Deterministic Stage 7 evaluation and report generation.

This is deliberately a small report layer over the frozen controlled records;
it never calls a provider and never drops unsafe rows.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import statistics
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tom.context import ContextProjector, ProjectionPolicy, Renderer, SelectionPolicy
from tom.models import Event, EventType
from tom.observer import DeterministicObserver
from tom.observer.tokenizer import count_tokens

from .knowledge_triage_repro import AACConfig, load_configs, per_type_preservation, split_configs
from .typed_strategy import TypedTOMMemory


def summarize_records(records_dir: str | Path, configs: list[AACConfig],
                       *, labels: set[str] | None = None) -> list[dict[str, Any]]:
    by_label = {config.label: config for config in configs}
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for path in sorted(Path(records_dir).glob("*.json")):
        if path.name == "controlled_manifest.json":
            continue
        row = json.loads(path.read_text(encoding="utf-8"))
        if labels is None or row["config"] in labels:
            grouped[(row["protocol"], row["strategy"], row.get("renderer", "legacy"),
                      row.get("selection", "legacy"))].append(row)

    summary = []
    for (protocol, strategy, renderer, selection), rows in sorted(grouped.items()):
        macros = []
        for row in rows:
            config = by_label[row["config"]]
            values = per_type_preservation(config.kb, row.get("output_text", ""))
            present = [value for value in values.values() if not math.isnan(value)]
            if present:
                macros.append(statistics.mean(present))
        valid = [row for row in rows if row["comparison_valid"]]
        summary.append({
            "protocol": protocol,
            "strategy": strategy,
            "renderer": renderer,
            "selection": selection,
            "records": len(rows),
            "valid_records": len(valid),
            "unsafe_rate": 1 - len(valid) / len(rows),
            "macro_preservation": statistics.mean(macros) if macros else None,
            "mean_output_tokens": statistics.mean(row["output_tokens"] for row in rows),
            "llm_calls": sum(row["llm_calls"] for row in rows),
        })
    return summary


async def run_ablations(configs: list[AACConfig], output: str | Path) -> Path:
    """Run paired renderer, selector, and sync/background deterministic arms."""
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "ablations.jsonl"
    rows: list[dict[str, Any]] = []
    for config in configs:
        events = [Event(id=f"e{i}", type=EventType.USER, content=line,
                        timestamp=datetime.now(UTC))
                  for i, line in enumerate(config.text.splitlines()) if line.strip()]
        budget = max(64, int(config.kb.total_tokens * 0.5))
        for renderer_name, compact in (("original", False), ("compact", True)):
            for selection in SelectionPolicy:
                projector = ContextProjector(
                    Renderer(compact=compact), policy=ProjectionPolicy.PAPER,
                    selection=selection,
                )
                try:
                    result = projector.project(
                        await DeterministicObserver().observe(events), budget
                    )
                    text, unsafe = result.text, result.unsafe
                except ValueError:
                    result = projector.project_best_effort(
                        await DeterministicObserver().observe(events), budget
                    )
                    text, unsafe = result.text, True
                rows.append({
                    "family": "projection", "config": config.label,
                    "renderer": renderer_name, "selection": selection.value,
                    "budget": budget, "output_tokens": result.token_count,
                    "comparison_valid": not unsafe and result.token_count <= budget,
                    "macro_preservation": _macro(config, text),
                })
        for background in (False, True):
            memory = TypedTOMMemory(DeterministicObserver(), ContextProjector(),
                                    background=background)
            started = time.perf_counter()
            await memory.ingest(config.label, events)
            await memory.compact(config.label, budget)
            try:
                text = await memory.context(config.label, "", budget)
                unsafe = False
            except ValueError:
                text = ""
                unsafe = True
            if background:
                await memory.aclose()
            rows.append({
                "family": "execution", "config": config.label,
                "background": background, "budget": budget,
                "output_tokens": count_tokens(text),
                "comparison_valid": not unsafe and count_tokens(text) <= budget,
                "macro_preservation": _macro(config, text),
                "elapsed_ms": (time.perf_counter() - started) * 1000,
            })
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                    encoding="utf-8")
    return path


def paired_comparison(records_dir: str | Path, configs: list[AACConfig],
                      labels: set[str] | None = None) -> list[dict[str, Any]]:
    by_label = {config.label: config for config in configs}
    pairs: dict[tuple[str, str, int], dict[str, float]] = defaultdict(dict)
    for path in Path(records_dir).glob("*.json"):
        if path.name == "controlled_manifest.json":
            continue
        row = json.loads(path.read_text(encoding="utf-8"))
        if labels is not None and row["config"] not in labels:
            continue
        values = per_type_preservation(by_label[row["config"]].kb, row.get("output_text", ""))
        present = [value for value in values.values() if not math.isnan(value)]
        if present:
            pairs[(row["protocol"], row["config"], row["round"])][row["strategy"]] = statistics.mean(present)
    by_config: dict[tuple[str, str], list[float]] = defaultdict(list)
    for (protocol, config, _round), values in pairs.items():
        if "TypeCompact" in values and "tom_deterministic" in values:
            by_config[(protocol, config)].append(
                values["TypeCompact"] - values["tom_deterministic"]
            )
    grouped: dict[str, list[float]] = defaultdict(list)
    for (protocol, _config), differences in by_config.items():
        grouped[protocol].append(statistics.mean(differences))
    result = []
    for protocol, differences in sorted(grouped.items()):
        rng = random.Random(11)
        samples = [statistics.mean(rng.choices(differences, k=len(differences)))
                   for _ in range(2000)]
        result.append({
            "protocol": protocol,
            "unit": "configuration_mean_across_rounds",
            "pairs": len(differences),
            "mean_delta_typecompact_minus_tom": statistics.mean(differences),
            "ci95": [sorted(samples)[50], sorted(samples)[1949]],
            "bootstrap_seed": 11, "bootstrap_samples": 2000,
        })
    return result


def _macro(config: AACConfig, text: str) -> float | None:
    values = per_type_preservation(config.kb, text).values()
    present = [value for value in values if not math.isnan(value)]
    return statistics.mean(present) if present else None


def write_report(records_root: str | Path, configs: list[AACConfig]) -> Path:
    root = Path(records_root)
    development, holdout = split_configs(configs)
    development_labels = {config.label for config in development}
    holdout_labels = {config.label for config in holdout}
    summaries = []
    holdout_summaries = []
    paired = []
    holdout_paired = []
    ablations = []
    ablation_path = root / "ablations.jsonl"
    if ablation_path.exists():
        ablations = [json.loads(line) for line in ablation_path.read_text(encoding="utf-8").splitlines() if line]
    for directory in sorted(root.iterdir()):
        if directory.is_dir() and (directory / "controlled_manifest.json").exists():
            summaries.extend(summarize_records(directory, configs))
            holdout_summaries.extend(summarize_records(
                directory, configs, labels=holdout_labels
            ))
            paired.extend(paired_comparison(directory, configs))
            holdout_paired.extend(paired_comparison(directory, configs, holdout_labels))
    report = root / "stage7-report.json"
    report.write_text(json.dumps({
        "protocol": "stage-7-deterministic-v1",
        "configs": [config.label for config in configs],
        "split": {
            "method": "deterministic sorted-label 80/20 partition",
            "status": "exploratory for existing records; freeze split before future runs",
            "development_configs": len(development_labels),
            "holdout_configs": len(holdout_labels),
            "holdout_summaries": holdout_summaries,
            "paired_comparisons": paired,
            "holdout_paired_comparisons": holdout_paired,
        },
        "summaries": summaries,
        "ablations": ablations,
        "limitations": [
            "This report covers deterministic arms only; no LLM arm is included.",
            "Unsafe rows remain in denominators and are not reported as valid wins.",
            "The sample is limited to the available AAC provenance.",
        ],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize deterministic Stage 7 records")
    parser.add_argument("records", default="results/stage7-smoke", nargs="?")
    parser.add_argument("--data-dir", default="data/aac/sample")
    parser.add_argument("--n", type=int, default=3)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--ablations", action="store_true")
    args = parser.parse_args()
    configs = load_configs(args.data_dir, n_configs=args.n, seed=args.seed)
    if args.ablations:
        asyncio.run(run_ablations(configs, args.records))
    print(write_report(args.records, configs))


if __name__ == "__main__":
    main()
