from __future__ import annotations

import pytest

from asme.bootstrap import BOOTSTRAP_SCHEMA, build_paired_bootstrap
from asme.canonical import ContractError, sha256_bytes
from asme.claims import ClaimClass, RunEvidence, evaluate_claim
from asme.contract import TraceFidelity
from asme.evalreport import EvalRun, EvalTaskScore


def _score(task_id: str, score: float) -> EvalTaskScore:
    return EvalTaskScore(
        task_id=task_id,
        score=score,
        output_hash=sha256_bytes(f"{task_id}:{score}".encode("utf-8")),
    )


def _run(run_id: str, *, baseline: float, final: float) -> EvalRun:
    tasks = ("task-1", "task-2", "task-3", "task-4")
    return EvalRun(
        run_id=run_id,
        phase_scores={
            "baseline": tuple(_score(task, baseline) for task in tasks),
            "validation": tuple(_score(task, final) for task in tasks),
            "confirmation": tuple(_score(task, final) for task in tasks),
        },
    )


def _evidence(run: EvalRun) -> RunEvidence:
    return RunEvidence(
        run_id=run.run_id,
        baseline_score=run.aggregate("baseline"),
        validation_score=run.aggregate("validation"),
        confirmation_score=run.aggregate("confirmation"),
        complete=True,
        trace_fidelity=TraceFidelity.FINAL_ONLY,
        isolation_label="scripted-offline-fixture",
    )


_RUNS = tuple(
    _run(f"run-{index}", baseline=0.25, final=1.0) for index in (1, 2, 3)
)


def test_bootstrap_artifact_is_deterministic_and_hash_bound() -> None:
    first = build_paired_bootstrap(runs=_RUNS, seed=7, resamples=1200)
    second = build_paired_bootstrap(runs=_RUNS, seed=7, resamples=1200)
    assert first.artifact == second.artifact
    assert first.payload["schema"] == BOOTSTRAP_SCHEMA
    assert first.payload["observed_mean_diff"] == 0.75
    assert first.evidence.artifact_hash == sha256_bytes(first.artifact)
    assert first.evidence.paired is True
    assert first.evidence.complete is True
    assert sorted(first.evidence.run_ids) == ["run-1", "run-2", "run-3"]


def test_three_run_paper_comparable_claim_passes_end_to_end() -> None:
    result = build_paired_bootstrap(runs=_RUNS, seed=7, resamples=1200)
    decision = evaluate_claim(
        claim_class=ClaimClass.PAPER_COMPARABLE_PUBLIC,
        runs=tuple(_evidence(run) for run in _RUNS),
        bootstrap=result.evidence,
    )
    assert decision.allowed is True
    assert decision.label == "paper_comparable"
    assert decision.reasons == ()


def test_insufficient_runs_refuse_the_paper_claim() -> None:
    result = build_paired_bootstrap(runs=_RUNS[:2], seed=7, resamples=1200)
    decision = evaluate_claim(
        claim_class=ClaimClass.PAPER_COMPARABLE_PUBLIC,
        runs=tuple(_evidence(run) for run in _RUNS[:2]),
        bootstrap=result.evidence,
    )
    assert decision.allowed is False
    assert "three_complete_runs_required" in decision.reasons
    assert decision.disclaimer is not None


def test_run_binding_mismatch_refuses_the_paper_claim() -> None:
    result = build_paired_bootstrap(runs=_RUNS[:3], seed=7, resamples=1200)
    other = tuple(
        _run(f"other-{index}", baseline=0.25, final=1.0) for index in (1, 2, 3)
    )
    decision = evaluate_claim(
        claim_class=ClaimClass.PAPER_COMPARABLE_PUBLIC,
        runs=tuple(_evidence(run) for run in other),
        bootstrap=result.evidence,
    )
    assert decision.allowed is False
    assert "bootstrap_run_binding_mismatch" in decision.reasons


def test_low_resample_bootstrap_is_incomplete() -> None:
    result = build_paired_bootstrap(runs=_RUNS, seed=7, resamples=200)
    assert result.evidence.complete is False
    decision = evaluate_claim(
        claim_class=ClaimClass.PAPER_COMPARABLE_PUBLIC,
        runs=tuple(_evidence(run) for run in _RUNS),
        bootstrap=result.evidence,
    )
    assert decision.allowed is False
    assert "paired_bootstrap_incomplete" in decision.reasons


def test_bootstrap_refuses_unpaired_or_invalid_inputs() -> None:
    with pytest.raises(ContractError, match="at least one run"):
        build_paired_bootstrap(runs=(), seed=7, resamples=1200)
    with pytest.raises(ContractError, match="resamples"):
        build_paired_bootstrap(runs=_RUNS, seed=7, resamples=0)
    with pytest.raises(ContractError, match="unique"):
        build_paired_bootstrap(runs=(_RUNS[0], _RUNS[0]), seed=7, resamples=1200)
    unpaired = EvalRun(
        run_id="run-x",
        phase_scores={
            "baseline": (_score("task-1", 0.0), _score("task-2", 0.0)),
            "validation": (_score("task-1", 1.0), _score("task-2", 1.0)),
            "confirmation": (_score("task-1", 1.0), _score("task-2", 1.0)),
        },
    )
    with pytest.raises(ContractError, match="same task"):
        build_paired_bootstrap(runs=(_RUNS[0], unpaired), seed=7, resamples=1200)


def test_seed_changes_resample_distribution_not_observed_diff() -> None:
    first = build_paired_bootstrap(runs=_RUNS, seed=1, resamples=1200)
    second = build_paired_bootstrap(runs=_RUNS, seed=2, resamples=1200)
    assert first.payload["observed_mean_diff"] == second.payload["observed_mean_diff"]
    assert first.artifact != second.artifact
