from __future__ import annotations

from dataclasses import asdict
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from asme.adapter import DispatchRefused, ProviderPolicy, prepare_job
from asme.canonical import ContractError
from asme.contract import (
    ApprovalRecord,
    CapabilityReport,
    CapturedExecution,
    IsolationLevel,
    Role,
    TraceFidelity,
    approval_record_from_mapping,
    capability_report_from_mapping,
    captured_execution_from_mapping,
)
from asme.evidence import role_spec


def _report(events: tuple[str, ...]) -> CapabilityReport:
    return CapabilityReport.conservative(
        runtime_id="hermes",
        runtime_version="0.20.5",
        adapter_version="0.1.0",
        provider="openai-codex",
        model_id="gpt-test",
        openai_backed=True,
        captured_events=events,
    )


def test_hf_a05_capability_labels_never_exceed_captured_events() -> None:
    unknown = _report(())
    final = _report(("final_answer",))
    observable = _report(("tool_call", "tool_output", "final_answer"))
    assert unknown.trace_fidelity is TraceFidelity.UNKNOWN
    assert unknown.claims_allowed == ("unknown", "unsandboxed")
    assert final.trace_fidelity is TraceFidelity.FINAL_ONLY
    assert observable.trace_fidelity is TraceFidelity.OBSERVABLE_TRANSCRIPT
    with pytest.raises(ContractError):
        replace(unknown, claims_allowed=("paper_complete", "unsandboxed"))


def test_hf_a07_unseen_requires_enforced_answer_and_wiki_isolation() -> None:
    report = _report(("final_answer",))
    with pytest.raises(ContractError):
        replace(report, claims_allowed=("final_only", "unsandboxed", "unseen"))
    enforced = replace(
        report,
        conversation_isolation=IsolationLevel.ENFORCED,
        filesystem_isolation=IsolationLevel.ENFORCED,
        tool_isolation=IsolationLevel.ENFORCED,
        held_out_answer_isolation=IsolationLevel.ENFORCED,
        wiki_isolation=IsolationLevel.ENFORCED,
        claims_allowed=("final_only", "sandboxed", "unseen"),
    )
    assert "unseen" in enforced.claims_allowed


def test_hf_a06_role_tools_are_role_specific_and_sorted() -> None:
    spec = role_spec(
        role=Role.PROPOSER,
        payload={"train_outcomes": []},
        prompt_text="Propose one change.",
        allowed_toolsets=("read_file", "finish", "read_file"),
        provider_allowlist=("openai-codex",),
        model_allowlist=("gpt-test",),
        output_schema={"type": "object"},
    )
    assert spec.allowed_toolsets == ("finish", "read_file")
    inference = replace(spec, role=Role.INFERENCE, allowed_toolsets=())
    assert inference.allowed_toolsets == ()


def test_hf_a27_approval_is_hash_bound_expiring_and_single_use() -> None:
    now = datetime(2026, 8, 31, tzinfo=timezone.utc)
    approval = ApprovalRecord(
        approval_id="approval-1",
        phase="implementation",
        artifact_hashes={"contract": "a" * 64},
        runtime_id="hermes",
        destination="staging",
        approved_at=now.isoformat(),
        expires_at=(now + timedelta(hours=1)).isoformat(),
        approver="Dr. Mani",
    )
    approval.validate_for(
        phase="implementation",
        artifact_hashes={"contract": "a" * 64},
        runtime_id="hermes",
        destination="staging",
        now=now,
    )
    with pytest.raises(ContractError):
        approval.validate_for(
            phase="publication",
            artifact_hashes={"contract": "a" * 64},
            runtime_id="hermes",
            destination="staging",
            now=now,
        )
    consumed = approval.consume()
    with pytest.raises(ContractError):
        consumed.validate_for(
            phase="implementation",
            artifact_hashes={"contract": "a" * 64},
            runtime_id="hermes",
            destination="staging",
            now=now,
        )


def test_hf_a27_approval_rejects_future_activation_and_non_sha256_hashes() -> None:
    now = datetime(2026, 8, 31, tzinfo=timezone.utc)
    with pytest.raises(ContractError, match="lowercase hexadecimal SHA-256"):
        ApprovalRecord(
            approval_id="approval-invalid-hash",
            phase="implementation",
            artifact_hashes={"contract": "g" * 64},
            runtime_id="hermes",
            destination="staging",
            approved_at=now.isoformat(),
            expires_at=(now + timedelta(hours=1)).isoformat(),
            approver="Dr. Mani",
        )

    future = ApprovalRecord(
        approval_id="approval-not-active",
        phase="implementation",
        artifact_hashes={"contract": "a" * 64},
        runtime_id="hermes",
        destination="staging",
        approved_at=(now + timedelta(minutes=5)).isoformat(),
        expires_at=(now + timedelta(hours=1)).isoformat(),
        approver="Dr. Mani",
    )
    with pytest.raises(ContractError, match="not active"):
        future.validate_for(
            phase="implementation",
            artifact_hashes={"contract": "a" * 64},
            runtime_id="hermes",
            destination="staging",
            now=now,
        )


def test_adapter_job_requires_measured_exact_openai_route() -> None:
    report = _report(("final_answer",))
    spec = role_spec(
        role=Role.INFERENCE,
        payload={"task_id": "t"},
        prompt_text="Answer.",
        allowed_toolsets=(),
        provider_allowlist=("openai-codex",),
        model_allowlist=("gpt-test",),
        output_schema={"type": "string"},
    )
    job = prepare_job(
        adapter_id="hermes",
        adapter_version="0.1.0",
        report=report,
        role_spec=spec,
        policy=ProviderPolicy(("openai-codex",), ("gpt-test",)),
        correlation_id="job-1",
    )
    assert job.provider == "openai-codex"
    with pytest.raises(DispatchRefused):
        prepare_job(
            adapter_id="hermes",
            adapter_version="0.1.0",
            report=replace(report, provider_is_openai_backed=False),
            role_spec=spec,
            policy=ProviderPolicy(("openai-codex",), ("gpt-test",)),
            correlation_id="job-2",
        )


def test_cli_record_decoders_round_trip_exact_contracts() -> None:
    report = _report(("final_answer",))
    assert capability_report_from_mapping(asdict(report)) == report
    execution = CapturedExecution(
        execution_id="execution-1",
        runtime_id="hermes",
        runtime_version="0.20.5",
        adapter_version="0.1.0",
        job_spec_hash="a" * 64,
        prompt_hash="b" * 64,
        active_snapshot_hash="c" * 64,
        started="2026-08-31T00:00:00+00:00",
        finished="2026-08-31T00:00:01+00:00",
        termination="completed",
        captured_events=({"kind": "final_answer", "text": "ok"},),
        returned_output="ok",
        returned_output_hash="2689367b205c16ce32ed4200942b8b8b1e262dfc70d9bc9fbc77c49699a4f1df",
        trace_fidelity=TraceFidelity.FINAL_ONLY,
        isolation_labels={
            "conversation": IsolationLevel.PROCEDURAL,
            "filesystem": IsolationLevel.UNKNOWN,
            "tool": IsolationLevel.PROCEDURAL,
            "held_out_answer": IsolationLevel.UNKNOWN,
            "wiki": IsolationLevel.UNKNOWN,
        },
        capability_report_hash=report.digest,
    )
    assert captured_execution_from_mapping(asdict(execution)) == execution
    now = datetime(2026, 8, 31, tzinfo=timezone.utc)
    approval = ApprovalRecord(
        approval_id="approval-2",
        phase="seed-observations",
        artifact_hashes={"seed_packet": "d" * 64},
        runtime_id=None,
        destination="test-domain",
        approved_at=now.isoformat(),
        expires_at=(now + timedelta(hours=1)).isoformat(),
        approver="Dr. Mani",
    )
    assert approval_record_from_mapping(asdict(approval)) == approval


@pytest.mark.parametrize(
    "decoder",
    (
        capability_report_from_mapping,
        captured_execution_from_mapping,
        approval_record_from_mapping,
    ),
)
def test_cli_record_decoders_reject_partial_or_extra_objects(decoder) -> None:
    with pytest.raises(ContractError):
        decoder({"unexpected": True})
