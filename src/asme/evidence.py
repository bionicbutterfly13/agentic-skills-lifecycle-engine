"""Role boundaries, trace normalization, and captured-output binding."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable, Mapping, Sequence

from .canonical import ContractError, hash_json, sha256_bytes
from .contract import (
    CapabilityReport,
    CapturedExecution,
    IsolationLevel,
    Role,
    RoleSpec,
    TraceFidelity,
)
from .domain import AnswerRecord, TaskRecord


FORBIDDEN_ROLLOUT_FIELDS = frozenset(
    {"expected", "answer", "answer_path", "wiki", "wiki_path", "marker", "session_handle"}
)


def _assert_absent(payload: Mapping[str, Any], forbidden: Iterable[str]) -> None:
    found = sorted(set(payload) & set(forbidden))
    if found:
        raise ContractError(f"forbidden evidence fields present: {found}")


def rollout_payload(
    *,
    task: TaskRecord,
    rendered_prompt: str,
    active_skill: str,
    tool_profile: Mapping[str, Any],
    runtime_policy: Mapping[str, Any],
    expected_capture_schema: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "task_id": task.task_id,
        "input": task.input,
        "rendered_prompt": rendered_prompt,
        "active_skill": active_skill,
        "tool_profile": dict(tool_profile),
        "runtime_policy": dict(runtime_policy),
        "expected_capture_schema": dict(expected_capture_schema),
    }
    _assert_absent(payload, FORBIDDEN_ROLLOUT_FIELDS)
    return payload


def maintainer_payload(
    *, samples: Sequence[Mapping[str, Any]], wiki_pages: Mapping[str, str]
) -> dict[str, Any]:
    clean_samples: list[dict[str, Any]] = []
    for sample in samples:
        _assert_absent(sample, {"expected", "answer_path", "marker"})
        clean_samples.append(dict(sample))
    return {"samples": clean_samples, "wiki_pages": dict(wiki_pages)}


def proposer_payload(
    *,
    train_outcomes: Sequence[tuple[TaskRecord, AnswerRecord, str, float]],
    wiki_pages: Mapping[str, str],
    impact_history: Sequence[Mapping[str, Any]],
    active_skill: str,
) -> dict[str, Any]:
    outcomes: list[dict[str, Any]] = []
    for task, answer, returned_output, score in train_outcomes:
        if answer.split != "train":
            raise ContractError("Proposer may receive ground truth for train outcomes only")
        outcomes.append(
            {
                "task_id": task.task_id,
                "input": task.input,
                "expected": answer.expected,
                "returned_output": returned_output,
                "score": score,
            }
        )
    return {
        "train_outcomes": outcomes,
        "wiki_pages": dict(wiki_pages),
        "impact_history": [dict(item) for item in impact_history],
        "active_skill": active_skill,
    }


def role_spec(
    *,
    role: Role,
    payload: Mapping[str, Any],
    prompt_text: str,
    allowed_toolsets: Sequence[str],
    provider_allowlist: Sequence[str],
    model_allowlist: Sequence[str],
    output_schema: Mapping[str, Any],
) -> RoleSpec:
    if role in {Role.INFERENCE, Role.MAINTAINER}:
        _assert_absent(payload, {"expected", "answer_path", "marker"})
    return RoleSpec(
        role=role,
        input_payload=dict(payload),
        prompt_text=prompt_text,
        allowed_toolsets=tuple(sorted(set(allowed_toolsets))),
        provider_allowlist=tuple(sorted(set(provider_allowlist))),
        model_allowlist=tuple(sorted(set(model_allowlist))),
        output_schema=dict(output_schema),
    )


def classify_trace(events: Sequence[Mapping[str, Any]], returned_output: str) -> TraceFidelity:
    event_types = {
        str(event.get("kind") or event.get("event_type") or "") for event in events
    }
    if {"reasoning", "tool_call", "tool_output", "final_answer"}.issubset(event_types):
        return TraceFidelity.PAPER_COMPLETE
    if event_types & {"assistant_message", "tool_call", "tool_output"}:
        return TraceFidelity.OBSERVABLE_TRANSCRIPT
    if returned_output:
        return TraceFidelity.FINAL_ONLY
    return TraceFidelity.UNKNOWN


def captured_execution(
    *,
    execution_id: str,
    runtime_id: str,
    runtime_version: str,
    adapter_version: str,
    job_spec_hash: str,
    prompt_hash: str,
    active_snapshot_hash: str,
    started: str,
    finished: str,
    termination: str,
    events: Sequence[Mapping[str, Any]],
    returned_output: str,
    capability: CapabilityReport,
) -> CapturedExecution:
    fidelity = classify_trace(events, returned_output)
    rank = {
        TraceFidelity.UNKNOWN: 0,
        TraceFidelity.FINAL_ONLY: 1,
        TraceFidelity.OBSERVABLE_TRANSCRIPT: 2,
        TraceFidelity.PAPER_COMPLETE: 3,
    }
    if rank[fidelity] > rank[capability.trace_fidelity]:
        raise ContractError("captured events exceed the measured capability report")
    isolation = {
        "conversation": capability.conversation_isolation,
        "filesystem": capability.filesystem_isolation,
        "tool": capability.tool_isolation,
        "held_out_answer": capability.held_out_answer_isolation,
        "wiki": capability.wiki_isolation,
    }
    return CapturedExecution(
        execution_id=execution_id,
        runtime_id=runtime_id,
        runtime_version=runtime_version,
        adapter_version=adapter_version,
        job_spec_hash=job_spec_hash,
        prompt_hash=prompt_hash,
        active_snapshot_hash=active_snapshot_hash,
        started=started,
        finished=finished,
        termination=termination,
        captured_events=tuple(dict(event) for event in events),
        returned_output=returned_output,
        returned_output_hash=sha256_bytes(returned_output.encode("utf-8")),
        trace_fidelity=fidelity,
        isolation_labels=isolation,
        capability_report_hash=capability.digest,
    )


def job_hash(spec: RoleSpec | Mapping[str, Any]) -> str:
    return hash_json(asdict(spec) if isinstance(spec, RoleSpec) else dict(spec))
