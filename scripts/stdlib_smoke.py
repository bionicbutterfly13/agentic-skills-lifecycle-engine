#!/usr/bin/env python3
"""Run a bounded no-network baseline to DONE using only the Python standard library."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PACKAGE_ROOT / "src"))

from asme.adapter import ProviderPolicy
from asme.canonical import canonical_bytes
from asme.cartridge import DomainCartridge
from asme.contract import CapabilityReport, LifecycleState
from asme.domain import load_declared_domain
from asme.evidence import captured_execution
from asme.workflow import EvolutionWorkflow
from asme.workspace import DomainWorkspace, WorkspaceLayout


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="asme-smoke-") as temporary:
        root = Path(temporary)
        tasks = root / "tasks.jsonl"
        answers = root / "answers.jsonl"
        prompt = root / "prompt.txt"
        _write_jsonl(
            tasks,
            [
                {"task_id": "train-1", "input": "Return one."},
                {"task_id": "validation-1", "input": "Return two."},
                {"task_id": "test-1", "input": "Return three."},
            ],
        )
        _write_jsonl(
            answers,
            [
                {
                    "task_id": "train-1",
                    "split": "train",
                    "expected": "1",
                    "marker": "smoke-marker-train",
                },
                {
                    "task_id": "validation-1",
                    "split": "validation",
                    "expected": "2",
                    "marker": "smoke-marker-validation",
                },
                {
                    "task_id": "test-1",
                    "split": "test",
                    "expected": "3",
                    "marker": "smoke-marker-test",
                },
            ],
        )
        prompt.write_text("{input}\n{active_skills}", encoding="utf-8")
        extractor = _PACKAGE_ROOT / "scripts/extractors/answer_tag.py"
        scorer = _PACKAGE_ROOT / "scripts/scorers/exact_match.py"
        domain = load_declared_domain(
            domain_id="stdlib-smoke",
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
            layout=WorkspaceLayout.under(root / "workspace"),
        )
        workspace.initialize(domain=domain, max_iterations=1, cartridge=cartridge)
        workspace.apply(operation="skip-seed")
        workflow = EvolutionWorkflow(workspace)
        report = CapabilityReport.conservative(
            runtime_id="stdlib-smoke-runtime",
            runtime_version="1.0.0",
            adapter_version="1.0.0",
            provider="openai-smoke",
            model_id="gpt-smoke",
            openai_backed=True,
            captured_events=("final_answer",),
        )
        policy = ProviderPolicy(("openai-smoke",), ("gpt-smoke",))
        prepared = workflow.prepare_rollout(
            phase="baseline", capability=report, provider_policy=policy
        )[0]
        output = "<answer>2</answer>"
        execution = captured_execution(
            execution_id="stdlib-smoke-execution",
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
        workflow.record_execution(
            phase="baseline", task_id=prepared.task_id, execution=execution
        )
        manifest = workflow.ingest_rollout(phase="baseline")
        if not manifest.valid:
            raise RuntimeError(
                "stdlib smoke baseline evidence is invalid: "
                + ", ".join(manifest.errors)
            )
        state = workflow.finalize_baseline()
        if state.state is not LifecycleState.DONE or manifest.aggregate_score != 1.0:
            raise RuntimeError("stdlib smoke did not reach DONE with a valid baseline")
        print(
            canonical_bytes(
                {
                    "domain_id": domain.domain_id,
                    "phase": state.state.value,
                    "score": state.best_score,
                    "trace_fidelity": report.trace_fidelity.value,
                    "isolation": "unsandboxed",
                    "network_used": False,
                }
            ).decode("utf-8"),
            end="",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
