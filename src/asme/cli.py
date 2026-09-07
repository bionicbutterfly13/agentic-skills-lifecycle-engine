"""Small core CLI. Runtime-specific orchestration remains adapter-owned."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from . import __version__
from .adapter import ProviderPolicy
from .canonical import ContractError, canonical_bytes, sha256_bytes
from .cartridge import DomainCartridge
from .clock import CanonicalClock
from .contract import (
    approval_record_from_mapping,
    capability_report_from_mapping,
    captured_execution_from_mapping,
)
from .domain import load_declared_domain
from .delivery import DeliveryWorkflow
from .evalreport import EvalRun, build_eval_report, run_cartridge_phase
from .lifecycle import transition_matrix
from .observer_bridge import verify_observer_review_packet
from .package import (
    build_projection,
    compatibility_from_mapping,
    read_bundle_manifest,
    verify_archive,
)
from .skill_install import install_skill
from .workflow import EvolutionWorkflow
from .workspace import DomainWorkspace, WorkspaceLayout


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="asme",
        description=(
            "Runtime-neutral WikiSkill core. Evolved candidates are staged, never "
            "installed; only `install` writes a skill directory, and it copies just "
            "Agent Skill Mastery Engine's own skill."
        ),
    )
    parser.add_argument("--version", action="version", version=__version__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    matrix = subcommands.add_parser("transition-matrix", help="Print the total lifecycle matrix")
    matrix.set_defaults(handler=_transition_matrix)

    archive = subcommands.add_parser("verify-archive", help="Verify a normalized staged .skill archive")
    archive.add_argument("archive", type=Path)
    archive.set_defaults(handler=_verify_archive)

    candidate_manifest = subcommands.add_parser(
        "candidate-manifest",
        help="Print a deterministic candidate manifest without writing an artifact",
    )
    candidate_manifest.add_argument("--source-root", type=Path, required=True)
    candidate_manifest.add_argument("--compatibility", type=Path, required=True)
    candidate_manifest.add_argument("--attribution", type=Path, required=True)
    candidate_manifest.add_argument(
        "--license-policy", default="resolved_mit_ccby4_distribution_gate4_blocked"
    )
    candidate_manifest.set_defaults(handler=_candidate_manifest)

    observation_candidate = subcommands.add_parser(
        "observation-candidate",
        help="Print a review-only reusable-signal candidate without writing Task Observer",
    )
    _workspace_arguments(observation_candidate)
    observation_candidate.add_argument("--skill", required=True)
    observation_candidate.set_defaults(handler=_observation_candidate)

    initialize = subcommands.add_parser("init", help="Initialize one sealed development domain")
    _workspace_arguments(initialize)
    initialize.add_argument("--tasks", type=Path, required=True)
    initialize.add_argument("--answers", type=Path, required=True)
    initialize.add_argument("--prompt", type=Path, required=True)
    initialize.add_argument("--extractor", type=Path, required=True)
    initialize.add_argument("--scorer", type=Path, required=True)
    initialize.add_argument("--tool-profile", type=Path, required=True)
    initialize.add_argument(
        "--read-resource",
        action="append",
        default=[],
        metavar="ID=PATH",
        help="Bind one declared read-only resource; repeat for multiple resources",
    )
    initialize.add_argument("--max-iterations", type=int, required=True)
    initialize.add_argument(
        "--visibility", choices=("internal", "public"), default="internal"
    )
    initialize.set_defaults(handler=_initialize)

    skip_seed = subcommands.add_parser(
        "skip-seed", help="Record that no optional observation seed is used"
    )
    _workspace_arguments(skip_seed)
    skip_seed.set_defaults(handler=_skip_seed)

    seed = subcommands.add_parser(
        "seed-observations", help="Apply one human-approved named observation packet"
    )
    _workspace_arguments(seed)
    seed.add_argument("--packet", type=Path, required=True)
    seed.add_argument("--approval", type=Path, required=True)
    seed.set_defaults(handler=_seed_observations)

    rollback_seed = subcommands.add_parser(
        "rollback-seed", help="Remove an exact seed before baseline evidence exists"
    )
    _workspace_arguments(rollback_seed)
    rollback_seed.set_defaults(handler=_rollback_seed)

    prepare = subcommands.add_parser(
        "prepare-rollout", help="Write hash-bound jobs for one rollout phase"
    )
    _workspace_arguments(prepare)
    prepare.add_argument("--phase", required=True)
    prepare.add_argument("--capability-report", type=Path, required=True)
    prepare.add_argument("--provider", action="append", required=True)
    prepare.add_argument("--model", action="append", required=True)
    prepare.set_defaults(handler=_prepare_rollout)

    record = subcommands.add_parser(
        "record-execution", help="Record one adapter-returned captured execution"
    )
    _workspace_arguments(record)
    record.add_argument("--phase", required=True)
    record.add_argument("--task-id", required=True)
    record.add_argument("--execution", type=Path, required=True)
    record.set_defaults(handler=_record_execution)

    ingest = subcommands.add_parser(
        "ingest-rollout", help="Evaluate captured outputs and create one manifest"
    )
    _workspace_arguments(ingest)
    ingest.add_argument("--phase", required=True)
    ingest.set_defaults(handler=_ingest_rollout)

    reset = subcommands.add_parser(
        "reset-manifest", help="Remove invalid unconsumed evidence, preserving outputs"
    )
    _workspace_arguments(reset)
    reset.set_defaults(handler=_reset_manifest)

    finalize = subcommands.add_parser(
        "finalize-baseline", help="Consume a valid baseline and enter evolution"
    )
    _workspace_arguments(finalize)
    finalize.set_defaults(handler=_finalize_baseline)

    sample = subcommands.add_parser(
        "sample", help="Create deterministic Wiki Maintainer input from train traces"
    )
    _workspace_arguments(sample)
    sample.set_defaults(handler=_sample)

    apply_wiki = subcommands.add_parser(
        "apply-wiki", help="Validate and apply one Wiki Maintainer JSON result"
    )
    _workspace_arguments(apply_wiki)
    apply_wiki.add_argument("--output", type=Path, required=True)
    apply_wiki.set_defaults(handler=_apply_wiki)

    context = subcommands.add_parser(
        "proposer-context", help="Create the train-only Skill Proposer context"
    )
    _workspace_arguments(context)
    context.set_defaults(handler=_proposer_context)

    apply_proposal = subcommands.add_parser(
        "apply-proposal", help="Validate one create, patch, or no-action proposal"
    )
    _workspace_arguments(apply_proposal)
    apply_proposal.add_argument("--output", type=Path, required=True)
    apply_proposal.set_defaults(handler=_apply_proposal)

    gate = subcommands.add_parser(
        "gate", help="Apply strict improvement and confirmation rules"
    )
    _workspace_arguments(gate)
    gate.set_defaults(handler=_gate)

    abandon = subcommands.add_parser(
        "abandon-candidate", help="Abandon the current candidate transactionally"
    )
    _workspace_arguments(abandon)
    abandon.set_defaults(handler=_abandon_candidate)

    export = subcommands.add_parser(
        "export", help="Stage a validated active skill; never install it"
    )
    _delivery_arguments(export)
    export.set_defaults(handler=_export)

    untested = subcommands.add_parser(
        "package-untested", help="Stage an explicitly untested skill with approval"
    )
    _delivery_arguments(untested)
    untested.add_argument("--approval", type=Path, required=True)
    untested.set_defaults(handler=_package_untested)

    eval_run = subcommands.add_parser(
        "eval-run",
        help="Score offline rollouts through one cartridge and print the A2 report",
    )
    eval_run.add_argument("--cartridge", type=Path, required=True)
    eval_run.add_argument("--rollouts", type=Path, required=True)
    eval_run.add_argument("--run-id", required=True)
    eval_run.add_argument("--domain-id", required=True)
    eval_run.add_argument("--seed", type=int, required=True)
    eval_run.add_argument("--fidelity", default="observable_transcript")
    eval_run.add_argument("--isolation", default="unsandboxed")
    eval_run.set_defaults(handler=_eval_run)

    verify_packet = subcommands.add_parser(
        "verify-packet",
        help="Verify one Task Observer review packet against its manifest, read-only",
    )
    verify_packet.add_argument("--packet", type=Path, required=True)
    verify_packet.set_defaults(handler=_verify_packet)

    install = subcommands.add_parser(
        "install",
        help="Copy Agent Skill Mastery Engine's own skill files into a Claude Code skill directory",
        description=(
            "Install only Agent Skill Mastery Engine's own agent skill (SKILL.md and companions). Sources "
            "under a staging or archive root and staged bundles are refused; evolved "
            "candidates are never installed by this command."
        ),
    )
    install.add_argument(
        "--target",
        type=Path,
        help="Skill directory to create (default: ~/.claude/skills/asme)",
    )
    install.add_argument(
        "--source",
        type=Path,
        help="Checkout holding Agent Skill Mastery Engine's SKILL.md; staging and archive roots are refused",
    )
    install.add_argument(
        "--force", action="store_true", help="Replace an existing asme skill directory"
    )
    install.add_argument(
        "--dry-run", action="store_true", help="Print the plan without writing anything"
    )
    install.set_defaults(handler=_install)

    status = subcommands.add_parser("status", help="Read one domain state without recovery")
    _workspace_arguments(status)
    status.set_defaults(handler=_status)

    recover = subcommands.add_parser("recover", help="Replay one recorded pending transaction")
    _workspace_arguments(recover)
    recover.set_defaults(handler=_recover)
    return parser


def _workspace_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--domain", required=True)
    parser.add_argument("--domain-root", type=Path, required=True)
    parser.add_argument(
        "--clock",
        help="Fixed timezone-aware ISO timestamp for deterministic conformance runs",
    )


def _delivery_arguments(parser: argparse.ArgumentParser) -> None:
    _workspace_arguments(parser)
    parser.add_argument("--skill", required=True)
    parser.add_argument("--compatibility", type=Path, required=True)
    parser.add_argument("--capability-report", type=Path, required=True)
    parser.add_argument("--attribution", type=Path, required=True)
    parser.add_argument("--recorded-at", required=True)
    parser.add_argument("--forbid-live-root", type=Path, action="append", required=True)
    parser.add_argument(
        "--license-policy", default="resolved_mit_ccby4_distribution_gate4_blocked"
    )


def _workspace(args: argparse.Namespace) -> DomainWorkspace:
    return DomainWorkspace(
        domain_id=args.domain,
        layout=WorkspaceLayout.under(args.domain_root),
        clock=(
            CanonicalClock.fixed(args.clock)
            if getattr(args, "clock", None)
            else CanonicalClock.system()
        ),
    )


def _transition_matrix(_: argparse.Namespace) -> Any:
    return transition_matrix()


def _verify_archive(args: argparse.Namespace) -> Any:
    verification = verify_archive(args.archive.read_bytes())
    return asdict(verification)


def _candidate_manifest(args: argparse.Namespace) -> Any:
    compatibility = compatibility_from_mapping(
        _load_json_object(args.compatibility, label="compatibility")
    )
    attribution = _load_source_attribution(args.attribution)
    projection = build_projection(
        source_root=args.source_root,
        compatibility=compatibility,
        source_attribution=attribution,
        license_policy=args.license_policy,
    )
    manifest = read_bundle_manifest(projection)
    return {
        "schema": "asme.candidate-manifest.v1",
        "status": manifest["status"],
        "license_policy": manifest["license_policy"],
        "tree_sha256": projection.tree_sha256,
        "manifest_sha256": projection.manifest_sha256,
        "file_count": len(projection.files),
        "files": [
            {
                "path": item.path,
                "sha256": item.sha256,
                "bytes": len(item.content),
            }
            for item in projection.files
        ],
        "swept_build_artifacts": list(projection.swept_build_artifacts),
        "live_mutation": False,
    }


def _observation_candidate(args: argparse.Namespace) -> Any:
    return EvolutionWorkflow(_workspace(args)).observation_candidate(
        skill_name=args.skill
    )


def _initialize(args: argparse.Namespace) -> Any:
    tool_profile = _load_json_object(args.tool_profile, label="tool profile")
    read_resources = _read_resource_paths(args.read_resource)
    domain = load_declared_domain(
        domain_id=args.domain,
        task_file=args.tasks,
        answer_file=args.answers,
        prompt_file=args.prompt,
        extractor_file=args.extractor,
        scorer_file=args.scorer,
        tool_profile=tool_profile,
        read_resources=read_resources,
        visibility=args.visibility,
    )
    cartridge = DomainCartridge.from_paths(
        domain=domain,
        prompt=args.prompt,
        extractor=args.extractor,
        scorer=args.scorer,
        read_resources=read_resources,
    )
    return asdict(
        _workspace(args).initialize(
            domain=domain,
            max_iterations=args.max_iterations,
            cartridge=cartridge,
        )
    )


def _skip_seed(args: argparse.Namespace) -> Any:
    return asdict(_workspace(args).apply(operation="skip-seed"))


def _seed_observations(args: argparse.Namespace) -> Any:
    approval = approval_record_from_mapping(
        _load_json_object(args.approval, label="seed approval")
    )
    return asdict(
        EvolutionWorkflow(_workspace(args)).seed_observations(
            args.packet.read_bytes(), approval=approval
        )
    )


def _rollback_seed(args: argparse.Namespace) -> Any:
    return asdict(EvolutionWorkflow(_workspace(args)).rollback_seed())


def _prepare_rollout(args: argparse.Namespace) -> Any:
    report = capability_report_from_mapping(
        _load_json_object(args.capability_report, label="capability report")
    )
    policy = ProviderPolicy(
        tuple(sorted(set(args.provider))),
        tuple(sorted(set(args.model))),
    )
    prepared = EvolutionWorkflow(_workspace(args)).prepare_rollout(
        phase=args.phase,
        capability=report,
        provider_policy=policy,
    )
    return {
        "phase": args.phase,
        "tasks": [
            {
                "task_id": item.task_id,
                "prompt_hash": item.prompt_hash,
                "snapshot_hash": item.snapshot_hash,
                "job_hash": item.job.digest,
            }
            for item in prepared
        ],
    }


def _record_execution(args: argparse.Namespace) -> Any:
    execution = captured_execution_from_mapping(
        _load_json_object(args.execution, label="captured execution")
    )
    EvolutionWorkflow(_workspace(args)).record_execution(
        phase=args.phase,
        task_id=args.task_id,
        execution=execution,
    )
    return {"phase": args.phase, "task_id": args.task_id, "recorded": True}


def _ingest_rollout(args: argparse.Namespace) -> Any:
    return asdict(
        EvolutionWorkflow(_workspace(args)).ingest_rollout(phase=args.phase)
    )


def _reset_manifest(args: argparse.Namespace) -> Any:
    return asdict(EvolutionWorkflow(_workspace(args)).reset_manifest())


def _finalize_baseline(args: argparse.Namespace) -> Any:
    return asdict(EvolutionWorkflow(_workspace(args)).finalize_baseline())


def _sample(args: argparse.Namespace) -> Any:
    sample = EvolutionWorkflow(_workspace(args)).sample_train()
    return {
        "sampled": [
            {
                "task_id": item.task_id,
                "passed": item.passed,
                "source_hash": item.source_hash,
            }
            for item in sample
        ]
    }


def _apply_wiki(args: argparse.Namespace) -> Any:
    output = args.output.read_text(encoding="utf-8")
    return asdict(EvolutionWorkflow(_workspace(args)).apply_wiki(output))


def _proposer_context(args: argparse.Namespace) -> Any:
    workflow = EvolutionWorkflow(_workspace(args))
    content = workflow.proposer_context()
    state = workflow.workspace.status()
    return {
        "path": f"runs/{state.iteration}/proposer-context.json",
        "sha256": sha256_bytes(content),
    }


def _apply_proposal(args: argparse.Namespace) -> Any:
    output = args.output.read_text(encoding="utf-8")
    return asdict(EvolutionWorkflow(_workspace(args)).apply_proposal(output))


def _gate(args: argparse.Namespace) -> Any:
    return asdict(EvolutionWorkflow(_workspace(args)).gate())


def _abandon_candidate(args: argparse.Namespace) -> Any:
    return asdict(EvolutionWorkflow(_workspace(args)).abandon_candidate())


def _export(args: argparse.Namespace) -> Any:
    return asdict(_stage_delivery(args, untested=False, approval=None))


def _package_untested(args: argparse.Namespace) -> Any:
    approval = approval_record_from_mapping(
        _load_json_object(args.approval, label="untested approval")
    )
    return asdict(_stage_delivery(args, untested=True, approval=approval))


def _stage_delivery(
    args: argparse.Namespace, *, untested: bool, approval: Any
) -> Any:
    compatibility = compatibility_from_mapping(
        _load_json_object(args.compatibility, label="compatibility")
    )
    capability = capability_report_from_mapping(
        _load_json_object(args.capability_report, label="capability report")
    )
    attribution = _load_source_attribution(args.attribution)
    try:
        recorded_at = datetime.fromisoformat(args.recorded_at)
    except ValueError as exc:
        raise ContractError("recorded-at must be an ISO-8601 timestamp") from exc
    if recorded_at.tzinfo is None:
        raise ContractError("recorded-at must include a timezone")
    return DeliveryWorkflow(_workspace(args)).stage_skill(
        skill_name=args.skill,
        compatibility=compatibility,
        source_attribution=attribution,
        recorded_at=recorded_at,
        forbidden_live_roots=tuple(args.forbid_live_root),
        capability=capability,
        untested=untested,
        approval=approval,
        license_policy=args.license_policy,
    )


def _eval_run(args: argparse.Namespace) -> Any:
    phase_scores = {
        phase: run_cartridge_phase(
            cartridge_root=args.cartridge,
            outputs_file=args.rollouts / f"{phase}.jsonl",
        )
        for phase in ("baseline", "validation", "confirmation")
    }
    return build_eval_report(
        domain_id=args.domain_id,
        runs=(EvalRun(run_id=args.run_id, phase_scores=phase_scores),),
        trace_fidelity=args.fidelity,
        isolation_label=args.isolation,
        seed=args.seed,
    )


def _verify_packet(args: argparse.Namespace) -> Any:
    return verify_observer_review_packet(args.packet)


def _install(args: argparse.Namespace) -> Any:
    return install_skill(
        target=args.target,
        source=args.source,
        force=args.force,
        dry_run=args.dry_run,
    )


def _status(args: argparse.Namespace) -> Any:
    return asdict(_workspace(args).status())


def _recover(args: argparse.Namespace) -> Any:
    return asdict(_workspace(args).recover())


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    raw = _load_json(path, label=label)
    if not isinstance(raw, dict):
        raise ContractError(f"{label} must be a JSON object")
    return raw


def _load_json(path: Path, *, label: str) -> Any:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} must be readable JSON") from exc
    return raw


def _load_source_attribution(path: Path) -> tuple[dict[str, str], ...]:
    raw = _load_json(path, label="source attribution")
    if not isinstance(raw, list) or not raw:
        raise ContractError("source attribution must be a nonempty JSON list")
    attribution: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict) or not item or any(
            not isinstance(key, str) or not isinstance(value, str) or not value.strip()
            for key, value in item.items()
        ):
            raise ContractError("each source attribution must map text keys to text values")
        attribution.append(dict(item))
    return tuple(attribution)


def _read_resource_paths(values: Sequence[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ContractError("read resource must use ID=PATH")
        resource_id, path = value.split("=", 1)
        if not resource_id or not path or resource_id in result:
            raise ContractError("read resource IDs and paths must be nonblank and unique")
        result[resource_id] = Path(path)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        result = args.handler(args)
        sys.stdout.buffer.write(canonical_bytes(result))
        return 0
    except (ContractError, OSError) as exc:
        sys.stderr.write(f"asme: {exc}\n")
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
