"""Domain workspace that composes lifecycle decisions with transactions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical import (
    ContractError,
    canonical_bytes,
    hash_json,
    require_identifier,
    require_regular_file,
    sha256_bytes,
    sha256_file,
)
from .cartridge import DomainCartridge, verify_cartridge_tree
from .clock import CanonicalClock
from .contract import LifecycleState, Route
from .domain import DeclaredDomain, declared_domain_from_mapping, verify_domain_seal
from .dependencies import default_dependency_matrix
from .lifecycle import DomainState, TransitionInput, transition
from .package import (
    Projection,
    archive_write_plan,
    ensure_staging_destination,
    projection_write_plan,
    read_bundle_manifest,
)
from .snapshot import Snapshot, mirror_rebuild_plan, snapshot_write_plan, verify_snapshot
from .transaction import (
    PlannedAbsence,
    PlannedDeletion,
    PlannedRead,
    PlannedTreeRead,
    PlannedValue,
    PlannedWrite,
    TransactionEngine,
    output_plan_hash,
)


WORKSPACE_SCHEMA = "asme.workspace.v1"
NON_TRANSITION_OPERATIONS = frozenset(
    {"prepare-rollout", "record-execution", "ingest-rollout", "sample", "proposer-context"}
)


@dataclass(frozen=True)
class WorkspaceLayout:
    domain_root: Path
    control_root: Path
    staging_root: Path
    archive_root: Path

    @classmethod
    def under(cls, root: Path) -> "WorkspaceLayout":
        canonical = root.resolve(strict=False)
        return cls(
            domain_root=canonical,
            control_root=canonical.parent / ".asme-control",
            staging_root=canonical / "staging",
            archive_root=canonical / "archives",
        )


class DomainWorkspace:
    """One sealed domain. No method installs into a runtime skill root."""

    def __init__(
        self,
        *,
        domain_id: str,
        layout: WorkspaceLayout,
        clock: CanonicalClock | None = None,
    ) -> None:
        self.domain_id = require_identifier(domain_id, field="domain_id")
        self.layout = layout
        self.clock = clock or CanonicalClock.system()
        root = layout.domain_root.resolve(strict=False)
        self.engine = TransactionEngine(
            domain_id=domain_id,
            domain_root=root,
            control_root=layout.control_root,
            target_roots={
                "snapshots": root / "snapshots",
                "mirror": root / "mirror",
                "raw": root / "raw",
                "runs": root / "runs",
                "wiki": root / "wiki",
                "impact": root / "impact",
                "staging": layout.staging_root,
                "archives": layout.archive_root,
            },
        )

    def initialize(
        self,
        *,
        domain: DeclaredDomain,
        max_iterations: int,
        cartridge: DomainCartridge | None = None,
        crash_at: str | None = None,
    ) -> DomainState:
        verify_domain_seal(domain)
        if domain.domain_id != self.domain_id:
            raise ContractError("declared domain ID differs from workspace ID")
        if max_iterations < 1:
            raise ContractError("max_iterations must be at least one")
        if self.engine.read_state() is not None:
            raise ContractError("domain workspace is already initialized")
        if self.layout.domain_root.exists() and any(self.layout.domain_root.iterdir()):
            raise ContractError("uninitialized domain root is not empty")
        empty = Snapshot.empty()
        initial = DomainState(
            domain_id=self.domain_id,
            seal=domain.seal,
            max_iterations=max_iterations,
            active_snapshot_hash=empty.snapshot_hash,
        )
        initialized = transition(initial, "init")
        domain_record = {
            "schema": WORKSPACE_SCHEMA,
            "domain": asdict(domain),
            "max_iterations": max_iterations,
            "empty_snapshot_hash": empty.snapshot_hash,
            "cartridge": cartridge.manifest() if cartridge is not None else None,
        }
        if cartridge is not None:
            cartridge.verify_domain(domain)
        arguments, input_hashes = self._mutation_metadata(
            arguments={"max_iterations": max_iterations},
            input_hashes={
                "domain_seal": domain.seal,
                **({"cartridge": cartridge.digest} if cartridge is not None else {}),
            },
        )
        final = self.engine.execute(
            operation="init",
            current_state=_state_json(initial),
            next_state=_state_json(initialized),
            arguments=arguments,
            input_hashes=input_hashes,
            writes=(
                PlannedWrite.from_bytes(
                    root="domain",
                    path="domain.json",
                    content=canonical_bytes(domain_record),
                    mode=0o600,
                ),
                *(cartridge.write_plan() if cartridge is not None else ()),
            ),
            crash_at=crash_at,
        )
        return _state_from_json(final)

    def status(self) -> DomainState:
        raw = self.engine.read_state()
        if raw is None:
            raise ContractError("domain workspace is not initialized")
        return _state_from_json(raw)

    def apply(
        self,
        *,
        operation: str,
        supplied: TransitionInput | None = None,
        arguments: Mapping[str, Any] | None = None,
        input_hashes: Mapping[str, str] | None = None,
        dependency_operation: str | None = None,
        reads: Sequence[PlannedRead] = (),
        tree_reads: Sequence[PlannedTreeRead] = (),
        values: Sequence[PlannedValue] = (),
        absences: Sequence[PlannedAbsence] = (),
        writes: Sequence[PlannedWrite] = (),
        deletions: Sequence[PlannedDeletion] = (),
        crash_at: str | None = None,
    ) -> DomainState:
        current = self.status()
        domain_record_hash = self._verify_recorded_domain(current)
        next_state = transition(current, operation, supplied)
        if next_state == current and not writes and not deletions:
            return current
        hashes = {
            "domain_seal": current.seal,
            "domain_record": domain_record_hash,
            "output_plan": output_plan_hash(
                writes=writes,
                deletions=deletions,
                next_state=_state_json(next_state),
            ),
            **dict(input_hashes or {}),
        }
        recorded_arguments, hashes = self._mutation_metadata(
            arguments=arguments,
            input_hashes=hashes,
        )
        recorded_arguments, hashes = self._bind_dependency_matrix(
            operation=dependency_operation,
            state_hash=hash_json(_state_json(current)),
            arguments=recorded_arguments,
            input_hashes=hashes,
            reads=reads,
            tree_reads=tree_reads,
            values=values,
            absences=absences,
        )
        final = self.engine.execute(
            operation=operation,
            current_state=_state_json(current),
            next_state=_state_json(next_state),
            arguments=recorded_arguments,
            input_hashes=hashes,
            reads=reads,
            tree_reads=tree_reads,
            values=values,
            absences=absences,
            writes=writes,
            deletions=deletions,
            crash_at=crash_at,
        )
        return _state_from_json(final)

    def persist(
        self,
        *,
        operation: str,
        arguments: Mapping[str, Any] | None = None,
        input_hashes: Mapping[str, str] | None = None,
        dependency_operation: str | None = None,
        reads: Sequence[PlannedRead] = (),
        tree_reads: Sequence[PlannedTreeRead] = (),
        values: Sequence[PlannedValue] = (),
        absences: Sequence[PlannedAbsence] = (),
        writes: Sequence[PlannedWrite] = (),
        deletions: Sequence[PlannedDeletion] = (),
        crash_at: str | None = None,
    ) -> DomainState:
        """Persist artifacts for an explicit no-phase-change core operation."""

        if operation not in NON_TRANSITION_OPERATIONS:
            raise ContractError("non-transition operation is not part of the core contract")
        current = self.status()
        domain_record_hash = self._verify_recorded_domain(current)
        if not writes and not deletions:
            return current
        recorded_arguments, hashes = self._mutation_metadata(
            arguments=arguments,
            input_hashes={
                "domain_seal": current.seal,
                "domain_record": domain_record_hash,
                "output_plan": output_plan_hash(
                    writes=writes,
                    deletions=deletions,
                    next_state=_state_json(current),
                ),
                **dict(input_hashes or {}),
            },
        )
        recorded_arguments, hashes = self._bind_dependency_matrix(
            operation=dependency_operation,
            state_hash=hash_json(_state_json(current)),
            arguments=recorded_arguments,
            input_hashes=hashes,
            reads=reads,
            tree_reads=tree_reads,
            values=values,
            absences=absences,
        )
        final = self.engine.execute(
            operation=operation,
            current_state=_state_json(current),
            next_state=_state_json(current),
            arguments=recorded_arguments,
            input_hashes=hashes,
            reads=reads,
            tree_reads=tree_reads,
            values=values,
            absences=absences,
            writes=writes,
            deletions=deletions,
            crash_at=crash_at,
        )
        return _state_from_json(final)

    def recorded_domain(self) -> DeclaredDomain:
        state = self.status()
        domain, _, _ = self._read_recorded_domain(state)
        return domain

    def _verify_recorded_domain(self, state: DomainState) -> str:
        _, digest, _ = self._read_recorded_domain(state)
        return digest

    def _read_recorded_domain(
        self, state: DomainState
    ) -> tuple[DeclaredDomain, str, Mapping[str, Any]]:
        path = require_regular_file(
            self.layout.domain_root / "domain.json", root=self.layout.domain_root
        )
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ContractError("recorded domain is unreadable") from exc
        if not isinstance(raw, dict) or raw.get("schema") != WORKSPACE_SCHEMA:
            raise ContractError("recorded domain schema is invalid")
        domain_raw = raw.get("domain")
        if not isinstance(domain_raw, Mapping):
            raise ContractError("recorded domain is malformed")
        try:
            domain = declared_domain_from_mapping(domain_raw)
        except ContractError as exc:
            raise ContractError(f"recorded domain verification failed: {exc}") from exc
        if domain.domain_id != self.domain_id or domain.seal != state.seal:
            raise ContractError("recorded domain identity differs from authoritative state")
        if raw.get("max_iterations") != state.max_iterations:
            raise ContractError("recorded domain iteration limit differs from authoritative state")
        cartridge_manifest = raw.get("cartridge")
        if cartridge_manifest is not None:
            if not isinstance(cartridge_manifest, Mapping):
                raise ContractError("recorded cartridge manifest is malformed")
            try:
                verify_cartridge_tree(
                    self.layout.domain_root / "cartridge",
                    cartridge_manifest,
                    domain=domain,
                )
            except ContractError as exc:
                raise ContractError(f"recorded cartridge verification failed: {exc}") from exc
        return domain, sha256_file(path), raw

    def recover(self, *, crash_at: str | None = None) -> DomainState:
        state = _state_from_json(self.engine.recover(crash_at=crash_at))
        self._verify_recorded_domain(state)
        return state

    def publish_snapshot(
        self,
        *,
        snapshot: Snapshot,
        operation: str,
        supplied: TransitionInput,
        crash_at: str | None = None,
    ) -> DomainState:
        return self.apply(
            operation=operation,
            supplied=supplied,
            arguments={"snapshot_hash": snapshot.snapshot_hash},
            input_hashes={"snapshot": snapshot.snapshot_hash},
            writes=snapshot_write_plan(snapshot),
            crash_at=crash_at,
        )

    def verify_active_snapshot(self, snapshot: Snapshot) -> None:
        state = self.status()
        if state.active_snapshot_hash != snapshot.snapshot_hash:
            raise ContractError("provided snapshot is not the active pointer")
        verify_snapshot(self.engine.target_roots["snapshots"], snapshot)

    def rebuild_mirror(self, snapshot: Snapshot, *, crash_at: str | None = None) -> DomainState:
        self.verify_active_snapshot(snapshot)
        writes, deletions = mirror_rebuild_plan(
            mirror_root=self.engine.target_roots["mirror"], snapshot=snapshot
        )
        current = self.status()
        if not writes and not deletions:
            return current
        arguments, input_hashes = self._mutation_metadata(
            arguments={
                "purpose": "lazy_mirror_rebuild",
                "snapshot": snapshot.snapshot_hash,
            },
            input_hashes={"snapshot": snapshot.snapshot_hash},
        )
        final = self.engine.execute(
            operation="rebuild-mirror",
            current_state=_state_json(current),
            next_state=_state_json(current),
            arguments=arguments,
            input_hashes=input_hashes,
            writes=writes,
            deletions=deletions,
            crash_at=crash_at,
        )
        return _state_from_json(final)

    def stage_projection(
        self,
        *,
        projection: Projection,
        archive_bytes: bytes,
        staging_id: str,
        untested: bool,
        approval_present: bool,
        approval_id: str | None = None,
        approval_hash: str | None = None,
        approval_record_bytes: bytes | None = None,
        forbidden_live_roots: Sequence[Path],
        dependency_hashes: Mapping[str, str] | None = None,
        dependency_operation: str | None = None,
        reads: Sequence[PlannedRead] = (),
        tree_reads: Sequence[PlannedTreeRead] = (),
        values: Sequence[PlannedValue] = (),
        absences: Sequence[PlannedAbsence] = (),
        crash_at: str | None = None,
    ) -> DomainState:
        require_identifier(staging_id, field="staging_id")
        suffix = "__untested" if untested else ""
        prefix = f"{staging_id}{suffix}"
        manifest = read_bundle_manifest(projection)
        contents = projection.content_map()
        if untested:
            if manifest.get("status") != "staged_candidate_untested_not_installed":
                raise ContractError("untested projection has the wrong package status")
            for required_file in ("README.md", "PURPOSE.md"):
                content = contents.get(required_file, b"")
                if b"test_evaluation: not_run" not in content:
                    raise ContractError(f"untested projection lacks label in {required_file}")
        elif manifest.get("status") != "staged_candidate_not_installed":
            raise ContractError("validated projection has the wrong package status")
        ensure_staging_destination(
            destination=self.layout.staging_root / prefix,
            staging_root=self.layout.staging_root,
            forbidden_live_roots=forbidden_live_roots,
        )
        if not forbidden_live_roots:
            raise ContractError("staging requires an explicit forbidden live-root set")
        archive_name = f"{staging_id}{'.untested' if untested else ''}.skill"
        archive_plan = archive_write_plan(archive_bytes, member=archive_name)
        approval_record_hash = (
            sha256_bytes(approval_record_bytes)
            if approval_record_bytes is not None
            else None
        )
        if untested and (
            not approval_present
            or approval_id is None
            or approval_hash is None
            or approval_record_bytes is None
        ):
            raise ContractError("untested staging requires a consumed approval record")
        if not untested and any(
            item is not None
            for item in (approval_id, approval_hash, approval_record_bytes)
        ):
            raise ContractError("validated staging cannot persist an untested approval")
        approval_writes = (
            (
                PlannedWrite.from_bytes(
                    root="runs",
                    path=f"delivery/{staging_id}/untested-approval.json",
                    content=approval_record_bytes,
                    mode=0o600,
                    allow_existing_identical=True,
                ),
            )
            if approval_record_bytes is not None
            else ()
        )
        writes = (
            *projection_write_plan(projection, prefix=prefix),
            archive_plan,
            *approval_writes,
        )
        operation = "package-untested" if untested else "export"
        supplied = TransitionInput(
            valid=not untested,
            approval_present=approval_present,
            approval_id=approval_id,
            approval_hash=approval_hash,
            approval_record_hash=approval_record_hash,
            delivery_id=staging_id,
        )
        return self.apply(
            operation=operation,
            supplied=supplied,
            arguments={
                "staging_id": staging_id,
                "projection_hash": projection.tree_sha256,
                "untested": untested,
                "delivery_route": "untested" if untested else "validated",
            },
            input_hashes={
                "projection": projection.tree_sha256,
                "archive": sha256_bytes(archive_bytes),
                **(
                    {"untested_approval": str(approval_record_hash)}
                    if approval_record_hash is not None
                    else {}
                ),
                **dict(dependency_hashes or {}),
            },
            dependency_operation=dependency_operation,
            reads=reads,
            tree_reads=tree_reads,
            values=values,
            absences=absences,
            writes=writes,
            crash_at=crash_at,
        )

    def _mutation_metadata(
        self,
        *,
        arguments: Mapping[str, Any] | None,
        input_hashes: Mapping[str, str] | None,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        recorded_arguments = dict(arguments or {})
        recorded_hashes = dict(input_hashes or {})
        if "clock" in recorded_arguments or "clock" in recorded_hashes:
            raise ContractError("clock is reserved for the core workspace")
        timestamp = self.clock.read()
        recorded_arguments["clock"] = timestamp
        recorded_hashes["clock"] = sha256_bytes(timestamp.encode("utf-8"))
        return recorded_arguments, recorded_hashes

    def _bind_dependency_matrix(
        self,
        *,
        operation: str | None,
        state_hash: str,
        arguments: Mapping[str, Any],
        input_hashes: Mapping[str, str],
        reads: Sequence[PlannedRead],
        tree_reads: Sequence[PlannedTreeRead],
        values: Sequence[PlannedValue],
        absences: Sequence[PlannedAbsence],
    ) -> tuple[dict[str, Any], dict[str, str]]:
        recorded_arguments = dict(arguments)
        recorded_hashes = dict(input_hashes)
        if operation is None:
            return recorded_arguments, recorded_hashes
        if "dependency_operation" in recorded_arguments:
            raise ContractError("dependency_operation is reserved for the core workspace")
        if "dependency_matrix" in recorded_hashes:
            raise ContractError("dependency_matrix input hash is reserved")
        if "operation_arguments" in recorded_hashes or "state" in recorded_hashes:
            raise ContractError("common dependency input hashes are reserved")
        matrix = default_dependency_matrix()
        recorded_hashes["operation_arguments"] = hash_json(recorded_arguments)
        recorded_hashes["state"] = state_hash
        matrix.verify_binding_coverage(
            operation=operation,
            value_names=recorded_hashes,
            material_names=(item.name for item in values),
            read_names=(item.name for item in (*reads, *tree_reads)),
            absence_names=(item.name for item in absences),
        )
        recorded_arguments["dependency_operation"] = operation
        recorded_hashes["dependency_matrix"] = matrix.digest
        return recorded_arguments, recorded_hashes


def _state_json(state: DomainState) -> dict[str, Any]:
    normalized = json.loads(canonical_bytes(asdict(state)).decode("utf-8"))
    if not isinstance(normalized, dict):  # pragma: no cover - dataclass invariant
        raise ContractError("domain state did not serialize to an object")
    return normalized


def _state_from_json(raw: Mapping[str, Any]) -> DomainState:
    expected = {field.name for field in fields(DomainState)}
    if set(raw) != expected:
        raise ContractError(
            f"domain state fields differ: missing={sorted(expected-set(raw))}, extra={sorted(set(raw)-expected)}"
        )
    values = dict(raw)
    try:
        values["state"] = LifecycleState(values["state"])
        values["route"] = Route(values["route"]) if values["route"] is not None else None
        values["history"] = tuple(dict(item) for item in values["history"])
        values["delivery_ledger"] = tuple(dict(item) for item in values["delivery_ledger"])
        values["consumed_manifests"] = tuple(
            dict(item) for item in values["consumed_manifests"]
        )
        values["test_manifests"] = tuple(dict(item) for item in values["test_manifests"])
        values["prepared_test_phases"] = tuple(values["prepared_test_phases"])
        values["seeded_observation_ids"] = tuple(values["seeded_observation_ids"])
        return DomainState(**values)
    except (TypeError, ValueError, KeyError) as exc:
        raise ContractError("domain state is malformed") from exc
