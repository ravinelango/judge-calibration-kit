# Judge calibration report

- Dataset: `synthetic_support_answers.jsonl` (10 examples)
- Judge: `mock`
- Generated: 2026-10-13 01:50 UTC

> **Synthetic demo.** The dataset is synthetic and the mock judge is a keyword heuristic, so these numbers only show the report format. They are not results.

## Agreement

| Metric | Value |
|---|---|
| Raw agreement | 80.0% |
| Cohen's kappa | 0.583 (moderate) |
| Human pass rate | 60.0% (95% CI 31.3% to 83.2%) |
| Judge pass rate | 60.0% (95% CI 31.3% to 83.2%) |

## Confusion matrix (rows: human, columns: judge)

| | judge pass | judge fail |
|---|---|---|
| **human pass** | 5 | 1 |
| **human fail** | 1 | 3 |

- Judge too lenient (human fail, judge pass): 1
- Judge too strict (human pass, judge fail): 1

## Disagreements

| id | human | judge | judge reason | output |
|---|---|---|---|---|
| s05 | pass | fail | contains marker "i don't know" | I don't know, but you can contact support from the Help menu for export options. |
| s08 | fail | pass | no failure markers found | Weekly scheduling lets you pick a day and the report is emailed to you automati… |

_Note: n=10 is small; treat kappa and the intervals as rough._
