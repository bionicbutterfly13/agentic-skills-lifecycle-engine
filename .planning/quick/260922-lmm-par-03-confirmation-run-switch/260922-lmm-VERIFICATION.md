---
phase: quick-260922-lmm-par-03-confirmation-run-switch
verified: 2026-09-22T20:58:38Z
status: gaps_found
score: 6/7 truths verified (1 confirmed gap at the ImpactEntry data-model layer)
covered_files:
  - .planning/quick/260922-lmm-par-03-confirmation-run-switch/260922-lmm-PLAN.md
  - .planning/quick/260922-lmm-par-03-confirmation-run-switch/260922-lmm-SUMMARY.md
  - docs/adr/0003-confirmation-run-switch.md
  - src/asme/lifecycle.py
  - src/asme/workspace.py
  - src/asme/workflow.py
  - src/asme/cli.py
  - src/asme/impact.py
  - MANIFEST.in
  - tests/test_lifecycle.py
  - tests/test_workspace.py
  - tests/test_cli.py
  - tests/test_workflow_candidate.py
gaps:
  - truth: "ImpactEntry score-count validity is cross-checked against the owning domain's confirmation_required mode"
    status: failed
    reason: >
      ImpactEntry.__post_init__ (src/asme/impact.py:36-42) validates score count purely
      against ImpactOutcome, accepting ACCEPTED with either 1 or 2 scores unconditionally.
      Neither ImpactEntry, create_impact, nor _read_impact_history (src/asme/workflow.py:1890-1916)
      receive or check the domain's confirmation_required value. The invariant "a 1-score
      ACCEPTED entry is only legitimate for an off-mode domain" is enforced today only
      incidentally, by workflow.py's gate() control flow being the sole production writer
      and its two write branches being mutually exclusive by construction (lifecycle.transition()
      only reaches the 1-score accept path when confirmation_required is False). Nothing
      stops a hand-edited, replayed, or future-code-path-written impact/history.json from
      recording a 1-score ACCEPTED entry for a domain whose recorded confirmation_required
      is True, and _read_impact_history would accept it as fully valid on read.
    artifacts:
      - path: "src/asme/impact.py"
        issue: "ImpactEntry.__post_init__ has no domain-mode parameter or cross-check; confirmed by direct construction test below"
      - path: "src/asme/workflow.py"
        issue: "_read_impact_history (line 1890) reconstructs ImpactEntry from raw JSON with no comparison against DomainState.confirmation_required"
    missing:
      - "A cross-check (either in ImpactEntry construction via an explicit confirmation_required parameter, or in _read_impact_history via a lookup against the domain's recorded confirmation_required) that refuses a 1-score ACCEPTED entry for a domain whose confirmation_required is True, and/or a 2-score ACCEPTED entry for a domain whose confirmation_required is False."
---

# Quick Task 260922-lmm: PAR-03 Confirmation-Run Switch Verification Report

**Task Goal:** Add a per-domain `confirmation_required` flag (ADR-0003) so `paper_comparable`
runs can accept a single strict validation win, while production runs keep the existing
two-strict-win confirmation gate as the default.

**Verified:** 2026-09-22T20:58:38Z
**Status:** gaps_found
**Worktree:** `.claude/worktrees/agent-ac89fbc43412df306` (commits 4fbe427 feat, 9f66855 docs, on 0e38c8c)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Off mode: strict validation win promotes directly (best_score, active snapshot, val manifest consumed, iteration advanced); non-strict rejected; equal scores rejected | VERIFIED | `src/asme/lifecycle.py:288-308` (accept branch, gated on `strict_win and not current.confirmation_required`), `:346-361` (shared reject branch, `strict_win = candidate > current.best_score` at line 287 means equal scores take the `else` reject path). Test: `tests/test_lifecycle.py:116-163` — `test_confirmation_off_accepts_a_strict_validation_win_immediately` asserts `state is DONE`, `active_snapshot_hash == candidate hash`, `best_score == 0.7`, `consumed_manifests == [{"by": "gate-validation"}]`; `test_confirmation_off_rejects_a_non_strict_validation_result` uses `provisional_score=0.5 == best_score=0.5` (the equal-score case) and asserts rejection. Full-suite run confirms both pass (700 passed, 0 failed). |
| 2 | Required mode (default): behavior byte-for-byte unchanged, still routes a strict win to NEEDS_VAL_CONFIRM | VERIFIED | `src/asme/lifecycle.py:309-323` (unchanged branch, reached when `confirmation_required` is True). `tests/test_lifecycle.py:53-114` — pre-existing `test_paper_strict_gate_requires_fresh_confirmation` and `test_confirmation_preserves_both_scores_and_promotes_their_minimum` are present verbatim and pass; `test_confirmation_required_default_is_unaffected_by_the_switch` (line 164) asserts default `confirmation_required is True`. |
| 3 | Legacy state JSON without confirmation_required loads as True; unknown extra fields still refused | VERIFIED | `src/asme/workspace.py:571-578` — backfill (`raw["confirmation_required"] = True`) happens before the `set(raw) != expected` exact-field-set check, so the check still runs and still rejects any other missing/extra field. Test: `tests/test_workspace.py:46-64` — `test_state_from_json_accepts_legacy_record_missing_confirmation_required` deletes the field and confirms `legacy.confirmation_required is True`, then separately adds an `unexpected_extra_field` and confirms `ContractError` is raised. |
| 4 | Domain record and state must agree; mismatch refused. CLI `init --confirmation off` round-trips | VERIFIED | `src/asme/workspace.py:326` — `_read_recorded_domain` raises `ContractError("recorded domain confirmation switch differs from authoritative state")` on mismatch, mirroring the `max_iterations` check at line 324. Test: `tests/test_workspace.py:68-77` — `test_recorded_domain_mismatch_on_confirmation_required_is_refused` flips the on-disk record after init and confirms the raise (`match="confirmation switch"`). CLI: `src/asme/cli.py:98` adds `--confirmation {required,off}` (default `required`); `:374` passes `confirmation_required=(args.confirmation != "off")`. Test: `tests/test_cli.py:153-185`, parametrized over `(None, "required", "off")`, drives `init` then `status` and asserts the reported value round-trips for all three cases. |
| 5 | ImpactEntry score-count validity is cross-checked against the domain's confirmation_required mode | FAILED | See Gaps section below — CONFIRMED GAP. |
| 6 | Full test suite passes with 0 regressions | VERIFIED | `PYTHONPATH=src timeout 1200 python3 -m pytest -p no:cacheprovider` run directly in this verification session (not taken from SUMMARY.md): **700 passed, 1 skipped, 1 warning in 408.77s, exit code 0**. Matches SUMMARY.md's claimed baseline delta (688 passed at 0e38c8c -> 700 passed here, net +12 new tests, 0 failures). The one warning is a pre-existing `zipfile` duplicate-name UserWarning in `test_distribution.py`, unrelated to this change. |
| 7 | No em dashes introduced in added prose/comments; adapters/ imports only asme.contract | VERIFIED | `git diff main -- src/ tests/ docs/ \| grep "^+" \| grep "—"` returned no matches (em dashes appear only in the pre-existing `260922-lmm-SUMMARY.md` verification bullet list and an unrelated pre-existing STATE.md row, neither of which is source/test/doc prose covered by this check). `adapters/direct/__init__.py` imports only `from asme.contract import (...)` — confirmed via grep; `git diff main --stat -- adapters/ src/asme/adapter.py` shows this phase touched neither file, so the import boundary is unaffected (regression-clean). |

**Score:** 6/7 truths verified (1 confirmed gap)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/asme/lifecycle.py` | `DomainState.confirmation_required` field + off-mode gate branch | VERIFIED | Field at line 50; accept branch lines 288-308; wired into `transition()`'s `gate` operation |
| `src/asme/workspace.py` | initialize/record/reload plumbing | VERIFIED | Lines 104, 122, 130, 139 (write path), 326 (mismatch check), 573-574 (legacy load) |
| `src/asme/workflow.py` | gate() outcome dispatch fix | VERIFIED | Lines 1413-1421, cleanly separates off-mode accept/reject from confirmation-phase branches |
| `src/asme/cli.py` | `--confirmation {required,off}` | VERIFIED | Line 98 (argparse), line 374 (wiring) |
| `src/asme/impact.py` | (not a declared must-have artifact, but modified as an auto-fixed deviation) | PARTIAL | Widened score-count validation to allow ACCEPTED with 1 or 2, but added no mode-awareness — see gap |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `DomainState.confirmation_required` | `transition()` gate/validation branch | `not current.confirmation_required` guard at lifecycle.py:291 | WIRED | Confirmed by direct read and passing tests |
| `workspace.initialize(confirmation_required=...)` | domain record field | `domain_record["confirmation_required"]` at workspace.py:130 | WIRED | Confirmed by `test_initialize_records_confirmation_required_false` |
| `cli.py --confirmation` | `DomainWorkspace.initialize(confirmation_required=bool)` | cli.py:374 | WIRED | Confirmed by parametrized CLI round-trip test |
| `workflow.gate()` impact outcome | `ImpactEntry` construction | `create_impact(...)` at workflow.py:1434 | WIRED but UNGUARDED | The write path is correct (single writer, mutually exclusive branches), but no explicit contract enforces the score-count/mode relationship at the `ImpactEntry`/read layer — see gap |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| ImpactEntry accepts a 1-score ACCEPTED entry with no domain-mode awareness | `PYTHONPATH=src python3 -c "from asme.impact import create_impact, ImpactOutcome; create_impact(domain_id='some-required-mode-domain', iteration=1, outcome=ImpactOutcome.ACCEPTED, active_before='a'*64, candidate_snapshot='b'*64, active_after='b'*64, scores=[1.0], unified_diff='diff')"` | Constructed successfully: `scores=(1.0,)`, no error, no domain lookup performed | CONFIRMS GAP |
| Adapters import boundary unaffected | `grep -n "^from asme" adapters/direct/__init__.py` + `git diff main --stat -- adapters/` | Only imports `asme.contract`; diff empty (untouched by this task) | PASS |
| Em dash scan on added code/test/doc prose | `git diff main -- src/ tests/ docs/ \| grep "^+" \| grep "—"` | No matches | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| PAR-03 | 260922-lmm-PLAN.md | Confirmation-run switch per ADR-0003 | PARTIALLY SATISFIED | Core switch, gate branching, persistence, CLI, and workflow dispatch are all correctly implemented and tested. The `ImpactEntry` data-model layer, touched as an auto-fixed deviation to make the off-mode accept case constructible at all, was widened without restoring an equivalent invariant at that layer. |

### Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers in any touched file.

### Gaps Summary

Five of the six plan-defined must-have truths, plus the test-suite and em-dash/adapter-boundary
checks, are solidly verified with direct evidence (not just SUMMARY.md claims) — the lifecycle
gate branching, workspace/CLI persistence, legacy-compatibility loading, and record/state mismatch
refusal are all implemented exactly as designed and covered by real tests I inspected and traced
line-by-line.

The one confirmed gap is at the `ImpactEntry` data-model layer (`src/asme/impact.py`), which this
task's Task 3 modified as an unplanned "auto-fixed" deviation (per SUMMARY.md's own account) to
unblock construction of a 1-score `ACCEPTED` entry. That fix widened `expected_scores` for
`ImpactOutcome.ACCEPTED` from a fixed `2` to `(1, 2)` with no accompanying check that ties the
allowed count back to the owning domain's `confirmation_required` value. Today this is not
exploitable through the only production writer (`workflow.gate()`), because `lifecycle.transition()`
guarantees the two write branches are mutually exclusive per domain mode. But the invariant ADR-0003
implicitly requires — "a required-mode domain's impact history never contains a 1-score ACCEPTED
entry" — is not actually enforced by any code that reads or validates `ImpactEntry`/`impact/history.json`
directly. A hand-edited history file, a replayed/merged history from a different domain, or any future
second writer would silently pass validation. This is a real, demonstrated gap (see the direct
construction spot-check above), not a hypothetical concern.

**Smallest fix:** Thread the domain's `confirmation_required` value into the one call site that
matters — `_read_impact_history` in `workflow.py` (or, more centrally, into `EvolutionWorkflow.gate()`'s
`create_impact` call and a corresponding read-time check) — and assert that a 1-score `ACCEPTED` entry
only appears for a domain whose recorded `confirmation_required` is `False` (and a 2-score `ACCEPTED`
entry only for `True`). This does not require changing `ImpactEntry`'s frozen-dataclass shape; it can
be a `ContractError` raised in `_read_impact_history` (which already has access to
`self.workspace.status()` in every calling context in `workflow.py`) or in a small wrapper function
called after `create_impact`/on every `_read_impact_history` load.

---

_Verified: 2026-09-22T20:58:38Z_
_Verifier: Claude (gsd-verifier)_

## Gap closure (orchestrator, 2026-09-22)

Gap 5 closed in commit 5992e82. `_read_impact_history` now takes the domain's
`confirmation_required` and refuses an ACCEPTED entry whose score count does
not match the mode (two when required, one when off). All five callers pass the
loaded state's value. Four parametrized cases in
`tests/test_workflow_candidate.py` cover both mismatches and both matches.
Full suite after the fix: 704 passed, 1 skipped, 0 failed, pytest exit 0.

Final status: PASSED (7/7).
