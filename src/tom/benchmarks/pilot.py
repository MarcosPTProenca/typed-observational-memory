"""Deterministic pilot manifests and small result summaries for stage 5."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .harness import BenchmarkCase, _history_key, file_sha256, load_cases


def create_pilot_manifests(
    cases: list[BenchmarkCase],
    *,
    benchmark: str,
    dataset_hash: str | None = None,
    max_cases: int = 40,
    seed: str = "stage-5-v1",
) -> dict[str, dict[str, Any]]:
    """Create development/evaluation manifests without choosing by answer quality.

    Histories are the split unit. This prevents LoCoMo questions from the same
    conversation leaking between development and evaluation.
    """
    if max_cases < 2:
        raise ValueError("max_cases must be at least 2")
    groups: dict[str, list[BenchmarkCase]] = defaultdict(list)
    for case in cases:
        groups[_history_key(case.events)].append(case)
    ordered = sorted(groups.items(), key=lambda item: hashlib.sha256(
        f"{seed}:{item[0]}".encode()).hexdigest())
    selected: list[tuple[str, BenchmarkCase]] = []
    # Round-robin avoids filling the pilot with one LoCoMo conversation, while
    # retaining every selected history as an indivisible split unit.
    queues = [(history, iter(sorted(group, key=lambda item: item.id))) for history, group in ordered]
    while queues and len(selected) < max_cases:
        remaining = []
        for history, queue in queues:
            try:
                selected.append((history, next(queue)))
            except StopIteration:
                continue
            remaining.append((history, queue))
            if len(selected) >= max_cases:
                break
        queues = remaining
    selected_groups = list(dict.fromkeys(history for history, _ in selected))
    split_at = max(1, len(selected_groups) // 2)
    split_by_history = {
        history: "development" if index < split_at else "evaluation"
        for index, history in enumerate(selected_groups)
    }
    result = {}
    for split in ("development", "evaluation"):
        split_cases = [case for history, case in selected if split_by_history[history] == split]
        result[split] = {
            "protocol": "stage-5-pilot-v1",
            "benchmark": benchmark,
            "dataset_hash": dataset_hash,
            "seed": seed,
            "case_count": len(split_cases),
            "case_ids": [case.id for case in split_cases],
            "categories": sorted({case.category for case in split_cases}),
            "history_ids": sorted({history for history, case in selected
                                    if split_by_history[history] == split}),
        }
    return result


def write_pilot_manifests(manifests: dict[str, dict[str, Any]], output_dir: str | Path) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for split, manifest in manifests.items():
        (output / f"{split}.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def summarize_results(output_dir: str | Path) -> list[dict[str, Any]]:
    """Aggregate valid quality, failures, retention, and p50/p95 latency."""
    output = Path(output_dir)
    rows = []
    for path in sorted((output / "raw").glob("*.jsonl")):
        if path.name.endswith(".diagnostics.jsonl"):
            continue
        rows.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["strategy"]), str(row.get("category", "unknown")))].append(row)
    summary = []
    for (strategy, category), values in sorted(grouped.items()):
        valid = [row for row in values if row.get("comparison_valid")]
        latencies = sorted(float(row.get("latency_ms", 0)) for row in values)
        correct = sum(bool(row.get("score")) for row in valid)
        quality = correct / len(valid) if valid else None
        margin = 1.96 * ((quality * (1 - quality) / len(valid)) ** 0.5) if valid and quality is not None else None
        summary.append({
            "strategy": strategy,
            "category": category,
            "cases": len(values),
            "valid_cases": len(valid),
            "quality": quality,
            "quality_ci95_low": max(0.0, quality - margin) if margin is not None else None,
            "quality_ci95_high": min(1.0, quality + margin) if margin is not None else None,
            "failure_rate": 1 - len(valid) / len(values),
            "abstention_rate": sum(not str(row.get("hypothesis", "")).strip() for row in values) / len(values),
            "evidence_count": sum(int(row.get("evidence_count", 0)) for row in values),
            "evidence_preserved_rate": _mean_optional(
                row.get("evidence_preserved") for row in values),
            "input_tokens": sum(int(row.get("input_tokens", 0)) for row in values),
            "output_tokens": sum(int(row.get("output_tokens", 0)) for row in values),
            "llm_calls": sum(int(row.get("llm_calls", 0)) for row in values),
            "storage_bytes": sum(len(json.dumps(row, ensure_ascii=False)) for row in values),
            "latency_p50_ms": _percentile(latencies, 0.50),
            "latency_p95_ms": _percentile(latencies, 0.95),
        })
    return summary


def write_summary(output_dir: str | Path) -> Path:
    output = Path(output_dir)
    summary = summarize_results(output)
    path = output / "tables" / "pilot-summary.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]) if summary else ["strategy"])
        writer.writeheader()
        writer.writerows(summary)
    return path


def _mean_optional(values: Any) -> float | None:
    present = [float(value) for value in values if value is not None]
    return sum(present) / len(present) if present else None


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    return values[min(len(values) - 1, max(0, int((len(values) - 1) * fraction)))]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or summarize a stage-5 benchmark pilot")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("benchmark", choices=("longmemeval", "locomo", "json"))
    create.add_argument("dataset")
    create.add_argument("--output", default="results/pilot-manifest")
    create.add_argument("--max-cases", type=int, default=40)
    report = subparsers.add_parser("report")
    report.add_argument("output")
    args = parser.parse_args()
    if args.command == "create":
        cases = load_cases(args.dataset, args.benchmark)
        manifests = create_pilot_manifests(cases, benchmark=args.benchmark,
                                            dataset_hash=file_sha256(args.dataset),
                                            max_cases=args.max_cases)
        write_pilot_manifests(manifests, args.output)
        print(f"Wrote development/evaluation manifests to {args.output}")
    else:
        print(f"Wrote {write_summary(args.output)}")


if __name__ == "__main__":
    main()
