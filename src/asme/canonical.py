"""Canonical serialization, hashing, atomic writes, and path safety."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any, Iterable


IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


class ContractError(ValueError):
    """Input violates an Agent Skill Mastery Engine contract."""


def canonical_bytes(value: Any) -> bytes:
    """Return stable UTF-8 JSON bytes with no platform-specific whitespace."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_json(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def require_identifier(value: str, *, field: str = "identifier") -> str:
    if not isinstance(value, str) or not IDENTIFIER_RE.fullmatch(value):
        raise ContractError(f"{field} must match {IDENTIFIER_RE.pattern}")
    return value


def safe_member_name(value: str) -> str:
    """Validate one regular-file archive member in normalized POSIX form."""

    if not isinstance(value, str) or not value or "\\" in value:
        raise ContractError("archive member must be a non-empty POSIX path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or str(pure) != value:
        raise ContractError(f"unsafe archive member: {value!r}")
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise ContractError(f"unsafe archive member: {value!r}")
    return value


def require_regular_file(path: Path, *, root: Path | None = None) -> Path:
    """Require a regular non-symlink file, optionally contained in root."""

    if path.is_symlink() or not path.is_file():
        raise ContractError(f"expected regular non-symlink file: {path}")
    resolved = path.resolve(strict=True)
    if root is not None:
        resolved_root = root.resolve(strict=True)
        if not resolved.is_relative_to(resolved_root):
            raise ContractError(f"path escapes declared root: {path}")
    return resolved


def atomic_write_bytes(path: Path, content: bytes, *, mode: int = 0o600) -> None:
    """Atomically replace a file after fsyncing bytes and its parent directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_json(path: Path, value: Any, *, mode: int = 0o600) -> None:
    atomic_write_bytes(path, canonical_bytes(value), mode=mode)


def tree_manifest(root: Path, *, excluded: Iterable[str] = ()) -> dict[str, str]:
    """Hash a regular-file tree and reject symlinks anywhere below root."""

    excluded_set = set(excluded)
    manifest: dict[str, str] = {}
    if not root.exists():
        return manifest
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if relative in excluded_set:
            continue
        if path.is_symlink():
            raise ContractError(f"symlink forbidden in governed tree: {relative}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ContractError(f"non-regular entry in governed tree: {relative}")
        safe_member_name(relative)
        manifest[relative] = sha256_file(path)
    return manifest
