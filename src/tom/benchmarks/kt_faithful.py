"""Knowledge Triage compaction protocol (Tables 6/7 of the paper) with metered, resumable arms.

Protocol copied from ``experiments/compression_curves.py`` and
``experiments/multiturn_stability.py`` of cikm26-knowledge-triage: same vanilla prompt,
budget = max(64, len(kb) // 4 * ratio), output truncated to budget * 4 characters before
scoring, C-recall against the ORIGINAL constraints. Labels come from ``kt_cascade``.
Every arm receives the raw config text and never sees a label: the cascade labels are used
only to score, so arms that need labels (TypeCompact) are deliberately not part of this module.
Vanilla LLM arms get a 16k completion cap because gpt-5.6/6 reasoning tokens count against it
and a tight cap returns empty output.
"""

from __future__ import annotations

import asyncio
import json
import math
import random
import statistics
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from knowledge_triage.classifier import KnowledgeType as KTType
from knowledge_triage.kb import KnowledgeBase as KTKnowledgeBase
from knowledge_triage.operators import aggressive_prune, hierarchical_summarize, temporal_window

from tom.context import ContextProjector, ProjectionPolicy, Renderer
from tom.context.budget import UnsafeContextBudget
from tom.observer import JevLineObserver, JevRelabeler, TypedObserver
from tom.providers import JevClassifier, OpenAIStructuredLLM

from .knowledge_triage_repro import (
    VANILLA_PROMPT,
    AACConfig,
    TypedTOMCompactor,
    _c_recall,
    _events_from_text,
    per_type_preservation,
    truncate_to_tokens,
)
from .kt_cascade import CostCapExceeded, Meter

JEV_PER_MILLION = 0.042
Compactor = Callable[[str, int], Awaitable[tuple[str, float]]]


def vanilla_compactor(client: Any, model: str, meter: Meter) -> Compactor:
    async def compact(text: str, budget: int) -> tuple[str, float]:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": VANILLA_PROMPT.format(
                        target_tokens=budget, config_text=text[:30_000]
                    ),
                }
            ],
            max_completion_tokens=16_000,
        )
        usage = response.usage
        before = meter.spent
        meter.charge(model, usage.prompt_tokens, usage.completion_tokens)
        return response.choices[0].message.content or "", meter.spent - before

    return compact


def tom_compactor(
    client: Any,
    model: str | None,
    meter: Meter,
    *,
    jev: bool,
    budgeted: bool = False,
    lines: bool = False,
) -> Compactor:
    policy = ProjectionPolicy.STANDARD if budgeted else ProjectionPolicy.PAPER
    projector = ContextProjector(Renderer(compact=True), policy=policy)

    async def compact(text: str, budget: int) -> tuple[str, float]:
        classifier = JevClassifier() if jev else None
        try:
            if lines:
                assert classifier is not None
                observer = JevLineObserver(classifier)
            else:
                assert model is not None
                observer = TypedObserver(
                    OpenAIStructuredLLM(client, model=model),
                    relabeler=JevRelabeler(classifier) if classifier is not None else None,
                )
            memory = TypedTOMCompactor(observer, projector)
            await memory.ingest("kt", _events_from_text(text))
            await memory.compact("kt", budget)
            try:
                output = await memory.context("kt", "", budget)
            except UnsafeContextBudget:
                output = memory.unsafe_protected_text("kt")
            metrics = memory._impl.last_metrics
        finally:
            if classifier is not None:
                await classifier.aclose()
        before = meter.spent
        if model is not None:
            meter.charge(model, metrics.observer_input_tokens, metrics.observer_output_tokens)
        meter.spent += metrics.jev_input_tokens * JEV_PER_MILLION / 1e6
        return output, meter.spent - before

    return compact


def structural_compactor(select: Callable[[KTKnowledgeBase, int], KTKnowledgeBase]) -> Compactor:
    async def compact(text: str, budget: int) -> tuple[str, float]:
        kb = KTKnowledgeBase.from_lines(text.splitlines())
        return "\n".join(item.text for item in select(kb, budget).items), 0.0

    return compact


STRUCTURAL = {
    "hierarchical_truncation": hierarchical_summarize,
    "temporal_window": temporal_window,
    "aggressive_pruning": aggressive_prune,
}


def _write(root: Path, name: str, record: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}.json").write_text(json.dumps(record), encoding="utf-8")


def _load(root: Path, name: str) -> dict[str, Any] | None:
    path = root / f"{name}.json"
    if not path.exists():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    return None if "error" in record else record


async def _guarded(
    meter: Meter, reserve: float, make: Callable[[], Awaitable[tuple[str, float]]]
) -> tuple[str, float, float]:
    """Run ``make`` with up to 3 attempts; return (text, cost, latency of the successful attempt)."""
    for attempt in range(3):
        if meter.spent >= meter.cap_usd - reserve:
            raise CostCapExceeded(f"spent ${meter.spent:.4f} near cap ${meter.cap_usd:.2f}")
        started = time.perf_counter()
        try:
            text, cost = await make()
        except CostCapExceeded:
            raise
        except Exception:
            if attempt == 2:
                raise
            await asyncio.sleep(3 * (attempt + 1))
            continue
        return text, cost, time.perf_counter() - started
    raise AssertionError("unreachable")


async def run_curves(
    configs: list[AACConfig],
    root: Path,
    arms: dict[str, Compactor],
    meter: Meter,
    *,
    ratios: tuple[float, ...],
    workers: int = 8,
) -> None:
    """Single-shot compaction at each ratio (paper Table 6 / compression_curves.py)."""
    semaphore = asyncio.Semaphore(workers)

    async def one(arm: str, compact: Compactor, ratio: float, config: AACConfig) -> None:
        name = f"{arm}--{ratio}--{config.label}"
        if _load(root, name) is not None:
            return
        budget = max(64, int(config.kb.total_tokens * ratio))
        async with semaphore:
            try:
                text, cost, latency = await _guarded(
                    meter, 0.05, lambda: compact(config.text, budget)
                )
            except CostCapExceeded:
                return
            except Exception as error:  # noqa: BLE001 - upstream also skips a failed config
                _write(
                    root,
                    name,
                    {
                        "arm": arm,
                        "config": config.label,
                        "ratio": ratio,
                        "error": f"{type(error).__name__}: {error}"[:300],
                    },
                )
                return
        truncated = truncate_to_tokens(text, budget)
        _write(
            root,
            name,
            {
                "arm": arm,
                "config": config.label,
                "ratio": ratio,
                "budget": budget,
                "raw_chars": len(text),
                "overshoot": len(text) > budget * 4,
                "cost_usd": cost,
                "latency_s": round(latency, 3),
                "per_type": per_type_preservation(config.kb, truncated),
                "output_text": truncated,
            },
        )

    await asyncio.gather(
        *(
            one(arm, compact, ratio, config)
            for ratio in ratios
            for arm, compact in arms.items()
            for config in configs
        )
    )


async def run_stability(
    configs: list[AACConfig],
    root: Path,
    arms: dict[str, Compactor],
    meter: Meter,
    *,
    rounds: int = 5,
    ratio: float = 0.5,
    workers: int = 8,
) -> None:
    """Sequential rounds at ``ratio`` each (paper Figure 3 / multiturn_stability.py)."""
    semaphore = asyncio.Semaphore(workers)

    async def one(arm: str, compact: Compactor, config: AACConfig) -> None:
        original = [item.text for item in config.kb.by_type(KTType.CONSTRAINT)]
        current, budget = config.text, max(64, int(config.kb.total_tokens * ratio))
        for round_number in range(1, rounds + 1):
            name = f"{arm}--round{round_number}--{config.label}"
            saved = _load(root, name)
            if saved is None:
                async with semaphore:
                    try:
                        text, cost, latency = await _guarded(
                            meter,
                            0.05,
                            lambda current=current, budget=budget: compact(current, budget),
                        )
                    except CostCapExceeded:
                        return
                    except Exception as error:  # noqa: BLE001
                        _write(
                            root,
                            name,
                            {
                                "arm": arm,
                                "config": config.label,
                                "round": round_number,
                                "error": str(error)[:300],
                            },
                        )
                        return
                truncated = truncate_to_tokens(text, budget)
                saved = {
                    "arm": arm,
                    "config": config.label,
                    "round": round_number,
                    "budget": budget,
                    "raw_chars": len(text),
                    "overshoot": len(text) > budget * 4,
                    "cost_usd": cost,
                    "latency_s": round(latency, 3),
                    "c_recall": _c_recall(original, truncated),
                    "output_text": truncated,
                }
                _write(root, name, saved)
            if "error" in saved:
                return
            current = saved["output_text"]
            budget = max(64, int(len(current) // 4 * ratio))

    await asyncio.gather(
        *(one(arm, compact, config) for arm, compact in arms.items() for config in configs)
    )


def _records(root: Path, pattern: str) -> list[dict[str, Any]]:
    return [json.loads(p.read_text()) for p in sorted(root.glob(pattern))]


def _valid(record: dict[str, Any]) -> bool:
    return "error" not in record


def _mean(values: Any) -> float:
    values = list(values)
    return round(statistics.mean(values), 4) if values else float("nan")


def summarize(
    configs: list[AACConfig],
    curves_root: Path,
    stability_root: Path,
    *,
    ratios: tuple[float, ...],
    rounds: int = 5,
    exclude: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Per-arm recall by type, overshoot, cost and latency, per ratio and per round."""
    labels = {c.label for c in configs if c.label not in exclude}
    out: dict[str, Any] = {
        "n_configs": len(labels),
        "excluded": sorted(exclude),
        "per_ratio": {},
        "per_strategy": {},
    }
    for r in ratios:
        by_arm: dict[str, list[dict[str, Any]]] = {}
        for record in _records(curves_root, f"*--{r}--*.json"):
            if record["config"] in labels and _valid(record):
                by_arm.setdefault(record["arm"], []).append(record)
        out["per_ratio"][str(r)] = {
            arm: {
                "per_type_mean": {
                    t.value: _mean(
                        x["per_type"][t.value] for x in rs if not math.isnan(x["per_type"][t.value])
                    )
                    for t in KTType
                },
                "n_completed": len(rs),
                "overshoot_rate": _mean(float(x["overshoot"]) for x in rs),
                "median_output_to_budget": round(
                    statistics.median(x["raw_chars"] / (x["budget"] * 4) for x in rs), 3
                ),
                "cost_usd_per_config": _mean(x["cost_usd"] for x in rs),
                "latency_s_mean": _mean(x["latency_s"] for x in rs),
                "latency_s_median": round(statistics.median(x["latency_s"] for x in rs), 3),
            }
            for arm, rs in by_arm.items()
        }

    rounds_by_arm: dict[str, dict[int, list[dict[str, Any]]]] = {}
    for record in _records(stability_root, "*--round*--*.json"):
        if record["config"] in labels and _valid(record):
            rounds_by_arm.setdefault(record["arm"], {}).setdefault(record["round"], []).append(
                record
            )
    for arm, by_round in rounds_by_arm.items():
        complete = {
            label
            for label in labels
            if all(
                any(x["config"] == label for x in by_round.get(k, [])) for k in range(1, rounds + 1)
            )
        }
        flat = [x for rs in by_round.values() for x in rs if x["config"] in complete]
        out["per_strategy"][arm] = {
            **{
                f"round_{k}_c_recall": _mean(
                    x["c_recall"] for x in by_round.get(k, []) if x["config"] in complete
                )
                for k in range(1, rounds + 1)
            },
            "n_completed": len(complete),
            "cost_usd_per_config": _mean(
                sum(x["cost_usd"] for x in flat if x["config"] == label) for label in complete
            ),
            "latency_s_mean_per_round": _mean(x["latency_s"] for x in flat),
        }
    return out


def paired_report(
    curves_root: Path,
    stability_root: Path,
    labels: set[str],
    *,
    ratios: tuple[float, ...],
    rounds: int = 5,
    seed: int = 11,
    draws: int = 10_000,
) -> dict[str, Any]:
    """Paired config-level bootstrap of constraint recall for every TOM arm vs every other arm."""

    def collect(root: Path, pattern: str, key: str, score: Callable[[dict[str, Any]], float]):
        table: dict[tuple[str, str], dict[str, float]] = {}
        for record in _records(root, pattern):
            if record["config"] in labels and _valid(record) and not math.isnan(score(record)):
                table.setdefault((record["arm"], str(record[key])), {})[record["config"]] = score(
                    record
                )
        return table

    def diff(table: dict[tuple[str, str], dict[str, float]], a: str, b: str, k: str):
        left, right = table.get((a, k), {}), table.get((b, k), {})
        common = sorted(set(left) & set(right))
        if len(common) < 5:
            return None
        deltas = [left[c] - right[c] for c in common]
        rng = random.Random(seed)
        means = sorted(statistics.mean(rng.choices(deltas, k=len(deltas))) for _ in range(draws))
        return {
            "n": len(common),
            "mean_diff": round(statistics.mean(deltas), 4),
            "ci95": [round(means[int(draws * 0.025)], 4), round(means[int(draws * 0.975)], 4)],
        }

    curve = collect(curves_root, "*.json", "ratio", lambda r: r["per_type"]["constraint"])
    stable = collect(stability_root, "*.json", "round", lambda r: r["c_recall"])
    arms = sorted({a for a, _ in curve} | {a for a, _ in stable})
    tom_arms = [a for a in arms if a.startswith("tom")]
    report: dict[str, Any] = {}
    for a in tom_arms:
        for b in arms:
            if a == b:
                continue
            entry: dict[str, Any] = {}
            for r in ratios:
                entry[f"ratio_{r}"] = diff(curve, a, b, str(r))
            for k in (1, rounds):
                entry[f"round_{k}"] = diff(stable, a, b, str(k))
            report[f"{a} - {b}"] = entry
    return report


def _arms(client: Any, meter: Meter, names: list[str]) -> dict[str, Compactor]:
    arms: dict[str, Compactor] = {}
    for name in names:
        kind, _, model = name.partition(":")
        if kind in STRUCTURAL:
            arms[name] = structural_compactor(STRUCTURAL[kind])
        elif kind == "vanilla":
            arms[name] = vanilla_compactor(client, model, meter)
        elif kind in ("tom_budget", "tom_jev_budget"):
            arms[name] = tom_compactor(client, model, meter, jev="jev" in kind, budgeted=True)
        elif kind == "tom_jev_lines":
            arms[name] = tom_compactor(client, None, meter, jev=True, budgeted=True, lines=True)
        else:
            raise ValueError(f"unknown arm {name}")
    return arms


def main() -> None:
    import argparse
    import datetime
    import subprocess

    from openai import AsyncOpenAI, OpenAI

    from .knowledge_triage_repro import load_configs
    from .kt_cascade import PRICES, cascade_relabel

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/aac/sample")
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--labels", required=True, help="cascade label cache (jsonl)")
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--arms",
        required=True,
        help="comma list, e.g. vanilla:gpt-5.4-mini,tom_jev_budget:gpt-6-luna,tom_jev_lines,"
        "hierarchical_truncation",
    )
    parser.add_argument("--phase", choices=("curves", "stability", "both"), default="both")
    parser.add_argument("--ratios", default="0.5,0.25,0.1")
    parser.add_argument(
        "--heldout-from",
        type=int,
        default=20,
        help="configs before this index are the development set",
    )
    parser.add_argument("--max-cost-usd", type=float, required=True, help="runaway guard")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    ratios = tuple(float(r) for r in args.ratios.split(","))
    configs, label_stats = cascade_relabel(
        load_configs(args.data_dir, n_configs=args.n, seed=args.seed),
        Path(args.labels),
        OpenAI(),
        cap_usd=5.0,
    )
    root, meter = Path(args.output), Meter(args.max_cost_usd)
    root.mkdir(parents=True, exist_ok=True)
    arms = _arms(AsyncOpenAI(), meter, args.arms.split(","))
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "started_utc": datetime.datetime.now(datetime.UTC).isoformat(),
                "git_sha": subprocess.run(
                    ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
                ).stdout.strip(),
                "args": vars(args),
                "arms": list(arms),
                "configs": [c.label for c in configs],
                "prices_usd_per_million": {k: list(v) for k, v in PRICES.items()},
                "jev_usd_per_million_input": JEV_PER_MILLION,
                "label_stages": label_stats.by_stage,
                "notes": "cascade labels (regex->text-embedding-3-large->gpt-5.4-mini) score only;"
                " arms see raw text; outputs truncated to budget*4 chars before scoring",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    async def go() -> None:
        if args.phase in ("curves", "both"):
            await run_curves(
                configs, root / "curves", arms, meter, ratios=ratios, workers=args.workers
            )
        if args.phase in ("stability", "both"):
            await run_stability(configs, root / "stability", arms, meter, workers=args.workers)

    asyncio.run(go())
    development = frozenset(c.label for c in configs[: args.heldout_from])
    for name, exclude in (("summary.json", frozenset()), ("summary_heldout.json", development)):
        summary = summarize(
            configs, root / "curves", root / "stability", ratios=ratios, exclude=exclude
        )
        (root / name).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    everything = {c.label for c in configs}
    (root / "paired.json").write_text(
        json.dumps(
            paired_report(root / "curves", root / "stability", everything, ratios=ratios),
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"spent this invocation ${meter.spent:.4f}; results in {root}")


if __name__ == "__main__":
    main()
