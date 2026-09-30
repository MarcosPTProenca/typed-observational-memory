"""Figures for the review (vector PDF + PNG). Run: uv run --with matplotlib --with numpy python ..."""

import json
import random
import statistics as st
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
REC = HERE / "records"
FIG = HERE.parent / "figures"
FIG.mkdir(exist_ok=True)
rows = json.loads((REC / "final_rows.json").read_text())
final = json.loads((REC / "final.json").read_text())
RATIOS = (0.1, 0.25, 0.5)
STYLE = {
    "jevP_tier": ("Jev-P budgeted (ours, improved)", "#0b6e4f", "o", "-"),
    "jevfit_imp": ("Jev-label budgeted", "#57a773", "s", "-"),
    "tom_jev_lines": ("LineTOM-Jev (paper)", "#08415c", "D", "--"),
    "vanilla:gpt-5.6-luna": ("GPT-5.6 Luna", "#6a4c93", "^", "-"),
    "vanilla:gpt-6-luna": ("GPT-6 Luna", "#9d79bc", "v", "-"),
    "vanilla:gpt-6-sol": ("GPT-6 Sol (frontier)", "#c44536", "P", "-"),
    "regexfit_doc": ("Regex budgeted (free)", "#b08968", "X", ":"),
    "random_fit": ("Random lines (chance)", "#8d99ae", ".", ":"),
    "ORACLE": ("Oracle labels (ceiling)", "#222222", "*", ":"),
}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def ci(xs, seed=11, draws=4000):
    rnd = random.Random(seed)
    m = sorted(st.mean(rnd.choices(xs, k=len(xs))) for _ in range(draws))
    return m[int(draws * .025)], m[int(draws * .975)]


def sel(**kw):
    return [x for x in rows if all(x[k] == v for k, v in kw.items())]


def recall_panel(ax, which, labels, strict, title):
    for arm, (name, color, marker, ls) in STYLE.items():
        pts = []
        for r in RATIOS:
            xs = [(x["C"] if (x["valid"] or not strict) else 0.0)
                  for x in sel(set=which, labels=labels, arm=arm, ratio=r)]
            if xs:
                lo, hi = ci(xs)
                pts.append((r, st.mean(xs), lo, hi))
        if not pts:
            continue
        xr = [RATIOS.index(p[0]) for p in pts]
        ax.errorbar(xr, [p[1] for p in pts], yerr=[[p[1] - p[2] for p in pts],
                                                    [p[3] - p[1] for p in pts]],
                    label=name, color=color, marker=marker, ls=ls, capsize=2, lw=1.4, ms=5)
    ax.set_xticks(range(3), ["10%", "25%", "50%"])
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("Target budget (fraction of original)")
    ax.set_title(title, fontsize=9)
    ax.grid(axis="y", alpha=.3)


for which, n in (("fresh", final["fresh_L1"]["n_configs"]), ("held", 30)):
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6), sharey=True)
    recall_panel(axes[0], which, "L1", False, "(a) Paper metric: recall after truncation")
    recall_panel(axes[1], which, "L1", True, "(b) Strict: recall if raw output fits, else 0")
    axes[0].set_ylabel("Constraint key-token recall")
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=5, fontsize=7.5, frameon=False,
               bbox_to_anchor=(0.5, -0.07))
    fig.suptitle(f"{'Fresh confirmatory' if which == 'fresh' else 'Original held-out'} set "
                 f"(n={n} configurations, 95% bootstrap CI)", fontsize=10)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"recall_{which}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)

# raw-output length relative to budget (feasibility)
fig, axes = plt.subplots(1, 3, figsize=(10, 3.2), sharey=True)
arms = ["tom_jev_lines", "vanilla:gpt-5.6-luna", "vanilla:gpt-6-luna", "vanilla:gpt-6-sol",
        "jevP_tier"]
for ax, r in zip(axes, RATIOS[::-1], strict=True):
    data = [[x["raw_over_budget"] for x in sel(set="fresh", labels="L1", arm=a, ratio=r)]
            for a in arms]
    ax.boxplot(data, showfliers=True, widths=.6, flierprops={"ms": 2})
    ax.axhline(1.0, color="#c44536", lw=1, ls="--")
    ax.set_yscale("log")
    ax.set_xticks(range(1, len(arms) + 1), [STYLE[a][0].split(" (")[0] for a in arms],
                  rotation=35, ha="right", fontsize=7)
    ax.set_title(f"target {int(r * 100)}%", fontsize=9)
axes[0].set_ylabel("raw output length / budget (log)")
fig.suptitle("Budget feasibility on the fresh set: values above the dashed line are invalid",
             fontsize=10)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(FIG / f"feasibility_fresh.{ext}", dpi=200, bbox_inches="tight")
plt.close(fig)

# five rounds
fig, ax = plt.subplots(figsize=(5.2, 3.4))
rd = final["fresh_L1"]["rounds"]
for arm in ("jevP_tier", "jevfit_imp", "regexfit_doc", "vanilla:gpt-5.6-luna"):
    if arm in rd:
        name, color, marker, ls = STYLE[arm]
        n = rd.get(arm + "_n")
        ax.plot(range(1, 6), rd[arm], label=name + (f" (n={n})" if n else ""), color=color,
                marker=marker, ls=ls)
ax.set_xticks(range(1, 6))
ax.set_xlabel("Compaction round (each 50% of previous output)")
ax.set_ylabel("Recall of ORIGINAL constraints")
ax.set_ylim(0, 1)
ax.legend(fontsize=7, frameon=False)
ax.grid(axis="y", alpha=.3)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(FIG / f"rounds_fresh.{ext}", dpi=200, bbox_inches="tight")
plt.close(fig)

# classifier precision/recall for constraints vs L1 (all 110 configs' distinct lines)
sys.path.insert(0, str(HERE))
from common import ROOT, _key, cache, rx_is_c  # noqa: E402

L1 = cache(ROOT / "results/kt-faithful/cascade-labels.jsonl") | cache(REC / "cascade-fresh.jsonl")
J = cache(REC / "jevprobs.jsonl")
L2 = cache(REC / "l2-labels.jsonl")
texts = json.loads((REC / "lines50.json").read_text()) + json.loads(
    (REC / "lines_fresh.json").read_text())
texts = sorted({t for t in texts if _key(t) in L1 and _key(t) in J})
gold = [L1[_key(t)]["type"] == "constraint" for t in texts]


def pr(pred):
    tp = sum(p and g for p, g in zip(pred, gold, strict=True))
    return tp / max(1, sum(pred)), tp / max(1, sum(gold))


fig, ax = plt.subplots(figsize=(4.6, 3.6))
for field, name, color in (("pc", "Jev P(constraint)", "#0b6e4f"),
                           ("binding", "Jev 'binding rule' Noul", "#57a773")):
    score = [J[_key(t)]["p_type"].get("constraint", 0) if field == "pc" else J[_key(t)]["binding"]
             for t in texts]
    pts = [pr([s >= th for s in score]) for th in [i / 50 for i in range(1, 50)]]
    ax.plot([p[1] for p in pts], [p[0] for p in pts], color=color, label=name)
for name, pred, m in (("Jev argmax (paper)", [J[_key(t)]["type"] == "constraint" for t in texts], "D"),
                      ("KT regex", [rx_is_c(t) for t in texts], "X")):
    p, r = pr(pred)
    ax.scatter([r], [p], marker=m, s=45, zorder=3, label=f"{name} (P={p:.2f}, R={r:.2f})")
if L2:
    sub = [(L2[_key(t)]["type"] == "constraint") for t in texts if _key(t) in L2]
    if len(sub) == len(texts):
        p, r = pr(sub)
        ax.scatter([r], [p], marker="P", s=45, zorder=3, label=f"GPT-6 Sol labeler (P={p:.2f}, R={r:.2f})")
ax.set_xlabel("Recall of cascade (L1) constraints")
ax.set_ylabel("Precision")
ax.set_xlim(0, 1.02)
ax.set_ylim(0, 1.02)
ax.legend(fontsize=6.5, frameon=True, loc="lower left")
ax.set_title(f"Constraint detection vs. reference cascade ({len(texts)} lines)", fontsize=9)
ax.grid(alpha=.3)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(FIG / f"classifier_pr.{ext}", dpi=200, bbox_inches="tight")
plt.close(fig)
print("figures written to", FIG)
