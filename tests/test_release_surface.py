from __future__ import annotations

from pathlib import Path
import re

from asme.integration import validate_skill_authoring
from asme.source_registry import PUBLIC_ARTIFACTS


def test_public_inventory_is_complete_and_license_matches_gate_a_option_a() -> None:
    root = Path(__file__).parents[1]
    required = PUBLIC_ARTIFACTS
    assert all((root / member).is_file() for member in required)
    license_text = (root / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in license_text
    assert "Copyright (c) 2026 Mani Saint-Victor, MD" in license_text
    assert "CC BY 4.0" in license_text
    assert not (root / "LICENSE.txt").exists()
    assert "distribution remains gated" in (root / "NOTICE.md").read_text(
        encoding="utf-8"
    )
    citation = (root / "CITATION.cff").read_text(encoding="utf-8")
    assert 'family-names: "Saint-Victor"' in citation
    assert 'given-names: "Mani"' in citation
    assert 'name-suffix: "MD"' in citation
    assert 'url: "https://manysaintvictormd.com"' in citation
    assert "date-released:" not in citation and "doi:" not in citation
    assert "license: MIT" in citation


def test_public_inventory_contains_no_private_paths_or_secret_like_values() -> None:
    root = Path(__file__).parents[1]
    forbidden_paths = (b"/Users/", b"/Volumes/")
    secret_patterns = (
        re.compile(rb"AKIA[0-9A-Z]{16}"),
        re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    )

    for member in PUBLIC_ARTIFACTS:
        content = (root / member).read_bytes()
        assert not any(marker in content for marker in forbidden_paths), member
        assert not any(pattern.search(content) for pattern in secret_patterns), member


def test_public_prose_has_no_em_dash_and_skill_description_is_bounded() -> None:
    root = Path(__file__).parents[1]
    prose = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in {".md", ".tmpl"}
        and not any(part.startswith(".") for part in path.relative_to(root).parts)
    ]
    assert not [path.relative_to(root).as_posix() for path in prose if "—" in path.read_text(encoding="utf-8")]
    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    description = re.search(r"^description: (.+)$", skill, flags=re.MULTILINE)
    assert description is not None and len(description.group(1)) < 300
    assert re.search(r"^1\. ", skill, flags=re.MULTILINE)
    metadata = validate_skill_authoring(
        skill.encode("utf-8"), expected_name="asme"
    )
    assert metadata.version == "0.1.0"
    assert metadata.last_updated == "2026-08-31"


def test_implementation_parity_has_every_source_row_exactly_once() -> None:
    root = Path(__file__).parents[1]
    text = (root / "docs/implementation-parity.md").read_text(encoding="utf-8")
    rows = [int(value) for value in re.findall(r"^\| SP-(\d{3}) \|", text, re.MULTILINE)]
    assert rows == list(range(1, 107))


def test_implementation_parity_has_every_hf_a_criterion_exactly_once() -> None:
    root = Path(__file__).parents[1]
    text = (root / "docs/implementation-parity.md").read_text(encoding="utf-8")
    rows = [int(value) for value in re.findall(r"^\| HF-A(\d{2}) \|", text, re.MULTILINE)]
    assert rows == list(range(1, 28))
