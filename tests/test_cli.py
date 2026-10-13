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
    assert data["n"] == 10 and data["synthetic"] is True
