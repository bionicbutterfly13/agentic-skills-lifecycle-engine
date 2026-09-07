from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from asme.adapter import ProviderPolicy
from asme.canonical import sha256_bytes
from asme.cartridge import DomainCartridge
from asme.contract import (
    ApprovalRecord,
    CapabilityReport,
    LifecycleState,
    Route,
)
from asme.delivery import DeliveryWorkflow
from asme.domain import load_declared_domain
from asme.evidence import captured_execution
from asme.lifecycle import TransitionRefused
from asme.package import (
    Compatibility,
    build_archive,
    build_projection_from_files,
)
from asme.snapshot import Snapshot
from asme.workflow import EvolutionWorkflow
from asme.workspace import DomainWorkspace, WorkspaceLayout


_SCORES = {0.25: 1, 0.5: 2, 0.75: 3, 1.0: 4}
_RECORDED_AT = datetime(2026, 8, 31, tzinfo=timezone.utc)
_ATTRIBUTION = (
    {
        "title": "WikiSkill",
        "arxiv_id": "2608.27454v1",
        "license": "CC BY 4.0",
        "adaptation": "independent implementation",
    },
)


class TerminalHarness:
    def __init__(self, root: Path, *, case_id: str, max_iterations: int) -> None:
        self.root = root
        self.attempts: dict[str, int] = {}
        tasks = root / "tasks.jsonl"
        answers = root / "answers.jsonl"
        task_rows: list[dict[str, str]] = []
        answer_rows: list[dict[str, str]] = []
        for split, prefix in (
            ("train", "train"),
            ("validation", "validation"),
            ("test", "test"),
        ):
            for index in range(1, 5):
                task_id = f"{prefix}-{index}"
                task_rows.append({"task_id": task_id, "input": f"input {task_id}"})
                answer_rows.append(
                    {
                        "task_id": task_id,
                        "split": split,
                        "expected": f"answer-{task_id}",
                        "marker": f"marker-{task_id}",
                    }
                )
        tasks.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in task_rows),
            encoding="utf-8",
        )
        answers.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in answer_rows),
            encoding="utf-8",
        )
        prompt = root / "prompt.txt"
        prompt.write_text("Solve {input}\n{active_skills}", encoding="utf-8")
        package_root = Path(__file__).parents[1]
        extractor = package_root / "scripts" / "extractors" / "answer_tag.py"
        scorer = package_root / "scripts" / "scorers" / "exact_match.py"
        domain = load_declared_domain(
            domain_id=f"terminal-{case_id.lower()}",
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
        self.workspace = DomainWorkspace(
            domain_id=domain.domain_id,
            layout=WorkspaceLayout.under(root / "workspace"),
        )
        self.workspace.initialize(
            domain=domain,
            max_iterations=max_iterations,
            cartridge=cartridge,
        )
        self.workspace.apply(operation="skip-seed")
        self.workflow = EvolutionWorkflow(self.workspace)
        self.report = CapabilityReport.conservative(
            runtime_id="terminal-runtime",
            runtime_version="1.0.0",
            adapter_version="1.0.0",
            provider="openai-terminal",
            model_id="gpt-terminal",
            openai_backed=True,
            captured_events=("final_answer",),
        )
        self.policy = ProviderPolicy(("openai-terminal",), ("gpt-terminal",))
        self.answers = domain.answer_map()

    def run_phase(self, phase: str, score: float, *, invalid: bool = False):
        correct = _SCORES[score]
        prepared = self.workflow.prepare_rollout(
            phase=phase,
            capability=self.report,
            provider_policy=self.policy,
        )
        attempt = self.attempts.get(phase, 0) + 1
        self.attempts[phase] = attempt
        for index, item in enumerate(prepared, 1):
            expected = str(self.answers[item.task_id].expected)
            if invalid and index == 1:
                output = "MALFORMED"
            elif index <= correct:
                output = f"<answer>{expected}</answer>"
            else:
                output = f"<answer>wrong-{phase}-{attempt}-{index}</answer>"
            execution = captured_execution(
                execution_id=f"{phase}-{attempt}-{item.task_id}",
                runtime_id=self.report.runtime_id,
                runtime_version=self.report.runtime_version,
                adapter_version=self.report.adapter_version,
                job_spec_hash=item.job.digest,
                prompt_hash=item.prompt_hash,
                active_snapshot_hash=item.snapshot_hash,
                started="2026-08-31T00:00:00+00:00",
                finished="2026-08-31T00:00:01+00:00",
                termination="completed",
                events=({"kind": "final_answer", "text": output},),
                returned_output=output,
                capability=self.report,
            )
            self.workflow.record_execution(
                phase=phase,
                task_id=item.task_id,
                execution=execution,
            )
        return self.workflow.ingest_rollout(phase=phase)

    def run_with_reset(self, phase: str, score: float):
        invalid = self.run_phase(phase, score, invalid=True)
        assert not invalid.valid and invalid.aggregate_score is None
        self.workflow.reset_manifest()
        corrected = self.run_phase(phase, score)
        assert corrected.valid and corrected.aggregate_score == score
        return corrected

    def baseline(self, score: float, *, reset: bool = False) -> None:
        manifest = (
            self.run_with_reset("baseline", score)
            if reset
            else self.run_phase("baseline", score)
        )
        assert manifest.valid and manifest.aggregate_score == score
        self.workflow.finalize_baseline()

    def proposal(self, action: str, *, test_label: str = "passed") -> None:
        train = self.run_phase("train", 1.0)
        assert train.valid and train.aggregate_score == 1.0
        self.workflow.sample_train()
        state = self.workspace.status()
        iteration = state.iteration
        pattern_name = f"pattern-{iteration}"
        maintainer_input = (
            self.workspace.engine.target_roots["runs"]
            / str(iteration)
            / "maintainer-input.json"
        )
        pattern = "\n".join(
            (
                "pattern_kind: success",
                "",
                "## Description",
                "Return the declared concise answer.",
                "## Root cause",
                "The successful trace follows the exact output contract.",
                "## Evidence",
                '- pass train-1: "<answer>answer-train-1</answer>"',
                "## Solution",
                "Keep the response constrained to the declared answer.",
            )
        )
        existing = self.workspace.engine.target_roots["wiki"] / "patterns"
        names = sorted(
            [path.stem for path in existing.glob("*.md")] + [pattern_name]
        )
        self.workflow.apply_wiki(
            json.dumps(
                {
                    "create_patterns": {pattern_name: pattern},
                    "update_patterns": {},
                    "update_index": "# Pattern index\n\n"
                    + "".join(f"- {name}\n" for name in names),
                    "append_log": f"iteration {iteration}: added {pattern_name}",
                    "attestation": {
                        "input_hash": sha256_bytes(maintainer_input.read_bytes()),
                        "class_coverage": {
                            "success": {"represented_by": [pattern_name]}
                        },
                        "per_pattern": {
                            pattern_name: {
                                "pattern_kind": "success",
                                "failure_traces": {
                                    "not_applicable": "No failing traces were sampled."
                                },
                                "success_traces": ["train-1"],
                                "quoted_commands": [
                                    {
                                        "trace": "train-1",
                                        "outcome": "pass",
                                        "span": "<answer>answer-train-1</answer>",
                                    }
                                ],
                                "dedup_disposition": "new",
                                "dedup_reason": "This iteration adds a distinct record.",
                                "root_cause_reason": "The cited trace demonstrates the rule.",
                                "generalizable_because": "The format applies across tasks.",
                            }
                        },
                    },
                }
            )
        )
        context = self.workflow.proposer_context()
        base = {
            "action": action,
            "context_hash": sha256_bytes(context),
            "reason": "The declared train evidence supports this bounded decision.",
            "trace_ids": [f"train-{index}" for index in range(1, 5)],
        }
        if action == "create":
            base.update(
                {
                    "skill_name": "terminal-skill",
                    "files": {
                        "SKILL.md": (
                            "---\n"
                            "name: terminal-skill\n"
                            "description: Return exact bounded output. Use when repeated text tasks require verified concise responses and explicit limits.\n"
                            "version: 0.1.0\n"
                            "last_updated: 2026-08-31\n"
                            "---\n\n"
                            "# Terminal skill\n\n"
                            "Return exact output.\n\n"
                            "## Triggers\n\n"
                            "1. Repeated text tasks require verified concise responses.\n"
                            "2. A bounded response procedure needs explicit limits.\n"
                        ),
                        "README.md": (
                            f"test_evaluation: {test_label}\n"
                            "trace_fidelity: final_only\n"
                            "isolation: unsandboxed\n"
                        ),
                        "PURPOSE.md": (
                            f"test_evaluation: {test_label}\n"
                            "trace_fidelity: final_only\n"
                            "isolation: unsandboxed\n"
                        ),
                    },
                }
            )
        elif action == "patch":
            base.update(
                {
                    "skill_name": "terminal-skill",
                    "patches": [
                        {
                            "path": "SKILL.md",
                            "target": "Return exact output.",
                            "replacement": "Return exact output with no extra text.",
                        }
                    ],
                }
            )
        else:
            base["trace_ids"] = ["train-1"]
        self.workflow.apply_proposal(json.dumps(base))

    def reject(self, score: float) -> None:
        self.run_phase("val", score)
        self.workflow.gate()

    def accept(self, validation: float, confirmation: float) -> None:
        self.run_phase("val", validation)
        self.workflow.gate()
        self.run_phase("val_confirm", confirmation)
        self.workflow.gate()

    def last_outcome(self) -> str:
        raw = json.loads(
            (self.workspace.engine.target_roots["impact"] / "history.json").read_text(
                encoding="utf-8"
            )
        )
        return str(raw["entries"][-1]["outcome"])

    def compatibility(self) -> Compatibility:
        return Compatibility(
            contract_version="asme.contract.v1",
            core_version="0.1.0",
            package_version="0.1.0",
            adapter_id=self.report.runtime_id,
            adapter_version=self.report.adapter_version,
            runtime_min_tested=self.report.runtime_version,
            runtime_max_tested=self.report.runtime_version,
            runtime_tested=(self.report.runtime_version,),
        )

    def stage_validated(self) -> None:
        result = DeliveryWorkflow(self.workspace).stage_skill(
            skill_name="terminal-skill",
            compatibility=self.compatibility(),
            source_attribution=_ATTRIBUTION,
            recorded_at=_RECORDED_AT,
            forbidden_live_roots=(self.root / "live",),
            capability=self.report,
        )
        assert result.state.validated_step == "exported"

    def stage_untested(self) -> None:
        state = self.workspace.status()
        snapshot_root = (
            self.workspace.engine.target_roots["snapshots"]
            / str(state.active_snapshot_hash)
        )
        snapshot = Snapshot.from_directory(snapshot_root)
        prefix = "terminal-skill/"
        files = {
            item.path.removeprefix(prefix): item.content
            for item in snapshot.files
            if item.path.startswith(prefix)
        }
        projection = build_projection_from_files(
            files=files,
            compatibility=self.compatibility(),
            source_attribution=_ATTRIBUTION,
            status="staged_candidate_untested_not_installed",
            license_policy="resolved_mit_ccby4_distribution_gate4_blocked",
        )
        archive = build_archive(projection, recorded_at=_RECORDED_AT)
        staging_id = f"{self.workspace.domain_id[:100]}__{snapshot.snapshot_hash[:12]}"
        now = datetime.now(timezone.utc)
        approval = ApprovalRecord(
            approval_id=f"approval-{self.workspace.domain_id}",
            phase="package-untested",
            artifact_hashes={
                "projection": projection.tree_sha256,
                "archive": sha256_bytes(archive),
            },
            runtime_id=None,
            destination=staging_id,
            approved_at=(now - timedelta(minutes=1)).isoformat(),
            expires_at=(now + timedelta(hours=1)).isoformat(),
            approver="test-owner",
        )
        DeliveryWorkflow(self.workspace).stage_skill(
            skill_name="terminal-skill",
            compatibility=self.compatibility(),
            source_attribution=_ATTRIBUTION,
            recorded_at=_RECORDED_AT,
            forbidden_live_roots=(self.root / "live",),
            capability=self.report,
            untested=True,
            approval=approval,
        )


def _run_terminal_case(case_id: str, root: Path) -> TerminalHarness:
    max_iterations = 1 if case_id in {f"P{index}" for index in range(1, 7)} | {
        "P12",
        "P13",
        "P14",
        "P20",
        "P21",
        "P22",
        "P23",
    } else 2
    harness = TerminalHarness(root, case_id=case_id, max_iterations=max_iterations)
    if case_id == "P1":
        harness.baseline(1.0)
    elif case_id == "P2":
        harness.baseline(1.0, reset=True)
    else:
        harness.baseline(0.25)
    if case_id in {"P1", "P2"}:
        return harness
    if case_id == "P3":
        harness.proposal("no_action")
    elif case_id == "P4":
        harness.proposal("create")
        harness.reject(0.25)
        assert harness.last_outcome() == "Rejected"
    elif case_id == "P5":
        harness.proposal("create")
        harness.accept(0.5, 0.25)
        assert harness.last_outcome() == "RejectedAfterConfirm"
    elif case_id in {"P6", "P7"}:
        harness.proposal("create")
        score = 0.5 if case_id == "P6" else 1.0
        harness.accept(score, score)
        assert harness.last_outcome() == "Accepted"
    elif case_id == "P8":
        harness.proposal("create")
        harness.workflow.abandon_candidate()
        harness.proposal("no_action")
    elif case_id == "P9":
        harness.proposal("create")
        harness.run_phase("val", 0.5)
        harness.workflow.gate()
        harness.workflow.abandon_candidate()
        harness.proposal("no_action")
    elif case_id == "P10":
        harness.proposal("create")
        harness.run_phase("val", 0.5)
        harness.workflow.abandon_candidate()
        harness.proposal("no_action")
    elif case_id == "P11":
        harness.proposal("create")
        harness.run_phase("val", 0.5)
        harness.workflow.gate()
        harness.run_phase("val_confirm", 0.5)
        harness.workflow.abandon_candidate()
        harness.proposal("no_action")
    elif case_id == "P12":
        harness.run_with_reset("train", 1.0)
        harness.workflow.sample_train()
        # Reuse the normal proposal helper after returning to the train phase would rerun
        # train, so complete the already-ingested train through its role outputs here.
        state = harness.workspace.status()
        assert state.state is LifecycleState.NEEDS_WIKI
        _finish_existing_train_no_action(harness)
    elif case_id in {"P13", "P14"}:
        harness.proposal("create")
        harness.run_with_reset("val", 0.5)
        harness.workflow.gate()
        if case_id == "P14":
            harness.run_with_reset("val_confirm", 0.5)
        else:
            harness.run_phase("val_confirm", 0.5)
        harness.workflow.gate()
    elif case_id == "P15":
        harness.proposal("create")
        harness.reject(0.25)
        harness.proposal("create")
        harness.accept(0.5, 0.5)
    elif case_id in {"P16", "P17", "P18", "P19"}:
        harness.proposal("create")
        harness.accept(0.5, 0.5)
        if case_id == "P17":
            harness.proposal("no_action")
        else:
            harness.proposal("patch")
            if case_id == "P16":
                harness.reject(0.5)
            elif case_id == "P18":
                harness.accept(0.75, 0.5)
            else:
                harness.accept(0.75, 0.75)
    elif case_id in {"P20", "P21", "P22", "P23"}:
        harness.proposal("create", test_label="not_run" if case_id in {"P22", "P23"} else "passed")
        harness.accept(0.5, 0.5)
        if case_id in {"P20", "P21", "P23"}:
            for phase in ("test-baseline", "test-final"):
                if (case_id == "P20" and phase == "test-baseline") or (
                    case_id == "P21" and phase == "test-final"
                ):
                    harness.run_with_reset(phase, 1.0)
                else:
                    harness.run_phase(phase, 1.0)
        if case_id in {"P20", "P21"}:
            harness.stage_validated()
        elif case_id == "P22":
            harness.stage_untested()
        else:
            with pytest.raises(TransitionRefused):
                harness.stage_untested()
    return harness


def _finish_existing_train_no_action(self: TerminalHarness) -> None:
    self.workflow.sample_train()
    state = self.workspace.status()
    iteration = state.iteration
    maintainer_input = (
        self.workspace.engine.target_roots["runs"]
        / str(iteration)
        / "maintainer-input.json"
    )
    pattern = "\n".join(
        (
            "pattern_kind: success",
            "",
            "## Description",
            "Return the declared concise answer.",
            "## Root cause",
            "The successful trace follows the output contract.",
            "## Evidence",
            '- pass train-1: "<answer>answer-train-1</answer>"',
            "## Solution",
            "Keep the response constrained to the declared answer.",
        )
    )
    self.workflow.apply_wiki(
        json.dumps(
            {
                "create_patterns": {"pattern-1": pattern},
                "update_patterns": {},
                "update_index": "# Pattern index\n\n- pattern-1\n",
                "append_log": "iteration 1: added pattern-1",
                "attestation": {
                    "input_hash": sha256_bytes(maintainer_input.read_bytes()),
                    "class_coverage": {
                        "success": {"represented_by": ["pattern-1"]}
                    },
                    "per_pattern": {
                        "pattern-1": {
                            "pattern_kind": "success",
                            "failure_traces": {
                                "not_applicable": "No failing traces were sampled."
                            },
                            "success_traces": ["train-1"],
                            "quoted_commands": [
                                {
                                    "trace": "train-1",
                                    "outcome": "pass",
                                    "span": "<answer>answer-train-1</answer>",
                                }
                            ],
                            "dedup_disposition": "new",
                            "dedup_reason": "No prior pattern exists.",
                            "root_cause_reason": "The trace demonstrates the rule.",
                            "generalizable_because": "The format applies across tasks.",
                        }
                    },
                },
            }
        )
    )
    context = self.workflow.proposer_context()
    self.workflow.apply_proposal(
        json.dumps(
            {
                "action": "no_action",
                "context_hash": sha256_bytes(context),
                "reason": "No skill change is justified by this bounded fixture.",
                "trace_ids": ["train-1"],
            }
        )
    )


@pytest.mark.parametrize("case_id", [f"P{index}" for index in range(1, 24)])
def test_p1_p23_terminal_paths(case_id: str, tmp_path: Path) -> None:
    harness = _run_terminal_case(case_id, tmp_path)
    state = harness.workspace.status()
    assert state.state is LifecycleState.DONE
    if case_id == "P7":
        assert state.iteration == 1 and state.best_score == 1.0
    if case_id == "P19":
        assert state.best_score == 0.75
    if case_id == "P22":
        assert state.route is Route.UNTESTED
    if case_id == "P23":
        assert state.route is Route.VALIDATED
