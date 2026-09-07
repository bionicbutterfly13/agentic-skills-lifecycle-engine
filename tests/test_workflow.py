from __future__ import annotations

import json
from pathlib import Path

import pytest

from asme.adapter import ProviderPolicy
from asme.canonical import ContractError, canonical_bytes, sha256_bytes
from asme.cartridge import DomainCartridge
from asme.contract import CapabilityReport, LifecycleState
from asme.evidence import captured_execution
from asme.workflow import EvolutionWorkflow
from asme.workspace import DomainWorkspace, WorkspaceLayout


def _cartridge(tmp_path: Path, declared_domain) -> DomainCartridge:
    prompt = tmp_path / "prompt.txt"
    extractor = tmp_path / "extractor"
    scorer = tmp_path / "scorer"
    prompt.write_text("Solve this task: {input}\n{active_skills}", encoding="utf-8")
    extractor.write_text(
        "#!/usr/bin/env python3\n"
        "import json,sys\n"
        "p=json.load(sys.stdin)\n"
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
    # The fixture domain was sealed with these exact bytes.
    return DomainCartridge.from_paths(
        domain=declared_domain,
        prompt=prompt,
        extractor=extractor,
        scorer=scorer,
        read_resources={},
    )


def _capture(prepared, report: CapabilityReport, output: str):
    return captured_execution(
        execution_id=f"execution-{prepared.task_id}",
        runtime_id=report.runtime_id,
        runtime_version=report.runtime_version,
        adapter_version=report.adapter_version,
        job_spec_hash=prepared.job.digest,
        prompt_hash=prepared.job.role_spec.input_payload["expected_capture_schema"][
            "prompt_hash"
        ],
        active_snapshot_hash=prepared.snapshot_hash,
        started="2026-08-31T00:00:00+00:00",
        finished="2026-08-31T00:00:01+00:00",
        termination="completed",
        events=({"kind": "final_answer", "text": output},),
        returned_output=output,
        capability=report,
    )


def test_record_execution_rejects_tampered_prepared_job_record(
    tmp_path: Path, declared_domain
) -> None:
    cartridge = DomainCartridge.from_paths(
        domain=declared_domain,
        prompt=tmp_path / "prompt.txt",
        extractor=tmp_path / "extractor",
        scorer=tmp_path / "scorer",
        read_resources={},
    )
    workspace = DomainWorkspace(
        domain_id=declared_domain.domain_id,
        layout=WorkspaceLayout.under(tmp_path / "workspace"),
    )
    workspace.initialize(domain=declared_domain, max_iterations=1, cartridge=cartridge)
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
    prepared = workflow.prepare_rollout(
        phase="baseline",
        capability=report,
        provider_policy=ProviderPolicy(("openai-codex",), ("gpt-test",)),
    )[0]
    job_path = (
        workspace.engine.target_roots["runs"]
        / "0/baseline/validation-1.job.json"
    )
    job_record = json.loads(job_path.read_text(encoding="utf-8"))
    job_record["job"]["correlation_id"] = "tampered-correlation"
    job_path.write_bytes(canonical_bytes(job_record))

    with pytest.raises(ContractError, match="prepared job digest"):
        workflow.record_execution(
            phase="baseline",
            task_id="validation-1",
            execution=_capture(prepared, report, "wrong"),
        )
    assert not (
        workspace.engine.target_roots["runs"]
        / "0/baseline/validation-1.execution.json"
    ).exists()


@pytest.mark.parametrize(
    "route", ("complete", "reset-corrupt-train", "reset-invalid-train")
)
def test_real_core_baseline_train_and_sample_path(
    tmp_path: Path, declared_domain, route: str
) -> None:
    # Re-seal the domain around executable arithmetic fixtures used by this test.
    prompt = tmp_path / "prompt.txt"
    extractor = tmp_path / "extractor"
    scorer = tmp_path / "scorer"
    prompt.write_text("Solve this task: {input}\n{active_skills}", encoding="utf-8")
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
    from asme.domain import load_declared_domain

    domain = load_declared_domain(
        domain_id=declared_domain.domain_id,
        task_file=tmp_path / "tasks.jsonl",
        answer_file=tmp_path / "answers.jsonl",
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

    baseline = workflow.prepare_rollout(
        phase="baseline", capability=report, provider_policy=policy
    )
    assert [item.task_id for item in baseline] == ["validation-1"]
    assert "expected" not in baseline[0].job.role_spec.input_payload
    workflow.record_execution(
        phase="baseline",
        task_id="validation-1",
        execution=_capture(baseline[0], report, "wrong"),
    )
    baseline_manifest = workflow.ingest_rollout(phase="baseline")
    assert baseline_manifest.valid and baseline_manifest.aggregate_score == 0.0
    finalized = workflow.finalize_baseline()
    assert finalized.state is LifecycleState.NEEDS_TRAIN_RUN

    train = workflow.prepare_rollout(
        phase="train", capability=report, provider_policy=policy
    )
    assert [item.task_id for item in train] == ["train-1"]
    workflow.record_execution(
        phase="train",
        task_id="train-1",
        execution=_capture(
            train[0], report, "MALFORMED" if route == "reset-invalid-train" else "1"
        ),
    )
    train_manifest = workflow.ingest_rollout(phase="train")
    if route == "reset-invalid-train":
        assert not train_manifest.valid and train_manifest.aggregate_score is None
        assert workspace.status().state is LifecycleState.NEEDS_TRAIN_RUN
    else:
        assert train_manifest.valid and train_manifest.aggregate_score == 1.0
        assert workspace.status().state is LifecycleState.NEEDS_WIKI
    if route in {"reset-corrupt-train", "reset-invalid-train"}:
        train_dir = workspace.engine.target_roots["runs"] / "1/train"
        if route == "reset-corrupt-train":
            (train_dir / "manifest.json").write_bytes(b"{broken\n")
        reset = workflow.reset_manifest()
        assert reset.state is LifecycleState.NEEDS_TRAIN_RUN
        assert not (train_dir / "manifest.json").exists()
        assert not list(train_dir.glob("*.sidecar.json"))
        original = "MALFORMED" if route == "reset-invalid-train" else "1"
        assert (train_dir / "train-1.out.md").read_text(encoding="utf-8") == original
        assert not (train_dir / "train-1.execution.json").exists()
        raw_trace_dir = workspace.engine.target_roots["raw"] / "traces/1"
        assert not raw_trace_dir.exists() or not any(raw_trace_dir.iterdir())
        assert not (workspace.engine.target_roots["raw"] / "aliases/train-1").exists()
        corrected = workflow.prepare_rollout(
            phase="train", capability=report, provider_policy=policy
        )
        workflow.record_execution(
            phase="train",
            task_id="train-1",
            execution=_capture(corrected[0], report, "1"),
        )
        corrected_manifest = workflow.ingest_rollout(phase="train")
        assert corrected_manifest.valid and corrected_manifest.aggregate_score == 1.0
        assert (train_dir / "train-1.out.md").read_text(encoding="utf-8") == "1"
        assert workspace.status().state is LifecycleState.NEEDS_WIKI
    sample = workflow.sample_train()
    assert len(sample) == 1 and sample[0].task_id == "train-1" and sample[0].passed
    maintainer_input = (
        workspace.engine.target_roots["runs"] / "1/maintainer-input.json"
    )
    assert maintainer_input.is_file()

    pattern = "\n".join(
        (
            "pattern_kind: success",
            "",
            "## Description",
            "Return the exact requested value.",
            "## Root cause",
            "The successful trace followed the task constraint.",
            "## Evidence",
            '- pass train-1: "1"',
            "## Solution",
            "Preserve the task constraint and return only its value.",
        )
    )
    maintainer_output = {
        "create_patterns": {"exact-value": pattern},
        "update_patterns": {},
        "update_index": "# Pattern index\n\n- exact-value\n",
        "append_log": "iteration 1: added exact-value",
        "attestation": {
            "input_hash": sha256_bytes(maintainer_input.read_bytes()),
            "class_coverage": {"success": {"represented_by": ["exact-value"]}},
            "per_pattern": {
                "exact-value": {
                    "pattern_kind": "success",
                    "failure_traces": {
                        "not_applicable": "No failing traces were sampled."
                    },
                    "success_traces": ["train-1"],
                    "quoted_commands": [
                        {"trace": "train-1", "outcome": "pass", "span": "1"}
                    ],
                    "dedup_disposition": "new",
                    "dedup_reason": "No prior pattern pages exist.",
                    "root_cause_reason": "The trace directly demonstrates the constraint.",
                    "generalizable_because": "Exact-value tasks share this output rule.",
                }
            },
        },
    }
    wiki_state = workflow.apply_wiki(json.dumps(maintainer_output))
    assert wiki_state.state is LifecycleState.NEEDS_PROPOSAL
    assert (
        workspace.engine.target_roots["wiki"] / "patterns/exact-value.md"
    ).read_text(encoding="utf-8") == pattern

    proposer_context = workflow.proposer_context()
    proposal = {
        "action": "no_action",
        "context_hash": sha256_bytes(proposer_context),
        "reason": "The train trace already passes and no skill change is justified.",
        "trace_ids": ["train-1"],
    }
    done = workflow.apply_proposal(json.dumps(proposal))
    assert done.state is LifecycleState.DONE
    impact = json.loads(
        (workspace.engine.target_roots["impact"] / "history.json").read_text(
            encoding="utf-8"
        )
    )
    assert impact["entries"][0]["outcome"] == "NoAction"
