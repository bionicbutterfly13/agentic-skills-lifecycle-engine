"""Fail-closed extractor and scorer subprocess contracts."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping

from .canonical import ContractError, require_regular_file, sha256_bytes


EVALUATION_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class EvaluationResult:
    valid: bool
    output_hash: str
    prediction: Any | None = None
    score: float | None = None
    error_class: str | None = None
    error_message: str | None = None


def _run_program(path: Path, payload: Mapping[str, Any], *, timeout: float) -> str:
    executable = require_regular_file(path)
    env = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONIOENCODING": "utf-8",
    }
    try:
        completed = subprocess.run(
            [str(executable)],
            input=json.dumps(payload, ensure_ascii=False, allow_nan=False),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise ContractError(f"program timeout after {timeout}s") from exc
    if completed.returncode != 0:
        raise ContractError(f"program exited with status {completed.returncode}")
    output = completed.stdout
    if not output.strip():
        raise ContractError("program produced empty output")
    return output


def evaluate_output(
    *,
    returned_output: str,
    expected: Any,
    extractor: Path,
    scorer: Path,
) -> EvaluationResult:
    """Bind evaluation to returned output and never synthesize a failure score."""

    output_hash = sha256_bytes(returned_output.encode("utf-8"))
    try:
        extracted_text = _run_program(
            extractor,
            {"returned_output": returned_output, "returned_output_hash": output_hash},
            timeout=EVALUATION_TIMEOUT_SECONDS,
        )
        try:
            extracted = json.loads(extracted_text)
        except json.JSONDecodeError as exc:
            raise ContractError("extractor output is malformed JSON") from exc
        if not isinstance(extracted, dict) or set(extracted) != {
            "returned_output_hash",
            "prediction",
        }:
            raise ContractError("extractor must emit exactly output hash and prediction")
        if extracted["returned_output_hash"] != output_hash:
            raise ContractError("extractor result is bound to the wrong output hash")
        scored_text = _run_program(
            scorer,
            {
                "returned_output_hash": output_hash,
                "prediction": extracted["prediction"],
                "expected": expected,
            },
            timeout=EVALUATION_TIMEOUT_SECONDS,
        )
        if len(scored_text.strip().splitlines()) != 1:
            raise ContractError("scorer output is ambiguous or multiline")
        try:
            score = float(scored_text.strip())
        except ValueError as exc:
            raise ContractError("scorer output is not numeric") from exc
        if not math.isfinite(score) or not 0.0 <= score <= 1.0:
            raise ContractError("scorer output must be finite and within [0,1]")
        return EvaluationResult(True, output_hash, extracted["prediction"], score)
    except (ContractError, OSError) as exc:
        return EvaluationResult(
            False,
            output_hash,
            error_class=type(exc).__name__,
            error_message=str(exc),
        )


def aggregate_scores(results: list[EvaluationResult]) -> float | None:
    if not results or any(not result.valid or result.score is None for result in results):
        return None
    return sum(float(result.score) for result in results) / len(results)
