import json
from pathlib import Path

import pytest

from judge_calibration import __version__
from judge_calibration.cli import main

EXAMPLE = Path(__file__).parents[1] / "examples" / "synthetic_support_answers.jsonl"


def test_cli_end_to_end_with_mock(tmp_path):
    out, js = tmp_path / "r.md", tmp_path / "r.json"
    rc = main(
        [
            "run",
            "--data",
            str(EXAMPLE),
            "--judge",
            "mock",
            "--out",
            str(out),
            "--json",
            str(js),
            "--synthetic",
        ]
    )
    assert rc == 0
    md = out.read_text()
    assert "Cohen's kappa" in md and "Synthetic demo" in md and "## Disagreements" in md
    data = json.loads(js.read_text())
    assert "Kappa 95% CI" in md and "## By rubric criterion" in md and len(data["kappa_ci_95"]) == 2
    assert data["n"] == 10 and data["synthetic"] is True


def test_json_summary_creates_missing_parent_folder(tmp_path):
    js = tmp_path / "reports" / "nightly" / "r.json"
    rc = main(["run", "--data", str(EXAMPLE), "--out", str(tmp_path / "r.md"), "--json", str(js)])
    assert rc == 0
    text = js.read_text()
    assert text.endswith("\n") and json.loads(text)["mode"] == "judge"


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


def test_blank_label_is_a_data_error_not_a_traceback(tmp_path, capsys):
    data = tmp_path / "sheet.jsonl"
    data.write_text(
        '{"id": "s1", "input": "q", "output": "a", "human_label": "pass"}\n'
        '{"id": "s2", "input": "q", "output": "a", "human_label": ""}\n',
        encoding="utf-8",
    )
    assert main(["run", "--data", str(data)]) == 1
    err = capsys.readouterr().err
    assert err.startswith("jck run: line 2:")
    assert "Traceback" not in err


def test_version_flag_prints_package_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"jck {__version__}"


def test_run_min_kappa_gate_exit_codes(tmp_path, capsys):
    base = ["run", "--data", str(EXAMPLE), "--out", str(tmp_path / "r.md")]
    js = tmp_path / "r.json"
    assert main([*base, "--json", str(js)]) == 0
    kappa = json.loads(js.read_text())["kappa"]
    assert main([*base, "--min-kappa", str(max(-1.0, kappa - 0.01))]) == 0
    if kappa < 0.99:
        assert main([*base, "--min-kappa", str(min(1.0, kappa + 0.01))]) == 1
        assert "below --min-kappa" in capsys.readouterr().err


def test_run_min_kappa_rejects_out_of_range():
    with pytest.raises(SystemExit) as exc:
        main(["run", "--data", str(EXAMPLE), "--min-kappa", "1.5"])
    assert exc.value.code == 2
