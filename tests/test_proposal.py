from __future__ import annotations

import json
from pathlib import Path

import pytest

from asme.canonical import ContractError, sha256_bytes
from asme.proposal import validate_proposal
from asme.snapshot import Snapshot


def _active_snapshot(tmp_path: Path) -> Snapshot:
    root = tmp_path / "active"
    (root / "skill-a").mkdir(parents=True)
    (root / "skill-a/SKILL.md").write_text(
        "# Skill A\n\nUse exact evidence.\n", encoding="utf-8"
    )
    return Snapshot.from_directory(root)


def test_no_action_preserves_snapshot_without_four_trace_requirement(tmp_path: Path) -> None:
    active = _active_snapshot(tmp_path)
    context = b"proposer context"
    result = validate_proposal(
        json.dumps(
            {
                "action": "no_action",
                "context_hash": sha256_bytes(context),
                "reason": "No generalizable change is supported.",
                "trace_ids": [],
            }
        ),
        proposer_context=context,
        available_trace_ids=("t1", "t2", "t3"),
        active_snapshot=active,
        forbidden_markers=("held-out-marker",),
    )
    assert result.action == "no_action"
    assert result.snapshot == active


def test_changed_proposal_requires_four_unique_available_traces(tmp_path: Path) -> None:
    active = _active_snapshot(tmp_path)
    context = b"proposer context"
    proposal = {
        "action": "create",
        "context_hash": sha256_bytes(context),
        "reason": "Repeated failures support a new procedure.",
        "trace_ids": ["t1", "t2", "t3"],
        "skill_name": "skill-b",
        "files": {"SKILL.md": "# Skill B\n"},
    }
    with pytest.raises(ContractError, match="at least four"):
        validate_proposal(
            json.dumps(proposal),
            proposer_context=context,
            available_trace_ids=("t1", "t2", "t3", "t4"),
            active_snapshot=active,
            forbidden_markers=(),
        )
    proposal["trace_ids"] = ["t1", "t2", "t3", "missing"]
    with pytest.raises(ContractError, match="unavailable"):
        validate_proposal(
            json.dumps(proposal),
            proposer_context=context,
            available_trace_ids=("t1", "t2", "t3", "t4"),
            active_snapshot=active,
            forbidden_markers=(),
        )


def test_create_and_patch_change_exactly_one_skill(tmp_path: Path) -> None:
    active = _active_snapshot(tmp_path)
    context = b"proposer context"
    traces = ("t1", "t2", "t3", "t4")
    created = validate_proposal(
        json.dumps(
            {
                "action": "create",
                "context_hash": sha256_bytes(context),
                "reason": "Four traces support the new procedure.",
                "trace_ids": list(traces),
                "skill_name": "skill-b",
                "files": {
                    "SKILL.md": "# Skill B\n\nUse the verified procedure.\n",
                    "references/checks.md": "# Checks\n",
                },
            }
        ),
        proposer_context=context,
        available_trace_ids=traces,
        active_snapshot=active,
        forbidden_markers=(),
    )
    assert "skill-b/SKILL.md" in created.snapshot.content_map()
    assert created.snapshot.snapshot_hash != active.snapshot_hash

    patched = validate_proposal(
        json.dumps(
            {
                "action": "patch",
                "context_hash": sha256_bytes(context),
                "reason": "Four traces support a narrow correction.",
                "trace_ids": list(traces),
                "skill_name": "skill-a",
                "patches": [
                    {
                        "path": "SKILL.md",
                        "target": "Use exact evidence.",
                        "replacement": "Use exact, source-bound evidence.",
                    }
                ],
            }
        ),
        proposer_context=context,
        available_trace_ids=traces,
        active_snapshot=active,
        forbidden_markers=(),
    )
    assert b"source-bound" in patched.snapshot.content_map()["skill-a/SKILL.md"]
    assert patched.snapshot.content_map()["skill-a/SKILL.md"] != active.content_map()[
        "skill-a/SKILL.md"
    ]


def test_patch_refuses_ambiguous_target_and_marker_propagation(tmp_path: Path) -> None:
    active = _active_snapshot(tmp_path)
    context = b"proposer context"
    traces = ("t1", "t2", "t3", "t4")
    base = {
        "action": "patch",
        "context_hash": sha256_bytes(context),
        "reason": "Four traces support a narrow correction.",
        "trace_ids": list(traces),
        "skill_name": "skill-a",
    }
    duplicate = {
        **base,
        "patches": [
            {"path": "SKILL.md", "target": "e", "replacement": "E"}
        ],
    }
    with pytest.raises(ContractError, match="exactly once"):
        validate_proposal(
            json.dumps(duplicate),
            proposer_context=context,
            available_trace_ids=traces,
            active_snapshot=active,
            forbidden_markers=(),
        )
    marked = {
        **base,
        "patches": [
            {
                "path": "SKILL.md",
                "target": "Use exact evidence.",
                "replacement": "Use held-out-marker evidence.",
            }
        ],
    }
    with pytest.raises(ContractError, match="provenance marker"):
        validate_proposal(
            json.dumps(marked),
            proposer_context=context,
            available_trace_ids=traces,
            active_snapshot=active,
            forbidden_markers=("held-out-marker",),
        )


def test_seed_using_proposal_requires_exact_purpose_origin_provenance(
    tmp_path: Path,
) -> None:
    active = _active_snapshot(tmp_path)
    context = b"proposer context with named seed origins"
    traces = ("t1", "t2", "t3", "t4")
    proposal = {
        "action": "create",
        "context_hash": sha256_bytes(context),
        "reason": "Four traces and one reviewed seed support this procedure.",
        "trace_ids": list(traces),
        "origin_observation_ids": ["observation-1"],
        "skill_name": "seeded-skill",
        "files": {"SKILL.md": "# Seeded skill\n"},
    }
    with pytest.raises(ContractError, match="PURPOSE.md"):
        validate_proposal(
            json.dumps(proposal),
            proposer_context=context,
            available_trace_ids=traces,
            available_origin_observation_ids=("observation-1",),
            active_snapshot=active,
            forbidden_markers=(),
        )

    proposal["files"]["PURPOSE.md"] = (
        'origin_observations: ["observation-1"]\n'
        "Use the human-reviewed seed only with supporting train traces.\n"
    )
    created = validate_proposal(
        json.dumps(proposal),
        proposer_context=context,
        available_trace_ids=traces,
        available_origin_observation_ids=("observation-1",),
        active_snapshot=active,
        forbidden_markers=(),
    )
    assert created.origin_observation_ids == ("observation-1",)

    proposal["files"]["PURPOSE.md"] = (
        'origin_observations: ["observation-2"]\n'
        "Use the human-reviewed seed only with supporting train traces.\n"
    )
    with pytest.raises(ContractError, match="origin_observations"):
        validate_proposal(
            json.dumps(proposal),
            proposer_context=context,
            available_trace_ids=traces,
            available_origin_observation_ids=("observation-1",),
            active_snapshot=active,
            forbidden_markers=(),
        )
