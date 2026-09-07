"""Intent-first transactions with deterministic, idempotent recovery.

The transaction engine is deliberately runtime-neutral.  It owns no model,
network, or live-runtime behavior.  Callers provide immutable output bytes and
the complete next state before the intent is recorded.
"""

from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import fcntl
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping, Sequence

from .canonical import (
    ContractError,
    atomic_write_bytes,
    atomic_write_json,
    canonical_bytes,
    hash_json,
    require_identifier,
    safe_member_name,
    sha256_bytes,
    sha256_file,
    tree_manifest,
)
from .dependencies import default_dependency_matrix


TRANSACTION_SCHEMA_V1 = "asme.transaction.v1"
TRANSACTION_SCHEMA = "asme.transaction.v2"
INITIALIZATION_SCHEMA = "asme.initialization-intent.v1"


class PendingTransaction(ContractError):
    """A state-changing operation was attempted while recovery is required."""


class RecoveryCorruption(ContractError):
    """Recorded replay inputs or governed output state cannot be trusted."""


class SimulatedCrash(RuntimeError):
    """Deterministic test-only interruption at a declared transaction boundary."""

    def __init__(self, point: str) -> None:
        super().__init__(f"simulated crash at {point}")
        self.point = point


@dataclass(frozen=True)
class PlannedWrite:
    """One immutable regular-file output inside a named governed root."""

    root: str
    path: str
    content_base64: str
    content_sha256: str
    expected_before_sha256: str | None
    mode: int = 0o600
    allow_existing_identical: bool = False

    @classmethod
    def from_bytes(
        cls,
        *,
        root: str,
        path: str,
        content: bytes,
        expected_before_sha256: str | None = None,
        mode: int = 0o600,
        allow_existing_identical: bool = False,
    ) -> "PlannedWrite":
        require_identifier(root, field="planned write root")
        safe_member_name(path)
        if not 0 <= mode <= 0o777:
            raise ContractError("planned write mode must be in [0o000,0o777]")
        return cls(
            root=root,
            path=path,
            content_base64=base64.b64encode(content).decode("ascii"),
            content_sha256=sha256_bytes(content),
            expected_before_sha256=expected_before_sha256,
            mode=mode,
            allow_existing_identical=allow_existing_identical,
        )

    def content(self) -> bytes:
        try:
            decoded = base64.b64decode(self.content_base64, validate=True)
        except ValueError as exc:
            raise RecoveryCorruption("planned write contains invalid base64") from exc
        if sha256_bytes(decoded) != self.content_sha256:
            raise RecoveryCorruption("planned write content hash mismatch")
        return decoded


@dataclass(frozen=True)
class PlannedDeletion:
    """One hash-bound regular file to delete during replay."""

    root: str
    path: str
    expected_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.root, field="planned deletion root")
        safe_member_name(self.path)
        if len(self.expected_sha256) != 64:
            raise ContractError("planned deletion requires a SHA-256 digest")


@dataclass(frozen=True)
class PlannedRead:
    """One hash-bound read dependency verified before intent is recorded."""

    name: str
    root: str
    path: str
    expected_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.name, field="planned read dependency name")
        require_identifier(self.root, field="planned read root")
        safe_member_name(self.path)
        if len(self.expected_sha256) != 64:
            raise ContractError("planned read requires a SHA-256 digest")


@dataclass(frozen=True)
class PlannedAbsence:
    """One path that must not exist when transaction intent is recorded."""

    name: str
    root: str
    path: str

    def __post_init__(self) -> None:
        require_identifier(self.name, field="planned absence dependency name")
        require_identifier(self.root, field="planned absence root")
        safe_member_name(self.path)


@dataclass(frozen=True)
class PlannedTreeRead:
    """One exact directory-membership and content dependency checked before intent."""

    name: str
    root: str
    path: str
    expected_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.name, field="planned tree dependency name")
        require_identifier(self.root, field="planned tree root")
        safe_member_name(self.path)
        if len(self.expected_sha256) != 64:
            raise ContractError("planned tree read requires a SHA-256 digest")


@dataclass(frozen=True)
class PlannedValue:
    """One transient in-memory dependency verified before intent is recorded."""

    name: str
    content_base64: str
    content_sha256: str

    @classmethod
    def from_bytes(cls, *, name: str, content: bytes) -> "PlannedValue":
        require_identifier(name, field="planned value dependency name")
        return cls(
            name=name,
            content_base64=base64.b64encode(content).decode("ascii"),
            content_sha256=sha256_bytes(content),
        )

    def content(self) -> bytes:
        try:
            decoded = base64.b64decode(self.content_base64, validate=True)
        except ValueError as exc:
            raise ContractError("planned value contains invalid base64") from exc
        if sha256_bytes(decoded) != self.content_sha256:
            raise ContractError(f"planned value drifted before intent: {self.name}")
        return decoded


@dataclass(frozen=True)
class TransactionRecord:
    schema: str
    transaction_id: str
    domain_id: str
    operation: str
    base_revision: int
    arguments: Mapping[str, Any]
    input_hashes: Mapping[str, str]
    reads: tuple[PlannedRead, ...]
    tree_reads: tuple[PlannedTreeRead, ...]
    absences: tuple[PlannedAbsence, ...]
    writes: tuple[PlannedWrite, ...]
    deletions: tuple[PlannedDeletion, ...]
    next_state: Mapping[str, Any]
    target_roots: Mapping[str, str]

    @property
    def digest(self) -> str:
        return hash_json(asdict(self))

    def as_json(self) -> dict[str, Any]:
        # Normalize tuples and mapping implementations to their persisted JSON
        # representation so in-memory and recovered records compare exactly.
        normalized = json.loads(canonical_bytes(asdict(self)).decode("utf-8"))
        if not isinstance(normalized, dict):  # pragma: no cover - dataclass invariant
            raise RecoveryCorruption("transaction record did not serialize as an object")
        return normalized

    @classmethod
    def from_json(cls, raw: Mapping[str, Any]) -> "TransactionRecord":
        try:
            record = cls(
                schema=str(raw["schema"]),
                transaction_id=str(raw["transaction_id"]),
                domain_id=str(raw["domain_id"]),
                operation=str(raw["operation"]),
                base_revision=int(raw["base_revision"]),
                arguments=dict(raw["arguments"]),
                input_hashes=dict(raw["input_hashes"]),
                reads=tuple(PlannedRead(**item) for item in raw.get("reads", ())),
                tree_reads=tuple(
                    PlannedTreeRead(**item) for item in raw.get("tree_reads", ())
                ),
                absences=tuple(
                    PlannedAbsence(**item) for item in raw.get("absences", ())
                ),
                writes=tuple(PlannedWrite(**item) for item in raw["writes"]),
                deletions=tuple(PlannedDeletion(**item) for item in raw["deletions"]),
                next_state=dict(raw["next_state"]),
                target_roots=dict(raw["target_roots"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RecoveryCorruption("malformed transaction record") from exc
        record.validate()
        return record

    def validate(self) -> None:
        if self.schema not in {TRANSACTION_SCHEMA_V1, TRANSACTION_SCHEMA}:
            raise RecoveryCorruption(f"unsupported transaction schema: {self.schema}")
        require_identifier(self.domain_id, field="transaction domain_id")
        require_identifier(self.operation, field="transaction operation")
        if self.base_revision < 0:
            raise RecoveryCorruption("transaction base revision cannot be negative")
        if self.next_state.get("txn") is not None:
            raise RecoveryCorruption("transaction next_state must clear txn")
        if list(self.target_roots) != sorted(self.target_roots):
            raise RecoveryCorruption("transaction target roots must be sorted and unique")
        if any(not isinstance(value, str) or len(value) != 64 for value in self.target_roots.values()):
            raise RecoveryCorruption("transaction target roots require path fingerprints")
        if any(root not in self.target_roots for root in (item.root for item in self.writes)):
            raise RecoveryCorruption("planned write references an undeclared target root")
        if any(root not in self.target_roots for root in (item.root for item in self.deletions)):
            raise RecoveryCorruption("planned deletion references an undeclared target root")
        if any(root not in self.target_roots for root in (item.root for item in self.reads)):
            raise RecoveryCorruption("planned read references an undeclared target root")
        if any(
            root not in self.target_roots for root in (item.root for item in self.tree_reads)
        ):
            raise RecoveryCorruption("planned tree read references an undeclared target root")
        if any(root not in self.target_roots for root in (item.root for item in self.absences)):
            raise RecoveryCorruption("planned absence references an undeclared target root")
        write_keys = [(item.root, item.path) for item in self.writes]
        delete_keys = [(item.root, item.path) for item in self.deletions]
        if len(set(write_keys)) != len(write_keys):
            raise RecoveryCorruption("transaction contains duplicate planned writes")
        if len(set(delete_keys)) != len(delete_keys):
            raise RecoveryCorruption("transaction contains duplicate planned deletions")
        if set(write_keys) & set(delete_keys):
            raise RecoveryCorruption("transaction cannot write and delete the same path")
        expected_id = transaction_id(
            operation=self.operation,
            base_revision=self.base_revision,
            arguments=self.arguments,
            input_hashes=self.input_hashes,
        )
        if self.transaction_id != expected_id:
            raise RecoveryCorruption("transaction ID does not match its immutable inputs")
        if self.schema == TRANSACTION_SCHEMA:
            expected_output_plan = output_plan_hash(
                writes=self.writes,
                deletions=self.deletions,
                next_state=self.next_state,
            )
            if self.input_hashes.get("output_plan") != expected_output_plan:
                raise RecoveryCorruption("transaction output plan hash mismatch")
        for item in self.writes:
            item.content()


def transaction_id(
    *,
    operation: str,
    base_revision: int,
    arguments: Mapping[str, Any],
    input_hashes: Mapping[str, str],
) -> str:
    """Derive the stable transaction identifier required by the contract."""

    require_identifier(operation, field="operation")
    if base_revision < 0:
        raise ContractError("base_revision cannot be negative")
    material = {
        "operation": operation,
        "base_revision": base_revision,
        "arguments": dict(arguments),
        "input_hashes": dict(input_hashes),
    }
    return sha256_bytes(canonical_bytes(material))


def output_plan_hash(
    *,
    writes: Sequence[PlannedWrite],
    deletions: Sequence[PlannedDeletion],
    next_state: Mapping[str, Any],
) -> str:
    """Bind every planned output, deletion, and authoritative next state."""

    normalized_next = dict(next_state)
    normalized_next["txn"] = None
    return hash_json(
        {
            "writes": [asdict(item) for item in writes],
            "deletions": [asdict(item) for item in deletions],
            "next_state": normalized_next,
        }
    )


class TransactionEngine:
    """Execute and recover transactions for one domain namespace."""

    def __init__(
        self,
        *,
        domain_id: str,
        domain_root: Path,
        control_root: Path,
        target_roots: Mapping[str, Path] | None = None,
    ) -> None:
        self.domain_id = require_identifier(domain_id, field="domain_id")
        # Resolve once at configuration time.  This accepts standard macOS
        # aliases such as /var -> /private/var without permitting a later
        # symlink swap inside a governed tree.
        self.domain_root = domain_root.resolve(strict=False)
        self.control_root = control_root.resolve(strict=False)
        roots = {"domain": self.domain_root, **dict(target_roots or {})}
        for name in roots:
            require_identifier(name, field="target root name")
        if len(set(roots.values())) != len(roots):
            raise ContractError("target roots must be distinct")
        self.target_roots = roots
        self.state_path = self.domain_root / "state.json"
        namespace = f"{self.domain_id}-{self._root_fingerprint(self.domain_root)[:16]}"
        self.intent_path = self.control_root / "intents" / f"{namespace}.json"
        self.lock_path = self.control_root / "locks" / f"{namespace}.lock"
        self._validate_configured_roots()

    def _validate_configured_roots(self) -> None:
        absolute_roots = list(self.target_roots.values())
        domain = self.target_roots["domain"]
        named_roots = [root for name, root in self.target_roots.items() if name != "domain"]
        for root in absolute_roots:
            if not root.is_absolute():
                raise ContractError("all governed roots must be absolute")
        for root in named_roots:
            if domain.is_relative_to(root):
                raise ContractError("a named governed root cannot contain the domain root")
        for index, root in enumerate(named_roots):
            for other in named_roots[index + 1 :]:
                if root == other or root.is_relative_to(other) or other.is_relative_to(root):
                    raise ContractError("named governed roots cannot overlap")
        if any(
            self.control_root == root
            or self.control_root.is_relative_to(root)
            or root.is_relative_to(self.control_root)
            for root in absolute_roots
        ):
            raise ContractError("control root must be outside every governed target root")
        for root in [self.control_root, *absolute_roots]:
            self._reject_existing_symlink_components(root)

    @staticmethod
    def _reject_existing_symlink_components(path: Path) -> None:
        current = Path(path.anchor)
        for part in path.parts[1:]:
            current /= part
            if current.is_symlink():
                raise ContractError(f"symlink component forbidden: {current}")
            if not current.exists():
                break

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self._reject_existing_symlink_components(self.control_root)
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        if self.lock_path.is_symlink():
            raise ContractError("transaction lock cannot be a symlink")
        descriptor = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def read_state(self) -> dict[str, Any] | None:
        if not self.state_path.exists():
            return None
        if self.state_path.is_symlink() or not self.state_path.is_file():
            raise RecoveryCorruption("state path is not a regular non-symlink file")
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RecoveryCorruption("state file is unreadable") from exc
        if not isinstance(raw, dict):
            raise RecoveryCorruption("state file must contain a JSON object")
        return raw

    def execute(
        self,
        *,
        operation: str,
        current_state: Mapping[str, Any],
        next_state: Mapping[str, Any],
        arguments: Mapping[str, Any],
        input_hashes: Mapping[str, str],
        reads: Sequence[PlannedRead] = (),
        tree_reads: Sequence[PlannedTreeRead] = (),
        values: Sequence[PlannedValue] = (),
        absences: Sequence[PlannedAbsence] = (),
        writes: Sequence[PlannedWrite] = (),
        deletions: Sequence[PlannedDeletion] = (),
        crash_at: str | None = None,
    ) -> dict[str, Any]:
        """Record intent, replay outputs, then atomically publish next state."""

        with self._lock():
            disk_state = self.read_state()
            if disk_state is not None and disk_state.get("txn") is not None:
                raise PendingTransaction("recover the pending transaction first")
            if disk_state != (dict(current_state) if disk_state is not None else None):
                if not (disk_state is None and not current_state):
                    raise ContractError("current_state does not match authoritative state")
            normalized_hashes = dict(input_hashes)
            normalized_next = dict(next_state)
            normalized_next["txn"] = None
            planned_output_hash = output_plan_hash(
                writes=writes,
                deletions=deletions,
                next_state=normalized_next,
            )
            supplied_output_hash = normalized_hashes.get("output_plan")
            if supplied_output_hash is not None and supplied_output_hash != planned_output_hash:
                raise ContractError("supplied output plan differs from planned transaction outputs")
            normalized_hashes["output_plan"] = planned_output_hash
            if reads or tree_reads or values or absences:
                if "dependency_plan" in normalized_hashes:
                    raise ContractError("dependency_plan input hash is reserved")
                normalized_hashes["dependency_plan"] = hash_json(
                    {
                        "reads": [asdict(item) for item in reads],
                        "tree_reads": [asdict(item) for item in tree_reads],
                        "values": [
                            {"name": item.name, "content_sha256": item.content_sha256}
                            for item in values
                        ],
                        "absences": [asdict(item) for item in absences],
                    }
                )
            self._validate_dependency_bindings(
                operation=operation,
                current_state=current_state,
                arguments=arguments,
                input_hashes=normalized_hashes,
                reads=reads,
                tree_reads=tree_reads,
                values=values,
                absences=absences,
            )
            self._validate_hash_map(normalized_hashes)
            self._validate_value_preconditions(values, normalized_hashes)
            self._validate_plan_preconditions(
                writes,
                deletions,
                reads,
                tree_reads,
                absences,
            )
            base_revision = int(current_state.get("revision", 0))
            record = TransactionRecord(
                schema=TRANSACTION_SCHEMA,
                transaction_id=transaction_id(
                    operation=operation,
                    base_revision=base_revision,
                    arguments=arguments,
                    input_hashes=normalized_hashes,
                ),
                domain_id=self.domain_id,
                operation=operation,
                base_revision=base_revision,
                arguments=dict(arguments),
                input_hashes=dict(sorted(normalized_hashes.items())),
                reads=tuple(reads),
                tree_reads=tuple(tree_reads),
                absences=tuple(absences),
                writes=tuple(writes),
                deletions=tuple(deletions),
                next_state=normalized_next,
                target_roots={
                    name: self._root_fingerprint(self.target_roots[name])
                    for name in sorted(
                        {
                            item.root
                            for item in (
                                *writes,
                                *deletions,
                                *reads,
                                *tree_reads,
                                *absences,
                            )
                        }
                        | {"domain"}
                    )
                },
            )
            record.validate()
            self._crash(crash_at, "pre-intent")
            self._record_intent(record, current_state=dict(current_state), initializing=disk_state is None)
            self._crash(crash_at, "post-intent")
            return self._replay(record, crash_at=crash_at)

    def _validate_dependency_bindings(
        self,
        *,
        operation: str,
        current_state: Mapping[str, Any],
        arguments: Mapping[str, Any],
        input_hashes: Mapping[str, str],
        reads: Sequence[PlannedRead],
        tree_reads: Sequence[PlannedTreeRead],
        values: Sequence[PlannedValue],
        absences: Sequence[PlannedAbsence],
    ) -> None:
        dependency_operation = arguments.get("dependency_operation")
        if dependency_operation is None:
            return
        if not isinstance(dependency_operation, str):
            raise ContractError("dependency operation binding is invalid")
        matrix = default_dependency_matrix()
        if input_hashes.get("dependency_matrix") != matrix.digest:
            raise ContractError("dependency matrix binding drifted")
        bound_arguments = {
            key: value
            for key, value in arguments.items()
            if key != "dependency_operation"
        }
        if input_hashes.get("operation_arguments") != hash_json(bound_arguments):
            raise ContractError("operation arguments binding drifted")
        if input_hashes.get("state") != hash_json(current_state):
            raise ContractError("state binding drifted")
        clock = arguments.get("clock")
        if (
            not isinstance(clock, str)
            or input_hashes.get("clock") != sha256_bytes(clock.encode("utf-8"))
        ):
            raise ContractError("clock binding drifted")
        matrix.verify_binding_coverage(
            operation=dependency_operation,
            value_names=input_hashes,
            material_names=(item.name for item in values),
            read_names=(item.name for item in (*reads, *tree_reads)),
            absence_names=(item.name for item in absences),
        )
        for cell in matrix.operation_cells(dependency_operation):
            if cell.kind.value == "seal" and cell.name == "seal":
                if input_hashes.get("seal") != current_state.get("seal"):
                    raise ContractError("seal binding drifted")
            if cell.kind.value == "route":
                route = arguments.get("delivery_route")
                if (
                    not isinstance(route, str)
                    or input_hashes.get(cell.name) != hash_json({"route": route})
                ):
                    raise ContractError("delivery route binding drifted")

    @staticmethod
    def _validate_value_preconditions(
        values: Sequence[PlannedValue], input_hashes: Mapping[str, str]
    ) -> None:
        names = [item.name for item in values]
        if len(names) != len(set(names)):
            raise ContractError("planned values contain duplicate dependency names")
        for item in values:
            item.content()
            if input_hashes.get(item.name) != item.content_sha256:
                raise ContractError(f"planned value hash differs: {item.name}")

    def recover(self, *, crash_at: str | None = None) -> dict[str, Any]:
        """Idempotently finish a pending transaction or fail closed."""

        with self._lock():
            state = self.read_state()
            raw_record: Mapping[str, Any] | None = None
            if state is not None and state.get("txn") is not None:
                raw_record = state["txn"]
            initialization = self._read_initialization_intent()
            if raw_record is None and initialization is not None:
                final_hash = initialization.get("final_state_sha256")
                if state is not None and final_hash == sha256_bytes(canonical_bytes(state)):
                    self.intent_path.unlink(missing_ok=True)
                    self._fsync_directory(self.intent_path.parent)
                    return state
                raw_record = initialization.get("transaction")
                if state is None:
                    initial_state = initialization.get("initial_state")
                    if not isinstance(initial_state, dict):
                        raise RecoveryCorruption("initialization intent lacks initial state")
                    record = TransactionRecord.from_json(self._require_mapping(raw_record))
                    self.domain_root.mkdir(parents=True, exist_ok=True)
                    pending = dict(initial_state)
                    pending["txn"] = record.as_json()
                    atomic_write_json(self.state_path, pending)
            if raw_record is None:
                if state is not None:
                    return state
                raise PendingTransaction("no transaction is available to recover")
            record = TransactionRecord.from_json(self._require_mapping(raw_record))
            if record.domain_id != self.domain_id:
                raise RecoveryCorruption("transaction belongs to another domain")
            return self._replay(record, crash_at=crash_at)

    def _record_intent(
        self,
        record: TransactionRecord,
        *,
        current_state: dict[str, Any],
        initializing: bool,
    ) -> None:
        if initializing:
            envelope = {
                "schema": INITIALIZATION_SCHEMA,
                "domain_id": self.domain_id,
                "initial_state": current_state,
                "transaction": record.as_json(),
                "transaction_sha256": record.digest,
                "final_state_sha256": sha256_bytes(canonical_bytes(record.next_state)),
            }
            atomic_write_json(self.intent_path, envelope)
            self.domain_root.mkdir(parents=True, exist_ok=True)
        pending = dict(current_state)
        pending["txn"] = record.as_json()
        atomic_write_json(self.state_path, pending)

    def _replay(self, record: TransactionRecord, *, crash_at: str | None) -> dict[str, Any]:
        record.validate()
        for name, fingerprint in record.target_roots.items():
            configured = self.target_roots.get(name)
            if configured is None or self._root_fingerprint(configured) != fingerprint:
                raise RecoveryCorruption(f"governed root binding changed: {name}")
        state = self.read_state()
        if state is None or state.get("txn") != record.as_json():
            raise RecoveryCorruption("authoritative state does not contain the replay record")
        total_writes = len(record.writes)
        for index, item in enumerate(record.writes):
            self._materialize_write(item)
            point = index + 1
            if point == 1:
                self._crash(crash_at, "first-output")
            if total_writes > 2 and point == (total_writes + 1) // 2:
                self._crash(crash_at, "mid-output")
            if point == total_writes:
                self._crash(crash_at, "last-output")
            self._crash(crash_at, f"output:{point}")
        for item in record.deletions:
            self._materialize_deletion(item)
        self._crash(crash_at, "publication")
        self._crash(crash_at, "pre-commit")
        atomic_write_json(self.state_path, record.next_state)
        initialization = self._read_initialization_intent()
        if initialization is not None:
            if initialization.get("transaction_sha256") != record.digest:
                raise RecoveryCorruption("initialization intent conflicts with transaction")
            self.intent_path.unlink(missing_ok=True)
            self._fsync_directory(self.intent_path.parent)
        return dict(record.next_state)

    def _materialize_write(self, item: PlannedWrite) -> None:
        target = self._target(item.root, item.path)
        content = item.content()
        if target.exists() or target.is_symlink():
            if target.is_symlink() or not target.is_file():
                raise RecoveryCorruption(f"planned output is not a regular file: {item.path}")
            current_hash = sha256_file(target)
            if current_hash == item.content_sha256:
                return
            if current_hash != item.expected_before_sha256:
                raise RecoveryCorruption(f"planned output drifted after intent: {item.path}")
        elif item.expected_before_sha256 is not None:
            raise RecoveryCorruption(f"planned replacement disappeared after intent: {item.path}")
        self._ensure_safe_parent(target, root_name=item.root)
        atomic_write_bytes(target, content, mode=item.mode)
        if sha256_file(target) != item.content_sha256:
            raise RecoveryCorruption(f"planned output failed post-write hash check: {item.path}")

    def _materialize_deletion(self, item: PlannedDeletion) -> None:
        target = self._target(item.root, item.path)
        if not target.exists() and not target.is_symlink():
            return
        if target.is_symlink() or not target.is_file():
            raise RecoveryCorruption(f"planned deletion is not a regular file: {item.path}")
        if sha256_file(target) != item.expected_sha256:
            raise RecoveryCorruption(f"planned deletion drifted after intent: {item.path}")
        target.unlink()
        self._fsync_directory(target.parent)

    def _validate_plan_preconditions(
        self,
        writes: Sequence[PlannedWrite],
        deletions: Sequence[PlannedDeletion],
        reads: Sequence[PlannedRead],
        tree_reads: Sequence[PlannedTreeRead],
        absences: Sequence[PlannedAbsence],
    ) -> None:
        keys: set[tuple[str, str]] = set()
        for item in (*writes, *deletions):
            if item.root not in self.target_roots:
                raise ContractError(f"unknown governed root: {item.root}")
            if item.root == "domain" and item.path == "state.json":
                raise ContractError("state.json is reserved for the transaction engine")
            key = (item.root, item.path)
            if key in keys:
                raise ContractError(f"duplicate transaction target: {item.root}:{item.path}")
            keys.add(key)
        for item in writes:
            target = self._target(item.root, item.path)
            if target.exists() or target.is_symlink():
                if target.is_symlink() or not target.is_file():
                    raise ContractError(f"planned write target is not a regular file: {item.path}")
                actual = sha256_file(target)
                if actual == item.content_sha256 and item.allow_existing_identical:
                    continue
                if item.expected_before_sha256 is None or actual != item.expected_before_sha256:
                    raise ContractError(f"planned write precondition failed: {item.path}")
            elif item.expected_before_sha256 is not None:
                raise ContractError(f"planned replacement target is missing: {item.path}")
        for item in deletions:
            target = self._target(item.root, item.path)
            if target.is_symlink() or not target.is_file():
                raise ContractError(f"planned deletion target is missing or unsafe: {item.path}")
            if sha256_file(target) != item.expected_sha256:
                raise ContractError(f"planned deletion precondition failed: {item.path}")
        for item in reads:
            if item.root not in self.target_roots:
                raise ContractError(f"unknown governed root: {item.root}")
            target = self._target(item.root, item.path)
            if target.is_symlink() or not target.is_file():
                raise ContractError(f"read dependency is missing or unsafe: {item.name}")
            if sha256_file(target) != item.expected_sha256:
                raise ContractError(f"read dependency drifted: {item.name}")
        for item in tree_reads:
            if item.root not in self.target_roots:
                raise ContractError(f"unknown governed root: {item.root}")
            target = self._target(item.root, item.path)
            if target.is_symlink() or not target.is_dir():
                raise ContractError(f"tree dependency is missing or unsafe: {item.name}")
            if hash_json(tree_manifest(target)) != item.expected_sha256:
                raise ContractError(f"tree dependency drifted: {item.name}")
        for item in absences:
            if item.root not in self.target_roots:
                raise ContractError(f"unknown governed root: {item.root}")
            target = self._target(item.root, item.path)
            if target.exists() or target.is_symlink():
                raise ContractError(f"negative-existence dependency failed: {item.name}")

    def _target(self, root_name: str, member: str) -> Path:
        safe_member_name(member)
        root = self.target_roots.get(root_name)
        if root is None:
            raise RecoveryCorruption(f"transaction references unknown root: {root_name}")
        target = root.joinpath(*PurePosixPath(member).parts)
        self._reject_existing_symlink_components(target)
        return target

    def _ensure_safe_parent(self, target: Path, *, root_name: str) -> None:
        root = self.target_roots[root_name]
        relative_parent = target.parent.relative_to(root)
        current = root
        if not current.exists():
            current.mkdir(parents=True, exist_ok=True)
        if current.is_symlink() or not current.is_dir():
            raise RecoveryCorruption(f"governed root is unsafe: {current}")
        for part in relative_parent.parts:
            current /= part
            if current.is_symlink():
                raise RecoveryCorruption(f"symlink parent forbidden: {current}")
            if current.exists() and not current.is_dir():
                raise RecoveryCorruption(f"non-directory parent forbidden: {current}")
            current.mkdir(exist_ok=True)

    def _read_initialization_intent(self) -> dict[str, Any] | None:
        if not self.intent_path.exists():
            return None
        if self.intent_path.is_symlink() or not self.intent_path.is_file():
            raise RecoveryCorruption("initialization intent is not a regular file")
        try:
            raw = json.loads(self.intent_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RecoveryCorruption("initialization intent is unreadable") from exc
        if not isinstance(raw, dict) or raw.get("schema") != INITIALIZATION_SCHEMA:
            raise RecoveryCorruption("initialization intent schema is invalid")
        if raw.get("domain_id") != self.domain_id:
            raise RecoveryCorruption("initialization intent belongs to another domain")
        record = TransactionRecord.from_json(self._require_mapping(raw.get("transaction")))
        if raw.get("transaction_sha256") != record.digest:
            raise RecoveryCorruption("initialization intent hash mismatch")
        return raw

    @staticmethod
    def _validate_hash_map(values: Mapping[str, str]) -> None:
        for name, digest in values.items():
            if not isinstance(name, str) or not name or not isinstance(digest, str) or len(digest) != 64:
                raise ContractError("input_hashes must map non-empty names to SHA-256 digests")

    @staticmethod
    def _root_fingerprint(path: Path) -> str:
        return sha256_bytes(b"asme.root.v1\0" + os.fsencode(path))

    @staticmethod
    def _require_mapping(value: Any) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise RecoveryCorruption("expected a JSON object")
        return value

    @staticmethod
    def _crash(requested: str | None, actual: str) -> None:
        if requested == actual:
            raise SimulatedCrash(actual)

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        if not path.exists():
            return
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
