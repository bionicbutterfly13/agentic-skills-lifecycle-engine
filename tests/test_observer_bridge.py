from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from asme.canonical import ContractError, sha256_bytes
from asme.contract import ApprovalRecord
from asme.observer_bridge import (
    OBSERVER_PACKET_SCHEMA,
    OBSERVER_REVIEW_PHASE,
    PACKET_VERIFICATION_SCHEMA,
    build_observer_review_packet,
    verify_observer_review_packet,
    write_observer_review_packet,
)

_SKILL_MD = b"""---
name: demo-skill
description: Answer arithmetic prompts with one tagged number. Use when a task needs the declared answer-tag output contract.
version: 1.0.0
last_updated: 2026-09-01
---

# demo-skill

## Triggers

1. The task asks for a single numeric answer in answer tags.
2. The transcript shows repeated answer-tag formatting mistakes.
"""

_FILES = {"SKILL.md": _SKILL_MD, "PURPOSE.md": b"staged review candidate\n"}


def _approval(
    files=_FILES,
    *,
    phase: str = OBSERVER_REVIEW_PHASE,
    consumed: bool = False,
    expires_at: str = "2026-09-02T00:00:00+00:00",
) -> ApprovalRecord:
    return ApprovalRecord(
        approval_id="approval-1",
        phase=phase,
        artifact_hashes={path: sha256_bytes(content) for path, content in files.items()},
        runtime_id=None,
        destination="task-observer-review",
        approved_at="2026-09-01T00:00:00+00:00",
        expires_at=expires_at,
        approver="Dr. Mani",
    )


def _packet(**overrides):
    arguments = {
        "skill_name": "demo-skill",
        "skill_files": _FILES,
        "approval": _approval(),
        "now": "2026-09-01T12:00:00+00:00",
    }
    arguments.update(overrides)
    return build_observer_review_packet(**arguments)


def test_packet_requires_the_dedicated_review_phase() -> None:
    with pytest.raises(ContractError, match="phase"):
        _packet(approval=_approval(phase="live_installation"))


def test_packet_requires_exact_artifact_hash_binding() -> None:
    wrong = dict(_FILES)
    wrong["PURPOSE.md"] = b"tampered\n"
    with pytest.raises(ContractError, match="artifact"):
        _packet(skill_files=wrong)
    missing = {"SKILL.md": _SKILL_MD}
    with pytest.raises(ContractError, match="artifact"):
        _packet(skill_files=missing)


def test_packet_refuses_consumed_or_expired_approval() -> None:
    with pytest.raises(ContractError, match="expired"):
        _packet(now="2026-09-03T00:00:00+00:00")
    with pytest.raises(ContractError, match="consumed"):
        _packet(approval=replace(_approval(), consumed=True))


def test_packet_validates_skill_authoring_contract() -> None:
    broken = dict(_FILES)
    broken["SKILL.md"] = b"# not frontmatter\n"
    with pytest.raises(ContractError, match="frontmatter"):
        _packet(skill_files=broken, approval=_approval(broken))


def test_packet_is_deterministic_and_manifest_binds_every_file() -> None:
    packet = _packet()
    assert packet == _packet()
    manifest = json.loads(packet["packet-manifest.json"])
    assert manifest["schema"] == OBSERVER_PACKET_SCHEMA
    assert manifest["handling"]["write_mode"] == "file_drop_create_only"
    assert manifest["handling"]["shared_observation_log_write"] == "forbidden"
    assert manifest["handling"]["installation"] == "human_review_required"
    listed = {item["path"]: item["sha256"] for item in manifest["files"]}
    assert listed == {
        f"skill/{path}": sha256_bytes(content) for path, content in _FILES.items()
    }
    assert "REVIEW-PACKET.md" in packet
    assert b"human review" in packet["REVIEW-PACKET.md"].lower().replace(b"\n", b" ")


def test_write_is_create_only_and_touches_nothing_else(tmp_path: Path) -> None:
    target = tmp_path / "packet"
    written = write_observer_review_packet(_packet(), target)
    assert sorted(path.relative_to(target).as_posix() for path in written) == [
        "REVIEW-PACKET.md",
        "packet-manifest.json",
        "skill/PURPOSE.md",
        "skill/SKILL.md",
    ]
    with pytest.raises(ContractError, match="already exists"):
        write_observer_review_packet(_packet(), target)
    assert (target / "skill" / "SKILL.md").read_bytes() == _SKILL_MD


def test_write_refuses_escaping_members_before_writing_anything(
    tmp_path: Path,
) -> None:
    sibling = tmp_path / "sibling"
    sibling.mkdir()
    tampered = dict(_packet())
    tampered["../sibling/escape.txt"] = b"escape\n"
    target = tmp_path / "packet"
    with pytest.raises(ContractError):
        write_observer_review_packet(tampered, target)
    assert not target.exists()
    assert list(sibling.iterdir()) == []


def test_approval_window_boundaries_are_inclusive_start_exclusive_end() -> None:
    packet = _packet(now="2026-09-01T00:00:00+00:00")
    assert "packet-manifest.json" in packet
    with pytest.raises(ContractError, match="expired"):
        _packet(now="2026-09-02T00:00:00+00:00")


def _written(tmp_path: Path) -> Path:
    target = tmp_path / "packet"
    write_observer_review_packet(_packet(), target)
    return target


def test_verify_accepts_a_freshly_written_packet(tmp_path: Path) -> None:
    target = _written(tmp_path)
    result = verify_observer_review_packet(target)
    assert result == {
        "schema": PACKET_VERIFICATION_SCHEMA,
        "skill_name": "demo-skill",
        "approval_id": "approval-1",
        "files_verified": 2,
        "verified": True,
    }


def test_verify_refuses_missing_packet_and_missing_members(tmp_path: Path) -> None:
    with pytest.raises(ContractError, match="missing"):
        verify_observer_review_packet(tmp_path / "absent")
    target = _written(tmp_path)
    (target / "packet-manifest.json").rename(target / "renamed.json")
    with pytest.raises(ContractError, match="no packet-manifest.json"):
        verify_observer_review_packet(target)
    (target / "renamed.json").rename(target / "packet-manifest.json")
    (target / "REVIEW-PACKET.md").unlink()
    with pytest.raises(ContractError, match="no REVIEW-PACKET.md"):
        verify_observer_review_packet(target)


def test_verify_refuses_manifest_shape_violations(tmp_path: Path) -> None:
    target = _written(tmp_path)
    manifest_path = target / "packet-manifest.json"
    original = json.loads(manifest_path.read_text(encoding="utf-8"))

    def rewrite(value) -> None:
        manifest_path.write_text(json.dumps(value), encoding="utf-8")

    manifest_path.write_text("not json object{", encoding="utf-8")
    with pytest.raises(ContractError, match="malformed"):
        verify_observer_review_packet(target)
    missing_field = {key: value for key, value in original.items() if key != "handling"}
    rewrite(missing_field)
    with pytest.raises(ContractError, match="fields differ"):
        verify_observer_review_packet(target)
    rewrite({**original, "schema": "asme.other.v1"})
    with pytest.raises(ContractError, match="schema differs"):
        verify_observer_review_packet(target)
    rewrite({**original, "handling": {**original["handling"], "installation": "auto"}})
    with pytest.raises(ContractError, match="handling block"):
        verify_observer_review_packet(target)
    rewrite({**original, "approval": {"approver": "someone"}})
    with pytest.raises(ContractError, match="approval identity"):
        verify_observer_review_packet(target)
    rewrite({**original, "files": []})
    with pytest.raises(ContractError, match="lists no files"):
        verify_observer_review_packet(target)
    rewrite({**original, "files": [{"path": "skill/SKILL.md", "sha256": "x"}]})
    with pytest.raises(ContractError, match="entry is invalid"):
        verify_observer_review_packet(target)
    outside = dict(original["files"][0])
    outside["path"] = "OUTSIDE.md"
    rewrite({**original, "files": [outside, *original["files"][1:]]})
    with pytest.raises(ContractError, match="outside skill/"):
        verify_observer_review_packet(target)
    ghost = dict(original["files"][0])
    ghost["path"] = "skill/GONE.md"
    rewrite({**original, "files": [ghost, *original["files"][1:]]})
    with pytest.raises(ContractError, match="member is missing"):
        verify_observer_review_packet(target)


def test_verify_refuses_content_and_length_tampering(tmp_path: Path) -> None:
    target = _written(tmp_path)
    purpose = target / "skill" / "PURPOSE.md"
    genuine = purpose.read_bytes()
    purpose.write_bytes(b"Xtaged review candidate\n")
    with pytest.raises(ContractError, match="differs from its manifest hash"):
        verify_observer_review_packet(target)
    purpose.write_bytes(genuine)
    manifest_path = target / "packet-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lied = [
        {**item, "bytes": item["bytes"] + 1}
        if item["path"] == "skill/PURPOSE.md"
        else item
        for item in manifest["files"]
    ]
    manifest_path.write_text(json.dumps({**manifest, "files": lied}), encoding="utf-8")
    with pytest.raises(ContractError, match="differs from its manifest hash"):
        verify_observer_review_packet(target)


def test_verify_refuses_unlisted_extra_files(tmp_path: Path) -> None:
    target = _written(tmp_path)
    (target / "skill" / "EXTRA.md").write_bytes(b"unlisted\n")
    with pytest.raises(ContractError, match="unlisted"):
        verify_observer_review_packet(target)
