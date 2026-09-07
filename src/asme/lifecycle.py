"""Total lifecycle transition table with explicit refusal paths."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, Mapping

from .canonical import ContractError, hash_json
from .contract import LifecycleState, Route


class TransitionRefused(ContractError):
    """An operation is not legal in the current lifecycle state."""


OPERATIONS = (
    "init",
    "seed-observations",
    "rollback-seed",
    "skip-seed",
    "baseline-finalize",
    "train-ingest",
    "apply-wiki",
    "apply-proposal-change",
    "apply-proposal-no-action",
    "val-ingest",
    "gate",
    "confirm-ingest",
    "abandon",
    "test-prepare",
    "test-ingest",
    "export",
    "package-untested",
    "reset-manifest",
    "recover",
    "status",
)

STATE_SCHEMA = "asme.state.v1"


@dataclass(frozen=True)
class DomainState:
    domain_id: str
    seal: str
    state: LifecycleState = LifecycleState.UNINITIALIZED
    revision: int = 0
    iteration: int = 0
    max_iterations: int = 1
    best_score: float | None = None
    active_snapshot_hash: str | None = None
    candidate_snapshot_hash: str | None = None
    provisional_score: float | None = None
    confirmation_score: float | None = None
    provisional_manifest_hash: str | None = None
    gate_phase: str | None = None
    current_manifest_hash: str | None = None
    current_manifest_phase: str | None = None
    consumed_manifests: tuple[Mapping[str, str], ...] = ()
    route: Route | None = None
    validated_step: str | None = None
    prepared_test_phases: tuple[str, ...] = ()
    test_manifests: tuple[Mapping[str, str], ...] = ()
    delivery_ledger: tuple[Mapping[str, Any], ...] = ()
    seed_decision: str | None = None
    seeded_observation_ids: tuple[str, ...] = ()
    txn: Mapping[str, Any] | None = None
    history: tuple[Mapping[str, Any], ...] = ()
    state_schema: str = STATE_SCHEMA

    @property
    def digest(self) -> str:
        return hash_json(asdict(self))


@dataclass(frozen=True)
class TransitionInput:
    valid: bool | None = None
    score: float | None = None
    snapshot_hash: str | None = None
    approval_present: bool = False
    approval_id: str | None = None
    approval_hash: str | None = None
    approval_record_hash: str | None = None
    delivery_id: str | None = None
    observation_ids: tuple[str, ...] = ()
    phase: str | None = None
    manifest_hash: str | None = None


def _advance_iteration(state: DomainState) -> DomainState:
    perfect = state.best_score == 1.0
    next_iteration = state.iteration if perfect else state.iteration + 1
    next_state = (
        LifecycleState.DONE
        if perfect or next_iteration > state.max_iterations
        else LifecycleState.NEEDS_TRAIN_RUN
    )
    return replace(
        state,
        state=next_state,
        iteration=next_iteration,
        candidate_snapshot_hash=None,
        provisional_score=None,
        confirmation_score=None,
        provisional_manifest_hash=None,
        gate_phase=None,
        current_manifest_hash=None,
        current_manifest_phase=None,
    )


def _require_score(value: float | None) -> float:
    if value is None or isinstance(value, bool) or not 0.0 <= value <= 1.0:
        raise TransitionRefused("operation requires a finite score in [0,1]")
    return float(value)


def _require_manifest_hash(value: str | None, *, phase: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise TransitionRefused(f"{phase} requires a manifest SHA-256")
    try:
        bytes.fromhex(value)
    except ValueError as exc:
        raise TransitionRefused(f"{phase} requires a manifest SHA-256") from exc
    return value


def _consume_manifest(state: DomainState, manifest_hash: str, *, by: str) -> DomainState:
    if any(item.get("manifest_hash") == manifest_hash for item in state.consumed_manifests):
        raise TransitionRefused("manifest has already been consumed")
    return replace(
        state,
        consumed_manifests=state.consumed_manifests
        + ({"manifest_hash": manifest_hash, "by": by},),
    )


def _record_current_manifest(
    state: DomainState, supplied: TransitionInput, *, phase: str
) -> DomainState:
    if supplied.phase != phase:
        raise TransitionRefused(f"manifest phase must be {phase}")
    manifest_hash = _require_manifest_hash(supplied.manifest_hash, phase=phase)
    if any(item.get("manifest_hash") == manifest_hash for item in state.consumed_manifests):
        raise TransitionRefused("manifest has already been consumed")
    return replace(
        state,
        current_manifest_hash=manifest_hash,
        current_manifest_phase=phase,
    )


def transition(
    current: DomainState,
    operation: str,
    supplied: TransitionInput | None = None,
) -> DomainState:
    """Return the next state or a stable refusal without mutating current."""

    supplied = supplied or TransitionInput()
    if operation not in OPERATIONS:
        raise TransitionRefused(f"unknown operation: {operation}")
    if operation == "status":
        return current
    if operation == "recover":
        if current.txn is None:
            raise TransitionRefused("recover requires a recorded transaction")
        return current

    state = current.state
    result: DomainState
    if operation == "init" and state is LifecycleState.UNINITIALIZED:
        result = replace(current, state=LifecycleState.NEEDS_OPTIONAL_SEED)
    elif operation in {"seed-observations", "skip-seed"} and state is LifecycleState.NEEDS_OPTIONAL_SEED:
        if operation == "seed-observations" and not supplied.approval_present:
            raise TransitionRefused("seed-observations requires a scoped approval record")
        if operation == "seed-observations":
            if (
                not supplied.observation_ids
                or len(supplied.observation_ids) != len(set(supplied.observation_ids))
                or any(not item.strip() for item in supplied.observation_ids)
            ):
                raise TransitionRefused("seed-observations requires named unique observation IDs")
            result = replace(
                current,
                state=LifecycleState.NEEDS_BASELINE_RUN,
                seed_decision="seeded",
                seeded_observation_ids=tuple(sorted(supplied.observation_ids)),
            )
        else:
            if supplied.observation_ids:
                raise TransitionRefused("skip-seed cannot carry observation IDs")
            result = replace(
                current,
                state=LifecycleState.NEEDS_BASELINE_RUN,
                seed_decision="skipped",
            )
    elif operation == "rollback-seed" and state is LifecycleState.NEEDS_BASELINE_RUN:
        if current.seed_decision != "seeded" or not current.seeded_observation_ids:
            raise TransitionRefused("rollback-seed requires an applied observation seed")
        result = replace(
            current,
            state=LifecycleState.NEEDS_OPTIONAL_SEED,
            seed_decision=None,
            seeded_observation_ids=(),
        )
    elif operation == "baseline-finalize" and state is LifecycleState.NEEDS_BASELINE_RUN:
        if supplied.valid is not True:
            return current
        if supplied.phase != "baseline":
            raise TransitionRefused("baseline-finalize requires the baseline manifest")
        manifest_hash = _require_manifest_hash(supplied.manifest_hash, phase="baseline")
        score = _require_score(supplied.score)
        if not supplied.snapshot_hash:
            raise TransitionRefused("baseline-finalize requires a snapshot hash")
        result = _consume_manifest(
            replace(
            current,
            best_score=score,
            active_snapshot_hash=supplied.snapshot_hash,
            iteration=1,
            state=LifecycleState.DONE if score == 1.0 else LifecycleState.NEEDS_TRAIN_RUN,
            ),
            manifest_hash,
            by="baseline-finalize",
        )
    elif operation == "train-ingest" and state is LifecycleState.NEEDS_TRAIN_RUN:
        result = (
            current
            if supplied.valid is not True
            else replace(
                _record_current_manifest(current, supplied, phase="train"),
                state=LifecycleState.NEEDS_WIKI,
            )
        )
    elif operation == "apply-wiki" and state is LifecycleState.NEEDS_WIKI:
        if current.current_manifest_phase != "train" or current.current_manifest_hash is None:
            raise TransitionRefused("apply-wiki requires an unconsumed train manifest")
        result = _consume_manifest(
            replace(
                current,
                state=LifecycleState.NEEDS_PROPOSAL,
                current_manifest_hash=None,
                current_manifest_phase=None,
            ),
            current.current_manifest_hash,
            by="apply-wiki",
        )
    elif operation == "apply-proposal-change" and state is LifecycleState.NEEDS_PROPOSAL:
        if not supplied.snapshot_hash:
            raise TransitionRefused("a changed proposal requires a candidate snapshot hash")
        result = replace(
            current,
            candidate_snapshot_hash=supplied.snapshot_hash,
            state=LifecycleState.NEEDS_VAL_RUN,
        )
    elif operation == "apply-proposal-no-action" and state is LifecycleState.NEEDS_PROPOSAL:
        result = _advance_iteration(current)
    elif operation == "val-ingest" and state is LifecycleState.NEEDS_VAL_RUN:
        if supplied.valid is not True:
            return current
        result = replace(
            _record_current_manifest(current, supplied, phase="val"),
            provisional_score=_require_score(supplied.score),
            gate_phase="validation",
            state=LifecycleState.NEEDS_GATE,
        )
    elif operation == "confirm-ingest" and state is LifecycleState.NEEDS_VAL_CONFIRM:
        if supplied.valid is not True:
            return current
        result = replace(
            _record_current_manifest(current, supplied, phase="val_confirm"),
            confirmation_score=_require_score(supplied.score),
            gate_phase="confirmation",
            state=LifecycleState.NEEDS_GATE,
        )
    elif operation == "gate" and state is LifecycleState.NEEDS_GATE:
        candidate = _require_score(
            current.confirmation_score
            if current.gate_phase == "confirmation"
            else current.provisional_score
        )
        if current.best_score is None:
            raise TransitionRefused("gate requires an established best score")
        strict_win = candidate > current.best_score
        if current.gate_phase == "validation" and strict_win:
            if current.current_manifest_phase != "val" or current.current_manifest_hash is None:
                raise TransitionRefused("validation gate requires an unconsumed val manifest")
            manifest_hash = current.current_manifest_hash
            result = _consume_manifest(
                replace(
                    current,
                    state=LifecycleState.NEEDS_VAL_CONFIRM,
                    provisional_manifest_hash=manifest_hash,
                    current_manifest_hash=None,
                    current_manifest_phase=None,
                ),
                manifest_hash,
                by="gate-validation",
            )
        elif current.gate_phase == "confirmation" and strict_win:
            if not current.candidate_snapshot_hash:
                raise TransitionRefused("accepted candidate has no snapshot hash")
            if (
                current.provisional_manifest_hash is None
                or current.provisional_score is None
                or current.current_manifest_phase != "val_confirm"
                or current.current_manifest_hash is None
            ):
                raise TransitionRefused("confirmation gate requires both validation manifests")
            confirmed = _consume_manifest(
                current,
                current.current_manifest_hash,
                by="gate-confirmation",
            )
            result = _advance_iteration(
                replace(
                    confirmed,
                    best_score=min(_require_score(current.provisional_score), candidate),
                    active_snapshot_hash=current.candidate_snapshot_hash,
                )
            )
        else:
            if current.current_manifest_hash is None or current.current_manifest_phase not in {
                "val",
                "val_confirm",
            }:
                raise TransitionRefused("rejection gate requires an unconsumed validation manifest")
            rejected = _consume_manifest(
                current,
                current.current_manifest_hash,
                by=(
                    "gate-validation-reject"
                    if current.gate_phase == "validation"
                    else "gate-confirmation-reject"
                ),
            )
            result = _advance_iteration(rejected)
    elif operation == "abandon" and state in {
        LifecycleState.NEEDS_VAL_RUN,
        LifecycleState.NEEDS_GATE,
        LifecycleState.NEEDS_VAL_CONFIRM,
    }:
        if not current.candidate_snapshot_hash:
            raise TransitionRefused("abandon requires a candidate snapshot")
        abandoned = current
        if current.current_manifest_hash is not None:
            if current.current_manifest_phase not in {"val", "val_confirm"}:
                raise TransitionRefused("abandon found an unexpected owned manifest")
            abandoned = _consume_manifest(
                current,
                current.current_manifest_hash,
                by="abandon",
            )
        result = _advance_iteration(abandoned)
    elif operation == "test-prepare" and state is LifecycleState.DONE:
        if supplied.phase not in {"test-baseline", "test-final"}:
            raise TransitionRefused("test prepare requires test-baseline or test-final")
        if current.route not in {None, Route.VALIDATED}:
            raise TransitionRefused("validated route conflicts with latched untested route")
        if any(item.get("phase") == supplied.phase for item in current.test_manifests):
            raise TransitionRefused("test phase is already ingested")
        if supplied.phase in current.prepared_test_phases:
            result = current
        else:
            phases = tuple(sorted((*current.prepared_test_phases, supplied.phase)))
            result = replace(
                current,
                route=Route.VALIDATED,
                validated_step="prepared",
                prepared_test_phases=phases,
            )
    elif operation == "test-ingest" and state is LifecycleState.DONE:
        if (
            current.route is not Route.VALIDATED
            or supplied.phase not in current.prepared_test_phases
        ):
            raise TransitionRefused("test ingest requires the validated prepared step")
        manifest_hash = _require_manifest_hash(supplied.manifest_hash, phase=str(supplied.phase))
        if any(item.get("phase") == supplied.phase for item in current.test_manifests):
            raise TransitionRefused("test manifest phase is already recorded")
        result = (
            replace(
                current,
                validated_step=(
                    "ingested"
                    if {item.get("phase") for item in current.test_manifests}
                    | {supplied.phase}
                    == {"test-baseline", "test-final"}
                    else "prepared"
                ),
                test_manifests=current.test_manifests
                + ({"phase": str(supplied.phase), "manifest_hash": manifest_hash},),
            )
            if supplied.valid is True
            else current
        )
    elif operation == "export" and state is LifecycleState.DONE:
        if current.route is not Route.VALIDATED:
            raise TransitionRefused("export requires valid ingested test evidence")
        if supplied.valid is not True or not supplied.delivery_id:
            raise TransitionRefused("export requires valid evidence and a delivery identity")
        matching = [
            item for item in current.delivery_ledger if item.get("delivery_id") == supplied.delivery_id
        ]
        if current.validated_step == "exported":
            if len(matching) == 1 and matching[0].get("route") == Route.VALIDATED.value:
                return current
            raise TransitionRefused("validated export is already latched to another identity")
        by_phase = {item.get("phase"): item.get("manifest_hash") for item in current.test_manifests}
        if set(by_phase) != {"test-baseline", "test-final"}:
            raise TransitionRefused("export requires both test manifests")
        if current.validated_step != "ingested":
            raise TransitionRefused("export requires valid ingested test evidence")
        consumed = current
        for phase in ("test-baseline", "test-final"):
            consumed = _consume_manifest(
                consumed,
                str(by_phase[phase]),
                by=f"export:{supplied.delivery_id}",
            )
        entry = {"delivery_id": supplied.delivery_id, "route": Route.VALIDATED.value}
        result = replace(
            consumed,
            validated_step="exported",
            delivery_ledger=consumed.delivery_ledger + (entry,),
        )
    elif operation == "package-untested" and state is LifecycleState.DONE:
        if not supplied.approval_present:
            raise TransitionRefused("untested route requires action-time approval")
        if current.route not in {None, Route.UNTESTED}:
            raise TransitionRefused("untested route conflicts with latched validated route")
        if current.prepared_test_phases or current.test_manifests:
            raise TransitionRefused("untested route requires no prepared test artifacts")
        if not supplied.delivery_id:
            raise TransitionRefused("untested route requires a delivery identity")
        if not supplied.approval_id:
            raise TransitionRefused("untested route requires an approval identity")
        approval_hash = _require_manifest_hash(
            supplied.approval_hash, phase="package-untested approval"
        )
        approval_record_hash = _require_manifest_hash(
            supplied.approval_record_hash,
            phase="package-untested approval record",
        )
        matching = [
            item for item in current.delivery_ledger if item.get("delivery_id") == supplied.delivery_id
        ]
        entry = {
            "delivery_id": supplied.delivery_id,
            "route": Route.UNTESTED.value,
            "approval_id": supplied.approval_id,
            "approval_hash": approval_hash,
            "approval_record_hash": approval_record_hash,
        }
        if current.route is Route.UNTESTED:
            if len(matching) == 1 and dict(matching[0]) == entry:
                return current
            raise TransitionRefused("untested package is already latched to another identity")
        result = replace(current, route=Route.UNTESTED, delivery_ledger=current.delivery_ledger + (entry,))
    elif operation == "reset-manifest" and state in {
        LifecycleState.NEEDS_BASELINE_RUN,
        LifecycleState.NEEDS_TRAIN_RUN,
        LifecycleState.NEEDS_WIKI,
        LifecycleState.NEEDS_VAL_RUN,
        LifecycleState.NEEDS_VAL_CONFIRM,
        LifecycleState.DONE,
    }:
        result = replace(
            current,
            state=(
                LifecycleState.NEEDS_TRAIN_RUN
                if state is LifecycleState.NEEDS_WIKI
                else current.state
            ),
            current_manifest_hash=None,
            current_manifest_phase=None,
        )
    else:
        raise TransitionRefused(f"{operation} is refused in {state.value}")

    if result is current:
        return current
    event = {
        "operation": operation,
        "from": state.value,
        "to": result.state.value,
        "source_class": "ARCHITECTURE",
    }
    return replace(result, revision=current.revision + 1, history=current.history + (event,))


def transition_matrix() -> dict[str, dict[str, str]]:
    """Enumerate one deterministic disposition for every state/operation pair."""

    matrix: dict[str, dict[str, str]] = {}
    for state_value in LifecycleState:
        seed = DomainState("matrix", "0" * 64, state=state_value, best_score=0.0)
        row: dict[str, str] = {}
        for operation in OPERATIONS:
            try:
                target = transition(seed, operation)
                row[operation] = f"transition:{target.state.value}"
            except TransitionRefused as exc:
                row[operation] = f"refused:{exc}"
        matrix[state_value.value] = row
    return matrix
