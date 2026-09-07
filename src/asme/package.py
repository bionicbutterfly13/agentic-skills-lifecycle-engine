"""Deterministic, community-safe staging and archive primitives.

This module builds bytes only.  It has no install operation and does not write
to a runtime skill root.  A caller must publish the returned files through the
intent-first transaction engine.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
import io
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Iterable, Mapping, Sequence
import zipfile

from .canonical import (
    ContractError,
    canonical_bytes,
    require_identifier,
    safe_member_name,
    sha256_bytes,
    sha256_file,
)
from .transaction import PlannedWrite


BUNDLE_MANIFEST_SCHEMA = "asme.bundle-manifest.v1"
COMPATIBILITY_SCHEMA = "asme.compatibility.v1"
BUNDLE_MANIFEST_NAME = "bundle-manifest.json"

_BUILD_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".langgraph_api",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".serena",
        "__pycache__",
        "build",
        "dist",
    }
)
_BUILD_FILE_SUFFIXES = (".pyc", ".pyo", ".swp", ".tmp")
_BUILD_FILE_NAMES = frozenset({".DS_Store", "Thumbs.db"})
_PRIVATE_PATH_PATTERNS = (
    re.compile(rb"/" + b"Users" + rb"/[A-Za-z0-9._-]+/"),
    re.compile(rb"/" + b"home" + rb"/[A-Za-z0-9._-]+/"),
    re.compile(rb"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\"),
    re.compile(rb"/" + b"Volumes" + b"/" + b"Asylum" + rb"(?:/|\b)"),
)
_SECRET_PATTERNS = (
    re.compile(b"-----" + b"BEGIN " + rb"(?:RSA |EC |OPENSSH )?" + b"PRIVATE KEY" + b"-----"),
    re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(
        rb"(?i)\b(?:api[_-]?key|access[_-]?token|secret[_-]?key|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{12,}"
    ),
)
_CREDENTIAL_FILE_NAMES = frozenset({".env", ".env.local", "credentials.json", "secrets.json"})


@dataclass(frozen=True)
class Compatibility:
    contract_version: str
    core_version: str
    package_version: str
    adapter_id: str
    adapter_version: str
    runtime_min_tested: str
    runtime_max_tested: str
    runtime_tested: tuple[str, ...]
    schema: str = COMPATIBILITY_SCHEMA

    def __post_init__(self) -> None:
        require_identifier(self.adapter_id, field="adapter_id")
        if not self.runtime_tested:
            raise ContractError("runtime_tested must contain exact verified versions")
        for field_name, value in asdict(self).items():
            if field_name == "runtime_tested":
                continue
            if not isinstance(value, str) or not value.strip():
                raise ContractError(f"compatibility field cannot be blank: {field_name}")


@dataclass(frozen=True)
class ProjectionFile:
    path: str
    content: bytes
    sha256: str

    @classmethod
    def create(cls, path: str, content: bytes) -> "ProjectionFile":
        return cls(safe_member_name(path), content, sha256_bytes(content))


@dataclass(frozen=True)
class Projection:
    files: tuple[ProjectionFile, ...]
    swept_build_artifacts: tuple[str, ...]
    tree_sha256: str
    manifest_sha256: str

    def __post_init__(self) -> None:
        paths = [item.path for item in self.files]
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            raise ContractError("projection paths must be sorted and unique")
        expected = canonical_tree_hash({item.path: item.content for item in self.files})
        if expected != self.tree_sha256:
            raise ContractError("projection tree hash mismatch")
        manifest = next((item for item in self.files if item.path == BUNDLE_MANIFEST_NAME), None)
        if manifest is None or manifest.sha256 != self.manifest_sha256:
            raise ContractError("projection manifest hash mismatch")

    def content_map(self) -> dict[str, bytes]:
        return {item.path: item.content for item in self.files}


@dataclass(frozen=True)
class ArchiveVerification:
    tree_sha256: str
    member_count: int
    archive_sha256: str


def compatibility_from_mapping(raw: Mapping[str, Any]) -> Compatibility:
    """Decode one exact compatibility record for staging commands."""

    if not isinstance(raw, Mapping):
        raise ContractError("compatibility record must be an object")
    expected = {item.name for item in fields(Compatibility)}
    if set(raw) != expected:
        raise ContractError("compatibility record fields differ from the contract")
    values = dict(raw)
    tested = values.get("runtime_tested")
    if not isinstance(tested, (list, tuple)):
        raise ContractError("compatibility runtime_tested must be a list")
    values["runtime_tested"] = tuple(tested)
    try:
        return Compatibility(**values)
    except (TypeError, ValueError) as exc:
        raise ContractError("compatibility record differs from the contract") from exc


def canonical_tree_hash(files: Mapping[str, bytes]) -> str:
    """Hash normalized member paths and their byte hashes, not filesystem metadata."""

    rows = []
    for path in sorted(files):
        safe_member_name(path)
        rows.append({"path": path, "sha256": sha256_bytes(files[path]), "bytes": len(files[path])})
    return sha256_bytes(canonical_bytes(rows))


def build_projection(
    *,
    source_root: Path,
    compatibility: Compatibility,
    source_attribution: Sequence[Mapping[str, str]],
    generated_files: Mapping[str, bytes] | None = None,
    status: str = "staged_candidate_not_installed",
    license_policy: str = "resolved_mit_ccby4_distribution_gate4_blocked",
) -> Projection:
    """Create deterministic staged bytes from one canonical source tree."""

    source = source_root.resolve(strict=True)
    if source_root.is_symlink() or not source.is_dir():
        raise ContractError("projection source must be a non-symlink directory")
    payload: dict[str, bytes] = {}
    swept: list[str] = []
    for path in sorted(source.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(source).as_posix()
        if _is_build_artifact(relative):
            if path.is_file() or path.is_symlink():
                swept.append(relative)
            continue
        if path.is_symlink():
            raise ContractError(f"symlink forbidden in package source: {relative}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ContractError(f"non-regular package source entry: {relative}")
        safe_member_name(relative)
        if relative == BUNDLE_MANIFEST_NAME:
            continue
        payload[relative] = path.read_bytes()
    for path, content in sorted((generated_files or {}).items()):
        safe_member_name(path)
        if path == BUNDLE_MANIFEST_NAME:
            raise ContractError("bundle manifest is generated by the package core")
        if path in payload:
            raise ContractError(f"generated file collides with canonical source: {path}")
        if not isinstance(content, bytes):
            raise ContractError(f"generated file must contain bytes: {path}")
        payload[path] = content
    return _finish_projection(
        payload=payload,
        swept=swept,
        compatibility=compatibility,
        source_attribution=source_attribution,
        status=status,
        license_policy=license_policy,
    )


def build_projection_from_files(
    *,
    files: Mapping[str, bytes],
    compatibility: Compatibility,
    source_attribution: Sequence[Mapping[str, str]],
    generated_files: Mapping[str, bytes] | None = None,
    status: str = "staged_candidate_not_installed",
    license_policy: str = "resolved_mit_ccby4_distribution_gate4_blocked",
) -> Projection:
    """Build the same projection from immutable in-memory snapshot bytes."""

    payload: dict[str, bytes] = {}
    swept: list[str] = []
    for path, content in sorted(files.items()):
        safe_member_name(path)
        if not isinstance(content, bytes):
            raise ContractError(f"projection file must contain bytes: {path}")
        if _is_build_artifact(path):
            swept.append(path)
            continue
        if path == BUNDLE_MANIFEST_NAME:
            continue
        payload[path] = content
    for path, content in sorted((generated_files or {}).items()):
        safe_member_name(path)
        if path == BUNDLE_MANIFEST_NAME:
            raise ContractError("bundle manifest is generated by the package core")
        if path in payload:
            raise ContractError(f"generated file collides with canonical source: {path}")
        if not isinstance(content, bytes):
            raise ContractError(f"generated file must contain bytes: {path}")
        payload[path] = content
    return _finish_projection(
        payload=payload,
        swept=swept,
        compatibility=compatibility,
        source_attribution=source_attribution,
        status=status,
        license_policy=license_policy,
    )


def _finish_projection(
    *,
    payload: Mapping[str, bytes],
    swept: Sequence[str],
    compatibility: Compatibility,
    source_attribution: Sequence[Mapping[str, str]],
    status: str,
    license_policy: str,
) -> Projection:
    scan_community_safety(payload)
    payload_rows = [
        {"path": path, "sha256": sha256_bytes(payload[path]), "bytes": len(payload[path])}
        for path in sorted(payload)
    ]
    manifest = {
        "schema": BUNDLE_MANIFEST_SCHEMA,
        "status": status,
        "license_policy": license_policy,
        "compatibility": asdict(compatibility),
        "source_attribution": [dict(item) for item in source_attribution],
        "payload_files": payload_rows,
        # A manifest cannot contain its own cryptographic hash.  Its bytes are
        # instead bound by the external staged tree hash and archive equality.
        "manifest_self_hash": "external_tree_hash",
    }
    manifest_bytes = canonical_bytes(manifest)
    complete = {**payload, BUNDLE_MANIFEST_NAME: manifest_bytes}
    scan_community_safety(complete)
    files = tuple(ProjectionFile.create(path, complete[path]) for path in sorted(complete))
    return Projection(
        files=files,
        swept_build_artifacts=tuple(sorted(swept)),
        tree_sha256=canonical_tree_hash(complete),
        manifest_sha256=sha256_bytes(manifest_bytes),
    )


def validate_existing_projection(root: Path, projection: Projection) -> bool:
    """Return true only when an existing staged tree has exact path-byte identity."""

    if not root.exists():
        return False
    if root.is_symlink() or not root.is_dir():
        raise ContractError("existing projection root is not a safe directory")
    actual: dict[str, bytes] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise ContractError(f"unsafe existing projection entry: {relative}")
        if path.is_file():
            safe_member_name(relative)
            actual[relative] = path.read_bytes()
    return actual == projection.content_map()


def ensure_staging_destination(
    *, destination: Path, staging_root: Path, forbidden_live_roots: Iterable[Path]
) -> Path:
    """Require a destination inside staging and outside every declared live root."""

    stage = staging_root.resolve(strict=False)
    target = destination.resolve(strict=False)
    if target == stage or not target.is_relative_to(stage):
        raise ContractError("destination must be a child of the configured staging root")
    for live in forbidden_live_roots:
        resolved_live = live.resolve(strict=False)
        if target == resolved_live or target.is_relative_to(resolved_live):
            raise ContractError("staging destination overlaps a forbidden live root")
    return target


def build_archive(projection: Projection, *, recorded_at: datetime) -> bytes:
    """Build one normalized `.skill` ZIP from the exact staged projection bytes."""

    if recorded_at.tzinfo is None:
        raise ContractError("archive recorded_at must include a timezone")
    stamp = recorded_at.astimezone(timezone.utc)
    if not 1980 <= stamp.year <= 2107:
        raise ContractError("ZIP timestamp year must be in [1980,2107]")
    output = io.BytesIO()
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for item in projection.files:
            info = zipfile.ZipInfo(item.path, date_time=stamp.timetuple()[:6])
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, item.content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    result = output.getvalue()
    verified = verify_archive(result, expected=projection)
    if verified.tree_sha256 != projection.tree_sha256:
        raise ContractError("archive member path-byte hash differs from staged tree")
    return result


def verify_archive(archive_bytes: bytes, *, expected: Projection | None = None) -> ArchiveVerification:
    """Reject unsafe members and return the canonical path-byte identity."""

    members: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes), mode="r") as archive:
            for info in archive.infolist():
                name = safe_member_name(info.filename)
                if info.is_dir() or name.endswith("/"):
                    raise ContractError("archive directory entries are forbidden")
                if name in members:
                    raise ContractError(f"duplicate archive member: {name}")
                mode = (info.external_attr >> 16) & 0o177777
                if mode != 0o100644:
                    raise ContractError(f"archive member mode must be regular 0644: {name}")
                members[name] = archive.read(info)
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise ContractError("invalid skill archive") from exc
    scan_community_safety(members)
    if expected is not None and members != expected.content_map():
        raise ContractError("archive membership or bytes differ from staged projection")
    return ArchiveVerification(
        tree_sha256=canonical_tree_hash(members),
        member_count=len(members),
        archive_sha256=sha256_bytes(archive_bytes),
    )


def scan_community_safety(files: Mapping[str, bytes]) -> None:
    """Fail closed on credential files, private absolute paths, and secret-like values."""

    for path, content in files.items():
        safe_member_name(path)
        name = PurePosixPath(path).name
        if name in _CREDENTIAL_FILE_NAMES or name.startswith(".env."):
            raise ContractError(f"credential-like file forbidden in community package: {path}")
        if any(pattern.search(content) for pattern in _PRIVATE_PATH_PATTERNS):
            raise ContractError(f"private absolute path detected in package file: {path}")
        if any(pattern.search(content) for pattern in _SECRET_PATTERNS):
            raise ContractError(f"credential-like content detected in package file: {path}")


def _is_build_artifact(relative: str) -> bool:
    path = PurePosixPath(relative)
    if any(part in _BUILD_DIRECTORY_NAMES for part in path.parts):
        return True
    name = path.name
    return (
        name in _BUILD_FILE_NAMES
        or name.startswith(".~lock.")
        or name.endswith(_BUILD_FILE_SUFFIXES)
    )


def read_bundle_manifest(projection: Projection) -> dict[str, Any]:
    """Parse and revalidate the generated manifest against projection payload bytes."""

    manifest_file = next(item for item in projection.files if item.path == BUNDLE_MANIFEST_NAME)
    try:
        raw = json.loads(manifest_file.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("bundle manifest is not valid UTF-8 JSON") from exc
    if not isinstance(raw, dict) or raw.get("schema") != BUNDLE_MANIFEST_SCHEMA:
        raise ContractError("bundle manifest schema is invalid")
    actual_payload = {
        item.path: item
        for item in projection.files
        if item.path != BUNDLE_MANIFEST_NAME
    }
    rows = raw.get("payload_files")
    if not isinstance(rows, list):
        raise ContractError("bundle manifest payload_files must be a list")
    recorded: dict[str, tuple[str, int]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ContractError("bundle manifest file record must be an object")
        path = safe_member_name(row.get("path"))
        if path in recorded:
            raise ContractError(f"duplicate bundle manifest path: {path}")
        recorded[path] = (row.get("sha256"), row.get("bytes"))
    expected = {path: (item.sha256, len(item.content)) for path, item in actual_payload.items()}
    if recorded != expected:
        raise ContractError("bundle manifest does not match projection payload")
    return raw


def projection_write_plan(
    projection: Projection, *, prefix: str, root_name: str = "staging"
) -> tuple[PlannedWrite, ...]:
    """Plan an idempotent stage without writing any live or staged path directly."""

    safe_member_name(prefix)
    return tuple(
        PlannedWrite.from_bytes(
            root=root_name,
            path=f"{prefix}/{item.path}",
            content=item.content,
            mode=0o600,
            allow_existing_identical=True,
        )
        for item in projection.files
    )


def archive_write_plan(
    archive_bytes: bytes, *, member: str, root_name: str = "archives"
) -> PlannedWrite:
    """Plan one idempotent normalized archive publication."""

    safe_member_name(member)
    verify_archive(archive_bytes)
    return PlannedWrite.from_bytes(
        root=root_name,
        path=member,
        content=archive_bytes,
        mode=0o600,
        allow_existing_identical=True,
    )
