"""Immutable skill-impact history with deterministic entry identities."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Sequence

from .canonical import ContractError, hash_json


class ImpactOutcome(StrEnum):
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"
    REJECTED_AFTER_CONFIRM = "RejectedAfterConfirm"
    NO_ACTION = "NoAction"
    ABANDONED = "Abandoned"


@dataclass(frozen=True)
class ImpactEntry:
    entry_id: str
    domain_id: str
    iteration: int
    outcome: ImpactOutcome
    active_before: str
    candidate_snapshot: str | None
    active_after: str
    scores: tuple[float, ...]
    unified_diff: str | None
    source_class: str = "ARCHITECTURE"

    def __post_init__(self) -> None:
        if self.iteration < 1:
            raise ContractError("impact iteration must be positive")
        expected_scores = {
            ImpactOutcome.REJECTED: 1,
            ImpactOutcome.ACCEPTED: 2,
            ImpactOutcome.REJECTED_AFTER_CONFIRM: 2,
            ImpactOutcome.NO_ACTION: 0,
            ImpactOutcome.ABANDONED: 0,
        }[self.outcome]
        if len(self.scores) != expected_scores:
            raise ContractError(f"{self.outcome.value} requires {expected_scores} score values")
        if any(isinstance(score, bool) or not 0.0 <= score <= 1.0 for score in self.scores):
            raise ContractError("impact scores must be within [0,1]")
        candidate_outcome = self.outcome is not ImpactOutcome.NO_ACTION
        if candidate_outcome and (not self.candidate_snapshot or self.unified_diff is None):
            raise ContractError("candidate outcome requires snapshot and unified diff")
        if self.outcome is ImpactOutcome.ACCEPTED:
            if self.active_after != self.candidate_snapshot:
                raise ContractError("accepted impact must promote the candidate")
        elif self.active_after != self.active_before:
            raise ContractError("non-accepted impact cannot change the active snapshot")
        if self.entry_id != _entry_id_material(self):
            raise ContractError("impact entry ID does not match its content")


def create_impact(
    *,
    domain_id: str,
    iteration: int,
    outcome: ImpactOutcome,
    active_before: str,
    candidate_snapshot: str | None,
    active_after: str,
    scores: Sequence[float],
    unified_diff: str | None,
) -> ImpactEntry:
    values = {
        "domain_id": domain_id,
        "iteration": iteration,
        "outcome": outcome,
        "active_before": active_before,
        "candidate_snapshot": candidate_snapshot,
        "active_after": active_after,
        "scores": tuple(scores),
        "unified_diff": unified_diff,
        "source_class": "ARCHITECTURE",
    }
    return ImpactEntry(entry_id=hash_json(values), **values)


def append_impact(
    history: Sequence[ImpactEntry], entry: ImpactEntry
) -> tuple[ImpactEntry, ...]:
    for existing in history:
        if existing.entry_id == entry.entry_id:
            if existing == entry:
                return tuple(history)
            raise ContractError("impact entry ID collision")
    return (*history, entry)


def _entry_id_material(entry: ImpactEntry) -> str:
    material = asdict(entry)
    material.pop("entry_id", None)
    return hash_json(material)
