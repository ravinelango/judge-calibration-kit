# Judge calibration report

- Dataset: `synthetic_multi_criteria.jsonl` (12 examples)
- Judge: `mock`
- Generated: 2026-10-23 23:47 UTC

> **Synthetic demo.** The dataset is synthetic and the mock judge is a keyword heuristic, so these numbers only show the report format. They are not results.

## Agreement

| Metric | Value |
|---|---|
| Raw agreement | 91.7% |
| Cohen's kappa | 0.824 (almost perfect) |
| Kappa 95% CI (bootstrap) | 0.429 to 1.000 |
| Human pass rate | 58.3% (95% CI 32.0% to 80.7%) |
| Judge pass rate | 66.7% (95% CI 39.1% to 86.2%) |

## Confusion matrix (rows: human, columns: judge)

| | judge pass | judge fail |
|---|---|---|
| **human pass** | 7 | 0 |
| **human fail** | 1 | 4 |

- Judge too lenient (human fail, judge pass): 1
- Judge too strict (human pass, judge fail): 0

## By rubric criterion

| Criterion | n | Agreement | Kappa | Too lenient | Too strict |
|---|---|---|---|---|---|
| Must not promise policy terms that are not stated. | 6 | 100.0% | 1.000 | 0 | 0 |
| Steps match the documented flow. | 6 | 83.3% | 0.667 | 1 | 0 |

## Disagreements

| id | human | judge | judge reason | output |
|---|---|---|---|---|
| m03/correct | fail | pass | no failure markers found | I'm not sure, but you can check the shipping page or contact support for the cu… |

_Note: n=12 is small; treat kappa and the intervals as rough._
