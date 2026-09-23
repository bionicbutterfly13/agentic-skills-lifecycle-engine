---
phase: 260923-cki-par-04-wire-maintainer-and-proposer-role
plan: 02
subsystem: ai
tags: [react-loop, tool-calling, skill-proposer, contract-validation, provenance]

requires:
  - "src/asme/model_client.py: stateless OpenAI-compatible ChatClient (plan 01)"
  - "src/asme/roles.py: build_role_prompt/PROPOSER_CONTRACT_WRAPPER (plan 01)"
provides:
  - "scripts/run_proposer.py: live Skill Proposer driver in both detective (default) and single-shot (ablation) modes, per ADR-0004"
  - "Driver-inserted context_hash pattern for Proposer-role driver scripts"
affects: [par-04-proposer-driver, distribution, wiki-draft]

actuals:
  tokens: 11193
  tasks: 3
  commits: 4
  plan_head_before: c6a2cb60790e3f0ce9670b7526cd69856c473b08

tech-stack:
  added: []
  patterns:
    - "Virtual read-only filesystem built once from a train-only context payload, exact-key-match only (no path resolution/traversal)"
    - "Driver-computed, model-untrusted context_hash: mechanically overwritten after finish()/response, never taken from the model's own claim"
    - "One-retry-then-raise refusal policy for under-provenanced tool-call finish() attempts"
    - "API key sourced from an env var (--api-key-env, default LIFECYCLE_MODEL_API_KEY), never a CLI value"

key-files:
  created:
    - scripts/run_proposer.py
    - tests/test_run_proposer.py
  modified:
    - scripts/run_maintainer.py
    - tests/test_run_maintainer.py
    - MANIFEST.in
    - .planning/REQUIREMENTS.md
    - .planning/wiki-draft/Additions-beyond-the-paper.md

key-decisions:
  - "Read the Maintainer and Proposer model-endpoint API key from an environment variable (--api-key-env, default LIFECYCLE_MODEL_API_KEY) instead of a --api-key CLI flag, per orchestrator addition #1: a CLI value leaks into the process list and shell history. Applied retroactively to plan 01's scripts/run_maintainer.py in its own scoped commit, plus scripts/run_proposer.py from its first commit."
  - "Detective mode's finish() retry budget is exactly 1 (FINISH_RETRY_BUDGET = 1): one re-prompt after an under-provenanced finish, then ContractError. Matches the plan's stated one-retry-then-raise design and mirrors the Maintainer driver's bounded-retry precedent from plan 01, though the two are unrelated mechanics (retry-on-validation-failure vs retry-on-provenance-failure)."
  - "The virtual filesystem is built directly from proposer_context()'s payload keys with no additional filtering layer, because asme.evidence.proposer_payload already raises ContractError if a non-train answer is ever passed into train_outcomes — validation/test-split content is structurally absent from the payload, not merely filtered out downstream. Documented explicitly in _build_virtual_filesystem's docstring and covered by a direct unit test."

requirements-completed: [PAR-04]

coverage:
  - id: D1
    description: "scripts/run_proposer.py --mode single-shot completes one proposer_context -> model call -> apply_proposal round trip with no retry on a malformed response"
    requirement: "PAR-04"
    verification:
      - kind: unit
        ref: "tests/test_run_proposer.py::test_single_shot_completes_in_one_call_and_applies_once"
        status: pass
      - kind: unit
        ref: "tests/test_run_proposer.py::test_single_shot_prompt_contains_full_context_payload_verbatim"
        status: pass
      - kind: unit
        ref: "tests/test_run_proposer.py::test_single_shot_malformed_response_raises_without_retry"
        status: pass
    human_judgment: false
  - id: D2
    description: "Detective mode's virtual filesystem exposes only wiki/*, traces/<train task_id>, and active-skill files; any other path (validation-split id, path traversal) is refused and logged, not served"
    requirement: "PAR-04"
    verification:
      - kind: unit
        ref: "tests/test_run_proposer.py::test_detective_reads_all_expected_paths_and_refuses_out_of_scope"
        status: pass
      - kind: unit
        ref: "tests/test_run_proposer.py::test_virtual_filesystem_never_serves_validation_or_test_split_reads"
        status: pass
    human_judgment: false
  - id: D3
    description: "finish() is refused once then raises ContractError when fewer than 4 distinct traces were read, or when a cited trace_id was never actually read"
    requirement: "PAR-04"
    verification:
      - kind: unit
        ref: "tests/test_run_proposer.py::test_detective_finish_with_fewer_than_four_traces_refused_once_then_raises"
        status: pass
      - kind: unit
        ref: "tests/test_run_proposer.py::test_detective_finish_citing_unread_trace_id_refused_then_raises"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every read_file attempt (successful or refused) is journaled with path, content sha256, and turn number, in call order, to a persisted reads log under the run directory"
    requirement: "PAR-04"
    verification:
      - kind: unit
        ref: "tests/test_run_proposer.py::test_detective_reads_log_has_path_hash_turn_in_call_order_including_refused"
        status: pass
    human_judgment: false
  - id: D5
    description: "context_hash forwarded to workflow.apply_proposal is always driver-computed from the exact proposer_context() bytes, never the model's own value"
    requirement: "PAR-04"
    verification:
      - kind: unit
        ref: "tests/test_run_proposer.py::test_detective_context_hash_is_always_driver_computed"
        status: pass
    human_judgment: false
  - id: D6
    description: "The Maintainer and Proposer API key is read from an environment variable, not a CLI flag"
    verification:
      - kind: unit
        ref: "tests/test_run_maintainer.py::test_api_key_is_read_from_environment_not_a_cli_flag"
        status: pass
    human_judgment: false

duration: 60min
completed: 2026-09-23
status: complete
---

# Phase 260923-cki-par-04-wire-maintainer-and-proposer-role Plan 02: Skill Proposer Driver (Detective + Single-Shot) Summary

**Built scripts/run_proposer.py in both of ADR-0004's modes: detective (default, multi-turn ReAct loop with a journaled, read-only virtual filesystem and a >=4-trace provenance gate) and single-shot (the local ablation), closing out PAR-04 and moving the Maintainer/Proposer API key off the CLI onto an environment variable.**

## Performance

- **Duration:** ~60 min
- **Completed:** 2026-09-23T14:22:41Z (approx)
- **Tasks:** 3/3
- **Commits:** 4 (measured via `git rev-list --count`, ledger base `c6a2cb6`)

## Accomplishments

- `scripts/run_proposer.py` drives the Skill Proposer role end to end in both modes:
  - `--mode single-shot`: one `proposer_context() -> model call -> apply_proposal` round trip, no retry on a malformed response (the ablation baseline).
  - `--mode detective` (default): a multi-turn ReAct loop (`--max-turns`, default 20) with `read_file`/`finish` tool calls against a virtual, read-only filesystem assembled once from `proposer_context()`'s train-only payload.
- Detective mode enforces the provenance gate exactly as ADR-0004 states it: `finish()` is refused once (a re-prompt naming the specific failure) and raises `ContractError` on a second insufficient attempt if fewer than 4 distinct traces were read, or if the proposal cites a trace_id never actually read via `read_file`.
- Every `read_file` call, successful or refused, is journaled to `{iteration}/proposer-reads-log.json` (path, sha256 of the exact content or refusal sentinel, turn number, refused flag), in call order.
- `context_hash` is always driver-computed (`sha256_bytes(context_bytes)`) and mechanically overwrites whatever the model supplied in `finish()`, labeled with the exact comment the plan specified (`# Driver-inserted: mechanical binding the model cannot compute.`).
- Both `scripts/run_maintainer.py` (plan 01) and `scripts/run_proposer.py` now read their model-endpoint API key from an environment variable (`--api-key-env`, default `LIFECYCLE_MODEL_API_KEY`) instead of a `--api-key` CLI value, per orchestrator addition #1.
- `PAR-04` is `[x]` in `.planning/REQUIREMENTS.md`; `.planning/wiki-draft/Additions-beyond-the-paper.md`'s "Detective-mode flag" entry now states it is implemented, and two new local-mechanics entries document the Maintainer's retry policy and the Proposer's driver-inserted `context_hash`.
- 16 new tests (10 in `tests/test_run_proposer.py`, 1 new env-var test in `tests/test_run_maintainer.py`, plus the untouched 3 from plan 01's file that still pass, and 2 already-passing files re-verified). Full suite: 730 passed, 1 skipped, exit 0 (up from plan 01's 719 passed, 1 skipped baseline).

## Task Commits

1. **Env-var API key fix (orchestrator addition #1, applied ahead of Task 1 to plan 01's script)** - `de58b60` (fix)
2. **Task 1: Single-shot Skill Proposer path end to end** - `6db95cc` (feat)
3. **Task 2: Detective-mode ReAct loop, virtual filesystem, read journal, provenance refusal** - `57b6c53` (test)
4. **Task 3: Full-suite verification, REQUIREMENTS.md and wiki-draft closeout** - `233ba0b` (docs)

## Files Created/Modified

- `scripts/run_proposer.py` - Live Skill Proposer driver: CLI (`--domain`, `--domain-root`, `--base-url`, `--model`, `--provider`, `--api-key-env`, `--mode`, `--max-turns`), shared workspace/workflow/client setup, `run_single_shot`, `run_detective`, the virtual-filesystem builder, tool schemas, and the reads-log persistence helper.
- `tests/test_run_proposer.py` - 10 tests: 3 single-shot (one-call completion, verbatim-context-in-prompt, malformed-response-no-retry) and 7 detective-mode (filesystem boundary + refusal, under-read finish refusal, unread-trace-id refusal, reads-log shape/order, driver-computed context_hash, virtual-filesystem train-only construction, turn-cap exhaustion).
- `scripts/run_maintainer.py` - `--api-key` replaced with `--api-key-env` (default `LIFECYCLE_MODEL_API_KEY`), read via `os.environ.get`.
- `tests/test_run_maintainer.py` - Added `test_api_key_is_read_from_environment_not_a_cli_flag`, asserting via source inspection that no `--api-key` value flag exists and that the env var actually supplies the key.
- `MANIFEST.in` - Added `scripts/run_proposer.py` and `tests/test_run_proposer.py` in sorted position.
- `.planning/REQUIREMENTS.md` - `PAR-04` ticked `[x]`.
- `.planning/wiki-draft/Additions-beyond-the-paper.md` - "Detective-mode flag" entry updated from "decided, not yet implemented" to implemented with evidence; two new entries added ("Maintainer driver's retry policy", "Driver-inserted context_hash (Proposer only)").

## Decisions Made

- API key sourced from an environment variable rather than a CLI flag for both driver scripts, per orchestrator addition #1 — a `--api-key` value is visible in `ps` output and shell history. `--api-key-env` (default `LIFECYCLE_MODEL_API_KEY`) is the flag; the value itself is never a CLI argument. Retrofitted onto plan 01's `run_maintainer.py` in a dedicated commit before Task 1's own work, since the same threat applies identically to both scripts.
- Detective mode's `finish()` retry budget is `FINISH_RETRY_BUDGET = 1`, matching the plan's explicit "refused once, then raises on a second insufficient attempt" design.
- No additional filtering layer was added to `_build_virtual_filesystem` beyond reading the keys `proposer_context()`'s payload already contains, because `asme.evidence.proposer_payload` already raises `ContractError` if any non-train answer were ever passed into `train_outcomes` — the train-only guarantee is structural, not a downstream filter. This is documented in the function's docstring with an explicit reference to the upstream check, and backed by a direct unit test (`test_virtual_filesystem_never_serves_validation_or_test_split_reads`) that also exercises `answers.jsonl`/`domain.json`/traversal paths for defense in depth.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added MANIFEST.in entries for scripts/run_proposer.py and tests/test_run_proposer.py**
- **Found during:** Task 1 verification (`pytest tests/test_distribution.py`)
- **Issue:** `test_distribution_complete_independent_families` failed because the two new files were unclassified in `MANIFEST.in`, mirroring the same gap plan 01 hit.
- **Fix:** Added `include` lines for both files in their correct alphabetical positions.
- **Files modified:** `MANIFEST.in`
- **Verification:** `tests/test_distribution.py` passes in full (92 tests).
- **Committed in:** `6db95cc` (Task 1)

**2. [Rule 2 - Missing critical functionality] Applied the env-var API key fix to plan 01's scripts/run_maintainer.py**
- **Found during:** Pre-Task-1 review of orchestrator addition #1
- **Issue:** Orchestrator addition #1 explicitly named both `run_maintainer.py` (already shipped in plan 01) and the new `run_proposer.py`. Leaving `run_maintainer.py`'s `--api-key` flag in place would leave the process-list/shell-history exposure live for the Maintainer driver even after this plan closed out the Proposer driver.
- **Fix:** Replaced `--api-key` with `--api-key-env` (default `LIFECYCLE_MODEL_API_KEY`) in `scripts/run_maintainer.py`, read via `os.environ.get`; added a source-inspection test proving no `--api-key` value flag remains and that the env var supplies the key.
- **Files modified:** `scripts/run_maintainer.py`, `tests/test_run_maintainer.py`
- **Verification:** `tests/test_run_maintainer.py` (4/4 pass) and `tests/test_distribution.py` (83/83 pass at that point).
- **Committed in:** `de58b60` (separate scoped commit, ahead of Task 1)

**3. [Rule 2 - Missing critical functionality] Added the explicit `# Driver-inserted:` comment the plan named**
- **Found during:** Task 3 wiki-draft closeout, cross-checking the plan's exact wording against the shipped code
- **Issue:** The plan's Task 2 action explicitly specified the comment text `# Driver-inserted: mechanical binding the model cannot compute.` above the `context_hash` overwrite line; the initial Task 2 implementation omitted it.
- **Fix:** Added the comment verbatim immediately above `proposal["context_hash"] = sha256_bytes(context_bytes)`.
- **Files modified:** `scripts/run_proposer.py`
- **Verification:** Re-ran `tests/test_run_proposer.py` (10/10 pass) and the full suite (730 passed, 1 skipped, exit 0) after the change.
- **Committed in:** `233ba0b` (Task 3)

---

**Total deviations:** 3 auto-fixed (1 blocking/Rule 3, 2 missing-functionality/Rule 2)
**Impact on plan:** All three were necessary to satisfy the plan's own stated verification and the orchestrator's explicit additions. No scope creep beyond what the plan and orchestrator additions already required.

## Orchestrator Additions: How Each Was Handled

1. **Secret handling (env var for API key):** Implemented in both `scripts/run_maintainer.py` and `scripts/run_proposer.py` via `--api-key-env` (default `LIFECYCLE_MODEL_API_KEY`), read with `os.environ.get`. No `--api-key` value flag exists in either script. Test: `tests/test_run_maintainer.py::test_api_key_is_read_from_environment_not_a_cli_flag` (inspects `main()`'s source to prove the flag is absent, and confirms the env var is what actually supplies the key). The key is never logged or printed by either script.
2. **Held-out isolation (T-260923-08):** The detective filesystem (`_build_virtual_filesystem`) is built exclusively from `proposer_context()`'s payload (`train_outcomes`, `wiki_pages`, `impact_history`, `active_skill`), which is itself constrained to train-split-only content by `asme.evidence.proposer_payload`'s own `ContractError` guard. Test: `tests/test_run_proposer.py::test_virtual_filesystem_never_serves_validation_or_test_split_reads` directly asserts that reads for `traces/validation-*`, `traces/test-*`, `answers.jsonl`, `domain.json`, and a traversal path are all refused (via `_resolve_read`), and that the only `traces/*` keys present are exactly `available_trace_ids`. A second, end-to-end test (`test_detective_reads_all_expected_paths_and_refuses_out_of_scope`) exercises the same boundary through the full ReAct loop against a fake transport.
3. **Additions-beyond-the-paper.md documentation:** Updated in Task 3. The "Detective-mode flag" entry's status changed from "not yet implemented" to implemented, naming `scripts/run_proposer.py`/`tests/test_run_proposer.py` as evidence and restating the >=4-trace and one-retry-then-refuse policies verbatim per ADR-0004. Two new subsections were added: "Maintainer driver's retry policy" (labeled local, non-paper) and "Driver-inserted context_hash (Proposer only)" (labeled local, non-paper, explicitly noting the Maintainer contract has no `context_hash` field so the two mechanics are not conflated).

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None — no external service configuration required. `scripts/run_proposer.py` requires a live OpenAI-compatible endpoint (and, for detective mode, tool-calling support) to run for real; both modes are fully exercised offline against a fake transport in `tests/test_run_proposer.py`.

## Next Phase Readiness

- PAR-04 is closed. Both Skill Proposer modes exist with passing offline tests, and the wiki-draft accurately reflects the shipped state.
- `scripts/run_proposer.py`'s detective mode requires a tool-calling-capable OpenAI-compatible endpoint to exercise live (not yet validated against a real model server in this plan; only against the fake transport). A future phase that runs an actual end-to-end LiveMath study should confirm the local Ollama/qwen setup actually supports OpenAI-style function calling in the `tools=` request body before relying on detective mode for real.
- No blockers identified for downstream phases.

---
*Phase: 260923-cki-par-04-wire-maintainer-and-proposer-role*
*Completed: 2026-09-23*

## Self-Check: PASSED

Both created files confirmed present on disk (`scripts/run_proposer.py`,
`tests/test_run_proposer.py`). All four task commits (`de58b60`, `6db95cc`,
`57b6c53`, `233ba0b`) confirmed present in `git log --oneline --all`.
