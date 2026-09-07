"""Versioned portable contracts and truthful capability labels."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, replace
from datetime import datetime, timezone
from enum import StrEnum
import re
from typing import Any, Mapping, Sequence

from .canonical import ContractError, hash_json, require_identifier


CONTRACT_VERSION = "asme.contract.v1"
ADAPTER_PORT_VERSION = "asme.adapter.v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")


class SourceClass(StrEnum):
    DIRECT = "DIRECT"
    GATE_A = "GATE_A"
    ARCHITECTURE = "ARCHITECTURE"
    PAPER = "PAPER"
    CODEX = "CODEX"
    RUNTIME = "RUNTIME"
    PLAN_PROPOSAL = "PLAN_PROPOSAL"
    TEST_EVIDENCE = "TEST_EVIDENCE"


class IsolationLevel(StrEnum):
    ENFORCED = "enforced"
    PROCEDURAL = "procedural"
    NONE = "none"
    UNKNOWN = "unknown"


class TraceFidelity(StrEnum):
    PAPER_COMPLETE = "paper_complete"
    OBSERVABLE_TRANSCRIPT = "observable_transcript"
    FINAL_ONLY = "final_only"
    UNKNOWN = "unknown"


class LifecycleState(StrEnum):
    UNINITIALIZED = "UNINITIALIZED"
    NEEDS_OPTIONAL_SEED = "NEEDS_OPTIONAL_SEED"
    NEEDS_BASELINE_RUN = "NEEDS_BASELINE_RUN"
    NEEDS_TRAIN_RUN = "NEEDS_TRAIN_RUN"
    NEEDS_WIKI = "NEEDS_WIKI"
    NEEDS_PROPOSAL = "NEEDS_PROPOSAL"
    NEEDS_VAL_RUN = "NEEDS_VAL_RUN"
    NEEDS_GATE = "NEEDS_GATE"
    NEEDS_VAL_CONFIRM = "NEEDS_VAL_CONFIRM"
    DONE = "DONE"


class Route(StrEnum):
    VALIDATED = "validated"
    UNTESTED = "untested"


class Role(StrEnum):
    INFERENCE = "inference"
    MAINTAINER = "maintainer"
    PROPOSER = "proposer"
    EXTRACTOR = "extractor"
    SCORER = "scorer"


@dataclass(frozen=True)
class RequirementRef:
    source_class: SourceClass
    source_locator: str
    decision_status: str
    supersedes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_locator.strip() or not self.decision_status.strip():
            raise ContractError("requirement provenance fields cannot be blank")


@dataclass(frozen=True)
class CapabilityEvidence:
    kind: str
    detail: str
    passed: bool | None
    evidence_hash: str | None = None


_PAPER_EVENTS = frozenset({"reasoning", "tool_call", "tool_output", "final_answer"})


@dataclass(frozen=True)
class CapabilityReport:
    runtime_id: str
    runtime_version: str
    adapter_version: str
    observed_at: str
    model_provider: str
    model_id: str
    provider_is_openai_backed: bool
    conversation_isolation: IsolationLevel
    filesystem_isolation: IsolationLevel
    tool_isolation: IsolationLevel
    held_out_answer_isolation: IsolationLevel
    wiki_isolation: IsolationLevel
    trace_fidelity: TraceFidelity
    captured_events: tuple[str, ...]
    approval_surface: tuple[str, ...] = ()
    write_roots: tuple[str, ...] = ()
    network_policy: str = "unknown"
    claims_allowed: tuple[str, ...] = ()
    claims_forbidden: tuple[str, ...] = ()
    evidence: tuple[CapabilityEvidence, ...] = ()
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        require_identifier(self.runtime_id, field="runtime_id")
        if self.trace_fidelity is TraceFidelity.PAPER_COMPLETE and not _PAPER_EVENTS.issubset(
            self.captured_events
        ):
            missing = sorted(_PAPER_EVENTS - set(self.captured_events))
            raise ContractError(f"paper_complete trace is missing events: {missing}")
        isolation = (
            self.conversation_isolation,
            self.filesystem_isolation,
            self.tool_isolation,
            self.held_out_answer_isolation,
            self.wiki_isolation,
        )
        if "unseen" in self.claims_allowed and (
            self.held_out_answer_isolation is not IsolationLevel.ENFORCED
            or self.wiki_isolation is not IsolationLevel.ENFORCED
        ):
            raise ContractError("unseen requires enforced held-out and wiki isolation")
        if any(level is not IsolationLevel.ENFORCED for level in isolation):
            if "sandboxed" in self.claims_allowed:
                raise ContractError("sandboxed claim requires every isolation dimension enforced")
            if "unsandboxed" not in self.claims_allowed:
                raise ContractError("non-enforced isolation must allow the unsandboxed label")
        fidelity_claims = {item.value for item in TraceFidelity}
        allowed_fidelity = fidelity_claims & set(self.claims_allowed)
        if allowed_fidelity != {self.trace_fidelity.value}:
            raise ContractError("claims_allowed must contain exactly the measured trace fidelity")

    @property
    def digest(self) -> str:
        return hash_json(asdict(self))

    @classmethod
    def conservative(
        cls,
        *,
        runtime_id: str,
        runtime_version: str,
        adapter_version: str,
        provider: str,
        model_id: str,
        openai_backed: bool,
        captured_events: Sequence[str],
        evidence: Sequence[CapabilityEvidence] = (),
    ) -> "CapabilityReport":
        captured = tuple(sorted(set(captured_events)))
        fidelity = (
            TraceFidelity.OBSERVABLE_TRANSCRIPT
            if {"tool_call", "tool_output", "final_answer"}.issubset(captured)
            else TraceFidelity.FINAL_ONLY
            if "final_answer" in captured
            else TraceFidelity.UNKNOWN
        )
        return cls(
            runtime_id=runtime_id,
            runtime_version=runtime_version,
            adapter_version=adapter_version,
            observed_at=datetime.now(timezone.utc).isoformat(),
            model_provider=provider,
            model_id=model_id,
            provider_is_openai_backed=openai_backed,
            conversation_isolation=IsolationLevel.PROCEDURAL,
            filesystem_isolation=IsolationLevel.UNKNOWN,
            tool_isolation=IsolationLevel.PROCEDURAL,
            held_out_answer_isolation=IsolationLevel.UNKNOWN,
            wiki_isolation=IsolationLevel.UNKNOWN,
            trace_fidelity=fidelity,
            captured_events=captured,
            claims_allowed=(fidelity.value, "unsandboxed"),
            claims_forbidden=tuple(
                sorted(({item.value for item in TraceFidelity} - {fidelity.value}) | {"sandboxed", "unseen"})
            ),
            evidence=tuple(evidence),
        )


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    phase: str
    artifact_hashes: Mapping[str, str]
    runtime_id: str | None
    destination: str | None
    approved_at: str
    expires_at: str
    approver: str
    consumed: bool = False

    def __post_init__(self) -> None:
        if not self.approval_id.strip() or not self.phase.strip() or not self.approver.strip():
            raise ContractError("approval identity, phase, and approver cannot be blank")
        for name, digest in self.artifact_hashes.items():
            if (
                not isinstance(name, str)
                or not name.strip()
                or not isinstance(digest, str)
                or _SHA256.fullmatch(digest) is None
            ):
                raise ContractError(
                    "approval artifacts require named lowercase hexadecimal SHA-256 digests"
                )
        approved = _aware_datetime(self.approved_at, field_name="approval time")
        expires = _aware_datetime(self.expires_at, field_name="approval expiry")
        if approved >= expires:
            raise ContractError("approval expiry must be after approval time")

    def validate_for(
        self,
        *,
        phase: str,
        artifact_hashes: Mapping[str, str],
        runtime_id: str | None = None,
        destination: str | None = None,
        now: datetime | None = None,
    ) -> None:
        if self.consumed:
            raise ContractError("approval record has already been consumed")
        if self.phase != phase or dict(self.artifact_hashes) != dict(artifact_hashes):
            raise ContractError("approval scope or artifact hash mismatch")
        if self.runtime_id != runtime_id or self.destination != destination:
            raise ContractError("approval runtime or destination mismatch")
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None or current.utcoffset() is None:
            raise ContractError("approval validation time must include timezone")
        approved = _aware_datetime(self.approved_at, field_name="approval time")
        expires = _aware_datetime(self.expires_at, field_name="approval expiry")
        if current < approved:
            raise ContractError("approval record is not active yet")
        if current >= expires:
            raise ContractError("approval record has expired")

    def consume(self) -> "ApprovalRecord":
        if self.consumed:
            raise ContractError("approval record has already been consumed")
        return replace(self, consumed=True)


@dataclass(frozen=True)
class CapturedExecution:
    execution_id: str
    runtime_id: str
    runtime_version: str
    adapter_version: str
    job_spec_hash: str
    prompt_hash: str
    active_snapshot_hash: str
    started: str
    finished: str
    termination: str
    captured_events: tuple[Mapping[str, Any], ...]
    returned_output: str
    returned_output_hash: str
    trace_fidelity: TraceFidelity
    isolation_labels: Mapping[str, IsolationLevel]
    capability_report_hash: str

    def __post_init__(self) -> None:
        from .canonical import sha256_bytes

        actual = sha256_bytes(self.returned_output.encode("utf-8"))
        if actual != self.returned_output_hash:
            raise ContractError("returned output is not bound to returned_output_hash")
        event_kinds = {
            str(event.get("kind") or event.get("event_type") or "")
            for event in self.captured_events
            if isinstance(event, Mapping)
        }
        if self.trace_fidelity is TraceFidelity.PAPER_COMPLETE and not _PAPER_EVENTS.issubset(
            event_kinds
        ):
            raise ContractError("paper_complete execution lacks required captured events")
        if self.trace_fidelity is TraceFidelity.FINAL_ONLY and "final_answer" not in event_kinds:
            raise ContractError("final_only execution lacks a captured final answer")


def capability_report_from_mapping(raw: Mapping[str, Any]) -> CapabilityReport:
    """Decode one exact capability record for CLI and adapter boundaries."""

    values = _exact_dataclass_values(raw, CapabilityReport, label="capability report")
    isolation_fields = (
        "conversation_isolation",
        "filesystem_isolation",
        "tool_isolation",
        "held_out_answer_isolation",
        "wiki_isolation",
    )
    try:
        for name in isolation_fields:
            values[name] = IsolationLevel(values[name])
        values["trace_fidelity"] = TraceFidelity(values["trace_fidelity"])
        for name in (
            "captured_events",
            "approval_surface",
            "write_roots",
            "claims_allowed",
            "claims_forbidden",
        ):
            values[name] = tuple(values[name])
        evidence = values["evidence"]
        if not isinstance(evidence, (list, tuple)):
            raise TypeError
        values["evidence"] = tuple(
            CapabilityEvidence(**dict(item)) for item in evidence
        )
        return CapabilityReport(**values)
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("capability report differs from the contract") from exc


def approval_record_from_mapping(raw: Mapping[str, Any]) -> ApprovalRecord:
    """Decode one exact approval record without broadening its scope."""

    values = _exact_dataclass_values(raw, ApprovalRecord, label="approval record")
    if not isinstance(values.get("artifact_hashes"), Mapping):
        raise ContractError("approval record artifact hashes must be an object")
    values["artifact_hashes"] = dict(values["artifact_hashes"])
    try:
        return ApprovalRecord(**values)
    except (TypeError, ValueError) as exc:
        raise ContractError("approval record differs from the contract") from exc


def captured_execution_from_mapping(raw: Mapping[str, Any]) -> CapturedExecution:
    """Decode one exact captured execution at the runtime adapter boundary."""

    values = _exact_dataclass_values(raw, CapturedExecution, label="captured execution")
    events = values.get("captured_events")
    labels = values.get("isolation_labels")
    if not isinstance(events, (list, tuple)) or not isinstance(labels, Mapping):
        raise ContractError("captured execution events or isolation labels are malformed")
    expected_labels = {
        "conversation",
        "filesystem",
        "tool",
        "held_out_answer",
        "wiki",
    }
    if set(labels) != expected_labels:
        raise ContractError("captured execution isolation labels differ from the contract")
    try:
        values["captured_events"] = tuple(dict(item) for item in events)
        values["trace_fidelity"] = TraceFidelity(values["trace_fidelity"])
        values["isolation_labels"] = {
            key: IsolationLevel(value) for key, value in labels.items()
        }
        return CapturedExecution(**values)
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("captured execution differs from the contract") from exc


@dataclass(frozen=True)
class RoleSpec:
    role: Role
    input_payload: Mapping[str, Any]
    prompt_text: str
    allowed_toolsets: tuple[str, ...]
    provider_allowlist: tuple[str, ...]
    model_allowlist: tuple[str, ...]
    output_schema: Mapping[str, Any]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.prompt_text.strip():
            raise ContractError("role prompt cannot be blank")
        for name, values in (
            ("allowed_toolsets", self.allowed_toolsets),
            ("provider_allowlist", self.provider_allowlist),
            ("model_allowlist", self.model_allowlist),
        ):
            if tuple(sorted(set(values))) != values:
                raise ContractError(f"{name} must be sorted and unique")
            if name != "allowed_toolsets" and not values:
                raise ContractError(f"{name} cannot be empty")
            if any(not value.strip() for value in values):
                raise ContractError(f"{name} cannot contain blank values")
        if not isinstance(self.input_payload, Mapping) or not isinstance(self.output_schema, Mapping):
            raise ContractError("role input and output schema must be mappings")

    @property
    def digest(self) -> str:
        return hash_json(asdict(self))


def _aware_datetime(value: str, *, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ContractError(f"{field_name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{field_name} must include timezone")
    return parsed


def _exact_dataclass_values(
    raw: Mapping[str, Any], record_type: type[Any], *, label: str
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ContractError(f"{label} must be an object")
    expected = {item.name for item in fields(record_type)}
    if set(raw) != expected:
        raise ContractError(
            f"{label} fields differ: missing={sorted(expected-set(raw))}, "
            f"extra={sorted(set(raw)-expected)}"
        )
    return dict(raw)
