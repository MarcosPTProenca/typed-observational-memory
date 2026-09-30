"""Unsafe signal, calibration and unit sensitivity (no API). Writes exp/offline_extra.json."""

from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PR = HERE.parent
sys.path.insert(0, str(PR))
from common import (KT, RATIOS, ROOT, JevView, _key, cache, fit, labeled, lines_of,  # noqa: E402
                    load_configs, policies)
from knowledge_triage.preservation import constraint_preserved  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from tom.observer.tokenizer import count_tokens  # noqa: E402

Jc = cache(PR / "jevprobs.jsonl")
J = JevView(Jc)
POL = policies(J)
L1 = cache(ROOT / "results/kt-faithful/cascade-labels.jsonl") | cache(PR / "cascade-fresh.jsonl")
L2 = cache(PR / "l2-labels.jsonl")
allc = load_configs(ROOT / "data/aac/sample", n_configs=10000, seed=11)
fresh = set(json.loads((PR / "fresh_manifest.json").read_text()))
cfgs = labeled([c for c in allc if c.label in fresh], L1)
out: dict = {}

# ---- 1. unsafe signal: excluded P(constraint) mass vs actually lost reference constraints
rows = []
for c in cfgs:
    lines = lines_of(c.text)
    for r in RATIOS:
        b = max(64, int(c.kb.total_tokens * r))
        kept = set(fit(lines, POL["jevP_tier"], b * 4).split("\n"))
        dropped_mass = sum(J.pc(s) for s in lines if s not in kept)
        cons = [i.text for i in c.kb.by_type(KT.CONSTRAINT)]
        text = "\n".join(kept)
        lost = sum(not constraint_preserved(t, text) for t in cons)
        rows.append({"config": c.label, "ratio": r, "dropped_mass": dropped_mass,
                     "lost": lost, "n_cons": len(cons), "recall": 1 - lost / len(cons)})
rho = spearmanr([x["dropped_mass"] for x in rows], [x["lost"] for x in rows])
curve = []
for tau in (0.5, 1, 2, 3, 5, 8, 12, 1e9):
    acc = [x for x in rows if x["dropped_mass"] <= tau]
    curve.append({"tau": tau, "coverage": round(len(acc) / len(rows), 3),
                  "recall_answered": round(st.mean(x["recall"] for x in acc), 3) if acc else None,
                  "any_loss_rate_answered": round(st.mean(x["lost"] > 0 for x in acc), 3)
                  if acc else None})
out["unsafe_signal"] = {"n": len(rows), "spearman_rho": round(rho.statistic, 3),
                        "p": float(rho.pvalue), "abstention_curve": curve}

# ---- 2. calibration of P(constraint) against L1 and L2 over all 9,348 lines
texts = sorted(set(json.loads((PR / "lines50.json").read_text())) |
               set(json.loads((PR / "lines_fresh.json").read_text())))
cal = {}
for name, lab in (("L1", L1), ("L2", L2)):
    pairs = [(J.pc(t), lab[_key(t)]["type"] == "constraint") for t in texts if _key(t) in lab]
    bins = []
    for lo in [i / 10 for i in range(10)]:
        xs = [(p, y) for p, y in pairs if lo <= p < lo + 0.1 or (lo == 0.9 and p == 1.0)]
        if xs:
            bins.append({"bin": f"{lo:.1f}-{lo + .1:.1f}", "n": len(xs),
                         "mean_p": round(st.mean(p for p, _ in xs), 3),
                         "frac_pos": round(st.mean(y for _, y in xs), 3)})
    ece = sum(b["n"] * abs(b["mean_p"] - b["frac_pos"]) for b in bins) / len(pairs)
    brier = st.mean((p - y) ** 2 for p, y in pairs)
    # AUROC via rank statistic
    pos = [p for p, y in pairs if y]
    neg = [p for p, y in pairs if not y]
    ranks = sorted([(p, 1) for p in pos] + [(p, 0) for p in neg])
    auc_num, rank_sum, i = 0.0, 0.0, 0
    while i < len(ranks):
        j = i
        while j < len(ranks) and ranks[j][0] == ranks[i][0]:
            j += 1
        avg = (i + j + 1) / 2
        rank_sum += avg * sum(1 for k in range(i, j) if ranks[k][1] == 1)
        i = j
    auc = (rank_sum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))
    cal[name] = {"n": len(pairs), "ece": round(ece, 4), "brier": round(brier, 4),
                 "auroc": round(auc, 4), "base_rate": round(len(pos) / len(pairs), 4),
                 "bins": bins}
out["calibration"] = cal

# ---- 3. validity under other units: real o200k tokens and tolerances (fresh set)
fr = json.loads((PR / "final_rows.json").read_text())
van = {}
for f in (PR / "codex/fresh/curves").glob("*.json"):
    r = json.loads(f.read_text())
    van[r["arm"], r["ratio"], r["config"]] = r["raw_text"]
units = {}
for arm in ("vanilla:gpt-5.6-luna", "vanilla:gpt-6-luna", "vanilla:gpt-6-sol", "jevP_tier",
            "tom_jev_lines"):
    per = {}
    for r in RATIOS:
        xs = [x for x in fr if x["set"] == "fresh" and x["labels"] == "L1" and x["arm"] == arm
              and x["ratio"] == r]
        o200 = []
        for x in xs:
            c = next(k for k in cfgs if k.label == x["config"])
            b = max(64, int(c.kb.total_tokens * r))
            if arm.startswith("vanilla"):
                text = van[arm, r, x["config"]]
            elif arm == "jevP_tier":
                text = fit(lines_of(c.text), POL["jevP_tier"], b * 4)
            else:
                from replay import replay_tom_jev_lines
                text = replay_tom_jev_lines(c.text, b)
            o200.append(count_tokens(text) <= b)
        per[str(r)] = {"n": len(xs), "valid_chars@1.00": sum(x["raw_over_budget"] <= 1 for x in xs),
                       "valid_chars@1.10": sum(x["raw_over_budget"] <= 1.1 for x in xs),
                       "valid_chars@1.25": sum(x["raw_over_budget"] <= 1.25 for x in xs),
                       "valid_o200k_tokens": sum(o200)}
    units[arm] = per
out["units"] = units
(HERE / "offline_extra.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out["unsafe_signal"].items()}, indent=0)[:1500])
for k, v in cal.items():
    print(k, {kk: vv for kk, vv in v.items() if kk != "bins"})
for a, v in units.items():
    print(a, v)
