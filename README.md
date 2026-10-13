# judge-calibration-kit

[![CI](https://github.com/ravinelango/judge-calibration-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/ravinelango/judge-calibration-kit/actions/workflows/ci.yml)
![status](https://img.shields.io/badge/status-early%20(v0.1)-orange)
![license](https://img.shields.io/badge/license-MIT-blue)

**Before you trust an LLM-as-a-judge, measure how often it agrees with you.**

This kit compares an automated judge's pass/fail verdicts with human labels and writes a
short markdown report: Cohen's kappa, raw agreement, a confusion matrix, judge vs human
pass rates with confidence intervals, and a table of every disagreement.

## Why judge calibration matters
LLM judges are now used as release gates and quality dashboards. An uncalibrated judge is an
unvalidated test instrument: it can be systematically lenient (passing bad answers),
strict (blocking good ones), or simply noisy. In classic QA you validate the measurement
system before trusting its readings; this applies the same discipline to LLM evaluation.

- **Kappa, not just accuracy.** Raw agreement looks good when most outputs pass. Kappa
  corrects for agreement expected by chance.
- **Direction of error.** The confusion matrix separates "too lenient" from "too strict",
  which need different fixes.
- **Uncertainty.** Wilson intervals show how much the pass rates could move with a small
  sample.
- **Disagreements are the point.** Reading them is how you fix the rubric, the judge
  prompt, or your own labels.

## Quickstart
```bash
pip install -e '.[dev]'
jck run --data examples/synthetic_support_answers.jsonl --judge mock --synthetic --out reports/demo.md
```
See [`examples/sample_report.md`](examples/sample_report.md) for the output.

Using a real model (optional; keys read from the environment):
```bash
pip install -e '.[openai]'      # or '.[anthropic]'
export OPENAI_API_KEY=...
jck run --data my_labels.jsonl --judge openai:gpt-4o-mini --out reports/openai.md --json reports/openai.json
```

## Data format
One JSON object per line: `input`, `output`, `human_label` (`pass`/`fail`), and optional
`id` and `rubric`. Label with the [labeling guide](docs/labeling-guide.md).

## Methodology
| Metric | What it tells you |
|---|---|
| Raw agreement | Share of items where judge and human match |
| Cohen's kappa | Agreement beyond chance; bands per Landis & Koch (1977) as a rough guide |
| Confusion matrix | Rows are human labels, columns are judge labels |
| Pass rates + Wilson 95% CI | Whether the judge's pass rate is biased relative to humans |

The judge interface is a small `Protocol`; add a provider by implementing
`judge(example) -> Verdict`.

## Status
**Early, v0.1.** The metrics, mock judge, report and CLI work and are tested. The bundled
dataset is **synthetic** and the mock judge is a keyword heuristic, so the sample report
demonstrates the format only. **No real-model calibration results are published yet.**

## Roadmap
- Run real judges against a hand-labeled set and publish the results with the raw data
- Per-criterion (multi-rubric) calibration
- Human-to-human agreement baseline
- Judge prompt A/B comparison
- Bootstrap CI for kappa

## License
MIT © Ravin Elango
