"""Tests for jck disagreements export."""

import csv
import json
from pathlib import Path

from judge_calibration.cli import main
from judge_calibration.dataset import Example
from judge_calibration.judges import Verdict
from judge_calibration.report import disagreement_rows, write_disagreements_jsonl

EXAMPLE = Path(__file__).parents[1] / "examples" / "synthetic_support_answers.jsonl"


def test_disagreement_rows_filters_and_labels_direction():
    examples = [
        Example("a", "q", "good", "pass", rubric="be helpful"),
        Example("b", "q", "bad", "fail"),
        Example("c", "q", "ok", "pass"),
    ]
    verdicts = [
        Verdict("fail", "too short"),
        Verdict("pass", "looks fine"),
        Verdict("pass", "ok"),
    ]
    rows = disagreement_rows(examples, verdicts, synthetic=True)
    assert [r["id"] for r in rows] == ["a", "b"]
    assert rows[0]["direction"] == "too_strict" and rows[0]["human"] == "pass"
    assert rows[1]["direction"] == "too_lenient" and rows[1]["judge"] == "pass"
    assert rows[0]["criterion"] == "be helpful"
    assert rows[1]["synthetic"] is True
    assert "The output answers" in rows[1]["criterion"]  # default rubric


def test_cli_disagreements_writes_jsonl_and_csv(tmp_path, capsys):
    out = tmp_path / "triage" / "dis.jsonl"
    csv_path = tmp_path / "triage" / "dis.csv"
    rc = main(
        [
            "disagreements",
            "--data",
            str(EXAMPLE),
            "--judge",
            "mock",
            "--out",
            str(out),
            "--csv",
            str(csv_path),
            "--synthetic",
        ]
    )
    assert rc == 0
    printed = capsys.readouterr().out
    assert "disagreements=2" in printed
    lines = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
    assert len(lines) == 2
    assert {r["id"] for r in lines} == {"s05", "s08"}
    assert all(r["synthetic"] is True for r in lines)
    assert {r["direction"] for r in lines} == {"too_strict", "too_lenient"}
    with csv_path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2 and rows[0]["synthetic"] == "True"


def test_cli_disagreements_requires_an_output(capsys):
    assert main(["disagreements", "--data", str(EXAMPLE)]) == 2
    err = capsys.readouterr().err
    assert "jck disagreements: pass --out" in err


def test_write_disagreements_jsonl_empty_when_all_agree(tmp_path):
    examples = [Example("x", "q", "answer", "pass")]
    verdicts = [Verdict("pass", "ok")]
    path = tmp_path / "empty.jsonl"
    assert write_disagreements_jsonl(examples, verdicts, path) == 0
    assert path.read_text() == ""
