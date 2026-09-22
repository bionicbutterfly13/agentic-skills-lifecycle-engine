"""Direct runtime adapter for any OpenAI-compatible chat completions endpoint.

This adapter dispatches one prepared role job to a local or tunnelled model
server (Ollama, llama.cpp, vLLM, an LM Studio server, or a Colab-hosted
endpoint) and normalizes the reply into a CapturedExecution.

Honest capability boundaries, stated rather than assumed:

- Isolation is procedural for conversation and tool use, because a fresh HTTP
  request carries no prior turns and the request body declares no tools. It is
  not enforced: nothing in this adapter constrains the server process.
- Held-out answer and wiki isolation are enforced here in the sense that this
  adapter never reads either root and sends only the prompt text the core
  rendered. The capability report still labels them conservatively, because the
  adapter cannot prove what the server can reach.
- Trace fidelity is final_only for a domain with tool mode none. A chat
  completions response carries the final message; reasoning content, where the
  server exposes it, is recorded as a reasoning event and raises fidelity to
  observable_transcript only when tool events also exist.

The adapter never writes to a live skill root and performs no installation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Callable, Mapping
import urllib.error
import urllib.request

from asme.contract import (
    CapabilityEvidence,
    CapabilityReport,
    CapturedExecution,
    ContractError,
    TraceFidelity,
)

# Adapters may import only asme.contract (governance rule HF-A03), so the job is
# duck-typed: dispatch reads role_spec, digest, correlation_id, and
# capability_report_hash from the prepared AdapterJob the core hands over.
AdapterJob = Any

ADAPTER_ID = "direct"
ADAPTER_VERSION = "0.1.0"

DEFAULT_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_TIMEOUT_SECONDS = 1800.0


class DirectAdapterError(ContractError):
    """One dispatch against the configured endpoint could not be completed."""


class DirectAdapter:
    """Dispatch prepared jobs to an OpenAI-compatible chat completions endpoint."""

    adapter_id = ADAPTER_ID
    adapter_version = ADAPTER_VERSION

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        model_id: str,
        provider: str = "ollama",
        api_key: str | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_output_tokens: int = 4096,
        temperature: float = 0.0,
        seed: int | None = 0,
        transport: Callable[[urllib.request.Request], Mapping[str, Any]] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_id = model_id
        self._provider = provider
        self._api_key = api_key
        self._timeout = float(timeout_seconds)
        self._max_output_tokens = int(max_output_tokens)
        self._temperature = float(temperature)
        self._seed = seed
        self._server_version = "unknown"
        self._report: CapabilityReport | None = None
        self._transport = transport

    # -- capability -----------------------------------------------------

    def probe(self, *, refresh: bool = False) -> CapabilityReport:
        """Measure what this endpoint currently supports, without assuming.

        The report carries an observation timestamp, so its digest changes on
        every fresh measurement. A prepared job binds one exact digest, so the
        measured report is cached and reused for the dispatches bound to it.
        Pass refresh to force a new measurement.
        """

        if self._report is not None and not refresh:
            return self._report

        models_seen: tuple[str, ...] = ()
        reachable = False
        detail = ""
        try:
            payload = self._get("/models")
            entries = payload.get("data") if isinstance(payload, Mapping) else None
            if isinstance(entries, list):
                models_seen = tuple(
                    str(item.get("id"))
                    for item in entries
                    if isinstance(item, Mapping) and item.get("id")
                )
            reachable = True
            detail = f"{len(models_seen)} model(s) listed at {self._base_url}"
        except DirectAdapterError as exc:
            detail = f"model listing failed: {exc}"

        model_present = self._model_id in models_seen

        report = CapabilityReport.conservative(
            runtime_id=ADAPTER_ID,
            runtime_version=self._server_version,
            adapter_version=ADAPTER_VERSION,
            provider=self._provider,
            model_id=self._model_id,
            openai_backed=False,
            captured_events=("final_answer",),
            evidence=(
                CapabilityEvidence(
                    kind="endpoint_reachable",
                    detail=detail,
                    passed=reachable,
                ),
                CapabilityEvidence(
                    kind="model_present",
                    detail=(
                        f"{self._model_id} is served by this endpoint"
                        if model_present
                        else f"{self._model_id} is not in the endpoint model list"
                    ),
                    passed=model_present,
                ),
                CapabilityEvidence(
                    kind="fresh_session_per_request",
                    detail=(
                        "each dispatch opens one stateless chat completions request "
                        "carrying only the rendered prompt"
                    ),
                    passed=True,
                ),
                CapabilityEvidence(
                    kind="no_tool_surface_declared",
                    detail="request body declares no tools and no function schema",
                    passed=True,
                ),
                CapabilityEvidence(
                    kind="enforced_filesystem_isolation",
                    detail=(
                        "not established; the adapter does not constrain the server "
                        "process and cannot prove what it can reach"
                    ),
                    passed=False,
                ),
            ),
        )
        self._report = report
        return report

    # -- dispatch -------------------------------------------------------

    def dispatch(self, job: AdapterJob) -> CapturedExecution:
        """Run one prepared job in a fresh request and normalize the evidence."""

        capability = self._capability_for(job)
        prompt = job.role_spec.prompt_text
        started = datetime.now(timezone.utc).isoformat()
        body: dict[str, Any] = {
            "model": self._model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self._max_output_tokens,
            "temperature": self._temperature,
            "stream": False,
        }
        if self._seed is not None:
            body["seed"] = self._seed

        termination = "completed"
        try:
            payload = self._post("/chat/completions", body)
        except DirectAdapterError as exc:
            finished = datetime.now(timezone.utc).isoformat()
            return _captured_execution(
                execution_id=f"execution-{job.correlation_id}",
                runtime_id=ADAPTER_ID,
                runtime_version=self._server_version,
                adapter_version=ADAPTER_VERSION,
                job_spec_hash=job.digest,
                prompt_hash=_prompt_hash(job),
                active_snapshot_hash=_snapshot_hash(job),
                started=started,
                finished=finished,
                termination=f"transport_error: {exc}",
                events=(),
                returned_output="",
                capability=capability,
            )

        finished = datetime.now(timezone.utc).isoformat()
        message, finish_reason = _first_message(payload)
        text = str(message.get("content") or "")
        events: list[dict[str, Any]] = []
        reasoning = message.get("reasoning_content") or message.get("reasoning")
        if isinstance(reasoning, str) and reasoning.strip():
            events.append({"kind": "reasoning", "text": reasoning})
        events.append({"kind": "final_answer", "text": text})
        if finish_reason and finish_reason != "stop":
            termination = f"truncated: {finish_reason}"

        return _captured_execution(
            execution_id=f"execution-{job.correlation_id}",
            runtime_id=ADAPTER_ID,
            runtime_version=self._server_version,
            adapter_version=ADAPTER_VERSION,
            job_spec_hash=job.digest,
            prompt_hash=_prompt_hash(job),
            active_snapshot_hash=_snapshot_hash(job),
            started=started,
            finished=finished,
            termination=termination,
            events=tuple(events),
            returned_output=text,
            capability=capability,
        )

    def projection_files(self, *, canonical_hash: str) -> Mapping[str, bytes]:
        """Emit the deterministic staging record for this adapter."""

        record = {
            "adapter_id": ADAPTER_ID,
            "adapter_version": ADAPTER_VERSION,
            "base_url": self._base_url,
            "canonical_hash": canonical_hash,
            "model_id": self._model_id,
            "provider": self._provider,
            "installs": False,
        }
        blob = json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return {"direct-adapter.json": blob}

    # -- internals ------------------------------------------------------

    def _capability_for(self, job: AdapterJob) -> CapabilityReport:
        report = self.probe()
        if report.digest != job.capability_report_hash:
            raise DirectAdapterError(
                "job was prepared against a different capability report"
            )
        return report

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _get(self, path: str) -> Mapping[str, Any]:
        request = urllib.request.Request(
            f"{self._base_url}{path}", headers=self._headers(), method="GET"
        )
        return self._send(request)

    def _post(self, path: str, body: Mapping[str, Any]) -> Mapping[str, Any]:
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}{path}", data=data, headers=self._headers(), method="POST"
        )
        return self._send(request)

    def _send(self, request: urllib.request.Request) -> Mapping[str, Any]:
        if self._transport is not None:
            return self._transport(request)
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise DirectAdapterError(f"HTTP {exc.code} from {request.full_url}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise DirectAdapterError(f"transport failure: {exc}") from exc
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DirectAdapterError("endpoint returned malformed JSON") from exc
        if not isinstance(decoded, Mapping):
            raise DirectAdapterError("endpoint returned a non-object payload")
        return decoded


def _first_message(payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], str]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise DirectAdapterError("completion payload has no choices")
    first = choices[0]
    if not isinstance(first, Mapping):
        raise DirectAdapterError("completion choice is malformed")
    message = first.get("message")
    if not isinstance(message, Mapping):
        raise DirectAdapterError("completion choice has no message")
    return message, str(first.get("finish_reason") or "")


def _prompt_hash(job: AdapterJob) -> str:
    schema = job.role_spec.input_payload.get("expected_capture_schema")
    if not isinstance(schema, Mapping) or not schema.get("prompt_hash"):
        raise DirectAdapterError("prepared job carries no prompt hash")
    return str(schema["prompt_hash"])


def _snapshot_hash(job: AdapterJob) -> str:
    schema = job.role_spec.input_payload.get("expected_capture_schema")
    if not isinstance(schema, Mapping) or not schema.get("snapshot_hash"):
        raise DirectAdapterError("prepared job carries no snapshot hash")
    return str(schema["snapshot_hash"])


_FIDELITY_RANK = {
    TraceFidelity.UNKNOWN: 0,
    TraceFidelity.FINAL_ONLY: 1,
    TraceFidelity.OBSERVABLE_TRANSCRIPT: 2,
    TraceFidelity.PAPER_COMPLETE: 3,
}


def _classify_trace(events: tuple[Mapping[str, Any], ...], returned_output: str) -> TraceFidelity:
    """Mirror the core trace classifier without importing a non-contract module."""

    kinds = {str(event.get("kind") or event.get("event_type") or "") for event in events}
    if {"reasoning", "tool_call", "tool_output", "final_answer"}.issubset(kinds):
        return TraceFidelity.PAPER_COMPLETE
    if kinds & {"assistant_message", "tool_call", "tool_output"}:
        return TraceFidelity.OBSERVABLE_TRANSCRIPT
    if returned_output:
        return TraceFidelity.FINAL_ONLY
    return TraceFidelity.UNKNOWN


def _captured_execution(
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
    events: tuple[Mapping[str, Any], ...],
    returned_output: str,
    capability: CapabilityReport,
) -> CapturedExecution:
    """Build one CapturedExecution bound to the measured capability report."""

    fidelity = _classify_trace(events, returned_output)
    if _FIDELITY_RANK[fidelity] > _FIDELITY_RANK[capability.trace_fidelity]:
        raise ContractError("captured events exceed the measured capability report")
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
        returned_output_hash=hashlib.sha256(returned_output.encode("utf-8")).hexdigest(),
        trace_fidelity=fidelity,
        isolation_labels={
            "conversation": capability.conversation_isolation,
            "filesystem": capability.filesystem_isolation,
            "tool": capability.tool_isolation,
            "held_out_answer": capability.held_out_answer_isolation,
            "wiki": capability.wiki_isolation,
        },
        capability_report_hash=capability.digest,
    )
