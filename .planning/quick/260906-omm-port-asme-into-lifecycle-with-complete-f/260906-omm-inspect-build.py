"""Reproduce the compatibility-port archive inspection; no extraction or dispatch."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import stat
import sys
import tarfile
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    root = args.source.resolve()
    sys.path.insert(0, str(root / "src"))
    from asme.canonical import safe_member_name
    from asme.package import scan_community_safety
    from asme.skill_assets import skill_files

    archives = sorted(args.artifacts.glob("*.whl")) + sorted(args.artifacts.glob("*.tar.gz"))
    assert len(archives) == 2, "one source archive and one wheel required"
    assert sum(path.suffix == ".whl" for path in archives) == 1
    source = {
        path.relative_to(root / "src").as_posix(): path.read_bytes()
        for path in sorted((root / "src/asme").rglob("*"))
        if path.is_file() and path.suffix in {".py", ".json"}
    }
    companions = {"asme/skill/" + name: (root / name).read_bytes() for name in skill_files(root)}
    results = []
    for archive in archives:
        files = {}
        seen = set()
        if archive.suffix == ".whl":
            kind = "wheel"
            with zipfile.ZipFile(archive) as stream:
                for item in stream.infolist():
                    assert item.filename not in seen, "duplicate ZIP member"
                    seen.add(item.filename)
                    safe_member_name(item.filename.rstrip("/"))
                    mode = item.external_attr >> 16
                    assert stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR), "special ZIP member"
                    if not item.is_dir():
                        files[item.filename] = stream.read(item)
            normalized = files
        else:
            kind = "sdist"
            with tarfile.open(archive, "r:gz") as stream:
                for item in stream.getmembers():
                    assert item.name not in seen, "duplicate tar member"
                    seen.add(item.name)
                    safe_member_name(item.name.rstrip("/"))
                    assert item.isdir() or item.isfile(), "special tar member"
                    if item.isfile():
                        reader = stream.extractfile(item)
                        assert reader is not None
                        files[item.name] = reader.read()
            prefixes = {PurePosixPath(name).parts[0] for name in files}
            assert len(prefixes) == 1, "source archive root mismatch"
            normalized = {name.split("/", 1)[1]: data for name, data in files.items()}
        scan_community_safety(files)
        for name, data in source.items():
            target = name if kind == "wheel" else "src/" + name
            assert normalized.get(target) == data, "runtime byte mismatch: " + target
        if kind == "wheel":
            for name, data in companions.items():
                assert normalized.get(name) == data, "skill byte mismatch: " + name
        omitted = []
        if kind == "sdist":
            omitted = [
                path.relative_to(root).as_posix()
                for path in sorted((root / "assets/eval").rglob("*"))
                if path.is_file() and path.relative_to(root).as_posix() not in normalized
            ]
        results.append({
            "kind": kind, "path": archive.as_posix(),
            "sha256": digest(archive.read_bytes()), "bytes": archive.stat().st_size,
            "archive_members": len(seen), "regular_members": len(files),
            "runtime_files_byte_equal": len(source),
            "skill_files_byte_equal": len(companions) if kind == "wheel" else None,
            "community_scan": "passed", "evaluation_assets_omitted": omitted,
            "files": [{"path": name, "bytes": len(data), "sha256": digest(data)}
                      for name, data in sorted(files.items())],
        })
    print(json.dumps({
        "schema": "lifecycle.asme-port-archive-inspection.v1",
        "status": "passed_with_inherited_sdist_asset_omission",
        "source_revision": "1137c6705fd844546d5588757a5a23d4007b20c4",
        "archives": results,
        "limits": [
            "This verifies compatibility runtime and wheel skill bytes, not complete source-distribution membership.",
            "The inherited evaluation-asset omission is assigned to the separate package-boundary feature.",
            "No host, provider, benchmark or empirical execution is performed."
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
