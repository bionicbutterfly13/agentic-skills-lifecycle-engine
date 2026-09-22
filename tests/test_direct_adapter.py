"""Offline contract tests for the direct OpenAI-compatible runtime adapter."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping
import urllib.request

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "adapters"))

from direct import (  # noqa: E402
    ADAPTER_ID,
    ADAPTER_VERSION,
    DirectAdapter,
    DirectAdapterError,
)

from asme.adapter import ProviderPolicy, prepare_job  # noqa: E402
from asme.contract import Role, TraceFidelity  # noqa: E402
from asme.evidence import role_spec  # noqa: E402

MODEL = "test-model:4b"
PROVIDER = "ollama"
PROMPT_HASH = "a" * 64
SNAPSHOT_HASH = "b" * 64


class FakeTransport:
    """One scripted OpenAI-compatible endpoint, with a recorded request log."""

    def __init__(
        self,
        *,
        models: tuple[str, ...] = (MODEL,),
        content: str = "<answer>C</answer>",
        reasoning: str | None = None,
        finish_reason: str = "stop",
        fail_completion: bool = False,
    ) -> None:
        self.models = models
        self.content = content
        self.reasoning = reasoning
        self.finish_reason = finish_reason
        self.fail_completion = fail_completion
        self.requests: list[dict[str, Any]] = []

    def __call__(self, request: urllib.request.Request) -> Mapping[str, Any]:
        body = json.loads(request.data) if request.data else None
        self.requests.append({"url": request.full_url, "body": body})
        if request.full_url.endswith("/models"):
            return {"data": [{"id": name} for name in self.models]}
        if self.fail_completion:
            raise DirectAdapterError("scripted transport failure")
        message: dict[str, Any] = {"role": "assistant", "content": self.content}
        if self.reasoning is not None:
            message["reasoning_content"] = self.reasoning
        return {
            "choices": [{"message": message, "finish_reason": self.finish_reason}]
        }


def _adapter(transport: FakeTransport) -> DirectAdapter:
    return DirectAdapter(
        base_url="http://endpoint.invalid/v1",
        model_id=MODEL,
        provider=PROVIDER,
        transport=transport,
    )


def _job(adapter: DirectAdapter, report):
    policy = ProviderPolicy((PROVIDER,), (MODEL,), require_openai_backed=False)
    spec = role_spec(
        role=Role.INFERENCE,
        payload={
            "expected_capture_schema": {
                "prompt_hash": PROMPT_HASH,
                "snapshot_hash": SNAPSHOT_HASH,
                "required_output": "text",
            }
        },
        prompt_text="Answer the question.",
        allowed_toolsets=(),
        provider_allowlist=policy.providers,
        model_allowlist=policy.models,
        output_schema={"type": "string"},
    )
    return prepare_job(
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        report=report,
        role_spec=spec,
        policy=policy,
        correlation_id="baseline-0-task-1",
    )


def test_probe_reports_final_only_and_refuses_sandbox_claims() -> None:
    adapter = _adapter(FakeTransport())
    report = adapter.probe()
    assert report.runtime_id == ADAPTER_ID
    assert report.adapter_version == ADAPTER_VERSION
    assert report.trace_fidelity is TraceFidelity.FINAL_ONLY
    assert "unsandboxed" in report.claims_allowed
    assert "sandboxed" in report.claims_forbidden
    assert "unseen" in report.claims_forbidden
    assert report.provider_is_openai_backed is False


def test_probe_is_cached_so_the_job_digest_stays_stable() -> None:
    adapter = _adapter(FakeTransport())
    first = adapter.probe()
    second = adapter.probe()
    assert first.digest == second.digest
    refreshed = adapter.probe(refresh=True)
    assert refreshed.observed_at >= first.observed_at


def test_probe_records_a_missing_model_as_failed_evidence() -> None:
    adapter = _adapter(FakeTransport(models=("other-model",)))
    report = adapter.probe()
    present = {item.kind: item.passed for item in report.evidence}
    assert present["model_present"] is False
    assert present["endpoint_reachable"] is True


def test_dispatch_binds_output_hash_prompt_and_snapshot() -> None:
    transport = FakeTransport(content="<answer>C</answer>")
    adapter = _adapter(transport)
    report = adapter.probe()
    job = _job(adapter, report)

    execution = adapter.dispatch(job)

    assert execution.returned_output == "<answer>C</answer>"
    assert execution.prompt_hash == PROMPT_HASH
    assert execution.active_snapshot_hash == SNAPSHOT_HASH
    assert execution.job_spec_hash == job.digest
    assert execution.capability_report_hash == report.digest
    assert execution.termination == "completed"
    assert execution.trace_fidelity is TraceFidelity.FINAL_ONLY


def test_dispatch_sends_only_the_rendered_prompt_and_declares_no_tools() -> None:
    transport = FakeTransport()
    adapter = _adapter(transport)
    job = _job(adapter, adapter.probe())

    adapter.dispatch(job)

    completion = transport.requests[-1]["body"]
    assert completion["messages"] == [
        {"role": "user", "content": "Answer the question."}
    ]
    assert "tools" not in completion
    assert "functions" not in completion
    assert completion["stream"] is False


def test_dispatch_records_reasoning_as_an_event_when_the_server_exposes_it() -> None:
    transport = FakeTransport(reasoning="step one, step two")
    adapter = _adapter(transport)
    job = _job(adapter, adapter.probe())

    execution = adapter.dispatch(job)

    kinds = [event["kind"] for event in execution.captured_events]
    assert kinds == ["reasoning", "final_answer"]


def test_dispatch_marks_a_truncated_completion() -> None:
    transport = FakeTransport(finish_reason="length")
    adapter = _adapter(transport)
    job = _job(adapter, adapter.probe())

    execution = adapter.dispatch(job)

    assert execution.termination == "truncated: length"


def test_dispatch_returns_evidence_when_the_endpoint_fails() -> None:
    transport = FakeTransport(fail_completion=True)
    adapter = _adapter(transport)
    job = _job(adapter, adapter.probe())

    execution = adapter.dispatch(job)

    assert execution.returned_output == ""
    assert execution.termination.startswith("transport_error:")


def test_dispatch_refuses_a_job_bound_to_another_capability_report() -> None:
    adapter = _adapter(FakeTransport())
    adapter.probe()
    other = _adapter(FakeTransport(models=("other-model",)))
    mismatched_job = _job(other, other.probe())

    with pytest.raises(DirectAdapterError):
        adapter.dispatch(mismatched_job)


def test_projection_files_stage_a_record_and_never_install() -> None:
    adapter = _adapter(FakeTransport())
    files = adapter.projection_files(canonical_hash="c" * 64)
    assert set(files) == {"direct-adapter.json"}
    record = json.loads(files["direct-adapter.json"])
    assert record["installs"] is False
    assert record["adapter_id"] == ADAPTER_ID
    assert record["model_id"] == MODEL
