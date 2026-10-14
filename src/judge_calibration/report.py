"""Render a markdown calibration report."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from .dataset import Example
from .judges import DEFAULT_RUBRIC, Verdict
from .metrics import CalibrationSummary, Interval, per_criterion


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _ci(i: Interval) -> str:
    return f"{_pct(i.point)} (95% CI {_pct(i.low)} to {_pct(i.high)})"


def _cell(text: str, limit: int = 80) -> str:
    text = " ".join(text.split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _kci(summary: CalibrationSummary) -> str:
    ci = summary.kappa_ci
    return "n/a" if ci is None else f"{ci.low:.3f} to {ci.high:.3f}"


def _criterion_rows(examples: Sequence[Example], verdicts: Sequence[Verdict]) -> list[str]:
    stats = per_criterion(
        [e.rubric or f"(default) {DEFAULT_RUBRIC}" for e in examples],
        [e.human_label for e in examples],
        [v.label for v in verdicts],
    )
    rows = []
    for c, m in sorted(stats.items(), key=lambda kv: (-kv[1]["n"], kv[0])):
        kappa = f"{m['kappa']:.3f}" if m["n"] >= 2 else "n/a"
        rows.append(
            f"| {_cell(c, 60)} | {m['n']} | {_pct(m['raw_agreement'])} | {kappa} | "
            f"{m['lenient']} | {m['strict']} |"
        )
    return rows


def kappa_band(k: float) -> str:
    """Landis & Koch (1977) descriptive bands. A convention, not a pass/fail threshold."""
    if k < 0:
        return "poor"
    for upper, name in ((0.2, "slight"), (0.4, "fair"), (0.6, "moderate"), (0.8, "substantial")):
        if k <= upper:
            return name
    return "almost perfect"


def render(
    examples: Sequence[Example],
    verdicts: Sequence[Verdict],
    summary: CalibrationSummary,
    judge_name: str,
    dataset_name: str,
    synthetic: bool = False,
) -> str:
    c = summary.confusion
    lines = [
        "# Judge calibration report",
        "",
        f"- Dataset: `{dataset_name}` ({summary.n} examples)",
        f"- Judge: `{judge_name}`",
        f"- Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
    ]
    if synthetic:
        lines += [
            "",
            "> **Synthetic demo.** The dataset is synthetic and the mock judge is a keyword "
            "heuristic, so these numbers only show the report format. They are not results.",
        ]
    lines += [
        "",
        "## Agreement",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Raw agreement | {_pct(summary.raw_agreement)} |",
        f"| Cohen's kappa | {summary.kappa:.3f} ({kappa_band(summary.kappa)}) |",
        f"| Kappa 95% CI (bootstrap) | {_kci(summary)} |",
        f"| Human pass rate | {_ci(summary.human_pass_rate)} |",
        f"| Judge pass rate | {_ci(summary.judge_pass_rate)} |",
        "",
        "## Confusion matrix (rows: human, columns: judge)",
        "",
        "| | judge pass | judge fail |",
        "|---|---|---|",
        f"| **human pass** | {c['pass']['pass']} | {c['pass']['fail']} |",
        f"| **human fail** | {c['fail']['pass']} | {c['fail']['fail']} |",
        "",
        f"- Judge too lenient (human fail, judge pass): {c['fail']['pass']}",
        f"- Judge too strict (human pass, judge fail): {c['pass']['fail']}",
        "",
        "## By rubric criterion",
        "",
        "| Criterion | n | Agreement | Kappa | Too lenient | Too strict |",
        "|---|---|---|---|---|---|",
        *_criterion_rows(examples, verdicts),
        "",
        "## Disagreements",
        "",
    ]
    rows = [(e, v) for e, v in zip(examples, verdicts, strict=True) if e.human_label != v.label]
    if not rows:
        lines.append("None. The judge matched every human label.")
    else:
        lines += ["| id | human | judge | judge reason | output |", "|---|---|---|---|---|"]
        for e, v in rows:
            lines.append(
                f"| {e.id} | {e.human_label} | {v.label} | {_cell(v.reason, 50)} | "
                f"{_cell(e.output)} |"
            )
    if summary.n < 50:
        lines += [
            "",
            f"_Note: n={summary.n} is small; treat kappa and the intervals as rough._",
        ]
    return "\n".join(lines) + "\n"


def render_human_agreement(
    examples: Sequence[Example],
    summary: CalibrationSummary,
    dataset_name: str,
    *,
    rater_a: str = "human_a",
    rater_b: str = "human_b",
    synthetic: bool = False,
) -> str:
    """Markdown report for agreement between two human label columns (no judge)."""
    c = summary.confusion
    lines = [
        "# Human–human agreement report",
        "",
        f"- Dataset: `{dataset_name}` ({summary.n} examples)",
        f"- Raters: `{rater_a}` vs `{rater_b}`",
        f"- Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
    ]
    if synthetic:
        lines += [
            "",
            "> **Synthetic demo.** Labels are hand-written for format checks, not a study result.",
        ]
    lines += [
        "",
        "## Agreement",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Raw agreement | {_pct(summary.raw_agreement)} |",
        f"| Cohen's kappa | {summary.kappa:.3f} ({kappa_band(summary.kappa)}) |",
        f"| Kappa 95% CI (bootstrap) | {_kci(summary)} |",
        f"| {rater_a} pass rate | {_ci(summary.human_pass_rate)} |",
        f"| {rater_b} pass rate | {_ci(summary.judge_pass_rate)} |",
        "",
        f"## Confusion matrix (rows: {rater_a}, columns: {rater_b})",
        "",
        f"| | {rater_b} pass | {rater_b} fail |",
        "|---|---|---|",
        f"| **{rater_a} pass** | {c['pass']['pass']} | {c['pass']['fail']} |",
        f"| **{rater_a} fail** | {c['fail']['pass']} | {c['fail']['fail']} |",
        "",
        "## Disagreements",
        "",
    ]
    rows = [e for e in examples if e.human_b is not None and e.human_label != e.human_b]
    if not rows:
        lines.append(f"None. `{rater_a}` and `{rater_b}` matched on every example.")
    else:
        lines += [f"| id | {rater_a} | {rater_b} | output |", "|---|---|---|---|"]
        for e in rows:
            lines.append(f"| {e.id} | {e.human_label} | {e.human_b} | {_cell(e.output)} |")
    if summary.n < 50:
        lines += [
            "",
            f"_Note: n={summary.n} is small; treat kappa and the intervals as rough._",
        ]
    return "\n".join(lines) + "\n"
