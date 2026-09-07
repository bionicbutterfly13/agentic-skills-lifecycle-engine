from __future__ import annotations

import base64
from dataclasses import replace
import ast
import hashlib
import json
from pathlib import Path
import re

import pytest

from asme.canonical import ContractError, canonical_bytes
from asme.claims import (
    BootstrapEvidence,
    ClaimClass,
    RunEvidence,
    evaluate_claim,
)
from asme.contract import TraceFidelity
from asme.dependencies import DependencyKind, default_dependency_matrix
from asme.gate2 import DEFAULT_GATE2_POLICY, compare_gate2
from asme.governance import (
    DEVELOPMENT_DECISIONS,
    DecisionStatus,
    HISTORICAL_PLAN_REVISION,
    HISTORICAL_PLAN_SOUND_VERDICT,
    HISTORICAL_PLAN_STATUS,
    PAPER_ATTRIBUTION,
    require_phase_authorized,
)
from asme.impact import ImpactOutcome, append_impact, create_impact
from asme.lifecycle import DomainState, TransitionInput, transition
from asme.contract import LifecycleState
from asme.snapshot import Snapshot
from asme.transaction import RecoveryCorruption, SimulatedCrash
from asme.source_registry import (
    PUBLIC_ARTIFACTS,
    default_source_registry,
    default_source_registry_bytes,
)
from asme.package import scan_community_safety
from test_terminal_paths import TerminalHarness


_COMMON_DEPENDENCIES = (
    (DependencyKind.ARGUMENT, "operation_arguments"),
    (DependencyKind.STATE, "state"),
    (DependencyKind.CLOCK, "clock"),
    (DependencyKind.OUTPUT, "output_plan"),
)
_EXPECTED_SPECIFIC_DEPENDENCIES = (
    ("prepare-rollout", ((DependencyKind.SEAL, "seal"), (DependencyKind.DYNAMIC_INPUT, "named_snapshot"))),
    ("record-execution", ((DependencyKind.DYNAMIC_INPUT, "prepared_job_record"), (DependencyKind.DYNAMIC_INPUT, "captured_execution"))),
    ("ingest-rollout", ((DependencyKind.SEAL, "seal"), (DependencyKind.DYNAMIC_INPUT, "prompts"), (DependencyKind.DYNAMIC_INPUT, "submitted_outputs"))),
    ("reset-manifest", ((DependencyKind.DYNAMIC_INPUT, "manifest"), (DependencyKind.DYNAMIC_INPUT, "manifest_sidecars"))),
    ("baseline-finalize", ((DependencyKind.DYNAMIC_INPUT, "baseline_manifest"), (DependencyKind.DYNAMIC_INPUT, "baseline_sidecars"))),
    ("sample", ((DependencyKind.DYNAMIC_INPUT, "train_manifest"), (DependencyKind.DYNAMIC_INPUT, "raw_traces"), (DependencyKind.DYNAMIC_INPUT, "raw_sidecars"), (DependencyKind.DYNAMIC_INPUT, "wiki"))),
    ("apply-wiki", ((DependencyKind.DYNAMIC_INPUT, "maintainer_output"), (DependencyKind.DYNAMIC_INPUT, "maintainer_input"), (DependencyKind.DYNAMIC_INPUT, "wiki"), (DependencyKind.DYNAMIC_INPUT, "train_manifest"))),
    ("proposer-context", ((DependencyKind.DYNAMIC_INPUT, "wiki"), (DependencyKind.DYNAMIC_INPUT, "train_manifest"), (DependencyKind.DYNAMIC_INPUT, "raw_sidecars"), (DependencyKind.DYNAMIC_INPUT, "train_answers"), (DependencyKind.DYNAMIC_INPUT, "active_snapshot"))),
    ("apply-proposal", ((DependencyKind.DYNAMIC_INPUT, "proposal_output"), (DependencyKind.DYNAMIC_INPUT, "active_snapshot"), (DependencyKind.SEAL, "seal_markers"))),
    ("gate", ((DependencyKind.DYNAMIC_INPUT, "evaluation_manifests"), (DependencyKind.DYNAMIC_INPUT, "evaluation_sidecars"), (DependencyKind.DYNAMIC_INPUT, "candidate_snapshot"), (DependencyKind.DYNAMIC_INPUT, "active_snapshot"), (DependencyKind.DYNAMIC_INPUT, "provisional"))),
    ("abandon", ((DependencyKind.DYNAMIC_INPUT, "evaluation_manifests"), (DependencyKind.DYNAMIC_INPUT, "evaluation_sidecars"), (DependencyKind.DYNAMIC_INPUT, "candidate_snapshot"), (DependencyKind.DYNAMIC_INPUT, "provisional"))),
    ("export", ((DependencyKind.DYNAMIC_INPUT, "test_manifests"), (DependencyKind.DYNAMIC_INPUT, "test_sidecars"), (DependencyKind.DYNAMIC_INPUT, "active_snapshot"), (DependencyKind.SEAL, "seal"), (DependencyKind.ROUTE, "delivery_route"), (DependencyKind.NEGATIVE_EXISTENCE, "existing_staging_target"))),
    ("package-untested", ((DependencyKind.DYNAMIC_INPUT, "active_snapshot"), (DependencyKind.DYNAMIC_INPUT, "untested_approval"), (DependencyKind.SEAL, "seal"), (DependencyKind.ROUTE, "delivery_route"), (DependencyKind.NEGATIVE_EXISTENCE, "test_artifacts_absent"), (DependencyKind.NEGATIVE_EXISTENCE, "existing_staging_target"))),
    ("recover", ((DependencyKind.REPLAY_SOURCE, "state_transaction"),)),
)
_EXPECTED_DEPENDENCY_CELLS = tuple(
    (f"dep-{sequence:03d}", operation, kind, name)
    for sequence, (operation, kind, name) in enumerate(
        (
            (operation, kind, name)
            for operation, specific in _EXPECTED_SPECIFIC_DEPENDENCIES
            for kind, name in (*_COMMON_DEPENDENCIES, *specific)
        ),
        start=1,
    )
)


def test_hf_a01_revision_8_status_never_becomes_sound() -> None:
    assert HISTORICAL_PLAN_REVISION == 8
    assert HISTORICAL_PLAN_STATUS == "NEEDS REVISION"
    assert HISTORICAL_PLAN_SOUND_VERDICT is False


def test_hf_a02_paper_attribution_and_local_rules_stay_distinct() -> None:
    assert PAPER_ATTRIBUTION["arxiv_id"] == "2608.27454v1"
    assert PAPER_ATTRIBUTION["source_license"] == "CC BY 4.0"
    assert "not a literal replication" in PAPER_ATTRIBUTION["adaptation_notice"]
    assert DEVELOPMENT_DECISIONS["A2"].source_class == "ARCHITECTURE_DEFAULT"


def _provenance_record(text: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}$.*?^```text\n(.*?)\n```$",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None
    return match.group(1)


def test_current_authority_and_attribution_sources_are_hash_reconstructable() -> None:
    provenance = (Path(__file__).parents[1] / "PROVENANCE.md").read_text(
        encoding="utf-8"
    )
    goal = _provenance_record(provenance, "Current development authority")
    owner_requirement = _provenance_record(
        provenance, "Owner attribution requirement"
    )

    assert hashlib.sha256(goal.encode("utf-8")).hexdigest() == (
        "c8966236b915aee64067f03ae28a7d6028c31b171b3b8e7c771ef2e7fed6e809"
    )
    assert hashlib.sha256(owner_requirement.encode("utf-8")).hexdigest() == (
        "8245fd2d7d6205935cd948b9af01a199d82f24118854192580c75237e3e13ac8"
    )
    registry = {entry.entry_id: entry for entry in default_source_registry().entries}
    assert registry["A1"].source_locator == DEVELOPMENT_DECISIONS["A1"].source_locator
    assert registry["A4"].source_locator == DEVELOPMENT_DECISIONS["A4"].source_locator
    assert registry["A5"].source_locator == DEVELOPMENT_DECISIONS["A5"].source_locator
    assert registry["A1"].source_locator.startswith(
        "PROVENANCE.md#current-development-authority; sha256:"
    )
    assert registry["A4"].source_locator.startswith(
        "PROVENANCE.md#owner-attribution-requirement; sha256:"
    )
    normalized = " ".join(provenance.split())
    assert "UTF-8 bytes of the exact fenced text, with no trailing newline" in normalized
    assert "/Users/" not in provenance and "/Volumes/" not in provenance


def test_hf_a02_complete_source_registry_is_serializable_and_package_safe() -> None:
    registry = default_source_registry()
    by_kind: dict[str, list[str]] = {}
    for entry in registry.entries:
        by_kind.setdefault(entry.kind, []).append(entry.entry_id)
        assert entry.source_class
        assert entry.source_locator
        assert entry.decision_status
    assert by_kind["source_parity"] == [f"SP-{index:03d}" for index in range(1, 107)]
    assert by_kind["acceptance"] == [f"HF-A{index:02d}" for index in range(1, 28)]
    assert by_kind["historical_gate_a"] == [f"GA-{index:02d}" for index in range(1, 6)]
    assert by_kind["development_gate_a"] == [f"A{index}" for index in range(1, 6)]
    assert by_kind["public_artifact"] == [
        f"PUB-{index:03d}" for index in range(1, len(PUBLIC_ARTIFACTS) + 1)
    ]
    assert tuple(entry.source_locator for entry in registry.entries if entry.kind == "public_artifact") == PUBLIC_ARTIFACTS
    encoded = default_source_registry_bytes()
    assert registry.digest
    scan_community_safety({"source-registry.json": encoded})
    assert b"/Users/" not in encoded and b"/Volumes/" not in encoded


def test_every_locked_source_registry_locator_resolves_inside_candidate() -> None:
    package_root = Path(__file__).parents[1]
    locked_entries = tuple(
        entry
        for entry in default_source_registry().entries
        if entry.source_locator.startswith("locked/")
    )
    assert len(locked_entries) == 140
    expected_hashes = {
        "locked/architecture-contract.md": (
            "63c32497e5c14fd8ea95138731d4b12c11c4d1dd910eb698b8f2fb03b3aafac0"
        ),
        "locked/source-parity-matrix.md": (
            "240f7211792b0b0dc0fc077d2008341b679515ad27b0b44957b673f2a3fa73ad"
        ),
        "locked/acceptance-matrix.md": (
            "15c6d089e666e4d2f60f86cbb91e4d5ee295b8dd66df30e543d0ad3177d4a25a"
        ),
    }
    contents: dict[str, bytes] = {}
    for relative, expected_hash in expected_hashes.items():
        path = package_root / relative
        assert path.is_file() and not path.is_symlink()
        content = path.read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected_hash
        contents[relative] = content
    scan_community_safety(contents)

    for entry in locked_entries:
        relative, marker = entry.source_locator.split(";", 1)[0].split(":", 1)
        text = contents[relative].decode("utf-8")
        if entry.entry_id.startswith(("SP-", "HF-A", "GA-")):
            rows = re.findall(
                rf"^\| {re.escape(entry.entry_id)}(?: \|| )",
                text,
                flags=re.MULTILINE,
            )
            assert len(rows) == 1
        else:
            assert entry.entry_id in {"A2", "A3"}
            assert text.count(f"### {entry.entry_id}.") == 1
            assert marker == f"section-16-{entry.entry_id}"


def test_hf_a03_adapters_do_not_fork_core_semantics() -> None:
    package_root = Path(__file__).parents[1]
    adapter_root = package_root / "adapters"
    semantic_modules = {"lifecycle", "transaction", "evaluation", "wiki", "snapshot", "claims"}
    assert not any(path.stem in semantic_modules for path in adapter_root.rglob("*.py"))
    imported_core_modules = set()
    for path in adapter_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(
                "asme."
            ):
                imported_core_modules.add(node.module)
    assert imported_core_modules == {"asme.contract"}


def test_hf_a04_paper_lifecycle_and_impact_history_are_retained() -> None:
    empty = Snapshot.empty()
    state = DomainState(
        "domain",
        "a" * 64,
        state=LifecycleState.NEEDS_BASELINE_RUN,
        active_snapshot_hash=empty.snapshot_hash,
        max_iterations=1,
    )
    state = transition(
        state,
        "baseline-finalize",
        TransitionInput(
            valid=True,
            score=0.4,
            snapshot_hash="b" * 64,
            phase="baseline",
            manifest_hash="1" * 64,
        ),
    )
    assert state.state is LifecycleState.NEEDS_TRAIN_RUN
    state = transition(
        state,
        "train-ingest",
        TransitionInput(valid=True, phase="train", manifest_hash="2" * 64),
    )
    assert state.state is LifecycleState.NEEDS_WIKI
    state = transition(state, "apply-wiki")
    assert state.state is LifecycleState.NEEDS_PROPOSAL
    state = transition(
        state,
        "apply-proposal-change",
        TransitionInput(snapshot_hash="c" * 64),
    )
    assert state.state is LifecycleState.NEEDS_VAL_RUN
    rejected = create_impact(
        domain_id="domain",
        iteration=1,
        outcome=ImpactOutcome.REJECTED,
        active_before="b" * 64,
        candidate_snapshot="c" * 64,
        active_after="b" * 64,
        scores=(0.3,),
        unified_diff="-old\n+new\n",
    )
    history = append_impact((), rejected)
    assert append_impact(history, rejected) == history
    assert history[0].active_after == history[0].active_before


def test_hf_a18_every_dependency_cell_has_a_drift_fixture() -> None:
    matrix = default_dependency_matrix()
    actual = tuple(
        (cell.cell_id, cell.operation, cell.kind, cell.name)
        for cell in matrix.cells
        if cell.required
    )
    assert actual == _EXPECTED_DEPENDENCY_CELLS
    matrix.verify_fixture_coverage(cell_id for cell_id, *_ in _EXPECTED_DEPENDENCY_CELLS)


@pytest.mark.parametrize(
    "expected_cell",
    _EXPECTED_DEPENDENCY_CELLS,
    ids=(cell_id for cell_id, *_ in _EXPECTED_DEPENDENCY_CELLS),
)
def test_hf_a18_each_independently_inventoried_cell_refuses_real_preintent_drift(
    tmp_path: Path,
    expected_cell: tuple[str, str, DependencyKind, str],
) -> None:
    cell_id, operation, target_kind, target_name = expected_cell
    harness = TerminalHarness(tmp_path, case_id=cell_id, max_iterations=1)
    if operation == "recover":
        _assert_real_recovery_refuses_drift(
            harness,
            target_kind=target_kind,
            target_name=target_name,
        )
        return

    original_execute = harness.workspace.engine.execute
    target_seen = False
    status_before_drift: list[object] = []

    def execute_with_one_drift(**kwargs: object) -> dict[str, object]:
        nonlocal target_seen
        arguments = dict(kwargs.get("arguments", {}))
        if arguments.get("dependency_operation") != operation:
            return original_execute(**kwargs)
        if target_seen:
            return original_execute(**kwargs)
        target_seen = True
        status_before_drift.append(harness.workspace.status())
        drifted = _drift_real_operation_call(
            harness,
            kwargs,
            target_kind=target_kind,
            target_name=target_name,
        )
        return original_execute(**drifted)

    harness.workspace.engine.execute = execute_with_one_drift
    with pytest.raises(ContractError):
        _exercise_real_dependency_operation(harness, operation)
    assert target_seen
    assert harness.workspace.status() == status_before_drift[0]


@pytest.mark.parametrize("operation", ("export", "package-untested"))
def test_hf_a18_route_hash_drift_alone_hits_dedicated_route_refusal(
    tmp_path: Path, operation: str
) -> None:
    harness = TerminalHarness(
        tmp_path, case_id=f"route-{operation}", max_iterations=1
    )
    original_execute = harness.workspace.engine.execute
    target_seen = False

    def execute_with_route_hash_drift(**kwargs: object) -> dict[str, object]:
        nonlocal target_seen
        arguments = dict(kwargs.get("arguments", {}))
        if arguments.get("dependency_operation") != operation or target_seen:
            return original_execute(**kwargs)
        target_seen = True
        drifted = dict(kwargs)
        hashes = dict(kwargs.get("input_hashes", {}))
        hashes["delivery_route"] = "f" * 64
        drifted["input_hashes"] = hashes
        return original_execute(**drifted)

    harness.workspace.engine.execute = execute_with_route_hash_drift
    with pytest.raises(ContractError, match="delivery route binding drifted"):
        _exercise_real_dependency_operation(harness, operation)
    assert target_seen


def _drift_real_operation_call(
    harness: TerminalHarness,
    supplied: dict[str, object],
    *,
    target_kind: DependencyKind,
    target_name: str,
) -> dict[str, object]:
    kwargs = dict(supplied)
    arguments = dict(kwargs.get("arguments", {}))
    hashes = dict(kwargs.get("input_hashes", {}))
    kwargs["arguments"] = arguments
    kwargs["input_hashes"] = hashes

    if target_kind is DependencyKind.ARGUMENT:
        arguments["preintent_drift"] = target_name
    elif target_kind is DependencyKind.STATE:
        hashes["state"] = "f" * 64
    elif target_kind is DependencyKind.CLOCK:
        arguments["clock"] = str(arguments["clock"]) + "+drift"
    elif target_kind is DependencyKind.OUTPUT:
        next_state = dict(kwargs["next_state"])
        next_state["revision"] = int(next_state.get("revision", 0)) + 1000
        kwargs["next_state"] = next_state
    elif target_kind is DependencyKind.SEAL:
        if target_name == "seal":
            hashes[target_name] = "f" * 64
        else:
            dependency = next(
                item for item in kwargs.get("reads", ()) if item.name == target_name
            )
            target = (
                harness.workspace.engine.target_roots[dependency.root]
                / dependency.path
            )
            target.write_bytes(target.read_bytes() + b"\nseal drift\n")
    elif target_kind is DependencyKind.ROUTE:
        arguments["delivery_route"] = "drifted"
    elif target_kind is DependencyKind.NEGATIVE_EXISTENCE:
        absence = next(
            item for item in kwargs.get("absences", ()) if item.name == target_name
        )
        target = harness.workspace.engine.target_roots[absence.root] / absence.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"unexpected\n")
    elif target_kind is DependencyKind.DYNAMIC_INPUT:
        values = list(kwargs.get("values", ()))
        for index, value in enumerate(values):
            if value.name == target_name:
                values[index] = replace(
                    value,
                    content_base64=base64.b64encode(b"preintent drift").decode("ascii"),
                )
                kwargs["values"] = tuple(values)
                break
        else:
            dependencies = (
                *kwargs.get("reads", ()),
                *kwargs.get("tree_reads", ()),
            )
            dependency = next(
                (item for item in dependencies if item.name == target_name),
                None,
            )
            if dependency is None:
                hashes[target_name] = "f" * 64
            else:
                target = (
                    harness.workspace.engine.target_roots[dependency.root]
                    / dependency.path
                )
                if target.is_dir():
                    member = next(path for path in target.rglob("*") if path.is_file())
                    member.write_bytes(member.read_bytes() + b"\npreintent drift\n")
                else:
                    target.write_bytes(target.read_bytes() + b"\npreintent drift\n")
    else:  # pragma: no cover - recovery owns the only replay-source cell
        raise AssertionError(f"unsupported real-operation drift kind: {target_kind}")
    return kwargs


def _exercise_real_dependency_operation(
    harness: TerminalHarness, operation: str
) -> None:
    if operation == "prepare-rollout":
        harness.run_phase("baseline", 0.25)
    elif operation in {"record-execution", "ingest-rollout"}:
        harness.run_phase("baseline", 0.25)
    elif operation == "reset-manifest":
        harness.run_phase("baseline", 0.25, invalid=True)
        harness.workflow.reset_manifest()
    elif operation == "baseline-finalize":
        harness.run_phase("baseline", 0.25)
        harness.workflow.finalize_baseline()
    elif operation == "sample":
        harness.baseline(0.25)
        harness.run_phase("train", 1.0)
        harness.workflow.sample_train()
    elif operation in {"apply-wiki", "proposer-context", "apply-proposal"}:
        harness.baseline(0.25)
        harness.proposal("create")
    elif operation == "gate":
        harness.baseline(0.25)
        harness.proposal("create")
        harness.run_phase("val", 0.5)
        harness.workflow.gate()
    elif operation == "abandon":
        harness.baseline(0.25)
        harness.proposal("create")
        harness.workflow.abandon_candidate()
    elif operation == "export":
        harness.baseline(0.25)
        harness.proposal("create")
        harness.accept(0.5, 0.5)
        harness.run_phase("test-baseline", 1.0)
        harness.run_phase("test-final", 1.0)
        harness.stage_validated()
    elif operation == "package-untested":
        harness.baseline(0.25)
        harness.proposal("create", test_label="not_run")
        harness.accept(0.5, 0.5)
        harness.stage_untested()
    else:  # pragma: no cover - matrix and helper must evolve together
        raise AssertionError(f"unhandled real dependency operation: {operation}")


def _assert_real_recovery_refuses_drift(
    harness: TerminalHarness,
    *,
    target_kind: DependencyKind,
    target_name: str,
) -> None:
    original_execute = harness.workspace.engine.execute

    def crash_real_prepare(**kwargs: object) -> dict[str, object]:
        if kwargs.get("arguments", {}).get("dependency_operation") == "prepare-rollout":
            kwargs = {**kwargs, "crash_at": "post-intent"}
        return original_execute(**kwargs)

    harness.workspace.engine.execute = crash_real_prepare
    with pytest.raises(SimulatedCrash):
        harness.run_phase("baseline", 0.25)
    harness.workspace.engine.execute = original_execute

    pending = json.loads(harness.workspace.engine.state_path.read_text(encoding="utf-8"))
    transaction = pending["txn"]
    if target_kind is DependencyKind.ARGUMENT:
        transaction["arguments"]["preintent_drift"] = target_name
    elif target_kind is DependencyKind.STATE:
        transaction["input_hashes"]["state"] = "f" * 64
    elif target_kind is DependencyKind.CLOCK:
        transaction["arguments"]["clock"] += "+drift"
    elif target_kind is DependencyKind.OUTPUT:
        transaction["next_state"]["revision"] += 1000
    elif target_kind is DependencyKind.REPLAY_SOURCE:
        transaction["transaction_id"] = "f" * 64
    else:  # pragma: no cover - recover has only common plus replay-source cells
        raise AssertionError(f"unsupported recovery drift kind: {target_kind}")
    harness.workspace.engine.state_path.write_bytes(canonical_bytes(pending))

    with pytest.raises(RecoveryCorruption):
        harness.workspace.recover()


def test_hf_a18_binding_coverage_requires_positive_and_negative_cells() -> None:
    matrix = default_dependency_matrix()
    for operation in sorted({cell.operation for cell in matrix.cells}):
        cells = matrix.operation_cells(operation)
        values = {
            cell.name
            for cell in cells
            if cell.kind is not DependencyKind.NEGATIVE_EXISTENCE
        }
        absences = {
            cell.name for cell in cells if cell.kind is DependencyKind.NEGATIVE_EXISTENCE
        }
        matrix.verify_binding_coverage(
            operation=operation,
            value_names=values,
            material_names=(
                cell.name
                for cell in cells
                if cell.kind is DependencyKind.DYNAMIC_INPUT
            ),
            read_names=(),
            absence_names=absences,
        )
        required_specific = sorted(
            values - {"operation_arguments", "state", "clock"}
        )
        if required_specific:
            with pytest.raises(ContractError, match="missing_positive"):
                matrix.verify_binding_coverage(
                    operation=operation,
                    value_names=values - {required_specific[0]},
                    material_names=(
                        cell.name
                        for cell in cells
                        if cell.kind is DependencyKind.DYNAMIC_INPUT
                        and cell.name != required_specific[0]
                    ),
                    read_names=(),
                    absence_names=absences,
                )
        if absences:
            with pytest.raises(ContractError, match="missing_absence"):
                matrix.verify_binding_coverage(
                    operation=operation,
                    value_names=values,
                    material_names=(
                        cell.name
                        for cell in cells
                        if cell.kind is DependencyKind.DYNAMIC_INPUT
                    ),
                    read_names=(),
                    absence_names=(),
                )


def test_hf_a18_every_matrix_operation_has_a_real_binding_path() -> None:
    package_root = Path(__file__).parents[1]
    bound: set[str] = set()
    for relative in (
        "src/asme/workflow.py",
        "src/asme/delivery.py",
    ):
        tree = ast.parse((package_root / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg != "dependency_operation":
                    continue
                bound.update(
                    item.value
                    for item in ast.walk(keyword.value)
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                )
    operations = {cell.operation for cell in default_dependency_matrix().cells}
    assert bound == operations - {"recover"}


def test_hf_a18_every_operation_binds_exact_output_plan() -> None:
    matrix = default_dependency_matrix()
    for operation in sorted({cell.operation for cell in matrix.cells}):
        output_cells = {
            cell.name
            for cell in matrix.operation_cells(operation)
            if cell.kind is DependencyKind.OUTPUT
        }
        assert output_cells == {"output_plan"}


def _gate_record(*, score=1.0):
    return {
        "archive": {"tree_sha256": "a" * 64},
        "domain": {"seal": "b" * 64},
        "ledger": {"consistent": True},
        "manifest": {"complete": True, "valid": True},
        "package": {"staged_tree_sha256": "a" * 64},
        "state": {"phase": "DONE"},
        "outcomes": {"impact_sequence": ["Accepted"], "scores": [score], "snapshot_empty": False},
    }


def test_hf_a21_gate2_fails_bindings_but_reports_llm_differences() -> None:
    expected = _gate_record(score=0.8)
    actual = _gate_record(score=0.9)
    result = compare_gate2(
        expected=expected,
        actual=actual,
        expected_policy_hash=DEFAULT_GATE2_POLICY.digest,
    )
    assert result.passed and [item.path for item in result.reported_differences] == [
        "outcomes.scores"
    ]
    actual["manifest"]["valid"] = False
    failed = compare_gate2(expected=expected, actual=actual)
    assert not failed.passed and failed.failures[0].path == "manifest.valid"


def test_hf_a26_public_claim_requires_three_runs_and_paired_bootstrap() -> None:
    run = RunEvidence(
        "run-1",
        baseline_score=0.4,
        validation_score=0.6,
        confirmation_score=0.5,
        complete=True,
        trace_fidelity=TraceFidelity.OBSERVABLE_TRANSCRIPT,
        isolation_label="unsandboxed",
    )
    local = evaluate_claim(claim_class=ClaimClass.LOCAL_ACCEPTANCE, runs=(run,))
    assert local.allowed
    public = evaluate_claim(claim_class=ClaimClass.PAPER_COMPARABLE_PUBLIC, runs=(run,))
    assert not public.allowed and public.disclaimer
    runs = (run, replace(run, run_id="run-2"), replace(run, run_id="run-3"))
    bootstrap = BootstrapEvidence(
        run_ids=("run-1", "run-2", "run-3"),
        paired=True,
        complete=True,
        method="paired bootstrap",
        artifact_hash="c" * 64,
    )
    assert evaluate_claim(
        claim_class=ClaimClass.PAPER_COMPARABLE_PUBLIC,
        runs=runs,
        bootstrap=bootstrap,
    ).allowed


def test_hf_a25_and_a27_gate_a_signed_publication_authorized_install_gated() -> None:
    registry_decisions = {
        entry.entry_id: entry
        for entry in default_source_registry().entries
        if entry.kind == "development_gate_a"
    }
    for decision_id, decision in DEVELOPMENT_DECISIONS.items():
        assert decision.source_locator
        assert registry_decisions[decision_id].source_locator == decision.source_locator
        assert decision.status is not DecisionStatus.UNRESOLVED
    a4 = DEVELOPMENT_DECISIONS["A4"]
    assert "free community use" in a4.value
    assert "attribution" in a4.value
    assert "manysaintvictormd.com" in a4.value
    assert "MIT" in a4.value and "CC BY 4.0" in a4.value
    assert a4.status is DecisionStatus.ADOPTED
    assert "Gate A approval record" in a4.value
    require_phase_authorized("implementation")
    require_phase_authorized("publication")
    require_phase_authorized("distribution")
    with pytest.raises(ContractError, match="separate action-time approval"):
        require_phase_authorized("live_installation")
