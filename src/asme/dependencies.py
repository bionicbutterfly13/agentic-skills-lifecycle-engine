"""Versioned dependency matrix used for pre-mutation drift checks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, Mapping, Sequence

from .canonical import ContractError, hash_json, require_identifier


DEPENDENCY_MATRIX_VERSION = "asme.dependencies.v1"


class DependencyKind(StrEnum):
    ARGUMENT = "argument"
    CLOCK = "clock"
    DYNAMIC_INPUT = "dynamic_input"
    NEGATIVE_EXISTENCE = "negative_existence"
    OUTPUT = "output"
    ROUTE = "route"
    SEAL = "seal"
    STATE = "state"
    REPLAY_SOURCE = "replay_source"


@dataclass(frozen=True)
class DependencyCell:
    cell_id: str
    operation: str
    kind: DependencyKind
    name: str
    required: bool = True
    source_class: str = "ARCHITECTURE"

    def __post_init__(self) -> None:
        require_identifier(self.cell_id, field="dependency cell_id")
        require_identifier(self.operation, field="dependency operation")
        if not self.name.strip():
            raise ContractError("dependency name cannot be blank")


@dataclass(frozen=True)
class DependencyMatrix:
    cells: tuple[DependencyCell, ...]
    version: str = DEPENDENCY_MATRIX_VERSION

    def __post_init__(self) -> None:
        ids = [cell.cell_id for cell in self.cells]
        if len(ids) != len(set(ids)):
            raise ContractError("dependency matrix cell IDs must be unique")
        operations = {cell.operation for cell in self.cells}
        for operation in operations:
            kinds = {cell.kind for cell in self.cells if cell.operation == operation}
            missing = {
                DependencyKind.ARGUMENT,
                DependencyKind.CLOCK,
                DependencyKind.STATE,
            } - kinds
            if missing:
                raise ContractError(
                    f"dependency operation {operation} lacks common cells: {sorted(missing)}"
                )

    @property
    def digest(self) -> str:
        return hash_json(
            {
                "version": self.version,
                "cells": [
                    {
                        "cell_id": cell.cell_id,
                        "operation": cell.operation,
                        "kind": cell.kind.value,
                        "name": cell.name,
                        "required": cell.required,
                        "source_class": cell.source_class,
                    }
                    for cell in self.cells
                ],
            }
        )

    def operation_cells(self, operation: str) -> tuple[DependencyCell, ...]:
        selected = tuple(cell for cell in self.cells if cell.operation == operation)
        if not selected:
            raise ContractError(f"operation absent from dependency matrix: {operation}")
        return selected

    def verify_hashes(
        self,
        *,
        operation: str,
        recorded: Mapping[str, str],
        current: Mapping[str, str],
        negative_existence: Mapping[str, bool],
    ) -> None:
        """Refuse any missing, changed, or newly-existing required dependency."""

        for cell in self.operation_cells(operation):
            if not cell.required:
                continue
            if cell.kind is DependencyKind.NEGATIVE_EXISTENCE:
                if negative_existence.get(cell.name) is not True:
                    raise ContractError(f"negative-existence predicate failed: {cell.name}")
                continue
            if cell.name not in recorded or cell.name not in current:
                raise ContractError(f"dependency hash is missing: {cell.name}")
            if recorded[cell.name] != current[cell.name]:
                raise ContractError(f"dependency drift detected: {cell.name}")

    def verify_fixture_coverage(self, fixture_cell_ids: Iterable[str]) -> None:
        """Require one mutation fixture for every required dependency cell."""

        expected = {cell.cell_id for cell in self.cells if cell.required}
        supplied = set(fixture_cell_ids)
        missing = sorted(expected - supplied)
        extra = sorted(supplied - expected)
        if missing or extra:
            raise ContractError(f"dependency fixture coverage mismatch: missing={missing}, extra={extra}")

    def verify_binding_coverage(
        self,
        *,
        operation: str,
        value_names: Iterable[str],
        material_names: Iterable[str],
        read_names: Iterable[str],
        absence_names: Iterable[str],
    ) -> None:
        """Require every matrix cell to have the correct pre-intent binding class."""

        cells = tuple(cell for cell in self.operation_cells(operation) if cell.required)
        common = {
            "operation_arguments",
            "state",
            "clock",
        }
        values = set(value_names)
        materials = set(material_names)
        reads = set(read_names)
        absences = set(absence_names)
        expected_absences = {
            cell.name for cell in cells if cell.kind is DependencyKind.NEGATIVE_EXISTENCE
        }
        expected_dynamic = {
            cell.name
            for cell in cells
            if cell.kind is DependencyKind.DYNAMIC_INPUT
        }
        expected_positive = {
            cell.name
            for cell in cells
            if cell.kind
            not in {DependencyKind.NEGATIVE_EXISTENCE, DependencyKind.DYNAMIC_INPUT}
        } - common
        missing_positive = sorted(
            (expected_positive - values - reads)
            | (expected_dynamic - materials - reads)
        )
        missing_absence = sorted(expected_absences - absences)
        unexpected_absence = sorted(absences - expected_absences)
        if missing_positive or missing_absence or unexpected_absence:
            raise ContractError(
                "dependency binding coverage mismatch: "
                f"missing_positive={missing_positive}, "
                f"missing_absence={missing_absence}, "
                f"unexpected_absence={unexpected_absence}"
            )


_OPERATION_INPUTS: Mapping[str, tuple[tuple[DependencyKind, str], ...]] = {
    "prepare-rollout": ((DependencyKind.SEAL, "seal"), (DependencyKind.DYNAMIC_INPUT, "named_snapshot")),
    "record-execution": (
        (DependencyKind.DYNAMIC_INPUT, "prepared_job_record"),
        (DependencyKind.DYNAMIC_INPUT, "captured_execution"),
    ),
    "ingest-rollout": (
        (DependencyKind.SEAL, "seal"),
        (DependencyKind.DYNAMIC_INPUT, "prompts"),
        (DependencyKind.DYNAMIC_INPUT, "submitted_outputs"),
    ),
    "reset-manifest": (
        (DependencyKind.DYNAMIC_INPUT, "manifest"),
        (DependencyKind.DYNAMIC_INPUT, "manifest_sidecars"),
    ),
    "baseline-finalize": (
        (DependencyKind.DYNAMIC_INPUT, "baseline_manifest"),
        (DependencyKind.DYNAMIC_INPUT, "baseline_sidecars"),
    ),
    "sample": (
        (DependencyKind.DYNAMIC_INPUT, "train_manifest"),
        (DependencyKind.DYNAMIC_INPUT, "raw_traces"),
        (DependencyKind.DYNAMIC_INPUT, "raw_sidecars"),
        (DependencyKind.DYNAMIC_INPUT, "wiki"),
    ),
    "apply-wiki": (
        (DependencyKind.DYNAMIC_INPUT, "maintainer_output"),
        (DependencyKind.DYNAMIC_INPUT, "maintainer_input"),
        (DependencyKind.DYNAMIC_INPUT, "wiki"),
        (DependencyKind.DYNAMIC_INPUT, "train_manifest"),
    ),
    "proposer-context": (
        (DependencyKind.DYNAMIC_INPUT, "wiki"),
        (DependencyKind.DYNAMIC_INPUT, "train_manifest"),
        (DependencyKind.DYNAMIC_INPUT, "raw_sidecars"),
        (DependencyKind.DYNAMIC_INPUT, "train_answers"),
        (DependencyKind.DYNAMIC_INPUT, "active_snapshot"),
    ),
    "apply-proposal": (
        (DependencyKind.DYNAMIC_INPUT, "proposal_output"),
        (DependencyKind.DYNAMIC_INPUT, "active_snapshot"),
        (DependencyKind.SEAL, "seal_markers"),
    ),
    "gate": (
        (DependencyKind.DYNAMIC_INPUT, "evaluation_manifests"),
        (DependencyKind.DYNAMIC_INPUT, "evaluation_sidecars"),
        (DependencyKind.DYNAMIC_INPUT, "candidate_snapshot"),
        (DependencyKind.DYNAMIC_INPUT, "active_snapshot"),
        (DependencyKind.DYNAMIC_INPUT, "provisional"),
    ),
    "abandon": (
        (DependencyKind.DYNAMIC_INPUT, "evaluation_manifests"),
        (DependencyKind.DYNAMIC_INPUT, "evaluation_sidecars"),
        (DependencyKind.DYNAMIC_INPUT, "candidate_snapshot"),
        (DependencyKind.DYNAMIC_INPUT, "provisional"),
    ),
    "export": (
        (DependencyKind.DYNAMIC_INPUT, "test_manifests"),
        (DependencyKind.DYNAMIC_INPUT, "test_sidecars"),
        (DependencyKind.DYNAMIC_INPUT, "active_snapshot"),
        (DependencyKind.SEAL, "seal"),
        (DependencyKind.ROUTE, "delivery_route"),
        (DependencyKind.NEGATIVE_EXISTENCE, "existing_staging_target"),
    ),
    "package-untested": (
        (DependencyKind.DYNAMIC_INPUT, "active_snapshot"),
        (DependencyKind.DYNAMIC_INPUT, "untested_approval"),
        (DependencyKind.SEAL, "seal"),
        (DependencyKind.ROUTE, "delivery_route"),
        (DependencyKind.NEGATIVE_EXISTENCE, "test_artifacts_absent"),
        (DependencyKind.NEGATIVE_EXISTENCE, "existing_staging_target"),
    ),
    "recover": ((DependencyKind.REPLAY_SOURCE, "state_transaction"),),
}


def default_dependency_matrix() -> DependencyMatrix:
    cells: list[DependencyCell] = []
    sequence = 1
    for operation, specific in _OPERATION_INPUTS.items():
        common: Sequence[tuple[DependencyKind, str]] = (
            (DependencyKind.ARGUMENT, "operation_arguments"),
            (DependencyKind.STATE, "state"),
            (DependencyKind.CLOCK, "clock"),
            (DependencyKind.OUTPUT, "output_plan"),
        )
        for kind, name in (*common, *specific):
            cells.append(
                DependencyCell(
                    cell_id=f"dep-{sequence:03d}",
                    operation=operation,
                    kind=kind,
                    name=name,
                )
            )
            sequence += 1
    return DependencyMatrix(tuple(cells))
