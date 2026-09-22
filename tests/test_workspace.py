from __future__ import annotations

import json
from pathlib import Path

import pytest

from asme.canonical import ContractError
from asme.domain import DeclaredDomain
from asme.workspace import DomainWorkspace, WorkspaceLayout, _state_from_json, _state_json


def _workspace(tmp_path: Path, domain: DeclaredDomain) -> DomainWorkspace:
    return DomainWorkspace(
        domain_id=domain.domain_id,
        layout=WorkspaceLayout.under(tmp_path / "workspace"),
    )


def test_initialize_records_confirmation_required_false(
    tmp_path: Path, declared_domain: DeclaredDomain
) -> None:
    workspace = _workspace(tmp_path, declared_domain)
    state = workspace.initialize(
        domain=declared_domain, max_iterations=1, confirmation_required=False
    )
    assert state.confirmation_required is False
    domain_record = json.loads(
        (workspace.layout.domain_root / "domain.json").read_text(encoding="utf-8")
    )
    assert domain_record["confirmation_required"] is False


def test_initialize_defaults_confirmation_required_true(
    tmp_path: Path, declared_domain: DeclaredDomain
) -> None:
    workspace = _workspace(tmp_path, declared_domain)
    state = workspace.initialize(domain=declared_domain, max_iterations=1)
    assert state.confirmation_required is True
    domain_record = json.loads(
        (workspace.layout.domain_root / "domain.json").read_text(encoding="utf-8")
    )
    assert domain_record["confirmation_required"] is True


def test_state_from_json_accepts_legacy_record_missing_confirmation_required(
    tmp_path: Path, declared_domain: DeclaredDomain
) -> None:
    workspace = _workspace(tmp_path, declared_domain)
    state = workspace.initialize(domain=declared_domain, max_iterations=1)
    raw = _state_json(state)
    del raw["confirmation_required"]
    legacy = _state_from_json(raw)
    assert legacy.confirmation_required is True

    with_extra = dict(raw)
    with_extra["confirmation_required"] = True
    with_extra["unexpected_extra_field"] = "nope"
    with pytest.raises(ContractError):
        _state_from_json(with_extra)

    missing_other_field = dict(raw)
    missing_other_field.pop("iteration")
    with pytest.raises(ContractError):
        _state_from_json(missing_other_field)


def test_recorded_domain_mismatch_on_confirmation_required_is_refused(
    tmp_path: Path, declared_domain: DeclaredDomain
) -> None:
    workspace = _workspace(tmp_path, declared_domain)
    workspace.initialize(domain=declared_domain, max_iterations=1, confirmation_required=False)
    domain_path = workspace.layout.domain_root / "domain.json"
    record = json.loads(domain_path.read_text(encoding="utf-8"))
    record["confirmation_required"] = True
    domain_path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ContractError, match="confirmation switch"):
        workspace.recorded_domain()
