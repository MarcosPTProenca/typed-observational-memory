"""Offline, paired analysis of AAC controlled records (no model calls)."""

from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path

from knowledge_triage.classifier import KnowledgeType as KTType

from .knowledge_triage_repro import _c_recall, load_configs


def report(records: Path, data_dir: Path, *, n: int, seed: int, exclude_first: int = 0) -> dict:
    configs = load_configs(data_dir, n_configs=n, seed=seed)
    if not 0 <= exclude_first < len(configs):
        raise ValueError("exclude_first must leave at least one evaluation config")
    excluded = [config.label for config in configs[:exclude_first]]
    references = {
        config.label: [item.text for item in config.kb.by_type(KTType.CONSTRAINT)]
        for config in configs[exclude_first:]
    }
    rows: dict[tuple[str, int, str], dict] = {}
    for path in records.glob("*-round-*.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row["config"] in references:
            rows[(row["strategy"], row["round"], row["config"])] = row
    summary: dict = {
        "protocol": "aac-controlled-paired-v1", "seed": seed, "n_selected": len(configs),
        "excluded_development_configs": excluded, "n_evaluation": len(references),
        "by_round": {},
    }
    rounds = sorted({round_number for _, round_number, _ in rows})
    strategies = sorted({name for name, _, _ in rows})
    for round_number in rounds:
        available = {name: {config: rows[(name, round_number, config)]
                            for config in references if (name, round_number, config) in rows}
                     for name in strategies}
        round_summary: dict = {}
        for name, selected in available.items():
            valid = [row for row in selected.values() if row["comparison_valid"]]
            recalls = {config: _c_recall(references[config], row["output_text"])
                       for config, row in selected.items() if row["comparison_valid"]}
            round_summary[name] = {
                "n": len(selected), "valid": len(valid),
                "full_constraint_recall_and_valid": sum(value == 1 for value in recalls.values()),
                "mean_constraint_recall_valid_only": round(statistics.mean(recalls.values()), 4)
                if recalls else None,
                "mean_output_to_budget": round(statistics.mean(
                    row["output_tokens"] / row["budget"] for row in selected.values()), 4)
                if selected else None,
                "estimated_usd": round(sum(row.get("billed_estimated_cost_usd", 0.0)
                                           for row in selected.values()), 6),
            }
        if "tom" in available and "tom_jev" in available:
            ids = sorted(available["tom"].keys() & available["tom_jev"].keys())
            def values(name: str, config: str, available: dict = available) -> tuple[int, int]:
                row = available[name][config]
                valid = bool(row["comparison_valid"])
                return int(valid), int(valid and _c_recall(references[config], row["output_text"]) == 1)

            differences = [[values("tom_jev", config)[i] - values("tom", config)[i]
                            for config in ids] for i in (0, 1)]
            rng = random.Random(seed + round_number)
            paired = {}
            for name, diffs in zip(("validity", "joint_full_recall"), differences, strict=True):
                replicates = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs)
                                    for _ in range(10_000)) if diffs else []
                paired[name] = {
                    "n": len(diffs), "jev_minus_tom": round(statistics.mean(diffs), 4) if diffs else None,
                    "paired_bootstrap_95": [round(replicates[int(0.025 * len(replicates))], 4),
                                            round(replicates[int(0.975 * len(replicates))], 4)]
                    if replicates else None,
                }
            round_summary["paired_tom_jev_vs_tom"] = paired
        summary["by_round"][str(round_number)] = round_summary
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize saved AAC compaction records offline")
    parser.add_argument("records", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path("data/aac/sample"))
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--exclude-first", type=int, default=2)
    args = parser.parse_args()
    path = args.records.parent / "summary.json"
    path.write_text(json.dumps(report(args.records, args.data_dir, n=args.n, seed=args.seed,
                                      exclude_first=args.exclude_first), indent=2) + "\n")
    print(path)
