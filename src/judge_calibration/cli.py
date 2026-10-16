"""Command line entry point: jck run / agree / ab / sheet / import-sheet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .dataset import load_jsonl
from .judges import get_judge, load_prompt_template
from .metrics import CalibrationSummary, summarize
from .report import higher_kappa, render, render_ab, render_human_agreement
from .sheet import read_sheet, write_sheet


def _cmd_run(args: argparse.Namespace) -> int:
    examples = load_jsonl(args.data)
    judge = get_judge(args.judge)
    verdicts = [judge.judge(e) for e in examples]
    summary = summarize([e.human_label for e in examples], [v.label for v in verdicts])
    md = render(examples, verdicts, summary, judge.name, args.data.name, args.synthetic)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        print(f"wrote {args.out}  kappa={summary.kappa:.3f}  agreement={summary.raw_agreement:.3f}")
    else:
        sys.stdout.write(md)
    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "mode": "judge",
                    "judge": judge.name,
                    "n": summary.n,
                    "raw_agreement": summary.raw_agreement,
                    "kappa": summary.kappa,
                    "kappa_ci_95": (
                        [summary.kappa_ci.low, summary.kappa_ci.high] if summary.kappa_ci else None
                    ),
                    "confusion": summary.confusion,
                    "synthetic": args.synthetic,
                },
                indent=2,
            )
        )
    return 0


def _cmd_agree(args: argparse.Namespace) -> int:
    examples = load_jsonl(
        args.data,
        label_a_field=args.col_a,
        label_b_field=args.col_b,
    )
    missing = [e.id for e in examples if e.human_b is None]
    if missing:
        raise SystemExit(
            f"human-to-human mode needs both '{args.col_a}' and '{args.col_b}' on every row; "
            f"missing {args.col_b} on: {', '.join(missing[:5])}"
            + ("…" if len(missing) > 5 else "")
        )
    summary = summarize(
        [e.human_label for e in examples],
        [e.human_b for e in examples],  # type: ignore[misc]
    )
    md = render_human_agreement(
        examples,
        summary,
        args.data.name,
        rater_a=args.col_a,
        rater_b=args.col_b,
        synthetic=args.synthetic,
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        print(
            f"wrote {args.out}  kappa={summary.kappa:.3f}  agreement={summary.raw_agreement:.3f} "
            f"({args.col_a} vs {args.col_b})"
        )
    else:
        sys.stdout.write(md)
    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "mode": "human_human",
                    "rater_a": args.col_a,
                    "rater_b": args.col_b,
                    "n": summary.n,
                    "raw_agreement": summary.raw_agreement,
                    "kappa": summary.kappa,
                    "kappa_ci_95": (
                        [summary.kappa_ci.low, summary.kappa_ci.high] if summary.kappa_ci else None
                    ),
                    "confusion": summary.confusion,
                    "synthetic": args.synthetic,
                },
                indent=2,
            )
        )
    return 0


def _summary_json(summary: CalibrationSummary) -> dict:
    return {
        "raw_agreement": summary.raw_agreement,
        "kappa": summary.kappa,
        "kappa_ci_95": [summary.kappa_ci.low, summary.kappa_ci.high] if summary.kappa_ci else None,
        "judge_pass_rate": summary.judge_pass_rate.point,
        "confusion": summary.confusion,
    }


def _cmd_ab(args: argparse.Namespace) -> int:
    examples = load_jsonl(args.data)
    human = [e.human_label for e in examples]
    sides = {}
    for side, spec, prompt_path in (
        ("a", args.judge_a, args.prompt_a),
        ("b", args.judge_b, args.prompt_b),
    ):
        template = load_prompt_template(prompt_path) if prompt_path else None
        judge = get_judge(spec, template)
        label = judge.name + (f" + {prompt_path.name}" if prompt_path else "")
        verdicts = [judge.judge(e) for e in examples]
        sides[side] = (label, verdicts, summarize(human, [v.label for v in verdicts]))
    (name_a, verdicts_a, sum_a), (name_b, verdicts_b, sum_b) = sides["a"], sides["b"]
    md = render_ab(
        examples, verdicts_a, verdicts_b, sum_a, sum_b, name_a, name_b, args.data.name,
        args.synthetic,
    )
    winner = higher_kappa(sum_a, sum_b)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        print(
            f"wrote {args.out}  kappa A={sum_a.kappa:.3f}  B={sum_b.kappa:.3f}  "
            f"higher={winner}"
        )
    else:
        sys.stdout.write(md)
    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "mode": "ab",
                    "judge_a": name_a,
                    "judge_b": name_b,
                    "n": sum_a.n,
                    "a": _summary_json(sum_a),
                    "b": _summary_json(sum_b),
                    "higher_kappa": winner,
                    "a_b_disagreements": sum(
                        va.label != vb.label for va, vb in zip(verdicts_a, verdicts_b, strict=True)
                    ),
                    "synthetic": args.synthetic,
                },
                indent=2,
            )
        )
    return 0


def _cmd_sheet(args: argparse.Namespace) -> int:
    n = write_sheet(args.data, args.out, seed=args.seed)
    print(f"wrote {args.out}  rows={n}  (labels blank; fill human_label with pass/fail)")
    return 0


def _cmd_import_sheet(args: argparse.Namespace) -> int:
    try:
        rows = read_sheet(args.sheet, allow_unlabeled=args.allow_unlabeled)
    except ValueError as exc:
        raise SystemExit(f"import-sheet: {exc}") from exc
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {args.out}  labeled={len(rows)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jck", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="judge a labeled dataset and write a report")
    run.add_argument("--data", required=True, type=Path)
    run.add_argument("--judge", default="mock", help="mock | openai[:model] | anthropic[:model]")
    run.add_argument("--out", type=Path, help="markdown report path (default: stdout)")
    run.add_argument("--json", type=Path, help="optional machine-readable summary")
    run.add_argument("--synthetic", action="store_true", help="label the report as a demo")
    run.set_defaults(func=_cmd_run)

    agree = sub.add_parser(
        "agree",
        help="compare two human label columns (no judge); measure inter-rater agreement",
    )
    agree.add_argument("--data", required=True, type=Path)
    agree.add_argument(
        "--col-a",
        default="human_a",
        help="JSONL field for rater A (also accepts human_label as fallback)",
    )
    agree.add_argument("--col-b", default="human_b", help="JSONL field for rater B")
    agree.add_argument("--out", type=Path, help="markdown report path (default: stdout)")
    agree.add_argument("--json", type=Path, help="optional machine-readable summary")
    agree.add_argument("--synthetic", action="store_true", help="label the report as a demo")
    agree.set_defaults(func=_cmd_agree)

    ab = sub.add_parser(
        "ab",
        help="compare two judge configurations (model and/or prompt) against the same labels",
    )
    ab.add_argument("--data", required=True, type=Path)
    ab.add_argument("--judge-a", default="mock", help="judge spec for A (default: mock)")
    ab.add_argument(
        "--judge-b", default="mock:strict", help="judge spec for B (default: mock:strict)"
    )
    ab.add_argument(
        "--prompt-a",
        type=Path,
        help="prompt template file for A (uses {rubric}, {input}, {output}); model judges only",
    )
    ab.add_argument("--prompt-b", type=Path, help="prompt template file for B")
    ab.add_argument("--out", type=Path, help="markdown report path (default: stdout)")
    ab.add_argument("--json", type=Path, help="optional machine-readable summary")
    ab.add_argument("--synthetic", action="store_true", help="label the report as a demo")
    ab.set_defaults(func=_cmd_ab)

    sheet = sub.add_parser(
        "sheet",
        help="write a blank CSV labeling sheet from a JSONL of outputs (labels hidden)",
    )
    sheet.add_argument("--data", required=True, type=Path, help="JSONL with input/output")
    sheet.add_argument("--out", required=True, type=Path, help="CSV sheet path")
    sheet.add_argument("--seed", type=int, help="shuffle row order with this seed")
    sheet.set_defaults(func=_cmd_sheet)

    imp = sub.add_parser("import-sheet", help="convert a filled CSV labeling sheet to JSONL")
    imp.add_argument("--sheet", required=True, type=Path)
    imp.add_argument("--out", required=True, type=Path, help="JSONL path for jck run/agree/ab")
    imp.add_argument(
        "--allow-unlabeled",
        action="store_true",
        help="drop blank rows instead of failing (for partial labeling passes)",
    )
    imp.set_defaults(func=_cmd_import_sheet)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
