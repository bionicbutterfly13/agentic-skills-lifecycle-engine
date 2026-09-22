#!/usr/bin/env python3
"""Drive one rollout phase through the direct adapter against a live model.

Usage:
    python scripts/run_rollout.py --domain <id> --domain-root <path> \
        --phase baseline --model qwen3.5:9b \
        --base-url http://127.0.0.1:11434/v1

The phase is one of the engine's rollout phases: baseline, train, val, or
val_confirm. The adapter is configured once and reused for every task in the
phase, so the capability report bound into each prepared job stays stable.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from asme.adapter import ProviderPolicy
from asme.workspace import DomainWorkspace, WorkspaceLayout
from asme.workflow import EvolutionWorkflow

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "adapters"))

from direct import DirectAdapter  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--domain-root", required=True, type=Path)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    parser.add_argument("--provider", default="ollama")
    parser.add_argument("--max-output-tokens", type=int, default=2048)
    args = parser.parse_args()

    adapter = DirectAdapter(
        base_url=args.base_url,
        model_id=args.model,
        provider=args.provider,
        max_output_tokens=args.max_output_tokens,
    )
    report = adapter.probe()
    policy = ProviderPolicy(
        (args.provider,), (args.model,), require_openai_backed=False
    )

    workspace = DomainWorkspace(
        domain_id=args.domain, layout=WorkspaceLayout.under(args.domain_root)
    )
    workflow = EvolutionWorkflow(workspace)

    prepared = workflow.prepare_rollout(
        phase=args.phase, capability=report, provider_policy=policy
    )
    print(f"prepared {len(prepared)} task(s) for phase {args.phase}", flush=True)

    for index, item in enumerate(prepared, 1):
        start = time.time()
        execution = adapter.dispatch(item.job)
        elapsed = time.time() - start
        workflow.record_execution(
            phase=args.phase, task_id=item.task_id, execution=execution
        )
        preview = execution.returned_output.replace("\n", " ")[-80:]
        print(
            f"  [{index}/{len(prepared)}] {item.task_id} "
            f"{elapsed:6.1f}s {execution.termination} | ...{preview}",
            flush=True,
        )

    manifest = workflow.ingest_rollout(phase=args.phase)
    print(f"manifest valid={manifest.valid} digest={manifest.digest[:16]}")
    scores = [entry.score for entry in manifest.entries]
    if scores and all(score is not None for score in scores):
        print(f"score = {sum(scores) / len(scores):.4f}  ({scores})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
