"""Gate 2 comparator with explicit deterministic and report-only fields."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .canonical import ContractError, hash_json


GATE2_POLICY_VERSION = "asme.gate2-policy.v1"


@dataclass(frozen=True)
class ComparatorPolicy:
    deterministic_paths: tuple[str, ...]
    report_only_paths: tuple[str, ...]
    version: str = GATE2_POLICY_VERSION

    def __post_init__(self) -> None:
        if not self.deterministic_paths:
            raise ContractError("Gate 2 requires deterministic binding fields")
        all_paths = (*self.deterministic_paths, *self.report_only_paths)
        if len(set(all_paths)) != len(all_paths) or any(not path.strip() for path in all_paths):
            raise ContractError("Gate 2 policy paths must be nonblank and unique")

    @property
    def digest(self) -> str:
        return hash_json(asdict(self))


@dataclass(frozen=True)
class FieldDifference:
    path: str
    expected: Any
    actual: Any
    verdict: str


@dataclass(frozen=True)
class Gate2Result:
    passed: bool
    policy_hash: str
    failures: tuple[FieldDifference, ...]
    reported_differences: tuple[FieldDifference, ...]


DEFAULT_GATE2_POLICY = ComparatorPolicy(
    deterministic_paths=(
        "archive.tree_sha256",
        "domain.seal",
        "ledger.consistent",
        "manifest.complete",
        "manifest.valid",
        "package.staged_tree_sha256",
        "state.phase",
    ),
    report_only_paths=(
        "outcomes.impact_sequence",
        "outcomes.scores",
        "outcomes.snapshot_empty",
    ),
)


def compare_gate2(
    *,
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
    policy: ComparatorPolicy = DEFAULT_GATE2_POLICY,
    expected_policy_hash: str | None = None,
) -> Gate2Result:
    if expected_policy_hash is not None and expected_policy_hash != policy.digest:
        raise ContractError("Gate 2 comparator policy hash changed")
    failures: list[FieldDifference] = []
    reports: list[FieldDifference] = []
    missing = object()
    for path in policy.deterministic_paths:
        left = _read_path(expected, path, missing)
        right = _read_path(actual, path, missing)
        if left is missing or right is missing or left != right:
            failures.append(
                FieldDifference(
                    path,
                    "<missing>" if left is missing else left,
                    "<missing>" if right is missing else right,
                    "fail",
                )
            )
    for path in policy.report_only_paths:
        left = _read_path(expected, path, missing)
        right = _read_path(actual, path, missing)
        if left is missing or right is missing or left != right:
            reports.append(
                FieldDifference(
                    path,
                    "<missing>" if left is missing else left,
                    "<missing>" if right is missing else right,
                    "report_only",
                )
            )
    return Gate2Result(not failures, policy.digest, tuple(failures), tuple(reports))


def _read_path(value: Mapping[str, Any], path: str, missing: object) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return missing
        current = current[part]
    return current
