"""Release gates, source attribution, and immutable historical status."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from .canonical import ContractError, hash_json


HISTORICAL_PLAN_REVISION = 8
HISTORICAL_PLAN_STATUS = "NEEDS REVISION"
HISTORICAL_PLAN_SOUND_VERDICT = False

PAPER_ATTRIBUTION = {
    "title": "WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution",
    "authors": (
        "L. Tang",
        "C. Rashtchian",
        "C.-S. Ferng",
        "A. Tomkins",
        "D.-C. Juan",
        "T. Vu",
    ),
    "arxiv_id": "2608.27454v1",
    "date": "2026-08-27",
    "source_license": "CC BY 4.0",
    "adaptation_notice": "Independent runtime-neutral implementation; not a literal replication.",
}


class DecisionStatus(StrEnum):
    ADOPTED = "adopted"
    PROVISIONAL = "provisional_implementation_default"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class GateDecision:
    decision_id: str
    status: DecisionStatus
    value: str
    source_class: str
    source_locator: str
    consequence: str

    def __post_init__(self) -> None:
        if self.decision_id not in {"A1", "A2", "A3", "A4", "A5"}:
            raise ContractError("unknown Gate A decision ID")
        if any(
            not item.strip()
            for item in (
                self.value,
                self.source_class,
                self.source_locator,
                self.consequence,
            )
        ):
            raise ContractError("Gate A decision fields cannot be blank")


DEVELOPMENT_DECISIONS: Mapping[str, GateDecision] = {
    "A1": GateDecision(
        "A1",
        DecisionStatus.ADOPTED,
        "truthful narrower evidence labels are allowed",
        "DIRECT_CURRENT_GOAL",
        (
            "PROVENANCE.md#current-development-authority; sha256:"
            "c8966236b915aee64067f03ae28a7d6028c31b171b3b8e7c771ef2e7fed6e809"
            "; scope:truthful-capability-labels"
        ),
        "no runtime claim may exceed measured evidence",
    ),
    "A2": GateDecision(
        "A2",
        DecisionStatus.ADOPTED,
        (
            "strict aggregate improvement plus fresh confirmation for local "
            "acceptance; adopted as drafted in the Gate A approval record, 2026-09-01"
        ),
        "ARCHITECTURE_DEFAULT",
        "locked/architecture-contract.md:section-16-A2",
        "paper-comparable public claims remain separately gated",
    ),
    "A3": GateDecision(
        "A3",
        DecisionStatus.ADOPTED,
        (
            "trusted text-only domains; adopted as drafted in the Gate A approval "
            "record, 2026-09-01"
        ),
        "ARCHITECTURE_DEFAULT",
        "locked/architecture-contract.md:section-16-A3",
        "artifact-producing and environment-interactive domains remain excluded",
    ),
    "A4": GateDecision(
        "A4",
        DecisionStatus.ADOPTED,
        (
            "free community use with preserved attribution; MIT (code) plus "
            "CC BY 4.0 (docs/methodology) selected per the Gate A approval record, "
            "2026-09-01, Option A; the project-page link to manysaintvictormd.com "
            "is a non-binding NOTICE.md request"
        ),
        "DIRECT_CURRENT_REQUIREMENT",
        (
            "PROVENANCE.md#owner-attribution-requirement; sha256:"
            "8245fd2d7d6205935cd948b9af01a199d82f24118854192580c75237e3e13ac8"
            "; scope:attribution-and-backlink"
        ),
        "publication and distribution proceed only through recorded owner action-time approvals",
    ),
    "A5": GateDecision(
        "A5",
        DecisionStatus.ADOPTED,
        "bounded core and Hermes adapter development in an isolated worktree",
        "DIRECT_CURRENT_GOAL",
        (
            "PROVENANCE.md#current-development-authority; sha256:"
            "c8966236b915aee64067f03ae28a7d6028c31b171b3b8e7c771ef2e7fed6e809"
            "; scope:bounded-isolated-worktree-implementation"
        ),
        "no live installation, commit, merge, publication, or distribution",
    ),
}


def decision_log_hash(decisions: Mapping[str, GateDecision] = DEVELOPMENT_DECISIONS) -> str:
    return hash_json(
        {
            key: {
                "decision_id": value.decision_id,
                "status": value.status.value,
                "value": value.value,
                "source_class": value.source_class,
                "source_locator": value.source_locator,
                "consequence": value.consequence,
            }
            for key, value in sorted(decisions.items())
        }
    )


def require_phase_authorized(
    phase: str, decisions: Mapping[str, GateDecision] = DEVELOPMENT_DECISIONS
) -> None:
    if phase == "implementation":
        if decisions["A5"].status is not DecisionStatus.ADOPTED:
            raise ContractError("implementation lacks an adopted A5 decision")
        return
    if phase in {"publication", "distribution"}:
        if decisions["A4"].status is not DecisionStatus.ADOPTED:
            raise ContractError("publication and distribution remain blocked by unresolved A4")
        return
    if phase == "live_installation":
        raise ContractError("live installation requires a separate action-time approval record")
    raise ContractError(f"unknown governed phase: {phase}")
