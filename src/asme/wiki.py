"""Paper-bounded trace sampling and mechanical wiki result validation."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import re
from typing import Any, Mapping, Sequence

from .canonical import ContractError, hash_json, require_identifier


FAILURE_LIMIT = 5
SUCCESS_LIMIT = 3
TRACE_CHAR_LIMIT = 15_000


@dataclass(frozen=True)
class TraceView:
    task_id: str
    passed: bool
    content: str
    source_hash: str


def sample_traces(records: Sequence[Mapping[str, Any]]) -> tuple[TraceView, ...]:
    """Apply paper limits using deterministic ID ordering, a local architecture rule."""

    failures = sorted((item for item in records if not bool(item.get("passed"))), key=lambda x: str(x.get("task_id")))
    successes = sorted((item for item in records if bool(item.get("passed"))), key=lambda x: str(x.get("task_id")))
    selected = failures[:FAILURE_LIMIT] + successes[:SUCCESS_LIMIT]
    views: list[TraceView] = []
    for record in selected:
        task_id = require_identifier(record.get("task_id"), field="trace.task_id")
        content = str(record.get("content") or "")[:TRACE_CHAR_LIMIT]
        source_hash = str(record.get("source_hash") or "")
        if len(source_hash) != 64:
            raise ContractError(f"trace {task_id} has no bound source hash")
        views.append(TraceView(task_id, bool(record.get("passed")), content, source_hash))
    return tuple(views)


def validate_pattern_multiset(
    observed: Sequence[Mapping[str, Any]], expected: Sequence[Mapping[str, Any]]
) -> None:
    """Compare pattern tuples as a multiset, preserving duplicate counts."""

    def normalize(item: Mapping[str, Any]) -> tuple[str, str, str]:
        fields = ("pattern_class", "evidence_id", "reason")
        missing = [field for field in fields if field not in item]
        if missing:
            raise ContractError(f"pattern tuple missing fields: {missing}")
        reason = str(item["reason"]).strip()
        if not reason:
            raise ContractError("pattern reason cannot be blank")
        return str(item["pattern_class"]), str(item["evidence_id"]), reason

    observed_counter = Counter(normalize(item) for item in observed)
    expected_counter = Counter(normalize(item) for item in expected)
    if observed_counter != expected_counter:
        raise ContractError("pattern tuple multiset mismatch")


def validate_role_json(value: str) -> dict[str, Any]:
    """Reject trailing JSON and require one complete top-level object."""

    decoder = json.JSONDecoder()
    try:
        result, end = decoder.raw_decode(value)
    except json.JSONDecodeError as exc:
        raise ContractError("role output is malformed JSON") from exc
    if value[end:].strip():
        raise ContractError("role output contains trailing JSON or text")
    if not isinstance(result, dict):
        raise ContractError("role output must be one JSON object")
    return result


def wiki_change_digest(value: Mapping[str, Any]) -> str:
    return hash_json(dict(value))


_HEADINGS = ("## Description", "## Root cause", "## Evidence", "## Solution")
_EVIDENCE_RE = re.compile(r"^- (fail|pass) ([a-z0-9][a-z0-9._-]{0,127}): (.+)$")


@dataclass(frozen=True)
class ValidatedWikiChange:
    pages: Mapping[str, str]
    index: str
    log_entry: str
    attestation: Mapping[str, Any]

    @property
    def digest(self) -> str:
        return hash_json(
            {
                "pages": dict(self.pages),
                "index": self.index,
                "log_entry": self.log_entry,
                "attestation": dict(self.attestation),
            }
        )


def validate_maintainer_change(
    *,
    payload: Mapping[str, Any],
    traces: Sequence[TraceView],
    maintainer_input_hash: str,
    existing_pages: Mapping[str, str],
) -> ValidatedWikiChange:
    """Validate structure/provenance without claiming semantic judgments are proven."""

    required = {"create_patterns", "update_patterns", "update_index", "append_log", "attestation"}
    if set(payload) != required:
        raise ContractError(f"maintainer output fields must equal {sorted(required)}")
    creates = _mapping(payload["create_patterns"], field="create_patterns")
    updates = _mapping(payload["update_patterns"], field="update_patterns")
    if set(creates) & set(updates):
        raise ContractError("a pattern cannot be created and updated in one change")
    pages = dict(existing_pages)
    changed_names: set[str] = set()
    for name, text in sorted(creates.items()):
        require_identifier(name, field="pattern name")
        if name in pages:
            raise ContractError(f"create pattern already exists: {name}")
        if not isinstance(text, str):
            raise ContractError(f"created pattern must be text: {name}")
        pages[name] = text
        changed_names.add(name)
    for name, operations in sorted(updates.items()):
        require_identifier(name, field="pattern name")
        if name not in pages:
            raise ContractError(f"updated pattern does not exist: {name}")
        if not isinstance(operations, list) or not operations:
            raise ContractError(f"updated pattern requires a nonempty operation list: {name}")
        pages[name] = _apply_patch_operations(pages[name], operations, pattern_name=name)
        changed_names.add(name)
    index = payload["update_index"]
    log_entry = payload["append_log"]
    if not isinstance(index, str) or not index.strip():
        raise ContractError("update_index must be nonblank text")
    if not isinstance(log_entry, str) or not log_entry.strip():
        raise ContractError("append_log must be nonblank text")
    attestation = _mapping(payload["attestation"], field="attestation")
    if set(attestation) != {"input_hash", "class_coverage", "per_pattern"}:
        raise ContractError("attestation fields must be input_hash, class_coverage, and per_pattern")
    if attestation["input_hash"] != maintainer_input_hash:
        raise ContractError("maintainer input hash mismatch")
    per_pattern = _mapping(attestation["per_pattern"], field="attestation.per_pattern")
    if set(per_pattern) != changed_names:
        raise ContractError("per_pattern attestation must cover every and only changed pattern")
    trace_map = {trace.task_id: trace for trace in traces}
    if len(trace_map) != len(traces):
        raise ContractError("sample contains duplicate trace IDs")
    _validate_class_coverage(
        attestation["class_coverage"], traces=traces, known_patterns=set(pages)
    )
    for name in sorted(changed_names):
        page_kind, evidence = _validate_pattern_page(pages[name])
        _validate_pattern_attestation(
            name=name,
            attestation=_mapping(per_pattern[name], field=f"attestation.per_pattern.{name}"),
            page_kind=page_kind,
            evidence=evidence,
            trace_map=trace_map,
            created=name in creates,
        )
    return ValidatedWikiChange(pages, index, log_entry, attestation)


def _apply_patch_operations(text: str, operations: Sequence[Any], *, pattern_name: str) -> str:
    current = text
    for index, raw in enumerate(operations, 1):
        operation = _mapping(raw, field=f"update {pattern_name} operation {index}")
        action = operation.get("op")
        target = operation.get("target")
        content = operation.get("content")
        if action not in {"append", "replace", "insert_after"}:
            raise ContractError(f"unknown patch operation for {pattern_name}: {action!r}")
        if not isinstance(content, str) or not content:
            raise ContractError(f"patch content must be nonempty for {pattern_name}")
        if action == "append":
            if target not in {None, ""}:
                raise ContractError("append patch must not name a target")
            current += content
            continue
        if not isinstance(target, str) or not target:
            raise ContractError(f"patch target must be nonempty for {pattern_name}")
        if current.count(target) != 1:
            raise ContractError(f"patch target must match exactly once for {pattern_name}")
        replacement = content if action == "replace" else target + content
        current = current.replace(target, replacement, 1)
    return current


def _validate_pattern_page(text: str) -> tuple[str, tuple[tuple[str, str, str], ...]]:
    lines = text.splitlines()
    if not 10 <= len(lines) <= 30:
        raise ContractError("pattern page must contain 10-30 lines")
    if not lines or lines[0] not in {
        "pattern_kind: failure",
        "pattern_kind: success",
        "pattern_kind: paired",
    }:
        raise ContractError("pattern page has an invalid pattern_kind first line")
    positions: list[int] = []
    for heading in _HEADINGS:
        matches = [index for index, line in enumerate(lines) if line == heading]
        if len(matches) != 1:
            raise ContractError(f"pattern page requires heading exactly once: {heading}")
        positions.append(matches[0])
    if positions != sorted(positions) or any(
        line.startswith("## ") and line not in _HEADINGS for line in lines
    ):
        raise ContractError("pattern page headings are out of order or unsupported")
    sections: dict[str, list[str]] = {}
    for offset, heading in enumerate(_HEADINGS):
        start = positions[offset] + 1
        end = positions[offset + 1] if offset + 1 < len(positions) else len(lines)
        sections[heading] = lines[start:end]
    for heading in ("## Description", "## Root cause", "## Solution"):
        if not any(line.strip() for line in sections[heading]):
            raise ContractError(f"pattern page section cannot be empty: {heading}")
    evidence: list[tuple[str, str, str]] = []
    for line in sections["## Evidence"]:
        match = _EVIDENCE_RE.fullmatch(line)
        if match is None:
            raise ContractError("every Evidence line must be one complete evidence tuple")
        outcome, task_id, encoded_span = match.groups()
        try:
            span = json.loads(encoded_span)
        except json.JSONDecodeError as exc:
            raise ContractError("Evidence span must be one complete JSON string") from exc
        if not isinstance(span, str) or not span.strip():
            raise ContractError("Evidence span must be a nonblank JSON string")
        evidence.append((task_id, outcome, span))
    if not evidence:
        raise ContractError("pattern page requires at least one Evidence line")
    return lines[0].removeprefix("pattern_kind: "), tuple(evidence)


def _validate_class_coverage(
    value: Any, *, traces: Sequence[TraceView], known_patterns: set[str]
) -> None:
    coverage = _mapping(value, field="class_coverage")
    present = {"success" if trace.passed else "failure" for trace in traces}
    if set(coverage) != present:
        raise ContractError("class_coverage must cover every and only sampled outcome class")
    for outcome, raw in coverage.items():
        disposition = _mapping(raw, field=f"class_coverage.{outcome}")
        if set(disposition) == {"represented_by"}:
            names = disposition["represented_by"]
            if not isinstance(names, list) or not names or len(names) != len(set(names)):
                raise ContractError(f"represented_by must be a nonempty unique list for {outcome}")
            unknown = sorted(set(names) - known_patterns)
            if unknown:
                raise ContractError(f"class_coverage references unknown patterns: {unknown}")
        elif set(disposition) == {"not_used"}:
            if not isinstance(disposition["not_used"], str) or not disposition["not_used"].strip():
                raise ContractError(f"class_coverage not_used reason cannot be blank for {outcome}")
        else:
            raise ContractError(f"invalid class_coverage disposition for {outcome}")


def _validate_pattern_attestation(
    *,
    name: str,
    attestation: Mapping[str, Any],
    page_kind: str,
    evidence: Sequence[tuple[str, str, str]],
    trace_map: Mapping[str, TraceView],
    created: bool,
) -> None:
    required = {
        "pattern_kind",
        "failure_traces",
        "success_traces",
        "quoted_commands",
        "dedup_disposition",
        "dedup_reason",
        "root_cause_reason",
        "generalizable_because",
    }
    if set(attestation) != required:
        raise ContractError(f"pattern attestation fields are incomplete for {name}")
    kind = attestation["pattern_kind"]
    if kind not in {"failure", "success", "paired"}:
        raise ContractError(f"invalid attested pattern_kind for {name}")
    if kind != page_kind:
        raise ContractError(f"page and attested pattern_kind differ for {name}")
    failure_ids = _trace_disposition(
        attestation["failure_traces"], outcome="failure", trace_map=trace_map
    )
    success_ids = _trace_disposition(
        attestation["success_traces"], outcome="success", trace_map=trace_map
    )
    if failure_ids & success_ids:
        raise ContractError(f"failure and success trace lists overlap for {name}")
    if kind == "failure" and not failure_ids:
        raise ContractError(f"failure pattern lacks failure traces: {name}")
    if kind == "success" and not success_ids:
        raise ContractError(f"success pattern lacks success traces: {name}")
    if kind == "paired" and (not failure_ids or not success_ids):
        raise ContractError(f"paired pattern requires both trace classes: {name}")
    quoted = attestation["quoted_commands"]
    if not isinstance(quoted, list) or not quoted:
        raise ContractError(f"quoted_commands must be a nonempty list for {name}")
    normalized: list[tuple[str, str, str]] = []
    for raw in quoted:
        item = _mapping(raw, field=f"quoted_commands for {name}")
        if set(item) != {"trace", "outcome", "span"}:
            raise ContractError(f"quoted command fields are invalid for {name}")
        trace_id = item["trace"]
        outcome = item["outcome"]
        span = item["span"]
        if trace_id not in trace_map:
            raise ContractError(f"quoted command references unknown trace: {trace_id}")
        actual_outcome = "pass" if trace_map[trace_id].passed else "fail"
        if outcome != actual_outcome:
            raise ContractError(f"quoted command outcome mismatch for trace: {trace_id}")
        if not isinstance(span, str) or not span.strip() or span not in trace_map[trace_id].content:
            raise ContractError(f"quoted command span is absent or blank for trace: {trace_id}")
        normalized.append((trace_id, outcome, span))
    if len(normalized) != len(set(normalized)):
        raise ContractError(f"quoted_commands contains duplicate tuples for {name}")
    if Counter(normalized) != Counter(evidence):
        raise ContractError(f"Evidence tuple multiset differs from quoted_commands for {name}")
    evidence_failure = {trace_id for trace_id, outcome, _ in evidence if outcome == "fail"}
    evidence_success = {trace_id for trace_id, outcome, _ in evidence if outcome == "pass"}
    if evidence_failure != failure_ids or evidence_success != success_ids:
        raise ContractError(f"Evidence trace IDs differ from attested trace lists for {name}")
    disposition = attestation["dedup_disposition"]
    if created:
        if disposition != "new":
            raise ContractError(f"created pattern must have new dedup disposition: {name}")
    elif disposition != {"updates": name}:
        raise ContractError(f"updated pattern must identify its dedup target: {name}")
    for field in ("dedup_reason", "root_cause_reason", "generalizable_because"):
        value = attestation[field]
        if not isinstance(value, str) or not value.strip():
            raise ContractError(f"agent judgment cannot be blank: {name}.{field}")


def _trace_disposition(
    value: Any, *, outcome: str, trace_map: Mapping[str, TraceView]
) -> set[str]:
    present = {
        trace_id
        for trace_id, trace in trace_map.items()
        if trace.passed is (outcome == "success")
    }
    if isinstance(value, dict):
        if set(value) != {"not_applicable"}:
            raise ContractError(f"invalid {outcome}_traces disposition")
        reason = value["not_applicable"]
        if not isinstance(reason, str) or not reason.strip() or present:
            raise ContractError(f"{outcome}_traces not_applicable is invalid")
        return set()
    if not isinstance(value, list) or not value or len(value) != len(set(value)):
        raise ContractError(f"{outcome}_traces must be a nonempty unique list")
    ids = set(value)
    unknown = ids - set(trace_map)
    wrong = ids - present
    if unknown or wrong:
        raise ContractError(f"{outcome}_traces contains unknown or wrong-label IDs")
    return ids


def _mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{field} must be an object")
    return value
