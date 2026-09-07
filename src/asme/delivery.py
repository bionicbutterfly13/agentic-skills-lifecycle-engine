"""Staging-only delivery from one verified active snapshot."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime
import json
from pathlib import Path
from typing import Mapping, Sequence

from .canonical import (
    ContractError,
    canonical_bytes,
    hash_json,
    require_identifier,
    require_regular_file,
    sha256_bytes,
    sha256_file,
    tree_manifest,
)
from .contract import ApprovalRecord, CapabilityReport, IsolationLevel
from .lifecycle import DomainState
from .manifest import rollout_manifest_from_mapping
from .package import (
    Compatibility,
    Projection,
    build_archive,
    build_projection_from_files,
    ensure_staging_destination,
    validate_existing_projection,
    verify_archive,
)
from .proposal import purpose_origin_observations
from .integration import validate_skill_authoring
from .skill_safety import require_safe_skill_files
from .snapshot import Snapshot, verify_snapshot
from .transaction import PlannedAbsence, PlannedRead, PlannedTreeRead, PlannedValue
from .workspace import DomainWorkspace


@dataclass(frozen=True)
class StagedDelivery:
    state: DomainState
    staging_id: str
    status: str
    tree_sha256: str
    archive_sha256: str
    swept_build_artifacts: tuple[str, ...]


class DeliveryWorkflow:
    """Build and stage candidates without any runtime installation operation."""

    def __init__(self, workspace: DomainWorkspace) -> None:
        self.workspace = workspace

    def stage_skill(
        self,
        *,
        skill_name: str,
        compatibility: Compatibility,
        source_attribution: Sequence[Mapping[str, str]],
        recorded_at: datetime,
        forbidden_live_roots: Sequence[Path],
        capability: CapabilityReport,
        untested: bool = False,
        approval: ApprovalRecord | None = None,
        license_policy: str = "resolved_mit_ccby4_distribution_gate4_blocked",
    ) -> StagedDelivery:
        require_identifier(skill_name, field="skill_name")
        if not source_attribution:
            raise ContractError("staging requires source attribution")
        self._verify_compatibility(
            compatibility=compatibility,
            capability=capability,
            validated=not untested,
        )
        state = self.workspace.status()
        if not state.active_snapshot_hash:
            raise ContractError("staging requires an active snapshot")
        snapshot = self._active_snapshot(state.active_snapshot_hash)
        prefix = f"{skill_name}/"
        files = {
            item.path.removeprefix(prefix): item.content
            for item in snapshot.files
            if item.path.startswith(prefix)
        }
        required = {"SKILL.md", "README.md", "PURPOSE.md"}
        missing = sorted(required - set(files))
        if missing:
            raise ContractError(f"staged skill is incomplete: missing={missing}")
        validate_skill_authoring(files["SKILL.md"], expected_name=skill_name)
        require_safe_skill_files(files)
        skill_origins = purpose_origin_observations(files["PURPOSE.md"])
        unknown_origins = sorted(
            set(skill_origins) - set(state.seeded_observation_ids)
        )
        if unknown_origins:
            raise ContractError(
                f"staged PURPOSE cites unseeded observations: {unknown_origins}"
            )
        expected_test_label = "not_run" if untested else "passed"
        expected_isolation = _package_isolation_label(capability)
        for member in ("README.md", "PURPOSE.md"):
            content = files[member]
            _require_document_label(
                content,
                key="test_evaluation",
                expected=expected_test_label,
                member=member,
            )
            _require_document_label(
                content,
                key="trace_fidelity",
                expected=capability.trace_fidelity.value,
                member=member,
            )
            _require_document_label(
                content,
                key="isolation",
                expected=expected_isolation,
                member=member,
            )
        evidence_hashes: dict[str, str] = {}
        evidence_reads: tuple[PlannedRead, ...] = ()
        if not untested:
            evidence_hashes, evidence_reads = self._verify_validated_evidence(
                state=state,
                capability=capability,
            )
        status = (
            "staged_candidate_untested_not_installed"
            if untested
            else "staged_candidate_not_installed"
        )
        projection = build_projection_from_files(
            files=files,
            compatibility=compatibility,
            source_attribution=source_attribution,
            status=status,
            license_policy=license_policy,
        )
        archive = build_archive(projection, recorded_at=recorded_at)
        archive_hash = sha256_bytes(archive)
        staging_id = f"{self.workspace.domain_id[:100]}__{snapshot.snapshot_hash[:12]}"
        require_identifier(staging_id, field="staging_id")
        approval_id: str | None = None
        approval_hash: str | None = None
        approval_record_bytes: bytes | None = None
        if untested:
            if approval is None:
                raise ContractError("untested staging requires an action-time approval record")
            normalized_approval = replace(approval, consumed=False)
            approval_id = normalized_approval.approval_id
            approval_hash = hash_json(asdict(normalized_approval))
            approval_record_bytes = canonical_bytes(
                {
                    "schema": "asme.consumed-approval.v1",
                    "approval": asdict(normalized_approval.consume()),
                    "original_approval_hash": approval_hash,
                    "consumed_for": staging_id,
                }
            )
        elif approval is not None:
            raise ContractError("validated staging does not consume an untested approval")
        suffix = "__untested" if untested else ""
        prefix = f"{staging_id}{suffix}"
        archive_name = f"{staging_id}{'.untested' if untested else ''}.skill"
        route = "untested" if untested else "validated"
        existing = self._exact_existing_delivery(
            state=state,
            staging_id=staging_id,
            staging_prefix=prefix,
            archive_name=archive_name,
            route=route,
            status=status,
            projection=projection,
            archive_bytes=archive,
            forbidden_live_roots=forbidden_live_roots,
            approval_id=approval_id,
            approval_hash=approval_hash,
            approval_record_bytes=approval_record_bytes,
        )
        if existing is not None:
            return existing
        if untested:
            assert approval is not None  # established above
            approval.validate_for(
                phase="package-untested",
                artifact_hashes={
                    "projection": projection.tree_sha256,
                    "archive": archive_hash,
                },
                runtime_id=None,
                destination=staging_id,
                now=self.workspace.clock.now(),
            )
        snapshot_root = self.workspace.engine.target_roots["snapshots"] / snapshot.snapshot_hash
        snapshot_reads = (
            PlannedTreeRead(
                name="active_snapshot",
                root="snapshots",
                path=snapshot.snapshot_hash,
                expected_sha256=hash_json(tree_manifest(snapshot_root)),
            ),
        )
        absences = [
            PlannedAbsence(
                name="existing_staging_target",
                root="staging",
                path=prefix,
            ),
            PlannedAbsence(
                name="existing_staging_target",
                root="archives",
                path=archive_name,
            ),
        ]
        if untested:
            absences.append(
                PlannedAbsence(
                    name="test_artifacts_absent",
                    root="runs",
                    path="final",
                )
            )
        next_state = self.workspace.stage_projection(
            projection=projection,
            archive_bytes=archive,
            staging_id=staging_id,
            untested=untested,
            approval_present=approval is not None,
            approval_id=approval_id,
            approval_hash=approval_hash,
            approval_record_bytes=approval_record_bytes,
            forbidden_live_roots=forbidden_live_roots,
            dependency_hashes={
                "active_snapshot": snapshot.snapshot_hash,
                "seal": state.seal,
                "delivery_route": hash_json({"route": route}),
                **evidence_hashes,
            },
            dependency_operation="package-untested" if untested else "export",
            reads=evidence_reads,
            tree_reads=snapshot_reads,
            values=(
                (
                    PlannedValue.from_bytes(
                        name="untested_approval", content=approval_record_bytes
                    ),
                )
                if approval_record_bytes is not None
                else ()
            ),
            absences=tuple(absences),
        )
        return StagedDelivery(
            state=next_state,
            staging_id=staging_id,
            status=status,
            tree_sha256=projection.tree_sha256,
            archive_sha256=archive_hash,
            swept_build_artifacts=projection.swept_build_artifacts,
        )

    def _exact_existing_delivery(
        self,
        *,
        state: DomainState,
        staging_id: str,
        staging_prefix: str,
        archive_name: str,
        route: str,
        status: str,
        projection: Projection,
        archive_bytes: bytes,
        forbidden_live_roots: Sequence[Path],
        approval_id: str | None,
        approval_hash: str | None,
        approval_record_bytes: bytes | None,
    ) -> StagedDelivery | None:
        """Return an exact prior delivery without recording another mutation."""

        if not forbidden_live_roots:
            raise ContractError("staging requires an explicit forbidden live-root set")
        stage_root = self.workspace.layout.staging_root / staging_prefix
        ensure_staging_destination(
            destination=stage_root,
            staging_root=self.workspace.layout.staging_root,
            forbidden_live_roots=forbidden_live_roots,
        )
        archive_path = self.workspace.layout.archive_root / archive_name
        matching = [
            item
            for item in state.delivery_ledger
            if item.get("delivery_id") == staging_id
        ]
        has_record = bool(matching)
        has_stage = stage_root.exists()
        has_archive = archive_path.exists()
        if not (has_record or has_stage or has_archive):
            return None
        expected_ledger = {"delivery_id": staging_id, "route": route}
        if route == "untested":
            if approval_id is None or approval_hash is None or approval_record_bytes is None:
                raise ContractError("untested replay requires the original approval identity")
            expected_ledger.update(
                {
                    "approval_id": approval_id,
                    "approval_hash": approval_hash,
                    "approval_record_hash": sha256_bytes(approval_record_bytes),
                }
            )
        if len(matching) != 1 or dict(matching[0]) != expected_ledger:
            raise ContractError("existing delivery ledger differs from the requested route")
        if route == "validated" and (
            state.validated_step != "exported" or state.route is None or state.route.value != route
        ):
            raise ContractError("existing validated delivery is not latched in state")
        if route == "untested" and (state.route is None or state.route.value != route):
            raise ContractError("existing untested delivery is not latched in state")
        if not has_stage or not has_archive:
            raise ContractError("existing delivery is incomplete")
        if not validate_existing_projection(stage_root, projection):
            raise ContractError("existing staged projection differs from the requested bytes")
        archive_content = require_regular_file(
            archive_path,
            root=self.workspace.layout.archive_root,
        ).read_bytes()
        if archive_content != archive_bytes:
            raise ContractError("existing staged archive differs from the requested bytes")
        verified = verify_archive(archive_content, expected=projection)
        if verified.archive_sha256 != sha256_bytes(archive_bytes):
            raise ContractError("existing staged archive hash differs from the requested bytes")
        if route == "untested":
            assert approval_record_bytes is not None
            approval_path = require_regular_file(
                self.workspace.engine.target_roots["runs"]
                / "delivery"
                / staging_id
                / "untested-approval.json",
                root=self.workspace.engine.target_roots["runs"],
            )
            if approval_path.read_bytes() != approval_record_bytes:
                raise ContractError("persisted approval differs from the requested replay")
        return StagedDelivery(
            state=state,
            staging_id=staging_id,
            status=status,
            tree_sha256=projection.tree_sha256,
            archive_sha256=verified.archive_sha256,
            swept_build_artifacts=projection.swept_build_artifacts,
        )

    def _verify_compatibility(
        self,
        *,
        compatibility: Compatibility,
        capability: CapabilityReport,
        validated: bool,
    ) -> None:
        if compatibility.adapter_id != capability.runtime_id:
            raise ContractError("compatibility adapter ID differs from capability runtime")
        if compatibility.adapter_version != capability.adapter_version:
            raise ContractError("compatibility adapter version differs from capability report")
        if validated and capability.runtime_version not in compatibility.runtime_tested:
            raise ContractError("validated runtime version is absent from compatibility evidence")

    def _verify_validated_evidence(
        self, *, state: DomainState, capability: CapabilityReport
    ) -> tuple[dict[str, str], tuple[PlannedRead, ...]]:
        recorded = {
            str(item.get("phase")): str(item.get("manifest_hash"))
            for item in state.test_manifests
        }
        if set(recorded) != {"test-baseline", "test-final"}:
            raise ContractError("validated delivery requires both test manifests")
        expected_snapshots = {
            "test-baseline": Snapshot.empty().snapshot_hash,
            "test-final": state.active_snapshot_hash,
        }
        manifest_hashes: dict[str, str] = {}
        sidecar_hashes: dict[str, str] = {}
        reads: list[PlannedRead] = []
        runs_root = self.workspace.engine.target_roots["runs"]
        for phase in ("test-baseline", "test-final"):
            path = require_regular_file(
                self.workspace.engine.target_roots["runs"]
                / "final"
                / phase
                / "manifest.json",
                root=self.workspace.engine.target_roots["runs"],
            )
            content = path.read_bytes()
            if sha256_bytes(content) != recorded[phase]:
                raise ContractError(f"{phase} manifest bytes differ from lifecycle evidence")
            try:
                raw = json.loads(content)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ContractError(f"{phase} manifest is malformed") from exc
            manifest = rollout_manifest_from_mapping(raw)
            if manifest.digest != recorded[phase]:
                raise ContractError(f"{phase} manifest is not canonical")
            if (
                manifest.phase != phase
                or manifest.split != "test"
                or manifest.iteration != -1
                or not manifest.complete
                or not manifest.valid
                or manifest.domain_seal_hash != state.seal
                or manifest.active_snapshot_hash != expected_snapshots[phase]
            ):
                raise ContractError(f"{phase} manifest differs from validated delivery scope")
            if manifest.capability_report_hash != capability.digest:
                raise ContractError(
                    f"{phase} capability report differs from staged package labels"
                )
            manifest_hashes[phase] = sha256_file(path)
            reads.append(
                PlannedRead(
                    name="test_manifests",
                    root="runs",
                    path=path.relative_to(runs_root).as_posix(),
                    expected_sha256=manifest_hashes[phase],
                )
            )
            for entry in manifest.entries:
                sidecar = require_regular_file(
                    path.parent / f"{entry.task_id}.sidecar.json",
                    root=path.parent,
                )
                key = f"{phase}:{entry.task_id}"
                sidecar_hashes[key] = sha256_file(sidecar)
                reads.append(
                    PlannedRead(
                        name="test_sidecars",
                        root="runs",
                        path=sidecar.relative_to(runs_root).as_posix(),
                        expected_sha256=sidecar_hashes[key],
                    )
                )
        return (
            {
                "test_manifests": hash_json(manifest_hashes),
                "test_sidecars": hash_json(sidecar_hashes),
            },
            tuple(reads),
        )

    def _active_snapshot(self, snapshot_hash: str) -> Snapshot:
        root = self.workspace.engine.target_roots["snapshots"] / snapshot_hash
        snapshot = Snapshot.from_directory(root)
        if snapshot.snapshot_hash != snapshot_hash:
            raise ContractError("active snapshot directory differs from its pointer")
        verify_snapshot(self.workspace.engine.target_roots["snapshots"], snapshot)
        return snapshot


def _package_isolation_label(capability: CapabilityReport) -> str:
    isolation = (
        capability.conversation_isolation,
        capability.filesystem_isolation,
        capability.tool_isolation,
        capability.held_out_answer_isolation,
        capability.wiki_isolation,
    )
    if all(item is IsolationLevel.ENFORCED for item in isolation):
        if "sandboxed" not in capability.claims_allowed:
            raise ContractError("fully enforced capability report lacks a package isolation claim")
        return "sandboxed"
    if "unsandboxed" not in capability.claims_allowed:
        raise ContractError("non-enforced capability report lacks the unsandboxed claim")
    return "unsandboxed"


def _require_document_label(
    content: bytes, *, key: str, expected: str, member: str
) -> None:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError(f"staged capability labels are not UTF-8 in {member}") from exc
    prefix = f"{key}:"
    labels = [
        line.removeprefix(prefix).strip()
        for line in text.splitlines()
        if line.startswith(prefix)
    ]
    if len(labels) != 1 or labels[0] != expected:
        raise ContractError(f"{key} label in {member} must be exactly {expected}")
