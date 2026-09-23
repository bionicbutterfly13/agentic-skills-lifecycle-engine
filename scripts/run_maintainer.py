#!/usr/bin/env python3
"""Drive the Wiki Maintainer role end to end against a live model.

Usage:
    python scripts/run_maintainer.py --domain <id> --domain-root <path> \
        --model qwen3.5:9b --base-url http://127.0.0.1:11434/v1

Flow: workflow.sample_train() has already persisted the maintainer-input
payload for the current iteration. This script reads that payload back,
builds the Maintainer prompt (paper text + local contract wrapper + JSON
input), calls the model, and applies the result through
workflow.apply_wiki(). On a ContractError from apply_wiki, it retries with
an appended validator-error section, up to 3 attempts total. Every raw
attempt is persisted to the runs root for evidence, regardless of outcome.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from asme.canonical import ContractError, require_regular_file
from asme.roles import build_role_prompt
from asme.model_client import ChatClient
from asme.workspace import DomainWorkspace, WorkspaceLayout
from asme.workflow import EvolutionWorkflow

# Local retry policy, not paper-specified.
MAX_ATTEMPTS = 3

# Default env var name holding the model endpoint's API key. Never taken as a
# CLI value: a --api-key flag would leak into the process list and shell
# history. The key is optional (a local Ollama endpoint needs none).
DEFAULT_API_KEY_ENV = "LIFECYCLE_MODEL_API_KEY"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--domain-root", required=True, type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--provider", default="ollama")
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    args = parser.parse_args()

    workspace = DomainWorkspace(
        domain_id=args.domain, layout=WorkspaceLayout.under(args.domain_root)
    )
    workflow = EvolutionWorkflow(workspace)
    key = os.environ.get(args.api_key_env)
    client = ChatClient(base_url=args.base_url, model_id=args.model, api_key=key)

    workflow.sample_train()
    state = workspace.status()
    run_dir = workspace.engine.target_roots["runs"] / str(state.iteration)
    input_path = require_regular_file(
        run_dir / "maintainer-input.json", root=workspace.engine.target_roots["runs"]
    )
    payload = _load_json(input_path)

    prompt = build_role_prompt("maintainer", payload)
    last_error: ContractError | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if attempt > 1 and last_error is not None:
            prompt = (
                prompt
                + f"\n\n## Validator error from attempt {attempt - 1}\n\n"
                + str(last_error)
                + "\n\nCorrect the output and return the complete corrected JSON object."
            )
        response = client.complete([{"role": "user", "content": prompt}])
        response_text = str(response.get("content") or "")
        attempt_path = run_dir / f"maintainer-attempt-{attempt}.txt"
        attempt_path.parent.mkdir(parents=True, exist_ok=True)
        attempt_path.write_text(response_text, encoding="utf-8")
        try:
            workflow.apply_wiki(response_text)
        except ContractError as exc:
            last_error = exc
            print(f"attempt {attempt}/{MAX_ATTEMPTS} failed: {exc}", flush=True)
            continue
        print(f"attempt {attempt}/{MAX_ATTEMPTS} succeeded", flush=True)
        return 0
    assert last_error is not None
    raise last_error


def _load_json(path: Path):
    try:
        return json.loads(path.read_bytes())
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractError(f"maintainer input is malformed: {path}") from exc


if __name__ == "__main__":
    sys.exit(main())
