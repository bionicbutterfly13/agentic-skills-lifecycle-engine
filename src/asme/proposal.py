"""Skill Proposer output validation and single-skill snapshot mutation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping, Sequence

from .canonical import ContractError, hash_json, require_identifier, safe_member_name, sha256_bytes
from .snapshot import Snapshot


PROPOSAL_SCHEMA = "asme.proposal.v1"


@dataclass(frozen=True)
class ValidatedProposal:
    action: str
    context_hash: str
    reason: str
    trace_ids: tuple[str, ...]
    origin_observation_ids: tuple[str, ...]
    skill_name: str | None
    snapshot: Snapshot
    schema: str = PROPOSAL_SCHEMA

    @property
    def digest(self) -> str:
        return hash_json(
            {
                "action": self.action,
                "context_hash": self.context_hash,
                "reason": self.reason,
                "trace_ids": self.trace_ids,
                "origin_observation_ids": self.origin_observation_ids,
                "skill_name": self.skill_name,
                "snapshot_hash": self.snapshot.snapshot_hash,
                "schema": self.schema,
            }
        )


def validate_proposal(
    value: str,
    *,
    proposer_context: bytes,
    available_trace_ids: Sequence[str],
    available_origin_observation_ids: Sequence[str] = (),
    active_snapshot: Snapshot,
    forbidden_markers: Sequence[str],
) -> ValidatedProposal:
    """Validate one create, patch, or no-action decision without semantic overclaiming."""

    try:
        raw = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ContractError("proposal output is malformed JSON") from exc
    if not isinstance(raw, dict):
        raise ContractError("proposal output must be a JSON object")
    action = raw.get("action")
    required_by_action = {
        "no_action": {"action", "context_hash", "reason", "trace_ids"},
        "create": {"action", "context_hash", "reason", "trace_ids", "skill_name", "files"},
        "patch": {"action", "context_hash", "reason", "trace_ids", "skill_name", "patches"},
    }
    if action not in required_by_action:
        raise ContractError("proposal action must be create, patch, or no_action")
    allowed_fields = required_by_action[action]
    if action != "no_action":
        allowed_fields = allowed_fields | {"origin_observation_ids"}
    supplied_fields = frozenset(raw)
    if supplied_fields not in {
        frozenset(required_by_action[action]),
        frozenset(allowed_fields),
    }:
        raise ContractError("proposal fields differ from the selected action schema")
    context_hash = raw.get("context_hash")
    if context_hash != sha256_bytes(proposer_context):
        raise ContractError("proposal context hash does not match proposer input")
    reason = raw.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ContractError("proposal reason cannot be blank")
    trace_ids = _trace_ids(raw.get("trace_ids"), available_trace_ids=available_trace_ids)
    if action != "no_action" and len(trace_ids) < 4:
        raise ContractError("changed proposal requires at least four unique train traces")
    if action == "no_action":
        return ValidatedProposal(
            action,
            context_hash,
            reason,
            trace_ids,
            (),
            None,
            active_snapshot,
        )

    skill_name = require_identifier(raw.get("skill_name"), field="proposal skill_name")
    origin_observation_ids = _origin_ids(
        raw.get("origin_observation_ids", []),
        available_origin_observation_ids=available_origin_observation_ids,
    )
    contents = active_snapshot.content_map()
    prefix = f"{skill_name}/"
    existing_origins = purpose_origin_observations(contents.get(f"{prefix}PURPOSE.md"))
    unavailable_existing = sorted(
        set(existing_origins) - set(available_origin_observation_ids)
    )
    if unavailable_existing:
        raise ContractError(
            f"existing PURPOSE cites unavailable seed observations: {unavailable_existing}"
        )
    if action == "create":
        if any(path.startswith(prefix) for path in contents):
            raise ContractError("create proposal targets an existing skill")
        proposed_files = raw.get("files")
        if not isinstance(proposed_files, Mapping) or not proposed_files:
            raise ContractError("create proposal requires a non-empty files object")
        if "SKILL.md" not in proposed_files:
            raise ContractError("created skill must include SKILL.md")
        for member, text in proposed_files.items():
            relative = safe_member_name(member)
            if not isinstance(text, str):
                raise ContractError(f"created skill file must be text: {relative}")
            contents[safe_member_name(prefix + relative)] = text.encode("utf-8")
    else:
        if not any(path.startswith(prefix) for path in contents):
            raise ContractError("patch proposal targets a missing skill")
        patches = raw.get("patches")
        if not isinstance(patches, list) or not patches:
            raise ContractError("patch proposal requires a non-empty patch list")
        for item in patches:
            _apply_patch(contents, skill_prefix=prefix, raw=item)

    candidate = Snapshot.from_mapping(contents, forbidden_markers=forbidden_markers)
    if candidate.snapshot_hash == active_snapshot.snapshot_hash:
        raise ContractError("changed proposal produced no snapshot change")
    expected_origins = tuple(sorted(set(existing_origins) | set(origin_observation_ids)))
    actual_origins = purpose_origin_observations(
        candidate.content_map().get(f"{prefix}PURPOSE.md")
    )
    if actual_origins != expected_origins:
        raise ContractError(
            "skill PURPOSE.md origin_observations differ from cited seed provenance"
        )
    return ValidatedProposal(
        action,
        context_hash,
        reason,
        trace_ids,
        expected_origins,
        skill_name,
        candidate,
    )


def _trace_ids(value: Any, *, available_trace_ids: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ContractError("proposal trace_ids must be a list")
    trace_ids = tuple(require_identifier(item, field="proposal trace_id") for item in value)
    if len(trace_ids) != len(set(trace_ids)):
        raise ContractError("proposal trace_ids must be unique")
    available = set(available_trace_ids)
    missing = sorted(set(trace_ids) - available)
    if missing:
        raise ContractError(f"proposal cites unavailable train traces: {missing}")
    return trace_ids


def _origin_ids(
    value: Any, *, available_origin_observation_ids: Sequence[str]
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ContractError("proposal origin_observation_ids must be a list")
    origins = tuple(
        require_identifier(item, field="proposal origin observation ID")
        for item in value
    )
    if len(origins) != len(set(origins)):
        raise ContractError("proposal origin_observation_ids must be unique")
    missing = sorted(set(origins) - set(available_origin_observation_ids))
    if missing:
        raise ContractError(f"proposal cites unavailable seed observations: {missing}")
    return tuple(sorted(origins))


def purpose_origin_observations(content: bytes | None) -> tuple[str, ...]:
    """Return one canonical PURPOSE origin list or refuse malformed provenance."""

    if content is None:
        return ()
    try:
        lines = content.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ContractError("skill PURPOSE.md provenance must be UTF-8") from exc
    matches = [line for line in lines if line.startswith("origin_observations:")]
    if not matches:
        return ()
    if len(matches) != 1 or not matches[0].startswith("origin_observations: "):
        raise ContractError("skill PURPOSE.md requires one origin_observations line")
    try:
        raw = json.loads(matches[0].removeprefix("origin_observations: "))
    except json.JSONDecodeError as exc:
        raise ContractError("skill PURPOSE.md origin_observations must be JSON") from exc
    if not isinstance(raw, list):
        raise ContractError("skill PURPOSE.md origin_observations must be a list")
    origins = tuple(
        require_identifier(item, field="PURPOSE origin observation ID")
        for item in raw
    )
    if origins != tuple(sorted(set(origins))):
        raise ContractError("skill PURPOSE.md origin_observations must be sorted and unique")
    expected = f"origin_observations: {json.dumps(list(origins))}"
    if matches[0] != expected:
        raise ContractError("skill PURPOSE.md origin_observations is not canonical")
    return origins


def _apply_patch(contents: dict[str, bytes], *, skill_prefix: str, raw: Any) -> None:
    if not isinstance(raw, Mapping) or set(raw) != {"path", "target", "replacement"}:
        raise ContractError("proposal patch must contain path, target, and replacement")
    member = safe_member_name(raw.get("path"))
    path = safe_member_name(skill_prefix + member)
    target = raw.get("target")
    replacement = raw.get("replacement")
    if not isinstance(target, str) or not target:
        raise ContractError("proposal patch target cannot be empty")
    if not isinstance(replacement, str):
        raise ContractError("proposal patch replacement must be text")
    content = contents.get(path)
    if content is None:
        raise ContractError(f"proposal patch file is missing: {path}")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError(f"proposal patch file is not UTF-8: {path}") from exc
    if text.count(target) != 1:
        raise ContractError("proposal patch target must match exactly once")
    contents[path] = text.replace(target, replacement, 1).encode("utf-8")
