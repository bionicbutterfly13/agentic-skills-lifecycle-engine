#!/usr/bin/env python3
"""Read-only, stdlib-only validation of a pinned ASME compatibility import."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys


class VerificationError(ValueError):
    """The receipt or filesystem does not preserve the pinned source."""


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if result.returncode:
        # Git diagnostics can contain remote URLs or local private data.
        raise VerificationError(f"Git {args[0]} failed with exit {result.returncode}")
    return result.stdout


def contained_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise VerificationError("Invalid relative path")
    path = PurePosixPath(relative)
    if path.is_absolute() or path.as_posix() != relative or any(
        part in {".", ".."} for part in path.parts
    ):
        raise VerificationError("Unsafe relative path")
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise VerificationError(f"Symlink traversal rejected: {relative}")
    if not current.is_file() or not current.resolve().is_relative_to(root.resolve()):
        raise VerificationError(f"Missing or uncontained file: {relative}")
    return current


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_file(root: Path, name: str, expected_hash: str, mode: str) -> bytes:
    path = contained_file(root, name)
    data = path.read_bytes()
    if digest(data) != expected_hash:
        raise VerificationError(f"Content mismatch: {name}")
    file_mode = path.stat().st_mode
    actual_mode = "100755" if file_mode & stat.S_IXUSR else "100644"
    if not stat.S_ISREG(file_mode) or actual_mode != mode:
        raise VerificationError(f"Git mode mismatch: {name}")
    return data


def verify(source: Path, target: Path, revision: str, manifest: dict) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise VerificationError("Source revision must be a full lowercase commit SHA")
    if manifest.get("schema") != "lifecycle.asme-port.v1":
        raise VerificationError("Unsupported manifest schema")
    if manifest.get("source_revision") != revision:
        raise VerificationError("Manifest source revision mismatch")
    toplevel = Path(git(source, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if source.resolve() != toplevel:
        raise VerificationError("Source must be the Git worktree top level")
    if git(source, "rev-parse", "HEAD").decode().strip() != revision:
        raise VerificationError("Source HEAD differs from the pinned revision")
    tree = {}
    for record in git(source, "ls-tree", "--full-tree", "-rz", revision).split(b"\0"):
        if not record:
            continue
        metadata, path_bytes = record.split(b"\t", 1)
        mode, kind, object_id = metadata.decode().split()
        name = path_bytes.decode("utf-8")
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise VerificationError(f"Unsupported source type or mode: {name}")
        if name in tree:
            raise VerificationError("Duplicate source Git path")
        tree[name] = (mode, object_id)
    index = {}
    for record in git(source, "ls-files", "--stage", "-z").split(b"\0"):
        if not record:
            continue
        metadata, path_bytes = record.split(b"\t", 1)
        mode, object_id, stage = metadata.decode().split()
        name = path_bytes.decode("utf-8")
        if stage != "0" or name in index:
            raise VerificationError("Source index contains unmerged or duplicate entries")
        index[name] = (mode, object_id)
    if index != tree:
        raise VerificationError("Source index differs from the pinned Git tree")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
        raise VerificationError("Manifest entries must be objects")
    names = [entry.get("source_path") for entry in entries]
    if not all(isinstance(name, str) for name in names):
        raise VerificationError("Invalid source path in receipt")
    if len(set(names)) != len(names):
        raise VerificationError("Duplicate source mapping")
    if set(names) != set(tree):
        raise VerificationError("Receipt source paths differ from the complete pinned tree")
    destinations = set()
    fingerprints = []
    retained = 0
    for entry in sorted(entries, key=lambda row: row["source_path"]):
        name = entry["source_path"]
        mode, object_id = tree[name]
        source_hash = digest(git(source, "cat-file", "blob", object_id))
        if entry.get("sha256") != source_hash or entry.get("git_mode") != mode:
            raise VerificationError(f"Receipt does not match pinned Git blob: {name}")
        check_file(source, name, source_hash, mode)
        disposition = entry.get("disposition")
        destination = entry.get("destination")
        historical = entry.get("historical_destination")
        if name.startswith(".planning/codebase/") and disposition != "retained_at_source":
            raise VerificationError(f"Source planning must remain at source: {name}")
        if disposition == "retained_at_source":
            if not name.startswith(".planning/codebase/") or destination is not None or historical:
                raise VerificationError(f"Invalid retained-at-source disposition: {name}")
            retained += 1
            continue
        if destination != name:
            raise VerificationError(f"Canonical destination must preserve the source path: {name}")
        if disposition == "historical_copy_with_current_document":
            if name not in {"README.md", "PROVENANCE.md", "CONTRIBUTING.md"}:
                raise VerificationError("Only approved current-facing documents may differ")
            if historical != f"docs/migration/asme-source/{name}":
                raise VerificationError(f"Unexpected historical destination: {name}")
            expected_current = entry.get("current_sha256")
            if not isinstance(expected_current, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_current):
                raise VerificationError(f"Missing current document digest: {name}")
            current = check_file(target, destination, expected_current, mode)
            if f"]({historical})".encode() not in current:
                raise VerificationError(f"Current document must link its exact historical copy: {name}")
            checks = [(destination, expected_current), (historical, source_hash)]
        elif disposition == "copied_exact" and historical is None:
            checks = [(destination, source_hash)]
        else:
            raise VerificationError(f"Unsupported preservation disposition: {name}")
        for destination, expected in checks:
            if destination in destinations:
                raise VerificationError("Duplicate destination mapping")
            destinations.add(destination)
            check_file(target, destination, expected, mode)
            fingerprints.append({"path": destination, "sha256": expected, "git_mode": mode})
    content_identity = json.dumps(sorted(fingerprints, key=lambda row: row["path"]),
                                  sort_keys=True, separators=(",", ":")).encode()
    return {"status": "pass", "source_revision": revision, "tracked_paths": len(tree),
            "retained_at_source": retained, "preserved_destinations": len(destinations),
            "destination_content_digest": digest(content_identity),
            "digest_scope": "Manifest destination paths, SHA256 values, and Git modes; sorted compact JSON"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--check", action="store_true", required=True)
    args = parser.parse_args(argv)
    target = Path(__file__).resolve().parents[1]
    try:
        manifest_path = contained_file(target, "docs/migration/asme-source-manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        result = verify(args.source.resolve(), target, args.source_revision, manifest)
    except (VerificationError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
