import pytest

from judge_calibration.metrics import (
    cohens_kappa,
    confusion_matrix,
    raw_agreement,
    summarize,
    wilson_interval,
)


def test_perfect_agreement():
    h = ["pass", "fail", "pass"]
    assert raw_agreement(h, h) == 1.0
    assert cohens_kappa(h, h) == pytest.approx(1.0)


def test_kappa_textbook_value():
    # 2x2 table: a=20 (pass/pass), b=5, c=10, d=15 -> po=0.7, pe=0.5, kappa=0.4
    h = ["pass"] * 25 + ["fail"] * 25
    j = ["pass"] * 20 + ["fail"] * 5 + ["pass"] * 10 + ["fail"] * 15
    assert raw_agreement(h, j) == pytest.approx(0.7)
    assert cohens_kappa(h, j) == pytest.approx(0.4)


def test_kappa_constant_raters():
    assert cohens_kappa(["pass"] * 3, ["pass"] * 3) == 1.0
    assert cohens_kappa(["pass"] * 3, ["fail"] * 3) == 0.0


def test_confusion_matrix_orientation():
    m = confusion_matrix(["pass", "fail"], ["fail", "fail"])
    assert m["pass"]["fail"] == 1 and m["fail"]["fail"] == 1 and m["pass"]["pass"] == 0


def test_wilson_known_value():
    ci = wilson_interval(8, 10)
    assert ci.point == 0.8
    assert ci.low == pytest.approx(0.4902, abs=1e-3)
    assert ci.high == pytest.approx(0.9433, abs=1e-3)


def test_wilson_edges_stay_in_bounds():
    assert wilson_interval(0, 5).low == 0.0
    assert wilson_interval(5, 5).high == 1.0
    with pytest.raises(ValueError):
        wilson_interval(1, 0)


def test_summarize():
    s = summarize(["pass", "fail"], ["pass", "pass"])
    assert s.n == 2 and s.judge_pass_rate.point == 1.0 and s.human_pass_rate.point == 0.5
