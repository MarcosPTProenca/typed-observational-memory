"""Run a public dataset: ``PYTHONPATH=src python -m tom.benchmarks.public_cli ...``."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from tom.context import ContextProjector
from tom.metrics import CostRates
from tom.observer import JevRelabeler, TypedObserver
from tom.providers import (
    JevClassifier,
    OpenAIStructuredLLM,
    OpenRouterStructuredLLM,
    PiStructuredLLM,
)

from .compaction_cliff import (
    FullContextMemory,
    KnowledgeTriageMemory,
    ObservationalMemory,
    RecursiveSummaryMemory,
    StructuredSummarizer,
    VanillaCompactionMemory,
)
from .harness import (
    OpenAIAnswerer,
    OpenRouterAnswerer,
    PiAnswerer,
    exact_match,
    file_sha256,
    load_cases,
    run_benchmark_async,
)
from .typed_strategy import TypedTOMMemory, UntypedTOMMemory


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TOM against LongMemEval or LoCoMo")
    parser.add_argument("benchmark", choices=("longmemeval", "locomo"))
    parser.add_argument("dataset", help="path to the downloaded JSON/JSONL dataset")
    parser.add_argument("--output", default="results/public")
    parser.add_argument("--model", default=None)
    parser.add_argument("--answerer", choices=("pi", "openai", "openrouter"), default="pi")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--budget", type=int, default=4096)
    parser.add_argument("--strategies", default="tom,full_context,vanilla_compaction,observational,knowledge_triage")
    parser.add_argument("--manifest", help="pilot manifest JSON containing case_ids")
    parser.add_argument("--resume", action="store_true", help="resume rows already written in output/raw")
    parser.add_argument("--max-calls", type=int, default=None)
    parser.add_argument("--max-cost-usd", type=float, default=None,
                        help="estimated API spend cap (requires a priced model)")
    parser.add_argument("--observation-tokens", type=int, default=2048,
                        help="token budget per observer chunk (fewer chunks = fewer LLM calls)")
    args = parser.parse_args()

    model = args.model
    if args.answerer == "pi":
        llm = PiStructuredLLM(model=model)
    elif args.answerer == "openai":
        llm = OpenAIStructuredLLM(model=model or "gpt-5-mini")
    else:
        llm = OpenRouterStructuredLLM(model=model) if model else OpenRouterStructuredLLM()
    # Conservative Luna input estimate: cache-write tokens can cost $0.125/M.
    rates = CostRates(input_per_million=0.125, output_per_million=0.50) if (
        args.answerer == "openai" and model == "gpt-6-luna"
    ) else None
    if args.max_cost_usd is not None and (args.max_cost_usd <= 0 or rates is None):
        parser.error("--max-cost-usd requires a positive value and priced gpt-6-luna model")
    jev = JevClassifier()
    strategies: dict[str, Any] = {}
    for name in args.strategies.split(","):
        name = name.strip()
        if name == "tom":
            strategies[name] = lambda: TypedTOMMemory(
                TypedObserver(llm, cost_rates=rates), ContextProjector(),
                observation_tokens=args.observation_tokens)
        elif name == "tom_jev":
            strategies[name] = lambda: TypedTOMMemory(
                TypedObserver(llm, cost_rates=rates, relabeler=JevRelabeler(jev)),
                ContextProjector(), observation_tokens=args.observation_tokens)
        elif name == "tom_no_retrieval":
            strategies[name] = lambda: TypedTOMMemory(
                TypedObserver(llm, cost_rates=rates), ContextProjector(),
                observation_tokens=args.observation_tokens, use_retrieval=False)
        elif name == "tom_untyped":
            strategies[name] = lambda: UntypedTOMMemory(
                TypedObserver(llm, cost_rates=rates), ContextProjector(),
                observation_tokens=args.observation_tokens)
        elif name == "recursive_summary":
            strategies[name] = lambda: RecursiveSummaryMemory(StructuredSummarizer(llm))
        else:
            strategies[name] = {
                "full_context": FullContextMemory,
                "vanilla_compaction": VanillaCompactionMemory,
                "observational": ObservationalMemory,
                "knowledge_triage": KnowledgeTriageMemory,
            }[name]

    cases = load_cases(args.dataset, args.benchmark)
    if args.manifest:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        if manifest.get("benchmark") != args.benchmark:
            raise ValueError("manifest benchmark does not match the selected dataset")
        if manifest.get("dataset_hash") and manifest["dataset_hash"] != file_sha256(args.dataset):
            raise ValueError("manifest dataset_hash does not match the dataset")
        allowed = set(manifest["case_ids"])
        cases = [case for case in cases if case.id in allowed]
    if args.limit is not None:
        cases = cases[:args.limit]
    if args.answerer == "pi":
        answerer = PiAnswerer(model=model)
    elif args.answerer == "openai":
        answerer = OpenAIAnswerer(model=model or "gpt-5-mini")
    else:
        answerer = OpenRouterAnswerer(model=model) if model else OpenRouterAnswerer()
    async def run() -> list[dict[str, Any]]:
        try:
            return await run_benchmark_async(
                cases, strategies, answerer, output_dir=args.output,
                budget=args.budget, dataset=args.benchmark, scorer=exact_match,
                dataset_hash=file_sha256(args.dataset),
                resume=args.resume, max_calls=args.max_calls,
                max_cost_usd=args.max_cost_usd, answer_cost_rates=rates,
                run_config={
                    "benchmark": args.benchmark, "budget": args.budget,
                    "answerer": args.answerer, "model": model,
                    "strategies": list(strategies), "harness_version": "stage-5-jev",
                    "observation_tokens": args.observation_tokens,
                    "manifest": args.manifest, "resume": args.resume, "max_calls": args.max_calls,
                    "max_cost_usd": args.max_cost_usd,
                },
            )
        finally:
            await jev.aclose()

    rows = asyncio.run(run())
    print(f"Wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
