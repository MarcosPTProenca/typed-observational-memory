# Pre-registration: confirmatory fresh-set evaluation (written before any fresh-set run)

Date: 2026-09-30. Selection evidence: `select_dev.json` (policy chosen on the 20 DEV configs only).

## Fresh set
Eligible AAC sample files (same `load_configs` filter, seed 11), positions 51.. in seeded order,
never used before. N = the first N in that order; N fixed by labeling budget only, before any
compactor is run on them.

## Reference labels
- L1 (primary): the paper's cascade (regex -> text-embedding-3-large -> gpt-5.4-mini), same code
  (`kt_cascade.cascade_relabel`) and cache format.
- L2 (secondary, independent of regex): gpt-6-sol via the Codex subscription bridge, batch prompt
  with the five-type definitions; used to re-score every arm on held-out and fresh sets.

## Arms
Primary method: `jevP_tier` = Jev five-way Choice argmax tier, then descending P(constraint), then
document order; greedy line fill of the hard budget 4B characters; output in document order.
Others: `jevfit_imp`, `hybridP` (uses the KT regex -> label-circular, reported as such),
`regexfit_doc` (zero-cost control), `random_fit` (20 seeds, chance level), `tom_jev_lines`
(paper method, re-executed with the new Jev labels through the original projector),
`vanilla:gpt-5.6-luna`, `vanilla:gpt-6-luna`, `vanilla:gpt-6-sol` (Codex endpoint; deviation from
the API endpoint used in the paper), ORACLE (label-aware ceiling, not a competitor).

## Primary hypotheses (L1 labels, strict metric = recall if raw output fits 4B chars else 0)
- H1: jevP_tier > vanilla:gpt-5.6-luna at 50%, 25%, 10%.
- H2: jevP_tier > regexfit_doc at 50%, 25%, 10%.
- H3: jevP_tier > tom_jev_lines at 50%, 25%, 10%.
9 tests; paired Wilcoxon signed-rank (two-sided), Holm-adjusted; effect = mean paired difference
with 10,000-draw config-level percentile bootstrap (seed 11).

## Secondary (descriptive)
Same comparisons under L2; post-truncation recall; procedural recall (guardrail); 5-round recall;
frontier model (gpt-6-sol) comparison; hybridP. No further policy changes after this file.
