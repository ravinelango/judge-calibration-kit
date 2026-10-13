"""Command line entry point: jck run --data FILE --judge mock --out report.md"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .dataset import load_jsonl
from .judges import get_judge
from .metrics import summarize
from .report import render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jck", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="judge a labeled dataset and write a report")
    run.add_argument("--data", required=True, type=Path)
    run.add_argument("--judge", default="mock", help="mock | openai[:model] | anthropic[:model]")
    run.add_argument("--out", type=Path, help="markdown report path (default: stdout)")
    run.add_argument("--json", type=Path, help="optional machine-readable summary")
    run.add_argument("--synthetic", action="store_true", help="label the report as a demo")
    args = parser.parse_args(argv)

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
                    "judge": judge.name,
                    "n": summary.n,
                    "raw_agreement": summary.raw_agreement,
                    "kappa": summary.kappa,
                    "confusion": summary.confusion,
                    "synthetic": args.synthetic,
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
