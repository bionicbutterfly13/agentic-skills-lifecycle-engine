#!/usr/bin/env python3
"""Build a LiveMathematicianBench domain cartridge for Lifecycle.

Usage:
    python scripts/build_livemath_cartridge.py --src <downloaded-json-dir> --out <cartridge-dir>

The source directory holds the dataset's per-month JSON files named lmb-<YYYYMM>.json,
downloaded from the Hugging Face dataset listed below.

Source: https://huggingface.co/datasets/LiveMathematicianBench/LiveMathematicianBench
Paper split shape (WikiSkill arXiv 2608.27454 Table 6): train 35, validation 18, test 124.

The source always labels the correct choice "A", so every item's options are
shuffled with a fixed seed before the expected label is recorded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

LABELS = ("A", "B", "C", "D", "E")
SPLIT_SIZES = {"train": 35, "validation": 18, "test": 124}


def load_rows(src: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(src.glob("lmb-2*.json")):
        for item in json.loads(path.read_text(encoding="utf-8")):
            rows.append(item)
    return rows


def build_item(row: dict, rng: random.Random) -> tuple[str, str]:
    """Return (rendered question with options, expected label)."""
    mcq = row["mcq"]
    options = [mcq["correct_choice"]["text"]] + [c["text"] for c in mcq["choices"]]
    if len(options) != len(LABELS):
        raise ValueError(f"row {row['no']} has {len(options)} options")
    order = list(range(len(options)))
    rng.shuffle(order)
    correct_position = order.index(0)
    expected = LABELS[correct_position]
    lines = [mcq["question"].strip(), ""]
    for label, idx in zip(LABELS, order):
        lines.append(f"{label}. {options[idx].strip()}")
    return "\n".join(lines), expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20260922)
    args = parser.parse_args()

    rows = load_rows(args.src)
    total = sum(SPLIT_SIZES.values())
    if len(rows) < total:
        raise SystemExit(f"need {total} rows, source has {len(rows)}")

    rng = random.Random(args.seed)
    # Deterministic selection: sort by a seeded digest of month+no, take the first 177.
    def key(row: dict) -> str:
        raw = f"{args.seed}:{row['month']}:{row['no']}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    selected = sorted(rows, key=key)[:total]

    tasks: list[dict] = []
    answers: list[dict] = []
    cursor = 0
    for split, size in SPLIT_SIZES.items():
        for n in range(size):
            row = selected[cursor]
            cursor += 1
            task_id = f"livemath-{split}-{n + 1:03d}"
            rendered, expected = build_item(row, rng)
            tasks.append({"input": rendered, "task_id": task_id})
            answers.append(
                {
                    "expected": expected,
                    "marker": f"lmbmark.{task_id}",
                    "split": split,
                    "task_id": task_id,
                }
            )

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "tasks.jsonl").open("w", encoding="utf-8") as handle:
        for item in tasks:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    with (args.out / "answers.jsonl").open("w", encoding="utf-8") as handle:
        for item in answers:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    (args.out / "cartridge.json").write_text(
        json.dumps(
            {
                "extractor": "../../../scripts/extractors/answer_tag.py",
                "scorer": "../../../scripts/scorers/exact_match.py",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (args.out / "prompt.txt").write_text(
        "You are an expert mathematical reasoning agent solving multiple-choice "
        "questions.\n\n"
        "{active_skills}\n\n"
        "## Task Format\n\n"
        "You will receive one mathematics multiple-choice question and its answer "
        "choices. Reason carefully about quantifiers, hypotheses, extremal wording, "
        "and exact equality conditions.\n\n"
        "## Answer Format\n\n"
        "Think step by step, then provide your final answer inside <answer>...</answer> "
        "tags. Inside the tags, output only the single choice label, such as A or C.\n\n"
        "Keep your reasoning short enough to reach the answer. If the question is hard, "
        "stop reasoning and commit to your best current choice rather than running out "
        "of room, because a response with no answer tag scores nothing.\n\n"
        "Example:\n\n<answer>B</answer>\n\n"
        "## Question\n\n{input}\n",
        encoding="utf-8",
    )
    counts: dict[str, int] = {}
    for item in answers:
        counts[item["expected"]] = counts.get(item["expected"], 0) + 1
    print(f"wrote {len(tasks)} tasks to {args.out}")
    print("expected-label distribution:", dict(sorted(counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
