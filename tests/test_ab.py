import json
from pathlib import Path

import pytest

from judge_calibration.cli import main
from judge_calibration.dataset import Example
from judge_calibration.judges import build_prompt, get_judge, load_prompt_template

EXAMPLE = Path(__file__).parents[1] / "examples" / "synthetic_support_answers.jsonl"


def ex(output):
    return Example(id="1", input="q", output=output, human_label="pass")


def test_strict_mock_is_stricter_than_mock():
    base, strict = get_judge("mock"), get_judge("mock:strict")
    assert strict.name == "mock:strict"
    promise = ex("The report is emailed to you every month without fail.")
    assert base.judge(promise).label == "pass" and strict.judge(promise).label == "fail"
    short = ex("Yes, it is encrypted.")
    assert base.judge(short).label == "pass" and strict.judge(short).label == "fail"
    with pytest.raises(ValueError):
        get_judge("mock:lenient")


def test_prompt_template_override(tmp_path):
    p = tmp_path / "p.txt"
    p.write_text("Grade strictly. {rubric}\nQ: {input}\nA: {output}\nPASS or FAIL:")
    tpl = load_prompt_template(p)
    prompt = build_prompt(ex("an answer"), tpl)
    assert prompt.startswith("Grade strictly.") and "A: an answer" in prompt
    (tmp_path / "bad.txt").write_text("no output placeholder {input}")
    with pytest.raises(ValueError, match="output"):
        load_prompt_template(tmp_path / "bad.txt")
    (tmp_path / "typo.txt").write_text("{output} {ouput}")
    with pytest.raises(ValueError, match="may only use"):
        load_prompt_template(tmp_path / "typo.txt")


def test_mock_rejects_prompt_template():
    with pytest.raises(ValueError, match="ignore prompts"):
        get_judge("mock", "{output}")


def test_cli_ab_end_to_end_mock_vs_strict(tmp_path):
    out, js = tmp_path / "ab.md", tmp_path / "ab.json"
    rc = main(["ab", "--data", str(EXAMPLE), "--judge-a", "mock", "--judge-b", "mock:strict",
               "--out", str(out), "--json", str(js), "--synthetic"])
    assert rc == 0
    md = out.read_text()
    assert "# Judge A/B comparison report" in md and "Synthetic demo" in md
    assert "## Where A and B disagree" in md and "| s08 | fail | pass | fail | B |" in md
    data = json.loads(js.read_text())
    assert data["mode"] == "ab" and data["synthetic"] is True and data["n"] == 10
    assert data["judge_a"] == "mock" and data["judge_b"] == "mock:strict"
    assert data["higher_kappa"] == "b" and data["a_b_disagreements"] == 1
    assert data["b"]["kappa"] > data["a"]["kappa"]
    assert len(data["a"]["kappa_ci_95"]) == 2 and len(data["b"]["kappa_ci_95"]) == 2


def test_cli_ab_same_judge_is_a_tie(tmp_path):
    js = tmp_path / "ab.json"
    main(["ab", "--data", str(EXAMPLE), "--judge-b", "mock", "--out", str(tmp_path / "ab.md"),
          "--json", str(js)])
    data = json.loads(js.read_text())
    assert data["higher_kappa"] == "tie" and data["a_b_disagreements"] == 0
    assert "None. A and B gave the same verdict" in (tmp_path / "ab.md").read_text()
