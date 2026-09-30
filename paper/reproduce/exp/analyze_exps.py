"""Analysis of E2 (SafetyMed), E3 (AAC rule probes), E4 (retry with feedback). Writes exp/exps.json."""

from __future__ import annotations

import json
import statistics as st
import sys
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import holm, paired  # noqa: E402


def mcnemar_exact(a: list[bool], b: list[bool]) -> dict:
    ab = sum(x and not y for x, y in zip(a, b, strict=True))
    ba = sum(y and not x for x, y in zip(a, b, strict=True))
    n = ab + ba
    p = min(1.0, 2 * sum(comb(n, k) for k in range(min(ab, ba) + 1)) / 2 ** n) if n else 1.0
    return {"a_only": ab, "b_only": ba, "p": p}


out: dict = {}

# ---------------- E2 SafetyMed
sm = HERE / "safetymed"
if sm.exists():
    recs = [json.loads(f.read_text()) for f in sm.glob("*--*.json")]
    conds = sorted({r["cond"] for r in recs})
    ids = sorted({r["id"] for r in recs})
    idx = {(r["id"], r["cond"]): r for r in recs}
    table = {}
    for c in conds:
        xs = [idx[i, c] for i in ids if (i, c) in idx]
        ref = [x for x in xs if x["gold"] == "REFUSE"]
        pro = [x for x in xs if x["gold"] == "PROCEED"]
        table[c] = {"n": len(xs), "pass": round(st.mean(x["decision"] == x["gold"] for x in xs), 3),
                    "refuse_recall": round(st.mean(x["decision"] == "REFUSE" for x in ref), 3),
                    "proceed_acc": round(st.mean(x["decision"] == "PROCEED" for x in pro), 3),
                    "ctx_tokens_median": st.median(x["ctx_tokens"] for x in xs),
                    "other": sum(x["decision"] == "OTHER" for x in xs)}
    tests = {}
    for b in [c for c in conds if c != "jevP"]:
        common = [i for i in ids if (i, "jevP") in idx and (i, b) in idx]
        a_ok = [idx[i, "jevP"]["decision"] == idx[i, "jevP"]["gold"] for i in common]
        b_ok = [idx[i, b]["decision"] == idx[i, b]["gold"] for i in common]
        tests[f"jevP vs {b}"] = mcnemar_exact(a_ok, b_ok) | {"n": len(common)}
    adj = holm({k: v["p"] for k, v in tests.items()})
    for k in tests:
        tests[k]["holm_p"] = round(adj[k], 5)
    out["safetymed"] = {"table": table, "mcnemar_pass": tests}

# ---------------- E3 AAC rule probes
ap = HERE / "aac_probe"
if ap.exists() and any(ap.glob("a*.json")):
    recs = [json.loads(f.read_text()) for f in ap.glob("a*--*.json")]
    arms = sorted({r["arm"] for r in recs})
    items = sorted({r["idx"] for r in recs})
    idx = {(r["idx"], r["arm"]): r for r in recs}
    full = [i for i in items if all((i, a) in idx for a in arms)]
    table = {}
    for a in arms:
        xs = [idx[i, a] for i in full]
        table[a] = {"n": len(xs),
                    "not_permitted": round(st.mean(x["answer"] == "NOT_PERMITTED" for x in xs), 3),
                    "unspecified": round(st.mean(x["answer"] == "UNSPECIFIED" for x in xs), 3),
                    "permitted": round(st.mean(x["answer"] == "PERMITTED" for x in xs), 3),
                    "key_token_preserved": round(st.mean(x["preserved"] for x in xs), 3),
                    "verbatim": round(st.mean(x["verbatim"] for x in xs), 3)}
    # items where the full configuration makes the model answer correctly = rule-dependent probes
    valid_items = [i for i in full if idx[i, "full"]["answer"] == "NOT_PERMITTED"]
    table_cond = {a: round(st.mean(idx[i, a]["answer"] == "NOT_PERMITTED" for i in valid_items), 3)
                  for a in arms}
    tests = {}
    for b in [a for a in arms if a != "jevP_tier"]:
        tests[f"jevP_tier vs {b}"] = mcnemar_exact(
            [idx[i, "jevP_tier"]["answer"] == "NOT_PERMITTED" for i in full],
            [idx[i, b]["answer"] == "NOT_PERMITTED" for i in full]) | {"n": len(full)}
    adj = holm({k: v["p"] for k, v in tests.items()})
    for k in tests:
        tests[k]["holm_p"] = round(adj[k], 5)
    # metric validity: does key-token preservation predict rule-consistent behaviour?
    comp = [idx[i, a] for i in full for a in arms if a not in ("none", "full")]
    kept = [x for x in comp if x["preserved"]]
    lost = [x for x in comp if not x["preserved"]]
    validity = {"n_kept": len(kept), "n_lost": len(lost),
                "correct_if_kept": round(st.mean(x["answer"] == "NOT_PERMITTED" for x in kept), 3)
                if kept else None,
                "correct_if_lost": round(st.mean(x["answer"] == "NOT_PERMITTED" for x in lost), 3)
                if lost else None,
                "unspecified_if_lost": round(st.mean(x["answer"] == "UNSPECIFIED" for x in lost), 3)
                if lost else None}
    control = {}
    crecs = [json.loads(f.read_text()) for f in ap.glob("c*--*.json")]
    if crecs:
        cidx = {(r["idx"], r["arm"]): r for r in crecs}
        cfull = [i for i in full if all((i, a) in cidx for a in arms)]
        for a in arms:
            fr = st.mean(cidx[i, a]["answer"] == "NOT_PERMITTED" for i in cfull)
            tpr = st.mean(idx[i, a]["answer"] == "NOT_PERMITTED" for i in cfull)
            control[a] = {"n": len(cfull), "false_refusal": round(fr, 3),
                          "violation_detect": round(tpr, 3),
                          "balanced_acc": round((tpr + 1 - fr) / 2, 3)}
        ctests = {}
        for b in [a for a in arms if a != "jevP_tier"]:
            ok = lambda a, i: (idx[i, a]["answer"] == "NOT_PERMITTED") + (  # noqa: E731
                cidx[i, a]["answer"] != "NOT_PERMITTED")
            ctests[f"jevP_tier vs {b}"] = paired([ok("jevP_tier", i) / 2 for i in cfull],
                                                  [ok(b, i) / 2 for i in cfull])
        cadj = holm({k: v["p"] for k, v in ctests.items()})
        for k in ctests:
            ctests[k]["holm_p"] = round(cadj[k], 6)
        control = {"per_arm": control, "balanced_tests": ctests}
    out["aac_probe"] = {"n_items": len(full), "n_rule_dependent": len(valid_items),
                        "control": control,
                        "table": table, "correct_on_rule_dependent": table_cond,
                        "mcnemar": tests, "metric_validity": validity}

# ---------------- E4 retry with feedback
rt = HERE / "retry"
if rt.exists():
    recs = [json.loads(f.read_text()) | {"model": f.name.split("--")[0]} for f in rt.glob("*.json")]
    final_rows = json.loads((HERE.parent / "final_rows.json").read_text())
    jev = {(x["ratio"], x["config"]): x for x in final_rows
           if x["set"] == "fresh" and x["labels"] == "L1" and x["arm"] == "jevP_tier"}
    res = {}
    for model in sorted({x["model"] for x in recs}):
        for r in (0.5, 0.25, 0.1):
            xs = [x for x in recs if x["model"] == model and x["ratio"] == r]
            if not xs:
                continue
            strict = [x["per_type"]["constraint"] if not x["overshoot"] else 0.0 for x in xs]
            j = [jev[r, x["config"]]["C"] for x in xs]
            res[f"{model}@{r}"] = {
                "n": len(xs), "valid": sum(not x["overshoot"] for x in xs),
                "C_trunc": round(st.mean(x["per_type"]["constraint"] for x in xs), 3),
                "C_strict": round(st.mean(strict), 3),
                "mean_attempts": round(st.mean(x["attempts"] for x in xs), 2),
                "jevP_minus_retry_strict": paired(j, strict)}
    out["retry"] = res

(HERE / "exps.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1)[:6000])
