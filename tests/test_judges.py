import pytest

from judge_calibration.dataset import Example
from judge_calibration.judges import MockJudge, build_prompt, get_judge, parse_verdict


def ex(output, rubric=None):
    return Example(id="1", input="q", output=output, human_label="pass", rubric=rubric)


def test_mock_is_deterministic():
    j = MockJudge()
    e = ex("This is a complete and careful answer.")
    assert j.judge(e) == j.judge(e)
    assert j.judge(e).label == "pass"


def test_mock_flags_markers_and_short_answers():
    assert MockJudge().judge(ex("It is guaranteed to work fine.")).label == "fail"
    assert MockJudge().judge(ex("Yes.")).label == "fail"


def test_parse_verdict():
    v = parse_verdict("FAIL: cites a source that does not exist")
    assert v.label == "fail" and "source" in v.reason
    assert parse_verdict("pass").label == "pass"
    with pytest.raises(ValueError):
        parse_verdict("unsure")


def test_prompt_uses_rubric():
    assert "Be brief" in build_prompt(ex("x", rubric="Be brief"))


def test_get_judge():
    assert get_judge("mock").name == "mock"
    with pytest.raises(ValueError):
        get_judge("nope")
