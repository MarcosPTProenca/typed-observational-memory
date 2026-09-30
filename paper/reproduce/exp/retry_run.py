"""LLM compaction with length feedback: up to 2 retries for outputs over the 4B-char budget.

Starts from the saved first attempt (codex/fresh/curves), so attempt 0 is identical to Table A.
Usage: retry_run.py <model> ; writes exp/retry/<model>--<ratio>--<config>.json
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PR = HERE.parent
sys.path.insert(0, str(PR))
from common import RATIOS, ROOT, cache, labeled, load_configs, score  # noqa: E402

os.environ.setdefault("TOM_CODEX_TIMEOUT_MS", "300000")
os.environ.setdefault("TOM_REASONING", "medium")
from tom.benchmarks.knowledge_triage_repro import VANILLA_PROMPT  # noqa: E402
from tom.providers.codex_bridge import CodexBridge  # noqa: E402

FEEDBACK = """{original}

YOUR PREVIOUS OUTPUT (attempt {n}) WAS TOO LONG: {chars} characters, about {tokens} tokens. \
The hard limit is {limit} characters (about {budget} tokens). Rewrite it so that it fits the \
limit, still keeping every safety rule and procedural command verbatim where possible. Output \
ONLY the compressed configuration text.

PREVIOUS OUTPUT:
{previous}
"""

model = sys.argv[1]
OUT = HERE / "retry"
OUT.mkdir(exist_ok=True)
allc = load_configs(ROOT / "data/aac/sample", n_configs=10000, seed=11)
fresh = json.loads((PR / "fresh_manifest.json").read_text())
cfgs = labeled([c for c in allc if c.label in set(fresh)], cache(PR / "cascade-fresh.jsonl"))


async def main():
    q: asyncio.Queue = asyncio.Queue()
    for _ in range(3):
        q.put_nowait(CodexBridge(model=model, provider="openai-codex",
                                 bridge=PR / "codex_bridge_r.mjs", timeout=320))

    async def ask(prompt):
        b = await q.get()
        try:
            for attempt in range(3):
                try:
                    return await b.prompt(prompt)
                except Exception:  # noqa: BLE001
                    if attempt == 2:
                        raise
                    if b.process.poll() is not None:
                        b = CodexBridge(model=model, provider="openai-codex",
                                        bridge=PR / "codex_bridge_r.mjs", timeout=320)
                    await asyncio.sleep(5)
        finally:
            q.put_nowait(b)

    async def one(c, r):
        path = OUT / f"{model}--{r}--{c.label}.json"
        if path.exists():
            return
        b = max(64, int(c.kb.total_tokens * r))
        first = json.loads((PR / "codex/fresh/curves" /
                            f"vanilla_{model}--{r}--{c.label}.json").read_text())["raw_text"]
        original = VANILLA_PROMPT.format(target_tokens=b, config_text=c.text[:30_000])
        attempts, text = [first], first
        for n in range(1, 3):
            if len(text) <= 4 * b:
                break
            text = await ask(FEEDBACK.format(original=original, n=n, chars=len(text),
                                             tokens=len(text) // 4, limit=4 * b, budget=b,
                                             previous=text))
            attempts.append(text)
        rec = score(c, text, b) | {"config": c.label, "ratio": r, "attempts": len(attempts),
                                    "attempt_chars": [len(a) for a in attempts],
                                    "raw_text": text}
        path.write_text(json.dumps(rec))

    async def safe(c, r):
        try:
            await one(c, r)
        except Exception as error:  # noqa: BLE001 - keep other configs running; rerun resumes
            print("FAIL", c.label, r, str(error)[:120], flush=True)

    await asyncio.gather(*(safe(c, r) for r in RATIOS for c in cfgs))
    while not q.empty():
        q.get_nowait().close()


asyncio.run(main())
