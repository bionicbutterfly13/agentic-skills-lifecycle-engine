from __future__ import annotations

from pathlib import Path

import pytest

from asme.canonical import sha256_bytes, tree_manifest
from asme.lifecycle import OPERATIONS
from asme.transaction import (
    PendingTransaction,
    PlannedDeletion,
    PlannedWrite,
    SimulatedCrash,
    TransactionEngine,
)
from asme.workspace import NON_TRANSITION_OPERATIONS


FIXED_CLOCK = "2026-08-31T12:34:56+00:00"
CRASH_POINTS = (
    "pre-intent",
    "post-intent",
    "first-output",
    "mid-output",
    "last-output",
    "publication",
    "pre-commit",
)
STATE_CHANGING_OPERATIONS = tuple(
    sorted(
        (set(OPERATIONS) - {"recover", "status"})
        | set(NON_TRANSITION_OPERATIONS)
        | {"rebuild-mirror"}
    )
)
OWNED_ROOTS = (
    "domain",
    "snapshots",
    "mirror",
    "raw",
    "runs",
    "wiki",
    "impact",
    "staging",
    "archives",
)


def _engine(base: Path) -> TransactionEngine:
    domain = base / "domain"
    return TransactionEngine(
        domain_id="crash-oracle",
        domain_root=domain,
        control_root=base / "control",
        target_roots={
            "snapshots": domain / "snapshots",
            "mirror": domain / "mirror",
            "raw": domain / "raw",
            "runs": domain / "runs",
            "wiki": domain / "wiki",
            "impact": domain / "impact",
            "staging": base / "staging",
            "archives": base / "archives",
        },
    )


def _initialize(engine: TransactionEngine) -> dict:
    state = {
        "domain_id": "crash-oracle",
        "revision": 1,
        "route": None,
        "delivery_ledger": [],
        "history": [],
        "txn": None,
    }
    writes: list[PlannedWrite] = []
    for root in OWNED_ROOTS:
        writes.extend(
            (
                PlannedWrite.from_bytes(
                    root=root,
                    path="oracle/shared.txt",
                    content=b"before\n",
                ),
                PlannedWrite.from_bytes(
                    root=root,
                    path="oracle/victim.txt",
                    content=b"delete\n",
                ),
            )
        )
    return engine.execute(
        operation="init",
        current_state={},
        next_state=state,
        arguments={"clock": FIXED_CLOCK, "purpose": "crash-oracle-setup"},
        input_hashes={
            "clock": sha256_bytes(FIXED_CLOCK.encode("utf-8")),
            "fixture": sha256_bytes(b"crash-oracle-setup"),
        },
        writes=tuple(writes),
    )


def _execute(
    engine: TransactionEngine,
    before: dict,
    *,
    operation: str,
    crash_at: str | None = None,
) -> dict:
    route = "untested" if operation == "package-untested" else (
        "validated" if operation == "export" else None
    )
    ledger = (
        [{"delivery_id": f"delivery-{operation}", "route": route}]
        if route is not None
        else []
    )
    after = {
        **before,
        "revision": 2,
        "route": route,
        "delivery_ledger": ledger,
        "history": [{"operation": operation, "clock": FIXED_CLOCK}],
        "txn": None,
    }
    writes: list[PlannedWrite] = []
    deletions: list[PlannedDeletion] = []
    for root in OWNED_ROOTS:
        writes.extend(
            (
                PlannedWrite.from_bytes(
                    root=root,
                    path="oracle/shared.txt",
                    content=f"after:{operation}\n".encode("utf-8"),
                    expected_before_sha256=sha256_bytes(b"before\n"),
                ),
                PlannedWrite.from_bytes(
                    root=root,
                    path=f"oracle/created/{operation}.txt",
                    content=f"created:{operation}\n".encode("utf-8"),
                ),
            )
        )
        deletions.append(
            PlannedDeletion(
                root=root,
                path="oracle/victim.txt",
                expected_sha256=sha256_bytes(b"delete\n"),
            )
        )
    return engine.execute(
        operation=operation,
        current_state=before,
        next_state=after,
        arguments={"clock": FIXED_CLOCK, "fixture_operation": operation},
        input_hashes={
            "clock": sha256_bytes(FIXED_CLOCK.encode("utf-8")),
            "fixture": sha256_bytes(operation.encode("utf-8")),
        },
        writes=tuple(writes),
        deletions=tuple(deletions),
        crash_at=crash_at,
    )


def _owned_manifests(base: Path) -> dict[str, dict[str, str]]:
    domain = base / "domain"
    roots = {
        "domain": domain,
        "snapshots": domain / "snapshots",
        "mirror": domain / "mirror",
        "raw": domain / "raw",
        "runs": domain / "runs",
        "wiki": domain / "wiki",
        "impact": domain / "impact",
        "staging": base / "staging",
        "archives": base / "archives",
    }
    return {name: tree_manifest(path) for name, path in roots.items()}


def _residue(base: Path) -> tuple[str, ...]:
    excluded = {
        "crash-oracle.lock",
        "state.json",
    }
    return tuple(
        sorted(
            path.relative_to(base).as_posix()
            for path in base.rglob("*")
            if path.name not in excluded
            and (
                ".tmp" in path.name
                or path.name.endswith(".intent.json")
                or path.name.endswith(".partial")
            )
        )
    )


def test_crash_oracle_operation_inventory_is_complete() -> None:
    assert set(STATE_CHANGING_OPERATIONS) == (
        (set(OPERATIONS) - {"recover", "status"})
        | set(NON_TRANSITION_OPERATIONS)
        | {"rebuild-mirror"}
    )


@pytest.mark.parametrize("operation", STATE_CHANGING_OPERATIONS)
@pytest.mark.parametrize("crash_point", CRASH_POINTS)
def test_fixed_clock_crash_recovery_equals_uninterrupted_for_every_operation(
    tmp_path: Path,
    operation: str,
    crash_point: str,
) -> None:
    expected_root = tmp_path / "expected"
    expected_engine = _engine(expected_root)
    expected_before = _initialize(expected_engine)
    expected_state = _execute(
        expected_engine,
        expected_before,
        operation=operation,
    )
    expected_manifests = _owned_manifests(expected_root)

    crashed_root = tmp_path / "crashed"
    crashed_engine = _engine(crashed_root)
    before = _initialize(crashed_engine)
    with pytest.raises(SimulatedCrash):
        _execute(
            crashed_engine,
            before,
            operation=operation,
            crash_at=crash_point,
        )
    if crash_point == "pre-intent":
        assert crashed_engine.read_state() == before
        assert crashed_engine.recover() == before
        recovered = _execute(crashed_engine, before, operation=operation)
    else:
        with pytest.raises(PendingTransaction):
            _execute(crashed_engine, before, operation=operation)
        recovered = crashed_engine.recover()

    assert crashed_engine.recover() == recovered
    assert recovered == expected_state
    assert _owned_manifests(crashed_root) == expected_manifests
    assert _residue(crashed_root) == ()

