"""Post-hoc Jev/cascade agreement and 10%-budget audit on the frozen AAC sample.

Only ``collect`` calls Jev. ``analyze`` reads cached labels and completed benchmark
records; neither the compaction arms nor their scores see cascade labels.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from knowledge_triage.classifier import KnowledgeType as KTType

from tom.context import ContextProjector, ProjectionPolicy, Renderer
from tom.models import Importance, KnowledgeType, MemoryItem, RetentionPolicy
from tom.observer.tokenizer import count_tokens
from tom.providers import JevClassifier

from .knowledge_triage_repro import AACConfig, _events_from_text, load_configs
from .kt_cascade import _key


def _cache(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return {row["key"]: row for line in path.read_text().splitlines() if (row := json.loads(line))}


async def collect(configs: list[AACConfig], path: Path, *, workers: int = 6) -> dict:
    """Cache one Jev call per distinct line; append immediately for safe resume."""
    existing = _cache(path)
    texts = sorted({item.text for cfg in configs for item in cfg.kb.items})
    todo = [text for text in texts if _key(text) not in existing]
    client = JevClassifier()
    sem = asyncio.Semaphore(workers)
    path.parent.mkdir(parents=True, exist_ok=True)

    async def one(text: str) -> None:
        async with sem:
            for attempt in range(3):
                try:
                    labels = await client.classify_labels(text)
                    with path.open("a", encoding="utf-8") as handle:
                        handle.write(
                            json.dumps(
                                {
                                    "key": _key(text),
                                    "type": labels.knowledge_type.value,
                                    "importance": labels.importance.value,
                                }
                            )
                            + "\n"
                        )
                    return
                except Exception:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(5 * (attempt + 1))

    try:
        await asyncio.gather(*(one(text) for text in todo))
        return {
            "new_calls": client.last_calls,
            "new_input_tokens": client.last_input_tokens,
            "estimated_usd": round(client.last_input_tokens * 0.042 / 1_000_000, 6),
            "model": client.model,
            "distinct_lines": len(texts),
        }
    finally:
        await client.aclose()


def analyze(configs: list[AACConfig], cascade_path: Path, jev_path: Path, benchmark: Path) -> dict:
    cascade, jev = _cache(cascade_path), _cache(jev_path)
    lines = {item.text for cfg in configs for item in cfg.kb.items}
    missing = [text for text in lines if _key(text) not in cascade or _key(text) not in jev]
    if missing:
        raise ValueError(
            f"incomplete label caches: {len(missing)} missing of {len(lines)} distinct lines"
        )
    types = [t.value for t in KTType]

    # KT uses PROCEDURAL; TOM/Jev uses PROCEDURE for the same class.
    def gt_name(jev_type: str) -> str:
        return "procedural" if jev_type == "procedure" else jev_type

    confusion: Counter[tuple[str, str]] = Counter()
    by_stage: dict[str, Counter[tuple[str, str]]] = {}
    for text in lines:
        gt, pred = cascade[_key(text)], jev[_key(text)]
        predicted = gt_name(pred["type"])
        confusion[(gt["type"], predicted)] += 1
        by_stage.setdefault(gt["decided_by"], Counter())[(gt["type"], predicted)] += 1
    total = len(lines)
    agreement = sum(confusion[(t, t)] for t in types) / total
    gt_counts = Counter({t: sum(confusion[(t, p)] for p in types) for t in types})
    pred_counts = Counter({t: sum(confusion[(g, t)] for g in types) for t in types})
    chance = sum(gt_counts[t] * pred_counts[t] for t in types) / (total * total)
    scores = {}
    for t in types:
        tp = confusion[(t, t)]
        scores[t] = {
            "support": gt_counts[t],
            "predicted": pred_counts[t],
            "precision": round(tp / pred_counts[t], 4) if pred_counts[t] else None,
            "recall": round(tp / gt_counts[t], 4) if gt_counts[t] else None,
        }
    projector = ContextProjector(Renderer(compact=True), policy=ProjectionPolicy.STANDARD)
    audit = []
    for cfg in configs:
        record_path = benchmark / "curves" / f"tom_jev_lines--0.1--{cfg.label}.json"
        record = json.loads(record_path.read_text())
        events = _events_from_text(cfg.text)
        memories = [
            MemoryItem(
                id=e.id,
                content=e.content,
                knowledge_type=KnowledgeType(jev[_key(e.content)]["type"]),
                retention=(
                    RetentionPolicy.EXACT
                    if jev[_key(e.content)]["type"] == "constraint"
                    else RetentionPolicy.HIGH_FIDELITY
                    if jev[_key(e.content)]["type"] == "procedure"
                    else RetentionPolicy.COMPRESSIBLE
                ),
                importance=Importance(jev[_key(e.content)]["importance"]),
                confidence=1,
                source_ids=[e.id],
                created_at=e.timestamp,
                event_time=e.timestamp,
            )
            for e in events
        ]
        exact = [m for m in memories if m.retention == RetentionPolicy.EXACT]
        pinned = [
            m
            for m in memories
            if m.retention in (RetentionPolicy.EXACT, RetentionPolicy.HIGH_FIDELITY)
        ]
        exact_text = projector.renderer.render(exact)
        fallback = projector.renderer.render(pinned)
        b = record["budget"]
        audit.append(
            {
                "config": cfg.label,
                "budget": b,
                "exact_tokens": count_tokens(exact_text),
                "exact_chars": len(exact_text),
                "pinned_tokens": count_tokens(fallback),
                "pinned_chars": len(fallback),
                "exact_count": len(exact),
                "procedure_count": len(pinned) - len(exact),
                "unsafe_by_exact_tokens": count_tokens(exact_text) > b,
                "fallback_equals_record_raw_chars": len(fallback) == record["raw_chars"],
                "raw_chars": record["raw_chars"],
                "scored_chars": len(record["output_text"]),
            }
        )
    disagreements = []
    for text in sorted(lines):
        gt, pred = cascade[_key(text)], jev[_key(text)]
        if gt["type"] != gt_name(pred["type"]):
            disagreements.append(
                {
                    "text": text,
                    "cascade": gt["type"],
                    "jev": gt_name(pred["type"]),
                    "stage": gt["decided_by"],
                }
            )
    groups: dict[str, list[dict]] = {}
    for row in disagreements:
        groups.setdefault(f"{row['cascade']}->{row['jev']}", []).append(row)
    samples = {key: rows[:5] for key, rows in sorted(groups.items(), key=lambda kv: -len(kv[1]))}
    return {
        "distinct_lines": total,
        "agreement": round(agreement, 4),
        "cohen_kappa": round((agreement - chance) / (1 - chance), 4),
        "per_type": scores,
        "confusion": {g: {p: confusion[(g, p)] for p in types} for g in types},
        "by_cascade_stage": {
            stage: {
                "n": sum(table.values()),
                "agreement": round(sum(table[(t, t)] for t in types) / sum(table.values()), 4),
            }
            for stage, table in by_stage.items()
        },
        "disagreement_samples": samples,
        "budget_audit": {
            "n": len(audit),
            "exact_exceeds_budget": sum(r["unsafe_by_exact_tokens"] for r in audit),
            "fallback_matches_raw_chars": sum(r["fallback_equals_record_raw_chars"] for r in audit),
            "median_exact_tokens_to_budget": round(
                statistics.median(r["exact_tokens"] / r["budget"] for r in audit), 3
            ),
            "median_pinned_tokens_to_budget": round(
                statistics.median(r["pinned_tokens"] / r["budget"] for r in audit), 3
            ),
            "median_fallback_chars_to_budget": round(
                statistics.median(r["pinned_chars"] / (4 * r["budget"]) for r in audit), 3
            ),
            "cases": audit,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/aac/sample")
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--cascade", default="results/kt-faithful/cascade-labels.jsonl")
    parser.add_argument("--jev", default="results/kt-benchmark-full/jev-labels.jsonl")
    parser.add_argument("--benchmark", default="results/kt-benchmark-full")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    configs = load_configs(args.data_dir, n_configs=args.n, seed=args.seed)
    jev_path, root = Path(args.jev), Path(args.benchmark)
    usage = asyncio.run(collect(configs, jev_path, workers=args.workers))
    output = analyze(configs, Path(args.cascade), jev_path, root)
    output["labeling_usage_this_invocation"] = usage
    output["created_at_utc"] = datetime.now(UTC).isoformat()
    (root / "diagnostics.json").write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(
        f"Jev calls {usage['new_calls']}, estimated ${usage['estimated_usd']}; "
        f"agreement {output['agreement']}; audit -> {root / 'diagnostics.json'}"
    )


if __name__ == "__main__":
    main()
