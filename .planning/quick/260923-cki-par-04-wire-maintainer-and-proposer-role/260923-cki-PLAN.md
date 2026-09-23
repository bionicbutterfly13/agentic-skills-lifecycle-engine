---
phase: 260923-cki-par-04-wire-maintainer-and-proposer-role
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/paper-prompts/E1-inference-agent-prompts.md
  - .planning/paper-prompts/E2-wiki-maintainer-prompt.md
  - .planning/paper-prompts/E3-skill-proposer-prompt.md
  - references/paper-prompts/E1-inference-agent-prompts.txt
  - references/paper-prompts/E2-wiki-maintainer-prompt.txt
  - references/paper-prompts/E3-skill-proposer-prompt.txt
  - MANIFEST.in
  - src/asme/roles.py
  - src/asme/model_client.py
  - scripts/run_maintainer.py
  - tests/test_roles.py
  - tests/test_model_client.py
  - tests/test_run_maintainer.py
autonomous: true
requirements: [PAR-04, PAR-05]

estimate:
  tokens: 95000
  raw_tokens: 63000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "The paper's Appendix E prompts ship inside the public distribution at references/paper-prompts/*.txt, verbatim, with CC BY 4.0 attribution intact, satisfying PAR-05 for real."
    - "A local wrapper module states this engine's exact JSON contract for the Maintainer and Proposer roles without editing a single byte of the verbatim paper text."
    - "scripts/run_maintainer.py drives workflow.sample_train() -> model call -> workflow.apply_wiki() against a live OpenAI-compatible endpoint, retrying at most twice on ContractError while keeping every raw attempt for evidence."
  artifacts:
    - references/paper-prompts/E2-wiki-maintainer-prompt.txt
    - references/paper-prompts/E3-skill-proposer-prompt.txt
    - src/asme/roles.py
    - src/asme/model_client.py
    - scripts/run_maintainer.py
  key_links:
    - "scripts/run_maintainer.py -> asme.workflow.EvolutionWorkflow.sample_train/apply_wiki (core state machine, not forked)"
    - "src/asme/roles.py -> references/paper-prompts/*.txt (verbatim text loaded at runtime, never re-embedded as a literal string)"
    - "src/asme/model_client.py -> OpenAI-compatible /chat/completions (chat client used by both role drivers)"
---

<objective>
Move the paper's verbatim Appendix E prompts to their distributable home, add the local
wrapper layer that states this engine's exact Maintainer/Proposer JSON contracts on top of
the verbatim text (per ADR-0005), build a small tool-calling-capable chat client, and drive
the Wiki Maintainer role end to end against a live model with a bounded retry policy.

Purpose: PAR-05 currently claims the paper prompts ship at `references/paper-prompts/`
but they only exist under `.planning/paper-prompts/`, which never ships (`.planning` is
excluded from every distribution). That claim is false today. This plan makes it true, and
lands the first of two role drivers PAR-04 needs (the Proposer driver is plan 02, which
depends on the model client this plan creates).

Output: `references/paper-prompts/*.txt` (shipped, verbatim, `.txt` so the markdown link
checker in `scripts/verify_distribution.py` never parses them for link dependencies),
`src/asme/roles.py` (wrapper contract text + prompt assembly), `src/asme/model_client.py`
(chat-completions client with tool-call support), `scripts/run_maintainer.py` (live
Maintainer driver with retry), and offline tests for all three.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@AGENTS.md
@docs/adr/0004-detective-mode-proposer.md
@docs/adr/0005-verbatim-paper-prompts.md
@CONTEXT.md
@src/asme/workflow.py
@src/asme/wiki.py
@src/asme/evidence.py
@adapters/direct/__init__.py
@scripts/run_rollout.py
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Relocate verbatim prompts to references/, wire MANIFEST.in, tracer end-to-end Maintainer call against a fake transport</name>
  <files>references/paper-prompts/E1-inference-agent-prompts.txt, references/paper-prompts/E2-wiki-maintainer-prompt.txt, references/paper-prompts/E3-skill-proposer-prompt.txt, MANIFEST.in, src/asme/roles.py, src/asme/model_client.py, scripts/run_maintainer.py, tests/test_run_maintainer.py</name>
  <action>
Git-move (not copy-and-delete-separately; use `git mv` so history follows) all three
files from `.planning/paper-prompts/` to `references/paper-prompts/`, renaming the
`.md` extension to `.txt` on the way (content byte-for-byte identical, including the
CC BY 4.0 attribution comment block at the top of each file). `.planning/paper-prompts/`
must end up empty of these three files; leave the directory itself alone if git leaves
it (do not fight git over an empty dir). Reasoning for `.txt`: `_document_dependencies`
in scripts/verify_distribution.py only parses files ending in `.md` for markdown link
syntax, so a `.txt` extension exempts these files from that link-resolution pass without
touching a single byte of the paper's text. This is a local packaging decision, not a
paper-parity concern, and belongs in code comments only, never in the verbatim files.

Add the three new paths to MANIFEST.in in sorted position: alphabetically
`references/paper-prompts/E1-inference-agent-prompts.txt` through
`E3-skill-proposer-prompt.txt` sort after `include references/paper-notes.md` and
before `include references/verification/README.md`. Insert three `include` lines there.

Create `src/asme/roles.py`, a new core module (importable by scripts, not by adapters):
a function `load_paper_prompt(role: str) -> str` that reads the matching verbatim
`.txt` file from the installed package's `references/paper-prompts/` directory
(resolve relative to `Path(__file__).parents[2] / "references" / "paper-prompts"` to
work from a source checkout; do not assume a specific packaging layout — this module
lives in core, not in an adapter, so it may import freely from asme.canonical) and
returns its exact text unmodified. Add `MAINTAINER_CONTRACT_WRAPPER` and
`PROPOSER_CONTRACT_WRAPPER` as separate local string constants (or template functions)
in this same file stating, in plain English wrapper prose appended after the verbatim
text: for Maintainer, the exact JSON contract from src/asme/wiki.py's
validate_maintainer_change (top-level keys create_patterns/update_patterns/update_index/
append_log/attestation as dict-shaped mappings, not lists; the pattern page grammar
from assets/pattern.md.tmpl — first line `pattern_kind: failure|success|paired`,
then `## Description`, `## Root cause`, `## Evidence`, `## Solution` headings in that
exact order, Evidence lines shaped `- fail|pass task_id: "JSON-encoded span"`; and the
attestation object's exact required keys input_hash/class_coverage/per_pattern); for
Proposer, the exact JSON contract from src/asme/proposal.py's validate_proposal
(top-level action one of create/patch/no_action; context_hash/reason/trace_ids always
required; create additionally requires skill_name and a files mapping of relative path
to text content including SKILL.md; patch additionally requires skill_name and a
patches list of objects shaped {path, target, replacement} where target must appear
exactly once in the named file). Add a function
`build_role_prompt(role: str, payload: dict) -> str` that returns
`load_paper_prompt(role) + "\n\n" + wrapper_text + "\n\n## Input\n\n" + json.dumps(payload, sort_keys=True, indent=2)`
so the model receives paper text, then the local contract wrapper, then the exact
JSON it must reason over. Never format Lifecycle-specific fields into the verbatim
paper string itself (no `.format()` or f-string substitution against the loaded
paper text) — concatenation only, per ADR-0005's "never edited into the paper text"
rule.

Create `src/asme/model_client.py`: a `ChatClient` class wrapping one OpenAI-compatible
`/chat/completions` endpoint, constructed with base_url, model_id, api_key (optional),
timeout_seconds, temperature=0.0, and an injectable `transport` callable for tests
(mirror adapters/direct/__init__.py's `_send`/`urllib.request` pattern exactly, since
this module is core and may duck-type the same way rather than import the adapter).
Provide `complete(messages: list[dict], *, tools: list[dict] | None = None) -> dict`
returning the raw first-choice message mapping (content, tool_calls if present,
finish_reason) so callers can branch on tool_calls without this module knowing about
detective mode or any role-specific behavior — it is a pure transport, no retry logic,
no role awareness.

Create `scripts/run_maintainer.py`, a live driver script (scripts may import any core
module per the adapters-only import restriction). CLI args: --domain, --domain-root,
--base-url, --model, --provider (default ollama), --api-key (optional), matching
scripts/run_rollout.py's argparse style. Flow: construct DomainWorkspace/WorkspaceLayout
exactly as scripts/run_rollout.py does, construct EvolutionWorkflow, call
`workflow.sample_train()` to get the TraceView tuple, build the maintainer_input
payload workflow already persisted (read it back via the run directory path
`{iteration}/maintainer-input.json` under the runs root, exactly as
workflow.apply_wiki expects to consume it — do not reconstruct the payload by hand),
call `build_role_prompt("maintainer", payload)`, call
`client.complete([{"role": "user", "content": prompt}])`, persist the raw response
text to `{run_dir}/maintainer-attempt-{n}.txt` under the runs root for evidence (n
starting at 1), then call `workflow.apply_wiki(response_text)`. On `ContractError`
from apply_wiki, retry at most 2 additional times (3 attempts total), re-prompting
with the original prompt plus an appended section
`"\n\n## Validator error from attempt {n}\n\n{str(exc)}\n\nCorrect the output and return the complete corrected JSON object."`
Persist every attempt's raw output regardless of outcome. If all 3 attempts fail,
re-raise the last ContractError (do not swallow it) after all raw outputs are
written — the caller must see the failure. Label this retry cap and re-prompt
mechanic with an inline comment `# Local retry policy, not paper-specified.` This is
the tracer: it proves prompt-load, wrapper-assembly, client-transport, and
core-workflow wiring end to end for one role before the Proposer driver (plan 02)
extends the pattern to a multi-turn loop.

Write tests/test_run_maintainer.py using a `FakeTransport` modeled exactly on
tests/test_direct_adapter.py's class (scripted queue of chat-completion responses,
recorded request log) to verify: (a) a first-attempt valid Maintainer JSON completes
in one call and calls apply_wiki exactly once; (b) an invalid first attempt followed
by a valid second attempt succeeds, and both raw attempt files exist on disk with
attempt 2's prompt containing the exact validator error string from attempt 1's
ContractError; (c) three invalid attempts in a row raises ContractError, all three
raw attempt files exist, and workspace state is unchanged (still NEEDS_WIKI) because
apply_wiki never wrote a successful transaction. Use the terminal-path domain
fixture pattern from tests/test_terminal_paths.py's TerminalHarness (or a minimal
inline equivalent) to get a workspace to NEEDS_WIKI state without duplicating its
full setUp — importing TerminalHarness from tests/test_terminal_paths.py in this new
test file is fine, both are test modules.
  </action>
  <verify>
    <automated>PYTHONPATH=src python3 -m pytest tests/test_run_maintainer.py tests/test_distribution.py -x</automated>
  </verify>
  <done>references/paper-prompts/*.txt exist with unchanged verbatim content and CC BY 4.0 headers, MANIFEST.in lists all three in sorted position, src/asme/roles.py assembles paper text + wrapper + JSON input without ever formatting into the paper string, src/asme/model_client.py sends one stateless chat-completions request per call, scripts/run_maintainer.py drives sample_train -> model -> apply_wiki with a 3-attempt retry cap and persists every raw attempt, and tests/test_run_maintainer.py's three scenarios (first-try success, retry-then-success, exhausted retries) all pass against a fake transport.</done>
</task>

<task type="auto">
  <name>Task 2: Wrapper and client unit tests, plus wiring verification against the real verbatim files</name>
  <files>tests/test_roles.py, tests/test_model_client.py</files>
  <action>
Write tests/test_roles.py covering: `load_paper_prompt("maintainer")` returns text
whose sha256 matches the actual bytes of
references/paper-prompts/E2-wiki-maintainer-prompt.txt read directly from disk (a
literal hash-equality check against the real file, not a mock, so a future accidental
edit to the verbatim file is caught here); same check for `load_paper_prompt("proposer")`
against E3-skill-proposer-prompt.txt; `load_paper_prompt("inference")` against
E1-inference-agent-prompts.txt; an unknown role name raises ContractError (or ValueError,
matching whatever this module raises — pick ContractError from asme.canonical for
consistency with the rest of core, since roles.py is a core module). Test
`build_role_prompt("maintainer", {"sample": "x"})` contains the verbatim prompt text
as an exact substring (proves no mutation happened to the paper text), contains the
wrapper's stated required keys (create_patterns, update_patterns, update_index,
append_log, attestation) as literal substrings, and contains the JSON-encoded input
payload as an exact substring via `json.dumps(payload, sort_keys=True, indent=2)`.
Repeat the substring checks for `build_role_prompt("proposer", ...)` against its
required keys (action, context_hash, reason, trace_ids, skill_name, files, patches).

Write tests/test_model_client.py using the same FakeTransport-style pattern as
tests/test_direct_adapter.py: `ChatClient.complete` with a scripted transport
returning a plain-content response returns a mapping with the expected "content" key
and no "tool_calls" key; a scripted transport returning a response with a
`tool_calls` array in the message returns that array unmodified in the result
mapping; passing `tools=[...]` to `complete` places that exact list under the
request body's `"tools"` key (assert on the FakeTransport's recorded request body,
not on internal client state); a transport that raises on the HTTP call surfaces as
a clear exception type from this module (name it `ModelClientError`, mirroring
DirectAdapterError's shape) rather than an unhandled urllib exception.
  </action>
  <verify>
    <automated>PYTHONPATH=src python3 -m pytest tests/test_roles.py tests/test_model_client.py -x</automated>
  </verify>
  <done>tests/test_roles.py proves the loaded prompt text is byte-identical to the real shipped verbatim files and that the wrapper never mutates that text; tests/test_model_client.py proves ChatClient.complete sends tools correctly, surfaces tool_calls to the caller, and raises ModelClientError (not a raw urllib exception) on transport failure. Both files pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| model endpoint -> ChatClient | The remote chat-completions server is untrusted: its JSON body, tool_calls, and content are attacker- or hallucination-controlled input to this process. |
| ChatClient response -> workflow.apply_wiki | The raw model text is untrusted input crossing into asme's validated state-mutation boundary; apply_wiki's existing ContractError-raising validation is the enforcement point, not this plan's driver code. |
| references/paper-prompts/*.txt -> distribution | Publicly shipped bytes; must not carry secrets, absolute paths, or unattributed derivative text. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-260923-01 | Tampering | scripts/run_maintainer.py retry loop | medium | mitigate | Retry count is hard-capped at 3 total attempts in code (not model-configurable), preventing an uncooperative or adversarial model from driving unbounded retries/cost; the cap is asserted by test_run_maintainer.py's exhausted-retries case. |
| T-260923-02 | Tampering | model output reaching apply_wiki | high | mitigate | No new trust is extended: apply_wiki's existing validate_maintainer_change (src/asme/wiki.py) remains the sole mutation gate and this plan adds no bypass path; the driver only ever calls the existing validated entrypoint, never writes wiki/pattern files directly. |
| T-260923-03 | Information Disclosure | raw attempt files under runs root | low | accept | Attempt files contain only the maintainer-input payload (already assembled by workflow.sample_train from train-split traces, never held-out answers per FORBIDDEN_ROLLOUT_FIELDS) and the model's raw reply; no held-out answers or markers are ever placed in the Maintainer prompt, matching the existing role_spec assertion in src/asme/evidence.py. |
| T-260923-04 | Tampering | verbatim paper text integrity | medium | mitigate | test_roles.py asserts sha256 equality between load_paper_prompt's returned text and the actual on-disk file bytes, so any accidental edit to the verbatim files during this move is caught by an automated test, not just review. |
| T-260923-05 | Denial of Service | ChatClient against a slow/hanging endpoint | low | accept | timeout_seconds is a required constructor parameter mirroring adapters/direct's DEFAULT_TIMEOUT_SECONDS pattern; no unbounded wait is introduced. |
</threat_model>

<verification>
Run the full offline suite plus the two named gates from the plan constraints:

```
PYTHONPATH=src timeout 1200 python3 -m pytest -p no:cacheprovider > log 2>&1; echo EXIT=$?
```

Must exit 0. Then confirm the two named gate files explicitly:

```
PYTHONPATH=src python3 -m pytest tests/test_workspace_hermes_adapter.py tests/test_distribution.py
```

Also confirm the adapters-import gate still holds (this plan adds no adapter-side
imports, so it should be unaffected, but the new src/asme/roles.py and model_client.py
modules must never be imported from adapters/):

```
PYTHONPATH=src python3 -m pytest tests/test_governance_dependencies_gate2.py -k test_hf_a03
```
</verification>

<success_criteria>
- references/paper-prompts/{E1,E2,E3}*.txt exist, ship in the source distribution (test_distribution.py's family check for `references`), and are byte-identical to the prior .planning/paper-prompts/*.md content minus the extension change.
- .planning/paper-prompts/E1, E2, and E3 no longer exist (all three moved via git mv, not copied).
- src/asme/roles.py and src/asme/model_client.py exist as core modules, importable by scripts, never imported by anything under adapters/.
- scripts/run_maintainer.py exists and its 3-scenario test suite (first-try success, retry-then-success, exhausted-retries) passes offline against a fake transport.
- MANIFEST.in contains the three new references/paper-prompts/*.txt lines in correct sorted order; test_distribution.py continues to pass.
- Full test suite exits 0.
</success_criteria>

<output>
Create `.planning/quick/260923-cki-par-04-wire-maintainer-and-proposer-role/260923-cki-01-SUMMARY.md` when done
</output>