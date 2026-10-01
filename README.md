# Typed Observational Memory

Research code and paper for **"Select, Don't Generate: Budget-Feasible Rule
Retention for Agent Configurations with a Non-Generative Classifier"** (Proença,
2026).

When an agent configuration file (`AGENTS.md`, `CLAUDE.md`) is compacted into a
token budget, binding rules should survive. The default approach — asking an LLM
to summarize — drops safety rules at the same rate as prose (the *compaction
cliff*). This work studies a generation-free alternative, **JevSelect**: a
structured-decision model (Jev) assigns each line a probability distribution over
five knowledge types, and a greedy selector fills a hard character budget by type
tier and constraint probability, emitting whole lines verbatim in document order.
The output always fits by construction.

On 60 pre-registered, previously unused configurations, JevSelect retains
0.92 / 0.75 / 0.54 of reference rules at 50 / 25 / 10 % budgets — several times
more than direct LLM compaction (≤ 0.12), with every output within budget.

## Repository layout

| Path | Contents |
|---|---|
| `paper/main.tex` | The manuscript (`Select, Don't Generate`). |
| `paper/arxiv-source.zip` | Self-contained arXiv submission package (`.tex` + `.bbl` + figures). |
| `paper/reproduce/` | Raw per-config LLM outputs, label caches, pre-registration (SHA-256) and figure/analysis scripts for every number in the paper. |
| `src/tom/context/budgeted.py` | The JevSelect selector (`select_lines`). |
| `src/tom/benchmarks/kt_faithful.py` | Benchmark harness; the `jev_budget_lines` arm. |
| `src/tom/providers/jev.py` | Jev classifier wrapper (`@typesafe-ai/sdk`). |
| `.pi/extensions/tom-memory.ts` | Pi extension: observational memory bridge. |
| `data/` | AAC sample metadata; third-party datasets referenced by URL + SHA-256 (see `data/README.md`). |

## Reproduce

```bash
uv sync --extra dev          # Python >= 3.12
PYTHONPATH=src uv run pytest  # unit tests
```

Analysis and figures regenerate from the frozen records without any model calls:

```bash
cd paper/reproduce
PYTHONPATH=. uv run --with matplotlib --with numpy python make_review_figures.py
```

The confirmatory results use the frozen records in `paper/reproduce/records/`;
the pre-registration hash is in `paper/reproduce/PREREGISTRATION.md`.

## Build the paper

```bash
cd paper
latexmk -pdf main.tex
```

## Reference implementation

JevSelect ships as a drop-in compaction extension for the Pi coding agent:
**[pi-jev-select](https://github.com/MarcosPTProenca/pi-jev-select)**.

## License

Code is MIT (see `LICENSE`). The manuscript text in `paper/` is intended for
arXiv release under CC BY 4.0.
