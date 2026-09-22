---
quick_id: 260922-lmm
requirements: [PAR-03]
status: complete
tags: [lifecycle, workspace, cli, workflow]
key-files:
  created:
    - tests/test_workspace.py
  modified:
    - src/asme/lifecycle.py
    - src/asme/workspace.py
    - src/asme/workflow.py
    - src/asme/cli.py
    - src/asme/impact.py
    - MANIFEST.in
    - tests/test_lifecycle.py
    - tests/test_cli.py
    - tests/test_workflow_candidate.py
metrics:
  duration: ~50 minutes
  completed: 2026-09-22
commit: 4fbe427
---

# Quick Task 260922-lmm: PAR-03 Confirmation-Run Switch Summary

Added `DomainState.confirmation_required` (ADR-0003) so `paper_comparable` runs can accept
a single strict validation win matching the paper's Algorithm 1, while production runs keep
the existing two-strict-win confirmation gate as the default.

## What Was Built

1. **`src/asme/lifecycle.py`** - Added `confirmation_required: bool = True` to `DomainState`
   (placed after `max_iterations`). In `transition()`'s `gate` operation, added a new branch:
   when `gate_phase == "validation"`, `strict_win` is true, and `confirmation_required` is
   false, the state consumes the val manifest by `"gate-validation"`, sets `best_score` and
   `active_snapshot_hash` from the single validation score/candidate hash, and runs
   `_advance_iteration` directly (no `NEEDS_VAL_CONFIRM` detour). The non-strict rejection
   branch is untouched in both modes.

2. **`src/asme/workspace.py`** - `DomainWorkspace.initialize()` accepts a
   `confirmation_required: bool = True` keyword, passed into `DomainState` construction, the
   `domain_record` dict, and the mutation `arguments`. `_read_recorded_domain` now checks
   `raw.get("confirmation_required", True) != state.confirmation_required` and raises
   `ContractError` on mismatch (mirrors the existing `max_iterations` check). `_state_from_json`
   treats a missing `confirmation_required` key as `True` before the exact-field-set check,
   so legacy `asme.state.v1` records load without modification.

3. **`src/asme/cli.py`** - Added `--confirmation {required,off}` (default `required`) to the
   `init` subcommand, next to `--visibility`. `_initialize` passes
   `confirmation_required=(args.confirmation != "off")` to `workspace.initialize()`.

4. **`src/asme/workflow.py`** - `EvolutionWorkflow.gate()`'s outcome dispatch previously took
   the `ImpactOutcome.REJECTED` branch unconditionally whenever `state.gate_phase ==
   "validation"`, which was correct before this change (validation-phase results never
   reached `DONE` directly) but wrong once off-mode can accept at validation. Changed the
   condition to `state.gate_phase == "validation" and next_state.active_snapshot_hash !=
   state.candidate_snapshot_hash` for the reject case, and added a new
   `elif state.gate_phase == "validation":` branch that records `ImpactOutcome.ACCEPTED`
   with a single-element `scores` tuple for the off-mode accept case.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `ImpactEntry.__post_init__` rejected a single-score Accepted outcome**

- **Found during:** Task 3, writing the off-mode accept test (RED phase surfaced
  `ContractError: non-accepted impact cannot change the active snapshot`, which traced back
  to `expected_scores` in `impact.py` hard-coding `ImpactOutcome.ACCEPTED: 2`).
- **Issue:** The plan's Task 3 action only described the `workflow.py` gate-dispatch fix. It
  did not anticipate that `ImpactEntry.__post_init__` unconditionally requires exactly 2
  scores for `ACCEPTED`, which makes it impossible to construct a single-score Accepted
  entry for the off-mode accept case regardless of the workflow.py fix.
- **Fix:** Changed `expected_scores` in `src/asme/impact.py` from a `{outcome: int}` mapping
  to `{outcome: tuple[int, ...]}`, allowing `ACCEPTED` to have either 1 or 2 scores. `REJECTED`,
  `REJECTED_AFTER_CONFIRM`, `NO_ACTION`, and `ABANDONED` counts are unchanged (each still maps
  to exactly one allowed count). No existing test pinned the old exact-count error message or
  count, so this widening does not change any prior passing/failing test.
- **Files modified:** `src/asme/impact.py`
- **Commit:** 4fbe427 (single commit for the whole task)

No other deviations. `src/asme/evolution_eval.py:315`'s `workspace.initialize(domain=...,
max_iterations=1, cartridge=...)` call was left unchanged per the plan checker's note; it
omits `confirmation_required`, so it defaults to `True` and preserves prior behavior. This is
covered by `test_state_from_json_accepts_legacy_record_missing_confirmation_required` in
`tests/test_workspace.py`, which asserts a domain initialized without the kwarg reports
`confirmation_required is True`.

## Test Coverage Added

- `tests/test_lifecycle.py`: 3 new tests (`test_confirmation_off_accepts_a_strict_validation_win_immediately`,
  `test_confirmation_off_rejects_a_non_strict_validation_result`,
  `test_confirmation_required_default_is_unaffected_by_the_switch`).
- `tests/test_workspace.py` (new file): 4 tests covering initialize round-trip in both modes,
  legacy `_state_from_json` compatibility (missing field defaults True; still rejects any
  other missing/extra field), and the record/state mismatch refusal.
- `tests/test_cli.py`: 1 new parametrized test (`test_cli_init_confirmation_switch_round_trips_through_status`,
  3 cases: no flag, `--confirmation required`, `--confirmation off`).
- `tests/test_workflow_candidate.py`: 2 new tests
  (`test_confirmation_off_accepts_a_single_strict_validation_win`,
  `test_confirmation_off_rejects_a_non_strict_validation_result`) using a factored-out
  `_build_candidate_workspace`/`_drive_to_candidate` helper pair (extracted from the existing
  parametrized fixture setup so the new tests share it without touching the pre-existing test).

All pre-existing tests in these four files remain green and unchanged in assertions.

## Verification

- `PYTHONPATH=src python3 -m pytest tests/test_lifecycle.py -q` — 13 passed.
- `PYTHONPATH=src python3 -m pytest tests/test_workspace.py tests/test_cli.py -q` — 11 passed.
- `PYTHONPATH=src python3 -m pytest tests/test_workflow_candidate.py -q` — 8 passed.
- `PYTHONPATH=src timeout 400 python3 -m pytest tests/test_workspace_hermes_adapter.py tests/test_distribution.py -p no:cacheprovider` — 92 passed.
- Full suite: `PYTHONPATH=src timeout 1200 python3 -m pytest -p no:cacheprovider` —
  **700 passed, 1 skipped, 0 failed** (baseline at 0e38c8c was 688 passed, 1 skipped; net +12
  new tests, 0 regressions).

## MANIFEST.in

Added `include tests/test_workspace.py` in sorted position (after `test_workflow_candidate.py`,
before `test_workspace_hermes_adapter.py`), required for `test_current_tree_is_community_scan_clean`
to keep passing with the new test file present.

## Self-Check: PASSED

- FOUND: src/asme/lifecycle.py, src/asme/workspace.py, src/asme/workflow.py, src/asme/cli.py,
  src/asme/impact.py, MANIFEST.in, tests/test_workspace.py, tests/test_lifecycle.py,
  tests/test_cli.py, tests/test_workflow_candidate.py
- FOUND: commit 4fbe427 in `git log --oneline`
