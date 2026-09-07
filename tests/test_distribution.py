"""Public project distributions have an explicit boundary; candidate scans do not."""

from __future__ import annotations

import base64
import csv
import hashlib
import importlib.util
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import zipfile

import pytest

from asme.canonical import ContractError
from asme.package import scan_community_safety

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = b"/" + b"Users" + b"/distribution-canary/work"


@pytest.fixture(scope="module")
def distribution():
    spec = importlib.util.spec_from_file_location(
        "verify_distribution", ROOT / "scripts/verify_distribution.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "source"
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(
        ".git", ".gsd", ".planning", "build", "dist", ".venv", "__pycache__",
        ".pytest_cache", "*.egg-info"
    ))
    return root


def test_distribution_complete_independent_families(distribution):
    files = distribution.source_distribution_files(ROOT)
    for family in ("src/asme", "assets", "adapters", "scripts", "tests", "references", "locked"):
        required = {p.relative_to(ROOT).as_posix() for p in (ROOT / family).rglob("*")
                    if p.is_file() and "__pycache__" not in p.parts}
        assert required <= files.keys()
    expected_eval = {f"assets/eval/{domain}/{member}"
                    for domain in ("arithmetic", "echo")
                    for member in ("answers.jsonl", "cartridge.json", "prompt.txt", "tasks.jsonl",
                                   "rollouts/run-1/baseline.jsonl",
                                   "rollouts/run-1/confirmation.jsonl",
                                   "rollouts/run-1/validation.jsonl")}
    assert len(expected_eval) == 14
    for name in expected_eval | {"LICENSE", "CITATION.cff", "NOTICE.md", "README.md",
                                "docs/evidence/asme-github-timeline.json",
                                "docs/migration/asme-source-manifest.json"}:
        assert files[name] == (ROOT / name).read_bytes()
    scan_community_safety(files)


@pytest.mark.parametrize("name", [
    ".planning/private.md", "docs/research/wikiskill-code-parity.md",
    "docs/evidence/wikiskill-parity-audit.json",
])
def test_distribution_exact_internal_records_preserved(distribution, tree, name):
    target = tree / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(PRIVATE)
    assert name not in distribution.source_distribution_files(tree)
    assert target.read_bytes() == PRIVATE
    with pytest.raises(ContractError, match="private absolute"):
        scan_community_safety({name: target.read_bytes()})


@pytest.mark.parametrize("name", ["src/asme/cli.py", "docs/evidence/ordinary.md",
                                  "docs/research/ordinary.md"])
def test_distribution_private_public_content_fails(distribution, tree, name):
    target = tree / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(PRIVATE)
    if name not in (tree / "MANIFEST.in").read_text():
        with (tree / "MANIFEST.in").open("a") as stream:
            stream.write(f"include {name}\n")
    with pytest.raises(ContractError, match="private absolute"):
        distribution.source_distribution_files(tree)
    with pytest.raises(ContractError, match="private absolute"):
        scan_community_safety({name: PRIVATE})


@pytest.mark.parametrize("mutation", ["omission", "missing", "unknown", "duplicate",
                                     "wildcard", "escape", "internal-runtime", "unclassified"])
def test_distribution_manifest_refusals(distribution, tree, mutation):
    manifest = tree / "MANIFEST.in"
    value = manifest.read_text()
    if mutation == "omission":
        value = value.replace("include assets/eval/echo/tasks.jsonl\n", "")
    elif mutation == "missing":
        value += "include docs/missing.md\n"
    elif mutation == "unknown":
        value += "graft docs\n"
    elif mutation == "duplicate":
        value += "include LICENSE\n"
    elif mutation == "wildcard":
        value += "include docs/*.md\n"
    elif mutation == "escape":
        value += "include ../escape\n"
    elif mutation == "internal-runtime":
        value += "exclude src/asme/cli.py\n"
    else:
        (tree / "unclassified.txt").write_text("unknown source")
    manifest.write_text(value)
    with pytest.raises(ContractError):
        distribution.source_distribution_files(tree)


@pytest.mark.parametrize("kind", ["file", "parent", "hardlink", "special"])
def test_distribution_nonregular_source_fails(distribution, tree, kind):
    import os
    target = tree / "assets/eval/echo/tasks.jsonl"
    if kind == "parent":
        original = tree / "assets/eval/echo"
        moved = tree / "assets/eval/moved"
        original.rename(moved)
        original.symlink_to(moved, target_is_directory=True)
    else:
        target.unlink()
        if kind == "file":
            target.symlink_to(tree / "LICENSE")
        elif kind == "hardlink":
            os.link(tree / "LICENSE", target)
        else:
            os.mkfifo(target)
    with pytest.raises(ContractError):
        distribution.source_distribution_files(tree)


def test_distribution_archival_context_and_draft(distribution, tree):
    archived = "docs/migration/asme-source/README.md"
    draft = "docs/public/2026-09-06-from-wikiskill-to-lifecycle.md"
    if not (tree / draft).exists():
        (tree / draft).parent.mkdir(parents=True, exist_ok=True)
        (tree / draft).write_text("# Internal fixture\n[Planning](../../.planning/PROJECT.md)\n")
    before = {name: (tree / name).read_bytes() for name in (archived, draft)}
    files = distribution.source_distribution_files(tree)
    assert files[archived] == before[archived]
    assert draft not in files and (tree / draft).read_bytes() == before[draft]
    assert "#install-for-claude-code" in files[archived].decode()
    assert "docs/migration/asme-source/NOTICE.md" not in files
    assert "NOTICE.md" in files and "references/integration.md" in files
    manifest = tree / "MANIFEST.in"
    manifest.write_text(manifest.read_text().replace("include NOTICE.md\n", ""))
    with pytest.raises(ContractError):
        distribution.source_distribution_files(tree)


def test_distribution_missing_document_dependency_fails(distribution, tree):
    with (tree / "README.md").open("a") as stream:
        stream.write("\n[Required data](docs/absent.json)\n")
    with pytest.raises(ContractError, match="link|dependency"):
        distribution.source_distribution_files(tree)


def test_distribution_no_git_or_internal_state_required(distribution, tree):
    assert not (tree / ".git").exists() and not (tree / ".planning").exists()
    assert distribution.source_distribution_files(tree)


def test_distribution_rejects_foreign_preloaded_asme():
    script = ("import runpy,sys,types; m=types.ModuleType('asme'); "
              "m.__file__='foreign/asme/__init__.py'; sys.modules['asme']=m; "
              "runpy.run_path(sys.argv[1])")
    result = subprocess.run([sys.executable, "-c", script,
                             str(ROOT / "scripts/verify_distribution.py")],
                            capture_output=True, text=True, check=False)
    assert result.returncode != 0 and "foreign" in result.stderr


def _sdist(distribution, tree, path, mutation=None, *, root="agent_skill_mastery_engine-0.2.0"):
    files = distribution.source_distribution_files(tree)
    generated = distribution.sdist_metadata(tree, files)
    members = {**files, **generated}
    if mutation == "missing":
        members.pop("assets/eval/echo/tasks.jsonl")
    if mutation == "extra":
        members["unknown.txt"] = b"extra"
    if mutation == "changed":
        members["src/asme/cli.py"] += b"# changed\n"
    if mutation == "metadata":
        members["PKG-INFO"] = b"Name: impostor\n"
    prefix = root + "/"
    with tarfile.open(path, "w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(prefix + name)
            info.size = len(data)
            info.mode = (tree / name).stat().st_mode & 0o777 if name in files else 0o644
            archive.addfile(info, io.BytesIO(data))
        if mutation in {"duplicate", "escape", "absolute", "normalized", "symlink",
                        "hardlink", "special"}:
            name = {"duplicate": prefix + "LICENSE", "escape": "other/LICENSE",
                    "absolute": "/unsafe", "normalized": prefix + "docs//extra"}.get(
                        mutation, prefix + "link")
            info = tarfile.TarInfo(name)
            if mutation in {"symlink", "hardlink", "special"}:
                info.type = {"symlink": tarfile.SYMTYPE, "hardlink": tarfile.LNKTYPE,
                             "special": tarfile.FIFOTYPE}[mutation]
                info.linkname = "LICENSE"
            archive.addfile(info, io.BytesIO())


@pytest.mark.parametrize("mutation", ["missing", "extra", "changed", "metadata", "duplicate",
                                     "escape", "absolute", "normalized", "symlink", "hardlink",
                                     "special"])
def test_distribution_sdist_adversarial(distribution, tree, tmp_path, mutation):
    path = tmp_path / "candidate.tar.gz"
    _sdist(distribution, tree, path, mutation)
    with pytest.raises(ContractError):
        distribution.verify_sdist(path, source_root=tree)


@pytest.mark.parametrize("root", ["agent_skill_mastery_engine-0.2.0",
                                 "agent-skill-mastery-engine-0.2.0"],
                         ids=["normalized", "declared"])
def test_distribution_sdist_declared_root_fixture(distribution, tree, tmp_path, root):
    """Complete root-spelling fixtures, not builds executed with a legacy backend."""
    path = tmp_path / "candidate.tar.gz"
    _sdist(distribution, tree, path, root=root)
    receipt = distribution.verify_sdist(path, source_root=tree)
    assert receipt["status"] == "pass"
    with tarfile.open(path) as archive:
        assert {item.name.split("/", 1)[0] for item in archive.getmembers()} == {root}
        for item in archive.getmembers():
            name = item.name.removeprefix(root + "/")
            source = tree / name
            if source.is_file():
                assert archive.extractfile(item).read() == source.read_bytes()
                assert receipt["member_modes"][item.name] == oct(source.stat().st_mode & 0o777)


@pytest.mark.parametrize("root", [
    "impostor-0.2.0", "agent_skill_mastery_engine-9.9.9",
    "agent.skill.mastery.engine-0.2.0", "../agent_skill_mastery_engine-0.2.0",
    "/agent_skill_mastery_engine-0.2.0", "agent_skill_mastery_engine-0.2.0/..",
    "agent_skill_mastery_engine-0.2.0/", "",
], ids=["wrong-name", "wrong-version", "other-normalization", "traversal-root",
        "absolute-root", "traversal-member", "malformed-member", "empty-root"])
def test_distribution_sdist_invalid_root_fixture(distribution, tree, tmp_path, root):
    path = tmp_path / "agent_skill_mastery_engine-0.2.0.tar.gz"
    _sdist(distribution, tree, path, root=root)
    with pytest.raises(ContractError):
        distribution.verify_sdist(path, source_root=tree)


@pytest.mark.parametrize("root, other", [
    ("agent_skill_mastery_engine-0.2.0", "agent-skill-mastery-engine-0.2.0"),
    ("agent-skill-mastery-engine-0.2.0", "agent_skill_mastery_engine-0.2.0"),
], ids=["normalized-first", "declared-first"])
@pytest.mark.parametrize("mutation", ["mixed-file", "mixed-directory", "root-file"])
def test_distribution_sdist_root_consistency(distribution, tree, tmp_path, root, other,
                                           mutation):
    original, changed = tmp_path / "original.tar.gz", tmp_path / "changed.tar.gz"
    _sdist(distribution, tree, original, root=root)
    with tarfile.open(original) as source, tarfile.open(changed, "w:gz") as output:
        for item in source.getmembers():
            data = source.extractfile(item).read()
            if mutation == "mixed-file" and item.name == root + "/LICENSE":
                item.name = other + "/LICENSE"
            output.addfile(item, io.BytesIO(data))
        if mutation != "mixed-file":
            item = tarfile.TarInfo(other if mutation == "mixed-directory" else root)
            item.type = tarfile.DIRTYPE if mutation == "mixed-directory" else tarfile.REGTYPE
            item.mode = 0o755 if mutation == "mixed-directory" else 0o644
            output.addfile(item, io.BytesIO())
    with pytest.raises(ContractError):
        distribution.verify_sdist(changed, source_root=tree)


def test_distribution_sdist_empty_archive(distribution, tree, tmp_path):
    path = tmp_path / "empty.tar.gz"
    with tarfile.open(path, "w:gz"):
        pass
    with pytest.raises(ContractError):
        distribution.verify_sdist(path, source_root=tree)


def _wheel(distribution, tree, path, mutation=None):
    files = distribution.wheel_payload(tree)
    metadata = distribution.wheel_metadata(tree)
    files.update(metadata)
    record = "agent_skill_mastery_engine-0.2.0.dist-info/RECORD"
    if mutation == "missing":
        files.pop("asme/cli.py")
    elif mutation == "extra":
        files["unknown.txt"] = b"extra"
    elif mutation == "changed":
        files["asme/cli.py"] += b"# changed\n"
    elif mutation == "metadata":
        files["agent_skill_mastery_engine-0.2.0.dist-info/METADATA"] = b"Name: impostor\n"
    elif mutation == "legacy":
        prefix = "agent_skill_mastery_engine-0.2.0.dist-info/"
        files[prefix + "METADATA"] = files[prefix + "METADATA"].replace(
            b"Metadata-Version: 2.4\n", b"Metadata-Version: 2.1\n").replace(
            b"Dynamic: license-file\n", b"")
        files[prefix + "WHEEL"] = files[prefix + "WHEEL"].replace(
            b"setuptools (84.0.0)", b"bdist_wheel (0.41.0)")
        for license_name in ("LICENSE", "NOTICE.md"):
            files[prefix + license_name] = files.pop(prefix + "licenses/" + license_name)
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    for name, data in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        writer.writerow([name, "sha256=" + digest, str(len(data))])
    writer.writerow([record, "", ""])
    files[record] = stream.getvalue().encode()
    if mutation == "record":
        files[record] = b"asme/cli.py,,\n"
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            info = zipfile.ZipInfo(name)
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
        if mutation in {"duplicate", "escape", "normalized", "symlink", "special"}:
            name = {"duplicate": "asme/cli.py", "escape": "../unsafe",
                    "normalized": "asme//extra"}.get(mutation, "asme/link")
            info = zipfile.ZipInfo(name)
            mode = {"symlink": 0o120777, "special": 0o010644}.get(mutation, 0o100644)
            info.external_attr = mode << 16
            archive.writestr(info, b"target")


@pytest.mark.parametrize("mutation", ["missing", "extra", "changed", "metadata", "record",
                                     "duplicate", "escape", "normalized", "symlink", "special"])
def test_distribution_wheel_adversarial(distribution, tree, tmp_path, mutation):
    path = tmp_path / "candidate.whl"
    _wheel(distribution, tree, path, mutation)
    with pytest.raises(ContractError):
        distribution.verify_wheel(path, source_root=tree)


def test_distribution_archive_positive_independent_payload(distribution, tree, tmp_path):
    sdist, wheel = tmp_path / "source.tar.gz", tmp_path / "package.whl"
    _sdist(distribution, tree, sdist)
    _wheel(distribution, tree, wheel)
    assert distribution.verify_sdist(sdist, source_root=tree)["status"] == "pass"
    assert distribution.verify_wheel(wheel, source_root=tree)["status"] == "pass"
    with zipfile.ZipFile(wheel) as archive:
        for source in (tree / "src/asme").rglob("*"):
            if source.is_file() and "__pycache__" not in source.parts:
                name = source.relative_to(tree / "src").as_posix()
                assert archive.read(name) == source.read_bytes()
        expected_skill = {"SKILL.md", "PURPOSE.md", "NOTICE.md", "LICENSE"} | {
            path.relative_to(tree).as_posix() for path in (tree / "references").rglob("*")
            if path.is_file()}
        assert {n.removeprefix("asme/skill/") for n in archive.namelist()
                if n.startswith("asme/skill/")} == expected_skill


def test_distribution_generated_collision_refused(distribution, tree):
    with (tree / "MANIFEST.in").open("a") as stream:
        stream.write("include PKG-INFO\n")
    (tree / "PKG-INFO").write_text("collision")
    with pytest.raises(ContractError):
        distribution.source_distribution_files(tree)


def test_distribution_deleted_imported_file_and_declaration_refused(distribution, tree):
    member = "assets/eval/echo/tasks.jsonl"
    (tree / member).unlink()
    manifest = tree / "MANIFEST.in"
    manifest.write_text(manifest.read_text().replace(f"include {member}\n", ""))
    with pytest.raises(ContractError, match="imported"):
        distribution.source_distribution_files(tree)


def test_distribution_backend_literal_list_and_generated_inputs(distribution, tree):
    files = distribution.source_distribution_files(tree)
    generated = distribution.sdist_metadata(tree, files)
    for name, content in generated.items():
        target = tree / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    egg = "src/agent_skill_mastery_engine.egg-info/"
    backend = sorted(set(files) | {egg + "SOURCES.txt"})
    selected = distribution.backend_sdist_inputs(tree, backend, files)
    assert set(selected) == set(files) | {egg + name for name in (
        "PKG-INFO", "SOURCES.txt", "dependency_links.txt", "entry_points.txt", "top_level.txt")}
    with pytest.raises(ContractError):
        distribution.backend_sdist_inputs(tree, backend + ["unknown.txt"], files)
    (tree / egg / "entry_points.txt").write_text("[console_scripts]\nevil = evil:main\n")
    with pytest.raises(ContractError):
        distribution.backend_sdist_inputs(tree, backend, files)


@pytest.mark.parametrize("mutation", ["pax-comment", "global-pax", "late-global-pax", "owner",
                                     "directory-mode", "file-mode"])
def test_distribution_tar_transport_metadata(distribution, tree, tmp_path, mutation):
    original, changed = tmp_path / "original.tar.gz", tmp_path / "changed.tar.gz"
    _sdist(distribution, tree, original)
    with tarfile.open(original) as source:
        members = [(item, source.extractfile(item).read()) for item in source.getmembers()]
    kwargs = {"pax_headers": {"comment": PRIVATE.decode()}} if mutation == "global-pax" else {}
    with tarfile.open(changed, "w:gz", **kwargs) as output:
        directory = tarfile.TarInfo("agent_skill_mastery_engine-0.2.0")
        directory.type = tarfile.DIRTYPE
        directory.mode = 0o2755 if mutation == "directory-mode" else 0o755
        output.addfile(directory)
        if mutation == "late-global-pax":
            header = tarfile.TarInfo.create_pax_global_header({"mtime": PRIVATE.decode()})
            output.fileobj.write(header)
            output.offset += len(header)
        for item, data in members:
            if mutation == "late-global-pax":
                item.pax_headers["mtime"] = "0"
            if item.name.endswith("/src/asme/cli.py"):
                if mutation == "pax-comment":
                    item.pax_headers["comment"] = PRIVATE.decode()
                elif mutation == "owner":
                    item.uname = PRIVATE.decode()
                elif mutation == "file-mode":
                    item.mode = 0o755
            output.addfile(item, io.BytesIO(data))
    expected = {"pax-comment": "tar PAX", "global-pax": "global tar PAX",
                "late-global-pax": "global tar PAX", "owner": "private absolute",
                "directory-mode": "privileged mode", "file-mode": "source policy"}
    with pytest.raises(ContractError, match=expected[mutation]):
        distribution.verify_sdist(changed, source_root=tree)


@pytest.mark.parametrize("mutation", ["archive-comment", "member-comment", "extra", "file-mode"])
def test_distribution_zip_transport_metadata(distribution, tree, tmp_path, mutation):
    import struct
    original, changed = tmp_path / "original.whl", tmp_path / "changed.whl"
    _wheel(distribution, tree, original)
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(changed, "w") as output:
        if mutation == "archive-comment":
            output.comment = PRIVATE
        for item in source.infolist():
            data = source.read(item)
            if item.filename == "asme/cli.py":
                if mutation == "member-comment":
                    item.comment = PRIVATE
                elif mutation == "extra":
                    item.extra = struct.pack("<HH", 0xCAFE, len(PRIVATE)) + PRIVATE
                elif mutation == "file-mode":
                    item.external_attr = 0o100755 << 16
            output.writestr(item, data)
    expected = {"archive-comment": "archive comments", "member-comment": "transport metadata",
                "extra": "transport metadata", "file-mode": "source policy"}
    with pytest.raises(ContractError, match=expected[mutation]):
        distribution.verify_wheel(changed, source_root=tree)


@pytest.mark.parametrize("member", ["PKG-INFO", "setup.cfg",
    "src/agent_skill_mastery_engine.egg-info/PKG-INFO",
    "src/agent_skill_mastery_engine.egg-info/SOURCES.txt",
    "src/agent_skill_mastery_engine.egg-info/entry_points.txt"])
def test_distribution_reserved_generated_source(distribution, tree, member):
    files = distribution.source_distribution_files(tree)
    for name, data in distribution.sdist_metadata(tree, files).items():
        target = tree / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    assert distribution.source_distribution_files(tree)
    (tree / member).write_bytes(PRIVATE)
    with pytest.raises(ContractError):
        distribution.source_distribution_files(tree)


def test_distribution_legacy_metadata_identity(distribution, tree):
    modern = distribution._metadata(tree)
    legacy = modern.replace(b"Metadata-Version: 2.4\n", b"Metadata-Version: 2.1\n").replace(
        b"Dynamic: license-file\n", b"")
    distribution._metadata_equal(legacy, modern, "PKG-INFO")
    for changed in (legacy.replace(b"Version: 0.2.0", b"Version: 9.9.9"),
                    legacy.replace(b"\n\n", b"\nUnknown: ignored\n\n", 1),
                    legacy.replace(b"Metadata-Version: 2.1", b"Metadata-Version: 9.9")):
        with pytest.raises(ContractError):
            distribution._metadata_equal(changed, modern, "PKG-INFO")


def test_distribution_absent_internal_draft(distribution, tree):
    draft = tree / "docs/public/2026-09-06-from-wikiskill-to-lifecycle.md"
    if draft.exists():
        draft.unlink()
    test_distribution_archival_context_and_draft(distribution, tree)


def test_distribution_legacy_wheel_metadata_layout(distribution, tree, tmp_path):
    archive = tmp_path / "legacy.whl"
    _wheel(distribution, tree, archive, "legacy")
    assert distribution.verify_wheel(archive, source_root=tree)["status"] == "pass"
