"""Choose the Jev-probability policy on the 20 DEV configs only; report held-out afterwards."""

import json

from common import (HERE, RATIOS, ROOT, JevView, cache, fit, labeled, lines_of, load_configs,
                    nanmean, oracle_policy, policies, rounds, score, st)

manifest = json.loads((ROOT / "results/kt-benchmark-full/manifest.json").read_text())
CASCADE = cache(ROOT / "results/kt-faithful/cascade-labels.jsonl")
configs = labeled(load_configs(ROOT / "data/aac/sample", n_configs=50, seed=11), CASCADE)
assert [c.label for c in configs] == manifest["configs"]
J = JevView(cache(HERE / "jevprobs.jsonl"))
POL = policies(J) | {"ORACLE": oracle_policy(CASCADE)}


def evaluate(subset):
    res = {}
    for name, key in POL.items():
        row = {}
        for r in RATIOS:
            recs = []
            for c in subset:
                b = max(64, int(c.kb.total_tokens * r))
                recs.append(score(c, fit(lines_of(c.text), key, b * 4), b))
            row[f"C@{r}"] = round(st.mean(x["per_type"]["constraint"] for x in recs), 4)
            row[f"P@{r}"] = round(nanmean(x["per_type"]["procedural"] for x in recs), 4)
            assert not any(x["overshoot"] for x in recs)
        row["C_mean"] = round(st.mean(row[f"C@{r}"] for r in RATIOS), 4)
        row["R5"] = round(st.mean(rounds(key, c)[-1]["c_recall"] for c in subset), 4)
        res[name] = row
    return res


dev = [c for c in configs if c.label in manifest["configs"][:20]]
held = [c for c in configs if c.label in manifest["configs"][20:]]
out = {"dev": evaluate(dev), "held": evaluate(held)}
(HERE / "select_dev.json").write_text(json.dumps(out, indent=1))
for split in ("dev", "held"):
    print(split)
    for name, row in sorted(out[split].items(), key=lambda kv: -kv[1]["C_mean"]):
        print(f"  {name:14s} " + " ".join(f"{k}={v:.3f}" for k, v in row.items()))
