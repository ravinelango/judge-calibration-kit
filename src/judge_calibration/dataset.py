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
    human_b: str | None = None


def _norm_label(value: object, line_no: int, field: str = "human_label") -> str:
    if isinstance(value, bool):
        return "pass" if value else "fail"
    label = str(value).strip().lower()
    if label not in VALID_LABELS:
        raise ValueError(f"line {line_no}: {field} must be pass/fail, got {value!r}")
    return label


def load_jsonl(
    path: str | Path,
    *,
    label_a_field: str = "human_label",
    label_b_field: str | None = "human_b",
) -> list[Example]:
    """Load examples. Primary label prefers `label_a_field`, then `human_a`, then `human_label`.

    When `label_b_field` is set and present on a row, it is stored as `human_b` for
    human-to-human agreement (no judge required).
    """
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
            for key in ("input", "output"):
                if key not in row:
                    raise ValueError(f"line {line_no}: missing required field {key!r}")

            primary = None
            primary_field = None
            for candidate in (label_a_field, "human_a", "human_label"):
                if candidate in row:
                    primary = row[candidate]
                    primary_field = candidate
                    break
            if primary is None:
                raise ValueError(
                    f"line {line_no}: missing label field "
                    f"({label_a_field!r} / 'human_a' / 'human_label')"
                )

            secondary = None
            if label_b_field and label_b_field in row:
                secondary = _norm_label(row[label_b_field], line_no, label_b_field)

            examples.append(
                Example(
                    id=str(row.get("id", line_no)),
                    input=str(row["input"]),
                    output=str(row["output"]),
                    human_label=_norm_label(primary, line_no, primary_field or "human_label"),
                    rubric=row.get("rubric"),
                    human_b=secondary,
                )
            )
    if not examples:
        raise ValueError(f"{path}: no examples found")
    return examples
