"""Truthful local and paper-comparable claim policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Sequence

from .canonical import ContractError
from .contract import TraceFidelity


class ClaimClass(StrEnum):
    LOCAL_ACCEPTANCE = "local_acceptance"
    PAPER_COMPARABLE_PUBLIC = "paper_comparable_public_claim"


@dataclass(frozen=True)
class RunEvidence:
    run_id: str
    baseline_score: float
    validation_score: float
    confirmation_score: float
    complete: bool
    trace_fidelity: TraceFidelity
    isolation_label: str

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ContractError("run_id cannot be blank")
        for name, score in (
            ("baseline", self.baseline_score),
            ("validation", self.validation_score),
            ("confirmation", self.confirmation_score),
        ):
            if isinstance(score, bool) or not 0.0 <= score <= 1.0:
                raise ContractError(f"{name} score must be within [0,1]")

    @property
    def strict_local_win(self) -> bool:
        return (
            self.complete
            and self.validation_score > self.baseline_score
            and self.confirmation_score > self.baseline_score
        )


@dataclass(frozen=True)
class BootstrapEvidence:
    run_ids: tuple[str, ...]
    paired: bool
    complete: bool
    method: str
    artifact_hash: str

    def __post_init__(self) -> None:
        if len(self.artifact_hash) != 64:
            raise ContractError("bootstrap evidence requires an artifact SHA-256")
        if len(set(self.run_ids)) != len(self.run_ids):
            raise ContractError("bootstrap run IDs must be unique")


@dataclass(frozen=True)
class ClaimDecision:
    claim_class: ClaimClass
    allowed: bool
    label: str
    reasons: tuple[str, ...]
    disclaimer: str | None = None


def evaluate_claim(
    *,
    claim_class: ClaimClass,
    runs: Sequence[RunEvidence],
    bootstrap: BootstrapEvidence | None = None,
) -> ClaimDecision:
    """Keep local acceptance distinct from the paper's three-run evidence."""

    if claim_class is ClaimClass.LOCAL_ACCEPTANCE:
        if len(runs) != 1:
            return ClaimDecision(claim_class, False, "not_accepted", ("exactly_one_local_run_required",))
        run = runs[0]
        reasons = [] if run.strict_local_win else ["strict_validation_and_confirmation_win_missing"]
        return ClaimDecision(
            claim_class,
            not reasons,
            "local_acceptance" if not reasons else "not_accepted",
            tuple(reasons),
        )
    reasons: list[str] = []
    complete_runs = [run for run in runs if run.complete]
    if len(complete_runs) < 3:
        reasons.append("three_complete_runs_required")
    if len({run.run_id for run in complete_runs}) != len(complete_runs):
        reasons.append("run_ids_not_unique")
    if any(not run.strict_local_win for run in complete_runs):
        reasons.append("one_or_more_runs_lack_strict_confirmed_improvement")
    expected_ids = tuple(sorted(run.run_id for run in complete_runs))
    if bootstrap is None:
        reasons.append("paired_bootstrap_evidence_missing")
    else:
        if not bootstrap.paired or not bootstrap.complete:
            reasons.append("paired_bootstrap_incomplete")
        if tuple(sorted(bootstrap.run_ids)) != expected_ids:
            reasons.append("bootstrap_run_binding_mismatch")
    allowed = not reasons
    disclaimer = None if allowed else (
        "Local evaluation only. This result is not paper-comparable because the required "
        "three complete runs and paired-bootstrap evidence were not fully satisfied."
    )
    return ClaimDecision(
        claim_class,
        allowed,
        "paper_comparable" if allowed else "non_comparable_local_evidence",
        tuple(reasons),
        disclaimer,
    )
