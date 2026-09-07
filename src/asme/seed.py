"""Human-approved, named observation seeding before the baseline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from typing import Any, Mapping

from .canonical import ContractError, hash_json, require_identifier
from .domain import DeclaredDomain


SEED_SCHEMA = "asme.observation-seed.v1"
_HEADINGS = ("## Description", "## Root cause", "## Evidence", "## Solution")
_EVIDENCE = re.compile(
    r"^- observation ([a-z0-9][a-z0-9._-]{0,127}): (.+)$"
)


@dataclass(frozen=True)
class SeedObservation:
    observation_id: str
    visibility: str
    pattern_name: str
    evidence: str
    page: str


@dataclass(frozen=True)
class SeedPacket:
    domain_id: str
    observation_ids: tuple[str, ...]
    pages: Mapping[str, str]
    index: str
    log_entry: str
    observations: tuple[SeedObservation, ...]
    schema: str = SEED_SCHEMA

    @property
    def digest(self) -> str:
        return hash_json(asdict(self))


def validate_seed_packet(value: bytes, *, domain: DeclaredDomain) -> SeedPacket:
    """Validate only provided observations; never inspect Task Observer state."""

    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("seed packet must be UTF-8 JSON") from exc
    decoder = json.JSONDecoder()
    try:
        raw, end = decoder.raw_decode(text)
    except json.JSONDecodeError as exc:
        raise ContractError("seed packet is malformed JSON") from exc
    if text[end:].strip():
        raise ContractError("seed packet contains trailing content")
    if not isinstance(raw, dict):
        raise ContractError("seed packet must be an object")
    required = {"schema", "domain_id", "observations", "index", "log_entry"}
    if set(raw) != required:
        raise ContractError("seed packet fields differ from the contract")
    if raw["schema"] != SEED_SCHEMA or raw["domain_id"] != domain.domain_id:
        raise ContractError("seed packet schema or domain identity is invalid")
    observations_raw = raw["observations"]
    if not isinstance(observations_raw, list) or not observations_raw:
        raise ContractError("seed packet requires named observations")
    observations: list[SeedObservation] = []
    pages: dict[str, str] = {}
    ids: set[str] = set()
    for item in observations_raw:
        if not isinstance(item, Mapping) or set(item) != {
            "observation_id",
            "visibility",
            "pattern_name",
            "evidence",
            "page",
        }:
            raise ContractError("seed observation fields differ from the contract")
        observation_id = require_identifier(
            item["observation_id"], field="observation_id"
        )
        pattern_name = require_identifier(item["pattern_name"], field="pattern_name")
        visibility = item["visibility"]
        evidence = item["evidence"]
        page = item["page"]
        if observation_id in ids or pattern_name in pages:
            raise ContractError("seed observation and pattern names must be unique")
        if visibility not in {"internal", "public"}:
            raise ContractError("seed observation visibility is invalid")
        if domain.visibility == "public" and visibility == "internal":
            raise ContractError("internal observation cannot seed a public domain")
        if not isinstance(evidence, str) or not evidence.strip():
            raise ContractError("seed observation evidence cannot be blank")
        if not isinstance(page, str):
            raise ContractError("seed observation page must be text")
        _validate_seed_page(
            page,
            observation_id=observation_id,
            evidence=evidence,
        )
        ids.add(observation_id)
        pages[pattern_name] = page
        observations.append(
            SeedObservation(
                observation_id,
                visibility,
                pattern_name,
                evidence,
                page,
            )
        )
    index = raw["index"]
    log_entry = raw["log_entry"]
    if not isinstance(index, str) or not index.strip():
        raise ContractError("seed index cannot be blank")
    if not isinstance(log_entry, str) or not log_entry.strip():
        raise ContractError("seed log entry cannot be blank")
    return SeedPacket(
        domain_id=domain.domain_id,
        observation_ids=tuple(sorted(ids)),
        pages={name: pages[name] for name in sorted(pages)},
        index=index,
        log_entry=log_entry,
        observations=tuple(sorted(observations, key=lambda item: item.observation_id)),
    )


def _validate_seed_page(page: str, *, observation_id: str, evidence: str) -> None:
    lines = page.splitlines()
    if not 10 <= len(lines) <= 30:
        raise ContractError("seed pattern page must contain 10-30 lines")
    if not lines or lines[0] not in {
        "pattern_kind: failure",
        "pattern_kind: success",
        "pattern_kind: paired",
    }:
        raise ContractError("seed pattern page has an invalid pattern_kind")
    origin_lines = [line for line in lines if line.startswith("origin_observations: ")]
    if len(origin_lines) != 1:
        raise ContractError("seed pattern page requires one origin_observations line")
    try:
        origins = json.loads(origin_lines[0].removeprefix("origin_observations: "))
    except json.JSONDecodeError as exc:
        raise ContractError("origin_observations must be a JSON list") from exc
    if origins != [observation_id]:
        raise ContractError("seed pattern origin differs from its observation ID")
    positions: list[int] = []
    for heading in _HEADINGS:
        matches = [index for index, line in enumerate(lines) if line == heading]
        if len(matches) != 1:
            raise ContractError(f"seed pattern requires heading exactly once: {heading}")
        positions.append(matches[0])
    if positions != sorted(positions) or any(
        line.startswith("## ") and line not in _HEADINGS for line in lines
    ):
        raise ContractError("seed pattern headings are invalid")
    sections: dict[str, list[str]] = {}
    for offset, heading in enumerate(_HEADINGS):
        start = positions[offset] + 1
        end = positions[offset + 1] if offset + 1 < len(positions) else len(lines)
        sections[heading] = lines[start:end]
    for heading in ("## Description", "## Root cause", "## Solution"):
        if not any(line.strip() for line in sections[heading]):
            raise ContractError(f"seed pattern section cannot be blank: {heading}")
    evidence_lines = [line for line in sections["## Evidence"] if line.strip()]
    if len(evidence_lines) != 1:
        raise ContractError("seed pattern requires one observation evidence line")
    match = _EVIDENCE.fullmatch(evidence_lines[0])
    if match is None or match.group(1) != observation_id:
        raise ContractError("seed pattern evidence is not bound to its observation")
    try:
        excerpt = json.loads(match.group(2))
    except json.JSONDecodeError as exc:
        raise ContractError("seed pattern evidence excerpt must be a JSON string") from exc
    if not isinstance(excerpt, str) or not excerpt.strip() or excerpt not in evidence:
        raise ContractError("seed pattern evidence excerpt is absent from observation evidence")
