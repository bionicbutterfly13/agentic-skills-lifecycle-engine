"""Runtime-neutral adapter port and pre-dispatch policy checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Mapping, Protocol, runtime_checkable

from .canonical import ContractError, hash_json, require_identifier
from .contract import ADAPTER_PORT_VERSION, CapabilityReport, CapturedExecution, Role, RoleSpec


class DispatchRefused(ContractError):
    """A runtime dispatch cannot satisfy the recorded route policy."""


@dataclass(frozen=True)
class ProviderPolicy:
    """Exact, explicitly approved provider and model allowlists."""

    providers: tuple[str, ...]
    models: tuple[str, ...]
    require_openai_backed: bool = True

    def __post_init__(self) -> None:
        if not self.providers or not self.models:
            raise ContractError("provider and model allowlists cannot be empty")
        if tuple(sorted(set(self.providers))) != self.providers:
            raise ContractError("provider allowlist must be sorted and unique")
        if tuple(sorted(set(self.models))) != self.models:
            raise ContractError("model allowlist must be sorted and unique")
        if any(not item.strip() for item in (*self.providers, *self.models)):
            raise ContractError("provider and model allowlist values cannot be blank")

    def validate(self, report: CapabilityReport) -> None:
        if report.model_provider not in self.providers:
            raise DispatchRefused("measured provider is outside the exact allowlist")
        if report.model_id not in self.models:
            raise DispatchRefused("measured model is outside the exact allowlist")
        if self.require_openai_backed and not report.provider_is_openai_backed:
            raise DispatchRefused("provider lacks verified OpenAI-backed evidence")


@dataclass(frozen=True)
class AdapterJob:
    """Hash-bound work request for one fresh runtime session."""

    adapter_id: str
    adapter_version: str
    runtime_id: str
    role_spec: RoleSpec
    capability_report_hash: str
    provider: str
    model: str
    correlation_id: str
    fresh_session_required: bool = True
    port_version: str = ADAPTER_PORT_VERSION

    def __post_init__(self) -> None:
        require_identifier(self.adapter_id, field="adapter_id")
        require_identifier(self.runtime_id, field="runtime_id")
        require_identifier(self.correlation_id, field="correlation_id")
        if not self.fresh_session_required:
            raise ContractError("WikiSkill roles require a fresh runtime session")
        if self.provider not in self.role_spec.provider_allowlist:
            raise ContractError("job provider is outside its role specification")
        if self.model not in self.role_spec.model_allowlist:
            raise ContractError("job model is outside its role specification")
        if len(self.capability_report_hash) != 64:
            raise ContractError("job requires a capability report SHA-256")
        if self.port_version != ADAPTER_PORT_VERSION:
            raise ContractError("job adapter port version differs from the core contract")

    @property
    def digest(self) -> str:
        return hash_json(asdict(self))


def adapter_job_from_mapping(raw: Mapping[str, Any]) -> AdapterJob:
    """Decode one complete prepared job before trusting its recorded digest."""

    if not isinstance(raw, Mapping):
        raise ContractError("prepared adapter job must be an object")
    expected = {item.name for item in fields(AdapterJob)}
    if set(raw) != expected:
        raise ContractError("prepared adapter job fields differ from the contract")
    values = dict(raw)
    role_raw = values.get("role_spec")
    if not isinstance(role_raw, Mapping):
        raise ContractError("prepared adapter job role specification is malformed")
    role_expected = {item.name for item in fields(RoleSpec)}
    if set(role_raw) != role_expected:
        raise ContractError("prepared role specification fields differ from the contract")
    role_values = dict(role_raw)
    try:
        role_values["role"] = Role(role_values["role"])
        for name in ("allowed_toolsets", "provider_allowlist", "model_allowlist"):
            role_values[name] = tuple(role_values[name])
        for name in ("input_payload", "output_schema", "metadata"):
            if not isinstance(role_values[name], Mapping):
                raise TypeError
            role_values[name] = dict(role_values[name])
        values["role_spec"] = RoleSpec(**role_values)
        return AdapterJob(**values)
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("prepared adapter job differs from the contract") from exc


def prepare_job(
    *,
    adapter_id: str,
    adapter_version: str,
    report: CapabilityReport,
    role_spec: RoleSpec,
    policy: ProviderPolicy,
    correlation_id: str,
) -> AdapterJob:
    """Bind a role request to measured capabilities before runtime dispatch."""

    policy.validate(report)
    if report.runtime_id != adapter_id:
        raise DispatchRefused("capability report runtime does not match adapter")
    if report.adapter_version != adapter_version:
        raise DispatchRefused("capability report adapter version is stale")
    if tuple(sorted(role_spec.provider_allowlist)) != policy.providers:
        raise DispatchRefused("role provider allowlist differs from active route policy")
    if tuple(sorted(role_spec.model_allowlist)) != policy.models:
        raise DispatchRefused("role model allowlist differs from active route policy")
    return AdapterJob(
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        runtime_id=report.runtime_id,
        role_spec=role_spec,
        capability_report_hash=report.digest,
        provider=report.model_provider,
        model=report.model_id,
        correlation_id=correlation_id,
    )


@runtime_checkable
class RuntimeAdapter(Protocol):
    """The only runtime behavior the core is permitted to call."""

    adapter_id: str
    adapter_version: str

    def probe(self) -> CapabilityReport:
        """Measure current runtime capability without claiming configuration as proof."""

    def dispatch(self, job: AdapterJob) -> CapturedExecution:
        """Run one prepared job in a fresh session and return normalized evidence."""

    def projection_files(self, *, canonical_hash: str) -> Mapping[str, bytes]:
        """Return deterministic adapter files for staging, never installation."""
