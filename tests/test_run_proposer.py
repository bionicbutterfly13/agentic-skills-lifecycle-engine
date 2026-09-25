"""Offline tests for the live Skill Proposer driver (single-shot and detective modes)."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Mapping
import urllib.request

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from test_terminal_paths import TerminalHarness  # noqa: E402

import run_proposer  # noqa: E402
from asme.canonical import ContractError, sha256_bytes  # noqa: E402
from asme.contract import LifecycleState  # noqa: E402
from asme.model_client import ChatClient  # noqa: E402
from asme.roles import build_role_prompt  # noqa: E402


class FakeProposerTransport:
    """One scripted OpenAI-compatible endpoint, with a recorded request log."""

    def __init__(self, responses: list[Mapping[str, Any]]) -> None:
        self._responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    def __call__(self, request: urllib.request.Request) -> Mapping[str, Any]:
        body = json.loads(request.data) if request.data else None
        self.requests.append({"url": request.full_url, "body": body})
        scripted = self._responses.pop(0)
        message: dict[str, Any] = {"role": "assistant"}
        message.update(scripted)
        return {"choices": [{"message": message, "finish_reason": "stop"}]}


def _harness_at_needs_proposal(tmp_path: Path) -> TerminalHarness:
    """Drive a harness to NEEDS_PROPOSAL, matching TerminalHarness.proposal()'s
    setup up to (but not including) apply_proposal, so the driver under test
    performs the final model call -> apply_proposal step itself."""

    harness = TerminalHarness(tmp_path, case_id="RUN-PROPOSER", max_iterations=2)
    harness.baseline(0.25)
    train = harness.run_phase("train", 1.0)
    assert train.valid and train.aggregate_score == 1.0
    harness.workflow.sample_train()
    state = harness.workspace.status()
    iteration = state.iteration
    pattern_name = f"pattern-{iteration}"
    maintainer_input = (
        harness.workspace.engine.target_roots["runs"] / str(iteration) / "maintainer-input.json"
    )
    pattern = "\n".join(
        (
            "pattern_kind: success",
            "",
            "## Description",
            "Return the declared concise answer.",
            "## Root cause",
            "The successful trace follows the exact output contract.",
            "## Evidence",
            '- pass train-1: "<answer>answer-train-1</answer>"',
            "## Solution",
            "Keep the response constrained to the declared answer.",
        )
    )
    harness.workflow.apply_wiki(
        json.dumps(
            {
                "create_patterns": {pattern_name: pattern},
                "update_patterns": {},
                "update_index": f"# Pattern index\n\n- {pattern_name}\n",
                "append_log": f"iteration {iteration}: added {pattern_name}",
                "attestation": {
                    "input_hash": sha256_bytes(maintainer_input.read_bytes()),
                    "class_coverage": {"success": {"represented_by": [pattern_name]}},
                    "per_pattern": {
                        pattern_name: {
                            "pattern_kind": "success",
                            "failure_traces": {"not_applicable": "No failing traces were sampled."},
                            "success_traces": ["train-1"],
                            "quoted_commands": [
                                {
                                    "trace": "train-1",
                                    "outcome": "pass",
                                    "span": "<answer>answer-train-1</answer>",
                                }
                            ],
                            "dedup_disposition": "new",
                            "dedup_reason": "This iteration adds a distinct record.",
                            "root_cause_reason": "The cited trace demonstrates the rule.",
                            "generalizable_because": "The format applies across tasks.",
                        }
                    },
                },
            }
        )
    )
    assert harness.workspace.status().state is LifecycleState.NEEDS_PROPOSAL
    return harness


def _client(transport: FakeProposerTransport) -> ChatClient:
    return ChatClient(base_url="http://endpoint.invalid/v1", model_id="test-model", transport=transport)


def _valid_create_payload(context_bytes: bytes) -> dict[str, Any]:
    return {
        "action": "create",
        "context_hash": sha256_bytes(context_bytes),
        "reason": "The declared train evidence supports this bounded decision.",
        "trace_ids": [f"train-{index}" for index in range(1, 5)],
        "skill_name": "terminal-skill",
        "files": {
            "SKILL.md": (
                "---\n"
                "name: terminal-skill\n"
                "description: Return exact bounded output. Use when repeated text tasks "
                "require verified concise responses and explicit limits.\n"
                "version: 0.1.0\n"
                "last_updated: 2026-08-31\n"
                "---\n\n"
                "# Terminal skill\n\n"
                "Return exact output.\n\n"
                "## Triggers\n\n"
                "1. Repeated text tasks require verified concise responses.\n"
                "2. A bounded response procedure needs explicit limits.\n"
            ),
            "README.md": "test_evaluation: passed\ntrace_fidelity: final_only\nisolation: unsandboxed\n",
            "PURPOSE.md": "test_evaluation: passed\ntrace_fidelity: final_only\nisolation: unsandboxed\n",
        },
    }


# ---------------------------------------------------------------------------
# Task 1: single-shot mode
# ---------------------------------------------------------------------------


def test_single_shot_completes_in_one_call_and_applies_once(tmp_path: Path) -> None:
    harness = _harness_at_needs_proposal(tmp_path)
    context_bytes = harness.workflow.proposer_context()
    proposal = _valid_create_payload(context_bytes)
    transport = FakeProposerTransport([{"content": json.dumps(proposal)}])
    client = _client(transport)
    run_dir = run_proposer.run_dir_for(harness.workspace)

    run_proposer.run_single_shot(harness.workflow, client, run_dir)

    assert len(transport.requests) == 1
    assert harness.workspace.status().state is not LifecycleState.NEEDS_PROPOSAL
    output_path = run_dir / "proposer-single-shot-output.txt"
    assert output_path.read_text(encoding="utf-8") == json.dumps(proposal)


def test_single_shot_prompt_contains_full_context_payload_verbatim(tmp_path: Path) -> None:
    harness = _harness_at_needs_proposal(tmp_path)
    context_bytes = harness.workflow.proposer_context()
    context_payload = json.loads(context_bytes)
    proposal = _valid_create_payload(context_bytes)
    transport = FakeProposerTransport([{"content": json.dumps(proposal)}])
    client = _client(transport)
    run_dir = run_proposer.run_dir_for(harness.workspace)

    run_proposer.run_single_shot(harness.workflow, client, run_dir)

    sent_prompt = transport.requests[0]["body"]["messages"][0]["content"]
    expected_prompt = build_role_prompt("proposer", context_payload)
    assert sent_prompt == expected_prompt
    encoded_input = json.dumps(dict(context_payload), sort_keys=True, indent=2)
    assert encoded_input in sent_prompt
    for key in (
        "train_outcomes",
        "wiki_pages",
        "impact_history",
        "active_skill",
        "available_trace_ids",
    ):
        assert key in context_payload


def test_single_shot_malformed_response_raises_without_retry(tmp_path: Path) -> None:
    harness = _harness_at_needs_proposal(tmp_path)
    malformed = json.dumps({"action": "create", "reason": "missing context_hash"})
    transport = FakeProposerTransport([{"content": malformed}])
    client = _client(transport)
    run_dir = run_proposer.run_dir_for(harness.workspace)

    with pytest.raises(ContractError):
        run_proposer.run_single_shot(harness.workflow, client, run_dir)

    assert len(transport.requests) == 1
    assert harness.workspace.status().state is LifecycleState.NEEDS_PROPOSAL


# ---------------------------------------------------------------------------
# Task 2: detective mode
# ---------------------------------------------------------------------------


def _tool_call(call_id: str, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def _read_call(call_id: str, path: str) -> dict[str, Any]:
    return _tool_call(call_id, "read_file", {"path": path})


def _finish_call(call_id: str, proposal: Mapping[str, Any]) -> dict[str, Any]:
    return _tool_call(call_id, "finish", {"proposal": proposal})


def _finish_proposal_without_context_hash(trace_ids: list[str]) -> dict[str, Any]:
    """A finish() proposal payload as the model would submit it: no context_hash,
    since the driver inserts that mechanically after finish() succeeds."""

    return {
        "action": "create",
        "reason": "The declared train evidence supports this bounded decision.",
        "trace_ids": trace_ids,
        "skill_name": "terminal-skill",
        "files": {
            "SKILL.md": (
                "---\n"
                "name: terminal-skill\n"
                "description: Return exact bounded output. Use when repeated text tasks "
                "require verified concise responses and explicit limits.\n"
                "version: 0.1.0\n"
                "last_updated: 2026-08-31\n"
                "---\n\n"
                "# Terminal skill\n\n"
                "Return exact output.\n\n"
                "## Triggers\n\n"
                "1. Repeated text tasks require verified concise responses.\n"
                "2. A bounded response procedure needs explicit limits.\n"
            ),
            "README.md": "test_evaluation: passed\ntrace_fidelity: final_only\nisolation: unsandboxed\n",
            "PURPOSE.md": "test_evaluation: passed\ntrace_fidelity: final_only\nisolation: unsandboxed\n",
        },
    }


def test_detective_reads_all_expected_paths_and_refuses_out_of_scope(tmp_path: Path) -> None:
    harness = _harness_at_needs_proposal(tmp_path)
    context_bytes = harness.workflow.proposer_context()
    context_payload = json.loads(context_bytes)
    trace_ids = context_payload["available_trace_ids"]
    assert len(trace_ids) >= 4

    proposal = _finish_proposal_without_context_hash(trace_ids[:4])
    responses = [
        {"tool_calls": [_read_call("r1", "wiki/index.md")]},
        {"tool_calls": [_read_call("r2", f"traces/{trace_ids[0]}")]},
        {"tool_calls": [_read_call("r3", f"traces/{trace_ids[1]}")]},
        {"tool_calls": [_read_call("r4", f"traces/{trace_ids[2]}")]},
        {"tool_calls": [_read_call("r5", f"traces/{trace_ids[3]}")]},
        # Out-of-scope reads: a validation-split id and a traversal attempt.
        {"tool_calls": [_read_call("r6", "traces/validation-1")]},
        {"tool_calls": [_read_call("r7", "../../etc/passwd")]},
        {"tool_calls": [_finish_call("f1", proposal)]},
    ]
    transport = FakeProposerTransport(responses)
    client = _client(transport)
    run_dir = run_proposer.run_dir_for(harness.workspace)

    run_proposer.run_detective(harness.workflow, client, run_dir, max_turns=20)

    assert harness.workspace.status().state is not LifecycleState.NEEDS_PROPOSAL
    reads_log = json.loads((run_dir / "proposer-reads-log.json").read_text(encoding="utf-8"))
    refused_entries = [entry for entry in reads_log if entry["refused"]]
    refused_paths = {entry["path"] for entry in refused_entries}
    assert "traces/validation-1" in refused_paths
    assert "../../etc/passwd" in refused_paths
    successful_paths = {entry["path"] for entry in reads_log if not entry["refused"]}
    assert f"traces/{trace_ids[0]}" in successful_paths
    assert "traces/validation-1" not in successful_paths


def test_detective_finish_with_fewer_than_four_traces_refused_once_then_raises(
    tmp_path: Path,
) -> None:
    harness = _harness_at_needs_proposal(tmp_path)
    context_bytes = harness.workflow.proposer_context()
    context_payload = json.loads(context_bytes)
    trace_ids = context_payload["available_trace_ids"]

    proposal = _finish_proposal_without_context_hash(trace_ids[:1])
    responses = [
        {"tool_calls": [_read_call("r1", f"traces/{trace_ids[0]}")]},
        {"tool_calls": [_finish_call("f1", proposal)]},
        # Retry granted once; second insufficient finish() raises.
        {"tool_calls": [_finish_call("f2", proposal)]},
    ]
    transport = FakeProposerTransport(responses)
    client = _client(transport)
    run_dir = run_proposer.run_dir_for(harness.workspace)

    with pytest.raises(ContractError):
        run_proposer.run_detective(harness.workflow, client, run_dir, max_turns=20)

    assert harness.workspace.status().state is LifecycleState.NEEDS_PROPOSAL
    assert len(transport.requests) == 3


def test_detective_finish_citing_unread_trace_id_refused_then_raises(tmp_path: Path) -> None:
    harness = _harness_at_needs_proposal(tmp_path)
    context_bytes = harness.workflow.proposer_context()
    context_payload = json.loads(context_bytes)
    trace_ids = context_payload["available_trace_ids"]
    assert len(trace_ids) >= 4

    # Read all 4 available traces, but the proposal also cites a trace_id that
    # was never read via read_file (never appears in the reads log).
    proposal = _finish_proposal_without_context_hash(trace_ids[:4] + ["train-never-read"])
    responses = [
        {"tool_calls": [_read_call("r1", f"traces/{trace_ids[0]}")]},
        {"tool_calls": [_read_call("r2", f"traces/{trace_ids[1]}")]},
        {"tool_calls": [_read_call("r3", f"traces/{trace_ids[2]}")]},
        {"tool_calls": [_read_call("r4", f"traces/{trace_ids[3]}")]},
        {"tool_calls": [_finish_call("f1", proposal)]},
        {"tool_calls": [_finish_call("f2", proposal)]},
    ]
    transport = FakeProposerTransport(responses)
    client = _client(transport)
    run_dir = run_proposer.run_dir_for(harness.workspace)

    with pytest.raises(ContractError):
        run_proposer.run_detective(harness.workflow, client, run_dir, max_turns=20)

    assert harness.workspace.status().state is LifecycleState.NEEDS_PROPOSAL


def test_detective_reads_log_has_path_hash_turn_in_call_order_including_refused(
    tmp_path: Path,
) -> None:
    harness = _harness_at_needs_proposal(tmp_path)
    context_bytes = harness.workflow.proposer_context()
    context_payload = json.loads(context_bytes)
    trace_ids = context_payload["available_trace_ids"]
    proposal = _finish_proposal_without_context_hash(trace_ids[:4])
    responses = [
        {"tool_calls": [_read_call("r1", "wiki/index.md")]},
        {"tool_calls": [_read_call("r2", "traces/does-not-exist")]},
        {"tool_calls": [_read_call("r3", f"traces/{trace_ids[0]}")]},
        {"tool_calls": [_read_call("r4", f"traces/{trace_ids[1]}")]},
        {"tool_calls": [_read_call("r5", f"traces/{trace_ids[2]}")]},
        {"tool_calls": [_read_call("r6", f"traces/{trace_ids[3]}")]},
        {"tool_calls": [_finish_call("f1", proposal)]},
    ]
    transport = FakeProposerTransport(responses)
    client = _client(transport)
    run_dir = run_proposer.run_dir_for(harness.workspace)

    run_proposer.run_detective(harness.workflow, client, run_dir, max_turns=20)

    reads_log = json.loads((run_dir / "proposer-reads-log.json").read_text(encoding="utf-8"))
    assert [entry["turn"] for entry in reads_log] == [1, 2, 3, 4, 5, 6]
    for entry in reads_log:
        assert set(entry) == {"turn", "path", "sha256", "refused"}
        assert isinstance(entry["sha256"], str) and len(entry["sha256"]) == 64
    assert reads_log[1]["path"] == "traces/does-not-exist"
    assert reads_log[1]["refused"] is True
    assert reads_log[0]["refused"] is False


def test_detective_context_hash_is_always_driver_computed(tmp_path: Path) -> None:
    harness = _harness_at_needs_proposal(tmp_path)
    context_bytes = harness.workflow.proposer_context()
    context_payload = json.loads(context_bytes)
    trace_ids = context_payload["available_trace_ids"]
    proposal = _finish_proposal_without_context_hash(trace_ids[:4])
    # The model supplies a wrong/garbage context_hash; the driver must overwrite it.
    proposal_with_wrong_hash = dict(proposal)
    proposal_with_wrong_hash["context_hash"] = "0" * 64
    responses = [
        {"tool_calls": [_read_call("r1", f"traces/{trace_ids[0]}")]},
        {"tool_calls": [_read_call("r2", f"traces/{trace_ids[1]}")]},
        {"tool_calls": [_read_call("r3", f"traces/{trace_ids[2]}")]},
        {"tool_calls": [_read_call("r4", f"traces/{trace_ids[3]}")]},
        {"tool_calls": [_finish_call("f1", proposal_with_wrong_hash)]},
    ]
    transport = FakeProposerTransport(responses)
    client = _client(transport)
    run_dir = run_proposer.run_dir_for(harness.workspace)

    run_proposer.run_detective(harness.workflow, client, run_dir, max_turns=20)

    assert harness.workspace.status().state is not LifecycleState.NEEDS_PROPOSAL
    output_path = run_dir / "proposer-output.json"
    stored = json.loads(output_path.read_text(encoding="utf-8"))
    assert stored["context_hash"] == sha256_bytes(context_bytes)
    assert stored["context_hash"] != "0" * 64


def test_virtual_filesystem_never_serves_validation_or_test_split_reads(tmp_path: Path) -> None:
    """T-260923-08: the detective filesystem is read-only and built only from the
    train-only proposer_context() payload. A read for any validation or test task
    id, or for answers.jsonl/domain.json directly, must be refused."""

    harness = _harness_at_needs_proposal(tmp_path)
    context_bytes = harness.workflow.proposer_context()
    context_payload = json.loads(context_bytes)
    virtual_fs = run_proposer._build_virtual_filesystem(context_payload)

    # Only train_outcomes ever produce traces/<id> keys (proposer_payload raises
    # if a non-train answer were ever passed in), so validation/test ids are
    # structurally absent, not filtered after the fact.
    for forbidden in (
        "traces/validation-1",
        "traces/validation-2",
        "traces/test-1",
        "answers.jsonl",
        "domain.json",
        "../answers.jsonl",
    ):
        content, refused = run_proposer._resolve_read(virtual_fs, forbidden)
        assert refused is True
        assert content is None

    # Sanity: the train ids that ARE present are exactly available_trace_ids.
    trace_keys = {key for key in virtual_fs if key.startswith("traces/")}
    assert trace_keys == {f"traces/{tid}" for tid in context_payload["available_trace_ids"]}


def test_detective_max_turns_reached_raises(tmp_path: Path) -> None:
    harness = _harness_at_needs_proposal(tmp_path)
    # Never call finish; force the loop to exhaust its turn budget.
    responses = [{"tool_calls": [_read_call(f"r{i}", "wiki/index.md")]} for i in range(3)]
    transport = FakeProposerTransport(responses)
    client = _client(transport)
    run_dir = run_proposer.run_dir_for(harness.workspace)

    with pytest.raises(ContractError):
        run_proposer.run_detective(harness.workflow, client, run_dir, max_turns=3)

    assert harness.workspace.status().state is LifecycleState.NEEDS_PROPOSAL
    reads_log = json.loads((run_dir / "proposer-reads-log.json").read_text(encoding="utf-8"))
    assert len(reads_log) == 3


# ---------------------------------------------------------------------------
# Quick task 260924-tdp: --header CLI option
# ---------------------------------------------------------------------------

CLI_HEADER_ARGS = [
    "--header",
    "originator: codex_cli_rs",
    "--header",
    "version: 0.155.1",
    "--header",
    "user-agent: codex_cli_rs/0.155.1 (probe)",
]


def _cli_argv(tmp_path: Path, *extra: str) -> list[str]:
    return [
        "run_proposer.py",
        "--domain",
        "terminal-run-proposer",
        "--domain-root",
        str(tmp_path / "workspace"),
        "--model",
        "test-model",
        *extra,
    ]


def _record_detective(monkeypatch: pytest.MonkeyPatch) -> list[ChatClient]:
    captured: list[ChatClient] = []

    def recorder(workflow: Any, client: ChatClient, run_dir: Path, *, max_turns: int) -> None:
        captured.append(client)

    monkeypatch.setattr(run_proposer, "run_detective", recorder)
    return captured


def test_cli_header_reaches_the_chat_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LIFECYCLE_MODEL_API_KEY", raising=False)
    _harness_at_needs_proposal(tmp_path)
    captured = _record_detective(monkeypatch)
    monkeypatch.setattr(sys, "argv", _cli_argv(tmp_path, *CLI_HEADER_ARGS))

    assert run_proposer.main() == 0

    (client,) = captured
    headers = {name.lower(): value for name, value in client._headers().items()}
    assert headers["originator"] == "codex_cli_rs"
    assert headers["version"] == "0.155.1"
    assert headers["user-agent"] == "codex_cli_rs/0.155.1 (probe)"
    assert "authorization" not in headers


def test_cli_without_header_keeps_default_client_headers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LIFECYCLE_MODEL_API_KEY", raising=False)
    _harness_at_needs_proposal(tmp_path)
    captured = _record_detective(monkeypatch)
    monkeypatch.setattr(sys, "argv", _cli_argv(tmp_path))

    assert run_proposer.main() == 0

    (client,) = captured
    assert client._headers() == {"Content-Type": "application/json"}


def test_cli_refuses_authorization_header_without_echoing_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("LIFECYCLE_MODEL_API_KEY", raising=False)
    _harness_at_needs_proposal(tmp_path)
    captured = _record_detective(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        _cli_argv(tmp_path, "--header", "Authorization: Bearer sk-test-should-not-echo"),
    )

    with pytest.raises(SystemExit) as exited:
        run_proposer.main()

    assert exited.value.code == 2
    stderr = capsys.readouterr().err
    assert "usage:" in stderr
    assert "authorization" in stderr.lower()
    assert "sk-test-should-not-echo" not in stderr
    assert captured == []
