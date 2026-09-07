"""Immutable skill snapshots, authoritative pointers, and disposable mirrors."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Iterable, Mapping

from .canonical import ContractError, safe_member_name, sha256_bytes, sha256_file
from .transaction import PlannedDeletion, PlannedWrite


@dataclass(frozen=True)
class SnapshotFile:
    path: str
    content: bytes
    sha256: str

    @classmethod
    def create(cls, path: str, content: bytes) -> "SnapshotFile":
        return cls(safe_member_name(path), content, sha256_bytes(content))


@dataclass(frozen=True)
class Snapshot:
    snapshot_hash: str
    files: tuple[SnapshotFile, ...]

    def __post_init__(self) -> None:
        paths = [item.path for item in self.files]
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            raise ContractError("snapshot paths must be sorted and unique")
        if _snapshot_hash(self.files) != self.snapshot_hash:
            raise ContractError("snapshot hash does not match its files")

    @classmethod
    def empty(cls) -> "Snapshot":
        return cls(_snapshot_hash(()), ())

    @classmethod
    def from_directory(
        cls, source_root: Path, *, forbidden_markers: Iterable[str] = ()
    ) -> "Snapshot":
        root = source_root.resolve(strict=True)
        if source_root.is_symlink() or not root.is_dir():
            raise ContractError("snapshot source must be a non-symlink directory")
        contents: dict[str, bytes] = {}
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise ContractError(f"symlink forbidden in snapshot: {relative}")
            if path.is_dir():
                continue
            if not path.is_file():
                raise ContractError(f"non-regular snapshot entry: {relative}")
            contents[relative] = path.read_bytes()
        return cls.from_mapping(contents, forbidden_markers=forbidden_markers)

    @classmethod
    def from_mapping(
        cls,
        contents: Mapping[str, bytes],
        *,
        forbidden_markers: Iterable[str] = (),
    ) -> "Snapshot":
        markers = tuple(marker.encode("utf-8") for marker in forbidden_markers if marker)
        files: list[SnapshotFile] = []
        for relative, content in sorted(contents.items()):
            safe_member_name(relative)
            if not isinstance(content, bytes):
                raise ContractError(f"snapshot content must be bytes: {relative}")
            for marker in markers:
                if marker in content:
                    raise ContractError(
                        f"provenance marker propagated into candidate: {relative}"
                    )
            files.append(SnapshotFile.create(relative, content))
        ordered = tuple(files)
        return cls(_snapshot_hash(ordered), ordered)

    def content_map(self) -> dict[str, bytes]:
        return {item.path: item.content for item in self.files}


def _snapshot_hash(files: Iterable[SnapshotFile]) -> str:
    return hashlib.sha256(_snapshot_material(tuple(files))).hexdigest()


def _snapshot_material(files: Iterable[SnapshotFile]) -> bytes:
    material = bytearray()
    for item in files:
        path = item.path.encode("utf-8")
        material.extend(len(path).to_bytes(8, "big"))
        material.extend(path)
        material.extend(len(item.content).to_bytes(8, "big"))
        material.extend(item.content)
    return bytes(material)


def snapshot_material(snapshot: Snapshot) -> bytes:
    """Return the exact length-framed bytes whose SHA-256 names the snapshot."""

    material = _snapshot_material(snapshot.files)
    if sha256_bytes(material) != snapshot.snapshot_hash:
        raise ContractError("snapshot material differs from its hash")
    return material


def snapshot_write_plan(snapshot: Snapshot, *, root_name: str = "snapshots") -> tuple[PlannedWrite, ...]:
    """Plan idempotent publication into `<snapshot_hash>/<member>` paths."""

    return tuple(
        PlannedWrite.from_bytes(
            root=root_name,
            path=f"{snapshot.snapshot_hash}/{item.path}",
            content=item.content,
            mode=0o600,
            allow_existing_identical=True,
        )
        for item in snapshot.files
    )


def verify_snapshot(root: Path, snapshot: Snapshot) -> None:
    """Require exact membership and byte identity for one immutable snapshot."""

    directory = root / snapshot.snapshot_hash
    if not snapshot.files and not directory.exists():
        return
    if directory.is_symlink() or not directory.is_dir():
        raise ContractError("snapshot directory is missing or unsafe")
    actual: dict[str, str] = {}
    for path in sorted(directory.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(directory).as_posix()
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise ContractError(f"unsafe snapshot entry: {relative}")
        if path.is_file():
            safe_member_name(relative)
            actual[relative] = sha256_file(path)
    expected = {item.path: item.sha256 for item in snapshot.files}
    if actual != expected:
        raise ContractError("immutable snapshot membership or bytes changed")


def mirror_rebuild_plan(
    *, mirror_root: Path, snapshot: Snapshot, root_name: str = "mirror"
) -> tuple[tuple[PlannedWrite, ...], tuple[PlannedDeletion, ...]]:
    """Plan complete lazy mirror repair without treating the mirror as authority."""

    actual: dict[str, str] = {}
    if mirror_root.exists():
        if mirror_root.is_symlink() or not mirror_root.is_dir():
            raise ContractError("mirror root is unsafe")
        for path in sorted(mirror_root.rglob("*"), key=lambda item: item.as_posix()):
            relative = path.relative_to(mirror_root).as_posix()
            if path.is_symlink() or (not path.is_file() and not path.is_dir()):
                raise ContractError(f"unsafe mirror entry: {relative}")
            if path.is_file():
                safe_member_name(relative)
                actual[relative] = sha256_file(path)
    expected = {item.path: item for item in snapshot.files}
    writes = []
    for path, item in sorted(expected.items()):
        before = actual.get(path)
        if before == item.sha256:
            continue
        writes.append(
            PlannedWrite.from_bytes(
                root=root_name,
                path=path,
                content=item.content,
                expected_before_sha256=before,
                mode=0o600,
            )
        )
    deletions = tuple(
        PlannedDeletion(root=root_name, path=path, expected_sha256=digest)
        for path, digest in sorted(actual.items())
        if path not in expected
    )
    return tuple(writes), deletions


def active_snapshot(state: Mapping[str, object], snapshots: Mapping[str, Snapshot]) -> Snapshot:
    """Resolve only the active pointer from state, never a mirror or newest directory."""

    pointer = state.get("active_snapshot_hash")
    if not isinstance(pointer, str) or pointer not in snapshots:
        raise ContractError("active snapshot pointer is missing or unknown")
    selected = snapshots[pointer]
    if selected.snapshot_hash != pointer:
        raise ContractError("active snapshot pointer hash mismatch")
    return selected
