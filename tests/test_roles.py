"""Offline tests for verbatim paper-prompt loading and contract wrapper assembly."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from asme.canonical import ContractError
from asme.roles import (
    MAINTAINER_CONTRACT_WRAPPER,
    PROPOSER_CONTRACT_WRAPPER,
    build_role_prompt,
    load_paper_prompt,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
# The commit at which the verbatim .md prompts existed under .planning/paper-prompts/,
# immediately before this plan's git-mv relocated them to references/paper-prompts/*.txt.
HISTORICAL_COMMIT = "f419d08"
_HISTORICAL_PATHS = {
    "inference": ".planning/paper-prompts/E1-inference-agent-prompts.md",
    "maintainer": ".planning/paper-prompts/E2-wiki-maintainer-prompt.md",
    "proposer": ".planning/paper-prompts/E3-skill-proposer-prompt.md",
}


def _git_available() -> bool:
    try:
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--git-dir"],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def _historical_bytes(role: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"{HISTORICAL_COMMIT}:{_HISTORICAL_PATHS[role]}"],
        check=True,
        capture_output=True,
    )
    return result.stdout


@pytest.mark.parametrize("role", ["maintainer", "proposer", "inference"])
def test_load_paper_prompt_matches_history_byte_for_byte(role: str) -> None:
    """The move must not change a single byte, verified against git history."""

    if not _git_available():
        pytest.skip("git is unavailable (e.g. an extracted sdist); cannot verify history")
    historical = _historical_bytes(role)
    loaded = load_paper_prompt(role).encode("utf-8")
    assert hashlib.sha256(loaded).hexdigest() == hashlib.sha256(historical).hexdigest()
    assert loaded == historical


def test_load_paper_prompt_unknown_role_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        load_paper_prompt("no-such-role")


def test_build_role_prompt_maintainer_never_mutates_paper_text() -> None:
    payload = {"sample": "x"}
    prompt = build_role_prompt("maintainer", payload)
    assert load_paper_prompt("maintainer") in prompt
    for key in (
        "create_patterns",
        "update_patterns",
        "update_index",
        "append_log",
        "attestation",
    ):
        assert key in prompt
    assert json.dumps(payload, sort_keys=True, indent=2) in prompt
    assert prompt.index(load_paper_prompt("maintainer")) < prompt.index(
        MAINTAINER_CONTRACT_WRAPPER
    )


def test_build_role_prompt_proposer_never_mutates_paper_text() -> None:
    payload = {"sample": "y"}
    prompt = build_role_prompt("proposer", payload)
    assert load_paper_prompt("proposer") in prompt
    for key in (
        "action",
        "context_hash",
        "reason",
        "trace_ids",
        "skill_name",
        "files",
        "patches",
    ):
        assert key in prompt
    assert json.dumps(payload, sort_keys=True, indent=2) in prompt
    assert prompt.index(load_paper_prompt("proposer")) < prompt.index(
        PROPOSER_CONTRACT_WRAPPER
    )


def test_build_role_prompt_unknown_role_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        build_role_prompt("no-such-role", {})
