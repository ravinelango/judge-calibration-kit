import csv
from pathlib import Path

import pytest

from judge_calibration.cli import main
from judge_calibration.dataset import load_jsonl
from judge_calibration.sheet import read_sheet, write_sheet

EXAMPLE = Path(__file__).parents[1] / "examples" / "synthetic_support_answers.jsonl"


def _fill(path: Path, labels: dict[str, str]) -> None:
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
        fields = list(rows[0].keys())
    for row in rows:
        row["human_label"] = labels.get(row["id"], "")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_sheet_hides_existing_labels_and_keeps_all_rows(tmp_path):
    out = tmp_path / "sheet.csv"
    n = write_sheet(EXAMPLE, out)
    with open(out, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert n == len(rows) == len(load_jsonl(EXAMPLE))
    assert all(r["human_label"] == "" for r in rows)
    assert "judge" not in rows[0] and "human_b" not in rows[0]


def test_seed_shuffle_is_reproducible(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    write_sheet(EXAMPLE, a, seed=7)
    write_sheet(EXAMPLE, b, seed=7)
    assert a.read_text() == b.read_text()


def test_round_trip_through_cli_loads_as_dataset(tmp_path):
    sheet, out = tmp_path / "s.csv", tmp_path / "labeled.jsonl"
    assert main(["sheet", "--data", str(EXAMPLE), "--out", str(sheet), "--seed", "1"]) == 0
    ids = [e.id for e in load_jsonl(EXAMPLE)]
    _fill(sheet, {i: ("pass" if k % 2 else "FAIL") for k, i in enumerate(ids)})
    assert main(["import-sheet", "--sheet", str(sheet), "--out", str(out)]) == 0
    examples = load_jsonl(out)
    assert sorted(e.id for e in examples) == sorted(ids)
    assert {e.human_label for e in examples} == {"pass", "fail"}


def test_unlabeled_rows_fail_unless_allowed(tmp_path):
    sheet = tmp_path / "s.csv"
    write_sheet(EXAMPLE, sheet)
    first = load_jsonl(EXAMPLE)[0].id
    _fill(sheet, {first: "pass"})
    with pytest.raises(ValueError, match="still unlabeled"):
        read_sheet(sheet)
    rows = read_sheet(sheet, allow_unlabeled=True)
    assert [r["id"] for r in rows] == [first]


def test_bad_label_is_rejected(tmp_path):
    sheet = tmp_path / "s.csv"
    write_sheet(EXAMPLE, sheet)
    first = load_jsonl(EXAMPLE)[0].id
    _fill(sheet, {first: "maybe"})
    with pytest.raises(ValueError, match="pass/fail"):
        read_sheet(sheet, allow_unlabeled=True)


MULTI = Path(__file__).parents[1] / "examples" / "synthetic_multi_criteria.jsonl"


def test_criteria_rows_become_one_sheet_row_per_criterion(tmp_path):
    out = tmp_path / "sheet.csv"
    n = write_sheet(MULTI, out, seed=3)
    with open(out, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    expected = load_jsonl(MULTI)
    assert n == len(rows) == len(expected)
    assert {r["id"] for r in rows} == {e.id for e in expected}
    assert all(r["human_label"] == "" and r["rubric"] for r in rows)
    # criteria of one output stay together so the labeler reads it once
    bases = [r["id"].split("/")[0] for r in rows]
    assert bases == sorted(bases, key=bases.index)


def test_criteria_sheet_round_trips_through_import(tmp_path):
    out = tmp_path / "sheet.csv"
    write_sheet(MULTI, out)
    truth = {e.id: e.human_label for e in load_jsonl(MULTI)}
    _fill(out, truth)
    back = read_sheet(out)
    assert {r["id"]: r["human_label"] for r in back} == truth
    assert all("/" in r["id"] and r["rubric"] for r in back)
