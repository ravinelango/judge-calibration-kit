# Labeling guide

The judge is only as trustworthy as the human labels you compare it to. Use this guide
so labels are consistent and the agreement numbers mean something.

## Before you label
1. **Write the rubric first.** One or two sentences per criterion. If two people would
   read it differently, rewrite it.
2. **Use binary pass/fail.** Likert scales (1 to 5) are harder to label consistently and
   hide disagreement. Split a fuzzy criterion into several binary ones instead.
3. **Sample realistically.** Pull outputs from real traffic or a realistic test set,
   including the hard and edge cases, not only the easy ones.

## While you label
- Label **blind**: do not look at the judge's verdict first.
- Judge the output against the rubric, not against how you would have written it.
- When unsure, add a short note and come back; do not guess.
- Record a one-line reason for every **fail**. Those reasons become your error taxonomy.

## Quality checks
- Have a second person label a 20% overlap sample and compute human-to-human kappa. If
  humans disagree with each other, fix the rubric before blaming the judge.
- Re-label 10 random items a week later to check your own consistency.

## How many examples?
Start with about 50 to 100. The tool prints Wilson confidence intervals so you can see
how wide the uncertainty still is; with 10 examples it is very wide.

## Labeling in a spreadsheet
Most domain experts would rather label in a spreadsheet than edit JSONL. Export a blank
sheet from your unlabeled outputs, label it, then convert it back:

```bash
jck sheet --data outputs.jsonl --out labels.csv --seed 42
# fill human_label (pass/fail) and fail_reason in Excel / Sheets, export as CSV
jck import-sheet --sheet labels.csv --out my_labels.jsonl
```

`jck sheet` leaves out any existing label or judge fields so you label blind, and
`--seed` shuffles the rows so you do not label in the order the outputs were generated.
`jck import-sheet` fails if any row is still blank or has a label other than pass/fail;
pass `--allow-unlabeled` to keep only the rows you have finished.

## JSONL format
```json
{"id": "s01", "input": "...", "output": "...", "human_label": "pass", "rubric": "optional"}
```
