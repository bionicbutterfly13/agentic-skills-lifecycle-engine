from __future__ import annotations

from copy import deepcopy
import json

import pytest

from asme.canonical import ContractError, sha256_bytes
from asme.wiki import (
    TraceView,
    sample_traces,
    validate_maintainer_change,
    validate_pattern_multiset,
    validate_role_json,
)


def _page() -> str:
    return "\n".join(
        (
            "pattern_kind: paired",
            "## Description",
            "A recurring execution pattern.",
            "## Root cause",
            "The chosen step does not match the task.",
            "## Evidence",
            '- fail fail-1: "bad command"',
            '- pass pass-1: "good command"',
            "## Solution",
            "Use the verified command sequence.",
        )
    )


def _traces() -> tuple[TraceView, ...]:
    return (
        TraceView("fail-1", False, "the bad command failed", "a" * 64),
        TraceView("pass-1", True, "the good command passed", "b" * 64),
    )


def _payload() -> dict:
    return {
        "create_patterns": {"paired-pattern": _page()},
        "update_patterns": {},
        "update_index": "- paired-pattern\n",
        "append_log": "Created paired-pattern.\n",
        "attestation": {
            "input_hash": "c" * 64,
            "class_coverage": {
                "failure": {"represented_by": ["paired-pattern"]},
                "success": {"represented_by": ["paired-pattern"]},
            },
            "per_pattern": {
                "paired-pattern": {
                    "pattern_kind": "paired",
                    "failure_traces": ["fail-1"],
                    "success_traces": ["pass-1"],
                    "quoted_commands": [
                        {"trace": "fail-1", "outcome": "fail", "span": "bad command"},
                        {"trace": "pass-1", "outcome": "pass", "span": "good command"},
                    ],
                    "dedup_disposition": "new",
                    "dedup_reason": "No existing page covers both outcomes.",
                    "root_cause_reason": "The evidence supports the stated mechanism.",
                    "generalizable_because": "The decision applies across tasks.",
                }
            },
        },
    }


def test_hf_a13_sampling_uses_paper_limits_and_deterministic_local_order() -> None:
    records = [
        {
            "task_id": f"f-{index}",
            "passed": False,
            "content": "x" * 20_000,
            "source_hash": f"{index:064x}",
        }
        for index in range(8)
    ] + [
        {
            "task_id": f"p-{index}",
            "passed": True,
            "content": "ok",
            "source_hash": f"{index+20:064x}",
        }
        for index in range(5)
    ]
    sampled = sample_traces(tuple(reversed(records)))
    assert len([item for item in sampled if not item.passed]) == 5
    assert len([item for item in sampled if item.passed]) == 3
    assert len(sampled[0].content) == 15_000
    assert [item.task_id for item in sampled] == sorted(
        item.task_id for item in sampled if not item.passed
    ) + sorted(item.task_id for item in sampled if item.passed)


def test_hf_a15_valid_pattern_structure_and_attestation() -> None:
    change = validate_maintainer_change(
        payload=_payload(),
        traces=_traces(),
        maintainer_input_hash="c" * 64,
        existing_pages={},
    )
    assert change.pages["paired-pattern"] == _page()
    assert len(change.digest) == 64


def test_hf_a16_missing_class_blank_reason_duplicate_tuple_and_trailing_json() -> None:
    missing = _payload()
    del missing["attestation"]["class_coverage"]["success"]
    with pytest.raises(ContractError, match="every and only"):
        validate_maintainer_change(
            payload=missing,
            traces=_traces(),
            maintainer_input_hash="c" * 64,
            existing_pages={},
        )
    blank = _payload()
    blank["attestation"]["class_coverage"]["failure"] = {"not_used": "   "}
    with pytest.raises(ContractError, match="cannot be blank"):
        validate_maintainer_change(
            payload=blank,
            traces=_traces(),
            maintainer_input_hash="c" * 64,
            existing_pages={},
        )
    duplicate = _payload()
    duplicate["attestation"]["per_pattern"]["paired-pattern"]["quoted_commands"].append(
        deepcopy(
            duplicate["attestation"]["per_pattern"]["paired-pattern"]["quoted_commands"][0]
        )
    )
    with pytest.raises(ContractError, match="duplicate tuples"):
        validate_maintainer_change(
            payload=duplicate,
            traces=_traces(),
            maintainer_input_hash="c" * 64,
            existing_pages={},
        )
    with pytest.raises(ContractError, match="trailing"):
        validate_role_json(json.dumps({"ok": True}) + " {}")


def test_pattern_multiset_preserves_duplicate_counts() -> None:
    one = {"pattern_class": "failure", "evidence_id": "fail-1", "reason": "reason"}
    validate_pattern_multiset((one, one), (one, one))
    with pytest.raises(ContractError, match="multiset"):
        validate_pattern_multiset((one,), (one, one))


def test_patch_target_must_match_exactly_once() -> None:
    existing = {"paired-pattern": _page() + "\nrepeat repeat"}
    payload = _payload()
    payload["create_patterns"] = {}
    payload["update_patterns"] = {
        "paired-pattern": [{"op": "replace", "target": "repeat", "content": "new"}]
    }
    payload["attestation"]["per_pattern"]["paired-pattern"]["dedup_disposition"] = {
        "updates": "paired-pattern"
    }
    with pytest.raises(ContractError, match="exactly once"):
        validate_maintainer_change(
            payload=payload,
            traces=_traces(),
            maintainer_input_hash="c" * 64,
            existing_pages=existing,
        )
