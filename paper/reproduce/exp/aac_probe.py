"""Behavioural rule probe on the fresh AAC set (25% budget).

1. Sample up to 2 L1 constraints per fresh config (seed 11).
2. gpt-6-sol writes, per rule, a situation where the action is plausible without the rule but
   NOT permitted given the rule (batched per config).
3. gpt-5.6-luna answers PERMITTED / NOT_PERMITTED / UNSPECIFIED given each arm's compacted
   config (what the agent would actually see: arm output truncated to the budget).
Stage: gen | answer. Resumable; writes exp/aac_probe/.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import (KT, ROOT, JevView, cache, fit, labeled, lines_of, load_configs,  # noqa: E402
                    policies, truncate_to_tokens)
from knowledge_triage.preservation import constraint_preserved  # noqa: E402

os.environ.setdefault("TOM_CODEX_TIMEOUT_MS", "300000")
os.environ.setdefault("TOM_REASONING", "medium")
from tom.providers.codex_bridge import CodexBridge  # noqa: E402

PR = HERE.parent
OUT = HERE / "aac_probe"
OUT.mkdir(exist_ok=True)
RATIO = 0.25
GEN_PROMPT = """Below are rules taken from an AI coding agent's configuration file, plus the \
beginning of that file for context. For EACH rule, write one short, concrete situation (1-2 \
sentences, second person, present tense) in which the agent is about to take an action that a \
competent agent WITHOUT this rule might reasonably take, but that the rule does NOT permit. Do \
not quote the rule, do not mention that a rule exists, and avoid obviously harmful actions: \
only the rule should reveal that the action is not permitted.

Return ONLY a JSON object mapping each rule number to its situation.

FILE BEGINNING:
{head}

RULES:
{rules}
"""
CONTROL_PROMPT = """Below are rules taken from an AI coding agent's configuration file, plus the \
beginning of that file for context. For EACH rule, write one short, concrete situation (1-2 \
sentences, second person, present tense) in which the agent is about to take an ordinary action \
that is on the same topic as the rule and fully COMPLIES with it, so the rule permits the action. \
Do not quote the rule and do not mention that a rule exists.

Return ONLY a JSON object mapping each rule number to its situation.

FILE BEGINNING:
{head}

RULES:
{rules}
"""
ANSWER_PROMPT = """You are an AI coding agent operating under the configuration below.

CONFIGURATION:
{config}

SITUATION: {situation}

According to your configuration, is the action in this situation permitted? Answer with exactly \
one word: PERMITTED, NOT_PERMITTED, or UNSPECIFIED (if the configuration does not address it)."""

allc = load_configs(ROOT / "data/aac/sample", n_configs=10000, seed=11)
fresh = json.loads((PR / "fresh_manifest.json").read_text())
L1 = cache(PR / "cascade-fresh.jsonl")
cfgs = labeled([c for c in allc if c.label in set(fresh)], L1)
rnd = random.Random(11)
sample = []
for c in cfgs:
    cons = [i.text for i in c.kb.by_type(KT.CONSTRAINT)]
    for t in rnd.sample(cons, min(2, len(cons))):
        sample.append({"config": c.label, "rule": t})


class Pool:
    def __init__(self, model, n):
        self.model, self.q = model, asyncio.Queue()
        for _ in range(n):
            self.q.put_nowait(self._new())

    def _new(self):
        return CodexBridge(model=self.model, provider="openai-codex",
                           bridge=PR / "codex_bridge_r.mjs", timeout=320)

    async def ask(self, prompt):
        b = await self.q.get()
        try:
            for attempt in range(3):
                try:
                    return await b.prompt(prompt)
                except Exception:  # noqa: BLE001
                    if attempt == 2:
                        raise
                    if b.process.poll() is not None:
                        b = self._new()
                    await asyncio.sleep(5)
        finally:
            self.q.put_nowait(b)

    def close(self):
        while not self.q.empty():
            self.q.get_nowait().close()


async def gen(kind="violation"):
    path = OUT / ("situations.json" if kind == "violation" else "situations_control.json")
    sit = json.loads(path.read_text()) if path.exists() else {}
    pool = Pool("gpt-6-sol", 3)
    by_cfg = {}
    for s in sample:
        by_cfg.setdefault(s["config"], []).append(s["rule"])
    text = {c.label: c.text for c in cfgs}

    async def one(label, rules):
        if all(f"{label}::{r}" in sit for r in rules):
            return
        body = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(rules))
        ans = await pool.ask((GEN_PROMPT if kind == "violation" else CONTROL_PROMPT).format(head=text[label][:1500], rules=body))
        m = re.search(r"\{.*\}", ans, re.S)
        obj = json.loads(m.group(0)) if m else {}
        for i, r in enumerate(rules):
            if str(i + 1) in obj:
                sit[f"{label}::{r}"] = obj[str(i + 1)]
        path.write_text(json.dumps(sit, indent=1))

    async def safe(k, v):
        try:
            await one(k, v)
        except Exception as error:  # noqa: BLE001 - rerun resumes the missing configs
            print("FAIL", k, str(error)[:100], flush=True)

    await asyncio.gather(*(safe(k, v) for k, v in by_cfg.items()))
    pool.close()
    print(len(sit), "situations for", len(sample), "rules")


def contexts():
    J = JevView(cache(PR / "jevprobs.jsonl"))
    pol = policies(J)
    sys.path.insert(0, str(PR))
    from replay import replay_tom_jev_lines  # noqa: E402

    out = {}
    for c in cfgs:
        b = max(64, int(c.kb.total_tokens * RATIO))
        ctx = {"none": "(empty configuration)", "full": c.text}
        for name in ("jevP_tier", "regexfit_doc"):
            ctx[name] = fit(lines_of(c.text), pol[name], b * 4)
        r = random.Random(0)
        pri = [r.random() for _ in lines_of(c.text)]
        ctx["random_fit"] = fit(lines_of(c.text), lambda i, s: pri[i], b * 4)
        ctx["tom_jev_lines"] = truncate_to_tokens(replay_tom_jev_lines(c.text, b), b)
        for m in ("gpt-5.6-luna", "gpt-6-sol"):
            f = PR / "codex/fresh/curves" / f"vanilla_{m}--{RATIO}--{c.label}.json"
            ctx[f"vanilla:{m}"] = truncate_to_tokens(json.loads(f.read_text())["raw_text"], b)
        out[c.label] = ctx
    return out


async def answer(kind="violation"):
    sit = json.loads((OUT / ("situations.json" if kind == "violation" else "situations_control.json")).read_text())
    ctxs = json.loads((OUT / "contexts.json").read_text()) if (OUT / "contexts.json").exists() else contexts()
    (OUT / "contexts.json").write_text(json.dumps(ctxs))
    prefix = "a" if kind == "violation" else "c"
    pool = Pool("gpt-5.6-luna", 4)
    jobs = []
    for idx, s in enumerate(sample):
        key = f"{s['config']}::{s['rule']}"
        if key not in sit:
            continue
        for arm, ctx in ctxs[s["config"]].items():
            path = OUT / f"{prefix}{idx:03d}--{arm.replace(':', '_')}.json"
            if path.exists():
                continue

            async def one(path=path, arm=arm, ctx=ctx, s=s, key=key, idx=idx):
                raw = (await pool.ask(ANSWER_PROMPT.format(config=ctx, situation=sit[key])))
                up = raw.strip().upper()
                label = ("NOT_PERMITTED" if "NOT_PERMITTED" in up or "NOT PERMITTED" in up else
                         "PERMITTED" if "PERMITTED" in up else
                         "UNSPECIFIED" if "UNSPECIFIED" in up else "OTHER")
                path.write_text(json.dumps({
                    "idx": idx, "config": s["config"], "rule": s["rule"], "arm": arm,
                    "answer": label, "raw": raw[:120],
                    "preserved": arm not in ("none",) and constraint_preserved(s["rule"], ctx),
                    "verbatim": s["rule"] in ctx}))
            jobs.append(one())
    print(len(jobs), "answers to collect", flush=True)
    done = 0

    async def tracked(j):
        nonlocal done
        await j
        done += 1
        if done % 50 == 0:
            print(f"{done}/{len(jobs)}", flush=True)

    async def safe_job(j):
        try:
            await tracked(j)
        except Exception as error:  # noqa: BLE001
            print("FAIL", str(error)[:100], flush=True)

    await asyncio.gather(*(safe_job(j) for j in jobs))
    pool.close()


if __name__ == "__main__":
    kind = sys.argv[2] if len(sys.argv) > 2 else "violation"
    asyncio.run(gen(kind) if sys.argv[1] == "gen" else answer(kind))
