# Judge calibration report

- Dataset: `synthetic_support_answers.jsonl` (10 examples)
- Judge: `mock`
- Generated: 2026-10-13 20:57 UTC

> **Synthetic demo.** The dataset is synthetic and the mock judge is a keyword heuristic, so these numbers only show the report format. They are not results.

## Agreement

| Metric | Value |
|---|---|
| Raw agreement | 80.0% |
| Cohen's kappa | 0.583 (moderate) |
| Kappa 95% CI (bootstrap) | 0.000 to 1.000 |
| Human pass rate | 60.0% (95% CI 31.3% to 83.2%) |
| Judge pass rate | 60.0% (95% CI 31.3% to 83.2%) |

## Confusion matrix (rows: human, columns: judge)

| | judge pass | judge fail |
|---|---|---|
| **human pass** | 5 | 1 |
| **human fail** | 1 | 3 |

- Judge too lenient (human fail, judge pass): 1
- Judge too strict (human pass, judge fail): 1

## By rubric criterion

| Criterion | n | Agreement | Kappa | Too lenient | Too strict |
|---|---|---|---|---|---|
| (default) The output answers the input correctly, safely an… | 6 | 100.0% | 1.000 | 0 | 0 |
| Answer must be internally consistent. | 1 | 0.0% | n/a | 1 | 0 |
| Answer must explain, not just assert. | 1 | 100.0% | n/a | 0 | 0 |
| Deferring to support is acceptable when unsure. | 1 | 0.0% | n/a | 0 | 1 |
| Must not promise policy terms that are not stated. | 1 | 100.0% | n/a | 0 | 0 |

## Disagreements

| id | human | judge | judge reason | output |
|---|---|---|---|---|
| s05 | pass | fail | contains marker "i don't know" | I don't know, but you can contact support from the Help menu for export options. |
| s08 | fail | pass | no failure markers found | Weekly scheduling lets you pick a day and the report is emailed to you automati… |

_Note: n=10 is small; treat kappa and the intervals as rough._
