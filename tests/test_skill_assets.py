from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

from asme.integration import validate_skill_authoring
from asme.skill_assets import (
    PACKAGED_SUBDIRECTORY,
    SKILL_DIRECTORIES,
    SKILL_FILES,
    SKILL_NAME,
    copy_skill_tree,
    skill_files,
    skill_root,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BUILD_NOISE = (".git", ".venv", "build", "dist", "__pycache__", ".pytest_cache", "*.egg-info")


def test_skill_root_holds_asme_own_skill_and_every_companion() -> None:
    root = skill_root()
    assert root.is_dir() and not root.is_symlink()
    for name in SKILL_FILES:
        assert (root / name).is_file(), name
    for directory in SKILL_DIRECTORIES:
        assert (root / directory).is_dir(), directory
    metadata = validate_skill_authoring(
        (root / "SKILL.md").read_bytes(), expected_name=SKILL_NAME
    )
    assert metadata.name == "asme"


def test_skill_files_are_sorted_relative_posix_paths_with_references() -> None:
    members = skill_files()
    assert members[: len(SKILL_FILES)] == SKILL_FILES
    references = members[len(SKILL_FILES) :]
    assert references == tuple(sorted(references))
    assert "references/fidelity.md" in references
    assert "references/verification/README.md" in references
    assert all("/" in item and not item.startswith("/") for item in references)
    assert not any(".." in Path(item).parts for item in members)


def test_skill_files_refuses_incomplete_source(tmp_path: Path) -> None:
    (tmp_path / "SKILL.md").write_text("---\n---\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        skill_files(tmp_path)


def test_copy_skill_tree_copies_exactly_the_members(tmp_path: Path) -> None:
    root = skill_root()
    destination = tmp_path / "skill"
    members = copy_skill_tree(root, destination)
    copied = sorted(
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    )
    assert copied == sorted(members)
    for relative in members:
        assert (destination / relative).read_bytes() == (root / relative).read_bytes()


def test_built_wheel_carries_the_skill_files(tmp_path: Path) -> None:
    if importlib.util.find_spec("setuptools") is None:
        pytest.skip("setuptools is not importable in this environment")
    tree = tmp_path / "tree"
    shutil.copytree(_REPO_ROOT, tree, ignore=shutil.ignore_patterns(*_BUILD_NOISE))
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from setuptools import build_meta; "
            "print(build_meta.build_wheel(sys.argv[1]))",
            str(wheels),
        ],
        cwd=tree,
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    wheel = wheels / completed.stdout.strip().splitlines()[-1]
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        packaged = {
            name[len(f"asme/{PACKAGED_SUBDIRECTORY}/") :]
            for name in names
            if name.startswith(f"asme/{PACKAGED_SUBDIRECTORY}/")
        }
        assert packaged == set(skill_files(_REPO_ROOT))
        assert archive.read(f"asme/{PACKAGED_SUBDIRECTORY}/SKILL.md") == (
            _REPO_ROOT / "SKILL.md"
        ).read_bytes()
