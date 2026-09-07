from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from asme.canonical import sha256_bytes, tree_manifest
from asme.cli import _parser, main
from asme.contract import ApprovalRecord
from asme.observer_bridge import (
    OBSERVER_REVIEW_PHASE,
    build_observer_review_packet,
    write_observer_review_packet,
)

_ASSETS = Path(__file__).resolve().parents[1] / "assets" / "eval"

_SKILL_MD = b"""---
name: demo-skill
description: Answer arithmetic prompts with one tagged number. Use when a task needs the declared answer-tag output contract.
version: 1.0.0
last_updated: 2026-09-01
---

# demo-skill

## Triggers

1. The task asks for a single numeric answer in answer tags.
2. The transcript shows repeated answer-tag formatting mistakes.
"""

_FILES = {"SKILL.md": _SKILL_MD, "PURPOSE.md": b"staged review candidate\n"}


def _packet_dir(tmp_path: Path) -> Path:
    approval = ApprovalRecord(
        approval_id="approval-1",
        phase=OBSERVER_REVIEW_PHASE,
        artifact_hashes={
            path: sha256_bytes(content) for path, content in _FILES.items()
        },
        runtime_id=None,
        destination="task-observer-review",
        approved_at="2026-09-01T00:00:00+00:00",
        expires_at="2026-09-02T00:00:00+00:00",
        approver="Dr. Mani",
    )
    packet = build_observer_review_packet(
        skill_name="demo-skill",
        skill_files=_FILES,
        approval=approval,
        now="2026-09-01T12:00:00+00:00",
    )
    target = tmp_path / "packet"
    write_observer_review_packet(packet, target)
    return target


def test_cli_exposes_eval_run_and_verify_packet() -> None:
    parser = _parser()
    subparsers = next(
        action
        for action in parser._actions
        if action.__class__.__name__ == "_SubParsersAction"
    )
    assert {"eval-run", "verify-packet"} <= set(subparsers.choices)


def test_eval_run_produces_byte_stable_accepted_report(
    capsys: pytest.CaptureFixture[str],
) -> None:
    command = [
        "eval-run",
        "--cartridge",
        str(_ASSETS / "arithmetic"),
        "--rollouts",
        str(_ASSETS / "arithmetic" / "rollouts" / "run-1"),
        "--run-id",
        "run-1",
        "--domain-id",
        "arithmetic",
        "--seed",
        "20260901",
    ]
    assert main(command) == 0
    first = capsys.readouterr().out
    report = json.loads(first)
    assert report["schema"] == "asme.eval-report.v1"
    (run,) = report["runs"]
    assert run["aggregates"] == {
        "baseline": 0.5,
        "validation": 0.75,
        "confirmation": 0.75,
    }
    assert run["a2_local_acceptance"]["allowed"] is True
    assert main(command) == 0
    assert capsys.readouterr().out == first


def test_eval_run_reports_flat_scores_as_not_accepted(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        main(
            [
                "eval-run",
                "--cartridge",
                str(_ASSETS / "echo"),
                "--rollouts",
                str(_ASSETS / "echo" / "rollouts" / "run-1"),
                "--run-id",
                "run-1",
                "--domain-id",
                "echo",
                "--seed",
                "20260901",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    (run,) = report["runs"]
    assert run["a2_local_acceptance"]["allowed"] is False
    assert (
        "strict_validation_and_confirmation_win_missing"
        in run["a2_local_acceptance"]["reasons"]
    )


def test_eval_run_refuses_missing_phase_and_unknown_task(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    partial = tmp_path / "partial"
    partial.mkdir()
    source = _ASSETS / "arithmetic" / "rollouts" / "run-1"
    shutil.copy(source / "baseline.jsonl", partial / "baseline.jsonl")
    shutil.copy(source / "validation.jsonl", partial / "validation.jsonl")
    command = [
        "eval-run",
        "--cartridge",
        str(_ASSETS / "arithmetic"),
        "--rollouts",
        str(partial),
        "--run-id",
        "run-1",
        "--domain-id",
        "arithmetic",
        "--seed",
        "1",
    ]
    assert main(command) == 2
    assert "asme:" in capsys.readouterr().err
    shutil.copy(source / "confirmation.jsonl", partial / "confirmation.jsonl")
    (partial / "baseline.jsonl").write_text(
        '{"returned_output": "<answer>4</answer>", "task_id": "unknown-1"}\n',
        encoding="utf-8",
    )
    assert main(command) == 2
    assert "unknown" in capsys.readouterr().err


def test_verify_packet_verifies_and_stays_read_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = _packet_dir(tmp_path)
    before = tree_manifest(target)
    assert main(["verify-packet", "--packet", str(target)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["verified"] is True
    assert result["skill_name"] == "demo-skill"
    assert result["approval_id"] == "approval-1"
    assert result["files_verified"] == 2
    assert tree_manifest(target) == before


def test_verify_packet_refuses_tampering_missing_manifest_and_extras(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = _packet_dir(tmp_path)
    (target / "skill" / "PURPOSE.md").write_bytes(b"tampered\n")
    assert main(["verify-packet", "--packet", str(target)]) == 2
    assert "differs" in capsys.readouterr().err

    (tmp_path / "fresh").mkdir()
    fresh = _packet_dir(tmp_path / "fresh")
    (fresh / "skill" / "EXTRA.md").write_bytes(b"unlisted\n")
    assert main(["verify-packet", "--packet", str(fresh)]) == 2
    assert "unlisted" in capsys.readouterr().err

    bare = tmp_path / "bare"
    bare.mkdir()
    assert main(["verify-packet", "--packet", str(bare)]) == 2
    assert "asme:" in capsys.readouterr().err
