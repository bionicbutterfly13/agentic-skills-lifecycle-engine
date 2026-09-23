"""Verbatim paper-prompt loading and local Maintainer/Proposer contract wrappers.

The paper's Appendix E prompts (references/paper-prompts/*.txt) are reproduced
byte-for-byte and never mutated. This module states this engine's exact JSON
contracts for the Maintainer and Proposer roles as separate wrapper text,
concatenated after the verbatim paper text, per ADR-0005: local additions are
never edited into the paper text itself.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .canonical import ContractError

PAPER_PROMPTS_ROOT = Path(__file__).parents[2] / "references" / "paper-prompts"

_ROLE_FILES = {
    "inference": "E1-inference-agent-prompts.txt",
    "maintainer": "E2-wiki-maintainer-prompt.txt",
    "proposer": "E3-skill-proposer-prompt.txt",
}


def load_paper_prompt(role: str) -> str:
    """Return the exact verbatim text of one Appendix E paper prompt."""

    filename = _ROLE_FILES.get(role)
    if filename is None:
        raise ContractError(f"unknown paper prompt role: {role!r}")
    path = PAPER_PROMPTS_ROOT / filename
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"paper prompt file is unreadable: {path}") from exc


MAINTAINER_CONTRACT_WRAPPER = """\
## This Engine's Exact Output Contract (local addition, not paper text)

The paper's own field names above describe the general Wiki Maintainer role. This
engine requires the exact JSON contract below instead, enforced mechanically by
asme.wiki.validate_maintainer_change. Return one JSON object with exactly these
top-level keys:

- "create_patterns": an object (not a list) mapping new pattern name -> full pattern
  page text.
- "update_patterns": an object (not a list) mapping existing pattern name -> a
  nonempty list of patch operations, each shaped {"op": "append"|"replace"|
  "insert_after", "target": "...", "content": "..."} ("target" is omitted or blank
  for "append").
- "update_index": the complete updated index.md text.
- "append_log": the complete log entry text to append.
- "attestation": an object with exactly the keys "input_hash", "class_coverage",
  and "per_pattern".

A pattern name must not appear in both "create_patterns" and "update_patterns".

Every pattern page (new or patched result) must follow this exact grammar:

- First line exactly one of: "pattern_kind: failure", "pattern_kind: success",
  "pattern_kind: paired".
- Then, in this exact order, the headings "## Description", "## Root cause",
  "## Evidence", "## Solution", each appearing exactly once.
- Evidence lines are shaped: `- fail|pass task_id: "JSON-encoded span"` (the span
  is a JSON string literal, not raw text).
- The page must be 10 to 30 lines total.

The "attestation" object's "per_pattern" key must map every pattern name that was
created or updated (and only those names) to an object with these keys:
"pattern_kind", "failure_traces", "success_traces", "quoted_commands",
"dedup_disposition", "dedup_reason", "root_cause_reason", "generalizable_because".
"""

PROPOSER_CONTRACT_WRAPPER = """\
## This Engine's Exact Output Contract (local addition, not paper text)

The paper's own field names above describe the general Skill Proposer role. This
engine requires the exact JSON contract below instead, enforced mechanically by
asme.proposal.validate_proposal. Return one JSON object with exactly these keys,
determined by "action":

- "action": one of "create", "patch", "no_action".
- "context_hash", "reason", "trace_ids": always required.
- "create" additionally requires "skill_name" and "files", a mapping of relative
  path to full text content that must include "SKILL.md".
- "patch" additionally requires "skill_name" and "patches", a list of objects
  shaped {"path": "...", "target": "...", "replacement": "..."} where "target"
  must appear exactly once in the named file's current content.
"""


def build_role_prompt(role: str, payload: Mapping[str, Any]) -> str:
    """Assemble verbatim paper text + local wrapper + exact JSON input.

    Never formats Lifecycle-specific fields into the verbatim paper string
    itself; concatenation only, per ADR-0005's "never edited into the paper
    text" rule.
    """

    if role == "maintainer":
        wrapper = MAINTAINER_CONTRACT_WRAPPER
    elif role == "proposer":
        wrapper = PROPOSER_CONTRACT_WRAPPER
    else:
        raise ContractError(f"unknown role contract wrapper: {role!r}")
    paper_text = load_paper_prompt(role)
    encoded_input = json.dumps(dict(payload), sort_keys=True, indent=2)
    return paper_text + "\n\n" + wrapper + "\n\n## Input\n\n" + encoded_input
