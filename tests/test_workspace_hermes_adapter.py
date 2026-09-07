from __future__ import annotations

import ast
from dataclasses import asdict
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from asme.canonical import ContractError
from asme.canonical import sha256_bytes, tree_manifest
from asme.lifecycle import TransitionInput
from asme.package import Compatibility, build_archive, build_projection
from asme.snapshot import Snapshot
from asme.transaction import PlannedDeletion, PlannedWrite
from asme.workspace import DomainWorkspace, WorkspaceLayout, _state_json


def _workspace(root: Path) -> DomainWorkspace:
    return DomainWorkspace(
        domain_id="test-domain",
        layout=WorkspaceLayout.under(root),
    )


def test_same_domain_id_in_different_roots_has_distinct_control_files(tmp_path: Path) -> None:
    first = _workspace(tmp_path / "first")
    second = _workspace(tmp_path / "second")
    assert first.engine.intent_path != second.engine.intent_path
    assert first.engine.lock_path != second.engine.lock_path


def test_workspace_rechecks_recorded_domain_seal_before_mutation(
    tmp_path: Path, declared_domain
) -> None:
    workspace = _workspace(tmp_path / "domain")
    workspace.initialize(domain=declared_domain, max_iterations=1)
    record = workspace.layout.domain_root / "domain.json"
    raw = json.loads(record.read_text(encoding="utf-8"))
    raw["domain"]["prompt_hash"] = "0" * 64
    record.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ContractError, match="recorded domain"):
        workspace.apply(operation="skip-seed")


def _baseline(workspace: DomainWorkspace, declared_domain, skill_root: Path) -> Snapshot:
    workspace.initialize(domain=declared_domain, max_iterations=1)
    workspace.apply(operation="skip-seed")
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
    snapshot = Snapshot.from_directory(skill_root)
    workspace.publish_snapshot(
        snapshot=snapshot,
        operation="baseline-finalize",
        supplied=TransitionInput(
            valid=True,
            score=0.5,
            snapshot_hash=snapshot.snapshot_hash,
            phase="baseline",
            manifest_hash="1" * 64,
        ),
    )
    return snapshot


def test_hf_a10_corrupt_train_reset_removes_derived_raw_and_reingests(
    tmp_path: Path, declared_domain
) -> None:
    workspace = _workspace(tmp_path / "domain-a")
    _baseline(workspace, declared_domain, tmp_path / "skill-a")
    submitted = b"model output\n"
    current = workspace.status()
    workspace.engine.execute(
        operation="submit-output",
        current_state=_state_json(current),
        next_state=_state_json(current),
        arguments={"phase": "train"},
        input_hashes={"domain_seal": current.seal},
        writes=(
            PlannedWrite.from_bytes(
                root="runs", path="1/train-1.out.md", content=submitted
            ),
        ),
    )
    valid_manifest = b'{"valid":true}\n'
    sidecar = b'{"score":1}\n'
    workspace.apply(
        operation="train-ingest",
        supplied=TransitionInput(
            valid=True,
            phase="train",
            manifest_hash=sha256_bytes(valid_manifest),
        ),
        input_hashes={"outputs": sha256_bytes(submitted)},
        writes=(
            PlannedWrite.from_bytes(root="raw", path="train/manifest.json", content=valid_manifest),
            PlannedWrite.from_bytes(root="raw", path="train/train-1.json", content=sidecar),
            PlannedWrite.from_bytes(root="raw", path="aliases/train-current", content=b"train/manifest.json\n"),
        ),
    )
    raw = workspace.engine.target_roots["raw"]
    corrupted = b"{broken\n"
    (raw / "train/manifest.json").write_bytes(corrupted)
    workspace.apply(
        operation="reset-manifest",
        deletions=(
            PlannedDeletion(root="raw", path="train/manifest.json", expected_sha256=sha256_bytes(corrupted)),
            PlannedDeletion(root="raw", path="train/train-1.json", expected_sha256=sha256_bytes(sidecar)),
            PlannedDeletion(
                root="raw",
                path="aliases/train-current",
                expected_sha256=sha256_bytes(b"train/manifest.json\n"),
            ),
        ),
        input_hashes={"corrupt_manifest": sha256_bytes(corrupted)},
    )
    assert tree_manifest(raw) == {}
    assert (workspace.engine.target_roots["runs"] / "1/train-1.out.md").read_bytes() == submitted
    corrected = b'{"valid":true,"corrected":true}\n'
    workspace.apply(
        operation="train-ingest",
        supplied=TransitionInput(
            valid=True,
            phase="train",
            manifest_hash=sha256_bytes(corrected),
        ),
        input_hashes={"outputs": sha256_bytes(submitted)},
        writes=(
            PlannedWrite.from_bytes(root="raw", path="train/manifest.json", content=corrected),
            PlannedWrite.from_bytes(root="raw", path="train/train-1.json", content=sidecar),
            PlannedWrite.from_bytes(root="raw", path="aliases/train-current", content=b"train/manifest.json\n"),
        ),
    )

    clean = _workspace(tmp_path / "domain-b")
    _baseline(clean, declared_domain, tmp_path / "skill-b")
    clean.apply(
        operation="train-ingest",
        supplied=TransitionInput(
            valid=True,
            phase="train",
            manifest_hash=sha256_bytes(corrected),
        ),
        input_hashes={"outputs": sha256_bytes(submitted)},
        writes=(
            PlannedWrite.from_bytes(root="raw", path="train/manifest.json", content=corrected),
            PlannedWrite.from_bytes(root="raw", path="train/train-1.json", content=sidecar),
            PlannedWrite.from_bytes(root="raw", path="aliases/train-current", content=b"train/manifest.json\n"),
        ),
    )
    assert tree_manifest(raw) == tree_manifest(clean.engine.target_roots["raw"])


def test_hf_a23_staging_leaves_declared_live_root_byte_identical(
    tmp_path: Path, declared_domain
) -> None:
    workspace = _workspace(tmp_path / "domain")
    _baseline(workspace, declared_domain, tmp_path / "skill")
    workspace.apply(
        operation="train-ingest",
        supplied=TransitionInput(valid=True, phase="train", manifest_hash="2" * 64),
    )
    workspace.apply(operation="apply-wiki")
    done = workspace.apply(operation="apply-proposal-no-action")
    assert done.state.value == "DONE"
    workspace.apply(
        operation="test-prepare", supplied=TransitionInput(phase="test-baseline")
    )
    workspace.apply(
        operation="test-ingest",
        supplied=TransitionInput(
            valid=True, phase="test-baseline", manifest_hash="3" * 64
        ),
    )
    workspace.apply(operation="test-prepare", supplied=TransitionInput(phase="test-final"))
    workspace.apply(
        operation="test-ingest",
        supplied=TransitionInput(valid=True, phase="test-final", manifest_hash="4" * 64),
    )

    package_source = tmp_path / "package-source"
    package_source.mkdir()
    (package_source / "SKILL.md").write_text("# Candidate\n", encoding="utf-8")
    (package_source / "README.md").write_text(
        "test_evaluation: passed\ntrace_fidelity: observable_transcript\nisolation: unsandboxed\n",
        encoding="utf-8",
    )
    (package_source / "PURPOSE.md").write_text(
        "test_evaluation: passed\ntrace_fidelity: observable_transcript\nisolation: unsandboxed\n",
        encoding="utf-8",
    )
    compatibility = Compatibility(
        contract_version="asme.contract.v1",
        core_version="0.1.0",
        package_version="0.1.0",
        adapter_id="hermes",
        adapter_version="0.1.0",
        runtime_min_tested="0.20.5",
        runtime_max_tested="0.20.6",
        runtime_tested=("0.20.5", "0.20.6"),
    )
    projection = build_projection(
        source_root=package_source,
        compatibility=compatibility,
        source_attribution=({"title": "WikiSkill", "license": "CC BY 4.0"},),
    )
    archive = build_archive(
        projection, recorded_at=datetime(2026, 8, 31, tzinfo=timezone.utc)
    )
    live = tmp_path / "live-runtime"
    live.mkdir()
    (live / "existing.txt").write_text("unchanged\n", encoding="utf-8")
    before = tree_manifest(live)
    staged = workspace.stage_projection(
        projection=projection,
        archive_bytes=archive,
        staging_id="candidate-1",
        untested=False,
        approval_present=False,
        forbidden_live_roots=(live,),
    )
    assert staged.delivery_ledger == (
        {"delivery_id": "candidate-1", "route": "validated"},
    )
    assert tree_manifest(live) == before
    assert (workspace.layout.staging_root / "candidate-1/SKILL.md").is_file()
    assert (workspace.layout.archive_root / "candidate-1.skill").is_file()


def test_hermes_adapter_is_thin_read_only_and_dispatch_disabled(monkeypatch) -> None:
    plugin_path = Path(__file__).parents[1] / "adapters" / "hermes_plugin" / "__init__.py"
    spec = importlib.util.spec_from_file_location("test_hermes_adapter", plugin_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    class Context:
        def __init__(self):
            self.tools = []

        def register_tool(self, **kwargs):
            self.tools.append(kwargs)

    context = Context()
    module.register(context)
    assert len(context.tools) == 1
    payload = json.loads(context.tools[0]["handler"]({}))
    assert payload["status"] == "staging_only_dispatch_disabled"
    assert payload["capability_report"]["trace_fidelity"] == "unknown"
    assert payload["capability_report"]["claims_allowed"] == ["unknown", "unsandboxed"]
    lifecycle_evidence = next(
        item
        for item in payload["capability_report"]["evidence"]
        if item["kind"] == "fresh_child_lifecycle"
    )
    assert lifecycle_evidence["passed"] is False
    manifest = plugin_path.with_name("plugin.yaml").read_text(encoding="utf-8")
    assert "provides_hooks" not in manifest and "wikiskill_run_role" not in manifest


def test_hermes_adapter_registration_does_not_require_importable_core() -> None:
    plugin_path = Path(__file__).parents[1] / "adapters" / "hermes_plugin" / "__init__.py"
    script = """
import builtins
import importlib.util
import sys

real_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "asme" or name.startswith("asme."):
        raise ModuleNotFoundError("asme deliberately unavailable")
    return real_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
spec = importlib.util.spec_from_file_location("isolated_hermes_adapter", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class Context:
    def __init__(self):
        self.tools = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)

context = Context()
module.register(context)
assert [item["name"] for item in context.tools] == ["wikiskill_capabilities"]
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(plugin_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    manifest = plugin_path.with_name("plugin.yaml").read_text(encoding="utf-8")
    assert '"agent-skill-mastery-engine>=0.2.0,<0.3"' in manifest


def test_hermes_adapter_probes_lifecycle_from_active_plugin_context() -> None:
    plugin_path = Path(__file__).parents[1] / "adapters" / "hermes_plugin" / "__init__.py"
    spec = importlib.util.spec_from_file_location("test_hermes_adapter_probe", plugin_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    class Lifecycle:
        launch = status = wait = cancel = result = reconnect = lambda *args, **kwargs: None

    class Context:
        subagent_lifecycle = Lifecycle()

        def __init__(self):
            self.tools = []

        def register_tool(self, **kwargs):
            self.tools.append(kwargs)

    context = Context()
    module.register(context)
    payload = json.loads(context.tools[0]["handler"]({}))
    lifecycle_evidence = next(
        item
        for item in payload["capability_report"]["evidence"]
        if item["kind"] == "fresh_child_lifecycle"
    )
    assert lifecycle_evidence["passed"] is True


def test_hermes_adapter_selects_zero_workers_and_has_no_launch_surface() -> None:
    plugin_path = Path(__file__).parents[1] / "adapters" / "hermes_plugin" / "__init__.py"
    tree = ast.parse(plugin_path.read_text(encoding="utf-8"))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    forbidden_imports = {
        "asyncio",
        "subprocess",
        "hermes_cli.delegation",
        "hermes_cli.kanban",
        "hermes_cli.subagents",
    }
    assert imported_modules.isdisjoint(forbidden_imports)
    function_names = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }
    assert not function_names & {"dispatch", "delegate", "launch", "run_role"}
    assert function_names == {"capability_report", "_handle_capabilities", "register"}


def test_current_tree_is_community_scan_clean() -> None:
    package_root = Path(__file__).parents[1]
    projection = build_projection(
        source_root=package_root,
        compatibility=Compatibility(
            contract_version="asme.contract.v1",
            core_version="0.1.0",
            package_version="0.1.0",
            adapter_id="hermes",
            adapter_version="0.1.0",
            runtime_min_tested="0.20.5",
            runtime_max_tested="0.20.6",
            runtime_tested=("0.20.5", "0.20.6"),
        ),
        source_attribution=({"title": "WikiSkill", "license": "CC BY 4.0"},),
    )
    assert projection.files
