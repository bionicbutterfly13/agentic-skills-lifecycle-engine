from __future__ import annotations

from dataclasses import replace

import pytest

from asme.contract import LifecycleState, Route
from asme.lifecycle import (
    OPERATIONS,
    DomainState,
    TransitionInput,
    TransitionRefused,
    transition,
    transition_matrix,
)


def _state(state: LifecycleState, **kwargs) -> DomainState:
    return DomainState("domain", "a" * 64, state=state, **kwargs)


def test_hf_a09_total_state_operation_cross_product() -> None:
    matrix = transition_matrix()
    assert set(matrix) == {state.value for state in LifecycleState}
    assert all(set(row) == set(OPERATIONS) for row in matrix.values())
    assert sum(len(row) for row in matrix.values()) == len(LifecycleState) * len(OPERATIONS)
    assert all(
        disposition.startswith(("transition:", "refused:"))
        for row in matrix.values()
        for disposition in row.values()
    )


def test_hf_a22_seed_is_real_one_time_provenance_transition() -> None:
    initial = _state(LifecycleState.UNINITIALIZED)
    optional = transition(initial, "init")
    with pytest.raises(TransitionRefused):
        transition(optional, "seed-observations", TransitionInput(approval_present=True))
    seeded = transition(
        optional,
        "seed-observations",
        TransitionInput(approval_present=True, observation_ids=("obs-2", "obs-1")),
    )
    assert seeded.state is LifecycleState.NEEDS_BASELINE_RUN
    assert seeded.seed_decision == "seeded"
    assert seeded.seeded_observation_ids == ("obs-1", "obs-2")
    with pytest.raises(TransitionRefused):
        transition(seeded, "seed-observations", TransitionInput(approval_present=True, observation_ids=("obs-3",)))
    skipped = transition(optional, "skip-seed")
    assert skipped.seed_decision == "skipped"


def test_paper_strict_gate_requires_fresh_confirmation() -> None:
    current = _state(
        LifecycleState.NEEDS_VAL_RUN,
        iteration=1,
        max_iterations=1,
        best_score=0.5,
        active_snapshot_hash="a" * 64,
        candidate_snapshot_hash="b" * 64,
    )
    validation = transition(
        current,
        "val-ingest",
        TransitionInput(valid=True, score=0.7, phase="val", manifest_hash="c" * 64),
    )
    confirm_needed = transition(validation, "gate")
    assert confirm_needed.state is LifecycleState.NEEDS_VAL_CONFIRM
    confirmation = transition(
        confirm_needed,
        "confirm-ingest",
        TransitionInput(
            valid=True,
            score=0.6,
            phase="val_confirm",
            manifest_hash="d" * 64,
        ),
    )
    accepted = transition(confirmation, "gate")
    assert accepted.state is LifecycleState.DONE
    assert accepted.active_snapshot_hash == "b" * 64
    assert accepted.best_score == 0.6


def test_confirmation_preserves_both_scores_and_promotes_their_minimum() -> None:
    current = _state(
        LifecycleState.NEEDS_VAL_RUN,
        iteration=1,
        max_iterations=1,
        best_score=0.5,
        active_snapshot_hash="a" * 64,
        candidate_snapshot_hash="b" * 64,
    )
    state = transition(
        current,
        "val-ingest",
        TransitionInput(valid=True, score=0.6, phase="val", manifest_hash="c" * 64),
    )
    state = transition(state, "gate")
    state = transition(
        state,
        "confirm-ingest",
        TransitionInput(
            valid=True,
            score=0.7,
            phase="val_confirm",
            manifest_hash="d" * 64,
        ),
    )
    assert state.provisional_score == 0.6
    assert state.confirmation_score == 0.7
    accepted = transition(state, "gate")
    assert accepted.best_score == 0.6


def test_equal_score_rejects_and_never_switches_active_pointer() -> None:
    current = _state(
        LifecycleState.NEEDS_GATE,
        iteration=1,
        max_iterations=1,
        best_score=0.5,
        provisional_score=0.5,
        gate_phase="validation",
        current_manifest_hash="c" * 64,
        current_manifest_phase="val",
        active_snapshot_hash="a" * 64,
        candidate_snapshot_hash="b" * 64,
    )
    rejected = transition(current, "gate")
    assert rejected.state is LifecycleState.DONE
    assert rejected.active_snapshot_hash == "a" * 64


def test_hf_a10_corrupt_train_reset_returns_to_train_owner() -> None:
    wiki_phase = _state(LifecycleState.NEEDS_WIKI, iteration=1, best_score=0.2)
    reset = transition(wiki_phase, "reset-manifest")
    assert reset.state is LifecycleState.NEEDS_TRAIN_RUN
    assert reset.revision == wiki_phase.revision + 1


def test_hf_a19_routes_are_durable_exclusive_and_idempotent() -> None:
    done = _state(LifecycleState.DONE, best_score=1.0)
    prepared = transition(done, "test-prepare", TransitionInput(phase="test-baseline"))
    assert prepared.route is Route.VALIDATED and prepared.validated_step == "prepared"
    assert (
        transition(prepared, "test-prepare", TransitionInput(phase="test-baseline"))
        is prepared
    )
    ingested = transition(
        prepared,
        "test-ingest",
        TransitionInput(
            valid=True, phase="test-baseline", manifest_hash="e" * 64
        ),
    )
    ingested = transition(
        ingested,
        "test-prepare",
        TransitionInput(phase="test-final"),
    )
    ingested = transition(
        ingested,
        "test-ingest",
        TransitionInput(valid=True, phase="test-final", manifest_hash="f" * 64),
    )
    exported = transition(
        ingested,
        "export",
        TransitionInput(valid=True, delivery_id="stage-1"),
    )
    assert exported.validated_step == "exported"
    assert transition(
        exported, "export", TransitionInput(valid=True, delivery_id="stage-1")
    ) is exported
    with pytest.raises(TransitionRefused):
        transition(exported, "package-untested", TransitionInput(approval_present=True, delivery_id="stage-1"))
    untested_input = TransitionInput(
        approval_present=True,
        approval_id="approval-stage-2",
        approval_hash="1" * 64,
        approval_record_hash="2" * 64,
        delivery_id="stage-2",
    )
    untested = transition(
        done,
        "package-untested",
        untested_input,
    )
    assert untested.route is Route.UNTESTED
    assert transition(untested, "package-untested", untested_input) is untested
    with pytest.raises(TransitionRefused):
        transition(
            untested,
            "package-untested",
            replace(untested_input, approval_hash="3" * 64),
        )
    with pytest.raises(TransitionRefused):
        transition(untested, "test-prepare", TransitionInput(phase="test-baseline"))


def test_invalid_ingest_has_no_state_effect() -> None:
    train = _state(LifecycleState.NEEDS_TRAIN_RUN, iteration=1, best_score=0.1)
    assert transition(train, "train-ingest", TransitionInput(valid=False)) is train
    with pytest.raises(TransitionRefused):
        transition(replace(train, txn={"pending": True}), "status-bogus")


def test_abandon_is_candidate_only_and_consumes_owned_valid_manifest() -> None:
    proposal = _state(
        LifecycleState.NEEDS_PROPOSAL,
        iteration=1,
        max_iterations=1,
        best_score=0.1,
        active_snapshot_hash="a" * 64,
    )
    with pytest.raises(TransitionRefused):
        transition(proposal, "abandon")
    candidate = transition(
        proposal,
        "apply-proposal-change",
        TransitionInput(snapshot_hash="b" * 64),
    )
    gated = transition(
        candidate,
        "val-ingest",
        TransitionInput(
            valid=True,
            score=0.2,
            phase="val",
            manifest_hash="3" * 64,
        ),
    )
    abandoned = transition(gated, "abandon")
    assert abandoned.state is LifecycleState.DONE
    assert abandoned.active_snapshot_hash == "a" * 64
    assert abandoned.consumed_manifests[-1] == {
        "manifest_hash": "3" * 64,
        "by": "abandon",
    }


def test_manifests_are_consumed_once_and_validated_export_requires_test_pair() -> None:
    baseline_hash = "1" * 64
    train_hash = "2" * 64
    val_hash = "3" * 64
    confirm_hash = "4" * 64
    test_baseline_hash = "5" * 64
    test_final_hash = "6" * 64
    state = _state(LifecycleState.NEEDS_BASELINE_RUN, max_iterations=1)
    state = transition(
        state,
        "baseline-finalize",
        TransitionInput(
            valid=True,
            score=0.25,
            snapshot_hash="a" * 64,
            manifest_hash=baseline_hash,
            phase="baseline",
        ),
    )
    assert state.consumed_manifests == (
        {"manifest_hash": baseline_hash, "by": "baseline-finalize"},
    )
    state = transition(
        state,
        "train-ingest",
        TransitionInput(valid=True, manifest_hash=train_hash, phase="train"),
    )
    state = transition(state, "apply-wiki")
    assert {item["manifest_hash"] for item in state.consumed_manifests} == {
        baseline_hash,
        train_hash,
    }
    state = transition(
        state,
        "apply-proposal-change",
        TransitionInput(snapshot_hash="b" * 64),
    )
    state = transition(
        state,
        "val-ingest",
        TransitionInput(valid=True, score=0.5, manifest_hash=val_hash, phase="val"),
    )
    state = transition(state, "gate")
    assert state.provisional_manifest_hash == val_hash
    state = transition(
        state,
        "confirm-ingest",
        TransitionInput(
            valid=True,
            score=0.5,
            manifest_hash=confirm_hash,
            phase="val_confirm",
        ),
    )
    state = transition(state, "gate")
    assert state.state is LifecycleState.DONE
    assert {item["manifest_hash"] for item in state.consumed_manifests} == {
        baseline_hash,
        train_hash,
        val_hash,
        confirm_hash,
    }

    state = transition(state, "test-prepare", TransitionInput(phase="test-baseline"))
    state = transition(
        state,
        "test-ingest",
        TransitionInput(
            valid=True,
            phase="test-baseline",
            manifest_hash=test_baseline_hash,
        ),
    )
    with pytest.raises(TransitionRefused, match="both test manifests"):
        transition(
            state,
            "export",
            TransitionInput(valid=True, delivery_id="stage-pair"),
        )
    state = transition(state, "test-prepare", TransitionInput(phase="test-final"))
    state = transition(
        state,
        "test-ingest",
        TransitionInput(valid=True, phase="test-final", manifest_hash=test_final_hash),
    )
    exported = transition(
        state,
        "export",
        TransitionInput(valid=True, delivery_id="stage-pair"),
    )
    assert exported.validated_step == "exported"
    assert {item["manifest_hash"] for item in exported.consumed_manifests} >= {
        test_baseline_hash,
        test_final_hash,
    }
