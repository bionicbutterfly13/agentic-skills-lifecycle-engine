from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from asme.canonical import ContractError
from asme.contract import LifecycleState, Route
from asme.impact import ImpactOutcome, create_impact
from asme.integration import (
    HYBRID_BENEFIT_DISPOSITIONS,
    build_observation_candidate,
    validate_skill_authoring,
)
from asme.lifecycle import DomainState
from asme.snapshot import Snapshot


def _skill() -> bytes:
    return b"""---
name: evidence-helper
description: Check source-bound claims before reuse. Use when a repeated task needs verified evidence and a clear refusal boundary.
version: 0.1.0
last_updated: 2026-08-31
---

# Evidence helper

## Triggers

1. A repeated task needs source-bound claim checks before reuse.
2. A reusable procedure needs a clear refusal boundary and evidence label.
"""


def test_hybrid_authoring_requires_version_date_and_concrete_triggers() -> None:
    metadata = validate_skill_authoring(_skill(), expected_name="evidence-helper")
    assert metadata.version == "0.1.0"
    assert metadata.last_updated == "2026-08-31"
    assert len(metadata.triggers) == 2

    for removed in (b"version: 0.1.0\n", b"last_updated: 2026-08-31\n"):
        with pytest.raises(ContractError):
            validate_skill_authoring(
                _skill().replace(removed, b""), expected_name="evidence-helper"
            )
    with pytest.raises(ContractError, match="Use when"):
        validate_skill_authoring(
            _skill().replace(b" Use when", b" Apply when"),
            expected_name="evidence-helper",
        )
    with pytest.raises(ContractError, match="two concrete triggers"):
        validate_skill_authoring(
            _skill().replace(
                b"2. A reusable procedure needs a clear refusal boundary and evidence label.\n",
                b"",
            ),
            expected_name="evidence-helper",
        )


def test_validated_export_emits_review_only_observation_candidate() -> None:
    snapshot = Snapshot.from_mapping(
        {
            "evidence-helper/SKILL.md": _skill(),
            "evidence-helper/PURPOSE.md": (
                b'origin_observations: ["observation-1"]\n'
                b"test_evaluation: passed\n"
            ),
        }
    )
    impact = create_impact(
        domain_id="integration-domain",
        iteration=1,
        outcome=ImpactOutcome.ACCEPTED,
        active_before="a" * 64,
        candidate_snapshot=snapshot.snapshot_hash,
        active_after=snapshot.snapshot_hash,
        scores=(0.8, 0.8),
        unified_diff="-old\n+new\n",
    )
    state = DomainState(
        domain_id="integration-domain",
        seal="b" * 64,
        state=LifecycleState.DONE,
        active_snapshot_hash=snapshot.snapshot_hash,
        route=Route.VALIDATED,
        validated_step="exported",
        seeded_observation_ids=("observation-1",),
        test_manifests=(
            {"phase": "test-baseline", "manifest_hash": "c" * 64},
            {"phase": "test-final", "manifest_hash": "d" * 64},
        ),
        delivery_ledger=(
            {"delivery_id": "integration-domain__snapshot", "route": "validated"},
        ),
    )

    candidate = build_observation_candidate(
        state=state,
        snapshot=snapshot,
        skill_name="evidence-helper",
        impact_history=(impact,),
    )
    assert candidate.review_status == "pending_human_review"
    assert candidate.shared_log_write_allowed is False
    assert candidate.origin_observation_ids == ("observation-1",)
    assert candidate.accepted_impact_id == impact.entry_id
    assert candidate.digest
    assert "task_observer_path" not in candidate.as_mapping()

    with pytest.raises(ContractError, match="validated export"):
        build_observation_candidate(
            state=replace(state, route=Route.UNTESTED, validated_step=None),
            snapshot=snapshot,
            skill_name="evidence-helper",
            impact_history=(impact,),
        )


def test_hybrid_benefit_dispositions_cover_both_bridges_and_retained_ownership() -> None:
    assert tuple(HYBRID_BENEFIT_DISPOSITIONS) == (
        "live_reusable_signal_observation",
        "reviewed_observation_seed",
        "create_patch_no_action",
        "version_date_trigger_authoring",
        "verified_reusable_content",
        "current_research",
        "confidence_and_clustering",
        "deprecation_and_archival",
        "wikiskill_observation_candidate",
        "delivery_hygiene",
    )
    assert HYBRID_BENEFIT_DISPOSITIONS["live_reusable_signal_observation"] == (
        "task_observer_owned"
    )
    assert HYBRID_BENEFIT_DISPOSITIONS["wikiskill_observation_candidate"] == (
        "explicit_review_only_output_bridge"
    )


def test_public_integration_contract_preserves_every_hybrid_benefit() -> None:
    root = Path(__file__).parents[1]
    text = (root / "references" / "integration.md").read_text(encoding="utf-8")

    for benefit, disposition in HYBRID_BENEFIT_DISPOSITIONS.items():
        assert f"`{benefit}`" in text
        assert f"`{disposition}`" in text

    assert "asme observation-candidate" in text
    assert "pending_human_review" in text
    assert "shared_log_write_allowed" in text
    assert "immediate authoring" in text
    assert "declared-task evolution" in text
    assert "~/.config/agent-memory" not in text


def test_public_templates_require_hybrid_authoring_and_seed_provenance() -> None:
    root = Path(__file__).parents[1]
    skill_template = (root / "assets" / "SKILL.md.tmpl").read_text(
        encoding="utf-8"
    )
    purpose_template = (root / "assets" / "PURPOSE.md.tmpl").read_text(
        encoding="utf-8"
    )

    for field in ("name: ", "description: ", "version: ", "last_updated: "):
        assert skill_template.count(field) == 1
    assert "Use when" in skill_template
    assert skill_template.count("## Triggers") == 1
    assert "1. " in skill_template
    assert "2. " in skill_template
    assert "origin_observations:" in purpose_template
    assert "canonical JSON array" in purpose_template


def test_authoring_accepts_task_observer_date_alias() -> None:
    aliased = _skill().replace(b"last_updated: 2026-08-31\n", b"date: 2026-08-31\n")
    metadata = validate_skill_authoring(aliased, expected_name="evidence-helper")
    assert metadata.last_updated == "2026-08-31"
    with pytest.raises(ContractError, match="ISO calendar date"):
        validate_skill_authoring(
            _skill().replace(
                b"last_updated: 2026-08-31\n", b"date: 31 Aug 2026\n"
            ),
            expected_name="evidence-helper",
        )


def test_authoring_refuses_both_or_neither_date_field() -> None:
    both = _skill().replace(
        b"last_updated: 2026-08-31\n",
        b"last_updated: 2026-08-31\ndate: 2026-08-31\n",
    )
    with pytest.raises(ContractError, match="exactly one"):
        validate_skill_authoring(both, expected_name="evidence-helper")
    neither = _skill().replace(b"last_updated: 2026-08-31\n", b"")
    with pytest.raises(ContractError):
        validate_skill_authoring(neither, expected_name="evidence-helper")
