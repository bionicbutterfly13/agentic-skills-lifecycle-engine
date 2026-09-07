"""Explicit benefit bridges that never couple WikiSkill to Task Observer state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any, Mapping, Sequence

from .canonical import ContractError, hash_json, require_identifier
from .contract import LifecycleState, Route
from .impact import ImpactEntry, ImpactOutcome
from .lifecycle import DomainState
from .proposal import purpose_origin_observations
from .snapshot import Snapshot


OBSERVATION_CANDIDATE_SCHEMA = "asme.observation-candidate.v1"
_SEMVER = re.compile(
    r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
)
_TRIGGER = re.compile(r"(\d+)\. (\S.*)")

HYBRID_BENEFIT_DISPOSITIONS: Mapping[str, str] = {
    "live_reusable_signal_observation": "task_observer_owned",
    "reviewed_observation_seed": "explicit_approval_bound_input_bridge",
    "create_patch_no_action": "shared_semantic_analog",
    "version_date_trigger_authoring": "wikiskill_staging_lint",
    "verified_reusable_content": "shared_evidence_outcome",
    "current_research": "external_adapter_or_human_review",
    "confidence_and_clustering": "task_observer_owned",
    "deprecation_and_archival": "task_observer_owned",
    "wikiskill_observation_candidate": "explicit_review_only_output_bridge",
    "delivery_hygiene": "shared_staging_gate_human_install",
}


@dataclass(frozen=True)
class SkillAuthoringMetadata:
    name: str
    description: str
    version: str
    last_updated: str
    triggers: tuple[str, ...]


@dataclass(frozen=True)
class ObservationCandidate:
    candidate_id: str
    domain_id: str
    skill_name: str
    active_snapshot_hash: str
    accepted_impact_id: str
    delivery_id: str
    test_manifest_hashes: tuple[tuple[str, str], ...]
    origin_observation_ids: tuple[str, ...]
    skill_version: str
    skill_last_updated: str
    description: str
    triggers: tuple[str, ...]
    accepted_scores: tuple[float, float]
    review_status: str = "pending_human_review"
    shared_log_write_allowed: bool = False
    source_system: str = "asme"
    schema: str = OBSERVATION_CANDIDATE_SCHEMA

    @property
    def digest(self) -> str:
        return hash_json(self.as_mapping())

    def as_mapping(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "candidate_id": self.candidate_id,
            "source_system": self.source_system,
            "review_status": self.review_status,
            "shared_log_write_allowed": self.shared_log_write_allowed,
            "domain_id": self.domain_id,
            "skill_name": self.skill_name,
            "active_snapshot_hash": self.active_snapshot_hash,
            "accepted_impact_id": self.accepted_impact_id,
            "delivery_id": self.delivery_id,
            "test_manifest_hashes": dict(self.test_manifest_hashes),
            "origin_observation_ids": list(self.origin_observation_ids),
            "skill_version": self.skill_version,
            "skill_last_updated": self.skill_last_updated,
            "description": self.description,
            "triggers": list(self.triggers),
            "accepted_scores": list(self.accepted_scores),
        }


def validate_skill_authoring(
    content: bytes, *, expected_name: str
) -> SkillAuthoringMetadata:
    """Enforce the portable version, date, description, and trigger contract."""

    require_identifier(expected_name, field="expected skill name")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("skill authoring metadata must be UTF-8") from exc
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ContractError("skill authoring metadata requires frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ContractError("skill authoring frontmatter is unterminated") from exc
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if ": " not in line:
            raise ContractError("skill authoring frontmatter fields are malformed")
        key, value = line.split(": ", 1)
        if key in fields or not key or not value.strip():
            raise ContractError("skill authoring frontmatter fields are invalid")
        fields[key] = value.strip()
    date_keys = {"last_updated", "date"} & set(fields)
    if len(date_keys) != 1:
        raise ContractError(
            "skill authoring frontmatter requires exactly one of last_updated or date"
        )
    date_key = date_keys.pop()
    if set(fields) != {"name", "description", "version", date_key}:
        raise ContractError("skill authoring frontmatter fields differ from the contract")
    name = require_identifier(fields["name"], field="skill frontmatter name")
    if name != expected_name:
        raise ContractError("skill frontmatter name differs from staged skill name")
    description = fields["description"]
    if not 40 <= len(description) < 300:
        raise ContractError("skill description must contain 40-299 characters")
    if "Use when " not in description:
        raise ContractError("skill description must include a concrete 'Use when' clause")
    version = fields["version"]
    if _SEMVER.fullmatch(version) is None:
        raise ContractError("skill version must use three-part semantic versioning")
    last_updated = fields[date_key]
    try:
        parsed_date = date.fromisoformat(last_updated)
    except ValueError as exc:
        raise ContractError(f"skill {date_key} must be an ISO calendar date") from exc
    if parsed_date.isoformat() != last_updated:
        raise ContractError(f"skill {date_key} must be canonical ISO date text")
    trigger_headings = [index for index, line in enumerate(lines) if line == "## Triggers"]
    if len(trigger_headings) != 1:
        raise ContractError("skill must contain one ## Triggers section")
    trigger_lines: list[str] = []
    for line in lines[trigger_headings[0] + 1 :]:
        if line.startswith("## "):
            break
        if line.strip():
            trigger_lines.append(line)
    matches = [_TRIGGER.fullmatch(line) for line in trigger_lines]
    if (
        len(matches) < 2
        or any(match is None for match in matches)
        or [int(match.group(1)) for match in matches if match is not None]
        != list(range(1, len(matches) + 1))
        or any(len(match.group(2).strip()) < 20 for match in matches if match is not None)
    ):
        raise ContractError("skill requires at least two concrete triggers in numbered order")
    triggers = tuple(match.group(2).strip() for match in matches if match is not None)
    if any("{{" in value or "}}" in value for value in (description, *triggers)):
        raise ContractError("skill authoring metadata contains unresolved template text")
    return SkillAuthoringMetadata(name, description, version, last_updated, triggers)


def build_observation_candidate(
    *,
    state: DomainState,
    snapshot: Snapshot,
    skill_name: str,
    impact_history: Sequence[ImpactEntry],
) -> ObservationCandidate:
    """Build a review-only bridge record from already validated local evidence."""

    require_identifier(skill_name, field="observation candidate skill name")
    if (
        state.state is not LifecycleState.DONE
        or state.route is not Route.VALIDATED
        or state.validated_step != "exported"
    ):
        raise ContractError("observation candidate requires a validated export")
    if state.active_snapshot_hash != snapshot.snapshot_hash:
        raise ContractError("observation candidate snapshot is not active")
    contents = snapshot.content_map()
    prefix = f"{skill_name}/"
    metadata = validate_skill_authoring(
        contents.get(f"{prefix}SKILL.md", b""), expected_name=skill_name
    )
    origins = purpose_origin_observations(contents.get(f"{prefix}PURPOSE.md"))
    if not set(origins).issubset(state.seeded_observation_ids):
        raise ContractError("observation candidate PURPOSE cites unseeded observations")
    accepted = [
        item
        for item in impact_history
        if item.outcome is ImpactOutcome.ACCEPTED
        and item.active_after == snapshot.snapshot_hash
    ]
    if len(accepted) != 1:
        raise ContractError("observation candidate requires one accepted active impact")
    impact = accepted[0]
    manifests = tuple(
        sorted(
            (str(item.get("phase")), str(item.get("manifest_hash")))
            for item in state.test_manifests
        )
    )
    if {phase for phase, _ in manifests} != {"test-baseline", "test-final"}:
        raise ContractError("observation candidate requires both final test manifests")
    deliveries = [
        item
        for item in state.delivery_ledger
        if item.get("route") == Route.VALIDATED.value
    ]
    if len(deliveries) != 1 or not deliveries[0].get("delivery_id"):
        raise ContractError("observation candidate requires one validated delivery identity")
    material = {
        "domain_id": state.domain_id,
        "skill_name": skill_name,
        "active_snapshot_hash": snapshot.snapshot_hash,
        "accepted_impact_id": impact.entry_id,
        "delivery_id": str(deliveries[0]["delivery_id"]),
        "test_manifest_hashes": dict(manifests),
        "origin_observation_ids": list(origins),
        "skill_version": metadata.version,
        "skill_last_updated": metadata.last_updated,
        "description": metadata.description,
        "triggers": list(metadata.triggers),
        "accepted_scores": list(impact.scores),
        "review_status": "pending_human_review",
        "shared_log_write_allowed": False,
        "source_system": "asme",
        "schema": OBSERVATION_CANDIDATE_SCHEMA,
    }
    return ObservationCandidate(
        candidate_id=hash_json(material),
        domain_id=state.domain_id,
        skill_name=skill_name,
        active_snapshot_hash=snapshot.snapshot_hash,
        accepted_impact_id=impact.entry_id,
        delivery_id=str(deliveries[0]["delivery_id"]),
        test_manifest_hashes=manifests,
        origin_observation_ids=origins,
        skill_version=metadata.version,
        skill_last_updated=metadata.last_updated,
        description=metadata.description,
        triggers=metadata.triggers,
        accepted_scores=(float(impact.scores[0]), float(impact.scores[1])),
    )
