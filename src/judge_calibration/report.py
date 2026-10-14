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


def higher_kappa(a: CalibrationSummary, b: CalibrationSummary) -> str:
    """'a', 'b' or 'tie' (point estimates only; see the CIs before calling it a win)."""
    if a.kappa == b.kappa:
        return "tie"
    return "a" if a.kappa > b.kappa else "b"


def _overlap(a: CalibrationSummary, b: CalibrationSummary) -> bool | None:
    if a.kappa_ci is None or b.kappa_ci is None:
        return None
    return a.kappa_ci.low <= b.kappa_ci.high and b.kappa_ci.low <= a.kappa_ci.high


def render_ab(
    examples: Sequence[Example],
    verdicts_a: Sequence[Verdict],
    verdicts_b: Sequence[Verdict],
    summary_a: CalibrationSummary,
    summary_b: CalibrationSummary,
    judge_a: str,
    judge_b: str,
    dataset_name: str,
    synthetic: bool = False,
) -> str:
    """Side-by-side report for two judge configurations scored against the same human labels."""
    winner = higher_kappa(summary_a, summary_b)
    a_only = sum(
        e.human_label == va.label != vb.label
        for e, va, vb in zip(examples, verdicts_a, verdicts_b, strict=True)
    )
    b_only = sum(
        e.human_label == vb.label != va.label
        for e, va, vb in zip(examples, verdicts_a, verdicts_b, strict=True)
    )
    lines = [
        "# Judge A/B comparison report",
        "",
        f"- Dataset: `{dataset_name}` ({summary_a.n} examples, same human labels for both)",
        f"- Judge A: `{judge_a}`",
        f"- Judge B: `{judge_b}`",
        f"- Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
    ]
    if synthetic:
        lines += [
            "",
            "> **Synthetic demo.** The dataset is synthetic and mock judges are keyword "
            "heuristics, so these numbers only show the report format. They are not results.",
        ]
    lines += [
        "",
        "## Agreement with human labels",
        "",
        "| Metric | A | B |",
        "|---|---|---|",
        f"| Raw agreement | {_pct(summary_a.raw_agreement)} | {_pct(summary_b.raw_agreement)} |",
        f"| Cohen's kappa | {summary_a.kappa:.3f} ({kappa_band(summary_a.kappa)}) | "
        f"{summary_b.kappa:.3f} ({kappa_band(summary_b.kappa)}) |",
        f"| Kappa 95% CI (bootstrap) | {_kci(summary_a)} | {_kci(summary_b)} |",
        f"| Judge pass rate | {_ci(summary_a.judge_pass_rate)} | "
        f"{_ci(summary_b.judge_pass_rate)} |",
        f"| Too lenient (human fail, judge pass) | {summary_a.confusion['fail']['pass']} | "
        f"{summary_b.confusion['fail']['pass']} |",
        f"| Too strict (human pass, judge fail) | {summary_a.confusion['pass']['fail']} | "
        f"{summary_b.confusion['pass']['fail']} |",
        "",
        "## Verdict",
        "",
    ]
    if winner == "tie":
        lines.append("- Both judges have the same kappa against human labels.")
    else:
        name = judge_a if winner == "a" else judge_b
        lines.append(f"- Higher kappa: **{winner.upper()}** (`{name}`).")
    lines.append(
        f"- Items only A got right: {a_only}. Items only B got right: {b_only}."
    )
    overlap = _overlap(summary_a, summary_b)
    if overlap:
        lines.append(
            "- The kappa intervals overlap, so this sample does not show a reliable "
            "difference. Label more items before switching judges on this evidence alone."
        )
    lines += [
        "",
        "## Where A and B disagree",
        "",
    ]
    rows = [
        (e, va, vb)
        for e, va, vb in zip(examples, verdicts_a, verdicts_b, strict=True)
        if va.label != vb.label
    ]
    if not rows:
        lines.append("None. A and B gave the same verdict on every example.")
    else:
        lines += [
            "| id | human | A | B | closer to human | output |",
            "|---|---|---|---|---|---|",
        ]
        for e, va, vb in rows:
            closer = "A" if va.label == e.human_label else "B"
            lines.append(
                f"| {e.id} | {e.human_label} | {va.label} | {vb.label} | {closer} | "
                f"{_cell(e.output)} |"
            )
    if summary_a.n < 50:
        lines += [
            "",
            f"_Note: n={summary_a.n} is small; treat kappa and the intervals as rough._",
        ]
    return "\n".join(lines) + "\n"
