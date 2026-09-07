from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path

import pytest

from asme.canonical import ContractError, canonical_bytes, tree_manifest
from asme.contract import LifecycleState
from asme.lifecycle import TransitionInput, TransitionRefused
from asme.manifest import RolloutManifest
from asme.snapshot import Snapshot
from asme.workflow import EvolutionWorkflow
from asme.workspace import (
    DomainWorkspace,
    WorkspaceLayout,
    _state_json,
)


RESET_CONTEXTS = (
    (LifecycleState.NEEDS_BASELINE_RUN, "baseline", 0),
    (LifecycleState.NEEDS_TRAIN_RUN, "train", 1),
    (LifecycleState.NEEDS_WIKI, "train", 1),
    (LifecycleState.NEEDS_VAL_RUN, "val", 1),
    (LifecycleState.NEEDS_VAL_CONFIRM, "val_confirm", 1),
    (LifecycleState.DONE, "test-baseline", -1),
    (LifecycleState.DONE, "test-final", -1),
)


def _workspace(tmp_path: Path, declared_domain) -> DomainWorkspace:
    workspace = DomainWorkspace(
        domain_id=declared_domain.domain_id,
        layout=WorkspaceLayout.under(tmp_path / "workspace"),
    )
    workspace.initialize(domain=declared_domain, max_iterations=1)
    return workspace


def _advance_to(
    workspace: DomainWorkspace,
    target: LifecycleState,
    *,
    test_phase: str | None = None,
) -> None:
    if target is LifecycleState.NEEDS_OPTIONAL_SEED:
        return
    workspace.apply(operation="skip-seed")
    if target is LifecycleState.NEEDS_BASELINE_RUN:
        return
    empty = Snapshot.empty()
    workspace.publish_snapshot(
        snapshot=empty,
        operation="baseline-finalize",
        supplied=TransitionInput(
            valid=True,
            score=0.5,
            snapshot_hash=empty.snapshot_hash,
            phase="baseline",
            manifest_hash="1" * 64,
        ),
    )
    if target is LifecycleState.NEEDS_TRAIN_RUN:
        return
    workspace.apply(
        operation="train-ingest",
        supplied=TransitionInput(
            valid=True,
            phase="train",
            manifest_hash="2" * 64,
        ),
    )
    if target is LifecycleState.NEEDS_WIKI:
        return
    workspace.apply(operation="apply-wiki")
    if target is LifecycleState.NEEDS_PROPOSAL:
        return
    if target is LifecycleState.DONE:
        workspace.apply(operation="apply-proposal-no-action")
        if test_phase is not None:
            workspace.apply(
                operation="test-prepare",
                supplied=TransitionInput(phase=test_phase),
            )
        return
    workspace.apply(
        operation="apply-proposal-change",
        supplied=TransitionInput(snapshot_hash="a" * 64),
    )
    if target is LifecycleState.NEEDS_VAL_RUN:
        return
    workspace.apply(
        operation="val-ingest",
        supplied=TransitionInput(
            valid=True,
            score=0.75,
            phase="val",
            manifest_hash="3" * 64,
        ),
    )
    if target is LifecycleState.NEEDS_GATE:
        return
    workspace.apply(operation="gate")
    if target is LifecycleState.NEEDS_VAL_CONFIRM:
        return
    raise AssertionError(f"unsupported fixture target: {target.value}")


def _run_dir(workspace: DomainWorkspace, phase: str, iteration: int) -> Path:
    member = f"final/{phase}" if phase.startswith("test-") else f"{iteration}/{phase}"
    return workspace.engine.target_roots["runs"] / member


def _manifest(
    workspace: DomainWorkspace,
    *,
    phase: str,
    iteration: int,
    valid: bool,
) -> RolloutManifest:
    split = (
        "train"
        if phase == "train"
        else "test"
        if phase.startswith("test-")
        else "validation"
    )
    state = workspace.status()
    return RolloutManifest(
        phase=phase,
        split=split,
        iteration=iteration,
        domain_seal_hash=state.seal,
        active_snapshot_hash=str(state.active_snapshot_hash),
        capability_report_hash="c" * 64,
        entries=(),
        complete=valid,
        valid=valid,
        aggregate_score=1.0 if valid else None,
        errors=() if valid else ("fixture-invalid",),
    )


def _write_manifest(
    workspace: DomainWorkspace,
    *,
    phase: str,
    iteration: int,
    valid: bool,
) -> RolloutManifest:
    manifest = _manifest(
        workspace,
        phase=phase,
        iteration=iteration,
        valid=valid,
    )
    run_dir = _run_dir(workspace, phase, iteration)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_bytes(canonical_bytes(asdict(manifest)))
    return manifest


@pytest.mark.parametrize(("target", "phase", "iteration"), RESET_CONTEXTS)
def test_reset_refuses_missing_manifest_without_mutation(
    tmp_path: Path,
    declared_domain,
    target: LifecycleState,
    phase: str,
    iteration: int,
) -> None:
    workspace = _workspace(tmp_path, declared_domain)
    _advance_to(
        workspace,
        target,
        test_phase=phase if phase.startswith("test-") else None,
    )
    before_state = workspace.status()
    before_tree = tree_manifest(workspace.layout.domain_root)

    with pytest.raises((ContractError, TransitionRefused)):
        EvolutionWorkflow(workspace).reset_manifest()

    assert workspace.status() == before_state
    assert tree_manifest(workspace.layout.domain_root) == before_tree


@pytest.mark.parametrize(("target", "phase", "iteration"), RESET_CONTEXTS)
def test_reset_refuses_valid_manifest_without_mutation(
    tmp_path: Path,
    declared_domain,
    target: LifecycleState,
    phase: str,
    iteration: int,
) -> None:
    workspace = _workspace(tmp_path, declared_domain)
    _advance_to(
        workspace,
        target,
        test_phase=phase if phase.startswith("test-") else None,
    )
    _write_manifest(
        workspace,
        phase=phase,
        iteration=iteration,
        valid=True,
    )
    before_state = workspace.status()
    before_tree = tree_manifest(workspace.layout.domain_root)

    with pytest.raises(ContractError, match="valid rollout manifest cannot be reset"):
        EvolutionWorkflow(workspace).reset_manifest()

    assert workspace.status() == before_state
    assert tree_manifest(workspace.layout.domain_root) == before_tree


@pytest.mark.parametrize("member", ("proof.sidecar.json", "proof.execution.json"))
def test_reset_refuses_symlinked_owned_evidence_without_mutation(
    tmp_path: Path,
    declared_domain,
    member: str,
) -> None:
    workspace = _workspace(tmp_path, declared_domain)
    _advance_to(workspace, LifecycleState.NEEDS_BASELINE_RUN)
    run_dir = _run_dir(workspace, "baseline", 0)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_bytes(b"{broken\n")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    (run_dir / member).symlink_to(outside)
    before_state = workspace.status()

    with pytest.raises(ContractError, match="owned deletion path has no governed root"):
        EvolutionWorkflow(workspace).reset_manifest()

    assert workspace.status() == before_state
    assert (run_dir / "manifest.json").is_file()
    assert (run_dir / member).is_symlink()
    assert outside.read_text(encoding="utf-8") == "outside\n"


def test_reset_refuses_consumed_invalid_manifest_without_mutation(
    tmp_path: Path,
    declared_domain,
) -> None:
    workspace = _workspace(tmp_path, declared_domain)
    _advance_to(workspace, LifecycleState.NEEDS_TRAIN_RUN)
    manifest = _write_manifest(
        workspace,
        phase="train",
        iteration=1,
        valid=False,
    )
    current = workspace.status()
    poisoned = replace(
        current,
        revision=current.revision + 1,
        consumed_manifests=(
            *current.consumed_manifests,
            {"manifest_hash": manifest.digest, "by": "fixture"},
        ),
    )
    workspace.engine.execute(
        operation="fixture-consumed-manifest",
        current_state=_state_json(current),
        next_state=_state_json(poisoned),
        arguments={"purpose": "negative-reset-fixture"},
        input_hashes={"fixture": "f" * 64},
    )
    before_tree = tree_manifest(workspace.layout.domain_root)

    with pytest.raises(ContractError, match="consumed rollout manifest cannot be reset"):
        EvolutionWorkflow(workspace).reset_manifest()

    assert workspace.status() == poisoned
    assert tree_manifest(workspace.layout.domain_root) == before_tree


def test_done_reset_refuses_ambiguous_invalid_prepared_phases_without_mutation(
    tmp_path: Path,
    declared_domain,
) -> None:
    workspace = _workspace(tmp_path, declared_domain)
    _advance_to(
        workspace,
        LifecycleState.DONE,
        test_phase="test-baseline",
    )
    workspace.apply(
        operation="test-prepare",
        supplied=TransitionInput(phase="test-final"),
    )
    for phase in ("test-baseline", "test-final"):
        run_dir = _run_dir(workspace, phase, -1)
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "manifest.json").write_bytes(b"{broken\n")
    before_state = workspace.status()
    before_tree = tree_manifest(workspace.layout.domain_root)

    with pytest.raises(
        TransitionRefused,
        match="exactly one invalid prepared phase",
    ):
        EvolutionWorkflow(workspace).reset_manifest()

    assert workspace.status() == before_state
    assert tree_manifest(workspace.layout.domain_root) == before_tree


@pytest.mark.parametrize(
    "target",
    (
        LifecycleState.NEEDS_OPTIONAL_SEED,
        LifecycleState.NEEDS_PROPOSAL,
        LifecycleState.NEEDS_GATE,
    ),
)
def test_reset_refuses_non_reset_phase_without_mutation(
    tmp_path: Path,
    declared_domain,
    target: LifecycleState,
) -> None:
    workspace = _workspace(tmp_path, declared_domain)
    _advance_to(workspace, target)
    before_state = workspace.status()
    before_tree = tree_manifest(workspace.layout.domain_root)

    with pytest.raises(TransitionRefused, match="refused in the current phase"):
        EvolutionWorkflow(workspace).reset_manifest()

    assert workspace.status() == before_state
    assert tree_manifest(workspace.layout.domain_root) == before_tree
