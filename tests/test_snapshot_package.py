from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import zipfile

import pytest

from asme.canonical import ContractError
from asme.package import (
    Compatibility,
    build_archive,
    build_projection,
    build_projection_from_files,
    ensure_staging_destination,
    read_bundle_manifest,
    scan_community_safety,
    validate_existing_projection,
    verify_archive,
)
from asme.snapshot import Snapshot, active_snapshot, verify_snapshot


def _compatibility() -> Compatibility:
    return Compatibility(
        contract_version="asme.contract.v1",
        core_version="0.1.0",
        package_version="0.1.0",
        adapter_id="hermes",
        adapter_version="0.1.0",
        runtime_min_tested="0.20.5",
        runtime_max_tested="0.20.6",
        runtime_tested=("0.20.5", "0.20.6"),
    )


def _projection(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
    (source / "README.md").write_text("staged candidate, not installed\n", encoding="utf-8")
    debris = source / "__pycache__"
    debris.mkdir()
    (debris / "noise.pyc").write_bytes(b"noise")
    return build_projection(
        source_root=source,
        compatibility=_compatibility(),
        source_attribution=(
            {
                "title": "WikiSkill",
                "arxiv_id": "2608.27454v1",
                "license": "CC BY 4.0",
                "adaptation": "independent implementation",
            },
        ),
    )


def test_snapshot_hash_uses_length_framed_paths_and_exact_bytes(tmp_path: Path) -> None:
    source = tmp_path / "framed-source"
    source.mkdir()
    (source / "a.txt").write_bytes(b"alpha")
    (source / "nested").mkdir()
    (source / "nested/b.txt").write_bytes(b"beta\x00gamma")
    snapshot = Snapshot.from_directory(source)

    expected = hashlib.sha256()
    for name, content in (
        (b"a.txt", b"alpha"),
        (b"nested/b.txt", b"beta\x00gamma"),
    ):
        expected.update(len(name).to_bytes(8, "big"))
        expected.update(name)
        expected.update(len(content).to_bytes(8, "big"))
        expected.update(content)
    assert snapshot.snapshot_hash == expected.hexdigest()


def test_hf_a12_snapshot_pointer_and_immutable_hash(tmp_path: Path) -> None:
    source = tmp_path / "skill"
    source.mkdir()
    (source / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
    snapshot = Snapshot.from_directory(source)
    store = tmp_path / "snapshots" / snapshot.snapshot_hash
    store.mkdir(parents=True)
    (store / "SKILL.md").write_bytes(snapshot.files[0].content)
    verify_snapshot(tmp_path / "snapshots", snapshot)
    assert active_snapshot(
        {"active_snapshot_hash": snapshot.snapshot_hash},
        {snapshot.snapshot_hash: snapshot},
    ) is snapshot
    (store / "SKILL.md").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ContractError, match="changed"):
        verify_snapshot(tmp_path / "snapshots", snapshot)


def test_hf_a17_candidate_marker_scan_is_literal_and_limited(tmp_path: Path) -> None:
    source = tmp_path / "skill"
    source.mkdir()
    marker = "propagation-marker"
    (source / "SKILL.md").write_text(f"contains {marker}\n", encoding="utf-8")
    with pytest.raises(ContractError, match="marker propagated"):
        Snapshot.from_directory(source, forbidden_markers=(marker,))
    (source / "SKILL.md").write_text("same idea without the literal token\n", encoding="utf-8")
    assert Snapshot.from_directory(source, forbidden_markers=(marker,)).files


def test_hf_a20_projection_archive_path_byte_equality_and_tamper_detection(tmp_path: Path) -> None:
    projection = _projection(tmp_path)
    assert projection.swept_build_artifacts == ("__pycache__/noise.pyc",)
    manifest = read_bundle_manifest(projection)
    assert manifest["manifest_self_hash"] == "external_tree_hash"
    archive = build_archive(
        projection, recorded_at=datetime(2026, 8, 31, tzinfo=timezone.utc)
    )
    verified = verify_archive(archive, expected=projection)
    assert verified.tree_sha256 == projection.tree_sha256
    with zipfile.ZipFile(io.BytesIO(archive), "r") as original:
        contents = {name: original.read(name) for name in original.namelist()}
    contents["SKILL.md"] = b"tampered\n"
    mutated = _zip_bytes(contents)
    with pytest.raises(ContractError, match="differ"):
        verify_archive(mutated, expected=projection)


def test_projection_from_memory_matches_canonical_source_tree(tmp_path: Path) -> None:
    source = tmp_path / "source-map"
    source.mkdir()
    files = {
        "SKILL.md": b"# Skill\n",
        "README.md": b"test_evaluation: passed\n",
        "PURPOSE.md": b"test_evaluation: passed\n",
    }
    for name, content in files.items():
        (source / name).write_bytes(content)
    kwargs = {
        "compatibility": _compatibility(),
        "source_attribution": ({"title": "WikiSkill", "license": "CC BY 4.0"},),
    }
    from_tree = build_projection(source_root=source, **kwargs)
    from_memory = build_projection_from_files(files=files, **kwargs)
    assert from_memory.content_map() == from_tree.content_map()
    assert from_memory.tree_sha256 == from_tree.tree_sha256


@pytest.mark.parametrize("unsafe", ("/absolute", "back\\slash", "../escape", "dot/../escape"))
def test_hf_a20_archive_rejects_unsafe_members(unsafe: str) -> None:
    with pytest.raises(ContractError):
        verify_archive(_zip_bytes({unsafe: b"x"}))


def test_archive_rejects_directory_and_symlink_members() -> None:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        directory = zipfile.ZipInfo("folder/")
        directory.external_attr = 0o40755 << 16
        archive.writestr(directory, b"")
    with pytest.raises(ContractError):
        verify_archive(output.getvalue())


def test_archive_rejects_duplicate_extra_and_missing_members(tmp_path: Path) -> None:
    output = io.BytesIO()
    with pytest.warns(UserWarning):
        with zipfile.ZipFile(output, "w") as archive:
            for content in (b"one", b"two"):
                info = zipfile.ZipInfo("same.txt")
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                archive.writestr(info, content)
    with pytest.raises(ContractError, match="duplicate"):
        verify_archive(output.getvalue())
    projection = _projection(tmp_path)
    extra = projection.content_map()
    extra["extra.txt"] = b"extra"
    with pytest.raises(ContractError, match="differ"):
        verify_archive(_zip_bytes(extra), expected=projection)
    missing = projection.content_map()
    missing.pop("SKILL.md")
    with pytest.raises(ContractError, match="differ"):
        verify_archive(_zip_bytes(missing), expected=projection)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        link = zipfile.ZipInfo("link")
        link.create_system = 3
        link.external_attr = 0o120777 << 16
        archive.writestr(link, b"target")
    with pytest.raises(ContractError):
        verify_archive(output.getvalue())


def test_existing_projection_requires_exact_membership(tmp_path: Path) -> None:
    projection = _projection(tmp_path)
    staged = tmp_path / "staged"
    for item in projection.files:
        target = staged / item.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(item.content)
    assert validate_existing_projection(staged, projection)
    (staged / "extra.txt").write_text("extra", encoding="utf-8")
    assert not validate_existing_projection(staged, projection)


def test_community_scan_and_live_root_guard_fail_closed(tmp_path: Path) -> None:
    private_path = b"/" + b"Users" + b"/person/private.txt"
    with pytest.raises(ContractError, match="private absolute path"):
        scan_community_safety({"note.txt": private_path})
    secret = b"sk" + b"-" + b"a" * 24
    with pytest.raises(ContractError, match="credential-like"):
        scan_community_safety({"note.txt": secret})
    stage = tmp_path / "live" / "staging"
    with pytest.raises(ContractError, match="forbidden live root"):
        ensure_staging_destination(
            destination=stage / "candidate",
            staging_root=stage,
            forbidden_live_roots=(tmp_path / "live",),
        )


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content in files.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 8, 31, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return output.getvalue()


def test_local_runtime_state_directories_are_swept_before_the_community_scan(
    tmp_path: Path,
) -> None:
    source = tmp_path / "runtime-source"
    source.mkdir()
    (source / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
    (source / "README.md").write_text("staged candidate, not installed\n", encoding="utf-8")
    for directory, member in (
        (".langgraph_api", ".langgraph_ops.pckl"),
        (".serena", "cache.json"),
    ):
        state = source / directory
        state.mkdir()
        (state / member).write_bytes(b"/" + b"Volumes" + b"/" + b"Asylum" + b"/x\n")
    projection = build_projection(
        source_root=source,
        compatibility=_compatibility(),
        source_attribution=({"title": "WikiSkill", "license": "CC BY 4.0"},),
    )
    assert projection.swept_build_artifacts == (
        ".langgraph_api/.langgraph_ops.pckl",
        ".serena/cache.json",
    )
    assert set(projection.content_map()) & {
        ".langgraph_api/.langgraph_ops.pckl",
        ".serena/cache.json",
    } == set()
