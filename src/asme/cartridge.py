"""Immutable domain programs and declared read resources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import stat
from typing import Mapping

from .canonical import ContractError, hash_json, require_regular_file, safe_member_name, sha256_bytes
from .domain import DeclaredDomain
from .transaction import PlannedWrite


CARTRIDGE_SCHEMA = "asme.cartridge.v1"


@dataclass(frozen=True)
class CartridgeFile:
    path: str
    content: bytes
    sha256: str
    mode: int

    @classmethod
    def create(cls, path: str, content: bytes, *, mode: int) -> "CartridgeFile":
        if mode not in {0o600, 0o700}:
            raise ContractError("cartridge mode must be 0600 or 0700")
        return cls(safe_member_name(path), content, sha256_bytes(content), mode)


@dataclass(frozen=True)
class DomainCartridge:
    files: tuple[CartridgeFile, ...]
    digest: str
    schema: str = CARTRIDGE_SCHEMA

    def __post_init__(self) -> None:
        paths = [item.path for item in self.files]
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            raise ContractError("cartridge paths must be sorted and unique")
        expected = hash_json(
            {
                "schema": self.schema,
                "files": [
                    {
                        "path": item.path,
                        "sha256": item.sha256,
                        "bytes": len(item.content),
                        "mode": item.mode,
                    }
                    for item in self.files
                ],
            }
        )
        if expected != self.digest:
            raise ContractError("cartridge digest mismatch")

    @classmethod
    def from_paths(
        cls,
        *,
        domain: DeclaredDomain,
        prompt: Path,
        extractor: Path,
        scorer: Path,
        read_resources: Mapping[str, Path],
    ) -> "DomainCartridge":
        resource_paths = dict(read_resources)
        if set(resource_paths) != set(domain.read_resource_ids):
            raise ContractError("cartridge read resources differ from the domain seal")
        files = [
            CartridgeFile.create(
                "prompt.txt", require_regular_file(prompt).read_bytes(), mode=0o600
            ),
            CartridgeFile.create(
                "extractor", require_regular_file(extractor).read_bytes(), mode=0o700
            ),
            CartridgeFile.create(
                "scorer", require_regular_file(scorer).read_bytes(), mode=0o700
            ),
        ]
        for resource_id in domain.read_resource_ids:
            files.append(
                CartridgeFile.create(
                    f"resources/{resource_id}",
                    require_regular_file(resource_paths[resource_id]).read_bytes(),
                    mode=0o600,
                )
            )
        ordered = tuple(sorted(files, key=lambda item: item.path))
        cartridge = cls(ordered, _cartridge_digest(ordered))
        cartridge.verify_domain(domain)
        return cartridge

    def verify_domain(self, domain: DeclaredDomain) -> None:
        by_path = {item.path: item.sha256 for item in self.files}
        expected = {
            "prompt.txt": domain.prompt_hash,
            "extractor": domain.extractor_hash,
            "scorer": domain.scorer_hash,
            **{
                f"resources/{name}": digest
                for name, digest in domain.read_resource_hashes
            },
        }
        if by_path != expected:
            changed = sorted(path for path in set(by_path) | set(expected) if by_path.get(path) != expected.get(path))
            raise ContractError(f"cartridge content differs from domain seal: {changed}")

    def manifest(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "digest": self.digest,
            "files": [
                {
                    "path": item.path,
                    "sha256": item.sha256,
                    "bytes": len(item.content),
                    "mode": item.mode,
                }
                for item in self.files
            ],
        }

    def write_plan(self, *, root_name: str = "domain") -> tuple[PlannedWrite, ...]:
        return tuple(
            PlannedWrite.from_bytes(
                root=root_name,
                path=f"cartridge/{item.path}",
                content=item.content,
                mode=item.mode,
            )
            for item in self.files
        )


def _cartridge_digest(files: tuple[CartridgeFile, ...]) -> str:
    return hash_json(
        {
            "schema": CARTRIDGE_SCHEMA,
            "files": [
                {
                    "path": item.path,
                    "sha256": item.sha256,
                    "bytes": len(item.content),
                    "mode": item.mode,
                }
                for item in files
            ],
        }
    )


def verify_cartridge_tree(
    root: Path, manifest: Mapping[str, object], *, domain: DeclaredDomain
) -> str:
    """Rebuild the cartridge from owned bytes and require exact manifest identity."""

    if manifest.get("schema") != CARTRIDGE_SCHEMA or not isinstance(manifest.get("files"), list):
        raise ContractError("recorded cartridge manifest is malformed")
    expected_rows = manifest["files"]
    recorded: dict[str, Mapping[str, object]] = {}
    for row in expected_rows:
        if not isinstance(row, Mapping):
            raise ContractError("recorded cartridge file row is malformed")
        path = safe_member_name(row.get("path"))
        if set(row) != {"path", "sha256", "bytes", "mode"} or path in recorded:
            raise ContractError("recorded cartridge file row differs from the contract")
        recorded[path] = row
    if root.is_symlink() or not root.is_dir():
        raise ContractError("recorded cartridge root is missing or unsafe")
    actual_paths: set[str] = set()
    files: list[CartridgeFile] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise ContractError(f"recorded cartridge entry is unsafe: {relative}")
        if path.is_dir():
            continue
        safe_member_name(relative)
        actual_paths.add(relative)
        row = recorded.get(relative)
        if row is None:
            raise ContractError(f"unrecorded cartridge file exists: {relative}")
        content = path.read_bytes()
        mode = stat.S_IMODE(path.stat().st_mode)
        item = CartridgeFile.create(relative, content, mode=mode)
        if item.sha256 != row.get("sha256") or len(content) != row.get("bytes") or mode != row.get("mode"):
            raise ContractError(f"recorded cartridge file drifted: {relative}")
        files.append(item)
    if actual_paths != set(recorded):
        raise ContractError("recorded cartridge membership differs from its manifest")
    cartridge = DomainCartridge(tuple(files), str(manifest.get("digest")))
    cartridge.verify_domain(domain)
    return cartridge.digest
