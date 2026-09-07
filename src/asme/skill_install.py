"""Install Agent Skill Mastery Engine's own agent skill into a Claude Code skill directory.

This is the one write outside a domain root that Agent Skill Mastery Engine performs, and it copies only
the packaged SKILL.md and its companions. It never installs an evolved candidate: a
source under a staging or archive root, a source carrying a staged bundle manifest, or
a SKILL.md whose frontmatter name is not ``asme`` is refused before any byte is
written. Evolved candidates stay staged until a human installs them by hand.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
from typing import Any

from .canonical import ContractError, sha256_file
from .integration import validate_skill_authoring
from .skill_assets import SKILL_NAME, skill_files, skill_root

INSTALL_SCHEMA = "asme.skill-install.v1"
INSTALL_SCOPE = "asme_own_skill_only"
_STAGING_COMPONENTS = frozenset({"staging", "archives", "archive"})
_STAGED_BUNDLE_MARKER = "bundle-manifest.json"


def default_target() -> Path:
    """Return the Claude Code skill directory Agent Skill Mastery Engine installs into by default."""

    return Path.home() / ".claude" / "skills" / SKILL_NAME


def install_skill(
    *,
    target: Path | None = None,
    source: Path | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Copy Agent Skill Mastery Engine's own skill files into ``target`` and describe the result."""

    root = _validated_source(source)
    members = skill_files(root)
    metadata = validate_skill_authoring(
        (root / "SKILL.md").read_bytes(), expected_name=SKILL_NAME
    )
    destination = (default_target() if target is None else target).expanduser()
    replacing = _check_target(destination, root, force=force)
    files = [
        {
            "path": relative,
            "sha256": sha256_file(root / relative),
            "bytes": (root / relative).stat().st_size,
        }
        for relative in members
    ]
    if not dry_run:
        _replace_tree(root, destination, members, replacing=replacing)
    return {
        "schema": INSTALL_SCHEMA,
        "scope": INSTALL_SCOPE,
        "evolved_candidate_installed": False,
        "skill_name": metadata.name,
        "skill_version": metadata.version,
        "skill_last_updated": metadata.last_updated,
        "source": str(root),
        "target": str(destination),
        "dry_run": dry_run,
        "force": force,
        "replaced_existing": replacing,
        "installed": not dry_run,
        "file_count": len(files),
        "files": files,
    }


def _validated_source(source: Path | None) -> Path:
    if source is None:
        root = skill_root()
    else:
        if source.is_symlink():
            raise ContractError("install source must not be a symlink")
        if source.is_file():
            raise ContractError(
                "install source must be a directory; a staged .skill archive is never installed"
            )
        if not source.is_dir():
            raise ContractError(f"install source is not a directory: {source}")
        root = source.resolve(strict=True)
        if any(part in _STAGING_COMPONENTS for part in root.parts):
            raise ContractError(
                "install refuses staging and archive sources; evolved candidates stay "
                "staged until a human installs them"
            )
    if (root / _STAGED_BUNDLE_MARKER).exists():
        raise ContractError(
            "install refuses a staged bundle; only Agent Skill Mastery Engine's own skill can be installed"
        )
    skill = root / "SKILL.md"
    if skill.is_symlink() or not skill.is_file():
        raise ContractError("install source must contain Agent Skill Mastery Engine's SKILL.md")
    try:
        validate_skill_authoring(skill.read_bytes(), expected_name=SKILL_NAME)
    except ContractError as exc:
        raise ContractError(f"install accepts only Agent Skill Mastery Engine's own SKILL.md: {exc}") from exc
    return root


def _check_target(destination: Path, root: Path, *, force: bool) -> bool:
    if destination.is_symlink():
        raise ContractError("install target must not be a symlink")
    resolved = destination.resolve(strict=False)
    if resolved == root or resolved.is_relative_to(root) or root.is_relative_to(resolved):
        raise ContractError("install target must not overlap the skill source")
    if not destination.exists():
        return False
    if not force:
        raise ContractError(
            f"install target already exists: {destination}; pass --force to replace it"
        )
    if not destination.is_dir() or not (destination / "SKILL.md").is_file():
        raise ContractError(
            "--force replaces only an existing skill directory that holds a SKILL.md"
        )
    return True


def _replace_tree(
    root: Path, destination: Path, members: tuple[str, ...], *, replacing: bool
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.parent / f".{destination.name}.asme-install-{os.getpid()}"
    if staging.exists():
        shutil.rmtree(staging)
    try:
        staging.mkdir()
        for relative in members:
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        if replacing:
            shutil.rmtree(destination)
        os.rename(staging, destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
