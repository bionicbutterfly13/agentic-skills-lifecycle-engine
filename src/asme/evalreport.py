"""Deterministic offline evaluation reports bound to the A2 acceptance rule."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical import ContractError, canonical_bytes, require_regular_file
from .claims import ClaimClass, RunEvidence, evaluate_claim
from .contract import TraceFidelity
from .evaluation import evaluate_output

EVAL_REPORT_SCHEMA = "asme.eval-report.v1"
_REQUIRED_PHASES = ("baseline", "validation", "confirmation")
_CARTRIDGE_CONFIG_FIELDS = {"extractor", "scorer"}
_OUTPUT_ROW_FIELDS = {"task_id", "returned_output"}
_ANSWER_ROW_FIELDS = {"task_id", "split", "expected", "marker"}


@dataclass(frozen=True)
class EvalTaskScore:
    task_id: str
    score: float
    output_hash: str

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ContractError("eval task_id cannot be blank")
        if isinstance(self.score, bool) or not 0.0 <= float(self.score) <= 1.0:
            raise ContractError("eval task score must be within [0,1]")
        if len(self.output_hash) != 64:
            raise ContractError("eval task output hash must be a SHA-256 hex digest")


@dataclass(frozen=True)
class EvalRun:
    run_id: str
    phase_scores: Mapping[str, tuple[EvalTaskScore, ...]]

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ContractError("eval run_id cannot be blank")
        missing = [phase for phase in _REQUIRED_PHASES if phase not in self.phase_scores]
        extra = [phase for phase in self.phase_scores if phase not in _REQUIRED_PHASES]
        if missing or extra:
            raise ContractError(
                f"eval run phases must be exactly {_REQUIRED_PHASES}:"
                f" missing={missing} extra={extra}"
            )
        for phase in _REQUIRED_PHASES:
            if not self.phase_scores[phase]:
                raise ContractError(f"eval run phase has no scored tasks: {phase}")

    def aggregate(self, phase: str) -> float:
        scores = self.phase_scores[phase]
        return sum(float(item.score) for item in scores) / len(scores)


def _read_jsonl(path: Path, *, required_fields: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        require_regular_file(path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            raise ContractError(f"blank line in {path.name}:{line_number}")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ContractError(f"malformed JSON in {path.name}:{line_number}") from exc
        if not isinstance(row, dict) or set(row) != required_fields:
            raise ContractError(
                f"row fields must be exactly {sorted(required_fields)}"
                f" in {path.name}:{line_number}"
            )
        rows.append(row)
    if not rows:
        raise ContractError(f"no rows in {path.name}")
    return rows


def load_cartridge_answers(cartridge_root: Path) -> dict[str, str]:
    rows = _read_jsonl(
        cartridge_root / "answers.jsonl", required_fields=_ANSWER_ROW_FIELDS
    )
    answers: dict[str, str] = {}
    for row in rows:
        task_id = str(row["task_id"])
        if task_id in answers:
            raise ContractError(f"duplicate answer for eval task: {task_id}")
        answers[task_id] = str(row["expected"])
    return answers


def _cartridge_programs(cartridge_root: Path) -> tuple[Path, Path]:
    config_path = require_regular_file(cartridge_root / "cartridge.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) != _CARTRIDGE_CONFIG_FIELDS:
        raise ContractError(
            f"cartridge config fields must be exactly {sorted(_CARTRIDGE_CONFIG_FIELDS)}"
        )
    extractor = require_regular_file((cartridge_root / str(config["extractor"])).resolve())
    scorer = require_regular_file((cartridge_root / str(config["scorer"])).resolve())
    return extractor, scorer


def run_cartridge_phase(
    *, cartridge_root: Path, outputs_file: Path
) -> tuple[EvalTaskScore, ...]:
    """Score one rollout file through the cartridge's real subprocess contracts."""

    answers = load_cartridge_answers(cartridge_root)
    extractor, scorer = _cartridge_programs(cartridge_root)
    rows = _read_jsonl(outputs_file, required_fields=_OUTPUT_ROW_FIELDS)
    scored: list[EvalTaskScore] = []
    seen: set[str] = set()
    for row in rows:
        task_id = str(row["task_id"])
        if task_id in seen:
            raise ContractError(f"duplicate eval output for task: {task_id}")
        seen.add(task_id)
        if task_id not in answers:
            raise ContractError(f"unknown eval task: {task_id}")
        result = evaluate_output(
            returned_output=str(row["returned_output"]),
            expected=answers[task_id],
            extractor=extractor,
            scorer=scorer,
        )
        if not result.valid or result.score is None:
            raise ContractError(
                f"unscorable eval output for task {task_id}:"
                f" {result.error_class}: {result.error_message}"
            )
        scored.append(
            EvalTaskScore(
                task_id=task_id,
                score=float(result.score),
                output_hash=result.output_hash,
            )
        )
    return tuple(scored)


def build_eval_report(
    *,
    domain_id: str,
    runs: Sequence[EvalRun],
    trace_fidelity: str,
    isolation_label: str,
    seed: int,
) -> dict[str, Any]:
    if not domain_id.strip():
        raise ContractError("eval report domain_id cannot be blank")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ContractError("eval report seed must be an integer")
    if not runs:
        raise ContractError("eval report requires at least one run")
    if len({run.run_id for run in runs}) != len(runs):
        raise ContractError("eval report run IDs must be unique")
    fidelity = TraceFidelity(trace_fidelity)
    if not isolation_label.strip():
        raise ContractError("eval report isolation label cannot be blank")

    run_entries: list[dict[str, Any]] = []
    for run in runs:
        aggregates = {phase: run.aggregate(phase) for phase in _REQUIRED_PHASES}
        evidence = RunEvidence(
            run_id=run.run_id,
            baseline_score=aggregates["baseline"],
            validation_score=aggregates["validation"],
            confirmation_score=aggregates["confirmation"],
            complete=True,
            trace_fidelity=fidelity,
            isolation_label=isolation_label,
        )
        decision = evaluate_claim(
            claim_class=ClaimClass.LOCAL_ACCEPTANCE, runs=(evidence,)
        )
        run_entries.append(
            {
                "run_id": run.run_id,
                "aggregates": aggregates,
                "tasks": {
                    phase: [
                        {
                            "task_id": item.task_id,
                            "score": float(item.score),
                            "output_hash": item.output_hash,
                        }
                        for item in run.phase_scores[phase]
                    ]
                    for phase in _REQUIRED_PHASES
                },
                "a2_local_acceptance": {
                    "allowed": decision.allowed,
                    "label": decision.label,
                    "reasons": list(decision.reasons),
                },
            }
        )
    return {
        "schema": EVAL_REPORT_SCHEMA,
        "domain_id": domain_id,
        "seed": seed,
        "trace_fidelity": fidelity.value,
        "isolation_label": isolation_label,
        "runs": run_entries,
    }


def eval_report_bytes(report: Mapping[str, Any]) -> bytes:
    if report.get("schema") != EVAL_REPORT_SCHEMA:
        raise ContractError("eval report schema mismatch")
    return canonical_bytes(dict(report))


def render_eval_summary(report: Mapping[str, Any]) -> str:
    if report.get("schema") != EVAL_REPORT_SCHEMA:
        raise ContractError("eval report schema mismatch")
    lines = [
        (
            f"Agent Skill Mastery Engine eval report for {report['domain_id']}"
            f" (seed {report['seed']}, fidelity {report['trace_fidelity']},"
            f" isolation {report['isolation_label']})"
        )
    ]
    for run in report["runs"]:
        aggregates = run["aggregates"]
        decision = run["a2_local_acceptance"]
        verdict = (
            "ACCEPTED"
            if decision["allowed"]
            else "NOT ACCEPTED (" + ", ".join(decision["reasons"]) + ")"
        )
        lines.append(
            f"- {run['run_id']}: baseline {aggregates['baseline']:g},"
            f" validation {aggregates['validation']:g},"
            f" confirmation {aggregates['confirmation']:g}: {verdict} under A2"
        )
    return "\n".join(lines) + "\n"
