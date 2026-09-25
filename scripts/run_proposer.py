#!/usr/bin/env python3
"""Drive the Skill Proposer role end to end against a live model.

Usage:
    python scripts/run_proposer.py --domain <id> --domain-root <path> \
        --model qwen3.5:9b --base-url http://127.0.0.1:11434/v1 --mode detective
    python scripts/run_proposer.py --domain <id> --domain-root <path> \
        --model <model> --base-url <url> --header "NAME: VALUE" --header "NAME: VALUE"

Two modes exist, per ADR-0004:

- detective (default): a multi-turn ReAct loop that reads the wiki and prior
  train traces through a read_file tool call against a virtual, read-only
  filesystem built only from workflow.proposer_context()'s payload, then
  calls finish() with a proposal. finish() is refused (once, then raised)
  unless at least 4 distinct traces were read and every cited trace_id was
  actually read. Every read is journaled to a persisted reads log.
- single-shot: the local ablation flag. One call with the full proposer
  context payload, no tool loop, no retry.

In both modes, context_hash is never taken from the model: the driver
computes it mechanically from the exact proposer_context() bytes and
inserts it before calling workflow.apply_proposal.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

from asme.canonical import ContractError, sha256_bytes
from asme.roles import build_role_prompt
from asme.model_client import ChatClient, ModelClientError, parse_header_specs
from asme.workspace import DomainWorkspace, WorkspaceLayout
from asme.workflow import EvolutionWorkflow

# Default env var name holding the model endpoint's API key. Never taken as a
# CLI value: a --api-key flag would leak into the process list and shell
# history. The key is optional (a local Ollama endpoint needs none).
DEFAULT_API_KEY_ENV = "LIFECYCLE_MODEL_API_KEY"

# Detective mode's default turn cap. A local, non-paper-specified bound
# preventing an unbounded ReAct loop (T-260923-09).
DEFAULT_MAX_TURNS = 20

# Detective mode requires at least this many distinct read traces before a
# finish() call is accepted, per ADR-0004.
MIN_TRACES_READ = 4

# Detective mode's finish() retry budget: one retry after an under-provenanced
# finish() call, then raise. Local design choice, not paper-specified.
FINISH_RETRY_BUDGET = 1

READ_FILE_TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": (
            "Read one file from the read-only detective filesystem (wiki pages, "
            "train traces, and active skill files). Returns the file's exact text."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Exact path, e.g. 'wiki/index.md' or 'traces/train-1'.",
                }
            },
            "required": ["path"],
        },
    },
}

FINISH_TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "finish",
        "description": (
            "Submit the final Skill Proposer decision. Requires having read at "
            "least 4 distinct train traces, and every trace_id cited must have "
            "been read via read_file first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "proposal": {
                    "type": "object",
                    "description": (
                        "The proposal object: action, context_hash, reason, "
                        "trace_ids, and action-specific fields per the contract."
                    ),
                }
            },
            "required": ["proposal"],
        },
    },
}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--domain-root", required=True, type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--provider", default="ollama")
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument(
        "--mode", choices=("detective", "single-shot"), default="detective"
    )
    parser.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS)
    parser.add_argument(
        "--header",
        action="append",
        default=None,
        metavar="NAME:VALUE",
        help=(
            "Extra HTTP header sent with every model request; may be repeated. "
            "Values are visible in the process list and shell history, so never "
            "pass secrets. Authorization is refused: the key comes only from "
            "--api-key-env."
        ),
    )
    return parser


def build_workspace_and_client(
    args: argparse.Namespace, *, extra_headers: Mapping[str, str] | None = None
) -> tuple[DomainWorkspace, EvolutionWorkflow, ChatClient]:
    workspace = DomainWorkspace(
        domain_id=args.domain, layout=WorkspaceLayout.under(args.domain_root)
    )
    workflow = EvolutionWorkflow(workspace)
    key = os.environ.get(args.api_key_env)
    client = ChatClient(
        base_url=args.base_url, model_id=args.model, api_key=key, extra_headers=extra_headers
    )
    return workspace, workflow, client


def run_dir_for(workspace: DomainWorkspace) -> Path:
    state = workspace.status()
    return workspace.engine.target_roots["runs"] / str(state.iteration)


def run_single_shot(workflow: EvolutionWorkflow, client: ChatClient, run_dir: Path) -> None:
    """One proposer_context -> model call -> apply_proposal round trip. No retry."""

    context_bytes = workflow.proposer_context()
    context_payload = json.loads(context_bytes)
    prompt = build_role_prompt("proposer", context_payload)
    response = client.complete([{"role": "user", "content": prompt}])
    response_text = str(response.get("content") or "")
    output_path = run_dir / "proposer-single-shot-output.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(response_text, encoding="utf-8")
    workflow.apply_proposal(response_text)


def run_detective(
    workflow: EvolutionWorkflow,
    client: ChatClient,
    run_dir: Path,
    *,
    max_turns: int,
) -> None:
    """Multi-turn ReAct loop with a virtual read-only filesystem and read journal."""

    context_bytes = workflow.proposer_context()
    context_payload = json.loads(context_bytes)
    virtual_fs = _build_virtual_filesystem(context_payload)
    prompt = build_role_prompt("proposer", context_payload)
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    reads_log: list[dict[str, Any]] = []
    read_traces: set[str] = set()
    finish_attempts = 0

    for turn in range(1, max_turns + 1):
        response = client.complete(
            messages, tools=[READ_FILE_TOOL_SCHEMA, FINISH_TOOL_SCHEMA]
        )
        tool_calls = response.get("tool_calls") or []
        if not tool_calls:
            # No tool call at all: treat as a stalled turn, replay the same
            # instruction rather than silently ending the loop.
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "You must call read_file or finish. No tool call was "
                        "received in your previous response."
                    ),
                }
            )
            continue
        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": response.get("content") or "",
            "tool_calls": tool_calls,
        }
        messages.append(assistant_message)
        for call in tool_calls:
            name, arguments, call_id = _parse_tool_call(call)
            if name == "read_file":
                path = arguments.get("path")
                content, refused = _resolve_read(virtual_fs, path)
                if not refused:
                    read_traces_update(read_traces, path)
                reads_log.append(
                    {
                        "turn": turn,
                        "path": path,
                        "sha256": sha256_bytes(
                            content if content is not None else _REFUSAL_SENTINEL
                        ),
                        "refused": refused,
                    }
                )
                tool_result = (
                    content.decode("utf-8")
                    if content is not None
                    else "refused: path is outside the detective filesystem"
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": tool_result,
                    }
                )
            elif name == "finish":
                finish_attempts += 1
                proposal = arguments.get("proposal")
                failure = _finish_failure(proposal, read_traces=read_traces)
                if failure is None:
                    _persist_reads_log(run_dir, reads_log)
                    # Driver-inserted: mechanical binding the model cannot compute.
                    proposal["context_hash"] = sha256_bytes(context_bytes)
                    workflow.apply_proposal(json.dumps(proposal, sort_keys=True))
                    return
                if finish_attempts > FINISH_RETRY_BUDGET:
                    _persist_reads_log(run_dir, reads_log)
                    raise ContractError(
                        f"detective-mode finish() refused and retry budget exhausted: {failure}"
                    )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": f"finish() refused: {failure}. Read more traces or "
                        "correct trace_ids, then call finish again.",
                    }
                )
            else:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": f"refused: unknown tool {name!r}",
                    }
                )
    _persist_reads_log(run_dir, reads_log)
    raise ContractError(f"detective mode reached the turn cap ({max_turns}) without finishing")


_REFUSAL_SENTINEL = b"__refused__"


def read_traces_update(read_traces: set[str], path: str | None) -> None:
    if isinstance(path, str) and path.startswith("traces/"):
        read_traces.add(path[len("traces/") :])


def _parse_tool_call(call: Mapping[str, Any]) -> tuple[str, dict[str, Any], str]:
    function = call.get("function") or {}
    name = str(function.get("name") or "")
    raw_arguments = function.get("arguments")
    if isinstance(raw_arguments, str):
        try:
            arguments = json.loads(raw_arguments) if raw_arguments else {}
        except json.JSONDecodeError as exc:
            raise ContractError("tool call arguments are malformed JSON") from exc
    elif isinstance(raw_arguments, Mapping):
        arguments = dict(raw_arguments)
    else:
        arguments = {}
    call_id = str(call.get("id") or "")
    return name, arguments, call_id


def _resolve_read(virtual_fs: dict[str, bytes], path: Any) -> tuple[bytes | None, bool]:
    """Exact-match only; never resolves path traversal. Returns (content, refused)."""

    if not isinstance(path, str) or path not in virtual_fs:
        return None, True
    return virtual_fs[path], False


def _finish_failure(proposal: Any, *, read_traces: set[str]) -> str | None:
    if not isinstance(proposal, Mapping):
        return "proposal argument must be an object"
    trace_ids = proposal.get("trace_ids")
    if not isinstance(trace_ids, list) or not trace_ids:
        return "proposal trace_ids must be a nonempty list"
    if len(read_traces) < MIN_TRACES_READ:
        return f"only {len(read_traces)} distinct traces read; at least {MIN_TRACES_READ} required"
    unread = sorted(set(str(item) for item in trace_ids) - read_traces)
    if unread:
        return f"proposal cites trace_ids never read: {unread}"
    return None


def _persist_reads_log(run_dir: Path, reads_log: list[dict[str, Any]]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "proposer-reads-log.json"
    path.write_text(json.dumps(reads_log, indent=2, sort_keys=True), encoding="utf-8")


def _build_virtual_filesystem(context_payload: Mapping[str, Any]) -> dict[str, bytes]:
    """Build the detective-mode read-only filesystem from proposer_context() only.

    Only wiki/*, traces/<train task_id>, and active-skill files are exposed.
    proposer_context() is constructed exclusively from train_outcomes (see
    asme.evidence.proposer_payload, which raises ContractError if a non-train
    answer is ever passed in), so no validation- or test-split content can
    reach this filesystem by construction (T-260923-08). This function adds
    no additional filtering because none is needed: it only ever reads keys
    already present in the train-only payload.
    """

    virtual_fs: dict[str, bytes] = {}

    wiki_pages = context_payload.get("wiki_pages")
    if isinstance(wiki_pages, Mapping):
        for name, text in wiki_pages.items():
            if isinstance(name, str) and isinstance(text, str):
                virtual_fs[f"wiki/{name}"] = text.encode("utf-8")

    impact_history = context_payload.get("impact_history")
    if isinstance(impact_history, list) and impact_history:
        lines = []
        for entry in impact_history:
            if not isinstance(entry, Mapping):
                continue
            lines.append(
                f"iteration {entry.get('iteration')}: {entry.get('outcome')} "
                f"scores={entry.get('scores')}"
            )
        virtual_fs["wiki/skill-impact.md"] = ("\n".join(lines) + "\n").encode("utf-8")

    train_outcomes = context_payload.get("train_outcomes")
    if isinstance(train_outcomes, list):
        for outcome in train_outcomes:
            if not isinstance(outcome, Mapping):
                continue
            task_id = outcome.get("task_id")
            if not isinstance(task_id, str):
                continue
            body = (
                f"task_id: {task_id}\n"
                f"input: {outcome.get('input')}\n"
                f"expected: {outcome.get('expected')}\n"
                f"returned_output: {outcome.get('returned_output')}\n"
                f"score: {outcome.get('score')}\n"
            )
            virtual_fs[f"traces/{task_id}"] = body.encode("utf-8")

    active_skill = context_payload.get("active_skill")
    if isinstance(active_skill, str) and active_skill:
        virtual_fs["active_skill.md"] = active_skill.encode("utf-8")

    return virtual_fs


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    # Parsed before any workspace access; refusal exits with argparse status 2.
    # Header values are never printed or logged.
    try:
        extra_headers = parse_header_specs(args.header)
    except ModelClientError as exc:
        parser.error(str(exc))
    workspace, workflow, client = build_workspace_and_client(args, extra_headers=extra_headers)
    run_dir = run_dir_for(workspace)
    if args.mode == "single-shot":
        run_single_shot(workflow, client, run_dir)
    else:
        run_detective(workflow, client, run_dir, max_turns=args.max_turns)
    return 0


if __name__ == "__main__":
    sys.exit(main())
