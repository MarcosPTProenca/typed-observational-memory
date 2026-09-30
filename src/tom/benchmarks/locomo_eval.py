"""LoCoMo QA scoring, following snap-research/locomo/task_eval/evaluation.py.

Only answer scoring is reproduced here (not the paper's retrieval metrics). Scores
are computed from saved predictions; rerunning the answerer is unnecessary.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import string
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from nltk.stem import PorterStemmer

from .harness import BenchmarkCase

_STEMMER = PorterStemmer()
_VERSION = "locomo-official-qa-f1-v1"


def _tokens(text: str) -> list[str]:
    # Same order as upstream: lowercase, remove ASCII punctuation, remove articles,
    # collapse whitespace, and Porter-stem each word.
    normalized = text.lower().translate(str.maketrans("", "", string.punctuation))
    normalized = re.sub(r"\b(a|an|the|and)\b", " ", normalized)
    return [_STEMMER.stem(word) for word in normalized.split()]


def _f1(prediction: str, truth: str) -> float:
    predicted, expected = _tokens(prediction), _tokens(truth)
    overlap = sum((Counter(predicted) & Counter(expected)).values())
    if not overlap:
        return 0.0
    precision, recall = overlap / len(predicted), overlap / len(expected)
    return 2 * precision * recall / (precision + recall)


def locomo_official_f1(case: BenchmarkCase, hypothesis: str) -> float:
    """Upstream categories: multi-answer F1 (1), token F1 (2–4), abstention (5)."""
    category = str(case.category)
    if category == "5":
        lowered = hypothesis.lower()
        return float("no information available" in lowered or "not mentioned" in lowered)
    answers = case.answer if isinstance(case.answer, (list, tuple)) else [case.answer]
    scores = []
    for answer in answers:
        truth = str(answer)
        if category == "3":
            truth = truth.split(";")[0].strip()
        if category == "1":
            predictions = [part.strip() for part in hypothesis.split(",")]
            truths = [part.strip() for part in truth.split(",")]
            scores.append(sum(max(_f1(part, gt) for part in predictions) for gt in truths) / len(truths))
        elif category in {"2", "3", "4"}:
            scores.append(_f1(hypothesis, truth))
        else:
            raise ValueError(f"Unknown LoCoMo category: {category}")
    return max(scores)


locomo_official_f1.version = _VERSION  # type: ignore[attr-defined]


def rescore_saved(output: Path) -> Path:
    """Write a separate score table without changing immutable benchmark rows."""
    rows = []
    for path in sorted((output / "raw").glob("*.jsonl")):
        if path.name.endswith(".diagnostics.jsonl"):
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row.get("dataset") != "locomo":
                continue
            case = BenchmarkCase(row["case_id"], "", row["answer"], (), str(row["category"]))
            rows.append({
                "case_id": case.id, "strategy": row["strategy"], "category": case.category,
                "official_f1": locomo_official_f1(case, row["hypothesis"])
                if row.get("comparison_valid") else None,
                "comparison_valid": row.get("comparison_valid"),
                "metric_version": _VERSION,
            })
    path = output / "tables" / "locomo-official-f1.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "case_id", "strategy", "category", "official_f1", "comparison_valid", "metric_version",
        ])
        writer.writeheader()
        writer.writerows(rows)
    paired = defaultdict(dict)
    for row in rows:
        if row["comparison_valid"] and row["strategy"] in {"tom", "tom_jev"}:
            paired[row["case_id"]][row["strategy"]] = row["official_f1"]
    matched = {case_id: value for case_id, value in paired.items() if len(value) == 2}
    if matched:
        clusters: dict[str, list[float]] = defaultdict(list)
        for case_id, value in matched.items():
            clusters[case_id.split(":", 1)[0]].append(value["tom_jev"] - value["tom"])
        histories = sorted(clusters)
        rng = random.Random(11)
        samples: list[float] = []
        for _ in range(10_000):
            sampled = [rng.choice(histories) for _ in histories]
            samples.append(sum(sum(clusters[history]) for history in sampled) /
                           sum(len(clusters[history]) for history in sampled))
        samples.sort()
        summary = {
            "metric": _VERSION, "paired_cases": len(matched), "histories": len(histories),
            "tom_jev_mean": mean(v["tom_jev"] for v in matched.values()),
            "tom_mean": mean(v["tom"] for v in matched.values()),
            "jev_minus_tom": mean(v["tom_jev"] - v["tom"] for v in matched.values()),
            "history_bootstrap_95": [samples[250], samples[9750]],
        }
        (output / "tables" / "locomo-official-summary.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rescore saved LoCoMo predictions without API calls")
    parser.add_argument("output", type=Path)
    print(rescore_saved(parser.parse_args().output))
