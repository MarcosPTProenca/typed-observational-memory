"""Offline re-analysis of results/kt-benchmark-full + zero-cost new arms.

No API calls: uses the frozen cascade cache, the frozen Jev label cache
(results/kt-benchmark-full/jev-labels.jsonl) and the saved per-config records.
Run: .venv/bin/python temp_docs/paper-review/offline.py
"""

from __future__ import annotations

import json
import math
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_triage.classifier import KnowledgeType as KT  # noqa: E402
from knowledge_triage.classifier import classify_instruction  # noqa: E402
from knowledge_triage.kb import Item, KnowledgeBase  # noqa: E402
from scipy.stats import wilcoxon  # noqa: E402

from tom.benchmarks.knowledge_triage_repro import (  # noqa: E402
    _c_recall,
    _events_from_text,
    load_configs,
    per_type_preservation,
    truncate_to_tokens,
)
from tom.benchmarks.kt_cascade import _key  # noqa: E402
from tom.context import ContextProjector, ProjectionPolicy, Renderer  # noqa: E402
from tom.context.budget import UnsafeContextBudget  # noqa: E402
from tom.models import Importance, KnowledgeType, MemoryItem, RetentionPolicy  # noqa: E402

RUN = ROOT / "results/kt-benchmark-full"
OUT = Path(__file__).resolve().parent
RATIOS = (0.5, 0.25, 0.1)
manifest = json.loads((RUN / "manifest.json").read_text())


def cache(path: Path) -> dict[str, dict]:
    return {r["key"]: r for line in path.read_text().splitlines() if (r := json.loads(line))}


CASCADE = cache(ROOT / "results/kt-faithful/cascade-labels.jsonl")
JEV = cache(RUN / "jev-labels.jsonl")
configs = load_configs(ROOT / "data/aac/sample", n_configs=50, seed=11)
assert [c.label for c in configs] == manifest["configs"]
for c in configs:  # relabel with the frozen cascade cache (no encoder fit, no API)
    c.kb = KnowledgeBase(items=[Item(text=i.text, type=KT(CASCADE[_key(i.text)]["type"]))
                                for i in c.kb.items])
DEV = set(manifest["configs"][:20])
HELD = set(manifest["configs"][20:])
CFG = {c.label: c for c in configs}

# ---------------------------------------------------------------- saved records
saved: dict[tuple[str, float, str], dict] = {}
for f in (RUN / "curves").glob("*.json"):
    r = json.loads(f.read_text())
    if "error" not in r:
        saved[r["arm"], r["ratio"], r["config"]] = r
saved_rounds: dict[tuple[str, int, str], dict] = {}
for f in (RUN / "stability").glob("*.json"):
    r = json.loads(f.read_text())
    if "error" not in r:
        saved_rounds[r["arm"], r["round"], r["config"]] = r

# ---------------------------------------------------------------- line helpers
IMP = {"critical": 0, "high": 1, "medium": 2, "low": 3}
JTIER = {"constraint": 0, "procedure": 1, "belief": 2, "preference": 3, "episodic": 4}
KTIER = {KT.CONSTRAINT: 0, KT.PROCEDURAL: 1, KT.BELIEF: 2, KT.PREFERENCE: 3, KT.EPISODIC: 4}


def lines_of(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def jev(line: str) -> dict:
    return JEV.get(_key(line)) or {"type": "belief", "importance": "low"}


def fit(lines: list[str], key, char_budget: int, *, doc_order: bool = True) -> str:
    """Greedy line-level fill of a hard character budget (valid by construction)."""
    chosen, used = [], 0
    for i in sorted(range(len(lines)), key=lambda i: key(i, lines[i])):
        cost = len(lines[i]) + (1 if chosen else 0)
        if used + cost <= char_budget:
            chosen.append(i)
            used += cost
    if doc_order:
        chosen.sort()
    out = "\n".join(lines[i] for i in chosen)
    assert len(out) <= char_budget
    return out


def grouped_then_truncate(lines: list[str], tier, budget: int) -> str:
    """Type-first rendering followed by the protocol's character truncation."""
    order = sorted(range(len(lines)), key=lambda i: (tier(lines[i]), i))
    return "\n".join(lines[i] for i in order)


def replay_jev_lines(text: str, budget: int) -> str:
    """Re-execute the original LineTOM projector on the cached Jev labels."""
    events = _events_from_text(text)
    mems = []
    for e in events:
        lab = jev(e.content)
        kind = KnowledgeType(lab["type"])
        ret = (RetentionPolicy.EXACT if kind == KnowledgeType.CONSTRAINT else
               RetentionPolicy.HIGH_FIDELITY if kind == KnowledgeType.PROCEDURE else
               RetentionPolicy.COMPRESSIBLE)
        mems.append(MemoryItem(id=e.id, content=e.content, knowledge_type=kind, retention=ret,
                               importance=Importance(lab["importance"]), confidence=1.0,
                               source_ids=[e.id], created_at=e.timestamp, event_time=e.timestamp))
    projector = ContextProjector(Renderer(compact=True), policy=ProjectionPolicy.STANDARD)
    try:
        return projector.project(mems, budget).text
    except UnsafeContextBudget:
        pinned = [m for m in mems if m.retention in (RetentionPolicy.EXACT,
                                                     RetentionPolicy.HIGH_FIDELITY)]
        return projector.renderer.render(pinned)


def regex_tier(line: str) -> int:
    return KTIER[classify_instruction(line)]


def oracle_tier(line: str) -> int:
    return KTIER[KT(CASCADE[_key(line)]["type"])] if _key(line) in CASCADE else 2


def rx_is_c(line: str) -> bool:
    return classify_instruction(line) == KT.CONSTRAINT


# priority keys (i = document index, s = line); lower sorts first
ARMS_FIT = {
    # budget-feasible Jev variants (candidate improvements)
    "jevfit_doc": lambda i, s: (JTIER[jev(s)["type"]], i),
    "jevfit_imp": lambda i, s: (JTIER[jev(s)["type"]], IMP[jev(s)["importance"]], i),
    "jevfit_short": lambda i, s: (JTIER[jev(s)["type"]], len(s), i),
    "jevfit_imp_short": lambda i, s: (JTIER[jev(s)["type"]], IMP[jev(s)["importance"]],
                                      len(s), i),
    # hybrid: regex constraints first, then Jev constraints (imp), then the rest by Jev
    "hybrid_fit": lambda i, s: (0 if rx_is_c(s) else 1 if jev(s)["type"] == "constraint" else 2,
                                JTIER[jev(s)["type"]], IMP[jev(s)["importance"]], i),
    # zero-cost controls
    "regexfit_doc": lambda i, s: (regex_tier(s), i),
    "regexfit_short": lambda i, s: (regex_tier(s), len(s), i),
    # label-aware ceiling (NOT a competitor: reads the evaluation labels)
    "ORACLE_fit": lambda i, s: (oracle_tier(s), i),
    "ORACLE_fit_short": lambda i, s: (oracle_tier(s), len(s), i),
}
RANDOM_SEEDS = range(20)


def run_arm(name: str, text: str, budget: int, seed: int | None = None) -> str:
    lines = lines_of(text)
    if name in ARMS_FIT:
        return fit(lines, ARMS_FIT[name], budget * 4)
    if name == "random_fit":
        rnd = random.Random(seed)
        pri = [rnd.random() for _ in lines]
        return fit(lines, lambda i, s: pri[i], budget * 4)
    if name == "regex_first_trunc":
        return grouped_then_truncate(lines, regex_tier, budget)
    if name == "jev_first_trunc":
        return grouped_then_truncate(lines, lambda s: JTIER[jev(s)["type"]], budget)
    if name == "replay_jev_lines":
        return replay_jev_lines(text, budget)
    raise KeyError(name)


NEW_ARMS = ["replay_jev_lines", "jev_first_trunc", "regex_first_trunc", *ARMS_FIT, "random_fit"]


def score(cfg, raw: str, budget: int) -> dict:
    trunc = truncate_to_tokens(raw, budget)
    pt = per_type_preservation(cfg.kb, trunc)
    return {"raw_chars": len(raw), "budget": budget, "overshoot": len(raw) > budget * 4,
            "per_type": pt, "out_chars": len(trunc)}


# ---------------------------------------------------------------- single-shot curves
new: dict[tuple[str, float, str], dict] = {}
for c in configs:
    for r in RATIOS:
        b = max(64, int(c.kb.total_tokens * r))
        for arm in NEW_ARMS:
            if arm == "random_fit":
                rs = [score(c, run_arm(arm, c.text, b, s), b) for s in RANDOM_SEEDS]
                rec = rs[0] | {"per_type": {t: st.mean(x["per_type"][t] for x in rs)
                                            if not math.isnan(rs[0]["per_type"][t]) else math.nan
                                            for t in rs[0]["per_type"]}}
            else:
                rec = score(c, run_arm(arm, c.text, b), b)
            new[arm, r, c.label] = rec


# ---------------------------------------------------------------- multi-round (fit arms)
def rounds_for(arm: str, cfg, n_rounds=5, ratio=0.5, seed=None):
    original = [i.text for i in cfg.kb.by_type(KT.CONSTRAINT)]
    current, budget, out = cfg.text, max(64, int(cfg.kb.total_tokens * ratio)), []
    for k in range(1, n_rounds + 1):
        raw = run_arm(arm, current, budget, seed)
        trunc = truncate_to_tokens(raw, budget)
        out.append({"round": k, "c_recall": _c_recall(original, trunc),
                    "overshoot": len(raw) > 4 * budget, "budget": budget})
        current, budget = trunc, max(64, int(len(trunc) // 4 * ratio))
    return out


ROUND_ARMS = ["jevfit_doc", "jevfit_imp", "jevfit_short", "hybrid_fit", "regexfit_doc",
              "regexfit_short", "ORACLE_fit", "random_fit"]
new_rounds: dict[tuple[str, int, str], dict] = {}
for c in configs:
    for arm in ROUND_ARMS:
        if arm == "random_fit":
            runs = [rounds_for(arm, c, seed=s) for s in RANDOM_SEEDS]
            for k in range(5):
                new_rounds[arm, k + 1, c.label] = {
                    "c_recall": st.mean(run[k]["c_recall"] for run in runs), "overshoot": False}
        else:
            for row in rounds_for(arm, c):
                new_rounds[arm, row["round"], c.label] = row


# ---------------------------------------------------------------- statistics
def boot(deltas, seed=11, draws=10_000):
    rnd = random.Random(seed)
    m = sorted(st.mean(rnd.choices(deltas, k=len(deltas))) for _ in range(draws))
    return [round(m[int(draws * .025)], 4), round(m[int(draws * .975)], 4)]


def rec(arm, r, cfg):
    return new.get((arm, r, cfg)) or saved[arm, r, cfg]


def cr(x):
    return x["per_type"]["constraint"]


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for rank, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - rank) * p))
        out[k] = running
    return out


def table(subset: set[str]) -> dict:
    arms = list(manifest["arms"]) + NEW_ARMS
    res = {}
    for r in RATIOS:
        res[str(r)] = {}
        for a in arms:
            rows = [rec(a, r, c) for c in sorted(subset)]
            ratio = [x["raw_chars"] / (4 * x["budget"]) for x in rows]
            res[str(r)][a] = {
                "C": round(st.mean(cr(x) for x in rows), 4),
                "C_ci": boot([cr(x) for x in rows]),
                "P": round(st.mean(x["per_type"]["procedural"] for x in rows
                                   if not math.isnan(x["per_type"]["procedural"])), 4),
                "valid@1.00": sum(v <= 1.00 for v in ratio),
                "valid@1.10": sum(v <= 1.10 for v in ratio),
                "valid@1.25": sum(v <= 1.25 for v in ratio),
                "median_raw_over_budget": round(st.median(ratio), 3),
                "strict_C": round(st.mean(0 if x["overshoot"] else cr(x) for x in rows), 4),
                "n": len(rows),
            }
    return res


def rounds_table(subset: set[str]) -> dict:
    arms = sorted({a for a, _, _ in saved_rounds} | set(ROUND_ARMS))
    out = {}
    for a in arms:
        src = new_rounds if a in ROUND_ARMS else saved_rounds
        out[a] = {k: round(st.mean(src[a, k, c]["c_recall"] for c in subset), 4)
                  for k in range(1, 6)}
        out[a]["valid_all_rounds"] = sum(
            all(not src[a, k, c]["overshoot"] for k in range(1, 6)) for c in subset)
    return out


def paired(a, b, r, subset, strict=False):
    f = (lambda x: 0 if x["overshoot"] else cr(x)) if strict else cr
    d = [f(rec(a, r, c)) - f(rec(b, r, c)) for c in sorted(subset)]
    nz = [x for x in d if x != 0]
    p = wilcoxon(nz).pvalue if len(nz) >= 5 else 1.0
    return {"diff": round(st.mean(d), 4), "ci95": boot(d), "wilcoxon_p": float(p), "n": len(d),
            "wins": sum(x > 0 for x in d), "ties": sum(x == 0 for x in d),
            "losses": sum(x < 0 for x in d)}


COMPARISONS = [
    ("tom_jev_lines", "vanilla:gpt-5.6-luna", False),
    ("tom_jev_lines", "regex_first_trunc", False),
    ("tom_jev_lines", "jev_first_trunc", False),
    ("jevfit_imp", "vanilla:gpt-5.6-luna", True),
    ("jevfit_imp", "tom_jev_lines", True),
    ("jevfit_imp", "regexfit_doc", True),
    ("jevfit_doc", "regexfit_doc", True),
    ("hybrid_fit", "regexfit_doc", True),
    ("hybrid_fit", "jevfit_imp", True),
    ("jevfit_short", "regexfit_short", True),
    ("regexfit_doc", "vanilla:gpt-5.6-luna", True),
]


def comparisons(subset):
    res = {f"{a} vs {b} ({'strict' if s else 'trunc'}) @{r}": paired(a, b, r, subset, s)
           for a, b, s in COMPARISONS for r in RATIOS}
    adj = holm({k: v["wilcoxon_p"] for k, v in res.items()})
    for k in res:
        res[k]["holm_p"] = round(adj[k], 5)
        res[k]["wilcoxon_p"] = round(res[k]["wilcoxon_p"], 5)
    return res


# replay fidelity: does the cached-label replay reproduce the measured LineTOM output?
fidelity = {}
for r in RATIOS:
    ratios = [new["replay_jev_lines", r, c]["raw_chars"] / saved["tom_jev_lines", r, c]["raw_chars"]
              for c in HELD]
    same_c = [abs(cr(new["replay_jev_lines", r, c]) - cr(saved["tom_jev_lines", r, c]))
              for c in HELD]
    fidelity[str(r)] = {"median_len_ratio": round(st.median(ratios), 3),
                        "within_5pct": sum(abs(x - 1) <= .05 for x in ratios),
                        "mean_abs_C_diff": round(st.mean(same_c), 4)}

# how much of each ref constraint set is regex-detectable (labeler/method circularity)
circ = {"ref_constraints": 0, "regex_hits": 0, "jev_hits": 0, "union_hits": 0}
for c in configs:
    if c.label not in HELD:
        continue
    for it in c.kb.by_type(KT.CONSTRAINT):
        circ["ref_constraints"] += 1
        circ["regex_hits"] += rx_is_c(it.text)
        circ["jev_hits"] += jev(it.text)["type"] == "constraint"
        circ["union_hits"] += rx_is_c(it.text) or jev(it.text)["type"] == "constraint"
# key-token vacuity: constraints with zero key tokens
from knowledge_triage.preservation import constraint_key_tokens  # noqa: E402

circ["no_key_tokens"] = sum(not constraint_key_tokens(i.text) for c in configs if c.label in HELD
                            for i in c.kb.by_type(KT.CONSTRAINT))

report = {
    "held": table(HELD), "dev": table(DEV), "all": table(HELD | DEV),
    "rounds_held": rounds_table(HELD), "rounds_all": rounds_table(HELD | DEV),
    "comparisons_held": comparisons(HELD), "replay_fidelity_held": fidelity,
    "circularity_held": circ,
}
(OUT / "offline.json").write_text(json.dumps(report, indent=1))
# per-config rows for plotting
rows = []
for (a, r, c), x in list(saved.items()) + list(new.items()):
    rows.append({"arm": a, "ratio": r, "config": c, "held": c in HELD, "C": cr(x),
                 "P": x["per_type"]["procedural"], "raw_over_budget": x["raw_chars"] / (4 * x["budget"]),
                 "overshoot": x["overshoot"]})
(OUT / "rows.json").write_text(json.dumps(rows))

H = report["held"]
print(f"{'arm':30s} " + " ".join(f"{'C@'+str(r):>7s} {'P':>5s} {'v1.0':>4s} {'v1.1':>4s} {'strC':>5s}"
                                   for r in RATIOS))
for a in H["0.5"]:
    print(f"{a:30s} " + " ".join(
        f"{H[str(r)][a]['C']:7.3f} {H[str(r)][a]['P']:5.2f} {H[str(r)][a]['valid@1.00']:4d} "
        f"{H[str(r)][a]['valid@1.10']:4d} {H[str(r)][a]['strict_C']:5.3f}" for r in RATIOS))
print("\nrounds (held):")
for a, v in report["rounds_held"].items():
    print(f"{a:30s}", [v[k] for k in range(1, 6)], "valid5:", v["valid_all_rounds"])
print("\nreplay fidelity:", fidelity)
print("circularity:", circ)
print()
for k, v in report["comparisons_held"].items():
    print(f"{k:62s} d={v['diff']:+.3f} {v['ci95']} W/T/L={v['wins']}/{v['ties']}/{v['losses']} "
          f"holm_p={v['holm_p']}")
