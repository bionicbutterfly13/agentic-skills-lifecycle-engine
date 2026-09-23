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
