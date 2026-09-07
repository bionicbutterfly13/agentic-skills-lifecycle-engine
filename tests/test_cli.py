from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from asme.canonical import tree_manifest
from asme.cli import _parser, main
from asme.contract import LifecycleState
from asme.evaluation import (
    EVALUATION_TIMEOUT_SECONDS,
    evaluate_output,
)
from asme.workflow import EvolutionWorkflow
from asme.workspace import DomainWorkspace, WorkspaceLayout


def test_cli_exposes_one_core_command_for_each_workflow_operation() -> None:
    parser = _parser()
    subparsers = next(
        action
        for action in parser._actions
        if action.__class__.__name__ == "_SubParsersAction"
    )
    assert set(subparsers.choices) >= {
        "init",
        "skip-seed",
        "seed-observations",
        "rollback-seed",
        "prepare-rollout",
        "record-execution",
        "ingest-rollout",
        "reset-manifest",
        "finalize-baseline",
        "sample",
        "apply-wiki",
        "proposer-context",
        "apply-proposal",
        "gate",
        "abandon-candidate",
        "export",
        "package-untested",
        "status",
        "recover",
        "verify-archive",
        "candidate-manifest",
        "observation-candidate",
        "transition-matrix",
        "install",
    }


def test_locked_evaluation_timeout_is_30_seconds_across_public_entrypoints(
    tmp_path: Path,
) -> None:
    args = _parser().parse_args(
        [
            "ingest-rollout",
            "--domain",
            "timeout-domain",
            "--domain-root",
            str(tmp_path),
            "--phase",
            "baseline",
        ]
    )
    assert not hasattr(args, "timeout")
    assert EVALUATION_TIMEOUT_SECONDS == 30.0
    assert "timeout" not in inspect.signature(evaluate_output).parameters
    assert "timeout" not in inspect.signature(EvolutionWorkflow.ingest_rollout).parameters
    with pytest.raises(SystemExit):
        _parser().parse_args(
            [
                "ingest-rollout",
                "--domain",
                "timeout-domain",
                "--domain-root",
                str(tmp_path),
                "--phase",
                "baseline",
                "--timeout",
                "0.01",
            ]
        )


def test_cli_init_seals_executable_cartridge_and_skip_seed(
    tmp_path: Path, declared_domain, capsys
) -> None:
    tool_profile = tmp_path / "tool-profile.json"
    tool_profile.write_text(json.dumps({"mode": "none"}), encoding="utf-8")
    root = tmp_path / "workspace"
    result = main(
        [
            "init",
            "--domain",
            declared_domain.domain_id,
            "--domain-root",
            str(root),
            "--tasks",
            str(tmp_path / "tasks.jsonl"),
            "--answers",
            str(tmp_path / "answers.jsonl"),
            "--prompt",
            str(tmp_path / "prompt.txt"),
            "--extractor",
            str(tmp_path / "extractor"),
            "--scorer",
            str(tmp_path / "scorer"),
            "--tool-profile",
            str(tool_profile),
            "--max-iterations",
            "1",
        ]
    )
    assert result == 0
    capsys.readouterr()
    cartridge = root / "cartridge"
    assert (cartridge / "prompt.txt").is_file()
    assert (cartridge / "extractor").stat().st_mode & 0o777 == 0o700
    assert (cartridge / "scorer").stat().st_mode & 0o777 == 0o700

    assert (
        main(
            [
                "skip-seed",
                "--domain",
                declared_domain.domain_id,
                "--domain-root",
                str(root),
            ]
        )
        == 0
    )
    capsys.readouterr()
    workspace = DomainWorkspace(
        domain_id=declared_domain.domain_id,
        layout=WorkspaceLayout.under(root),
    )
    assert workspace.status().state is LifecycleState.NEEDS_BASELINE_RUN


def test_candidate_manifest_is_stdout_only_and_byte_stable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "candidate"
    source.mkdir()
    (source / "SKILL.md").write_text("# Candidate\n", encoding="utf-8")
    (source / "README.md").write_text(
        "staged candidate, not installed\n", encoding="utf-8"
    )
    compatibility = tmp_path / "compatibility.json"
    compatibility.write_text(
        json.dumps(
            {
                "schema": "asme.compatibility.v1",
                "contract_version": "asme.contract.v1",
                "core_version": "0.1.0",
                "package_version": "0.1.0",
                "adapter_id": "hermes",
                "adapter_version": "0.1.0",
                "runtime_min_tested": "0.20.5",
                "runtime_max_tested": "0.20.5",
                "runtime_tested": ["0.20.5"],
            }
        ),
        encoding="utf-8",
    )
    attribution = tmp_path / "attribution.json"
    attribution.write_text(
        json.dumps([{"title": "WikiSkill", "license": "CC BY 4.0"}]),
        encoding="utf-8",
    )
    before = tree_manifest(source)
    command = [
        "candidate-manifest",
        "--source-root",
        str(source),
        "--compatibility",
        str(compatibility),
        "--attribution",
        str(attribution),
    ]

    assert main(command) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["schema"] == "asme.candidate-manifest.v1"
    assert first["file_count"] == 3
    assert [item["path"] for item in first["files"]] == [
        "README.md",
        "SKILL.md",
        "bundle-manifest.json",
    ]
    assert first["license_policy"] == "resolved_mit_ccby4_distribution_gate4_blocked"
    assert tree_manifest(source) == before

    assert main(command) == 0
    assert json.loads(capsys.readouterr().out) == first
    assert tree_manifest(source) == before
