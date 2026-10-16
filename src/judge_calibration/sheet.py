"""Blank labeling sheets: export unlabeled outputs to CSV, read the filled sheet back.

A spreadsheet is the easiest place for a domain expert to label. `write_sheet` drops any
existing label or judge fields so the labeler works blind, optionally shuffles the row
order with a fixed seed, and leaves `human_label` and `fail_reason` empty. `read_sheet`
turns the filled CSV back into the JSONL rows the other commands expect and refuses to
silently skip rows that are still unlabeled.
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from .dataset import VALID_LABELS

SHEET_COLUMNS = ["id", "rubric", "input", "output", "human_label", "fail_reason", "notes"]


def _read_rows(path: str | Path) -> list[dict]:
    rows: list[dict] = []
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
            row.setdefault("id", str(line_no))
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no rows found")
    return rows


def write_sheet(src: str | Path, dest: str | Path, *, seed: int | None = None) -> int:
    """Write a blank CSV labeling sheet from a JSONL of outputs. Returns the row count."""
    rows = _read_rows(src)
    if seed is not None:
        random.Random(seed).shuffle(rows)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "id": row["id"],
                    "rubric": row.get("rubric") or "",
                    "input": row["input"],
                    "output": row["output"],
                    "human_label": "",
                    "fail_reason": "",
                    "notes": "",
                }
            )
    return len(rows)


def read_sheet(path: str | Path, *, allow_unlabeled: bool = False) -> list[dict]:
    """Read a filled CSV sheet into JSONL-ready dicts.

    Raises if any label is not pass/fail, or if rows are unlabeled and
    `allow_unlabeled` is False. With `allow_unlabeled`, blank rows are dropped.
    """
    out: list[dict] = []
    unlabeled: list[str] = []
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = {"id", "input", "output", "human_label"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: sheet is missing columns {sorted(missing)}")
        for row_no, row in enumerate(reader, start=2):
            label = (row.get("human_label") or "").strip().lower()
            if not label:
                unlabeled.append(row["id"])
                continue
            if label not in VALID_LABELS:
                raise ValueError(
                    f"row {row_no} (id {row['id']}): human_label must be pass/fail, "
                    f"got {row['human_label']!r}"
                )
            item = {
                "id": row["id"],
                "input": row["input"],
                "output": row["output"],
                "human_label": label,
            }
            if row.get("rubric"):
                item["rubric"] = row["rubric"]
            if row.get("fail_reason"):
                item["fail_reason"] = row["fail_reason"]
            if row.get("notes"):
                item["notes"] = row["notes"]
            out.append(item)
    if unlabeled and not allow_unlabeled:
        shown = ", ".join(unlabeled[:5]) + ("…" if len(unlabeled) > 5 else "")
        raise ValueError(f"{len(unlabeled)} row(s) still unlabeled: {shown}")
    if not out:
        raise ValueError(f"{path}: no labeled rows")
    return out
