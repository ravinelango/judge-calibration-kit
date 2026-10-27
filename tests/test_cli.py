import json
from pathlib import Path

from judge_calibration.cli import main

EXAMPLE = Path(__file__).parents[1] / "examples" / "synthetic_support_answers.jsonl"


def test_cli_end_to_end_with_mock(tmp_path):
    out, js = tmp_path / "r.md", tmp_path / "r.json"
    rc = main(["run", "--data", str(EXAMPLE), "--judge", "mock", "--out", str(out),
               "--json", str(js), "--synthetic"])
    assert rc == 0
    md = out.read_text()
    assert "Cohen's kappa" in md and "Synthetic demo" in md and "## Disagreements" in md
    data = json.loads(js.read_text())
    assert "Kappa 95% CI" in md and "## By rubric criterion" in md and len(data["kappa_ci_95"]) == 2
    assert data["n"] == 10 and data["synthetic"] is True


def test_missing_input_file_is_a_usage_error(tmp_path, capsys):
    missing = tmp_path / "nope.jsonl"
    assert main(["run", "--data", str(missing)]) == 2
    err = capsys.readouterr().err
    assert "jck run: no such file:" in err
    assert "nope.jsonl" in err

    sheet = tmp_path / "nope.csv"
    out = tmp_path / "out.jsonl"
    assert main(["import-sheet", "--sheet", str(sheet), "--out", str(out)]) == 2
    assert "jck import-sheet: no such file:" in capsys.readouterr().err
    assert not out.exists()
