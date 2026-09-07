"""Immutable rollout manifests bound to prompts, captures, and evaluations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Mapping, Sequence

from .canonical import ContractError, hash_json, require_identifier, sha256_bytes
from .contract import CapturedExecution
from .domain import DeclaredDomain, marker_propagated
from .evaluation import EvaluationResult, aggregate_scores


ROLLOUT_MANIFEST_SCHEMA = "asme.rollout-manifest.v1"


@dataclass(frozen=True)
class RolloutEntry:
    task_id: str
    prompt_hash: str
    execution_hash: str
    returned_output_hash: str
    evaluation_hash: str
    valid: bool
    score: float | None
    error_class: str | None


@dataclass(frozen=True)
class RolloutManifest:
    phase: str
    split: str
    iteration: int
    domain_seal_hash: str
    active_snapshot_hash: str
    capability_report_hash: str
    entries: tuple[RolloutEntry, ...]
    complete: bool
    valid: bool
    aggregate_score: float | None
    errors: tuple[str, ...]
    schema: str = ROLLOUT_MANIFEST_SCHEMA

    def __post_init__(self) -> None:
        require_identifier(self.phase, field="manifest phase")
        if self.split not in {"train", "validation", "test"}:
            raise ContractError("manifest split is invalid")
        ids = [entry.task_id for entry in self.entries]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ContractError("manifest task IDs must be sorted and unique")
        if self.valid and (not self.complete or self.aggregate_score is None or self.errors):
            raise ContractError("valid manifest must be complete, scored, and error-free")
        if not self.valid and self.aggregate_score is not None:
            raise ContractError("invalid manifest cannot carry an aggregate score")

    @property
    def digest(self) -> str:
        return hash_json(asdict(self))


def rollout_manifest_from_mapping(raw: Mapping[str, Any]) -> RolloutManifest:
    """Decode an exact immutable rollout manifest at a persisted boundary."""

    if not isinstance(raw, Mapping):
        raise ContractError("rollout manifest must be an object")
    expected = {item.name for item in fields(RolloutManifest)}
    if set(raw) != expected:
        raise ContractError("rollout manifest fields differ from the contract")
    values = dict(raw)
    entries = values.get("entries")
    errors = values.get("errors")
    if not isinstance(entries, (list, tuple)) or not isinstance(errors, (list, tuple)):
        raise ContractError("rollout manifest entries or errors are malformed")
    try:
        values["entries"] = tuple(RolloutEntry(**dict(item)) for item in entries)
        values["errors"] = tuple(errors)
        manifest = RolloutManifest(**values)
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("rollout manifest differs from the contract") from exc
    if manifest.digest != hash_json(raw):
        raise ContractError("rollout manifest hash is unstable")
    return manifest


def build_rollout_manifest(
    *,
    domain: DeclaredDomain,
    phase: str,
    split: str,
    iteration: int,
    active_snapshot_hash: str,
    prompts: Mapping[str, str],
    executions: Mapping[str, CapturedExecution],
    evaluations: Mapping[str, EvaluationResult],
) -> RolloutManifest:
    """Build a manifest with no numeric score when any evidence is invalid."""

    require_identifier(phase, field="phase")
    expected_ids = sorted(answer.task_id for answer in domain.answers if answer.split == split)
    if not expected_ids:
        raise ContractError(f"declared split has no tasks: {split}")
    supplied_sets = {
        "prompts": set(prompts),
        "executions": set(executions),
        "evaluations": set(evaluations),
    }
    errors: list[str] = []
    for name, supplied in supplied_sets.items():
        if supplied != set(expected_ids):
            errors.append(
                f"{name} task IDs differ: missing={sorted(set(expected_ids)-supplied)}, "
                f"extra={sorted(supplied-set(expected_ids))}"
            )
    answer_map = domain.answer_map()
    entries: list[RolloutEntry] = []
    capability_hashes: set[str] = set()
    results: list[EvaluationResult] = []
    for task_id in expected_ids:
        execution = executions.get(task_id)
        evaluation = evaluations.get(task_id)
        prompt = prompts.get(task_id)
        if execution is None or evaluation is None or prompt is None:
            continue
        capability_hashes.add(execution.capability_report_hash)
        entry_errors: list[str] = []
        prompt_hash = sha256_bytes(prompt.encode("utf-8"))
        if execution.prompt_hash != prompt_hash:
            entry_errors.append("prompt_hash_mismatch")
        if execution.active_snapshot_hash != active_snapshot_hash:
            entry_errors.append("snapshot_hash_mismatch")
        if execution.returned_output_hash != evaluation.output_hash:
            entry_errors.append("output_hash_mismatch")
        if marker_propagated(execution.returned_output, answer_map[task_id]):
            entry_errors.append("provenance_marker_propagated")
        if not evaluation.valid:
            entry_errors.append(evaluation.error_class or "evaluation_invalid")
        entry_valid = not entry_errors
        if entry_errors:
            errors.extend(f"{task_id}:{item}" for item in entry_errors)
        evaluation_payload = asdict(evaluation)
        entries.append(
            RolloutEntry(
                task_id=task_id,
                prompt_hash=prompt_hash,
                execution_hash=hash_json(asdict(execution)),
                returned_output_hash=execution.returned_output_hash,
                evaluation_hash=hash_json(evaluation_payload),
                valid=entry_valid,
                score=evaluation.score if entry_valid else None,
                error_class=None if entry_valid else ",".join(entry_errors),
            )
        )
        results.append(evaluation if entry_valid else EvaluationResult(False, evaluation.output_hash))
    if len(capability_hashes) != 1:
        errors.append("capability_report_hash_not_uniform")
    complete = all(set(expected_ids) == supplied for supplied in supplied_sets.values())
    valid = complete and not errors and len(entries) == len(expected_ids)
    aggregate = aggregate_scores(results) if valid else None
    if valid and aggregate is None:
        valid = False
        errors.append("aggregate_unavailable")
    return RolloutManifest(
        phase=phase,
        split=split,
        iteration=iteration,
        domain_seal_hash=domain.seal,
        active_snapshot_hash=active_snapshot_hash,
        capability_report_hash=next(iter(capability_hashes), "unknown"),
        entries=tuple(entries),
        complete=complete,
        valid=valid,
        aggregate_score=aggregate if valid else None,
        errors=tuple(sorted(errors)),
    )


def verify_manifest_bindings(
    manifest: RolloutManifest,
    *,
    domain_seal_hash: str,
    active_snapshot_hash: str,
    capability_report_hash: str,
) -> None:
    if manifest.domain_seal_hash != domain_seal_hash:
        raise ContractError("rollout manifest domain seal drifted")
    if manifest.active_snapshot_hash != active_snapshot_hash:
        raise ContractError("rollout manifest active snapshot drifted")
    if manifest.capability_report_hash != capability_report_hash:
        raise ContractError("rollout manifest capability report drifted")
    if not manifest.complete or not manifest.valid or manifest.aggregate_score is None:
        raise ContractError("rollout manifest is incomplete or invalid")
