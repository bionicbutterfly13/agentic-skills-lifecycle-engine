"""Validate this project's explicit source boundary and complete built archives.

This is build tooling, not a candidate-package scanner exemption. No Git or
installed ASME package is needed, including when rebuilding an extracted sdist.
"""

from __future__ import annotations

import argparse
import base64
import csv
from email.parser import BytesParser
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import stat
import sys
import tarfile
import tomllib
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCAL_PACKAGE = ROOT / "src/asme"
for _name, _module in tuple(sys.modules.items()):
    if _name == "asme" or _name.startswith("asme."):
        _origin = getattr(_module, "__file__", None)
        if not _origin or not Path(_origin).resolve().is_relative_to(LOCAL_PACKAGE):
            raise RuntimeError("foreign already-loaded asme module refused")
sys.path.insert(0, str(ROOT / "src"))

from asme.canonical import ContractError, safe_member_name  # noqa: E402
from asme.package import scan_community_safety  # noqa: E402
from asme.skill_assets import skill_files  # noqa: E402

INTERNAL_FILES = {
    "AGENTS.md": "Agent workflow instructions are repository operational state.",
    ".gitignore": "Git working-tree exclusions are not package inputs.",
    "docs/research/wikiskill-code-parity.md": "Exact historical local-path audit.",
    "docs/evidence/wikiskill-parity-audit.json": "Exact historical local-path audit receipt.",
    "docs/public/2026-09-06-from-wikiskill-to-lifecycle.md": "Unpublished preliminary draft.",
}
INTERNAL_TREES = {".planning", ".agents", ".claude", ".codex", ".cursor", ".github"}
OPERATIONAL_ROOTS = {".git", ".gsd", ".venv", "venv", "build", "dist",
                     ".pytest_cache", ".ruff_cache", ".mypy_cache", ".tox", ".nox"}
REQUIRED_TREES = {"src", "assets", "adapters", "scripts", "tests", "references", "locked", "docs"}
REQUIRED_ROOTS = {"pyproject.toml", "setup.py", "MANIFEST.in", "LICENSE", "NOTICE.md",
                  "README.md", "PROVENANCE.md", "CONTRIBUTING.md", "SKILL.md", "PURPOSE.md",
                  "CHANGELOG.md", "CITATION.cff", "SECURITY.md"}


def _file(root: Path, name: str) -> bytes:
    safe_member_name(name)
    target = root
    for part in PurePosixPath(name).parts:
        target = target / part
        if target.is_symlink():
            raise ContractError(f"symlink source forbidden: {name}")
    try:
        info = target.stat()
    except OSError as exc:
        raise ContractError(f"required source missing: {name}") from exc
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o7000:
        raise ContractError(f"nonregular or hardlinked source forbidden: {name}")
    return target.read_bytes()


def _identity(root: Path) -> dict:
    project = tomllib.loads(_file(root, "pyproject.toml").decode())["project"]
    project["normalized_name"] = re.sub(r"[-_.]+", "_", project["name"])
    return project


def _egg(root: Path) -> str:
    return "src/" + _identity(root)["normalized_name"] + ".egg-info/"


def _dist(root: Path) -> str:
    project = _identity(root)
    return project["normalized_name"] + "-" + project["version"] + ".dist-info/"


def _generated_names(root: Path) -> set[str]:
    return {"PKG-INFO", "setup.cfg"} | {_egg(root) + name for name in (
        "PKG-INFO", "SOURCES.txt", "dependency_links.txt", "entry_points.txt", "top_level.txt")}


def _manifest(root: Path) -> set[str]:
    lines = [line.strip() for line in _file(root, "MANIFEST.in").decode().splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    if not lines or lines.pop(0) != "global-exclude *":
        raise ContractError("manifest must first clear implicit sources with global-exclude *")
    members: set[str] = set()
    generated = _generated_names(root)
    for line in lines:
        fields = line.split()
        if len(fields) != 2 or fields[0] != "include":
            raise ContractError("manifest accepts only literal single-path include directives")
        name = safe_member_name(fields[1])
        if any(char in name for char in "*?[]"):
            raise ContractError("manifest wildcard forbidden")
        if name in members:
            raise ContractError(f"duplicate manifest entry: {name}")
        if (name in INTERNAL_FILES or name.split("/")[0] in INTERNAL_TREES | OPERATIONAL_ROOTS
                or name in generated):
            raise ContractError(f"internal/generated manifest collision: {name}")
        members.add(name)
    return members


def source_inventory(root: Path) -> dict[str, str]:
    """Exhaustively classify source paths; never descend into opaque root state."""
    root = Path(root)
    result: dict[str, str] = {}
    generated = _generated_names(root)
    for folder, directories, filenames in os.walk(root, followlinks=False):
        relative = Path(folder).relative_to(root)
        for name in list(directories):
            path = Path(folder) / name
            member = path.relative_to(root).as_posix()
            if relative == Path(".") and name in OPERATIONAL_ROOTS | INTERNAL_TREES:
                directories.remove(name)
                result[member + "/"] = (
                    "operational tree" if name in OPERATIONAL_ROOTS else "internal workflow tree"
                )
            elif path.is_symlink():
                raise ContractError(f"symlink directory forbidden: {member}")
            elif name == "__pycache__":
                # Only actual Python bytecode may occupy this generated directory.
                for cached in path.iterdir():
                    if cached.is_symlink() or not cached.is_file() or cached.suffix != ".pyc":
                        raise ContractError(f"unknown Python cache entry: {member}")
                directories.remove(name)
                result[member + "/"] = "generated Python bytecode"
        for name in filenames:
            member = (relative / name).as_posix()
            if relative == Path(".") and name in OPERATIONAL_ROOTS:
                result[member] = "operational root marker"
            elif member in INTERNAL_FILES:
                _file(root, member)
                result[member] = INTERNAL_FILES[member]
            elif member in generated:
                _file(root, member)
                result[member] = "generated backend metadata"
            elif name == ".DS_Store":
                result[member] = "generated filesystem metadata"
            else:
                _file(root, member)
                result[member] = "public source"
    return result


def _document_dependencies(files: dict[str, bytes]) -> None:
    manifest = json.loads(files["docs/migration/asme-source-manifest.json"])
    origins = {entry["historical_destination"]: entry["source_path"]
               for entry in manifest["entries"] if entry.get("historical_destination")}
    destinations = {
        entry["source_path"]: entry.get("historical_destination") or entry.get("destination")
        for entry in manifest["entries"]
    }
    for name, content in files.items():
        if not name.endswith(".md"):
            continue
        text = content.decode("utf-8")
        targets = re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)
        targets += re.findall(r"(?m)^\s*\[[^\]]+\]:\s*(\S+)", text)
        for raw in targets:
            target = raw.strip().split(' "', 1)[0].strip("<>")
            link = urlsplit(target)
            if link.scheme or link.netloc or not link.path:
                continue
            origin = origins.get(name, name)
            locator = posixpath.normpath(
                posixpath.join(posixpath.dirname(origin), unquote(link.path))
            )
            safe_member_name(locator)
            destination = destinations.get(locator) if name in origins else locator
            if not destination or (destination not in files and not any(
                    item.startswith(destination.rstrip("/") + "/") for item in files)):
                raise ContractError(f"missing document link dependency: {name} -> {locator}")


def source_distribution_files(root: Path) -> dict[str, bytes]:
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ContractError("source root must be a real directory")
    members = _manifest(root)
    inventory = source_inventory(root)
    public = {name for name, reason in inventory.items() if reason == "public source"}
    if public != members:
        raise ContractError(f"unclassified or missing manifest source: {sorted(public ^ members)}")
    if not REQUIRED_ROOTS <= members:
        raise ContractError(f"missing required root sources: {sorted(REQUIRED_ROOTS - members)}")
    for family in REQUIRED_TREES:
        if not any(name.startswith(family + "/") for name in members):
            raise ContractError(f"missing required source family: {family}")
    files = {name: _file(root, name) for name in sorted(members)}
    imported = json.loads(files["docs/migration/asme-source-manifest.json"])
    required_imported = {entry[key] for entry in imported["entries"]
                         for key in ("destination", "historical_destination")
                         if entry.get(key) and entry[key] not in INTERNAL_FILES}
    if not required_imported <= files.keys():
        missing = sorted(required_imported - files.keys())
        raise ContractError(f"missing imported public sources: {missing}")
    scan_community_safety(files)
    _document_dependencies(files)
    generated = sdist_metadata(root, files)
    for name, expected in generated.items():
        if name in inventory:
            _generated_equal(name, _file(root, name), expected)
    return files


def _entry_points(root: Path) -> bytes:
    scripts = _identity(root)["scripts"]
    entries = "".join(f"{name} = {value}\n" for name, value in sorted(scripts.items()))
    return ("[console_scripts]\n" + entries).encode()


def _metadata(root: Path) -> bytes:
    project = _identity(root)
    headers = ["Metadata-Version: 2.4", f"Name: {project['name']}",
               f"Version: {project['version']}",
               f"Summary: {project['description']}",
               "Author: " + ", ".join(author["name"] for author in project["authors"]),
               f"License: {project['license']['text']}"]
    headers += ["Classifier: " + value for value in project["classifiers"]]
    headers += [f"Requires-Python: {project['requires-python']}",
                "Description-Content-Type: text/markdown",
                "License-File: LICENSE", "License-File: NOTICE.md", "Dynamic: license-file"]
    return ("\n".join(headers) + "\n\n").encode() + _file(root, project["readme"])


def sdist_metadata(root: Path, files: dict[str, bytes]) -> dict[str, bytes]:
    """Canonical metadata fixture and policy values; the backend still builds archives."""
    egg = _egg(root)
    generated = {
        "PKG-INFO": _metadata(root),
        "setup.cfg": b"[egg_info]\ntag_build = \ntag_date = 0\n\n",
        egg + "PKG-INFO": _metadata(root),
        egg + "dependency_links.txt": b"\n",
        egg + "entry_points.txt": _entry_points(root),
        egg + "top_level.txt": b"asme\n",
    }
    # egg_info writes the literal source inventory; sdist then appends SOURCES
    # to its in-memory copy list. Other generated inputs are explicitly validated below.
    generated[egg + "SOURCES.txt"] = ("\n".join(sorted(files)) + "\n").encode()
    return generated


def backend_sdist_inputs(root: Path, backend_files, files: dict[str, bytes]) -> list[str]:
    egg = _egg(root)
    if (len(backend_files) != len(set(backend_files))
            or set(backend_files) != files.keys() | {egg + "SOURCES.txt"}):
        raise ContractError("backend source list differs from explicit inventory")
    generated = sdist_metadata(root, files)
    selected = {name for name in generated if name.startswith(egg)}
    for name in selected:
        _generated_equal(name, _file(root, name), generated[name])
    return sorted(files.keys() | selected)


def wheel_payload(root: Path) -> dict[str, bytes]:
    files = source_distribution_files(root)
    payload = {name.removeprefix("src/"): data for name, data in files.items()
               if name.startswith("src/asme/")}
    payload.update({"asme/skill/" + name: files[name] for name in skill_files(root)})
    return payload


def wheel_metadata(root: Path) -> dict[str, bytes]:
    dist = _dist(root)
    return {dist + "METADATA": _metadata(root),
            dist + "WHEEL": (b"Wheel-Version: 1.0\nGenerator: setuptools (84.0.0)\n"
                             b"Root-Is-Purelib: true\nTag: py3-none-any\n"),
            dist + "entry_points.txt": _entry_points(root), dist + "top_level.txt": b"asme\n",
            dist + "licenses/LICENSE": _file(root, "LICENSE"),
            dist + "licenses/NOTICE.md": _file(root, "NOTICE.md")}


def _metadata_equal(actual: bytes, expected: bytes, name: str) -> None:
    left, right = BytesParser().parsebytes(actual), BytesParser().parsebytes(expected)
    versions = left.get_all("Metadata-Version", [])
    if len(versions) != 1 or versions[0] not in {"2.1", "2.2", "2.3", "2.4"}:
        raise ContractError(f"unsupported generated metadata version: {name}")
    dynamic = left.get_all("Dynamic", [])
    if dynamic not in ([], ["license-file"]) or (versions[0] == "2.1" and dynamic):
        raise ContractError(f"unexpected dynamic metadata: {name}")
    for message in (left, right):
        del message["Metadata-Version"]
        del message["Dynamic"]
    def headers(message):
        return sorted((key.lower(), " ".join(value.split())) for key, value in message.items())
    if (left.defects or headers(left) != headers(right)
            or left.get_payload().rstrip("\n") != right.get_payload().rstrip("\n")):
        raise ContractError(f"generated metadata differs: {name}")


def _generated_equal(name: str, actual: bytes, expected: bytes) -> None:
    scan_community_safety({name: actual})
    if name.endswith("PKG-INFO"):
        _metadata_equal(actual, expected, name)
    elif name.endswith("SOURCES.txt"):
        lines = actual.decode().splitlines()
        if len(lines) != len(set(lines)) or set(lines) != set(expected.decode().splitlines()):
            raise ContractError("generated SOURCES membership differs")
    elif actual != expected:
        raise ContractError(f"generated metadata differs: {name}")


def _same_payload(actual: dict[str, bytes], expected: dict[str, bytes], label: str) -> None:
    if actual.keys() != expected.keys():
        difference = sorted(actual.keys() ^ expected.keys())
        raise ContractError(f"{label} membership differs: {difference}")
    for name in actual:
        if actual[name] != expected[name]:
            raise ContractError(f"{label} bytes differ: {name}")


def validate_release_tree(root: Path, files: dict[str, bytes], source_root: Path) -> None:
    actual = {}
    for folder, directories, filenames in os.walk(root, followlinks=False):
        if any((Path(folder) / name).is_symlink() for name in directories):
            raise ContractError("symlink release-tree directory")
        for name in filenames:
            member = (Path(folder) / name).relative_to(root).as_posix()
            # setuptools may deliberately hardlink unchanged source files in its release tree.
            target = Path(folder) / name
            if target.is_symlink() or not target.is_file():
                raise ContractError("nonregular release-tree entry")
            actual[member] = target.read_bytes()
    _validate_sdist_files(actual, files, source_root)


def _validate_sdist_files(actual: dict[str, bytes], files: dict[str, bytes], root: Path) -> None:
    generated = sdist_metadata(root, files)
    if actual.keys() != files.keys() | generated.keys():
        difference = sorted(actual.keys() ^ (files.keys() | generated.keys()))
        raise ContractError(f"sdist membership differs: {difference}")
    _same_payload({name: actual[name] for name in files}, files, "sdist source")
    for name, expected in generated.items():
        _generated_equal(name, actual[name], expected)
    scan_community_safety(actual)


def _receipt(archive: Path, members: dict[str, bytes], directories=(), *, modes=None) -> dict:
    return {"status": "pass", "archive": archive.name,
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "file_count": len(members), "directories": sorted(directories),
            "member_modes": dict(sorted((modes or {}).items())),
            "members": [{"path": name, "bytes": len(data),
                         "sha256": hashlib.sha256(data).hexdigest()}
                        for name, data in sorted(members.items())]}


def verify_sdist(archive: Path, *, source_root: Path) -> dict:
    files = source_distribution_files(source_root)
    project = _identity(source_root)
    prefixes = {project[key] + "-" + project["version"] for key in ("name", "normalized_name")}
    members, directories, seen, modes = {}, set(), set(), {}
    with tarfile.open(archive, "r:gz") as stream:
        infos = stream.getmembers()
        if stream.pax_headers:
            raise ContractError("global tar PAX metadata is not part of this distribution")
        roots = {safe_member_name(info.name).split("/", 1)[0] for info in infos}
        if len(roots) != 1 or not roots <= prefixes:
            raise ContractError("sdist root prefix differs")
        prefix = roots.pop()
        for info in infos:
            name = safe_member_name(info.name)
            if name in seen:
                raise ContractError(f"duplicate tar member: {name}")
            seen.add(name)
            if name != prefix and not name.startswith(prefix + "/"):
                raise ContractError("sdist root prefix differs")
            if info.mode & 0o7000 or info.linkname:
                raise ContractError(f"privileged mode or link metadata: {name}")
            if not set(info.pax_headers) <= {"mtime", "path"}:
                raise ContractError(f"unsupported tar PAX metadata: {name}")
            if "path" in info.pax_headers and info.pax_headers["path"] != name:
                raise ContractError("tar PAX path differs from member name")
            try:
                valid_time = math.isfinite(float(info.pax_headers.get("mtime", info.mtime)))
            except (ValueError, TypeError):
                valid_time = False
            if not valid_time:
                raise ContractError("invalid tar timestamp metadata")
            scan_community_safety({name: json.dumps({"uname": info.uname, "gname": info.gname,
                "pax": info.pax_headers}, ensure_ascii=False).encode()})
            modes[name] = oct(info.mode)
            if info.isdir():
                if info.mode != 0o755:
                    raise ContractError(f"unexpected tar directory mode: {name}")
                directories.add(name)
            elif not info.isreg():
                raise ContractError(f"nonregular or privileged tar member: {name}")
            else:
                relative = name[len(prefix) + 1:]
                allowed_modes = ({(source_root / relative).stat().st_mode & 0o777}
                                 if relative in files else {0o644, 0o664})
                if info.mode not in allowed_modes:
                    raise ContractError(f"tar file mode differs from source policy: {name}")
        for info in infos:
            if info.isreg():
                if info.name == prefix:
                    raise ContractError("sdist root is a file")
                members[info.name[len(prefix) + 1:]] = stream.extractfile(info).read()
    expected_directories = {prefix}
    for name in members:
        parent = PurePosixPath(prefix + "/" + name).parent
        while str(parent) != ".":
            expected_directories.add(str(parent))
            parent = parent.parent
    if not directories <= expected_directories:
        raise ContractError("unknown sdist directory")
    _validate_sdist_files(members, files, source_root)
    return _receipt(Path(archive), members, directories, modes=modes)


def verify_wheel(archive: Path, *, source_root: Path) -> dict:
    payload = wheel_payload(source_root)
    metadata = wheel_metadata(source_root)
    record_name = _dist(source_root) + "RECORD"
    members, modes = {}, {}
    with zipfile.ZipFile(archive) as stream:
        if stream.comment:
            raise ContractError("wheel archive comments are not part of this distribution")
        for info in stream.infolist():
            name = safe_member_name(info.filename)
            if name in members:
                raise ContractError(f"duplicate wheel member: {name}")
            mode = info.external_attr >> 16
            if info.is_dir() or stat.S_IFMT(mode) not in {0, stat.S_IFREG} or mode & 0o7000:
                raise ContractError(f"nonregular or privileged wheel member: {name}")
            if info.comment or info.extra or info.flag_bits & ~(0x800 | 0x8):
                raise ContractError(f"unsupported wheel transport metadata: {name}")
            if name in payload:
                original = (source_root / name.removeprefix("asme/skill/")
                            if name.startswith("asme/skill/") else source_root / "src" / name)
                allowed_modes = {original.stat().st_mode & 0o777}
            else:
                allowed_modes = {0o644, 0o664}
            if stat.S_IMODE(mode) not in allowed_modes:
                raise ContractError(f"wheel mode differs from source policy: {name}")
            modes[name] = oct(mode)
            members[name] = stream.read(info)
    dist = _dist(source_root)
    # Legacy wheel 0.41 places the same two notices at the dist-info root.
    # Admit only that complete, versioned layout; runtime and skill bytes stay fixed.
    if dist + "LICENSE" in members or dist + "NOTICE.md" in members:
        message = BytesParser().parsebytes(members.get(dist + "METADATA", b""))
        wheel = BytesParser().parsebytes(members.get(dist + "WHEEL", b""))
        if (message.get("Metadata-Version") not in {"2.1", "2.2", "2.3"}
                or not wheel.get("Generator", "").startswith("bdist_wheel (")):
            raise ContractError("unexpected legacy wheel license layout")
        for license_name in ("LICENSE", "NOTICE.md"):
            metadata[dist + license_name] = metadata.pop(dist + "licenses/" + license_name)
    if members.keys() != payload.keys() | metadata.keys() | {record_name}:
        raise ContractError("wheel membership differs")
    _same_payload({name: members[name] for name in payload}, payload, "wheel payload")
    for name, expected in metadata.items():
        if name.endswith("/METADATA"):
            _metadata_equal(members[name], expected, name)
        elif name.endswith("/WHEEL"):
            message = BytesParser().parsebytes(members[name])
            generator = message.get_all("Generator", [])
            generator_pattern = r"(?:setuptools|bdist_wheel) \([0-9]+(?:\.[0-9]+)+(?:[^\s()]*)\)"
            if (len(generator) != 1 or not re.fullmatch(generator_pattern, generator[0])
                    or message.get_payload().strip() or message.defects):
                raise ContractError("invalid wheel generator metadata")
            del message["Generator"]
            expected_headers = [("Wheel-Version", "1.0"), ("Root-Is-Purelib", "true"),
                                ("Tag", "py3-none-any")]
            if sorted(message.items()) != sorted(expected_headers):
                raise ContractError("wheel compatibility metadata differs")
        elif members[name] != expected:
            raise ContractError(f"wheel metadata differs: {name}")
    rows = list(csv.reader(io.StringIO(members[record_name].decode())))
    if (any(len(row) != 3 for row in rows) or len(rows) != len(members)
            or {row[0] for row in rows} != members.keys()):
        raise ContractError("wheel RECORD membership differs")
    for name, digest, size in rows:
        if name == record_name:
            if digest or size:
                raise ContractError("wheel RECORD self-entry must be unhashed")
        else:
            expected = base64.urlsafe_b64encode(
                hashlib.sha256(members[name]).digest()).rstrip(b"=").decode()
            if digest != "sha256=" + expected or size != str(len(members[name])):
                raise ContractError(f"wheel RECORD digest or size differs: {name}")
    scan_community_safety(members)
    return _receipt(Path(archive), members, modes=modes)


def validate_build_lib(build_lib: Path, source_root: Path) -> None:
    actual = {}
    for folder, directories, filenames in os.walk(build_lib, followlinks=False):
        if any((Path(folder) / name).is_symlink() for name in directories):
            raise ContractError("symlink build directory")
        for name in filenames:
            member = (Path(folder) / name).relative_to(build_lib).as_posix()
            actual[member] = _file(build_lib, member)
    _same_payload(actual, wheel_payload(source_root), "built runtime/skill")
    scan_community_safety(actual)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--check-source", action="store_true")
    args = parser.parse_args(argv)
    files = source_distribution_files(args.source)
    result = {"status": "pass", "source_count": len(files),
              "source_inventory": source_inventory(args.source), "artifacts": []}
    if args.artifacts:
        archives = sorted(args.artifacts.iterdir())
        if not archives or any(not path.is_file() or path.is_symlink() or not (
                path.name.endswith(".tar.gz") or path.suffix == ".whl") for path in archives):
            raise ContractError("artifact directory must contain only real source/wheel archives")
        for path in archives:
            verify = verify_wheel if path.suffix == ".whl" else verify_sdist
            result["artifacts"].append(verify(path, source_root=args.source))
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
