"""Approval-bound, file-drop-only Task Observer review packets.

This bridge renders a gated Agent Skill Mastery Engine candidate skill as a review packet a human
can hand to Task Observer. It never installs anything, never writes a shared
observation log, and only ever creates one new directory that must not exist.
"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Mapping

from .canonical import (
    ContractError,
    canonical_bytes,
    require_identifier,
    safe_member_name,
    sha256_bytes,
)
from .contract import ApprovalRecord
from .integration import validate_skill_authoring

OBSERVER_PACKET_SCHEMA = "asme.observer-review-packet.v1"
OBSERVER_REVIEW_PHASE = "task-observer-review-packet"


def _parse_moment(value: str, *, field: str) -> datetime:
    try:
        moment = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ContractError(f"{field} must be an ISO timestamp") from exc
    if moment.tzinfo is None:
        raise ContractError(f"{field} must carry an explicit timezone")
    return moment


def build_observer_review_packet(
    *,
    skill_name: str,
    skill_files: Mapping[str, bytes],
    approval: ApprovalRecord,
    now: str,
) -> dict[str, bytes]:
    """Render one deterministic review packet bound to an explicit approval."""

    require_identifier(skill_name, field="observer packet skill name")
    if not skill_files:
        raise ContractError("observer packet requires at least one skill file")
    for path, content in skill_files.items():
        safe_member_name(path)
        if not isinstance(content, bytes):
            raise ContractError(f"observer packet file must contain bytes: {path}")
    if "SKILL.md" not in skill_files:
        raise ContractError("observer packet requires SKILL.md")
    validate_skill_authoring(skill_files["SKILL.md"], expected_name=skill_name)

    if approval.phase != OBSERVER_REVIEW_PHASE:
        raise ContractError(
            f"observer packet approval phase must be {OBSERVER_REVIEW_PHASE!r}"
        )
    if approval.consumed:
        raise ContractError("observer packet approval is already consumed")
    moment = _parse_moment(now, field="observer packet now")
    approved_at = _parse_moment(approval.approved_at, field="approval approved_at")
    expires_at = _parse_moment(approval.expires_at, field="approval expires_at")
    if not approved_at <= moment < expires_at:
        raise ContractError("observer packet approval is expired or not yet active")
    expected_hashes = {
        path: sha256_bytes(content) for path, content in skill_files.items()
    }
    if dict(approval.artifact_hashes) != expected_hashes:
        raise ContractError(
            "observer packet approval artifact hashes differ from the packet files"
        )

    manifest = {
        "schema": OBSERVER_PACKET_SCHEMA,
        "skill_name": skill_name,
        "approval": {
            "approval_id": approval.approval_id,
            "approver": approval.approver,
            "approved_at": approval.approved_at,
            "expires_at": approval.expires_at,
            "destination": approval.destination,
        },
        "files": [
            {
                "path": f"skill/{path}",
                "sha256": expected_hashes[path],
                "bytes": len(skill_files[path]),
            }
            for path in sorted(skill_files)
        ],
        "handling": {
            "write_mode": "file_drop_create_only",
            "shared_observation_log_write": "forbidden",
            "installation": "human_review_required",
        },
    }
    review_doc = "\n".join(
        (
            f"# Task Observer review packet: {skill_name}",
            "",
            "This packet is a candidate for HUMAN REVIEW only. Nothing in it is",
            "installed, and nothing may write to a live Task Observer root or the",
            "shared observation log.",
            "",
            f"- Approved by: {approval.approver} ({approval.approval_id})",
            f"- Approved at: {approval.approved_at}",
            f"- Expires at: {approval.expires_at}",
            "",
            "To accept the skill, a human copies skill/ into a Task Observer",
            "skill root after their own review. Every file is hash-listed in",
            "packet-manifest.json; verify the hashes before accepting.",
            "",
        )
    ).encode("utf-8")

    packet: dict[str, bytes] = {
        "packet-manifest.json": canonical_bytes(manifest),
        "REVIEW-PACKET.md": review_doc,
    }
    for path in sorted(skill_files):
        packet[f"skill/{path}"] = skill_files[path]
    return packet


PACKET_VERIFICATION_SCHEMA = "asme.packet-verification.v1"
_EXPECTED_HANDLING = {
    "write_mode": "file_drop_create_only",
    "shared_observation_log_write": "forbidden",
    "installation": "human_review_required",
}


def verify_observer_review_packet(packet_dir: Path) -> dict[str, object]:
    """Read-only verification of one written review packet against its manifest."""

    if packet_dir.is_symlink() or not packet_dir.is_dir():
        raise ContractError(f"observer packet directory is missing: {packet_dir}")
    manifest_path = packet_dir / "packet-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ContractError("observer packet has no packet-manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("observer packet manifest is malformed") from exc
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema",
        "skill_name",
        "approval",
        "files",
        "handling",
    }:
        raise ContractError("observer packet manifest fields differ from the contract")
    if manifest["schema"] != OBSERVER_PACKET_SCHEMA:
        raise ContractError("observer packet manifest schema differs from the contract")
    if manifest["handling"] != _EXPECTED_HANDLING:
        raise ContractError("observer packet handling block differs from the contract")
    approval = manifest["approval"]
    if not isinstance(approval, dict) or not isinstance(
        approval.get("approval_id"), str
    ):
        raise ContractError("observer packet manifest has no approval identity")
    review_doc = packet_dir / "REVIEW-PACKET.md"
    if review_doc.is_symlink() or not review_doc.is_file():
        raise ContractError("observer packet has no REVIEW-PACKET.md")
    listed = manifest["files"]
    if not isinstance(listed, list) or not listed:
        raise ContractError("observer packet manifest lists no files")
    expected = {"packet-manifest.json", "REVIEW-PACKET.md"}
    for item in listed:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "bytes"}:
            raise ContractError("observer packet manifest file entry is invalid")
        member = safe_member_name(item["path"])
        if not member.startswith("skill/"):
            raise ContractError(f"observer packet member is outside skill/: {member}")
        target = packet_dir / member
        if target.is_symlink() or not target.is_file():
            raise ContractError(f"observer packet member is missing: {member}")
        content = target.read_bytes()
        if sha256_bytes(content) != item["sha256"] or len(content) != item["bytes"]:
            raise ContractError(
                f"observer packet member differs from its manifest hash: {member}"
            )
        expected.add(member)
    actual = {
        path.relative_to(packet_dir).as_posix()
        for path in packet_dir.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    extra = sorted(actual - expected)
    if extra:
        raise ContractError(f"observer packet contains unlisted files: {extra}")
    return {
        "schema": PACKET_VERIFICATION_SCHEMA,
        "skill_name": manifest["skill_name"],
        "approval_id": approval["approval_id"],
        "files_verified": len(listed),
        "verified": True,
    }


def write_observer_review_packet(
    packet: Mapping[str, bytes], target_dir: Path
) -> tuple[Path, ...]:
    """Create-only file drop: validate every member before writing anything."""

    if not packet:
        raise ContractError("observer packet has no files to write")
    if target_dir.exists():
        raise ContractError(f"observer packet target already exists: {target_dir}")
    resolved_target = target_dir.parent.resolve(strict=True) / target_dir.name
    members: list[str] = []
    for member, content in packet.items():
        safe_member_name(member)
        if not isinstance(content, bytes):
            raise ContractError(f"observer packet member must contain bytes: {member}")
        destination = (resolved_target / member).resolve()
        if not destination.is_relative_to(resolved_target):
            raise ContractError(f"observer packet member escapes the target: {member}")
        members.append(member)

    written: list[Path] = []
    resolved_target.mkdir()
    for member in sorted(members):
        destination = resolved_target / member
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(packet[member])
        written.append(destination)
    return tuple(written)
