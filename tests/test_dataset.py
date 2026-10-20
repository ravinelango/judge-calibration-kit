import pytest

from judge_calibration.dataset import load_jsonl


def test_loads_rows_and_normalizes_labels(tmp_path):
    p = tmp_path / "d.jsonl"
    p.write_text(
        '{"id": "a", "input": "q", "output": "x", "human_label": "PASS"}\n'
        "\n"
        '{"input": "q2", "output": "y", "human_label": false, "rubric": "r"}\n'
    )
    rows = load_jsonl(p)
    assert [r.human_label for r in rows] == ["pass", "fail"]
    assert rows[1].id == "3" and rows[1].rubric == "r"


def test_rejects_missing_field(tmp_path):
    p = tmp_path / "d.jsonl"
    p.write_text('{"input": "q", "human_label": "pass"}\n')
    with pytest.raises(ValueError, match="output"):
        load_jsonl(p)


def test_rejects_bad_label(tmp_path):
    p = tmp_path / "d.jsonl"
    p.write_text('{"input": "q", "output": "o", "human_label": "maybe"}\n')
    with pytest.raises(ValueError, match="pass/fail"):
        load_jsonl(p)


def test_expands_criteria_into_one_example_each(tmp_path):
    p = tmp_path / "d.jsonl"
    p.write_text(
        '{"id": "m1", "input": "q", "output": "o", "criteria": ['
        '{"name": "grounded", "rubric": "Claims match the source.",'
        ' "label": "pass", "human_b": "fail"},'
        '{"name": "tone", "label": false}]}\n'
        '{"id": "s1", "input": "q2", "output": "o2", "human_label": "pass"}\n'
    )
    rows = load_jsonl(p)
    assert [r.id for r in rows] == ["m1/grounded", "m1/tone", "s1"]
    assert [r.human_label for r in rows] == ["pass", "fail", "pass"]
    assert rows[0].rubric == "Claims match the source." and rows[0].human_b == "fail"
    assert rows[1].rubric == "tone" and rows[1].human_b is None


@pytest.mark.parametrize(
    "criteria, msg",
    [
        ("[]", "non-empty list"),
        ('[{"name": "a"}]', "needs 'name' and 'label'"),
        ('[{"name": "a", "label": "pass"}, {"name": "a", "label": "fail"}]', "repeated"),
        ('[{"name": "a", "label": "ok"}]', "pass/fail"),
    ],
)
def test_rejects_bad_criteria(tmp_path, criteria, msg):
    p = tmp_path / "d.jsonl"
    p.write_text('{"input": "q", "output": "o", "criteria": ' + criteria + "}\n")
    with pytest.raises(ValueError, match=msg):
        load_jsonl(p)
