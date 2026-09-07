"""Declared task ingestion, split integrity, marker collision checks, and seals."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import secrets
from typing import Any, Callable, Iterable, Mapping

from .canonical import (
    ContractError,
    hash_json,
    require_identifier,
    require_regular_file,
    sha256_bytes,
    sha256_file,
)


SPLITS = ("train", "validation", "test")
_GENERATED_MARKER = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    input: Any


@dataclass(frozen=True)
class AnswerRecord:
    task_id: str
    split: str
    expected: Any
    marker: str | None = None


@dataclass(frozen=True)
class DeclaredDomain:
    domain_id: str
    visibility: str
    task_class: str
    output_kind: str
    tool_mode: str
    read_resource_ids: tuple[str, ...]
    read_resource_hashes: tuple[tuple[str, str], ...]
    tasks: tuple[TaskRecord, ...]
    answers: tuple[AnswerRecord, ...]
    task_source_hash: str
    answer_source_hash: str
    prompt_hash: str
    extractor_hash: str
    scorer_hash: str
    tool_profile_hash: str
    seal: str

    def task_map(self) -> dict[str, TaskRecord]:
        return {record.task_id: record for record in self.tasks}

    def answer_map(self) -> dict[str, AnswerRecord]:
        return {record.task_id: record for record in self.answers}

    @property
    def tool_profile(self) -> dict[str, Any]:
        return {"mode": self.tool_mode, "resources": self.read_resource_ids}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    require_regular_file(path)
    records: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            raise ContractError(f"blank JSONL line at {path}:{line_number}")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ContractError(f"invalid JSONL at {path}:{line_number}: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise ContractError(f"JSONL record must be an object at {path}:{line_number}")
        records.append(value)
    if not records:
        raise ContractError(f"declared source is empty: {path}")
    return records


def _normalized_input_hash(value: Any) -> str:
    return hash_json(value)


def _reject_unapproved_keys(record: Mapping[str, Any], allowed: Iterable[str], *, kind: str) -> None:
    extra = sorted(set(record) - set(allowed))
    if extra:
        raise ContractError(f"{kind} contains unsupported fields: {extra}")


def _normalize_tool_profile(tool_profile: Mapping[str, Any]) -> tuple[str, tuple[str, ...]]:
    if not isinstance(tool_profile, Mapping) or "mode" not in tool_profile:
        raise ContractError("tool profile requires an explicit mode")
    _reject_unapproved_keys(tool_profile, ("mode", "resources"), kind="tool profile")
    mode = tool_profile.get("mode")
    if mode not in {"none", "read"}:
        raise ContractError("portable v1 tool mode must be none or read")
    raw_resources = tool_profile.get("resources", ())
    if not isinstance(raw_resources, (list, tuple)):
        raise ContractError("tool profile resources must be a list")
    resources = tuple(
        require_identifier(item, field="tool profile resource") for item in raw_resources
    )
    if tuple(sorted(set(resources))) != resources:
        raise ContractError("tool profile resources must be sorted and unique")
    if mode == "none" and resources:
        raise ContractError("none mode cannot declare read resources")
    if mode == "read" and not resources:
        raise ContractError("read mode requires at least one named resource")
    return mode, resources


def load_declared_domain(
    *,
    domain_id: str,
    task_file: Path,
    answer_file: Path,
    prompt_file: Path,
    extractor_file: Path,
    scorer_file: Path,
    tool_profile: Mapping[str, Any],
    read_resources: Mapping[str, Path] | None = None,
    visibility: str = "internal",
    task_class: str = "trusted_text",
    output_kind: str = "text",
    marker_factory: Callable[[], str] | None = None,
) -> DeclaredDomain:
    """Load only explicitly declared files and seal every dynamic input."""

    require_identifier(domain_id, field="domain_id")
    if visibility not in {"internal", "public"}:
        raise ContractError("domain visibility must be internal or public")
    if task_class != "trusted_text":
        raise ContractError("portable v1 supports trusted_text tasks only")
    if output_kind != "text":
        raise ContractError("portable v1 supports text output only")
    tool_mode, read_resource_ids = _normalize_tool_profile(tool_profile)
    resource_paths = dict(read_resources or {})
    if set(resource_paths) != set(read_resource_ids):
        raise ContractError("read resource paths must exactly match the tool profile IDs")
    read_resource_hashes = tuple(
        (resource_id, sha256_file(require_regular_file(resource_paths[resource_id])))
        for resource_id in read_resource_ids
    )
    tasks_raw = _read_jsonl(task_file)
    answers_raw = _read_jsonl(answer_file)
    tasks: list[TaskRecord] = []
    answers: list[AnswerRecord] = []
    task_ids: set[str] = set()
    input_hashes: set[str] = set()

    for raw in tasks_raw:
        _reject_unapproved_keys(raw, ("task_id", "input"), kind="task")
        task_id = require_identifier(raw.get("task_id"), field="task_id")
        if task_id in task_ids:
            raise ContractError(f"duplicate task_id: {task_id}")
        input_hash = _normalized_input_hash(raw.get("input"))
        if input_hash in input_hashes:
            raise ContractError(f"duplicate normalized task input: {task_id}")
        task_ids.add(task_id)
        input_hashes.add(input_hash)
        tasks.append(TaskRecord(task_id, raw.get("input")))

    seen_answers: set[str] = set()
    split_ids = {split: set() for split in SPLITS}
    for raw in answers_raw:
        _reject_unapproved_keys(raw, ("task_id", "split", "expected", "marker"), kind="answer")
        task_id = require_identifier(raw.get("task_id"), field="answer.task_id")
        split = raw.get("split")
        if split not in SPLITS:
            raise ContractError(f"unknown split for {task_id}: {split!r}")
        if task_id not in task_ids:
            raise ContractError(f"answer without declared task: {task_id}")
        if task_id in seen_answers:
            raise ContractError(f"duplicate answer task_id: {task_id}")
        marker = raw.get("marker")
        if marker is not None and (not isinstance(marker, str) or not marker):
            raise ContractError(f"marker must be a non-empty string for {task_id}")
        seen_answers.add(task_id)
        split_ids[split].add(task_id)
        answers.append(AnswerRecord(task_id, split, raw.get("expected"), marker))

    if seen_answers != task_ids:
        missing = sorted(task_ids - seen_answers)
        raise ContractError(f"tasks missing answers: {missing}")
    empty = [split for split, ids in split_ids.items() if not ids]
    if empty:
        raise ContractError(f"all train/validation/test splits must be nonempty: {empty}")

    answer_source = answer_file.read_text(encoding="utf-8")
    other_source_bytes = b"\0".join(
        require_regular_file(path).read_bytes()
        for path in (
            task_file,
            prompt_file,
            extractor_file,
            scorer_file,
            *(resource_paths[name] for name in read_resource_ids),
        )
    )
    explicit_counts: dict[str, int] = {}
    for answer in answers:
        if answer.marker is not None:
            explicit_counts[answer.marker] = explicit_counts.get(answer.marker, 0) + 1
    for marker, count in explicit_counts.items():
        if answer_source.count(marker) != count or marker.encode("utf-8") in other_source_bytes:
            raise ContractError("explicit marker collides with another sealed input")

    factory = marker_factory or (lambda: secrets.token_hex(16))
    used = set(explicit_counts)
    generated_by_split: dict[str, str] = {}
    for split in SPLITS:
        split_answers = [answer for answer in answers if answer.split == split]
        missing = [answer for answer in split_answers if answer.marker is None]
        if missing and len(missing) != len(split_answers):
            raise ContractError(f"split markers must be all explicit or all generated: {split}")
        if missing:
            generated_by_split[split] = _fresh_marker(
                factory,
                used=used,
                forbidden=answer_source.encode("utf-8") + b"\0" + other_source_bytes,
            )
            used.add(generated_by_split[split])
    if generated_by_split:
        answers = [
            AnswerRecord(
                answer.task_id,
                answer.split,
                answer.expected,
                answer.marker or generated_by_split[answer.split],
            )
            for answer in answers
        ]

    components = {
        "domain_id": domain_id,
        "visibility": visibility,
        "task_class": task_class,
        "output_kind": output_kind,
        "tool_mode": tool_mode,
        "read_resource_ids": read_resource_ids,
        "read_resource_hashes": read_resource_hashes,
        "task_source_hash": sha256_file(task_file),
        "answer_source_hash": sha256_file(answer_file),
        "prompt_hash": sha256_file(require_regular_file(prompt_file)),
        "extractor_hash": sha256_file(require_regular_file(extractor_file)),
        "scorer_hash": sha256_file(require_regular_file(scorer_file)),
        "tool_profile_hash": hash_json(
            {
                "mode": tool_mode,
                "resources": read_resource_ids,
                "resource_hashes": read_resource_hashes,
            }
        ),
        "tasks": [asdict(record) for record in tasks],
        "answers": [asdict(record) for record in answers],
    }
    return DeclaredDomain(
        domain_id=domain_id,
        visibility=visibility,
        task_class=task_class,
        output_kind=output_kind,
        tool_mode=tool_mode,
        read_resource_ids=read_resource_ids,
        read_resource_hashes=read_resource_hashes,
        tasks=tuple(tasks),
        answers=tuple(answers),
        seal=hash_json(components),
        **{key: value for key, value in components.items() if key.endswith("_hash")},
    )


def verify_domain_seal(domain: DeclaredDomain) -> None:
    components = {
        "domain_id": domain.domain_id,
        "visibility": domain.visibility,
        "task_class": domain.task_class,
        "output_kind": domain.output_kind,
        "tool_mode": domain.tool_mode,
        "read_resource_ids": domain.read_resource_ids,
        "read_resource_hashes": domain.read_resource_hashes,
        "task_source_hash": domain.task_source_hash,
        "answer_source_hash": domain.answer_source_hash,
        "prompt_hash": domain.prompt_hash,
        "extractor_hash": domain.extractor_hash,
        "scorer_hash": domain.scorer_hash,
        "tool_profile_hash": domain.tool_profile_hash,
        "tasks": [asdict(record) for record in domain.tasks],
        "answers": [asdict(record) for record in domain.answers],
    }
    if hash_json(components) != domain.seal:
        raise ContractError("domain seal mismatch; create a new domain identity")


def declared_domain_from_mapping(raw: Mapping[str, Any]) -> DeclaredDomain:
    """Rebuild and verify the immutable domain record stored in a workspace."""

    expected = {
        "domain_id",
        "visibility",
        "task_class",
        "output_kind",
        "tool_mode",
        "read_resource_ids",
        "read_resource_hashes",
        "tasks",
        "answers",
        "task_source_hash",
        "answer_source_hash",
        "prompt_hash",
        "extractor_hash",
        "scorer_hash",
        "tool_profile_hash",
        "seal",
    }
    if set(raw) != expected:
        raise ContractError("recorded domain fields differ from the contract")
    try:
        task_rows = raw["tasks"]
        answer_rows = raw["answers"]
        if not isinstance(task_rows, list) or not isinstance(answer_rows, list):
            raise TypeError
        tasks = tuple(TaskRecord(**dict(item)) for item in task_rows)
        answers = tuple(AnswerRecord(**dict(item)) for item in answer_rows)
        domain = DeclaredDomain(
            domain_id=str(raw["domain_id"]),
            visibility=str(raw["visibility"]),
            task_class=str(raw["task_class"]),
            output_kind=str(raw["output_kind"]),
            tool_mode=str(raw["tool_mode"]),
            read_resource_ids=tuple(raw["read_resource_ids"]),
            read_resource_hashes=tuple(
                (str(item[0]), str(item[1])) for item in raw["read_resource_hashes"]
            ),
            tasks=tasks,
            answers=answers,
            task_source_hash=str(raw["task_source_hash"]),
            answer_source_hash=str(raw["answer_source_hash"]),
            prompt_hash=str(raw["prompt_hash"]),
            extractor_hash=str(raw["extractor_hash"]),
            scorer_hash=str(raw["scorer_hash"]),
            tool_profile_hash=str(raw["tool_profile_hash"]),
            seal=str(raw["seal"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("recorded domain is malformed") from exc
    if domain.visibility not in {"internal", "public"}:
        raise ContractError("recorded domain visibility is invalid")
    if domain.task_class != "trusted_text" or domain.output_kind != "text":
        raise ContractError("recorded domain is outside portable v1 scope")
    mode, resources = _normalize_tool_profile(domain.tool_profile)
    if mode != domain.tool_mode or resources != domain.read_resource_ids:
        raise ContractError("recorded domain tool profile is malformed")
    if tuple(name for name, _ in domain.read_resource_hashes) != domain.read_resource_ids:
        raise ContractError("recorded domain resource hashes differ from tool profile")
    if any(len(digest) != 64 for _, digest in domain.read_resource_hashes):
        raise ContractError("recorded domain resource hash is malformed")
    if not domain.tasks or not domain.answers:
        raise ContractError("recorded domain cannot be empty")
    verify_domain_seal(domain)
    return domain


def marker_propagated(returned_output: str, answer: AnswerRecord) -> bool:
    """Detect literal marker propagation only, never infer access or paraphrase."""

    return bool(answer.marker and answer.marker in returned_output)


def _fresh_marker(
    factory: Callable[[], str], *, used: set[str], forbidden: bytes
) -> str:
    for _ in range(128):
        try:
            candidate = factory()
        except (StopIteration, TypeError, ValueError) as exc:
            raise ContractError("marker generator failed before producing a safe marker") from exc
        if (
            isinstance(candidate, str)
            and _GENERATED_MARKER.fullmatch(candidate)
            and candidate not in used
            and candidate.encode("ascii") not in forbidden
        ):
            return candidate
    raise ContractError("marker generator could not produce a collision-free 32-hex marker")


def output_hash(returned_output: str) -> str:
    return sha256_bytes(returned_output.encode("utf-8"))
