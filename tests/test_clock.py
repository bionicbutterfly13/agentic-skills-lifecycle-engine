from __future__ import annotations

from pathlib import Path

import pytest

from asme.canonical import sha256_bytes
from asme.clock import CanonicalClock
from asme.transaction import PlannedWrite, SimulatedCrash
from asme.workspace import DomainWorkspace, WorkspaceLayout


FIXED = "2026-08-31T12:34:56+00:00"


def _assert_pending_clock(workspace: DomainWorkspace) -> None:
    state = workspace.engine.read_state()
    assert state is not None and state["txn"] is not None
    transaction = state["txn"]
    assert transaction["arguments"]["clock"] == FIXED
    assert transaction["input_hashes"]["clock"] == sha256_bytes(FIXED.encode("utf-8"))


def test_fixed_clock_is_recorded_for_transition_and_persistence(
    tmp_path: Path, declared_domain
) -> None:
    workspace = DomainWorkspace(
        domain_id=declared_domain.domain_id,
        layout=WorkspaceLayout.under(tmp_path / "workspace"),
        clock=CanonicalClock.fixed(FIXED),
    )
    with pytest.raises(SimulatedCrash):
        workspace.initialize(
            domain=declared_domain,
            max_iterations=1,
            crash_at="post-intent",
        )
    _assert_pending_clock(workspace)
    workspace.recover()

    with pytest.raises(SimulatedCrash):
        workspace.apply(operation="skip-seed", crash_at="post-intent")
    _assert_pending_clock(workspace)
    workspace.recover()

    with pytest.raises(SimulatedCrash):
        workspace.persist(
            operation="record-execution",
            writes=(
                PlannedWrite.from_bytes(
                    root="runs",
                    path="clock-proof.txt",
                    content=b"fixed\n",
                ),
            ),
            crash_at="post-intent",
        )
    _assert_pending_clock(workspace)
    workspace.recover()


def test_fixed_clock_normalizes_to_utc() -> None:
    clock = CanonicalClock.fixed("2026-08-31T08:34:56-04:00")
    assert clock.read() == FIXED
    assert clock.now().isoformat() == FIXED
