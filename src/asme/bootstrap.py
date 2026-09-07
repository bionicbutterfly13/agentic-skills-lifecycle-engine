"""Deterministic seeded paired-bootstrap evidence for the paper-comparable claim.

The statistic is the mean, over tasks, of the per-task confirmation-minus-
baseline score difference averaged across runs (a paired design over the shared
task axis). Resampling indices come from SHA-256 of ``seed:resample:draw`` so
the artifact is byte-stable across platforms and Python versions, with no
dependency on ``random`` module internals.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping, Sequence

from .canonical import ContractError, canonical_bytes, sha256_bytes
from .claims import BootstrapEvidence
from .evalreport import EvalRun

BOOTSTRAP_SCHEMA = "asme.paired-bootstrap.v1"
COMPLETE_RESAMPLES = 1000
_METHOD = "paired-task-bootstrap-sha256"


@dataclass(frozen=True)
class PairedBootstrapResult:
    payload: Mapping[str, Any]
    artifact: bytes
    evidence: BootstrapEvidence


def _draw_index(seed: int, resample: int, draw: int, population: int) -> int:
    digest = hashlib.sha256(f"{seed}:{resample}:{draw}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % population


def _paired_diffs(runs: Sequence[EvalRun]) -> tuple[tuple[str, ...], dict[str, float]]:
    task_ids: tuple[str, ...] | None = None
    per_task_sums: dict[str, float] = {}
    for run in runs:
        run_tasks: dict[str, dict[str, float]] = {}
        for phase in ("baseline", "confirmation"):
            phase_map = {
                item.task_id: float(item.score) for item in run.phase_scores[phase]
            }
            if len(phase_map) != len(run.phase_scores[phase]):
                raise ContractError(
                    f"bootstrap run has duplicate {phase} tasks: {run.run_id}"
                )
            run_tasks[phase] = phase_map
        if set(run_tasks["baseline"]) != set(run_tasks["confirmation"]):
            raise ContractError(
                f"bootstrap run phases must score the same tasks: {run.run_id}"
            )
        ids = tuple(sorted(run_tasks["baseline"]))
        if task_ids is None:
            task_ids = ids
            per_task_sums = {task_id: 0.0 for task_id in ids}
        elif ids != task_ids:
            raise ContractError(
                "bootstrap runs must share the same task set for pairing"
            )
        for task_id in ids:
            per_task_sums[task_id] += (
                run_tasks["confirmation"][task_id] - run_tasks["baseline"][task_id]
            )
    assert task_ids is not None
    return task_ids, {
        task_id: total / len(runs) for task_id, total in per_task_sums.items()
    }


def build_paired_bootstrap(
    *,
    runs: Sequence[EvalRun],
    seed: int,
    resamples: int,
) -> PairedBootstrapResult:
    """Produce one canonical bootstrap artifact and its claim-layer evidence."""

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ContractError("bootstrap seed must be an integer")
    if isinstance(resamples, bool) or not isinstance(resamples, int) or resamples < 1:
        raise ContractError("bootstrap resamples must be a positive integer")
    if not runs:
        raise ContractError("bootstrap requires at least one run")
    run_ids = tuple(run.run_id for run in runs)
    if len(set(run_ids)) != len(run_ids):
        raise ContractError("bootstrap run IDs must be unique")
    task_ids, mean_diffs = _paired_diffs(runs)

    observed = sum(mean_diffs.values()) / len(task_ids)
    statistics: list[float] = []
    for resample in range(resamples):
        total = 0.0
        for draw in range(len(task_ids)):
            index = _draw_index(seed, resample, draw, len(task_ids))
            total += mean_diffs[task_ids[index]]
        statistics.append(total / len(task_ids))
    ordered = sorted(statistics)

    def _percentile(fraction: float) -> float:
        position = min(
            len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1)))
        )
        return ordered[position]

    payload: dict[str, Any] = {
        "schema": BOOTSTRAP_SCHEMA,
        "method": _METHOD,
        "seed": seed,
        "resamples": resamples,
        "run_ids": sorted(run_ids),
        "task_ids": list(task_ids),
        "per_task_mean_diff": {
            task_id: mean_diffs[task_id] for task_id in task_ids
        },
        "observed_mean_diff": observed,
        "ci_lower_2_5": _percentile(0.025),
        "ci_upper_97_5": _percentile(0.975),
        "fraction_nonpositive": sum(
            1 for value in statistics if value <= 0.0
        ) / len(statistics),
    }
    artifact = canonical_bytes(payload)
    evidence = BootstrapEvidence(
        run_ids=tuple(sorted(run_ids)),
        paired=True,
        complete=resamples >= COMPLETE_RESAMPLES,
        method=f"{_METHOD}/resamples={resamples}",
        artifact_hash=sha256_bytes(artifact),
    )
    return PairedBootstrapResult(payload=payload, artifact=artifact, evidence=evidence)
