from __future__ import annotations

import json
from pathlib import Path

import pytest

from asme.adapter import ProviderPolicy
from asme.canonical import sha256_bytes
from asme.cartridge import DomainCartridge
from asme.contract import CapabilityReport, LifecycleState
from asme.domain import load_declared_domain
from asme.evidence import captured_execution
from asme.workflow import EvolutionWorkflow
from asme.workspace import DomainWorkspace, WorkspaceLayout


def _capture(prepared, report: CapabilityReport, output: str):
    return captured_execution(
        execution_id=f"execution-{prepared.job.correlation_id}",
        runtime_id=report.runtime_id,
        runtime_version=report.runtime_version,
        adapter_version=report.adapter_version,
        job_spec_hash=prepared.job.digest,
        prompt_hash=prepared.prompt_hash,
        active_snapshot_hash=prepared.snapshot_hash,
        started="2026-08-31T00:00:00+00:00",
        finished="2026-08-31T00:00:01+00:00",
        termination="completed",
        events=({"kind": "final_answer", "text": output},),
        returned_output=output,
        capability=report,
    )


def _record_phase(
    workflow: EvolutionWorkflow,
    report: CapabilityReport,
    policy: ProviderPolicy,
    *,
    phase: str,
    outputs: dict[str, str],
):
    prepared = workflow.prepare_rollout(
        phase=phase, capability=report, provider_policy=policy
    )
    for item in prepared:
        workflow.record_execution(
            phase=phase,
            task_id=item.task_id,
            execution=_capture(item, report, outputs[item.task_id]),
        )
    return workflow.ingest_rollout(phase=phase)


@pytest.mark.parametrize(
    "route",
    (
        "accept",
        "accept-reset-test-baseline",
        "accept-reset-test-final",
        "reject",
        "reject-confirmation",
        "abandon",
    ),
)
def test_changed_candidate_requires_two_wins_and_records_terminal_impact(
    tmp_path: Path, route: str
) -> None:
    tasks = tmp_path / "tasks.jsonl"
    answers = tmp_path / "answers.jsonl"
    task_rows = [
        *(
            {"task_id": f"train-{index}", "input": f"train input {index}"}
            for index in range(1, 5)
        ),
        {"task_id": "validation-1", "input": "validation input"},
        {"task_id": "test-1", "input": "test input"},
    ]
    answer_rows = [
        *(
            {
                "task_id": f"train-{index}",
                "split": "train",
                "expected": str(index),
                "marker": f"marker-train-{index}",
            }
            for index in range(1, 5)
        ),
        {
            "task_id": "validation-1",
            "split": "validation",
            "expected": "v",
            "marker": "marker-validation",
        },
        {
            "task_id": "test-1",
            "split": "test",
            "expected": "t",
            "marker": "marker-test",
        },
    ]
    tasks.write_text(
        "".join(json.dumps(item) + "\n" for item in task_rows), encoding="utf-8"
    )
    answers.write_text(
        "".join(json.dumps(item) + "\n" for item in answer_rows), encoding="utf-8"
    )
    prompt = tmp_path / "prompt.txt"
    extractor = tmp_path / "extractor"
    scorer = tmp_path / "scorer"
    prompt.write_text("Solve: {input}\n{active_skills}", encoding="utf-8")
    extractor.write_text(
        "#!/usr/bin/env python3\n"
        "import json,sys\n"
        "p=json.load(sys.stdin)\n"
        "sys.exit(2) if p['returned_output']=='MALFORMED' else None\n"
        "print(json.dumps({'returned_output_hash':p['returned_output_hash'],'prediction':p['returned_output'].strip()}))\n",
        encoding="utf-8",
    )
    scorer.write_text(
        "#!/usr/bin/env python3\n"
        "import json,sys\n"
        "p=json.load(sys.stdin)\n"
        "print('1' if p['prediction']==p['expected'] else '0')\n",
        encoding="utf-8",
    )
    domain = load_declared_domain(
        domain_id="candidate-domain",
        task_file=tasks,
        answer_file=answers,
        prompt_file=prompt,
        extractor_file=extractor,
        scorer_file=scorer,
        tool_profile={"mode": "none"},
    )
    cartridge = DomainCartridge.from_paths(
        domain=domain,
        prompt=prompt,
        extractor=extractor,
        scorer=scorer,
        read_resources={},
    )
    workspace = DomainWorkspace(
        domain_id=domain.domain_id,
        layout=WorkspaceLayout.under(tmp_path / "workspace"),
    )
    workspace.initialize(domain=domain, max_iterations=1, cartridge=cartridge)
    workspace.apply(operation="skip-seed")
    workflow = EvolutionWorkflow(workspace)
    report = CapabilityReport.conservative(
        runtime_id="test-runtime",
        runtime_version="1.0.0",
        adapter_version="1.0.0",
        provider="openai-codex",
        model_id="gpt-test",
        openai_backed=True,
        captured_events=("final_answer",),
    )
    policy = ProviderPolicy(("openai-codex",), ("gpt-test",))

    _record_phase(
        workflow,
        report,
        policy,
        phase="baseline",
        outputs={"validation-1": "wrong"},
    )
    workflow.finalize_baseline()
    _record_phase(
        workflow,
        report,
        policy,
        phase="train",
        outputs={f"train-{index}": str(index) for index in range(1, 5)},
    )
    workflow.sample_train()
    maintainer_input = workspace.engine.target_roots["runs"] / "1/maintainer-input.json"
    pattern = "\n".join(
        (
            "pattern_kind: success",
            "",
            "## Description",
            "Return the expected concise output.",
            "## Root cause",
            "The successful trace respected the requested format.",
            "## Evidence",
            '- pass train-1: "1"',
            "## Solution",
            "Keep the response constrained to the requested output.",
        )
    )
    workflow.apply_wiki(
        json.dumps(
            {
                "create_patterns": {"concise-output": pattern},
                "update_patterns": {},
                "update_index": "# Pattern index\n\n- concise-output\n",
                "append_log": "iteration 1: added concise-output",
                "attestation": {
                    "input_hash": sha256_bytes(maintainer_input.read_bytes()),
                    "class_coverage": {
                        "success": {"represented_by": ["concise-output"]}
                    },
                    "per_pattern": {
                        "concise-output": {
                            "pattern_kind": "success",
                            "failure_traces": {
                                "not_applicable": "No failing traces were sampled."
                            },
                            "success_traces": ["train-1"],
                            "quoted_commands": [
                                {
                                    "trace": "train-1",
                                    "outcome": "pass",
                                    "span": "1",
                                }
                            ],
                            "dedup_disposition": "new",
                            "dedup_reason": "No prior pattern pages exist.",
                            "root_cause_reason": "The trace demonstrates the format rule.",
                            "generalizable_because": "The rule applies across concise outputs.",
                        }
                    },
                },
            }
        )
    )
    context = workflow.proposer_context()
    proposed = workflow.apply_proposal(
        json.dumps(
            {
                "action": "create",
                "context_hash": sha256_bytes(context),
                "reason": "Four successful train traces support a reusable constraint.",
                "trace_ids": [f"train-{index}" for index in range(1, 5)],
                "skill_name": "concise-answer",
                "files": {
                    "SKILL.md": "# Concise answer\n\nReturn only the requested value.\n"
                },
            }
        )
    )
    assert proposed.state is LifecycleState.NEEDS_VAL_RUN
    candidate_hash = proposed.candidate_snapshot_hash

    if route == "abandon":
        abandoned = workflow.abandon_candidate()
        assert abandoned.state is LifecycleState.DONE
        assert abandoned.active_snapshot_hash != candidate_hash
        impact = json.loads(
            (workspace.engine.target_roots["impact"] / "history.json").read_text(
                encoding="utf-8"
            )
        )["entries"]
        assert impact[0]["outcome"] == "Abandoned"
        assert impact[0]["scores"] == []
        return

    _record_phase(
        workflow,
        report,
        policy,
        phase="val",
        outputs={"validation-1": "wrong" if route == "reject" else "v"},
    )
    first_gate = workflow.gate()
    if route == "reject":
        assert first_gate.state is LifecycleState.DONE
        assert first_gate.active_snapshot_hash != candidate_hash
        impact = json.loads(
            (workspace.engine.target_roots["impact"] / "history.json").read_text(
                encoding="utf-8"
            )
        )["entries"]
        assert impact[0]["outcome"] == "Rejected"
        assert impact[0]["scores"] == [0.0]
        return
    assert first_gate.state is LifecycleState.NEEDS_VAL_CONFIRM
    assert not (workspace.engine.target_roots["impact"] / "history.json").exists()

    _record_phase(
        workflow,
        report,
        policy,
        phase="val_confirm",
        outputs={
            "validation-1": "wrong" if route == "reject-confirmation" else "v"
        },
    )
    accepted = workflow.gate()
    if route == "reject-confirmation":
        assert accepted.state is LifecycleState.DONE
        assert accepted.active_snapshot_hash != candidate_hash
        impact = json.loads(
            (workspace.engine.target_roots["impact"] / "history.json").read_text(
                encoding="utf-8"
            )
        )["entries"]
        assert impact[0]["outcome"] == "RejectedAfterConfirm"
        assert impact[0]["scores"] == [1.0, 0.0]
        return
    assert accepted.state is LifecycleState.DONE
    assert accepted.active_snapshot_hash == candidate_hash
    assert accepted.best_score == 1.0
    impact = json.loads(
        (workspace.engine.target_roots["impact"] / "history.json").read_text(
            encoding="utf-8"
        )
    )["entries"]
    assert impact[0]["outcome"] == "Accepted"
    assert impact[0]["scores"] == [1.0, 1.0]

    invalid_phase = {
        "accept-reset-test-baseline": "test-baseline",
        "accept-reset-test-final": "test-final",
    }.get(route)
    for phase in ("test-baseline", "test-final"):
        manifest = _record_phase(
            workflow,
            report,
            policy,
            phase=phase,
            outputs={"test-1": "MALFORMED" if phase == invalid_phase else "t"},
        )
        if phase == invalid_phase:
            assert not manifest.valid and manifest.aggregate_score is None
            reset = workflow.reset_manifest()
            assert reset.state is LifecycleState.DONE
            corrected = _record_phase(
                workflow,
                report,
                policy,
                phase=phase,
                outputs={"test-1": "t"},
            )
            assert corrected.valid and corrected.aggregate_score == 1.0
    tested = workspace.status()
    assert tested.validated_step == "ingested"
    assert {item["phase"] for item in tested.test_manifests} == {
        "test-baseline",
        "test-final",
    }
