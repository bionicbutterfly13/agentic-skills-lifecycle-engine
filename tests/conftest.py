from __future__ import annotations

import json
from pathlib import Path

import pytest

from asme.domain import DeclaredDomain, load_declared_domain


@pytest.fixture
def declared_domain(tmp_path: Path) -> DeclaredDomain:
    tasks = tmp_path / "tasks.jsonl"
    answers = tmp_path / "answers.jsonl"
    task_rows = [
        {"task_id": "train-1", "input": "one"},
        {"task_id": "validation-1", "input": "two"},
        {"task_id": "test-1", "input": "three"},
    ]
    answer_rows = [
        {"task_id": "train-1", "split": "train", "expected": "1", "marker": "marker-train"},
        {"task_id": "validation-1", "split": "validation", "expected": "2", "marker": "marker-validation"},
        {"task_id": "test-1", "split": "test", "expected": "3", "marker": "marker-test"},
    ]
    tasks.write_text("".join(json.dumps(row) + "\n" for row in task_rows), encoding="utf-8")
    answers.write_text("".join(json.dumps(row) + "\n" for row in answer_rows), encoding="utf-8")
    prompt = tmp_path / "prompt.txt"
    extractor = tmp_path / "extractor"
    scorer = tmp_path / "scorer"
    prompt.write_text("Solve {input}\n", encoding="utf-8")
    extractor.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    scorer.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    extractor.chmod(0o700)
    scorer.chmod(0o700)
    return load_declared_domain(
        domain_id="test-domain",
        task_file=tasks,
        answer_file=answers,
        prompt_file=prompt,
        extractor_file=extractor,
        scorer_file=scorer,
        tool_profile={"mode": "none"},
    )


def write_program(path: Path, body: str) -> Path:
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(0o700)
    return path

