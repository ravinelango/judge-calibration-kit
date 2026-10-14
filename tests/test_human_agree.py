"""Human-to-human agreement mode (two label columns, no judge)."""

from __future__ import annotations

from pathlib import Path

from judge_calibration.cli import main
from judge_calibration.dataset import load_jsonl
from judge_calibration.metrics import summarize
from judge_calibration.report import render_human_agreement


def test_loads_human_a_and_human_b(tmp_path: Path) -> None:
    p = tmp_path / "d.jsonl"
    p.write_text(
        '{"id": "1", "input": "q", "output": "o", "human_a": "pass", "human_b": "fail"}\n'
        '{"id": "2", "input": "q2", "output": "o2", "human_a": "fail", "human_b": "fail"}\n',
        encoding="utf-8",
    )
    rows = load_jsonl(p, label_a_field="human_a", label_b_field="human_b")
    assert [r.human_label for r in rows] == ["pass", "fail"]
    assert [r.human_b for r in rows] == ["fail", "fail"]


def test_human_label_plus_human_b_still_works(tmp_path: Path) -> None:
    p = tmp_path / "d.jsonl"
    p.write_text(
        '{"input": "q", "output": "o", "human_label": "pass", "human_b": "pass"}\n',
        encoding="utf-8",
    )
    rows = load_jsonl(p)
    assert rows[0].human_label == "pass" and rows[0].human_b == "pass"


def test_agree_cli_and_report(tmp_path: Path) -> None:
    data = Path(__file__).resolve().parents[1] / "examples" / "synthetic_two_raters.jsonl"
    out = tmp_path / "agree.md"
    js = tmp_path / "agree.json"
    rc = main(
        [
            "agree",
            "--data",
            str(data),
            "--col-a",
            "human_a",
            "--col-b",
            "human_b",
            "--out",
            str(out),
            "--json",
            str(js),
            "--synthetic",
        ]
    )
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "Human–human agreement" in text
    assert "Synthetic demo" in text
    assert "human_a" in text and "human_b" in text
    payload = js.read_text(encoding="utf-8")
    assert '"mode": "human_human"' in payload

    examples = load_jsonl(data, label_a_field="human_a", label_b_field="human_b")
    summary = summarize([e.human_label for e in examples], [e.human_b for e in examples])  # type: ignore[misc]
    md = render_human_agreement(examples, summary, data.name, synthetic=True)
    assert "Disagreements" in md
    # s04 and s07 disagree in the synthetic file
    assert "s04" in md and "s07" in md
