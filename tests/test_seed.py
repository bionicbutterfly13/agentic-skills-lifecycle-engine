from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from asme.canonical import ContractError, sha256_bytes
from asme.contract import ApprovalRecord, LifecycleState
from asme.domain import load_declared_domain
from asme.seed import validate_seed_packet
from asme.workflow import EvolutionWorkflow
from asme.workspace import DomainWorkspace, WorkspaceLayout


def _page() -> str:
    return "\n".join(
        (
            "pattern_kind: success",
            'origin_observations: ["observation-1"]',
            "## Description",
            "Use a named reviewed observation.",
            "## Root cause",
            "The observation identified a reusable method.",
            "## Evidence",
            '- observation observation-1: "verified excerpt"',
            "## Solution",
            "Apply the reviewed method inside this declared domain.",
        )
    )


def _payload(*, visibility: str = "public") -> dict:
    return {
        "schema": "asme.observation-seed.v1",
        "domain_id": "seed-domain",
        "observations": [
            {
                "observation_id": "observation-1",
                "visibility": visibility,
                "pattern_name": "reviewed-method",
                "evidence": "The record contains a verified excerpt for reuse.",
                "page": _page(),
            }
        ],
        "index": "# Pattern index\n\n- reviewed-method\n",
        "log_entry": "seeded observation-1 into reviewed-method",
    }


def _domain(tmp_path: Path, *, visibility: str):
    tasks = tmp_path / "tasks.jsonl"
    answers = tmp_path / "answers.jsonl"
    tasks.write_text(
        "".join(
            json.dumps({"task_id": f"{split}-1", "input": split}) + "\n"
            for split in ("train", "validation", "test")
        ),
        encoding="utf-8",
    )
    answers.write_text(
        "".join(
            json.dumps(
                {
                    "task_id": f"{split}-1",
                    "split": split,
                    "expected": split,
                    "marker": f"marker-{split}",
                }
            )
            + "\n"
            for split in ("train", "validation", "test")
        ),
        encoding="utf-8",
    )
    prompt = tmp_path / "prompt.txt"
    extractor = tmp_path / "extractor"
    scorer = tmp_path / "scorer"
    prompt.write_text("{input}\n{active_skills}", encoding="utf-8")
    extractor.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    scorer.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    return load_declared_domain(
        domain_id="seed-domain",
        task_file=tasks,
        answer_file=answers,
        prompt_file=prompt,
        extractor_file=extractor,
        scorer_file=scorer,
        tool_profile={"mode": "none"},
        visibility=visibility,
    )


def test_named_public_observation_seed_is_structurally_valid(tmp_path: Path) -> None:
    packet = validate_seed_packet(
        json.dumps(_payload()).encode("utf-8"),
        domain=_domain(tmp_path, visibility="public"),
    )
    assert packet.observation_ids == ("observation-1",)
    assert packet.pages == {"reviewed-method": _page()}


def test_internal_observation_cannot_seed_public_domain(tmp_path: Path) -> None:
    with pytest.raises(ContractError, match="internal observation"):
        validate_seed_packet(
            json.dumps(_payload(visibility="internal")).encode("utf-8"),
            domain=_domain(tmp_path, visibility="public"),
        )


@pytest.mark.parametrize(
    "mutation,match",
    (
        (lambda value: value["observations"][0].update(evidence="unrelated"), "absent"),
        (lambda value: value.update(domain_id="another-domain"), "domain"),
        (lambda value: value.update(extra=True), "fields"),
    ),
)
def test_seed_packet_refuses_unbound_or_extra_content(
    tmp_path: Path, mutation, match: str
) -> None:
    payload = _payload()
    mutation(payload)
    with pytest.raises(ContractError, match=match):
        validate_seed_packet(
            json.dumps(payload).encode("utf-8"),
            domain=_domain(tmp_path, visibility="public"),
        )


def test_seed_transition_is_approved_single_use_and_reversible_before_baseline(
    tmp_path: Path,
) -> None:
    domain = _domain(tmp_path, visibility="public")
    workspace = DomainWorkspace(
        domain_id=domain.domain_id,
        layout=WorkspaceLayout.under(tmp_path / "workspace"),
    )
    workspace.initialize(domain=domain, max_iterations=1)
    workflow = EvolutionWorkflow(workspace)
    packet = json.dumps(_payload(), sort_keys=True).encode("utf-8")
    now = datetime(2026, 8, 31, tzinfo=timezone.utc)
    approval = ApprovalRecord(
        approval_id="seed-approval-1",
        phase="seed-observations",
        artifact_hashes={"seed_packet": sha256_bytes(packet)},
        runtime_id=None,
        destination=domain.domain_id,
        approved_at=now.isoformat(),
        expires_at=(now + timedelta(hours=1)).isoformat(),
        approver="Dr. Mani",
    )
    seeded = workflow.seed_observations(packet, approval=approval, now=now)
    assert seeded.state is LifecycleState.NEEDS_BASELINE_RUN
    assert seeded.seeded_observation_ids == ("observation-1",)
    wiki = workspace.engine.target_roots["wiki"]
    assert (wiki / "patterns/reviewed-method.md").is_file()
    stored_approval = json.loads(
        (workspace.engine.target_roots["runs"] / "0/seed-approval.json").read_text(
            encoding="utf-8"
        )
    )
    assert stored_approval["consumed"] is True
    with pytest.raises(ContractError):
        workflow.seed_observations(packet, approval=approval, now=now)

    rolled_back = workflow.rollback_seed()
    assert rolled_back.state is LifecycleState.NEEDS_OPTIONAL_SEED
    assert rolled_back.seed_decision is None
    assert not (wiki / "patterns/reviewed-method.md").exists()
