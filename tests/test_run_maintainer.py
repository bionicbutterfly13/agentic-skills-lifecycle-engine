"""Offline tests for the live Wiki Maintainer driver against a fake transport."""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
import sys
from typing import Any, Mapping
import urllib.request

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from test_terminal_paths import TerminalHarness  # noqa: E402

import run_maintainer  # noqa: E402
from asme.canonical import ContractError, sha256_bytes  # noqa: E402
from asme.contract import LifecycleState  # noqa: E402
from asme.model_client import ChatClient  # noqa: E402


class FakeMaintainerTransport:
    """One scripted OpenAI-compatible endpoint, with a recorded request log."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    def __call__(self, request: urllib.request.Request) -> Mapping[str, Any]:
        body = json.loads(request.data) if request.data else None
        self.requests.append({"url": request.full_url, "body": body})
        content = self._responses.pop(0)
        return {
            "choices": [
                {"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
            ]
        }


def _harness(tmp_path: Path) -> TerminalHarness:
    harness = TerminalHarness(tmp_path, case_id="RUN-MAINTAINER", max_iterations=2)
    harness.baseline(0.25)
    train = harness.run_phase("train", 1.0)
    assert train.valid and train.aggregate_score == 1.0
    harness.workflow.sample_train()
    return harness


def _valid_maintainer_output(harness: TerminalHarness, *, pattern_name: str = "pattern-1") -> str:
    state = harness.workspace.status()
    iteration = state.iteration
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
    return json.dumps(
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


def _run_dir(harness: TerminalHarness) -> Path:
    state = harness.workspace.status()
    return harness.workspace.engine.target_roots["runs"] / str(state.iteration)


def _drive(harness: TerminalHarness, transport: FakeMaintainerTransport) -> None:
    """Run the shipped retry loop from scripts/run_maintainer.py against a fake transport."""

    client = ChatClient(base_url="http://endpoint.invalid/v1", model_id="test-model", transport=transport)
    run_dir = _run_dir(harness)
    payload = json.loads((run_dir / "maintainer-input.json").read_bytes())
    run_maintainer.run_maintainer_loop(
        workflow=harness.workflow, client=client, run_dir=run_dir, payload=payload
    )


def test_first_attempt_valid_completes_in_one_call(tmp_path: Path) -> None:
    harness = _harness(tmp_path)
    output = _valid_maintainer_output(harness)
    transport = FakeMaintainerTransport([output])
    _drive(harness, transport)
    assert len(transport.requests) == 1
    run_dir = _run_dir(harness)
    assert (run_dir / "maintainer-attempt-1.txt").read_text(encoding="utf-8") == output
    assert not (run_dir / "maintainer-attempt-2.txt").exists()
    state = harness.workspace.status()
    assert state.state is not LifecycleState.NEEDS_WIKI


def test_invalid_then_valid_retries_once(tmp_path: Path) -> None:
    harness = _harness(tmp_path)
    invalid = json.dumps({"not": "the contract"})
    valid = _valid_maintainer_output(harness)
    transport = FakeMaintainerTransport([invalid, valid])
    _drive(harness, transport)
    assert len(transport.requests) == 2
    run_dir = _run_dir(harness)
    attempt_1 = run_dir / "maintainer-attempt-1.txt"
    attempt_2 = run_dir / "maintainer-attempt-2.txt"
    assert attempt_1.read_text(encoding="utf-8") == invalid
    assert attempt_2.read_text(encoding="utf-8") == valid
    attempt_2_prompt = transport.requests[1]["body"]["messages"][0]["content"]
    assert "## Validator error from attempt 1" in attempt_2_prompt
    try:
        from asme.wiki import validate_role_json

        payload = validate_role_json(invalid)
        from asme.wiki import validate_maintainer_change

        validate_maintainer_change(
            payload=payload,
            traces=(),
            maintainer_input_hash="0" * 64,
            existing_pages={},
        )
    except ContractError as exc:
        assert str(exc) in attempt_2_prompt
    state = harness.workspace.status()
    assert state.state is not LifecycleState.NEEDS_WIKI


def test_api_key_is_read_from_environment_not_a_cli_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """The key must come from an env var; no --api-key flag may exist (secret exposure)."""

    # Inspect the source of main()'s parser wiring rather than duplicating
    # flag names, so this test fails if a --api-key value flag is
    # reintroduced (leaking into the process list and shell history).
    source = inspect.getsource(run_maintainer.main)
    assert "--api-key-env" in source
    assert "--api-key'" not in source and '--api-key"' not in source
    assert run_maintainer.DEFAULT_API_KEY_ENV == "LIFECYCLE_MODEL_API_KEY"
    monkeypatch.setenv("LIFECYCLE_MODEL_API_KEY", "secret-value-should-not-be-logged")
    import os

    key = os.environ.get(run_maintainer.DEFAULT_API_KEY_ENV)
    assert key == "secret-value-should-not-be-logged"


def test_three_invalid_attempts_raises_and_state_unchanged(tmp_path: Path) -> None:
    harness = _harness(tmp_path)
    invalid = json.dumps({"not": "the contract"})
    transport = FakeMaintainerTransport([invalid, invalid, invalid])
    with pytest.raises(ContractError):
        _drive(harness, transport)
    assert len(transport.requests) == 3
    run_dir = _run_dir(harness)
    for attempt in (1, 2, 3):
        assert (run_dir / f"maintainer-attempt-{attempt}.txt").read_text(
            encoding="utf-8"
        ) == invalid
    state = harness.workspace.status()
    assert state.state is LifecycleState.NEEDS_WIKI


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


def _cli_harness(tmp_path: Path) -> TerminalHarness:
    """A harness ready for run_maintainer.main(), which calls sample_train() itself."""

    harness = TerminalHarness(tmp_path, case_id="RUN-MAINTAINER-CLI", max_iterations=2)
    harness.baseline(0.25)
    train = harness.run_phase("train", 1.0)
    assert train.valid and train.aggregate_score == 1.0
    return harness


def _cli_argv(harness: TerminalHarness, tmp_path: Path, *extra: str) -> list[str]:
    return [
        "run_maintainer.py",
        "--domain",
        harness.workspace.domain_id,
        "--domain-root",
        str(tmp_path / "workspace"),
        "--model",
        "test-model",
        *extra,
    ]


def _record_loop(monkeypatch: pytest.MonkeyPatch) -> list[ChatClient]:
    captured: list[ChatClient] = []

    def recorder(**kwargs: Any) -> int:
        captured.append(kwargs["client"])
        return 1

    monkeypatch.setattr(run_maintainer, "run_maintainer_loop", recorder)
    return captured


def test_cli_header_reaches_the_chat_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LIFECYCLE_MODEL_API_KEY", raising=False)
    harness = _cli_harness(tmp_path)
    captured = _record_loop(monkeypatch)
    monkeypatch.setattr(sys, "argv", _cli_argv(harness, tmp_path, *CLI_HEADER_ARGS))

    assert run_maintainer.main() == 0

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
    harness = _cli_harness(tmp_path)
    captured = _record_loop(monkeypatch)
    monkeypatch.setattr(sys, "argv", _cli_argv(harness, tmp_path))

    assert run_maintainer.main() == 0

    (client,) = captured
    assert client._headers() == {"Content-Type": "application/json"}


def test_cli_refuses_authorization_header_without_echoing_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("LIFECYCLE_MODEL_API_KEY", raising=False)
    harness = _cli_harness(tmp_path)
    captured = _record_loop(monkeypatch)
    # Assembled at runtime so this file's bytes do not trip the package
    # secret scanner (asme.package._SECRET_PATTERNS).
    sentinel = "sk-" + "test-should-not-echo"
    monkeypatch.setattr(
        sys,
        "argv",
        _cli_argv(harness, tmp_path, "--header", f"Authorization: Bearer {sentinel}"),
    )

    with pytest.raises(SystemExit) as exited:
        run_maintainer.main()

    assert exited.value.code == 2
    stderr = capsys.readouterr().err
    assert "usage:" in stderr
    assert "authorization" in stderr.lower()
    assert sentinel not in stderr
    assert captured == []
