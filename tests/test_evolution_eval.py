from __future__ import annotations

import json
from pathlib import Path

import pytest

from asme.canonical import ContractError
from asme.evalreport import EVAL_REPORT_SCHEMA, eval_report_bytes
from asme.evolution_eval import run_evolution_evaluation
from asme.workspace import DomainWorkspace, WorkspaceLayout

_ASSETS = Path(__file__).resolve().parents[1] / "assets" / "eval"


@pytest.mark.parametrize("cartridge", ("arithmetic", "echo"))
def test_evolution_eval_drives_real_state_machine_and_improves(
    tmp_path: Path, cartridge: str
) -> None:
    report = run_evolution_evaluation(
        cartridge_root=_ASSETS / cartridge,
        workspace_root=tmp_path / "workspace",
        seed=20260901,
        run_id=f"evolution-{cartridge}",
    )
    assert report["schema"] == EVAL_REPORT_SCHEMA
    assert report["seed"] == 20260901
    (run,) = report["runs"]
    assert run["run_id"] == f"evolution-{cartridge}"
    aggregates = run["aggregates"]
    assert aggregates["baseline"] == 0.5
    assert aggregates["validation"] == 1.0
    assert aggregates["confirmation"] == 1.0
    assert run["a2_local_acceptance"]["allowed"] is True
    impact = json.loads(
        (tmp_path / "workspace" / "domain" / "impact" / "history.json").read_text(
            encoding="utf-8"
        )
    )["entries"]
    assert [item["outcome"] for item in impact] == ["Accepted"]
    assert impact[0]["scores"] == [1.0, 1.0]
    workspace = DomainWorkspace(
        domain_id=report["domain_id"],
        layout=WorkspaceLayout.under(tmp_path / "workspace" / "domain"),
    )
    assert workspace.status().state.value == "DONE"


def test_evolution_eval_is_deterministic_and_byte_stable(tmp_path: Path) -> None:
    reports = [
        run_evolution_evaluation(
            cartridge_root=_ASSETS / "arithmetic",
            workspace_root=tmp_path / f"workspace-{index}",
            seed=20260901,
            run_id="evolution-arithmetic",
        )
        for index in range(2)
    ]
    assert eval_report_bytes(reports[0]) == eval_report_bytes(reports[1])


def test_evolution_eval_seed_changes_baseline_membership_not_shape(
    tmp_path: Path,
) -> None:
    first = run_evolution_evaluation(
        cartridge_root=_ASSETS / "arithmetic",
        workspace_root=tmp_path / "workspace-a",
        seed=1,
        run_id="evolution-arithmetic",
    )
    second = run_evolution_evaluation(
        cartridge_root=_ASSETS / "arithmetic",
        workspace_root=tmp_path / "workspace-b",
        seed=2,
        run_id="evolution-arithmetic",
    )
    for report in (first, second):
        assert report["runs"][0]["aggregates"]["baseline"] == 0.5
    correct_tasks = [
        tuple(
            item["task_id"]
            for item in report["runs"][0]["tasks"]["baseline"]
            if item["score"] == 1.0
        )
        for report in (first, second)
    ]
    assert correct_tasks[0] != correct_tasks[1]


def test_evolution_eval_refuses_reused_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    run_evolution_evaluation(
        cartridge_root=_ASSETS / "arithmetic",
        workspace_root=workspace,
        seed=20260901,
        run_id="evolution-arithmetic",
    )
    with pytest.raises(ContractError, match="workspace"):
        run_evolution_evaluation(
            cartridge_root=_ASSETS / "arithmetic",
            workspace_root=workspace,
            seed=20260901,
            run_id="evolution-arithmetic",
        )
