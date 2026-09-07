"""Complete package-safe authority registry for parity and acceptance evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib import resources
import json
import re
from typing import Any, Mapping

from .canonical import ContractError, canonical_bytes, hash_json, safe_member_name
from .contract import SourceClass


SOURCE_REGISTRY_SCHEMA = "asme.source-registry.v1"
_ENTRY_ID = re.compile(r"(?:SP-\d{3}|HF-A\d{2}|GA-\d{2}|A[1-5]|PUB-\d{3})")

PUBLIC_ARTIFACTS = (
    "README.md",
    "CITATION.cff",
    "SKILL.md",
    "PURPOSE.md",
    "NOTICE.md",
    "PROVENANCE.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "references/paper-notes.md",
    "references/fidelity.md",
    "references/integration.md",
    "src/asme/data/source-registry.json",
    "references/verification/README.md",
    "references/verification/independent-review-protocol.md",
    "docs/implementation-parity.md",
    "docs/license-decision.md",
    "adapters/hermes_plugin/README.md",
    "adapters/hermes_plugin/plugin.yaml",
    "scripts/stdlib_smoke.py",
    "scripts/extractors/answer_tag.py",
    "scripts/scorers/exact_match.py",
    "assets/pattern.md.tmpl",
    "assets/index.md.tmpl",
    "assets/log.md.tmpl",
    "assets/skill-impact.md.tmpl",
    "assets/PURPOSE.md.tmpl",
    "assets/SKILL.md.tmpl",
    "assets/inference-prompt.txt.tmpl",
    "LICENSE",
)


@dataclass(frozen=True)
class SourceRegistryEntry:
    entry_id: str
    kind: str
    source_class: SourceClass
    source_locator: str
    decision_status: str

    def __post_init__(self) -> None:
        if _ENTRY_ID.fullmatch(self.entry_id) is None:
            raise ContractError("source registry entry ID is invalid")
        if self.kind not in {
            "source_parity",
            "acceptance",
            "historical_gate_a",
            "development_gate_a",
            "public_artifact",
        }:
            raise ContractError("source registry entry kind is invalid")
        if not self.source_locator.strip() or not self.decision_status.strip():
            raise ContractError("source registry locator and status cannot be blank")
        if self.kind == "public_artifact":
            safe_member_name(self.source_locator)


@dataclass(frozen=True)
class SourceRegistry:
    entries: tuple[SourceRegistryEntry, ...]
    schema: str = SOURCE_REGISTRY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != SOURCE_REGISTRY_SCHEMA:
            raise ContractError("source registry schema is unsupported")
        ids = [entry.entry_id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ContractError("source registry entry IDs must be unique")
        expected = (
            tuple(f"SP-{index:03d}" for index in range(1, 107))
            + tuple(f"HF-A{index:02d}" for index in range(1, 28))
            + tuple(f"GA-{index:02d}" for index in range(1, 6))
            + tuple(f"A{index}" for index in range(1, 6))
            + tuple(f"PUB-{index:03d}" for index in range(1, len(PUBLIC_ARTIFACTS) + 1))
        )
        if tuple(ids) != expected:
            raise ContractError("source registry is incomplete or out of canonical order")
        artifacts = tuple(
            entry.source_locator
            for entry in self.entries
            if entry.kind == "public_artifact"
        )
        if artifacts != PUBLIC_ARTIFACTS:
            raise ContractError("source registry public artifact inventory differs")

    @property
    def digest(self) -> str:
        return hash_json(self.as_mapping())

    def as_mapping(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "entries": [
                {
                    **asdict(entry),
                    "source_class": entry.source_class.value,
                }
                for entry in self.entries
            ],
        }


def source_registry_from_mapping(raw: Mapping[str, Any]) -> SourceRegistry:
    if set(raw) != {"schema", "entries"} or raw.get("schema") != SOURCE_REGISTRY_SCHEMA:
        raise ContractError("source registry fields or schema differ")
    rows = raw.get("entries")
    if not isinstance(rows, list):
        raise ContractError("source registry entries must be a list")
    entries: list[SourceRegistryEntry] = []
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {
            "entry_id",
            "kind",
            "source_class",
            "source_locator",
            "decision_status",
        }:
            raise ContractError("source registry entry fields differ")
        try:
            entries.append(
                SourceRegistryEntry(
                    entry_id=str(row["entry_id"]),
                    kind=str(row["kind"]),
                    source_class=SourceClass(str(row["source_class"])),
                    source_locator=str(row["source_locator"]),
                    decision_status=str(row["decision_status"]),
                )
            )
        except ValueError as exc:
            raise ContractError("source registry source class is invalid") from exc
    return SourceRegistry(tuple(entries))


def default_source_registry_bytes() -> bytes:
    resource = resources.files("asme").joinpath(
        "data/source-registry.json"
    )
    raw_bytes = resource.read_bytes()
    try:
        raw = json.loads(raw_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("default source registry is malformed") from exc
    if not isinstance(raw, Mapping):
        raise ContractError("default source registry must be an object")
    registry = source_registry_from_mapping(raw)
    encoded = canonical_bytes(registry.as_mapping())
    if raw_bytes != encoded:
        raise ContractError("default source registry is not canonical JSON")
    return encoded


def default_source_registry() -> SourceRegistry:
    raw = json.loads(default_source_registry_bytes())
    if not isinstance(raw, Mapping):  # pragma: no cover - checked by bytes loader
        raise ContractError("default source registry must be an object")
    return source_registry_from_mapping(raw)
