from __future__ import annotations

import json
from pathlib import Path

import pytest

from asme.canonical import ContractError
from asme.evalreport import (
    EVAL_REPORT_SCHEMA,
    EvalRun,
    EvalTaskScore,
    build_eval_report,
    eval_report_bytes,
    load_cartridge_answers,
    render_eval_summary,
    run_cartridge_phase,
)

_PACKAGE_ROOT = Path(__file__).parents[1]
_ARITHMETIC = _PACKAGE_ROOT / "assets" / "eval" / "arithmetic"
_ECHO = _PACKAGE_ROOT / "assets" / "eval" / "echo"


def _run_from_rollouts(cartridge: Path, rollout: str) -> EvalRun:
    return EvalRun(
        run_id=f"{cartridge.name}-{rollout}",
        phase_scores={
            phase: run_cartridge_phase(
                cartridge_root=cartridge,
                outputs_file=cartridge / "rollouts" / rollout / f"{phase}.jsonl",
            )
            for phase in ("baseline", "validation", "confirmation")
        },
    )


def test_eval_task_score_rejects_out_of_range_scores() -> None:
    with pytest.raises(ContractError):
        EvalTaskScore(task_id="t-1", score=1.5, output_hash="a" * 64)
    with pytest.raises(ContractError):
        EvalTaskScore(task_id="", score=0.5, output_hash="a" * 64)
    with pytest.raises(ContractError):
        EvalTaskScore(task_id="t-1", score=0.5, output_hash="short")


def test_both_eval_cartridges_declare_four_answered_tasks() -> None:
    for cartridge in (_ARITHMETIC, _ECHO):
        answers = load_cartridge_answers(cartridge)
        assert len(answers) == 4
        assert (cartridge / "prompt.txt").is_file()
        assert (cartridge / "tasks.jsonl").is_file()


def test_run_cartridge_phase_scores_through_real_extractor_and_scorer() -> None:
    baseline = run_cartridge_phase(
        cartridge_root=_ARITHMETIC,
        outputs_file=_ARITHMETIC / "rollouts" / "run-1" / "baseline.jsonl",
    )
    assert [item.task_id for item in baseline] == [
        "arith-1",
        "arith-2",
        "arith-3",
        "arith-4",
    ]
    assert [item.score for item in baseline] == [1.0, 1.0, 0.0, 0.0]
    validation = run_cartridge_phase(
        cartridge_root=_ARITHMETIC,
        outputs_file=_ARITHMETIC / "rollouts" / "run-1" / "validation.jsonl",
    )
    assert sum(item.score for item in validation) == 3.0


def test_run_cartridge_phase_fails_closed_on_unscorable_output(tmp_path: Path) -> None:
    outputs = tmp_path / "broken.jsonl"
    outputs.write_text(
        json.dumps({"task_id": "arith-1", "returned_output": "no tag at all"})
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ContractError, match="arith-1"):
        run_cartridge_phase(cartridge_root=_ARITHMETIC, outputs_file=outputs)
    missing = tmp_path / "unknown-task.jsonl"
    missing.write_text(
        json.dumps({"task_id": "not-a-task", "returned_output": "<answer>4</answer>"})
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ContractError, match="not-a-task"):
        run_cartridge_phase(cartridge_root=_ARITHMETIC, outputs_file=missing)


def test_build_eval_report_applies_a2_and_is_byte_deterministic() -> None:
    improving = _run_from_rollouts(_ARITHMETIC, "run-1")
    flat = _run_from_rollouts(_ECHO, "run-1")
    report = build_eval_report(
        domain_id="eval-demo",
        runs=(improving, flat),
        trace_fidelity="observable_transcript",
        isolation_label="unsandboxed",
        seed=20260901,
    )
    assert report["schema"] == EVAL_REPORT_SCHEMA
    assert report["seed"] == 20260901
    by_run = {run["run_id"]: run for run in report["runs"]}
    arithmetic = by_run["arithmetic-run-1"]
    assert arithmetic["aggregates"]["baseline"] == 0.5
    assert arithmetic["aggregates"]["validation"] == 0.75
    assert arithmetic["aggregates"]["confirmation"] == 0.75
    assert arithmetic["a2_local_acceptance"]["allowed"] is True
    flat_report = report["runs"][1]
    assert flat_report["a2_local_acceptance"]["allowed"] is False
    assert (
        "strict_validation_and_confirmation_win_missing"
        in flat_report["a2_local_acceptance"]["reasons"]
    )
    again = build_eval_report(
        domain_id="eval-demo",
        runs=(improving, flat),
        trace_fidelity="observable_transcript",
        isolation_label="unsandboxed",
        seed=20260901,
    )
    assert eval_report_bytes(report) == eval_report_bytes(again)


def test_build_eval_report_requires_distinct_run_ids() -> None:
    run = _run_from_rollouts(_ARITHMETIC, "run-1")
    with pytest.raises(ContractError, match="run IDs"):
        build_eval_report(
            domain_id="eval-demo",
            runs=(run, run),
            trace_fidelity="observable_transcript",
            isolation_label="unsandboxed",
            seed=1,
        )


def test_render_eval_summary_states_scores_and_verdicts() -> None:
    run = _run_from_rollouts(_ARITHMETIC, "run-1")
    report = build_eval_report(
        domain_id="eval-demo",
        runs=(run,),
        trace_fidelity="observable_transcript",
        isolation_label="unsandboxed",
        seed=7,
    )
    summary = render_eval_summary(report)
    assert "eval-demo" in summary
    assert "baseline 0.5" in summary
    assert "confirmation 0.75" in summary
    assert "ACCEPTED" in summary
    assert "observable_transcript" in summary


def test_eval_run_refuses_missing_and_extra_phases_independently() -> None:
    scores = (EvalTaskScore(task_id="t-1", score=1.0, output_hash="a" * 64),)
    with pytest.raises(ContractError, match="missing=\\['confirmation'\\]"):
        EvalRun(run_id="r", phase_scores={"baseline": scores, "validation": scores})
    with pytest.raises(ContractError, match="extra=\\['bonus'\\]"):
        EvalRun(
            run_id="r",
            phase_scores={
                "baseline": scores,
                "validation": scores,
                "confirmation": scores,
                "bonus": scores,
            },
        )


def test_rollout_rows_report_exact_line_numbers_and_reject_non_objects(
    tmp_path: Path,
) -> None:
    blank = tmp_path / "blank.jsonl"
    blank.write_text(
        '{"task_id": "arith-1", "returned_output": "<answer>4</answer>"}\n \n',
        encoding="utf-8",
    )
    with pytest.raises(ContractError, match="blank.jsonl:2"):
        run_cartridge_phase(cartridge_root=_ARITHMETIC, outputs_file=blank)
    non_object = tmp_path / "nonobject.jsonl"
    non_object.write_text(
        '{"task_id": "arith-1", "returned_output": "<answer>4</answer>"}\n'
        '["returned_output", "task_id"]\n',
        encoding="utf-8",
    )
    with pytest.raises(ContractError, match="nonobject.jsonl:2"):
        run_cartridge_phase(cartridge_root=_ARITHMETIC, outputs_file=non_object)


def test_cartridge_config_must_be_a_json_object(tmp_path: Path) -> None:
    cartridge = tmp_path / "cartridge"
    cartridge.mkdir()
    (cartridge / "answers.jsonl").write_text(
        '{"task_id": "t-1", "split": "test", "expected": "1", "marker": "m-1"}\n',
        encoding="utf-8",
    )
    (cartridge / "cartridge.json").write_text(
        '["extractor", "scorer"]', encoding="utf-8"
    )
    outputs = tmp_path / "outputs.jsonl"
    outputs.write_text(
        '{"task_id": "t-1", "returned_output": "<answer>1</answer>"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ContractError, match="cartridge config fields"):
        run_cartridge_phase(cartridge_root=cartridge, outputs_file=outputs)


def test_build_eval_report_rejects_boolean_seed() -> None:
    run = _run_from_rollouts(_ARITHMETIC, "run-1")
    with pytest.raises(ContractError, match="seed must be an integer"):
        build_eval_report(
            domain_id="eval-demo",
            runs=(run,),
            trace_fidelity="observable_transcript",
            isolation_label="unsandboxed",
            seed=True,
        )


def test_render_eval_summary_names_refusal_reasons() -> None:
    flat = _run_from_rollouts(_ECHO, "run-1")
    report = build_eval_report(
        domain_id="eval-demo",
        runs=(flat,),
        trace_fidelity="observable_transcript",
        isolation_label="unsandboxed",
        seed=7,
    )
    summary = render_eval_summary(report)
    assert (
        "NOT ACCEPTED (strict_validation_and_confirmation_win_missing)" in summary
    )
