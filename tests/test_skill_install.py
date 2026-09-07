from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from asme.canonical import ContractError
from asme.cli import main
from asme.skill_assets import skill_files, skill_root
from asme.skill_install import INSTALL_SCOPE, default_target, install_skill

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _entries(directory: Path) -> set[str]:
    return {path.name for path in directory.iterdir()} if directory.exists() else set()


def _copy_source(destination: Path) -> Path:
    root = skill_root()
    for relative in skill_files(root):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / relative).read_bytes())
    return destination


def test_default_target_is_the_claude_code_skill_directory() -> None:
    assert default_target() == Path.home() / ".claude" / "skills" / "asme"


def test_dry_run_writes_nothing_and_reports_the_plan(tmp_path: Path) -> None:
    parent = tmp_path / "skills"
    parent.mkdir()
    before = _entries(parent)
    result = install_skill(target=parent / "asme", dry_run=True)
    assert result["dry_run"] is True and result["installed"] is False
    assert result["scope"] == INSTALL_SCOPE
    assert result["evolved_candidate_installed"] is False
    assert result["skill_name"] == "asme"
    assert tuple(item["path"] for item in result["files"]) == skill_files()
    assert _entries(parent) == before
    assert not (parent / "asme").exists()


def test_install_copies_exactly_the_skill_files(tmp_path: Path) -> None:
    target = tmp_path / "skills" / "asme"
    result = install_skill(target=target)
    assert result["installed"] is True and result["replaced_existing"] is False
    copied = sorted(
        path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()
    )
    assert copied == sorted(skill_files())
    root = skill_root()
    for item in result["files"]:
        assert (target / item["path"]).read_bytes() == (root / item["path"]).read_bytes()
    assert _entries(target.parent) == {"asme"}


def test_install_refuses_existing_target_without_force(tmp_path: Path) -> None:
    target = tmp_path / "asme"
    target.mkdir()
    (target / "SKILL.md").write_text("stale", encoding="utf-8")
    with pytest.raises(ContractError, match="--force"):
        install_skill(target=target)
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "stale"
    assert _entries(tmp_path) == {"asme"}


def test_force_replaces_an_existing_skill_directory(tmp_path: Path) -> None:
    target = tmp_path / "asme"
    target.mkdir()
    (target / "SKILL.md").write_text("stale", encoding="utf-8")
    (target / "leftover.md").write_text("old", encoding="utf-8")
    result = install_skill(target=target, force=True)
    assert result["replaced_existing"] is True
    assert not (target / "leftover.md").exists()
    assert (target / "SKILL.md").read_bytes() == (skill_root() / "SKILL.md").read_bytes()
    assert _entries(tmp_path) == {"asme"}


def test_force_refuses_a_target_that_is_not_a_skill_directory(tmp_path: Path) -> None:
    target = tmp_path / "not-a-skill"
    target.mkdir()
    (target / "keep.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(ContractError, match="SKILL.md"):
        install_skill(target=target, force=True)
    assert (target / "keep.txt").exists()


def test_install_refuses_symlink_target_and_source_overlap(tmp_path: Path) -> None:
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "elsewhere")
    with pytest.raises(ContractError, match="symlink"):
        install_skill(target=link, dry_run=True)
    source = _copy_source(tmp_path / "checkout")
    with pytest.raises(ContractError, match="overlap"):
        install_skill(target=source / "nested", source=source, dry_run=True)


@pytest.mark.parametrize("component", ["staging", "archives"])
def test_install_refuses_any_source_under_a_staging_or_archive_root(
    tmp_path: Path, component: str
) -> None:
    source = _copy_source(tmp_path / "domain" / component / "asme__deadbeef0000")
    target = tmp_path / "skills" / "asme"
    with pytest.raises(ContractError, match="staging and archive"):
        install_skill(target=target, source=source, dry_run=True)
    with pytest.raises(ContractError, match="staging and archive"):
        install_skill(target=target, source=source)
    assert not target.exists()


def test_install_refuses_a_staged_bundle_or_foreign_skill(tmp_path: Path) -> None:
    bundle = _copy_source(tmp_path / "bundle")
    (bundle / "bundle-manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ContractError, match="staged bundle"):
        install_skill(target=tmp_path / "out", source=bundle, dry_run=True)
    foreign = _copy_source(tmp_path / "foreign")
    skill = foreign / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8").replace("name: asme", "name: candidate", 1),
        encoding="utf-8",
    )
    with pytest.raises(ContractError, match="only Agent Skill Mastery Engine's own SKILL.md"):
        install_skill(target=tmp_path / "out", source=foreign, dry_run=True)
    archive = tmp_path / "candidate.skill"
    archive.write_bytes(b"PK")
    with pytest.raises(ContractError, match="never installed"):
        install_skill(target=tmp_path / "out", source=archive, dry_run=True)
    assert not (tmp_path / "out").exists()


def test_cli_install_verb_emits_json_and_refuses_staging_sources(
    tmp_path: Path, capsys
) -> None:
    target = tmp_path / "skills" / "asme"
    assert main(["install", "--target", str(target), "--dry-run"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["schema"] == "asme.skill-install.v1"
    assert result["installed"] is False and not target.exists()

    assert main(["install", "--target", str(target)]) == 0
    assert json.loads(capsys.readouterr().out)["installed"] is True
    assert (target / "SKILL.md").is_file()

    assert main(["install", "--target", str(target)]) == 2
    assert "--force" in capsys.readouterr().err

    staged = _copy_source(tmp_path / "domain" / "staging" / "asme__deadbeef0000")
    assert main(
        ["install", "--target", str(target), "--source", str(staged), "--force"]
    ) == 2
    assert "staging and archive" in capsys.readouterr().err
    assert (target / "SKILL.md").read_bytes() == (skill_root() / "SKILL.md").read_bytes()


def test_install_script_matches_the_cli_verb_and_dry_run_writes_nothing(
    tmp_path: Path,
) -> None:
    target = tmp_path / "skills" / "asme"
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"}
    script = _REPO_ROOT / "scripts" / "install_claude_skill.py"
    dry = subprocess.run(
        [sys.executable, str(script), "--target", str(target), "--dry-run"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert dry.returncode == 0, dry.stderr
    assert json.loads(dry.stdout)["installed"] is False
    assert not (tmp_path / "skills").exists()
    real = subprocess.run(
        [sys.executable, str(script), "--target", str(target)],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert real.returncode == 0, real.stderr
    assert json.loads(real.stdout)["file_count"] == len(skill_files())
    assert (target / "references" / "fidelity.md").is_file()
    refused = subprocess.run(
        [sys.executable, str(script), "--target", str(target)],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert refused.returncode == 2 and "--force" in refused.stderr
