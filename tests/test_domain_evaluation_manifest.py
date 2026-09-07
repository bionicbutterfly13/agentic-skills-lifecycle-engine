from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from conftest import write_program
from asme.canonical import ContractError, sha256_bytes
from asme.contract import CapabilityReport
from asme.domain import AnswerRecord, TaskRecord, load_declared_domain, verify_domain_seal
from asme.evaluation import EvaluationResult, evaluate_output
from asme.evidence import captured_execution, maintainer_payload, proposer_payload, rollout_payload
from asme.manifest import build_rollout_manifest, verify_manifest_bindings


def test_hf_a24_domain_accepts_declared_sources_only(declared_domain, tmp_path: Path) -> None:
    verify_domain_seal(declared_domain)
    tasks = tmp_path / "bad-tasks.jsonl"
    answers = tmp_path / "answers.jsonl"
    tasks.write_text(
        json.dumps({"task_id": "a", "input": "x", "session_handle": "ambient"}) + "\n",
        encoding="utf-8",
    )
    answers.write_text(
        "".join(
            json.dumps({"task_id": item, "split": split, "expected": "x"}) + "\n"
            for item, split in (("a", "train"), ("b", "validation"), ("c", "test"))
        ),
        encoding="utf-8",
    )
    prompt = tmp_path / "p"
    extractor = tmp_path / "e"
    scorer = tmp_path / "s"
    for path in (prompt, extractor, scorer):
        path.write_text("x", encoding="utf-8")
    with pytest.raises(ContractError, match="unsupported fields"):
        load_declared_domain(
            domain_id="bad",
            task_file=tasks,
            answer_file=answers,
            prompt_file=prompt,
            extractor_file=extractor,
            scorer_file=scorer,
            tool_profile={"mode": "none"},
        )


@pytest.mark.parametrize(
    "tool_profile,error_fragment",
    [
        ({}, "tool profile"),
        ({"mode": "write"}, "none or read"),
        ({"mode": "none", "resources": ["source-a"]}, "none mode"),
        ({"mode": "read"}, "read mode"),
        ({"mode": "read", "resources": ["bad/resource"]}, "resource"),
    ],
)
def test_portable_v1_rejects_out_of_scope_tool_profiles(
    tmp_path: Path, tool_profile: dict[str, object], error_fragment: str
) -> None:
    tasks = tmp_path / "tasks.jsonl"
    answers = tmp_path / "answers.jsonl"
    tasks.write_text(
        "".join(
            json.dumps({"task_id": task_id, "input": task_id}) + "\n"
            for task_id in ("train-1", "validation-1", "test-1")
        ),
        encoding="utf-8",
    )
    answers.write_text(
        "".join(
            json.dumps({"task_id": task_id, "split": split, "expected": "ok"}) + "\n"
            for task_id, split in (
                ("train-1", "train"),
                ("validation-1", "validation"),
                ("test-1", "test"),
            )
        ),
        encoding="utf-8",
    )
    prompt = tmp_path / "prompt.txt"
    extractor = tmp_path / "extractor"
    scorer = tmp_path / "scorer"
    for path in (prompt, extractor, scorer):
        path.write_text("x\n", encoding="utf-8")
    with pytest.raises(ContractError, match=error_fragment):
        load_declared_domain(
            domain_id="scope-test",
            task_file=tasks,
            answer_file=answers,
            prompt_file=prompt,
            extractor_file=extractor,
            scorer_file=scorer,
            tool_profile=tool_profile,
        )


def test_portable_v1_records_narrow_task_scope_in_seal(declared_domain) -> None:
    assert declared_domain.task_class == "trusted_text"
    assert declared_domain.output_kind == "text"
    assert declared_domain.tool_profile == {"mode": "none", "resources": ()}


def test_missing_split_markers_are_generated_as_collision_checked_32_hex(
    tmp_path: Path,
) -> None:
    tasks = tmp_path / "tasks.jsonl"
    answers = tmp_path / "answers.jsonl"
    tasks.write_text(
        "".join(
            json.dumps({"task_id": f"{split}-1", "input": f"input {split}"}) + "\n"
            for split in ("train", "validation", "test")
        ),
        encoding="utf-8",
    )
    answers.write_text(
        "".join(
            json.dumps(
                {
                    "task_id": f"{split}-1",
                    "split": split,
                    "expected": f"answer {split}",
                }
            )
            + "\n"
            for split in ("train", "validation", "test")
        ),
        encoding="utf-8",
    )
    prompt = tmp_path / "prompt.txt"
    extractor = tmp_path / "extractor"
    scorer = tmp_path / "scorer"
    colliding = "a" * 32
    prompt.write_text(f"{{input}}\n{colliding}\n", encoding="utf-8")
    extractor.write_text("extract\n", encoding="utf-8")
    scorer.write_text("score\n", encoding="utf-8")
    candidates = iter((colliding, "b" * 32, "c" * 32, "d" * 32))
    domain = load_declared_domain(
        domain_id="generated-markers",
        task_file=tasks,
        answer_file=answers,
        prompt_file=prompt,
        extractor_file=extractor,
        scorer_file=scorer,
        tool_profile={"mode": "none"},
        marker_factory=lambda: next(candidates),
    )
    by_split = {
        split: {answer.marker for answer in domain.answers if answer.split == split}
        for split in ("train", "validation", "test")
    }
    assert by_split == {
        "train": {"b" * 32},
        "validation": {"c" * 32},
        "test": {"d" * 32},
    }
    assert all(
        marker is not None
        and len(marker) == 32
        and set(marker) <= set("0123456789abcdef")
        for markers in by_split.values()
        for marker in markers
    )
    assert "marker" not in answers.read_text(encoding="utf-8")


def test_read_resources_are_named_and_content_bound_into_domain_seal(tmp_path: Path) -> None:
    tasks = tmp_path / "tasks.jsonl"
    answers = tmp_path / "answers.jsonl"
    tasks.write_text(
        "".join(
            json.dumps({"task_id": task_id, "input": task_id}) + "\n"
            for task_id in ("train-1", "validation-1", "test-1")
        ),
        encoding="utf-8",
    )
    answers.write_text(
        "".join(
            json.dumps({"task_id": task_id, "split": split, "expected": "ok"}) + "\n"
            for task_id, split in (
                ("train-1", "train"),
                ("validation-1", "validation"),
                ("test-1", "test"),
            )
        ),
        encoding="utf-8",
    )
    prompt = tmp_path / "prompt.txt"
    extractor = tmp_path / "extractor"
    scorer = tmp_path / "scorer"
    resource = tmp_path / "facts.txt"
    for path, text in (
        (prompt, "{input}\n"),
        (extractor, "extract\n"),
        (scorer, "score\n"),
        (resource, "fixed facts\n"),
    ):
        path.write_text(text, encoding="utf-8")
    domain = load_declared_domain(
        domain_id="read-domain",
        task_file=tasks,
        answer_file=answers,
        prompt_file=prompt,
        extractor_file=extractor,
        scorer_file=scorer,
        tool_profile={"mode": "read", "resources": ["facts"]},
        read_resources={"facts": resource},
    )
    assert domain.read_resource_hashes == (("facts", sha256_bytes(resource.read_bytes())),)
    resource.write_text("changed facts\n", encoding="utf-8")
    changed = load_declared_domain(
        domain_id="read-domain",
        task_file=tasks,
        answer_file=answers,
        prompt_file=prompt,
        extractor_file=extractor,
        scorer_file=scorer,
        tool_profile={"mode": "read", "resources": ["facts"]},
        read_resources={"facts": resource},
    )
    assert changed.seal != domain.seal


def test_hf_a14_role_payloads_enforce_ground_truth_boundaries() -> None:
    task = TaskRecord("train-1", "one")
    answer = AnswerRecord("train-1", "train", "1", "marker")
    rollout = rollout_payload(
        task=task,
        rendered_prompt="Solve one",
        active_skill="",
        tool_profile={},
        runtime_policy={},
        expected_capture_schema={},
    )
    assert "expected" not in rollout and "marker" not in rollout and "wiki" not in rollout
    with pytest.raises(ContractError):
        maintainer_payload(samples=({"expected": "secret"},), wiki_pages={})
    proposal = proposer_payload(
        train_outcomes=((task, answer, "1", 1.0),),
        wiki_pages={},
        impact_history=(),
        active_skill="",
    )
    assert proposal["train_outcomes"][0]["expected"] == "1"
    with pytest.raises(ContractError):
        proposer_payload(
            train_outcomes=((task, AnswerRecord("train-1", "test", "1"), "1", 1.0),),
            wiki_pages={},
            impact_history=(),
            active_skill="",
        )


@pytest.mark.parametrize(
    "extractor_body,scorer_body,error_fragment",
    [
        ("raise SystemExit(3)\n", "print('1')\n", "status 3"),
        ("print('')\n", "print('1')\n", "empty"),
        ("print('not json')\n", "print('1')\n", "malformed"),
        (
            "import json,sys; p=json.load(sys.stdin); print(json.dumps({'returned_output_hash':p['returned_output_hash'],'prediction':'x'}))\n",
            "print('1\\n0')\n",
            "ambiguous",
        ),
        (
            "import json,sys; p=json.load(sys.stdin); print(json.dumps({'returned_output_hash':p['returned_output_hash'],'prediction':'x'}))\n",
            "print('nan')\n",
            "finite",
        ),
        (
            "import json,sys; p=json.load(sys.stdin); print(json.dumps({'returned_output_hash':p['returned_output_hash'],'prediction':'x'}))\n",
            "print('2')\n",
            "within",
        ),
    ],
)
def test_hf_a08_extractor_scorer_failures_never_become_scores(
    tmp_path: Path,
    extractor_body: str,
    scorer_body: str,
    error_fragment: str,
) -> None:
    extractor = write_program(tmp_path / "extractor", extractor_body)
    scorer = write_program(tmp_path / "scorer", scorer_body)
    result = evaluate_output(
        returned_output="x",
        expected="x",
        extractor=extractor,
        scorer=scorer,
    )
    assert not result.valid and result.score is None
    assert error_fragment in (result.error_message or "")


def test_hf_a08_valid_evaluation_and_manifest_are_output_hash_bound(
    tmp_path: Path, declared_domain
) -> None:
    extractor = write_program(
        tmp_path / "extractor",
        "import json,sys; p=json.load(sys.stdin); print(json.dumps({'returned_output_hash':p['returned_output_hash'],'prediction':p['returned_output']}))\n",
    )
    scorer = write_program(
        tmp_path / "scorer",
        "import json,sys; p=json.load(sys.stdin); print('1' if p['prediction']==p['expected'] else '0')\n",
    )
    evaluation = evaluate_output(
        returned_output="2",
        expected="2",
        extractor=extractor,
        scorer=scorer,
    )
    assert evaluation.valid and evaluation.score == 1.0
    capability = CapabilityReport.conservative(
        runtime_id="test-runtime",
        runtime_version="1",
        adapter_version="1",
        provider="openai-codex",
        model_id="gpt-test",
        openai_backed=True,
        captured_events=("final_answer",),
    )
    prompt = "Solve two"
    execution = captured_execution(
        execution_id="execution-1",
        runtime_id="test-runtime",
        runtime_version="1",
        adapter_version="1",
        job_spec_hash="a" * 64,
        prompt_hash=sha256_bytes(prompt.encode()),
        active_snapshot_hash="b" * 64,
        started="2026-08-31T00:00:00+00:00",
        finished="2026-08-31T00:00:01+00:00",
        termination="completed",
        events=({"kind": "final_answer", "text": "2"},),
        returned_output="2",
        capability=capability,
    )
    manifest = build_rollout_manifest(
        domain=declared_domain,
        phase="validation-1",
        split="validation",
        iteration=1,
        active_snapshot_hash="b" * 64,
        prompts={"validation-1": prompt},
        executions={"validation-1": execution},
        evaluations={"validation-1": evaluation},
    )
    assert manifest.valid and manifest.aggregate_score == 1.0
    verify_manifest_bindings(
        manifest,
        domain_seal_hash=declared_domain.seal,
        active_snapshot_hash="b" * 64,
        capability_report_hash=capability.digest,
    )
    bad = EvaluationResult(True, "c" * 64, prediction="2", score=1.0)
    invalid = build_rollout_manifest(
        domain=declared_domain,
        phase="validation-1",
        split="validation",
        iteration=1,
        active_snapshot_hash="b" * 64,
        prompts={"validation-1": prompt},
        executions={"validation-1": execution},
        evaluations={"validation-1": bad},
    )
    assert not invalid.valid and invalid.aggregate_score is None


def test_hf_a08_extractor_and_scorer_each_use_exactly_30_seconds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    extractor = write_program(tmp_path / "extractor", "print('unused')\n")
    scorer = write_program(tmp_path / "scorer", "print('unused')\n")
    observed_timeouts: list[float] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed_timeouts.append(float(kwargs["timeout"]))
        payload = json.loads(str(kwargs["input"]))
        if len(observed_timeouts) == 1:
            stdout = json.dumps(
                {
                    "returned_output_hash": payload["returned_output_hash"],
                    "prediction": "expected",
                }
            )
        else:
            stdout = "1\n"
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    monkeypatch.setattr("asme.evaluation.subprocess.run", fake_run)
    result = evaluate_output(
        returned_output="returned",
        expected="expected",
        extractor=extractor,
        scorer=scorer,
    )

    assert result.valid
    assert observed_timeouts == [30.0, 30.0]


def test_hf_a08_timeout_fails_closed_without_waiting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    extractor = write_program(tmp_path / "extractor", "print('unused')\n")
    scorer = write_program(tmp_path / "scorer", "print('unused')\n")

    def time_out(command: list[str], **kwargs: object) -> None:
        assert kwargs["timeout"] == 30.0
        raise subprocess.TimeoutExpired(command, timeout=30.0)

    monkeypatch.setattr("asme.evaluation.subprocess.run", time_out)
    result = evaluate_output(
        returned_output="returned",
        expected="expected",
        extractor=extractor,
        scorer=scorer,
    )

    assert not result.valid and result.score is None
    assert "timeout after 30.0s" in (result.error_message or "")
