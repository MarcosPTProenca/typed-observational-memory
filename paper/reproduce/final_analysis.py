"""Confirmatory (fresh, pre-registered) + held-out analysis. No API calls.

Writes final.json and per-config rows (final_rows.json) for plotting.
"""

from __future__ import annotations

import json
import math
import random
import statistics as st

from common import (HERE, RATIOS, ROOT, KT, JevView, _c_recall, _key, cache, fit, holm, labeled,
                    lines_of, load_configs, nanmean, oracle_policy, paired, policies, rounds,
                    score, truncate_to_tokens)
from knowledge_triage.kb import Item, KnowledgeBase

from tom.benchmarks.knowledge_triage_repro import _events_from_text, per_type_preservation
from tom.context import ContextProjector, ProjectionPolicy, Renderer
from tom.context.budget import UnsafeContextBudget
from tom.models import Importance, KnowledgeType, MemoryItem, RetentionPolicy

RUN = ROOT / "results/kt-benchmark-full"
manifest = json.loads((RUN / "manifest.json").read_text())
ALL = load_configs(ROOT / "data/aac/sample", n_configs=10000, seed=11)
L1_HELD = cache(ROOT / "results/kt-faithful/cascade-labels.jsonl")
L1_FRESH = cache(HERE / "cascade-fresh.jsonl")
L2 = cache(HERE / "l2-labels.jsonl")
J = JevView(cache(HERE / "jevprobs.jsonl"))
POL = policies(J)
HELD_LABELS = manifest["configs"][20:]
FRESH_LABELS = json.loads((HERE / "fresh_manifest.json").read_text())


def configs_for(names, labels):
    return labeled([c for c in ALL if c.label in set(names)], labels)


def replay_tom_jev_lines(text: str, budget: int) -> str:
    """Paper method (TypedTOMCompactor + JevLineObserver + STANDARD projector) on Jev labels."""
    mems = []
    for e in _events_from_text(text):
        row = J.row(e.content)
        kind = KnowledgeType(row["type"])
        ret = (RetentionPolicy.EXACT if kind == KnowledgeType.CONSTRAINT else
               RetentionPolicy.HIGH_FIDELITY if kind == KnowledgeType.PROCEDURE else
               RetentionPolicy.COMPRESSIBLE)
        mems.append(MemoryItem(id=e.id, content=e.content, knowledge_type=kind, retention=ret,
                               importance=Importance(row["importance"]), confidence=1.0,
                               source_ids=[e.id], created_at=e.timestamp, event_time=e.timestamp))
    projector = ContextProjector(Renderer(compact=True), policy=ProjectionPolicy.STANDARD)
    try:
        return projector.project(mems, budget).text
    except UnsafeContextBudget:
        pinned = [m for m in mems if m.retention in (RetentionPolicy.EXACT,
                                                     RetentionPolicy.HIGH_FIDELITY)]
        return projector.renderer.render(pinned)


def random_fit(text, budget, seed):
    lines = lines_of(text)
    rnd = random.Random(seed)
    pri = [rnd.random() for _ in lines]
    return fit(lines, lambda i, s: pri[i], budget * 4)


def load_vanilla(which: str) -> dict[tuple[str, float, str], str]:
    """(arm, ratio, config) -> raw output text (API runs keep only the truncated text)."""
    out: dict[tuple[str, float, str], tuple[str, int]] = {}
    if which == "held":
        for f in (RUN / "curves").glob("vanilla*--*.json"):
            r = json.loads(f.read_text())
            if "error" not in r:
                out[r["arm"], r["ratio"], r["config"]] = (r["output_text"], r["raw_chars"])
        for f in (RUN / "curves").glob("tom_jev_lines--*.json"):
            r = json.loads(f.read_text())
            out[r["arm"], r["ratio"], r["config"]] = (r["output_text"], r["raw_chars"])
    for f in (HERE / "codex" / which / "curves").glob("*.json"):
        r = json.loads(f.read_text())
        out[r["arm"] + "+codex" if which == "held" else r["arm"], r["ratio"], r["config"]] = (
            r["raw_text"], len(r["raw_text"]))
    return out


def evaluate(which: str, labels: dict, tag: str):
    names = HELD_LABELS if which == "held" else FRESH_LABELS
    # configs without any reference constraint under this labeling carry no recall signal
    cfgs = [c for c in configs_for(names, labels) if c.kb.by_type(KT.CONSTRAINT)]
    van = load_vanilla(which)
    rows = []
    for c in cfgs:
        for r in RATIOS:
            b = max(64, int(c.kb.total_tokens * r))

            def add(arm, text, raw_chars, extra=None):
                trunc = truncate_to_tokens(text, b)
                pt = per_type_preservation(c.kb, trunc)
                rows.append({"set": which, "labels": tag, "arm": arm, "ratio": r,
                             "config": c.label, "C": pt["constraint"], "P": pt["procedural"],
                             "raw_over_budget": raw_chars / (4 * b),
                             "valid": raw_chars <= 4 * b, **(extra or {})})

            for name, key in POL.items():
                out = fit(lines_of(c.text), key, b * 4)
                add(name, out, len(out))
            out = fit(lines_of(c.text), oracle_policy(labels), b * 4)
            add("ORACLE", out, len(out))
            if tag == "L1" and L2:  # frontier LLM as line classifier, same selector
                out = fit(lines_of(c.text), oracle_policy(L2), b * 4)
                add("llmlabel_fit:gpt-6-sol", out, len(out))
            rs = [random_fit(c.text, b, s) for s in range(20)]
            cs = [per_type_preservation(c.kb, x) for x in rs]
            rows.append({"set": which, "labels": tag, "arm": "random_fit", "ratio": r,
                         "config": c.label, "C": st.mean(x["constraint"] for x in cs),
                         "P": nanmean(x["procedural"] for x in cs), "raw_over_budget": 1.0,
                         "valid": True})
            if which == "fresh":
                out = replay_tom_jev_lines(c.text, b)
                add("tom_jev_lines", out, len(out))
            for (arm, rr, cfg), (text, raw_chars) in van.items():
                if rr == r and cfg == c.label:
                    add(arm, text, raw_chars)
    return cfgs, rows


def aggregate(rows):
    out = {}
    by = {}
    for x in rows:
        by.setdefault((x["arm"], x["ratio"]), []).append(x)
    for (arm, r), xs in sorted(by.items()):
        out.setdefault(arm, {})[str(r)] = {
            "n": len(xs),
            "C_trunc": round(st.mean(x["C"] for x in xs), 4),
            "C_strict": round(st.mean(x["C"] if x["valid"] else 0.0 for x in xs), 4),
            "P_trunc": round(nanmean(x["P"] for x in xs), 4),
            "valid": sum(x["valid"] for x in xs),
            "valid@1.1": sum(x["raw_over_budget"] <= 1.1 for x in xs),
            "median_raw_over_budget": round(st.median(x["raw_over_budget"] for x in xs), 3),
        }
    return out


def tests(rows, pairs, strict=True):
    idx = {(x["arm"], x["ratio"], x["config"]): x for x in rows}
    cfgs = sorted({x["config"] for x in rows})
    f = (lambda x: x["C"] if x["valid"] else 0.0) if strict else (lambda x: x["C"])
    res = {}
    for a, b in pairs:
        for r in RATIOS:
            common = [c for c in cfgs if (a, r, c) in idx and (b, r, c) in idx]
            if len(common) < 5:
                continue
            res[f"{a} vs {b} @{r}"] = paired([f(idx[a, r, c]) for c in common],
                                            [f(idx[b, r, c]) for c in common])
    adj = holm({k: v["p"] for k, v in res.items()})
    for k in res:
        res[k]["holm_p"] = round(adj[k], 6)
        res[k]["p"] = round(res[k]["p"], 6)
    return res


def five_rounds(cfgs, which):
    out = {}
    for name in ("jevP_tier", "jevfit_imp", "hybridP", "regexfit_doc"):
        out[name] = [round(st.mean(rounds(POL[name], c)[k]["c_recall"] for c in cfgs), 4)
                     for k in range(5)]
    stab = HERE / "codex" / which / "stability"
    if stab.exists():
        recs = [json.loads(f.read_text()) for f in stab.glob("*.json")]
        for arm in sorted({x["arm"] for x in recs}):
            per = {}
            for x in recs:
                if x["arm"] == arm:
                    per.setdefault(x["config"], {})[x["round"]] = x["c_recall"]
            full = [v for v in per.values() if len(v) == 5]
            if full:
                out[arm] = [round(st.mean(v[k] for v in full), 4) for k in range(1, 6)]
                out[arm + "_n"] = len(full)
    return out


PRIMARY = [("jevP_tier", "vanilla:gpt-5.6-luna"), ("jevP_tier", "regexfit_doc"),
           ("jevP_tier", "tom_jev_lines")]
SECONDARY = [("jevP_tier", "vanilla:gpt-6-luna"), ("jevP_tier", "vanilla:gpt-6-sol"),
             ("jevP_tier", "llmlabel_fit:gpt-6-sol"),
             ("jevP_tier", "jevfit_imp"), ("hybridP", "jevP_tier"),
             ("jevP_tier", "random_fit")]

report, all_rows = {}, []
fresh_cfgs, fresh_rows = evaluate("fresh", L1_FRESH, "L1")
held_cfgs, held_rows = evaluate("held", L1_HELD, "L1")
all_rows += fresh_rows + held_rows
report["fresh_L1"] = {"n_configs": len(fresh_cfgs),
                      "n_constraints": sum(len(c.kb.by_type(KT.CONSTRAINT)) for c in fresh_cfgs),
                      "table": aggregate(fresh_rows),
                      "primary_strict": tests(fresh_rows, PRIMARY, strict=True),
                      "secondary_strict": tests(fresh_rows, SECONDARY, strict=True),
                      "secondary_trunc": tests(fresh_rows, PRIMARY + SECONDARY, strict=False),
                      "rounds": five_rounds(fresh_cfgs, "fresh")}
held_pairs = [("jevP_tier", "vanilla:gpt-5.6-luna"), ("jevP_tier", "regexfit_doc"),
              ("jevP_tier", "tom_jev_lines"), ("jevP_tier", "vanilla:gpt-6-sol+codex"),
              ("jevP_tier", "llmlabel_fit:gpt-6-sol")]
report["held_L1"] = {"table": aggregate(held_rows),
                     "strict": tests(held_rows, held_pairs, strict=True),
                     "trunc": tests(held_rows, held_pairs, strict=False),
                     "rounds": five_rounds(held_cfgs, "held")}

# independent labeler L2 (if available): agreement with L1 + re-scored primary comparisons
if L2:
    for which, l1, names in (("fresh", L1_FRESH, FRESH_LABELS), ("held", L1_HELD, HELD_LABELS)):
        texts = sorted({i.text for c in ALL if c.label in set(names) for i in c.kb.items})
        pairs_ = [(l1[_key(t)]["type"], L2[_key(t)]["type"]) for t in texts if _key(t) in L2]
        if len(pairs_) < 0.95 * len(texts):
            continue
        agree = sum(a == b for a, b in pairs_) / len(pairs_)
        cats = sorted({a for a, _ in pairs_} | {b for _, b in pairs_})
        pe = sum((sum(a == k for a, _ in pairs_) / len(pairs_)) *
                 (sum(b == k for _, b in pairs_) / len(pairs_)) for k in cats)
        bc = [(a == "constraint", b == "constraint") for a, b in pairs_]
        po_b = sum(x == y for x, y in bc) / len(bc)
        p1, p2 = sum(x for x, _ in bc) / len(bc), sum(y for _, y in bc) / len(bc)
        pe_b = p1 * p2 + (1 - p1) * (1 - p2)
        jc = [(J.row(t)["type"] == "constraint", L2[_key(t)]["type"] == "constraint")
              for t in texts if _key(t) in L2]
        tp = sum(a and b for a, b in jc)
        l2c = {k: v for k, v in L2.items()}
        cfgs2, rows2 = evaluate(which, l2c, "L2")
        all_rows += rows2
        report[f"{which}_L2"] = {
            "lines": len(pairs_), "agreement_5way": round(agree, 4),
            "kappa_5way": round((agree - pe) / (1 - pe), 4),
            "kappa_constraint_binary": round((po_b - pe_b) / (1 - pe_b), 4),
            "L1_constraints": sum(x for x, _ in bc), "L2_constraints": sum(y for _, y in bc),
            "jev_vs_L2_constraint_precision": round(tp / max(1, sum(a for a, _ in jc)), 4),
            "jev_vs_L2_constraint_recall": round(tp / max(1, sum(b for _, b in jc)), 4),
            "table": aggregate(rows2),
            "strict": tests(rows2, PRIMARY + [("jevP_tier", "vanilla:gpt-6-sol")], strict=True),
        }

(HERE / "final.json").write_text(json.dumps(report, indent=1))
(HERE / "final_rows.json").write_text(json.dumps(all_rows))

for key in [k for k in report if "table" in report[k]]:
    print(f"\n== {key}")
    for arm, per in sorted(report[key]["table"].items(), key=lambda kv: -kv[1]["0.5"]["C_strict"]):
        print(f"  {arm:28s} " + "  ".join(
            f"{r}: {per[r]['C_trunc']:.3f}/{per[r]['C_strict']:.3f} P={per[r]['P_trunc']:.2f} "
            f"v={per[r]['valid']:2d}/{per[r]['n']}" for r in ("0.5", "0.25", "0.1") if r in per))
    for tk in ("primary_strict", "secondary_strict", "strict"):
        for k, v in report[key].get(tk, {}).items():
            print(f"   [{tk}] {k:48s} d={v['diff']:+.3f} {v['ci95']} "
                  f"W/T/L={v['wins']}/{v['ties']}/{v['losses']} holm={v['holm_p']}")
    if "rounds" in report[key]:
        print("   rounds:", report[key]["rounds"])
    for k in ("agreement_5way", "kappa_5way", "kappa_constraint_binary", "L1_constraints",
              "L2_constraints", "jev_vs_L2_constraint_precision", "jev_vs_L2_constraint_recall"):
        if k in report[key]:
            print(f"   {k}: {report[key][k]}")
