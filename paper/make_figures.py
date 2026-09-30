"""Regenerate figures and article statistics from frozen per-case JSON records.

Run from repo root: python3 paper/make_figures.py (requires Pillow).
No model calls. Primary analysis is the 30 configs not used in method development.
"""

import hashlib
import json
import random
import statistics as stats
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results/kt-benchmark-full"
LAT = ROOT / "results/kt-benchmark-latency"
OUT = Path(__file__).resolve().parent
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)
manifest = json.loads((RUN / "manifest.json").read_text())
held = set(manifest["configs"][20:])
arms = {
    "tom_jev_lines": ("Jev line-TOM", "#156b70"),
    "tom_jev_budget:gpt-6-luna": ("TOM + Jev / GPT-6 Luna", "#897029"),
    "tom_budget:gpt-6-luna": ("TOM / GPT-6 Luna", "#bd6a29"),
    "vanilla:gpt-5.6-luna": ("GPT-5.6 Luna", "#534c9d"),
    "vanilla:gpt-6-luna": ("GPT-6 Luna", "#8564ae"),
    "vanilla:gpt-5.4-mini": ("GPT-5.4 mini", "#637fa4"),
    "temporal_window": ("Temporal window", "#828b95"),
}
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font = ImageFont.truetype(font_path, 22)
small = ImageFont.truetype(font_path, 19)
title = ImageFont.truetype(font_path, 27)


def records(kind, *, subset):
    return [
        r
        for f in sorted((RUN / kind).glob("*.json"))
        if (r := json.loads(f.read_text())).get("config") in subset and "error" not in r
    ]


curve = records("curves", subset=held)
rounds = records("stability", subset=held)
assert len(curve) == 30 * 12 * 3 and len(rounds) == 30 * 12 * 5
idx = {(r["arm"], r["ratio"], r["config"]): r for r in curve}
ridx = {(r["arm"], r["round"], r["config"]): r for r in rounds}


def ci(values, seed=11):
    rnd = random.Random(seed)
    samples = sorted(stats.mean(rnd.choices(values, k=len(values))) for _ in range(10000))
    return [round(samples[250], 4), round(samples[9750], 4)]


def paired(a, b, ratio, *, valid_only=False):
    deltas = []
    for c in sorted(held):
        x, y = idx[a, ratio, c], idx[b, ratio, c]
        measure = lambda r: (
            (0 if r["overshoot"] else r["per_type"]["constraint"])
            if valid_only
            else r["per_type"]["constraint"]
        )
        deltas.append(measure(x) - measure(y))
    return {"difference": round(stats.mean(deltas), 4), "ci95": ci(deltas), "n": len(deltas)}


by_ratio = {}
for r in (0.5, 0.25, 0.1):
    by_ratio[str(r)] = {}
    for arm in manifest["arms"]:
        rows = [idx[arm, r, c] for c in held]
        valid = [x for x in rows if not x["overshoot"]]
        by_ratio[str(r)][arm] = {
            "n": len(rows),
            "valid": len(valid),
            "mean_constraint_recall_after_truncation": round(
                stats.mean(x["per_type"]["constraint"] for x in rows), 4
            ),
            "mean_procedure_recall_after_truncation": round(
                stats.mean(x["per_type"]["procedural"] for x in rows), 4
            ),
            "mean_validity_weighted_recall": round(
                sum(x["per_type"]["constraint"] for x in valid) / len(rows), 4
            ),
            "valid_only_recall": round(stats.mean(x["per_type"]["constraint"] for x in valid), 4)
            if valid
            else None,
            "median_raw_to_budget": round(
                stats.median(x["raw_chars"] / (4 * x["budget"]) for x in rows), 3
            ),
            "mean_cost_usd": round(stats.mean(x["cost_usd"] for x in rows), 6),
        }


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


statistic = {
    "analysis_set": "30 held-out configurations: positions 21-50 in seed-11 manifest",
    "dev_set_size": 20,
    "score": "constraint key-token match on text[:4*budget]",
    "valid": "len(raw_text)<=4*budget before truncation",
    "validity_weighted_recall": "mean over all configurations of recall*1[valid] (invalid assigned zero)",
    "ratios": by_ratio,
    "paired": {
        f"{a} vs {b}, ratio {r}": paired(a, b, r)
        for a, b in (
            ("tom_jev_lines", "vanilla:gpt-5.6-luna"),
            ("tom_jev_lines", "tom_jev_budget:gpt-6-luna"),
            ("tom_jev_budget:gpt-6-luna", "tom_budget:gpt-6-luna"),
            ("tom_jev_budget:gpt-5.6-luna", "tom_budget:gpt-5.6-luna"),
        )
        for r in (0.5, 0.25, 0.1)
    },
    "validity_weighted_pair": {
        f"Jev line-TOM vs GPT-5.6 Luna, ratio {r}": paired(
            "tom_jev_lines", "vanilla:gpt-5.6-luna", r, valid_only=True
        )
        for r in (0.5, 0.25, 0.1)
    },
    "run_records": {
        kind: sum(1 for _ in (RUN / kind).glob("*.json")) for kind in ("curves", "stability")
    },
    "input_hashes": {
        str(p.relative_to(ROOT)): digest(p)
        for p in (
            ROOT / "src/tom/benchmarks/kt_faithful.py",
            ROOT / "src/tom/benchmarks/kt_cascade.py",
            RUN / "manifest.json",
            ROOT / "results/kt-faithful/cascade-labels.jsonl",
        )
    },
}
(OUT / "analysis.json").write_text(json.dumps(statistic, indent=2) + "\n")


def canvas(name, xlabel, ylabel, xmax, ticks, series, subtitle):
    image = Image.new("RGB", (1300, 690), "white")
    d = ImageDraw.Draw(image)
    left, top, width, height = 115, 105, 1000, 400
    d.text((left, 20), subtitle, font=title, fill="#162d42")
    for y in (0, 0.25, 0.5, 0.75, 1):
        yy = top + height * (1 - y)
        d.line((left, yy, left + width, yy), fill="#d8e0e5", width=2)
        d.text((40, yy - 11), f"{y:.2f}", font=small, fill="#324455")
    for x, label in ticks:
        xx = left + width * x / xmax
        d.text((xx - 35, top + height + 12), str(label), font=small, fill="#324455")
    d.text((left + width / 2 - 115, top + height + 50), xlabel, font=font, fill="#162d42")
    d.text((left, top - 42), ylabel, font=small, fill="#162d42")
    for label, color, xy in series:
        points = [(left + width * x / xmax, top + height * (1 - y)) for x, y in xy]
        d.line(points, fill=color, width=5)
        for x, y in points:
            d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color)
    for i, (label, color, _) in enumerate(series):
        x = 35 + (i % 4) * 307
        y = 590 + (i // 4) * 34
        d.line((x, y + 10, x + 35, y + 10), fill=color, width=5)
        d.text((x + 45, y), label, font=small, fill="#243747")
    image.save(FIG / name, dpi=(180, 180))


ratio_series = []
for arm, (label, color) in arms.items():
    ratio_series.append(
        (
            label,
            color,
            [
                (i, by_ratio[str(r)][arm]["mean_constraint_recall_after_truncation"])
                for i, r in enumerate((0.1, 0.25, 0.5))
            ],
        )
    )
canvas(
    "recall.png",
    "Target ratio",
    "Constraint recall",
    2,
    [(0, "10%"), (1, "25%"), (2, "50%")],
    ratio_series,
    "Key-token recall after truncation (held-out n=30)",
)
round_series = []
for arm, (label, color) in arms.items():
    round_series.append(
        (
            label,
            color,
            [(i - 1, stats.mean(ridx[arm, i, c]["c_recall"] for c in held)) for i in range(1, 6)],
        )
    )
canvas(
    "rounds.png",
    "Round (50% of prior output)",
    "Constraint recall",
    4,
    [(i, str(i + 1)) for i in range(5)],
    round_series,
    "Five successive compactions (held-out n=30)",
)

# Plot the actual ability to meet the target, rather than treating truncated outputs as valid.
valid_series = []
for arm in (
    "tom_jev_lines",
    "tom_jev_budget:gpt-6-luna",
    "vanilla:gpt-5.6-luna",
    "vanilla:gpt-6-luna",
):
    label, color = arms[arm]
    valid_series.append(
        (
            label,
            color,
            [(i, by_ratio[str(r)][arm]["valid"] / 30) for i, r in enumerate((0.1, 0.25, 0.5))],
        )
    )
canvas(
    "validity.png",
    "Target ratio",
    "Valid fraction (raw output within budget)",
    2,
    [(0, "10%"), (1, "25%"), (2, "50%")],
    valid_series,
    "Hard-budget validity before truncation (held-out n=30)",
)
print("Wrote", OUT / "analysis.json", "and 3 figures")
