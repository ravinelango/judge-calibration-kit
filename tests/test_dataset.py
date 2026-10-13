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
