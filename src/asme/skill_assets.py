"""Locate Agent Skill Mastery Engine's own agent skill: SKILL.md and its companion files.

The canonical copies live at the repository root. A built wheel carries them under
``asme/skill/`` (see ``setup.py``); an editable or source checkout serves the root
files directly. This module deliberately has no package-relative imports so that
``setup.py`` can load it by file path at build time without importing the package.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
import shutil

SKILL_NAME = "asme"
SKILL_FILES: tuple[str, ...] = ("SKILL.md", "PURPOSE.md", "NOTICE.md", "LICENSE")
SKILL_DIRECTORIES: tuple[str, ...] = ("references",)
PACKAGED_SUBDIRECTORY = "skill"
_IGNORED_NAMES = frozenset({"__pycache__", ".DS_Store", "Thumbs.db"})


def skill_root() -> Path:
    """Return the directory that holds Agent Skill Mastery Engine's own SKILL.md and companions."""

    packaged = resources.files("asme").joinpath(PACKAGED_SUBDIRECTORY)
    if isinstance(packaged, Path) and _holds_skill(packaged):
        return packaged
    checkout = Path(__file__).resolve().parents[2]
    if (checkout / "src" / "asme").is_dir() and _holds_skill(checkout):
        return checkout
    raise FileNotFoundError(
        "Agent Skill Mastery Engine skill files are neither packaged under asme/skill nor present in a "
        "source checkout"
    )


def skill_files(root: Path | None = None) -> tuple[str, ...]:
    """List the relative POSIX paths that make up the installable skill, sorted."""

    base = skill_root() if root is None else root
    members: list[str] = []
    for name in SKILL_FILES:
        path = base / name
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError(f"skill file missing or not a regular file: {name}")
        members.append(name)
    for directory in SKILL_DIRECTORIES:
        folder = base / directory
        if folder.is_symlink() or not folder.is_dir():
            raise FileNotFoundError(f"skill directory missing: {directory}")
        for path in sorted(folder.rglob("*"), key=lambda item: item.as_posix()):
            relative = path.relative_to(base)
            if any(part in _IGNORED_NAMES or part.startswith(".") for part in relative.parts):
                continue
            if path.is_symlink():
                raise FileNotFoundError(f"symlink forbidden in skill tree: {relative.as_posix()}")
            if path.is_file():
                members.append(relative.as_posix())
    return tuple(members)


def copy_skill_tree(source_root: Path, destination: Path) -> tuple[str, ...]:
    """Copy exactly the skill members from ``source_root`` into ``destination``."""

    members = skill_files(source_root)
    destination.mkdir(parents=True, exist_ok=True)
    for relative in members:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)
    return members


def _holds_skill(base: Path) -> bool:
    return all((base / name).is_file() for name in SKILL_FILES) and all(
        (base / directory).is_dir() for directory in SKILL_DIRECTORIES
    )
