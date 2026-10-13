"""Agreement metrics between judge and human pass/fail labels."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

LABELS = ("pass", "fail")


@dataclass(frozen=True)
class Interval:
    point: float
    low: float
    high: float


def wilson_interval(successes: int, n: int, z: float = 1.959964) -> Interval:
    """Wilson score interval for a binomial proportion (95% by default)."""
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 <= successes <= n:
        raise ValueError("successes must be between 0 and n")
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return Interval(p, max(0.0, center - half), min(1.0, center + half))


def confusion_matrix(human: Sequence[str], judge: Sequence[str]) -> dict[str, dict[str, int]]:
    """Rows are human labels, columns are judge labels."""
    if len(human) != len(judge):
        raise ValueError("label sequences must be the same length")
    m = {h: {j: 0 for j in LABELS} for h in LABELS}
    for h, j in zip(human, judge, strict=True):
        m[h][j] += 1
    return m


def raw_agreement(human: Sequence[str], judge: Sequence[str]) -> float:
    if not human:
        raise ValueError("need at least one label")
    return sum(h == j for h, j in zip(human, judge, strict=True)) / len(human)


def cohens_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """Cohen's kappa for two raters. Returns 1.0 when both raters are constant and agree."""
    n = len(human)
    po = raw_agreement(human, judge)
    pe = sum((human.count(lab) / n) * (judge.count(lab) / n) for lab in LABELS)
    if pe == 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


@dataclass(frozen=True)
class CalibrationSummary:
    n: int
    raw_agreement: float
    kappa: float
    confusion: dict[str, dict[str, int]]
    human_pass_rate: Interval
    judge_pass_rate: Interval


def summarize(human: Sequence[str], judge: Sequence[str]) -> CalibrationSummary:
    n = len(human)
    return CalibrationSummary(
        n=n,
        raw_agreement=raw_agreement(human, judge),
        kappa=cohens_kappa(human, judge),
        confusion=confusion_matrix(human, judge),
        human_pass_rate=wilson_interval(list(human).count("pass"), n),
        judge_pass_rate=wilson_interval(list(judge).count("pass"), n),
    )
