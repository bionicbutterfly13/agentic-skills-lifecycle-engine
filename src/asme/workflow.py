"""Runtime-neutral rollout preparation, capture ingestion, and sampling workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import difflib
import json
from pathlib import Path
from typing import Any, Mapping

from .adapter import AdapterJob, ProviderPolicy, adapter_job_from_mapping, prepare_job
from .canonical import (
    ContractError,
    canonical_bytes,
    hash_json,
    require_identifier,
    require_regular_file,
    sha256_bytes,
    sha256_file,
    tree_manifest,
)
from .contract import (
    CapabilityReport,
    CapturedExecution,
    ApprovalRecord,
    IsolationLevel,
    LifecycleState,
    Role,
    TraceFidelity,
)
from .evaluation import EvaluationResult, evaluate_output
from .evidence import proposer_payload, role_spec, rollout_payload
from .impact import ImpactEntry, ImpactOutcome, append_impact, create_impact
from .integration import build_observation_candidate
from .lifecycle import DomainState, TransitionInput, TransitionRefused, transition
from .manifest import (
    RolloutManifest,
    build_rollout_manifest,
    rollout_manifest_from_mapping,
)
from .proposal import ValidatedProposal, validate_proposal
from .seed import SEED_SCHEMA, validate_seed_packet
from .snapshot import Snapshot, snapshot_material, snapshot_write_plan, verify_snapshot
from .transaction import (
    PlannedDeletion,
    PlannedRead,
    PlannedTreeRead,
    PlannedValue,
    PlannedWrite,
)
from .wiki import TraceView, sample_traces, validate_maintainer_change, validate_role_json
from .workspace import DomainWorkspace


RUN_SCHEMA = "asme.run.v1"
JOB_SCHEMA = "asme.job.v1"
IMPACT_SCHEMA = "asme.impact-history.v1"
CANDIDATE_SCHEMA = "asme.candidate.v1"
SEED_MANIFEST_SCHEMA = "asme.seed-manifest.v1"


@dataclass(frozen=True)
class PreparedTask:
    task_id: str
    prompt: str
    prompt_hash: str
    snapshot_hash: str
    job: AdapterJob


class EvolutionWorkflow:
    """Drive paper-method artifacts without owning runtime dispatch."""

    def __init__(self, workspace: DomainWorkspace) -> None:
        self.workspace = workspace

    def seed_observations(
        self,
        seed_packet: bytes,
        *,
        approval: ApprovalRecord,
        now: datetime | None = None,
    ) -> DomainState:
        """Apply only a human-named seed packet; never read Task Observer state."""

        state = self.workspace.status()
        if state.state is not LifecycleState.NEEDS_OPTIONAL_SEED:
            raise TransitionRefused("observation seed is refused in the current phase")
        packet_hash = sha256_bytes(seed_packet)
        approval.validate_for(
            phase="seed-observations",
            artifact_hashes={"seed_packet": packet_hash},
            runtime_id=None,
            destination=self.workspace.domain_id,
            now=now or self.workspace.clock.now(),
        )
        domain = self.workspace.recorded_domain()
        packet = validate_seed_packet(seed_packet, domain=domain)
        wiki_root = self.workspace.engine.target_roots["wiki"]
        if _read_text_tree(wiki_root):
            raise ContractError("observation seed requires an empty pre-baseline wiki")
        consumed_approval = approval.consume()
        writes: list[PlannedWrite] = [
            PlannedWrite.from_bytes(
                root="runs", path="0/seed-packet.json", content=seed_packet
            ),
            PlannedWrite.from_bytes(
                root="runs",
                path="0/seed-approval.json",
                content=canonical_bytes(asdict(consumed_approval)),
            ),
        ]
        wiki_files: dict[str, bytes] = {
            **{
                f"patterns/{name}.md": page.encode("utf-8")
                for name, page in packet.pages.items()
            },
            "index.md": packet.index.encode("utf-8"),
            "log.md": packet.log_entry.rstrip().encode("utf-8") + b"\n",
        }
        writes.extend(
            PlannedWrite.from_bytes(root="wiki", path=path, content=content)
            for path, content in sorted(wiki_files.items())
        )
        seed_manifest = {
            "schema": SEED_MANIFEST_SCHEMA,
            "seed_schema": SEED_SCHEMA,
            "domain_id": domain.domain_id,
            "packet_hash": packet_hash,
            "packet_digest": packet.digest,
            "approval_id": approval.approval_id,
            "observation_ids": packet.observation_ids,
            "wiki_files": {
                path: sha256_bytes(content) for path, content in sorted(wiki_files.items())
            },
        }
        writes.append(
            PlannedWrite.from_bytes(
                root="runs",
                path="0/seed-manifest.json",
                content=canonical_bytes(seed_manifest),
            )
        )
        return self.workspace.apply(
            operation="seed-observations",
            supplied=TransitionInput(
                approval_present=True,
                observation_ids=packet.observation_ids,
            ),
            arguments={
                "approval_id": approval.approval_id,
                "observation_ids": packet.observation_ids,
            },
            input_hashes={
                "seed_packet": packet_hash,
                "seed_packet_digest": packet.digest,
                "approval": hash_json(asdict(approval)),
            },
            writes=tuple(writes),
        )

    def observation_candidate(self, *, skill_name: str) -> Mapping[str, Any]:
        """Return a review-only reusable-signal candidate without writing any log."""

        state = self.workspace.status()
        snapshot = self._load_snapshot(str(state.active_snapshot_hash))
        history = _read_impact_history(self.workspace.engine.target_roots["impact"])
        return build_observation_candidate(
            state=state,
            snapshot=snapshot,
            skill_name=skill_name,
            impact_history=history,
        ).as_mapping()

    def rollback_seed(self) -> DomainState:
        """Remove the exact pre-baseline seed transaction before baseline consumption."""

        state = self.workspace.status()
        if (
            state.state is not LifecycleState.NEEDS_BASELINE_RUN
            or state.seed_decision != "seeded"
        ):
            raise TransitionRefused("seed rollback is refused in the current phase")
        baseline_manifest = (
            self.workspace.engine.target_roots["runs"] / "0/baseline/manifest.json"
        )
        if baseline_manifest.exists() or baseline_manifest.is_symlink():
            raise ContractError("seed rollback is refused after baseline evidence exists")
        manifest_path = require_regular_file(
            self.workspace.engine.target_roots["runs"] / "0/seed-manifest.json",
            root=self.workspace.engine.target_roots["runs"],
        )
        manifest = _read_json_object(manifest_path, label="seed manifest")
        if (
            manifest.get("schema") != SEED_MANIFEST_SCHEMA
            or manifest.get("domain_id") != self.workspace.domain_id
            or tuple(manifest.get("observation_ids", ()))
            != state.seeded_observation_ids
            or not isinstance(manifest.get("wiki_files"), Mapping)
        ):
            raise ContractError("seed manifest differs from authoritative state")
        paths = [
            self.workspace.engine.target_roots["runs"] / "0/seed-packet.json",
            self.workspace.engine.target_roots["runs"] / "0/seed-approval.json",
            manifest_path,
            *(
                self.workspace.engine.target_roots["wiki"] / path
                for path in manifest["wiki_files"]
            ),
        ]
        deletions = _existing_file_deletions(
            paths,
            roots={
                "runs": self.workspace.engine.target_roots["runs"],
                "wiki": self.workspace.engine.target_roots["wiki"],
            },
        )
        if len(deletions) != len(paths):
            raise ContractError("seed rollback artifacts are incomplete")
        for deletion in deletions:
            if deletion.root == "wiki":
                expected = manifest["wiki_files"].get(deletion.path)
                if expected != deletion.expected_sha256:
                    raise ContractError("seeded wiki content drifted before rollback")
        return self.workspace.apply(
            operation="rollback-seed",
            arguments={"observation_ids": state.seeded_observation_ids},
            input_hashes={"seed_manifest": sha256_file(manifest_path)},
            deletions=deletions,
        )

    def prepare_rollout(
        self,
        *,
        phase: str,
        capability: CapabilityReport,
        provider_policy: ProviderPolicy,
    ) -> tuple[PreparedTask, ...]:
        state = self.workspace.status()
        domain = self.workspace.recorded_domain()
        split, iteration, snapshot = self._phase_context(phase, state)
        template = self._cartridge_file("prompt.txt").read_text(encoding="utf-8")
        skills = _active_skill_text(snapshot)
        selected = sorted(
            (
                task
                for task in domain.tasks
                if domain.answer_map()[task.task_id].split == split
            ),
            key=lambda task: task.task_id,
        )
        prepared: list[PreparedTask] = []
        writes: list[PlannedWrite] = []
        run_root = _run_root(phase, iteration)
        for task in selected:
            input_text = (
                task.input
                if isinstance(task.input, str)
                else canonical_bytes(task.input).decode("utf-8")
            )
            try:
                prompt = template.format(input=input_text, active_skills=skills)
            except (KeyError, IndexError, ValueError) as exc:
                raise ContractError("prompt template has unsupported format fields") from exc
            prompt_hash = sha256_bytes(prompt.encode("utf-8"))
            payload = rollout_payload(
                task=task,
                rendered_prompt=prompt,
                active_skill=skills,
                tool_profile=domain.tool_profile,
                runtime_policy={
                    "fresh_session": True,
                    "wiki_access": "forbidden",
                    "held_out_answers": "excluded",
                    "output_kind": domain.output_kind,
                },
                expected_capture_schema={
                    "prompt_hash": prompt_hash,
                    "snapshot_hash": snapshot.snapshot_hash,
                    "required_output": "text",
                },
            )
            spec = role_spec(
                role=Role.INFERENCE,
                payload=payload,
                prompt_text=prompt,
                allowed_toolsets=("read",) if domain.tool_mode == "read" else (),
                provider_allowlist=provider_policy.providers,
                model_allowlist=provider_policy.models,
                output_schema={"type": "string"},
            )
            job = prepare_job(
                adapter_id=capability.runtime_id,
                adapter_version=capability.adapter_version,
                report=capability,
                role_spec=spec,
                policy=provider_policy,
                correlation_id=f"{phase}-{iteration}-{task.task_id}",
            )
            prepared.append(
                PreparedTask(task.task_id, prompt, prompt_hash, snapshot.snapshot_hash, job)
            )
            writes.extend(
                (
                    PlannedWrite.from_bytes(
                        root="runs",
                        path=f"{run_root}/{task.task_id}.prompt.md",
                        content=prompt.encode("utf-8"),
                        allow_existing_identical=True,
                    ),
                    PlannedWrite.from_bytes(
                        root="runs",
                        path=f"{run_root}/{task.task_id}.job.json",
                        content=canonical_bytes(
                            {
                                "schema": JOB_SCHEMA,
                                "task_id": task.task_id,
                                "job": asdict(job),
                                "job_hash": job.digest,
                                "prompt_hash": prompt_hash,
                                "snapshot_hash": snapshot.snapshot_hash,
                            }
                        ),
                        allow_existing_identical=True,
                    ),
                )
            )
        run_metadata = {
            "schema": RUN_SCHEMA,
            "phase": phase,
            "split": split,
            "iteration": iteration,
            "snapshot_hash": snapshot.snapshot_hash,
            "task_ids": [item.task_id for item in prepared],
            "capability_report_hash": capability.digest,
        }
        writes.append(
            PlannedWrite.from_bytes(
                root="runs",
                path=f"{run_root}/run.json",
                content=canonical_bytes(run_metadata),
                allow_existing_identical=True,
            )
        )
        hashes = {
            "capability_report": capability.digest,
            "snapshot": snapshot.snapshot_hash,
            "seal": domain.seal,
            "named_snapshot": snapshot.snapshot_hash,
            "run_metadata": hash_json(run_metadata),
        }
        snapshot_root = self.workspace.engine.target_roots["snapshots"] / snapshot.snapshot_hash
        snapshot_reads = (
            (
                PlannedTreeRead(
                    name="named_snapshot",
                    root="snapshots",
                    path=snapshot.snapshot_hash,
                    expected_sha256=hash_json(tree_manifest(snapshot_root)),
                ),
            )
            if snapshot_root.is_dir() and not snapshot_root.is_symlink()
            else ()
        )
        if phase in {"test-baseline", "test-final"}:
            self.workspace.apply(
                operation="test-prepare",
                supplied=TransitionInput(phase=phase),
                arguments={"phase": phase, "iteration": iteration},
                input_hashes=hashes,
                dependency_operation="prepare-rollout",
                tree_reads=snapshot_reads,
                values=(
                    PlannedValue.from_bytes(
                        name="named_snapshot", content=snapshot_material(snapshot)
                    ),
                ),
                writes=tuple(writes),
            )
        else:
            self.workspace.persist(
                operation="prepare-rollout",
                arguments={"phase": phase, "iteration": iteration},
                input_hashes=hashes,
                dependency_operation="prepare-rollout",
                tree_reads=snapshot_reads,
                values=(
                    PlannedValue.from_bytes(
                        name="named_snapshot", content=snapshot_material(snapshot)
                    ),
                ),
                writes=tuple(writes),
            )
        return tuple(prepared)

    def record_execution(
        self, *, phase: str, task_id: str, execution: CapturedExecution
    ) -> None:
        state = self.workspace.status()
        _, iteration, _ = self._phase_context(phase, state, allow_after_ingest=True)
        run_root = _run_root(phase, iteration)
        run_dir = self.workspace.engine.target_roots["runs"] / run_root
        job_path = require_regular_file(
            run_dir / f"{task_id}.job.json",
            root=self.workspace.engine.target_roots["runs"],
        )
        job_bytes = job_path.read_bytes()
        try:
            job = json.loads(job_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ContractError("prepared job record is malformed") from exc
        if not isinstance(job, dict) or job.get("schema") != JOB_SCHEMA:
            raise ContractError("prepared job schema is invalid")
        prepared_job = adapter_job_from_mapping(job.get("job"))
        if prepared_job.digest != job.get("job_hash"):
            raise ContractError("prepared job digest differs from its recorded hash")
        if job.get("task_id") != task_id or execution.job_spec_hash != prepared_job.digest:
            raise ContractError("captured execution is bound to another job")
        if execution.prompt_hash != job.get("prompt_hash"):
            raise ContractError("captured execution is bound to another prompt")
        if execution.active_snapshot_hash != job.get("snapshot_hash"):
            raise ContractError("captured execution is bound to another snapshot")
        if execution.capability_report_hash != prepared_job.capability_report_hash:
            raise ContractError("captured execution capability report differs from its job")
        execution_path = run_dir / f"{task_id}.execution.json"
        output_path = run_dir / f"{task_id}.out.md"
        replacing_reset_output = (
            not execution_path.exists()
            and not execution_path.is_symlink()
            and output_path.exists()
            and not output_path.is_symlink()
        )
        if replacing_reset_output and (
            not state.history or state.history[-1].get("operation") != "reset-manifest"
        ):
            raise ContractError("orphaned submitted output cannot be replaced without reset")
        output_before = sha256_file(output_path) if replacing_reset_output else None
        self.workspace.persist(
            operation="record-execution",
            arguments={"phase": phase, "iteration": iteration, "task_id": task_id},
            input_hashes={
                "prepared_job": prepared_job.digest,
                "captured_execution": hash_json(asdict(execution)),
            },
            dependency_operation="record-execution",
            values=(
                PlannedValue.from_bytes(
                    name="captured_execution",
                    content=canonical_bytes(asdict(execution)),
                ),
            ),
            reads=(
                PlannedRead(
                    name="prepared_job_record",
                    root="runs",
                    path=job_path.relative_to(
                        self.workspace.engine.target_roots["runs"]
                    ).as_posix(),
                    expected_sha256=sha256_bytes(job_bytes),
                ),
            ),
            writes=(
                PlannedWrite.from_bytes(
                    root="runs",
                    path=f"{run_root}/{task_id}.execution.json",
                    content=canonical_bytes(asdict(execution)),
                    allow_existing_identical=True,
                ),
                PlannedWrite.from_bytes(
                    root="runs",
                    path=f"{run_root}/{task_id}.out.md",
                    content=execution.returned_output.encode("utf-8"),
                    expected_before_sha256=output_before,
                    allow_existing_identical=True,
                ),
            ),
        )

    def ingest_rollout(self, *, phase: str) -> RolloutManifest:
        state = self.workspace.status()
        domain = self.workspace.recorded_domain()
        split, iteration, snapshot = self._phase_context(phase, state)
        run_root = _run_root(phase, iteration)
        run_dir = self.workspace.engine.target_roots["runs"] / run_root
        manifest_path = run_dir / "manifest.json"
        if manifest_path.exists() or manifest_path.is_symlink():
            raise ContractError("rollout manifest already exists")
        task_ids = sorted(answer.task_id for answer in domain.answers if answer.split == split)
        answers = domain.answer_map()
        prompts: dict[str, str] = {}
        executions: dict[str, CapturedExecution] = {}
        evaluations: dict[str, EvaluationResult] = {}
        sidecars: dict[str, bytes] = {}
        dependency_reads: list[PlannedRead] = []
        prompt_file_hashes: dict[str, str] = {}
        output_file_hashes: dict[str, str] = {}
        capture_file_hashes: dict[str, str] = {}
        for task_id in task_ids:
            prompt_path = require_regular_file(run_dir / f"{task_id}.prompt.md", root=run_dir)
            execution_path = require_regular_file(
                run_dir / f"{task_id}.execution.json", root=run_dir
            )
            output_path = require_regular_file(run_dir / f"{task_id}.out.md", root=run_dir)
            prompt_file_hashes[task_id] = sha256_file(prompt_path)
            capture_file_hashes[task_id] = sha256_file(execution_path)
            output_file_hashes[task_id] = sha256_file(output_path)
            dependency_reads.extend(
                (
                    PlannedRead(
                        name="prompts",
                        root="runs",
                        path=prompt_path.relative_to(
                            self.workspace.engine.target_roots["runs"]
                        ).as_posix(),
                        expected_sha256=prompt_file_hashes[task_id],
                    ),
                    PlannedRead(
                        name="submitted_outputs",
                        root="runs",
                        path=output_path.relative_to(
                            self.workspace.engine.target_roots["runs"]
                        ).as_posix(),
                        expected_sha256=output_file_hashes[task_id],
                    ),
                    PlannedRead(
                        name="submitted_outputs",
                        root="runs",
                        path=execution_path.relative_to(
                            self.workspace.engine.target_roots["runs"]
                        ).as_posix(),
                        expected_sha256=capture_file_hashes[task_id],
                    ),
                )
            )
            prompt = prompt_path.read_text(encoding="utf-8")
            execution = _execution_from_json(execution_path)
            output = output_path.read_text(encoding="utf-8")
            if output != execution.returned_output:
                raise ContractError("submitted output differs from captured execution")
            evaluation = evaluate_output(
                returned_output=output,
                expected=answers[task_id].expected,
                extractor=self._cartridge_file("extractor"),
                scorer=self._cartridge_file("scorer"),
            )
            prompts[task_id] = prompt
            executions[task_id] = execution
            evaluations[task_id] = evaluation
            sidecars[task_id] = canonical_bytes(
                {
                    "task_id": task_id,
                    "split": split,
                    "phase": phase,
                    "iteration": iteration,
                    "snapshot_hash": snapshot.snapshot_hash,
                    "prompt_hash": sha256_bytes(prompt.encode("utf-8")),
                    "output_hash": execution.returned_output_hash,
                    "prediction": evaluation.prediction,
                    "expected": answers[task_id].expected,
                    "score": evaluation.score,
                    "valid": evaluation.valid,
                    "error_class": evaluation.error_class,
                    "trace_fidelity": execution.trace_fidelity.value,
                    "capability_report_hash": execution.capability_report_hash,
                }
            )
        manifest = build_rollout_manifest(
            domain=domain,
            phase=phase,
            split=split,
            iteration=iteration,
            active_snapshot_hash=snapshot.snapshot_hash,
            prompts=prompts,
            executions=executions,
            evaluations=evaluations,
        )
        manifest_bytes = canonical_bytes(asdict(manifest))
        manifest_hash = sha256_bytes(manifest_bytes)
        if manifest_hash != manifest.digest:
            raise ContractError("manifest byte identity differs from its digest")
        writes: list[PlannedWrite] = [
            *(
                PlannedWrite.from_bytes(
                    root="runs", path=f"{run_root}/{task_id}.sidecar.json", content=sidecars[task_id]
                )
                for task_id in task_ids
            ),
            PlannedWrite.from_bytes(
                root="runs", path=f"{run_root}/manifest.json", content=manifest_bytes
            ),
        ]
        if phase == "train" and manifest.valid:
            for task_id in task_ids:
                output = executions[task_id].returned_output.encode("utf-8")
                alias_member = f"aliases/{task_id}"
                alias_path = self.workspace.engine.target_roots["raw"] / alias_member
                alias_before = (
                    sha256_file(require_regular_file(
                        alias_path,
                        root=self.workspace.engine.target_roots["raw"],
                    ))
                    if alias_path.exists() or alias_path.is_symlink()
                    else None
                )
                writes.extend(
                    (
                        PlannedWrite.from_bytes(
                            root="raw",
                            path=f"traces/{iteration}/{task_id}.md",
                            content=output,
                        ),
                        PlannedWrite.from_bytes(
                            root="raw",
                            path=f"traces/{iteration}/{task_id}.json",
                            content=sidecars[task_id],
                        ),
                        PlannedWrite.from_bytes(
                            root="raw",
                            path=alias_member,
                            content=f"traces/{iteration}/{task_id}.md\n".encode("utf-8"),
                            expected_before_sha256=alias_before,
                        ),
                    )
                )
        supplied = TransitionInput(
            valid=manifest.valid,
            score=manifest.aggregate_score,
            phase=phase,
            manifest_hash=manifest_hash,
        )
        hashes = {
            "manifest": manifest_hash,
            "seal": domain.seal,
            "prompts": hash_json(prompt_file_hashes),
            "submitted_outputs": hash_json(output_file_hashes),
            "capture_records": hash_json(capture_file_hashes),
        }
        if phase == "baseline":
            self.workspace.persist(
                operation="ingest-rollout",
                arguments={"phase": phase, "iteration": iteration},
                input_hashes=hashes,
                dependency_operation="ingest-rollout",
                reads=tuple(dependency_reads),
                writes=tuple(writes),
            )
        else:
            operation = {
                "train": "train-ingest",
                "val": "val-ingest",
                "val_confirm": "confirm-ingest",
                "test-baseline": "test-ingest",
                "test-final": "test-ingest",
            }[phase]
            self.workspace.apply(
                operation=operation,
                supplied=supplied,
                arguments={"phase": phase, "iteration": iteration},
                input_hashes=hashes,
                dependency_operation="ingest-rollout",
                reads=tuple(dependency_reads),
                writes=tuple(writes),
            )
        return manifest

    def finalize_baseline(self) -> DomainState:
        state = self.workspace.status()
        if state.state is not LifecycleState.NEEDS_BASELINE_RUN:
            raise TransitionRefused("baseline finalization is refused in the current phase")
        manifest = self._read_manifest("baseline", 0)
        if not manifest.valid or manifest.aggregate_score is None:
            raise ContractError("baseline manifest is incomplete or invalid")
        snapshot = Snapshot.empty()
        run_dir = self.workspace.engine.target_roots["runs"] / "0/baseline"
        manifest_path = require_regular_file(run_dir / "manifest.json", root=run_dir)
        sidecar_paths = sorted(run_dir.glob("*.sidecar.json"))
        sidecar_hashes = {
            path.name: sha256_file(require_regular_file(path, root=run_dir))
            for path in sidecar_paths
        }
        return self.workspace.apply(
            operation="baseline-finalize",
            supplied=TransitionInput(
                valid=True,
                score=manifest.aggregate_score,
                snapshot_hash=snapshot.snapshot_hash,
                phase="baseline",
                manifest_hash=manifest.digest,
            ),
            arguments={"phase": "baseline", "iteration": 0},
            input_hashes={
                "manifest": manifest.digest,
                "snapshot": snapshot.snapshot_hash,
                "baseline_manifest": sha256_file(manifest_path),
                "baseline_sidecars": hash_json(sidecar_hashes),
            },
            dependency_operation="baseline-finalize",
            reads=(
                PlannedRead(
                    name="baseline_manifest",
                    root="runs",
                    path="0/baseline/manifest.json",
                    expected_sha256=sha256_file(manifest_path),
                ),
                *(
                    PlannedRead(
                        name="baseline_sidecars",
                        root="runs",
                        path=path.relative_to(
                            self.workspace.engine.target_roots["runs"]
                        ).as_posix(),
                        expected_sha256=sidecar_hashes[path.name],
                    )
                    for path in sidecar_paths
                ),
            ),
        )

    def sample_train(self) -> tuple[TraceView, ...]:
        state = self.workspace.status()
        if state.state is not LifecycleState.NEEDS_WIKI or state.current_manifest_phase != "train":
            raise TransitionRefused("train sampling requires a valid unconsumed train manifest")
        manifest = self._read_manifest("train", state.iteration)
        if not manifest.valid or manifest.digest != state.current_manifest_hash:
            raise ContractError("train manifest differs from authoritative state")
        run_root = _run_root("train", state.iteration)
        run_dir = self.workspace.engine.target_roots["runs"] / run_root
        raw_root = self.workspace.engine.target_roots["raw"]
        trace_hashes: dict[str, str] = {}
        sidecar_hashes: dict[str, str] = {}
        dependency_reads: list[PlannedRead] = [
            PlannedRead(
                name="train_manifest",
                root="runs",
                path=f"{run_root}/manifest.json",
                expected_sha256=manifest.digest,
            )
        ]
        records: list[dict[str, Any]] = []
        for entry in manifest.entries:
            trace_path = require_regular_file(
                raw_root / f"traces/{state.iteration}/{entry.task_id}.md",
                root=raw_root,
            )
            sidecar_path = require_regular_file(
                raw_root / f"traces/{state.iteration}/{entry.task_id}.json",
                root=raw_root,
            )
            sidecar = _read_json_object(sidecar_path, label="raw trace sidecar")
            if (
                sidecar.get("task_id") != entry.task_id
                or sidecar.get("output_hash") != entry.returned_output_hash
                or sidecar.get("score") != entry.score
            ):
                raise ContractError("raw trace sidecar differs from train manifest")
            trace_hashes[entry.task_id] = sha256_file(trace_path)
            sidecar_hashes[entry.task_id] = sha256_file(sidecar_path)
            dependency_reads.extend(
                (
                    PlannedRead(
                        name="raw_traces",
                        root="raw",
                        path=trace_path.relative_to(raw_root).as_posix(),
                        expected_sha256=trace_hashes[entry.task_id],
                    ),
                    PlannedRead(
                        name="raw_sidecars",
                        root="raw",
                        path=sidecar_path.relative_to(raw_root).as_posix(),
                        expected_sha256=sidecar_hashes[entry.task_id],
                    ),
                )
            )
            records.append(
                {
                    "task_id": entry.task_id,
                    "passed": entry.score == 1.0,
                    "content": trace_path.read_text(encoding="utf-8"),
                    "source_hash": entry.returned_output_hash,
                }
            )
        sample = sample_traces(records)
        wiki_root = self.workspace.engine.target_roots["wiki"]
        wiki_pages = _read_text_tree(wiki_root)
        wiki_reads = (
            (
                PlannedTreeRead(
                    name="wiki",
                    root="domain",
                    path="wiki",
                    expected_sha256=hash_json(tree_manifest(wiki_root)),
                ),
            )
            if wiki_root.is_dir() and not wiki_root.is_symlink()
            else ()
        )
        payload = {
            "source_class": "ARCHITECTURE",
            "ordering": "task_id_sorted_local_rule",
            "limits": {"failures": 5, "passes": 3, "characters_per_view": 15000},
            "traces": [asdict(item) for item in sample],
            "wiki_pages": wiki_pages,
        }
        content = canonical_bytes(payload)
        self.workspace.persist(
            operation="sample",
            arguments={"phase": "train", "iteration": state.iteration},
            input_hashes={
                "train_manifest": manifest.digest,
                "raw_traces": hash_json(trace_hashes),
                "raw_sidecars": hash_json(sidecar_hashes),
                "wiki": hash_json(wiki_pages),
            },
            dependency_operation="sample",
            reads=tuple(dependency_reads),
            tree_reads=wiki_reads,
            values=(
                PlannedValue.from_bytes(
                    name="wiki", content=canonical_bytes(wiki_pages)
                ),
            ),
            writes=(
                PlannedWrite.from_bytes(
                    root="runs",
                    path=f"{state.iteration}/maintainer-input.json",
                    content=content,
                    allow_existing_identical=True,
                ),
            ),
        )
        return sample

    def apply_wiki(self, maintainer_output: str) -> DomainState:
        """Validate and atomically apply one Wiki Maintainer result."""

        state = self.workspace.status()
        if state.state is not LifecycleState.NEEDS_WIKI:
            raise TransitionRefused("wiki application is refused in the current phase")
        input_path = require_regular_file(
            self.workspace.engine.target_roots["runs"]
            / str(state.iteration)
            / "maintainer-input.json",
            root=self.workspace.engine.target_roots["runs"],
        )
        input_bytes = input_path.read_bytes()
        try:
            source = json.loads(input_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ContractError("maintainer input is malformed") from exc
        if not isinstance(source, Mapping) or not isinstance(source.get("traces"), list):
            raise ContractError("maintainer input has no trace sample")
        try:
            traces = tuple(TraceView(**dict(item)) for item in source["traces"])
        except (TypeError, ValueError) as exc:
            raise ContractError("maintainer trace sample differs from the contract") from exc
        payload = validate_role_json(maintainer_output)
        patterns_root = self.workspace.engine.target_roots["wiki"] / "patterns"
        existing_pages = _read_pattern_pages(patterns_root)
        change = validate_maintainer_change(
            payload=payload,
            traces=traces,
            maintainer_input_hash=sha256_bytes(input_bytes),
            existing_pages=existing_pages,
        )
        changed_names = sorted(
            set(payload["create_patterns"]) | set(payload["update_patterns"])
        )
        writes: list[PlannedWrite] = [
            PlannedWrite.from_bytes(
                root="runs",
                path=f"{state.iteration}/maintainer-output.json",
                content=canonical_bytes(payload),
            )
        ]
        for name in changed_names:
            before = existing_pages.get(name)
            writes.append(
                PlannedWrite.from_bytes(
                    root="wiki",
                    path=f"patterns/{name}.md",
                    content=change.pages[name].encode("utf-8"),
                    expected_before_sha256=(
                        sha256_bytes(before.encode("utf-8")) if before is not None else None
                    ),
                )
            )
        index_before = _optional_regular_bytes(
            self.workspace.engine.target_roots["wiki"] / "index.md",
            root=self.workspace.engine.target_roots["wiki"],
        )
        log_before = _optional_regular_bytes(
            self.workspace.engine.target_roots["wiki"] / "log.md",
            root=self.workspace.engine.target_roots["wiki"],
        )
        log_content = log_before or b""
        if log_content and not log_content.endswith(b"\n"):
            log_content += b"\n"
        log_content += change.log_entry.rstrip().encode("utf-8") + b"\n"
        writes.extend(
            (
                PlannedWrite.from_bytes(
                    root="wiki",
                    path="index.md",
                    content=change.index.encode("utf-8"),
                    expected_before_sha256=(
                        sha256_bytes(index_before) if index_before is not None else None
                    ),
                ),
                PlannedWrite.from_bytes(
                    root="wiki",
                    path="log.md",
                    content=log_content,
                    expected_before_sha256=(
                        sha256_bytes(log_before) if log_before is not None else None
                    ),
                ),
            )
        )
        wiki_root = self.workspace.engine.target_roots["wiki"]
        wiki_pages = _read_text_tree(wiki_root)
        train_manifest_path = require_regular_file(
            self.workspace.engine.target_roots["runs"]
            / _run_root("train", state.iteration)
            / "manifest.json",
            root=self.workspace.engine.target_roots["runs"],
        )
        return self.workspace.apply(
            operation="apply-wiki",
            arguments={"iteration": state.iteration, "change": change.digest},
            input_hashes={
                "maintainer_input": sha256_bytes(input_bytes),
                "maintainer_output": sha256_bytes(canonical_bytes(payload)),
                "wiki": hash_json(wiki_pages),
                "train_manifest": sha256_file(train_manifest_path),
            },
            dependency_operation="apply-wiki",
            values=(
                PlannedValue.from_bytes(
                    name="maintainer_output", content=canonical_bytes(payload)
                ),
                PlannedValue.from_bytes(
                    name="wiki", content=canonical_bytes(wiki_pages)
                ),
            ),
            reads=(
                PlannedRead(
                    name="maintainer_input",
                    root="runs",
                    path=input_path.relative_to(
                        self.workspace.engine.target_roots["runs"]
                    ).as_posix(),
                    expected_sha256=sha256_bytes(input_bytes),
                ),
                PlannedRead(
                    name="train_manifest",
                    root="runs",
                    path=train_manifest_path.relative_to(
                        self.workspace.engine.target_roots["runs"]
                    ).as_posix(),
                    expected_sha256=sha256_file(train_manifest_path),
                ),
            ),
            tree_reads=(
                (
                    PlannedTreeRead(
                        name="wiki",
                        root="domain",
                        path="wiki",
                        expected_sha256=hash_json(tree_manifest(wiki_root)),
                    ),
                )
                if wiki_root.is_dir() and not wiki_root.is_symlink()
                else ()
            ),
            writes=tuple(writes),
        )

    def proposer_context(self) -> bytes:
        """Build the Proposer input from train-only outcomes and governed state."""

        state = self.workspace.status()
        if state.state is not LifecycleState.NEEDS_PROPOSAL:
            raise TransitionRefused("proposer context is refused in the current phase")
        manifest = self._read_manifest("train", state.iteration)
        if not any(
            item.get("manifest_hash") == manifest.digest
            and item.get("by") == "apply-wiki"
            for item in state.consumed_manifests
        ):
            raise ContractError("proposer context requires the consumed train manifest")
        domain = self.workspace.recorded_domain()
        tasks = domain.task_map()
        answers = domain.answer_map()
        runs_root = self.workspace.engine.target_roots["runs"]
        run_dir = runs_root / _run_root("train", state.iteration)
        raw_root = self.workspace.engine.target_roots["raw"]
        dependency_reads: list[PlannedRead] = [
            PlannedRead(
                name="train_manifest",
                root="runs",
                path=f"{_run_root('train', state.iteration)}/manifest.json",
                expected_sha256=manifest.digest,
            )
        ]
        raw_sidecar_hashes: dict[str, str] = {}
        raw_trace_hashes: dict[str, str] = {}
        outcomes = []
        for entry in manifest.entries:
            sidecar_path = require_regular_file(
                raw_root / f"traces/{state.iteration}/{entry.task_id}.json",
                root=raw_root,
            )
            trace_path = require_regular_file(
                raw_root / f"traces/{state.iteration}/{entry.task_id}.md",
                root=raw_root,
            )
            sidecar = _read_json_object(sidecar_path, label="raw train sidecar")
            output = trace_path.read_text(encoding="utf-8")
            expected = answers[entry.task_id]
            if (
                sidecar.get("task_id") != entry.task_id
                or sidecar.get("split") != "train"
                or sidecar.get("phase") != "train"
                or sidecar.get("iteration") != state.iteration
                or sidecar.get("output_hash") != entry.returned_output_hash
                or sidecar.get("score") != entry.score
                or sidecar.get("expected") != expected.expected
            ):
                raise ContractError("train sidecar differs from its manifest or answer")
            raw_sidecar_hashes[entry.task_id] = sha256_file(sidecar_path)
            raw_trace_hashes[entry.task_id] = sha256_file(trace_path)
            dependency_reads.extend(
                (
                    PlannedRead(
                        name="raw_sidecars",
                        root="raw",
                        path=sidecar_path.relative_to(raw_root).as_posix(),
                        expected_sha256=raw_sidecar_hashes[entry.task_id],
                    ),
                    PlannedRead(
                        name="raw_traces",
                        root="raw",
                        path=trace_path.relative_to(raw_root).as_posix(),
                        expected_sha256=raw_trace_hashes[entry.task_id],
                    ),
                )
            )
            outcomes.append((tasks[entry.task_id], expected, output, float(entry.score)))
        snapshot = self._load_snapshot(str(state.active_snapshot_hash))
        wiki_root = self.workspace.engine.target_roots["wiki"]
        wiki_pages = _read_text_tree(wiki_root)
        impact_root = self.workspace.engine.target_roots["impact"]
        history = _read_impact_history(impact_root)
        domain_record_path = require_regular_file(
            self.workspace.layout.domain_root / "domain.json",
            root=self.workspace.layout.domain_root,
        )
        dependency_reads.append(
            PlannedRead(
                name="train_answers",
                root="domain",
                path="domain.json",
                expected_sha256=sha256_file(domain_record_path),
            )
        )
        snapshot_root = self.workspace.engine.target_roots["snapshots"] / snapshot.snapshot_hash
        tree_reads: list[PlannedTreeRead] = []
        if wiki_root.is_dir() and not wiki_root.is_symlink():
            tree_reads.append(
                PlannedTreeRead(
                    name="wiki",
                    root="domain",
                    path="wiki",
                    expected_sha256=hash_json(tree_manifest(wiki_root)),
                )
            )
        if snapshot_root.is_dir() and not snapshot_root.is_symlink():
            tree_reads.append(
                PlannedTreeRead(
                    name="active_snapshot",
                    root="snapshots",
                    path=snapshot.snapshot_hash,
                    expected_sha256=hash_json(tree_manifest(snapshot_root)),
                )
            )
        if impact_root.is_dir() and not impact_root.is_symlink():
            tree_reads.append(
                PlannedTreeRead(
                    name="impact_history",
                    root="domain",
                    path="impact",
                    expected_sha256=hash_json(tree_manifest(impact_root)),
                )
            )
        payload = proposer_payload(
            train_outcomes=tuple(outcomes),
            wiki_pages=wiki_pages,
            impact_history=tuple(asdict(item) for item in history),
            active_skill=_active_skill_text(snapshot),
        )
        payload.update(
            {
                "schema": "asme.proposer-context.v1",
                "source_class": "ARCHITECTURE",
                "iteration": state.iteration,
                "active_snapshot_hash": snapshot.snapshot_hash,
                "train_manifest_hash": manifest.digest,
                "available_trace_ids": [entry.task_id for entry in manifest.entries],
                "seeded_observation_ids": list(state.seeded_observation_ids),
            }
        )
        content = canonical_bytes(payload)
        self.workspace.persist(
            operation="proposer-context",
            arguments={"iteration": state.iteration},
            input_hashes={
                "train_manifest": manifest.digest,
                "wiki": hash_json(wiki_pages),
                "raw_sidecars": hash_json(raw_sidecar_hashes),
                "raw_traces": hash_json(raw_trace_hashes),
                "train_answers": sha256_file(domain_record_path),
                "impact_history": hash_json([asdict(item) for item in history]),
                "active_snapshot": snapshot.snapshot_hash,
            },
            dependency_operation="proposer-context",
            reads=tuple(dependency_reads),
            tree_reads=tuple(tree_reads),
            values=(
                PlannedValue.from_bytes(
                    name="active_snapshot", content=snapshot_material(snapshot)
                ),
            ),
            writes=(
                PlannedWrite.from_bytes(
                    root="runs",
                    path=f"{state.iteration}/proposer-context.json",
                    content=content,
                    allow_existing_identical=True,
                ),
            ),
        )
        return content

    def apply_proposal(self, proposer_output: str) -> DomainState:
        """Validate one Proposer result and record no-action or candidate state."""

        state = self.workspace.status()
        if state.state is not LifecycleState.NEEDS_PROPOSAL:
            raise TransitionRefused("proposal application is refused in the current phase")
        context_path = require_regular_file(
            self.workspace.engine.target_roots["runs"]
            / str(state.iteration)
            / "proposer-context.json",
            root=self.workspace.engine.target_roots["runs"],
        )
        context = context_path.read_bytes()
        context_record = _read_json_object(context_path, label="proposer context")
        trace_ids = context_record.get("available_trace_ids")
        if not isinstance(trace_ids, list):
            raise ContractError("proposer context has no available trace IDs")
        origin_observation_ids = context_record.get("seeded_observation_ids")
        if (
            not isinstance(origin_observation_ids, list)
            or tuple(origin_observation_ids) != state.seeded_observation_ids
        ):
            raise ContractError("proposer context seed origins differ from state")
        active = self._load_snapshot(str(state.active_snapshot_hash))
        domain = self.workspace.recorded_domain()
        validated = validate_proposal(
            proposer_output,
            proposer_context=context,
            available_trace_ids=tuple(trace_ids),
            available_origin_observation_ids=tuple(origin_observation_ids),
            active_snapshot=active,
            forbidden_markers=tuple(
                answer.marker for answer in domain.answers if answer.marker is not None
            ),
        )
        normalized_output = canonical_bytes(validate_role_json(proposer_output))
        writes: list[PlannedWrite] = [
            PlannedWrite.from_bytes(
                root="runs",
                path=f"{state.iteration}/proposer-output.json",
                content=normalized_output,
            )
        ]
        input_hashes = {
            "proposer_context": sha256_bytes(context),
            "proposer_output": sha256_bytes(normalized_output),
            "proposal_output": sha256_bytes(normalized_output),
            "active_snapshot": active.snapshot_hash,
            "seal_markers": sha256_file(
                require_regular_file(
                    self.workspace.layout.domain_root / "domain.json",
                    root=self.workspace.layout.domain_root,
                )
            ),
        }
        proposal_reads = (
            PlannedRead(
                name="proposer_context",
                root="runs",
                path=context_path.relative_to(
                    self.workspace.engine.target_roots["runs"]
                ).as_posix(),
                expected_sha256=sha256_bytes(context),
            ),
            PlannedRead(
                name="seal_markers",
                root="domain",
                path="domain.json",
                expected_sha256=input_hashes["seal_markers"],
            ),
        )
        active_root = self.workspace.engine.target_roots["snapshots"] / active.snapshot_hash
        proposal_tree_reads = (
            (
                PlannedTreeRead(
                    name="active_snapshot",
                    root="snapshots",
                    path=active.snapshot_hash,
                    expected_sha256=hash_json(tree_manifest(active_root)),
                ),
            )
            if active_root.is_dir() and not active_root.is_symlink()
            else ()
        )
        if validated.action == "no_action":
            history = _read_impact_history(self.workspace.engine.target_roots["impact"])
            entry = create_impact(
                domain_id=self.workspace.domain_id,
                iteration=state.iteration,
                outcome=ImpactOutcome.NO_ACTION,
                active_before=active.snapshot_hash,
                candidate_snapshot=None,
                active_after=active.snapshot_hash,
                scores=(),
                unified_diff=None,
            )
            writes.append(_impact_history_write(history, entry))
            return self.workspace.apply(
                operation="apply-proposal-no-action",
                arguments={"iteration": state.iteration, "proposal": validated.digest},
                input_hashes=input_hashes,
                dependency_operation="apply-proposal",
                reads=proposal_reads,
                tree_reads=proposal_tree_reads,
                values=(
                    PlannedValue.from_bytes(
                        name="proposal_output", content=normalized_output
                    ),
                    PlannedValue.from_bytes(
                        name="active_snapshot", content=snapshot_material(active)
                    ),
                ),
                writes=tuple(writes),
            )
        unified_diff = _snapshot_diff(active, validated.snapshot)
        candidate = {
            "schema": CANDIDATE_SCHEMA,
            "iteration": state.iteration,
            "action": validated.action,
            "proposal_hash": validated.digest,
            "context_hash": validated.context_hash,
            "trace_ids": validated.trace_ids,
            "origin_observation_ids": validated.origin_observation_ids,
            "skill_name": validated.skill_name,
            "active_before": active.snapshot_hash,
            "candidate_snapshot": validated.snapshot.snapshot_hash,
            "unified_diff": unified_diff,
        }
        writes.extend(snapshot_write_plan(validated.snapshot))
        writes.append(
            PlannedWrite.from_bytes(
                root="runs",
                path=f"{state.iteration}/candidate.json",
                content=canonical_bytes(candidate),
            )
        )
        return self.workspace.apply(
            operation="apply-proposal-change",
            supplied=TransitionInput(snapshot_hash=validated.snapshot.snapshot_hash),
            arguments={"iteration": state.iteration, "proposal": validated.digest},
            input_hashes={
                **input_hashes,
                "candidate_snapshot": validated.snapshot.snapshot_hash,
            },
            dependency_operation="apply-proposal",
            reads=proposal_reads,
            tree_reads=proposal_tree_reads,
            values=(
                PlannedValue.from_bytes(
                    name="proposal_output", content=normalized_output
                ),
                PlannedValue.from_bytes(
                    name="active_snapshot", content=snapshot_material(active)
                ),
            ),
            writes=tuple(writes),
        )

    def gate(self) -> DomainState:
        """Apply the strict validation gate and record only terminal outcomes."""

        state = self.workspace.status()
        if state.state is not LifecycleState.NEEDS_GATE:
            raise TransitionRefused("gate is refused in the current phase")
        candidate_path = require_regular_file(
            self.workspace.engine.target_roots["runs"]
            / str(state.iteration)
            / "candidate.json",
            root=self.workspace.engine.target_roots["runs"],
        )
        candidate = _read_json_object(candidate_path, label="candidate record")
        expected_fields = {
            "schema",
            "iteration",
            "action",
            "proposal_hash",
            "context_hash",
            "trace_ids",
            "origin_observation_ids",
            "skill_name",
            "active_before",
            "candidate_snapshot",
            "unified_diff",
        }
        if set(candidate) != expected_fields or candidate.get("schema") != CANDIDATE_SCHEMA:
            raise ContractError("candidate record fields differ from the contract")
        if (
            candidate.get("iteration") != state.iteration
            or candidate.get("candidate_snapshot") != state.candidate_snapshot_hash
            or candidate.get("active_before") != state.active_snapshot_hash
            or not isinstance(candidate.get("unified_diff"), str)
            or not candidate["unified_diff"]
        ):
            raise ContractError("candidate record differs from authoritative state")
        next_state = transition(state, "gate")
        evidence_hashes, evidence_reads, evidence_materials = _validation_dependency_bundle(
            self.workspace,
            state,
            require_current=True,
        )
        snapshot_hashes, snapshot_reads = _snapshot_dependency_bundle(
            self.workspace,
            {
                "candidate_snapshot": str(state.candidate_snapshot_hash),
                "active_snapshot": str(state.active_snapshot_hash),
            },
        )
        input_hashes = {
            "candidate_record": sha256_file(candidate_path),
            "candidate_snapshot": str(state.candidate_snapshot_hash),
            "validation_manifest": str(state.current_manifest_hash),
            "evaluation_manifests": evidence_hashes["evaluation_manifests"],
            "evaluation_sidecars": evidence_hashes["evaluation_sidecars"],
            "active_snapshot": str(state.active_snapshot_hash),
            "provisional": hash_json(
                {
                    "score": state.provisional_score,
                    "confirmation_score": state.confirmation_score,
                    "manifest": state.provisional_manifest_hash,
                    "gate_phase": state.gate_phase,
                }
            ),
            **snapshot_hashes,
        }
        provisional_material = canonical_bytes(
            {
                "score": state.provisional_score,
                "confirmation_score": state.confirmation_score,
                "manifest": state.provisional_manifest_hash,
                "gate_phase": state.gate_phase,
            }
        )
        active_snapshot = self._load_snapshot(str(state.active_snapshot_hash))
        gate_values = (
            PlannedValue.from_bytes(
                name="evaluation_manifests",
                content=evidence_materials["evaluation_manifests"],
            ),
            PlannedValue.from_bytes(
                name="evaluation_sidecars",
                content=evidence_materials["evaluation_sidecars"],
            ),
            PlannedValue.from_bytes(
                name="active_snapshot", content=snapshot_material(active_snapshot)
            ),
            PlannedValue.from_bytes(name="provisional", content=provisional_material),
        )
        gate_reads = (
            PlannedRead(
                name="candidate_record",
                root="runs",
                path=candidate_path.relative_to(
                    self.workspace.engine.target_roots["runs"]
                ).as_posix(),
                expected_sha256=sha256_file(candidate_path),
            ),
            *evidence_reads,
        )
        if next_state.state is LifecycleState.NEEDS_VAL_CONFIRM:
            return self.workspace.apply(
                operation="gate",
                arguments={"iteration": state.iteration, "phase": state.gate_phase},
                input_hashes=input_hashes,
                dependency_operation="gate",
                reads=gate_reads,
                tree_reads=snapshot_reads,
                values=gate_values,
            )
        if state.gate_phase == "validation":
            outcome = ImpactOutcome.REJECTED
            scores = (float(state.provisional_score),)
        elif next_state.active_snapshot_hash == state.candidate_snapshot_hash:
            outcome = ImpactOutcome.ACCEPTED
            scores = (
                float(state.provisional_score),
                float(state.confirmation_score),
            )
        else:
            outcome = ImpactOutcome.REJECTED_AFTER_CONFIRM
            scores = (
                float(state.provisional_score),
                float(state.confirmation_score),
            )
        entry = create_impact(
            domain_id=self.workspace.domain_id,
            iteration=state.iteration,
            outcome=outcome,
            active_before=str(candidate["active_before"]),
            candidate_snapshot=str(candidate["candidate_snapshot"]),
            active_after=str(next_state.active_snapshot_hash),
            scores=scores,
            unified_diff=str(candidate["unified_diff"]),
        )
        history = _read_impact_history(self.workspace.engine.target_roots["impact"])
        return self.workspace.apply(
            operation="gate",
            arguments={
                "iteration": state.iteration,
                "phase": state.gate_phase,
                "outcome": outcome.value,
            },
            input_hashes=input_hashes,
            dependency_operation="gate",
            reads=gate_reads,
            tree_reads=snapshot_reads,
            values=gate_values,
            writes=(_impact_history_write(history, entry),),
        )

    def abandon_candidate(self) -> DomainState:
        """Abandon one published candidate while preserving the active snapshot and wiki."""

        state = self.workspace.status()
        if state.state not in {
            LifecycleState.NEEDS_VAL_RUN,
            LifecycleState.NEEDS_GATE,
            LifecycleState.NEEDS_VAL_CONFIRM,
        }:
            raise TransitionRefused("abandon is refused without a candidate")
        candidate_path = require_regular_file(
            self.workspace.engine.target_roots["runs"]
            / str(state.iteration)
            / "candidate.json",
            root=self.workspace.engine.target_roots["runs"],
        )
        candidate = _read_json_object(candidate_path, label="candidate record")
        if (
            candidate.get("schema") != CANDIDATE_SCHEMA
            or candidate.get("iteration") != state.iteration
            or candidate.get("candidate_snapshot") != state.candidate_snapshot_hash
            or candidate.get("active_before") != state.active_snapshot_hash
            or not isinstance(candidate.get("unified_diff"), str)
            or not candidate["unified_diff"]
        ):
            raise ContractError("candidate record differs from authoritative state")
        deletions: tuple[PlannedDeletion, ...] = ()
        invalid_phase = {
            LifecycleState.NEEDS_VAL_RUN: "val",
            LifecycleState.NEEDS_VAL_CONFIRM: "val_confirm",
        }.get(state.state)
        if invalid_phase is not None:
            deletions = self._invalid_rollout_deletions(
                phase=invalid_phase,
                iteration=state.iteration,
            )
        history = _read_impact_history(self.workspace.engine.target_roots["impact"])
        entry = create_impact(
            domain_id=self.workspace.domain_id,
            iteration=state.iteration,
            outcome=ImpactOutcome.ABANDONED,
            active_before=str(candidate["active_before"]),
            candidate_snapshot=str(candidate["candidate_snapshot"]),
            active_after=str(state.active_snapshot_hash),
            scores=(),
            unified_diff=str(candidate["unified_diff"]),
        )
        evidence_hashes, evidence_reads, evidence_materials = _validation_dependency_bundle(
            self.workspace,
            state,
            require_current=False,
        )
        snapshot_hashes, snapshot_reads = _snapshot_dependency_bundle(
            self.workspace,
            {"candidate_snapshot": str(state.candidate_snapshot_hash)},
        )
        provisional_material = canonical_bytes(
            {
                "score": state.provisional_score,
                "confirmation_score": state.confirmation_score,
                "manifest": state.provisional_manifest_hash,
                "gate_phase": state.gate_phase,
            }
        )
        return self.workspace.apply(
            operation="abandon",
            arguments={"iteration": state.iteration, "phase": state.state.value},
            input_hashes={
                "candidate_record": sha256_file(candidate_path),
                "candidate_snapshot": str(state.candidate_snapshot_hash),
                "evaluation_manifests": evidence_hashes["evaluation_manifests"],
                "evaluation_sidecars": evidence_hashes["evaluation_sidecars"],
                "provisional": hash_json(
                    {
                        "score": state.provisional_score,
                        "confirmation_score": state.confirmation_score,
                        "manifest": state.provisional_manifest_hash,
                        "gate_phase": state.gate_phase,
                    }
                ),
                **snapshot_hashes,
                **(
                    {"owned_manifest": state.current_manifest_hash}
                    if state.current_manifest_hash is not None
                    else {}
                ),
            },
            dependency_operation="abandon",
            values=(
                PlannedValue.from_bytes(
                    name="evaluation_manifests",
                    content=evidence_materials["evaluation_manifests"],
                ),
                PlannedValue.from_bytes(
                    name="evaluation_sidecars",
                    content=evidence_materials["evaluation_sidecars"],
                ),
                PlannedValue.from_bytes(
                    name="provisional", content=provisional_material
                ),
            ),
            reads=(
                PlannedRead(
                    name="candidate_record",
                    root="runs",
                    path=candidate_path.relative_to(
                        self.workspace.engine.target_roots["runs"]
                    ).as_posix(),
                    expected_sha256=sha256_file(candidate_path),
                ),
                *evidence_reads,
            ),
            tree_reads=snapshot_reads,
            writes=(_impact_history_write(history, entry),),
            deletions=deletions,
        )

    def reset_manifest(self) -> DomainState:
        """Delete only invalid or unparseable owned evidence and preserve outputs."""

        state = self.workspace.status()
        contexts = {
            LifecycleState.NEEDS_BASELINE_RUN: ("baseline", 0),
            LifecycleState.NEEDS_TRAIN_RUN: ("train", state.iteration),
            LifecycleState.NEEDS_WIKI: ("train", state.iteration),
            LifecycleState.NEEDS_VAL_RUN: ("val", state.iteration),
            LifecycleState.NEEDS_VAL_CONFIRM: ("val_confirm", state.iteration),
        }
        if state.state is LifecycleState.DONE:
            ingested = {str(item.get("phase")) for item in state.test_manifests}
            pending = [
                phase
                for phase in state.prepared_test_phases
                if phase not in ingested
                and (
                    self.workspace.engine.target_roots["runs"]
                    / _run_root(phase, -1)
                    / "manifest.json"
                ).exists()
            ]
            if len(pending) != 1:
                raise TransitionRefused(
                    "test manifest reset requires exactly one invalid prepared phase"
                )
            phase, iteration = pending[0], -1
        elif state.state not in contexts:
            raise TransitionRefused("manifest reset is refused in the current phase")
        else:
            phase, iteration = contexts[state.state]
        run_dir = self.workspace.engine.target_roots["runs"] / _run_root(
            phase, iteration
        )
        manifest_path = require_regular_file(run_dir / "manifest.json", root=run_dir)
        manifest_bytes = manifest_path.read_bytes()
        try:
            manifest = self._read_manifest(phase, iteration)
        except ContractError:
            manifest = None
        if manifest is not None:
            if manifest.valid:
                raise ContractError("valid rollout manifest cannot be reset")
            if any(
                item.get("manifest_hash") == manifest.digest
                for item in state.consumed_manifests
            ):
                raise ContractError("consumed rollout manifest cannot be reset")
        paths = [
            manifest_path,
            *sorted(run_dir.glob("*.sidecar.json")),
            *sorted(run_dir.glob("*.execution.json")),
        ]
        if phase == "train":
            domain = self.workspace.recorded_domain()
            task_ids = sorted(
                answer.task_id for answer in domain.answers if answer.split == "train"
            )
            raw = self.workspace.engine.target_roots["raw"]
            for task_id in task_ids:
                paths.extend(
                    (
                        raw / f"traces/{iteration}/{task_id}.md",
                        raw / f"traces/{iteration}/{task_id}.json",
                        raw / f"aliases/{task_id}",
                    )
                )
        deletions = _existing_file_deletions(
            paths,
            roots={
                "runs": self.workspace.engine.target_roots["runs"],
                "raw": self.workspace.engine.target_roots["raw"],
            },
        )
        deletion_hashes = {
            f"{item.root}:{item.path}": item.expected_sha256
            for item in deletions
            if not (item.root == "runs" and item.path.endswith("/manifest.json"))
        }
        return self.workspace.apply(
            operation="reset-manifest",
            arguments={"phase": phase, "iteration": iteration},
            input_hashes={
                "invalid_manifest": sha256_bytes(manifest_bytes),
                "manifest": sha256_bytes(manifest_bytes),
                "manifest_sidecars": hash_json(deletion_hashes),
            },
            dependency_operation="reset-manifest",
            reads=(
                PlannedRead(
                    name="manifest",
                    root="runs",
                    path=manifest_path.relative_to(
                        self.workspace.engine.target_roots["runs"]
                    ).as_posix(),
                    expected_sha256=sha256_bytes(manifest_bytes),
                ),
                *(
                    PlannedRead(
                        name="manifest_sidecars",
                        root=item.root,
                        path=item.path,
                        expected_sha256=item.expected_sha256,
                    )
                    for item in deletions
                    if not (
                        item.root == "runs" and item.path.endswith("/manifest.json")
                    )
                ),
            ),
            deletions=deletions,
        )

    def _invalid_rollout_deletions(
        self, *, phase: str, iteration: int
    ) -> tuple[PlannedDeletion, ...]:
        run_dir = self.workspace.engine.target_roots["runs"] / _run_root(
            phase, iteration
        )
        manifest_path = run_dir / "manifest.json"
        if manifest_path.is_symlink():
            raise ContractError("owned rollout manifest is a symlink")
        if not manifest_path.exists():
            return ()
        try:
            manifest = self._read_manifest(phase, iteration)
        except ContractError:
            manifest = None
        if manifest is not None and manifest.valid:
            raise ContractError("valid rollout evidence must be consumed, not deleted")
        paths = [manifest_path]
        if run_dir.exists():
            for path in sorted(run_dir.glob("*.sidecar.json")):
                paths.append(path)
        result: list[PlannedDeletion] = []
        for path in paths:
            regular = require_regular_file(path, root=run_dir)
            result.append(
                PlannedDeletion(
                    root="runs",
                    path=regular.relative_to(
                        self.workspace.engine.target_roots["runs"].resolve(strict=True)
                    ).as_posix(),
                    expected_sha256=sha256_file(regular),
                )
            )
        return tuple(result)

    def _phase_context(
        self, phase: str, state: DomainState, *, allow_after_ingest: bool = False
    ) -> tuple[str, int, Snapshot]:
        expected_states = {
            "baseline": {LifecycleState.NEEDS_BASELINE_RUN},
            "train": {LifecycleState.NEEDS_TRAIN_RUN},
            "val": {LifecycleState.NEEDS_VAL_RUN},
            "val_confirm": {LifecycleState.NEEDS_VAL_CONFIRM},
            "test-baseline": {LifecycleState.DONE},
            "test-final": {LifecycleState.DONE},
        }
        if phase not in expected_states:
            raise ContractError(f"unknown rollout phase: {phase}")
        allowed = set(expected_states[phase])
        if allow_after_ingest:
            allowed.update(
                {
                    "train": {LifecycleState.NEEDS_WIKI},
                    "val": {LifecycleState.NEEDS_GATE},
                    "val_confirm": {LifecycleState.NEEDS_GATE},
                }.get(phase, set())
            )
        if state.state not in allowed:
            raise TransitionRefused(f"{phase} rollout is refused in {state.state.value}")
        split = {
            "baseline": "validation",
            "train": "train",
            "val": "validation",
            "val_confirm": "validation",
            "test-baseline": "test",
            "test-final": "test",
        }[phase]
        iteration = 0 if phase == "baseline" else state.iteration
        if phase.startswith("test-"):
            iteration = -1
        pointer = (
            Snapshot.empty().snapshot_hash
            if phase in {"baseline", "test-baseline"}
            else state.candidate_snapshot_hash
            if phase in {"val", "val_confirm"}
            else state.active_snapshot_hash
        )
        if not pointer:
            raise ContractError(f"{phase} has no authoritative snapshot pointer")
        return split, iteration, self._load_snapshot(pointer)

    def _load_snapshot(self, snapshot_hash: str) -> Snapshot:
        empty = Snapshot.empty()
        if snapshot_hash == empty.snapshot_hash:
            return empty
        root = self.workspace.engine.target_roots["snapshots"] / snapshot_hash
        snapshot = Snapshot.from_directory(root)
        if snapshot.snapshot_hash != snapshot_hash:
            raise ContractError("snapshot directory name differs from its content")
        verify_snapshot(self.workspace.engine.target_roots["snapshots"], snapshot)
        return snapshot

    def _cartridge_file(self, member: str) -> Path:
        return require_regular_file(
            self.workspace.layout.domain_root / "cartridge" / member,
            root=self.workspace.layout.domain_root / "cartridge",
        )

    def _read_manifest(self, phase: str, iteration: int) -> RolloutManifest:
        path = require_regular_file(
            self.workspace.engine.target_roots["runs"]
            / _run_root(phase, iteration)
            / "manifest.json",
            root=self.workspace.engine.target_roots["runs"],
        )
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ContractError("rollout manifest is malformed") from exc
        return rollout_manifest_from_mapping(raw)


def _run_root(phase: str, iteration: int) -> str:
    return f"final/{phase}" if phase.startswith("test-") else f"{iteration}/{phase}"


def _active_skill_text(snapshot: Snapshot) -> str:
    sections: list[str] = []
    for item in snapshot.files:
        if Path(item.path).name != "SKILL.md":
            continue
        try:
            text = item.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContractError(f"active SKILL.md is not UTF-8: {item.path}") from exc
        sections.append(f"## {item.path}\n{text}")
    return "\n\n".join(sections)


def _execution_from_json(path: Path) -> CapturedExecution:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("captured execution record is malformed") from exc
    if not isinstance(raw, dict):
        raise ContractError("captured execution record must be an object")
    values = dict(raw)
    try:
        values["captured_events"] = tuple(dict(item) for item in values["captured_events"])
        values["trace_fidelity"] = TraceFidelity(values["trace_fidelity"])
        values["isolation_labels"] = {
            key: IsolationLevel(value) for key, value in values["isolation_labels"].items()
        }
        return CapturedExecution(**values)
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("captured execution record differs from the contract") from exc


def _read_text_tree(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    if root.is_symlink() or not root.is_dir():
        raise ContractError("wiki root is unsafe")
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise ContractError(f"wiki entry is unsafe: {relative}")
        if path.is_file():
            result[relative] = path.read_text(encoding="utf-8")
    return result


def _read_pattern_pages(root: Path) -> dict[str, str]:
    if not root.exists():
        if root.is_symlink():
            raise ContractError("wiki pattern root is unsafe")
        return {}
    if root.is_symlink() or not root.is_dir():
        raise ContractError("wiki pattern root is unsafe")
    result: dict[str, str] = {}
    for path in sorted(root.iterdir(), key=lambda item: item.name):
        if path.is_symlink() or not path.is_file() or path.suffix != ".md":
            raise ContractError(f"wiki pattern entry is unsafe: {path.name}")
        name = require_identifier(path.stem, field="stored pattern name")
        if name in result:
            raise ContractError(f"duplicate stored pattern name: {name}")
        result[name] = path.read_text(encoding="utf-8")
    return result


def _optional_regular_bytes(path: Path, *, root: Path) -> bytes | None:
    if path.is_symlink():
        raise ContractError(f"optional path is a symlink: {path}")
    if not path.exists():
        return None
    return require_regular_file(path, root=root).read_bytes()


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} is malformed") from exc
    if not isinstance(raw, dict):
        raise ContractError(f"{label} must be an object")
    return raw


def _read_impact_history(root: Path) -> tuple[ImpactEntry, ...]:
    path = root / "history.json"
    content = _optional_regular_bytes(path, root=root)
    if content is None:
        return ()
    try:
        raw = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("impact history is malformed") from exc
    if not isinstance(raw, dict) or set(raw) != {"schema", "entries"}:
        raise ContractError("impact history fields differ from the contract")
    if raw["schema"] != IMPACT_SCHEMA or not isinstance(raw["entries"], list):
        raise ContractError("impact history schema is invalid")
    entries: list[ImpactEntry] = []
    for item in raw["entries"]:
        if not isinstance(item, Mapping):
            raise ContractError("impact history entry must be an object")
        values = dict(item)
        try:
            values["outcome"] = ImpactOutcome(values["outcome"])
            values["scores"] = tuple(values["scores"])
            entries.append(ImpactEntry(**values))
        except (KeyError, TypeError, ValueError) as exc:
            raise ContractError("impact history entry differs from the contract") from exc
    if len({item.entry_id for item in entries}) != len(entries):
        raise ContractError("impact history contains duplicate entry IDs")
    return tuple(entries)


def _impact_history_write(
    history: tuple[ImpactEntry, ...], entry: ImpactEntry
) -> PlannedWrite:
    updated = append_impact(history, entry)
    content = canonical_bytes(
        {"schema": IMPACT_SCHEMA, "entries": [asdict(item) for item in updated]}
    )
    existing = canonical_bytes(
        {"schema": IMPACT_SCHEMA, "entries": [asdict(item) for item in history]}
    )
    return PlannedWrite.from_bytes(
        root="impact",
        path="history.json",
        content=content,
        expected_before_sha256=sha256_bytes(existing) if history else None,
    )


def _snapshot_diff(before: Snapshot, after: Snapshot) -> str:
    old = before.content_map()
    new = after.content_map()
    chunks: list[str] = []
    for member in sorted(set(old) | set(new)):
        try:
            old_text = old.get(member, b"").decode("utf-8")
            new_text = new.get(member, b"").decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContractError(f"skill snapshot is not UTF-8 text: {member}") from exc
        if old_text == new_text:
            continue
        chunks.extend(
            difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=f"active/{member}",
                tofile=f"candidate/{member}",
            )
        )
    result = "".join(chunks)
    if not result:
        raise ContractError("candidate snapshot has no textual diff")
    return result


def _existing_file_deletions(
    paths: list[Path], *, roots: Mapping[str, Path]
) -> tuple[PlannedDeletion, ...]:
    resolved_roots = {
        name: root.resolve(strict=True) for name, root in roots.items() if root.exists()
    }
    deletions: list[PlannedDeletion] = []
    seen: set[tuple[str, str]] = set()
    for path in paths:
        if not path.exists() and not path.is_symlink():
            continue
        root_name = next(
            (
                name
                for name, root in resolved_roots.items()
                if path.resolve(strict=False).is_relative_to(root)
            ),
            None,
        )
        if root_name is None:
            raise ContractError(f"owned deletion path has no governed root: {path}")
        regular = require_regular_file(path, root=resolved_roots[root_name])
        relative = regular.relative_to(resolved_roots[root_name]).as_posix()
        key = (root_name, relative)
        if key in seen:
            continue
        seen.add(key)
        deletions.append(
            PlannedDeletion(
                root=root_name,
                path=relative,
                expected_sha256=sha256_file(regular),
            )
        )
    return tuple(deletions)


def _validation_dependency_bundle(
    workspace: DomainWorkspace,
    state: DomainState,
    *,
    require_current: bool,
) -> tuple[dict[str, str], tuple[PlannedRead, ...], dict[str, bytes]]:
    expected: dict[str, str] = {}
    if (
        state.state is LifecycleState.NEEDS_VAL_CONFIRM
        and state.provisional_manifest_hash is not None
    ):
        expected["val"] = state.provisional_manifest_hash
    elif state.gate_phase == "validation":
        if require_current and state.current_manifest_phase != "val":
            raise ContractError("validation gate has no current val manifest")
        if state.current_manifest_hash is not None:
            expected["val"] = state.current_manifest_hash
    elif state.gate_phase == "confirmation":
        if state.provisional_manifest_hash is not None:
            expected["val"] = state.provisional_manifest_hash
        if require_current and state.current_manifest_phase != "val_confirm":
            raise ContractError("confirmation gate has no current val-confirm manifest")
        if state.current_manifest_hash is not None:
            expected["val_confirm"] = state.current_manifest_hash
    elif require_current:
        raise ContractError("gate phase has no validation dependency scope")

    manifest_hashes: dict[str, str] = {}
    sidecar_hashes: dict[str, str] = {}
    reads: list[PlannedRead] = []
    runs_root = workspace.engine.target_roots["runs"]
    for phase, expected_hash in sorted(expected.items()):
        run_root = _run_root(phase, state.iteration)
        run_dir = runs_root / run_root
        manifest_path = require_regular_file(run_dir / "manifest.json", root=run_dir)
        actual_hash = sha256_file(manifest_path)
        if actual_hash != expected_hash:
            raise ContractError(f"{phase} manifest differs from authoritative state")
        manifest = rollout_manifest_from_mapping(
            _read_json_object(manifest_path, label=f"{phase} manifest")
        )
        if manifest.digest != expected_hash or manifest.phase != phase:
            raise ContractError(f"{phase} manifest differs from dependency scope")
        manifest_hashes[phase] = actual_hash
        reads.append(
            PlannedRead(
                name="evaluation_manifests",
                root="runs",
                path=f"{run_root}/manifest.json",
                expected_sha256=actual_hash,
            )
        )
        for entry in manifest.entries:
            sidecar_path = require_regular_file(
                run_dir / f"{entry.task_id}.sidecar.json",
                root=run_dir,
            )
            key = f"{phase}:{entry.task_id}"
            sidecar_hashes[key] = sha256_file(sidecar_path)
            reads.append(
                PlannedRead(
                    name="evaluation_sidecars",
                    root="runs",
                    path=sidecar_path.relative_to(runs_root).as_posix(),
                    expected_sha256=sidecar_hashes[key],
                )
            )
    return (
        {
            "evaluation_manifests": hash_json(manifest_hashes),
            "evaluation_sidecars": hash_json(sidecar_hashes),
        },
        tuple(reads),
        {
            "evaluation_manifests": canonical_bytes(manifest_hashes),
            "evaluation_sidecars": canonical_bytes(sidecar_hashes),
        },
    )


def _snapshot_dependency_bundle(
    workspace: DomainWorkspace,
    named_hashes: Mapping[str, str],
) -> tuple[dict[str, str], tuple[PlannedTreeRead, ...]]:
    hashes: dict[str, str] = {}
    reads: list[PlannedTreeRead] = []
    snapshots_root = workspace.engine.target_roots["snapshots"]
    empty_hash = Snapshot.empty().snapshot_hash
    for name, snapshot_hash in sorted(named_hashes.items()):
        if len(snapshot_hash) != 64:
            raise ContractError(f"{name} has no snapshot SHA-256")
        hashes[name] = snapshot_hash
        root = snapshots_root / snapshot_hash
        if snapshot_hash == empty_hash and not root.exists():
            continue
        if root.is_symlink() or not root.is_dir():
            raise ContractError(f"{name} snapshot directory is missing or unsafe")
        snapshot = Snapshot.from_directory(root)
        if snapshot.snapshot_hash != snapshot_hash:
            raise ContractError(f"{name} snapshot content differs from its pointer")
        verify_snapshot(snapshots_root, snapshot)
        reads.append(
            PlannedTreeRead(
                name=name,
                root="snapshots",
                path=snapshot_hash,
                expected_sha256=hash_json(tree_manifest(root)),
            )
        )
    return hashes, tuple(reads)
