"""Shared loaders, selection policies and statistics for the paper review scripts."""

from __future__ import annotations

import json
import math
import random
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_triage.classifier import KnowledgeType as KT  # noqa: E402
from knowledge_triage.classifier import classify_instruction  # noqa: E402
from knowledge_triage.kb import Item, KnowledgeBase  # noqa: E402
from scipy.stats import wilcoxon  # noqa: E402

from tom.benchmarks.knowledge_triage_repro import (  # noqa: E402
    _c_recall,
    load_configs,
    per_type_preservation,
    truncate_to_tokens,
)
from tom.benchmarks.kt_cascade import _key  # noqa: E402

HERE = Path(__file__).resolve().parent
RATIOS = (0.5, 0.25, 0.1)
IMP = {"critical": 0, "high": 1, "medium": 2, "low": 3}
JTIER = {"constraint": 0, "procedure": 1, "belief": 2, "preference": 3, "episodic": 4}
KTIER = {KT.CONSTRAINT: 0, KT.PROCEDURAL: 1, KT.BELIEF: 2, KT.PREFERENCE: 3, KT.EPISODIC: 4}


def cache(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return {r["key"]: r for line in path.read_text().splitlines() if (r := json.loads(line))}


def labeled(configs, labels: dict[str, dict]):
    """Copies of configs whose kb types come from a label cache (type field)."""
    out = []
    for c in configs:
        items = [Item(text=i.text, type=KT(labels[_key(i.text)]["type"])) for i in c.kb.items]
        out.append(type(c)(label=c.label, kb=KnowledgeBase(items=items), text=c.text))
    return out


def lines_of(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def fit(lines: list[str], key, char_budget: int) -> str:
    """Greedy line-level fill of a hard character budget, emitted in document order."""
    chosen, used = [], 0
    for i in sorted(range(len(lines)), key=lambda i: key(i, lines[i])):
        cost = len(lines[i]) + (1 if chosen else 0)
        if used + cost <= char_budget:
            chosen.append(i)
            used += cost
    out = "\n".join(lines[i] for i in sorted(chosen))
    assert len(out) <= char_budget
    return out


def rx_is_c(line: str) -> bool:
    return classify_instruction(line) == KT.CONSTRAINT


def regex_tier(line: str) -> int:
    return KTIER[classify_instruction(line)]


class JevView:
    """Accessors over a Jev probability cache (jev_probs.py output)."""

    def __init__(self, probs: dict[str, dict]):
        self.p = probs

    def row(self, s):
        return self.p.get(_key(s)) or {"type": "belief", "importance": "low",
                                       "p_type": {"constraint": 0.0, "procedure": 0.0},
                                       "binding": 0.0, "p_imp": {"low": 1.0}}

    def pc(self, s):
        return self.row(s)["p_type"].get("constraint", 0.0)

    def pp(self, s):
        return self.row(s)["p_type"].get("procedure", 0.0)

    def tier(self, s):
        return JTIER[self.row(s)["type"]]

    def imp(self, s):
        return IMP[self.row(s)["importance"]]

    def eimp(self, s):  # expected importance rank (0 = critical)
        return sum(IMP[k] * v for k, v in self.row(s)["p_imp"].items())

    def binding(self, s):
        return self.row(s)["binding"]


def policies(j: JevView) -> dict:
    """Pre-specified selection policies. Keys are (doc index, line) -> sort key (asc)."""
    return {
        # label-only (what the paper's cache could already do)
        "jevfit_imp": lambda i, s: (j.tier(s), j.imp(s), i),
        # probability-based variants
        "jevP_tier": lambda i, s: (j.tier(s), -j.pc(s), i),
        "jevP_c": lambda i, s: (-j.pc(s), i),
        "jevP_density": lambda i, s: (-j.pc(s) / max(1, len(s)), i),
        "jevB": lambda i, s: (-j.binding(s), i),
        "jevBP": lambda i, s: (-(j.binding(s) + j.pc(s)) / 2, i),
        "jevBP_tier": lambda i, s: (j.tier(s) if j.tier(s) < 2 else 2,
                                    -(j.binding(s) + j.pc(s)) / 2, i),
        # hybrid with the (label-circular) regex detector
        "hybridP": lambda i, s: (0 if rx_is_c(s) else 1, -(j.binding(s) + j.pc(s)) / 2, i),
        # zero-cost controls
        "regexfit_doc": lambda i, s: (regex_tier(s), i),
    }


def oracle_policy(labels: dict[str, dict]):
    def key(i, s):
        t = labels.get(_key(s), {}).get("type", "belief")
        return ({"constraint": 0, "procedural": 1}.get(t, 2), i)
    return key


def random_scores(config, seeds=range(20)):
    """Mean per-type preservation of seeded random line orders (chance level)."""
    return seeds


def score(cfg, raw: str, budget: int) -> dict:
    trunc = truncate_to_tokens(raw, budget)
    return {"raw_chars": len(raw), "budget": budget, "overshoot": len(raw) > budget * 4,
            "per_type": per_type_preservation(cfg.kb, trunc)}


def rounds(policy_key, cfg, n_rounds=5, ratio=0.5):
    original = [i.text for i in cfg.kb.by_type(KT.CONSTRAINT)]
    current, budget, out = cfg.text, max(64, int(cfg.kb.total_tokens * ratio)), []
    for k in range(1, n_rounds + 1):
        text = fit(lines_of(current), policy_key, budget * 4)
        out.append({"round": k, "c_recall": _c_recall(original, text), "overshoot": False})
        current, budget = text, max(64, int(len(text) // 4 * ratio))
    return out


def boot(deltas, seed=11, draws=10_000):
    rnd = random.Random(seed)
    m = sorted(st.mean(rnd.choices(deltas, k=len(deltas))) for _ in range(draws))
    return [round(m[int(draws * .025)], 4), round(m[int(draws * .975)], 4)]


def paired(xs: list[float], ys: list[float]) -> dict:
    d = [x - y for x, y in zip(xs, ys, strict=True)]
    nz = [x for x in d if x != 0]
    p = float(wilcoxon(nz).pvalue) if len(nz) >= 5 else 1.0
    return {"diff": round(st.mean(d), 4), "ci95": boot(d), "p": p, "n": len(d),
            "wins": sum(x > 0 for x in d), "ties": sum(x == 0 for x in d),
            "losses": sum(x < 0 for x in d)}


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for rank, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - rank) * p))
        out[k] = running
    return out


def nanmean(xs):
    xs = [x for x in xs if not (isinstance(x, float) and math.isnan(x))]
    return st.mean(xs) if xs else float("nan")


__all__ = ["KT", "ROOT", "HERE", "RATIOS", "cache", "labeled", "lines_of", "fit", "JevView",
           "policies", "oracle_policy", "score", "rounds", "boot", "paired", "holm", "nanmean",
           "load_configs", "_key", "_c_recall", "truncate_to_tokens", "rx_is_c", "st"]
