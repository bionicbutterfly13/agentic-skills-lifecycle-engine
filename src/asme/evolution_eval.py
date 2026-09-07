"""Offline end-to-end evolution evaluation through the real state machine.

Every transition here runs the actual :class:`EvolutionWorkflow` against a
throwaway workspace. The only scripted parts are the fixtures the paper's
human/agent roles would supply: the task responder, the Wiki Maintainer JSON,
and the Skill Proposer JSON. All of them are deterministic in the seed, so two
runs on the same cartridge produce byte-identical eval reports.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .adapter import ProviderPolicy
from .canonical import ContractError, require_regular_file, sha256_bytes
from .cartridge import DomainCartridge
from .contract import CapabilityReport
from .domain import load_declared_domain
from .evalreport import EvalRun, EvalTaskScore, build_eval_report, _cartridge_programs
from .evidence import captured_execution
from .manifest import rollout_manifest_from_mapping
from .workflow import EvolutionWorkflow, PreparedTask
from .workspace import DomainWorkspace, WorkspaceLayout

_SKILL_NAME = "answer-tag-discipline"
_WRONG_OUTPUT = "<answer>unscored-guess</answer>"
_STARTED = "2026-09-01T00:00:00+00:00"
_FINISHED = "2026-09-01T00:00:01+00:00"


def _read_rows(path: Path, *, required_fields: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    text = require_regular_file(path).read_text(encoding="utf-8")
    for line_number, line in enumerate(text.splitlines(), start=1):
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


def _weak_correct_ids(task_ids: list[str], *, seed: int) -> frozenset[str]:
    """Deterministically pick the half of validation tasks the weak fixture solves."""

    ranked = sorted(
        task_ids, key=lambda task_id: sha256_bytes(f"{seed}:{task_id}".encode("utf-8"))
    )
    return frozenset(ranked[: len(ranked) // 2])


def _scripted_output(
    *,
    task_id: str,
    prompt: str,
    expected: str,
    weak_correct: frozenset[str],
) -> str:
    """One deterministic responder for every phase of the loop.

    Train traces are always solved (they are the fixture's demonstrations),
    post-adoption prompts are solved because the proposed skill is actually in
    the rendered prompt, and the pre-skill baseline solves only the seeded half.
    """

    if _SKILL_NAME in prompt or task_id.startswith("train-") or task_id in weak_correct:
        return f"<answer>{expected}</answer>"
    return _WRONG_OUTPUT


def _record_phase(
    workflow: EvolutionWorkflow,
    *,
    phase: str,
    report: CapabilityReport,
    policy: ProviderPolicy,
    expected: Mapping[str, str],
    weak_correct: frozenset[str],
) -> None:
    prepared = workflow.prepare_rollout(
        phase=phase, capability=report, provider_policy=policy
    )
    for item in prepared:
        output = _scripted_output(
            task_id=item.task_id,
            prompt=item.prompt,
            expected=expected[item.task_id],
            weak_correct=weak_correct,
        )
        workflow.record_execution(
            phase=phase, task_id=item.task_id, execution=_capture(item, report, output)
        )
    workflow.ingest_rollout(phase=phase)


def _capture(prepared: PreparedTask, report: CapabilityReport, output: str):
    return captured_execution(
        execution_id=f"execution-{prepared.job.correlation_id}",
        runtime_id=report.runtime_id,
        runtime_version=report.runtime_version,
        adapter_version=report.adapter_version,
        job_spec_hash=prepared.job.digest,
        prompt_hash=prepared.prompt_hash,
        active_snapshot_hash=prepared.snapshot_hash,
        started=_STARTED,
        finished=_FINISHED,
        termination="completed",
        events=({"kind": "final_answer", "text": output},),
        returned_output=output,
        capability=report,
    )


def _maintainer_payload(
    *, maintainer_input: bytes, span_task: str, span: str
) -> dict[str, Any]:
    pattern = "\n".join(
        (
            "pattern_kind: success",
            "",
            "## Description",
            "Answer with exactly one answer tag holding the expected value.",
            "## Root cause",
            "Successful traces respected the single-answer-tag output contract.",
            "## Evidence",
            f"- pass {span_task}: {json.dumps(span)}",
            "## Solution",
            "Constrain the response to one answer tag with the exact value.",
        )
    )
    return {
        "create_patterns": {_SKILL_NAME: pattern},
        "update_patterns": {},
        "update_index": f"# Pattern index\n\n- {_SKILL_NAME}\n",
        "append_log": f"iteration 1: added {_SKILL_NAME}",
        "attestation": {
            "input_hash": sha256_bytes(maintainer_input),
            "class_coverage": {"success": {"represented_by": [_SKILL_NAME]}},
            "per_pattern": {
                _SKILL_NAME: {
                    "pattern_kind": "success",
                    "failure_traces": {
                        "not_applicable": "No failing traces were sampled."
                    },
                    "success_traces": [span_task],
                    "quoted_commands": [
                        {"trace": span_task, "outcome": "pass", "span": span}
                    ],
                    "dedup_disposition": "new",
                    "dedup_reason": "No prior pattern pages exist.",
                    "root_cause_reason": "The trace demonstrates the format rule.",
                    "generalizable_because": "The rule holds for every task prompt.",
                }
            },
        },
    }


def _proposal_payload(*, context: bytes, trace_ids: list[str]) -> dict[str, Any]:
    skill_text = "\n".join(
        (
            f"# {_SKILL_NAME}",
            "",
            "Reply with exactly one <answer>...</answer> tag containing the",
            "exact requested value and nothing else.",
            "",
        )
    )
    return {
        "action": "create",
        "context_hash": sha256_bytes(context),
        "reason": "Every successful train trace used one exact answer tag.",
        "trace_ids": trace_ids,
        "skill_name": _SKILL_NAME,
        "files": {"SKILL.md": skill_text},
    }


def _manifest_scores(
    workspace: DomainWorkspace, *, phase: str, iteration: int
) -> tuple[EvalTaskScore, ...]:
    path = require_regular_file(
        workspace.engine.target_roots["runs"] / f"{iteration}/{phase}/manifest.json",
        root=workspace.engine.target_roots["runs"],
    )
    manifest = rollout_manifest_from_mapping(
        json.loads(path.read_text(encoding="utf-8"))
    )
    if not manifest.valid:
        raise ContractError(f"evolution eval requires a valid {phase} manifest")
    return tuple(
        EvalTaskScore(
            task_id=entry.task_id,
            score=float(entry.score),
            output_hash=entry.returned_output_hash,
        )
        for entry in manifest.entries
    )


def run_evolution_evaluation(
    *,
    cartridge_root: Path,
    workspace_root: Path,
    seed: int,
    run_id: str,
) -> dict[str, Any]:
    """Drive one full baseline-to-accepted-candidate loop and report it under A2."""

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ContractError("evolution eval seed must be an integer")
    if workspace_root.exists() or workspace_root.is_symlink():
        raise ContractError(
            f"evolution eval workspace already exists: {workspace_root}"
        )
    tasks = _read_rows(
        cartridge_root / "tasks.jsonl", required_fields={"task_id", "input"}
    )
    answers = _read_rows(
        cartridge_root / "answers.jsonl",
        required_fields={"task_id", "split", "expected", "marker"},
    )
    expected_by_source = {str(row["task_id"]): str(row["expected"]) for row in answers}
    ordered = sorted(tasks, key=lambda row: str(row["task_id"]))
    if len(ordered) < 4:
        raise ContractError("evolution eval requires at least four cartridge tasks")
    missing = [row["task_id"] for row in ordered if row["task_id"] not in expected_by_source]
    if missing:
        raise ContractError(f"cartridge tasks lack answers: {missing}")

    domain_rows: list[dict[str, Any]] = []
    answer_rows: list[dict[str, Any]] = []
    expected: dict[str, str] = {}
    for index, row in enumerate(ordered, start=1):
        for prefix, split in (("train", "train"), ("val", "validation")):
            task_id = f"{prefix}-{index}"
            task_input = (
                row["input"]
                if split == "validation"
                else f"train demonstration {index}: {row['input']}"
            )
            domain_rows.append({"task_id": task_id, "input": task_input})
            answer_rows.append(
                {
                    "task_id": task_id,
                    "split": split,
                    "expected": expected_by_source[row["task_id"]],
                }
            )
            expected[task_id] = expected_by_source[row["task_id"]]
    domain_rows.append(
        {"task_id": "test-1", "input": f"held-out check: {ordered[0]['input']}"}
    )
    answer_rows.append(
        {
            "task_id": "test-1",
            "split": "test",
            "expected": expected_by_source[ordered[0]["task_id"]],
        }
    )
    expected["test-1"] = expected_by_source[ordered[0]["task_id"]]

    workspace_root.mkdir(parents=True)
    inputs = workspace_root / "inputs"
    inputs.mkdir()
    task_file = inputs / "tasks.jsonl"
    answer_file = inputs / "answers.jsonl"
    task_file.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in domain_rows),
        encoding="utf-8",
    )
    answer_file.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in answer_rows),
        encoding="utf-8",
    )
    extractor, scorer = _cartridge_programs(cartridge_root)
    prompt_file = require_regular_file(cartridge_root / "prompt.txt")

    counter = iter(range(1, 1000))
    domain_id = f"evolution-eval-{cartridge_root.name}"
    domain = load_declared_domain(
        domain_id=domain_id,
        task_file=task_file,
        answer_file=answer_file,
        prompt_file=prompt_file,
        extractor_file=extractor,
        scorer_file=scorer,
        tool_profile={"mode": "none"},
        marker_factory=lambda: sha256_bytes(
            f"evalmarker:{seed}:{next(counter)}".encode("utf-8")
        )[:32],
    )
    cartridge = DomainCartridge.from_paths(
        domain=domain,
        prompt=prompt_file,
        extractor=extractor,
        scorer=scorer,
        read_resources={},
    )
    workspace = DomainWorkspace(
        domain_id=domain_id,
        layout=WorkspaceLayout.under(workspace_root / "domain"),
    )
    workspace.initialize(domain=domain, max_iterations=1, cartridge=cartridge)
    workspace.apply(operation="skip-seed")
    workflow = EvolutionWorkflow(workspace)
    report = CapabilityReport.conservative(
        runtime_id="asme-evolution-eval",
        runtime_version="1.0.0",
        adapter_version="1.0.0",
        provider="openai-codex",
        model_id="scripted-fixture",
        openai_backed=True,
        captured_events=("final_answer",),
    )
    policy = ProviderPolicy(("openai-codex",), ("scripted-fixture",))
    weak_correct = _weak_correct_ids(
        [row["task_id"] for row in answer_rows if row["split"] == "validation"],
        seed=seed,
    )

    _record_phase(
        workflow,
        phase="baseline",
        report=report,
        policy=policy,
        expected=expected,
        weak_correct=weak_correct,
    )
    workflow.finalize_baseline()
    _record_phase(
        workflow,
        phase="train",
        report=report,
        policy=policy,
        expected=expected,
        weak_correct=weak_correct,
    )
    sample = workflow.sample_train()
    maintainer_input = (
        workspace.engine.target_roots["runs"] / "1/maintainer-input.json"
    ).read_bytes()
    span_trace = sample[0]
    workflow.apply_wiki(
        json.dumps(
            _maintainer_payload(
                maintainer_input=maintainer_input,
                span_task=span_trace.task_id,
                span=span_trace.content,
            )
        )
    )
    context = workflow.proposer_context()
    workflow.apply_proposal(
        json.dumps(
            _proposal_payload(
                context=context,
                trace_ids=[
                    row["task_id"] for row in answer_rows if row["split"] == "train"
                ],
            )
        )
    )
    for phase in ("val", "val_confirm"):
        _record_phase(
            workflow,
            phase=phase,
            report=report,
            policy=policy,
            expected=expected,
            weak_correct=weak_correct,
        )
        workflow.gate()

    run = EvalRun(
        run_id=run_id,
        phase_scores={
            "baseline": _manifest_scores(workspace, phase="baseline", iteration=0),
            "validation": _manifest_scores(workspace, phase="val", iteration=1),
            "confirmation": _manifest_scores(
                workspace, phase="val_confirm", iteration=1
            ),
        },
    )
    return build_eval_report(
        domain_id=domain_id,
        runs=(run,),
        trace_fidelity=report.trace_fidelity.value,
        isolation_label="scripted-offline-fixture",
        seed=seed,
    )
