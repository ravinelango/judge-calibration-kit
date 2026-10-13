"""Load labeled examples from JSONL."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

VALID_LABELS = {"pass", "fail"}


@dataclass(frozen=True)
class Example:
    id: str
    input: str
    output: str
    human_label: str
    rubric: str | None = None


def _norm_label(value: object, line_no: int) -> str:
    if isinstance(value, bool):
        return "pass" if value else "fail"
    label = str(value).strip().lower()
    if label not in VALID_LABELS:
        raise ValueError(f"line {line_no}: human_label must be pass/fail, got {value!r}")
    return label


def load_jsonl(path: str | Path) -> list[Example]:
    examples: list[Example] = []
    with open(path, encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {line_no}: invalid JSON ({exc.msg})") from exc
            for key in ("input", "output", "human_label"):
                if key not in row:
                    raise ValueError(f"line {line_no}: missing required field {key!r}")
            examples.append(
                Example(
                    id=str(row.get("id", line_no)),
                    input=str(row["input"]),
                    output=str(row["output"]),
                    human_label=_norm_label(row["human_label"], line_no),
                    rubric=row.get("rubric"),
                )
            )
    if not examples:
        raise ValueError(f"{path}: no examples found")
    return examples
