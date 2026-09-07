from __future__ import annotations

from pathlib import Path

import pytest

from asme.canonical import (
    ContractError,
    canonical_bytes,
    hash_json,
    sha256_bytes,
    tree_manifest,
)
from asme.transaction import (
    PendingTransaction,
    PlannedAbsence,
    PlannedDeletion,
    PlannedRead,
    PlannedTreeRead,
    PlannedWrite,
    RecoveryCorruption,
    SimulatedCrash,
    TransactionEngine,
    transaction_id,
)
from asme.dependencies import default_dependency_matrix


CRASH_POINTS = (
    "pre-intent",
    "post-intent",
    "first-output",
    "mid-output",
    "last-output",
    "publication",
    "pre-commit",
)


def _engine(base: Path) -> TransactionEngine:
    return TransactionEngine(
        domain_id="domain",
        domain_root=base / "domain",
        control_root=base / "control",
        target_roots={"raw": base / "domain" / "raw"},
    )


def _initialize(engine: TransactionEngine) -> dict:
    state = {"domain_id": "domain", "revision": 1, "txn": None}
    engine.execute(
        operation="init",
        current_state={},
        next_state=state,
        arguments={},
        input_hashes={"seal": "a" * 64},
        writes=(
            PlannedWrite.from_bytes(root="domain", path="a.txt", content=b"old\n"),
            PlannedWrite.from_bytes(root="domain", path="victim.txt", content=b"remove\n"),
        ),
    )
    return state


def _second_transaction(engine: TransactionEngine, before: dict, *, crash_at=None) -> dict:
    after = {"domain_id": "domain", "revision": 2, "txn": None}
    return engine.execute(
        operation="update",
        current_state=before,
        next_state=after,
        arguments={"iteration": 1},
        input_hashes={"seal": "a" * 64, "input": "b" * 64},
        writes=(
            PlannedWrite.from_bytes(
                root="domain",
                path="a.txt",
                content=b"new\n",
                expected_before_sha256=sha256_bytes(b"old\n"),
            ),
            PlannedWrite.from_bytes(root="raw", path="b.txt", content=b"b\n"),
            PlannedWrite.from_bytes(root="raw", path="c.txt", content=b"c\n"),
        ),
        deletions=(
            PlannedDeletion(
                root="domain",
                path="victim.txt",
                expected_sha256=sha256_bytes(b"remove\n"),
            ),
        ),
        crash_at=crash_at,
    )


@pytest.mark.parametrize("point", CRASH_POINTS)
def test_hf_a11_crash_recover_twice_equals_uninterrupted(tmp_path: Path, point: str) -> None:
    expected_root = tmp_path / "expected"
    expected_engine = _engine(expected_root)
    expected_before = _initialize(expected_engine)
    expected_state = _second_transaction(expected_engine, expected_before)
    expected_tree = tree_manifest(expected_root / "domain")

    crashed_root = tmp_path / "crashed"
    crashed_engine = _engine(crashed_root)
    before = _initialize(crashed_engine)
    with pytest.raises(SimulatedCrash):
        _second_transaction(crashed_engine, before, crash_at=point)
    if point == "pre-intent":
        assert crashed_engine.read_state() == before
        assert crashed_engine.recover() == before
        recovered = _second_transaction(crashed_engine, before)
    else:
        with pytest.raises(PendingTransaction):
            _second_transaction(crashed_engine, before)
        recovered = crashed_engine.recover()
    assert crashed_engine.recover() == recovered
    assert recovered == expected_state
    assert tree_manifest(crashed_root / "domain") == expected_tree


def test_hf_a11_recovery_refuses_changed_root_binding(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    before = _initialize(engine)
    with pytest.raises(SimulatedCrash):
        _second_transaction(engine, before, crash_at="post-intent")
    changed = TransactionEngine(
        domain_id="domain",
        domain_root=tmp_path / "domain",
        control_root=tmp_path / "control",
        target_roots={"raw": tmp_path / "domain" / "different-raw"},
    )
    with pytest.raises(RecoveryCorruption, match="root binding changed"):
        changed.recover()


@pytest.mark.parametrize("point", CRASH_POINTS)
def test_initialization_journal_covers_absent_domain_root(tmp_path: Path, point: str) -> None:
    engine = _engine(tmp_path)
    final = {"domain_id": "domain", "revision": 1, "txn": None}
    kwargs = {
        "operation": "init",
        "current_state": {},
        "next_state": final,
        "arguments": {},
        "input_hashes": {"seal": "a" * 64},
        "writes": tuple(
            PlannedWrite.from_bytes(root="raw", path=f"item-{index}", content=str(index).encode())
            for index in range(3)
        ),
    }
    with pytest.raises(SimulatedCrash):
        engine.execute(**kwargs, crash_at=point)
    if point == "pre-intent":
        with pytest.raises(PendingTransaction):
            engine.recover()
        recovered = engine.execute(**kwargs)
    else:
        recovered = engine.recover()
    assert recovered == final
    assert engine.recover() == final
    assert len(tree_manifest(tmp_path / "domain")) == 4


def test_transaction_rejects_reserved_state_and_symlink_escape(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    before = _initialize(engine)
    with pytest.raises(ContractError, match="reserved"):
        engine.execute(
            operation="bad",
            current_state=before,
            next_state={**before, "revision": 2},
            arguments={},
            input_hashes={"seal": "a" * 64},
            writes=(PlannedWrite.from_bytes(root="domain", path="state.json", content=b"bad"),),
        )
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "domain" / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ContractError, match="symlink"):
        engine.execute(
            operation="bad-link",
            current_state=before,
            next_state={**before, "revision": 2},
            arguments={},
            input_hashes={"seal": "a" * 64},
            writes=(PlannedWrite.from_bytes(root="domain", path="link/file", content=b"bad"),),
        )


def test_uninitialized_recover_has_no_intent(tmp_path: Path) -> None:
    with pytest.raises(PendingTransaction):
        _engine(tmp_path).recover()


def test_read_dependency_and_negative_existence_are_checked_before_intent(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    before = _initialize(engine)
    dependency = tmp_path / "domain" / "input.txt"
    dependency.write_bytes(b"recorded\n")
    forbidden = tmp_path / "domain" / "must-not-exist.txt"
    dependency.write_bytes(b"drifted\n")

    with pytest.raises(ContractError, match="read dependency drifted"):
        engine.execute(
            operation="dependency-check",
            current_state=before,
            next_state={**before, "revision": 2},
            arguments={},
            input_hashes={"input": sha256_bytes(b"recorded\n")},
            reads=(
                PlannedRead(
                    name="input",
                    root="domain",
                    path="input.txt",
                    expected_sha256=sha256_bytes(b"recorded\n"),
                ),
            ),
            absences=(
                PlannedAbsence(
                    name="negative_target",
                    root="domain",
                    path="must-not-exist.txt",
                ),
            ),
        )
    assert engine.read_state() == before
    dependency.write_bytes(b"recorded\n")
    forbidden.write_bytes(b"present\n")
    with pytest.raises(ContractError, match="negative-existence dependency failed"):
        engine.execute(
            operation="dependency-check",
            current_state=before,
            next_state={**before, "revision": 2},
            arguments={},
            input_hashes={"input": sha256_bytes(b"recorded\n")},
            reads=(
                PlannedRead(
                    name="input",
                    root="domain",
                    path="input.txt",
                    expected_sha256=sha256_bytes(b"recorded\n"),
                ),
            ),
            absences=(
                PlannedAbsence(
                    name="negative_target",
                    root="domain",
                    path="must-not-exist.txt",
                ),
            ),
        )
    assert engine.read_state() == before


def test_recovery_uses_recorded_intent_not_mutable_read_dependency(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    before = _initialize(engine)
    dependency = tmp_path / "domain" / "input.txt"
    dependency.write_bytes(b"recorded\n")
    kwargs = {
        "operation": "dependency-replay",
        "current_state": before,
        "next_state": {**before, "revision": 2},
        "arguments": {},
        "input_hashes": {"input": sha256_bytes(b"recorded\n")},
        "reads": (
            PlannedRead(
                name="input",
                root="domain",
                path="input.txt",
                expected_sha256=sha256_bytes(b"recorded\n"),
            ),
        ),
        "writes": (
            PlannedWrite.from_bytes(
                root="raw",
                path="recorded-output.txt",
                content=b"frozen output\n",
            ),
        ),
    }
    with pytest.raises(SimulatedCrash):
        engine.execute(**kwargs, crash_at="post-intent")
    dependency.write_bytes(b"changed-after-intent\n")

    recovered = engine.recover()

    assert recovered["revision"] == 2
    assert (tmp_path / "domain" / "raw" / "recorded-output.txt").read_bytes() == b"frozen output\n"


def test_tree_dependency_detects_added_member_before_intent(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    before = _initialize(engine)
    tree = tmp_path / "domain" / "raw" / "dependency-tree"
    tree.mkdir(parents=True)
    (tree / "a.txt").write_bytes(b"a\n")
    expected = hash_json(tree_manifest(tree))
    (tree / "added.txt").write_bytes(b"added\n")

    with pytest.raises(ContractError, match="tree dependency drifted"):
        engine.execute(
            operation="tree-dependency-check",
            current_state=before,
            next_state={**before, "revision": 2},
            arguments={},
            input_hashes={"tree": expected},
            tree_reads=(
                PlannedTreeRead(
                    name="tree",
                    root="raw",
                    path="dependency-tree",
                    expected_sha256=expected,
                ),
            ),
        )
    assert engine.read_state() == before


@pytest.mark.parametrize(
    "binding",
    ("operation_arguments", "state", "clock", "dependency_matrix"),
)
def test_dependency_common_binding_drift_is_refused_before_real_operation_intent(
    tmp_path: Path, binding: str
) -> None:
    engine = _engine(tmp_path)
    before = _initialize(engine)
    clock = "2026-08-31T12:00:00+00:00"
    arguments = {
        "clock": clock,
        "dependency_operation": "record-execution",
    }
    hashes = {
        "operation_arguments": hash_json({"clock": clock}),
        "state": hash_json(before),
        "clock": sha256_bytes(clock.encode("utf-8")),
        "dependency_matrix": default_dependency_matrix().digest,
        "prepared_job_record": "a" * 64,
        "captured_execution": "b" * 64,
    }
    hashes[binding] = "f" * 64
    with pytest.raises(ContractError, match=binding.replace("_", " ")):
        engine.execute(
            operation="record-execution",
            current_state=before,
            next_state={**before, "revision": 2},
            arguments=arguments,
            input_hashes=hashes,
        )
    assert engine.read_state() == before


def test_recovery_refuses_tampered_recorded_output_plan(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    before = _initialize(engine)
    after = {**before, "revision": 2}
    with pytest.raises(SimulatedCrash):
        engine.execute(
            operation="output-plan",
            current_state=before,
            next_state=after,
            arguments={},
            input_hashes={"input": "a" * 64},
            writes=(
                PlannedWrite.from_bytes(
                    root="raw",
                    path="planned.txt",
                    content=b"planned\n",
                ),
            ),
            crash_at="post-intent",
        )
    pending = engine.read_state()
    assert pending is not None
    pending["txn"]["next_state"]["revision"] = 999
    engine.state_path.write_bytes(canonical_bytes(pending))

    with pytest.raises(RecoveryCorruption, match="output plan"):
        engine.recover()
    assert not (tmp_path / "domain" / "raw" / "planned.txt").exists()


def test_recovery_accepts_legacy_v1_intent_without_output_plan(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    before = _initialize(engine)
    with pytest.raises(SimulatedCrash):
        engine.execute(
            operation="legacy-replay",
            current_state=before,
            next_state={**before, "revision": 2},
            arguments={"legacy": True},
            input_hashes={"input": "a" * 64},
            writes=(
                PlannedWrite.from_bytes(
                    root="raw",
                    path="legacy.txt",
                    content=b"legacy\n",
                ),
            ),
            crash_at="post-intent",
        )
    pending = engine.read_state()
    assert pending is not None
    record = pending["txn"]
    record["schema"] = "asme.transaction.v1"
    record["input_hashes"].pop("output_plan")
    record["transaction_id"] = transaction_id(
        operation=record["operation"],
        base_revision=record["base_revision"],
        arguments=record["arguments"],
        input_hashes=record["input_hashes"],
    )
    engine.state_path.write_bytes(canonical_bytes(pending))

    recovered = engine.recover()

    assert recovered["revision"] == 2
    assert (tmp_path / "domain" / "raw" / "legacy.txt").read_bytes() == b"legacy\n"
