"""Adversarial checks for the lossless port receipt, using a synthetic Git view."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def port(tmp_path, monkeypatch):
    script = Path(__file__).parents[1] / "scripts" / "verify_asme_port.py"
    spec = importlib.util.spec_from_file_location("verify_asme_port", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source, target = tmp_path / "source", tmp_path / "target"
    source.mkdir()
    target.mkdir()
    revision = "1" * 40
    contents = {"runner.py": b"print('ok')\n", "README.md": b"Original docs\n",
                ".planning/codebase/map.md": b"Private planning\n"}
    modes = {name: "100755" if name == "runner.py" else "100644" for name in contents}
    objects = {name: str(index) * 40 for index, name in enumerate(contents, 2)}
    entries = []
    for name, data in contents.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(int(modes[name][-3:], 8))
        retained = name.startswith(".planning/")
        historical = "docs/migration/asme-source/README.md" if name == "README.md" else None
        entry = {"source_path": name, "sha256": hashlib.sha256(data).hexdigest(),
                 "git_mode": modes[name], "destination": None if retained else name,
                 "historical_destination": historical,
                 "disposition": "retained_at_source" if retained else
                 "historical_copy_with_current_document" if historical else "copied_exact"}
        if historical:
            current = b"# Current docs\n[Original](docs/migration/asme-source/README.md)\n"
            entry["current_sha256"] = hashlib.sha256(current).hexdigest()
        for destination in ([name, historical] if historical else [] if retained else [name]):
            out = target / destination
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(current if historical and destination == name else data)
            out.chmod(int(modes[name][-3:], 8))
        entries.append(entry)
    manifest = {"schema": "lifecycle.asme-port.v1", "source_revision": revision,
                "entries": entries}
    def git(repo, *args):
        assert repo == source
        if args == ("rev-parse", "HEAD"):
            return (revision + "\n").encode()
        if args == ("rev-parse", "--show-toplevel"):
            return (str(source) + "\n").encode()
        if args in (("ls-tree", "-rz", revision), ("ls-tree", "--full-tree", "-rz", revision)):
            return b"".join(f"{modes[name]} blob {objects[name]}\t{name}\0".encode()
                            for name in contents)
        if args == ("ls-files", "--stage", "-z"):
            return b"".join(f"{modes[name]} {objects[name]} 0\t{name}\0".encode()
                            for name in contents)
        if args[:2] == ("cat-file", "blob"):
            return next(data for name, data in contents.items() if objects[name] == args[2])
        raise AssertionError(args)
    monkeypatch.setattr(module, "git", git)
    return module, source, target, revision, manifest


def verify(port):
    module, source, target, revision, manifest = port
    return module.verify(source, target, revision, manifest)


def test_complete_mapping_and_historical_document_pass(port):
    result = verify(port)
    assert result["status"] == "pass"
    assert result["tracked_paths"] == 3
    assert result["retained_at_source"] == 1
    assert len(result["destination_content_digest"]) == 64


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "extra", "revision", "hash", "mode"])
def test_rejects_invalid_receipt(port, mutation):
    module, _, _, _, manifest = port
    if mutation == "missing":
        manifest["entries"].pop()
    elif mutation == "duplicate":
        manifest["entries"].append(dict(manifest["entries"][0]))
    elif mutation == "extra":
        manifest["entries"].append({**manifest["entries"][0], "source_path": "unknown.py"})
    elif mutation == "revision":
        manifest["source_revision"] = "9" * 40
    elif mutation == "hash":
        manifest["entries"][0]["sha256"] = "0" * 64
    else:
        manifest["entries"][0]["git_mode"] = "100644"
    with pytest.raises(module.VerificationError):
        verify(port)


@pytest.mark.parametrize("name", ["runner.py", "docs/migration/asme-source/README.md", "README.md"])
def test_rejects_changed_or_missing_destination(port, name):
    module, _, target, _, _ = port
    (target / name).write_bytes(b"tampered\n")
    with pytest.raises(module.VerificationError):
        verify(port)
    (target / name).unlink()
    with pytest.raises(module.VerificationError):
        verify(port)


def test_rejects_executable_mode_change(port):
    module, _, target, _, _ = port
    (target / "runner.py").chmod(0o644)
    with pytest.raises(module.VerificationError):
        verify(port)


@pytest.mark.parametrize("destination", ["../escape", "/tmp/escape", "docs/../../escape", "docs//file"])
def test_rejects_unsafe_destinations(port, destination):
    module, _, _, _, manifest = port
    manifest["entries"][0]["destination"] = destination
    with pytest.raises(module.VerificationError):
        verify(port)


def test_rejects_symlink_file_even_when_it_points_to_identical_content(port):
    module, source, target, _, _ = port
    (target / "runner.py").unlink()
    (target / "runner.py").symlink_to(source / "runner.py")
    with pytest.raises(module.VerificationError):
        verify(port)


def test_rejects_symlink_parent(port):
    module, source, target, _, manifest = port
    (target / "linked").symlink_to(source, target_is_directory=True)
    manifest["entries"][0]["destination"] = "linked/runner.py"
    with pytest.raises(module.VerificationError):
        verify(port)
    with pytest.raises(module.VerificationError):
        module.contained_file(target, "linked/runner.py")


def test_rejects_source_symlink(port):
    module, source, target, _, _ = port
    (source / "runner.py").unlink()
    (source / "runner.py").symlink_to(target / "runner.py")
    with pytest.raises(module.VerificationError):
        verify(port)


@pytest.mark.parametrize("relative", ["../source/runner.py", "/tmp/file", "./runner.py", "dir//file"])
def test_containment_rejects_noncanonical_paths_directly(port, relative):
    module, _, target, _, _ = port
    with pytest.raises(module.VerificationError):
        module.contained_file(target, relative)


def test_rejects_modified_retained_source(port):
    module, source, _, _, _ = port
    (source / ".planning/codebase/map.md").write_bytes(b"changed\n")
    with pytest.raises(module.VerificationError):
        verify(port)


def test_rejects_missing_link_to_historical_document(port):
    module, _, target, _, manifest = port
    content = b"Current documentation without its history\n"
    (target / "README.md").write_bytes(content)
    manifest["entries"][1]["current_sha256"] = hashlib.sha256(content).hexdigest()
    with pytest.raises(module.VerificationError):
        verify(port)


def test_rejects_destination_aliases(port):
    module, _, _, _, manifest = port
    manifest["entries"][1]["historical_destination"] = "runner.py"
    with pytest.raises(module.VerificationError):
        verify(port)


def test_rejects_source_head_drift(port, monkeypatch):
    module, _, _, _, _ = port
    original = module.git
    monkeypatch.setattr(module, "git", lambda repo, *args:
                        b"9" * 40 if args == ("rev-parse", "HEAD") else original(repo, *args))
    with pytest.raises(module.VerificationError):
        verify(port)


@pytest.mark.parametrize("tampered", [False, True])
def test_cli_returns_explicit_status_and_failure_exit(port, monkeypatch, capsys, tampered):
    module, source, target, revision, manifest = port
    receipt = target / "docs/migration/asme-source-manifest.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(module, "__file__", str(target / "scripts/verify_asme_port.py"))
    if tampered:
        (target / "runner.py").write_bytes(b"tampered\n")
    code = module.main(["--source", str(source), "--source-revision", revision, "--check"])
    captured = capsys.readouterr()
    assert code == (1 if tampered else 0)
    assert json.loads(captured.err if tampered else captured.out)["status"] == (
        "fail" if tampered else "pass"
    )


def test_rejects_git_subdirectory_with_empty_receipt(port, monkeypatch):
    module, source, target, revision, manifest = port
    nested = source / "empty"
    nested.mkdir()
    original = module.git
    def nested_git(repo, *args):
        if args == ("rev-parse", "--show-toplevel"):
            return str(source).encode()
        if args == ("ls-tree", "-rz", revision):
            return b""
        return original(source, *args)
    monkeypatch.setattr(module, "git", nested_git)
    manifest["entries"] = []
    with pytest.raises(module.VerificationError):
        module.verify(nested, target, revision, manifest)


def test_planning_retention_cannot_be_overridden_by_receipt(port):
    module, source, target, _, manifest = port
    entry = manifest["entries"][2]
    name = entry["source_path"]
    destination = target / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes((source / name).read_bytes())
    destination.chmod(0o644)
    entry.update(disposition="copied_exact", destination=name)
    with pytest.raises(module.VerificationError):
        verify(port)


@pytest.mark.parametrize("mutation", ["blob", "mode", "missing", "extra", "unmerged", "duplicate"])
def test_rejects_source_index_drift_with_unchanged_working_bytes(port, monkeypatch, mutation):
    module, _, _, _, _ = port
    original = module.git
    def changed_index(repo, *args):
        result = original(repo, *args)
        if args != ("ls-files", "--stage", "-z"):
            return result
        rows = result.rstrip(b"\0").split(b"\0")
        if mutation == "blob":
            rows[0] = rows[0].replace(b"2" * 40, b"9" * 40)
        elif mutation == "mode":
            rows[0] = rows[0].replace(b"100755", b"100644")
        elif mutation == "missing":
            rows.pop()
        elif mutation == "extra":
            rows.append(b"100644 " + b"8" * 40 + b" 0\textra.py")
        elif mutation == "unmerged":
            rows[0] = rows[0].replace(b" 0\t", b" 2\t")
        else:
            rows.append(rows[0])
        return b"\0".join(rows) + b"\0"
    monkeypatch.setattr(module, "git", changed_index)
    with pytest.raises(module.VerificationError):
        verify(port)
