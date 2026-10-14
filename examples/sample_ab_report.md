# Judge A/B comparison report

- Dataset: `synthetic_support_answers.jsonl` (10 examples, same human labels for both)
- Judge A: `mock`
- Judge B: `mock:strict`
- Generated: 2026-10-14 19:47 UTC

> **Synthetic demo.** The dataset is synthetic and mock judges are keyword heuristics, so these numbers only show the report format. They are not results.

## Agreement with human labels

| Metric | A | B |
|---|---|---|
| Raw agreement | 80.0% | 90.0% |
| Cohen's kappa | 0.583 (moderate) | 0.800 (substantial) |
| Kappa 95% CI (bootstrap) | 0.000 to 1.000 | 0.400 to 1.000 |
| Judge pass rate | 60.0% (95% CI 31.3% to 83.2%) | 50.0% (95% CI 23.7% to 76.3%) |
| Too lenient (human fail, judge pass) | 1 | 0 |
| Too strict (human pass, judge fail) | 1 | 1 |

## Verdict

- Higher kappa: **B** (`mock:strict`).
- Items only A got right: 0. Items only B got right: 1.
- The kappa intervals overlap, so this sample does not show a reliable difference. Label more items before switching judges on this evidence alone.

## Where A and B disagree

| id | human | A | B | closer to human | output |
|---|---|---|---|---|---|
| s08 | fail | pass | fail | B | Weekly scheduling lets you pick a day and the report is emailed to you automati… |

_Note: n=10 is small; treat kappa and the intervals as rough._
