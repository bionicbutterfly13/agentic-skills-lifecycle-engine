---
phase: quick-260922-lmm
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/asme/lifecycle.py
  - src/asme/workspace.py
  - src/asme/workflow.py
  - src/asme/cli.py
  - tests/test_lifecycle.py
  - tests/test_workspace.py
  - tests/test_workflow_candidate.py
  - tests/test_cli.py
autonomous: true
requirements: [PAR-03]

estimate:
  tokens: 55000
  raw_tokens: 55000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "A domain initialized with confirmation off accepts a strict validation win immediately, without ever entering NEEDS_VAL_CONFIRM."
    - "A domain initialized with confirmation off still rejects a non-strict validation result exactly as required mode does."
    - "A domain initialized with confirmation required (default, or legacy state missing the field) behaves exactly as before this change."
    - "The domain record and the state agree on confirmation_required; a mismatched record is refused, mirroring max_iterations."
    - "CLI --confirmation off round-trips: init records confirmation_required=false and status reports it."
  artifacts:
    - src/asme/lifecycle.py
    - src/asme/workspace.py
    - src/asme/workflow.py
    - src/asme/cli.py
  key_links:
    - "DomainState.confirmation_required -> transition() gate/validation branch -> accept-immediately path (consume val manifest, set best_score/active_snapshot_hash, _advance_iteration)"
    - "workspace.initialize(confirmation_required=...) -> domain record field -> recorded_domain() mismatch check"
    - "cli.py --confirmation {required,off} -> DomainWorkspace.initialize(confirmation_required=bool)"
    - "workflow.gate() impact outcome -> ACCEPTED with a single provisional score when off-mode accepts at validation"
---

<objective>
Implement PAR-03, the confirmation-run switch (ADR-0003): add a per-domain
`confirmation_required` flag so `paper_comparable` runs can accept a single
strict validation win (matching the paper's Algorithm 1), while production
runs keep the existing two-strict-win confirmation gate as the default.

Purpose: ADR-0003 requires the switch to be recorded per run for
reproducibility, and paper-comparable runs cannot be planned against the
paper's Algorithm 1 without this off-mode existing in the lifecycle.

Output: `DomainState.confirmation_required` field, off-mode accept-immediately
gate branch, workspace/CLI plumbing to set it at init, and tests pinning both
modes plus backward compatibility with existing state records.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@/Volumes/Asylum/dev/agentic-skills-lifecycle-engine/docs/adr/0003-confirmation-run-switch.md
@/Volumes/Asylum/dev/agentic-skills-lifecycle-engine/src/asme/lifecycle.py
@/Volumes/Asylum/dev/agentic-skills-lifecycle-engine/src/asme/workspace.py
@/Volumes/Asylum/dev/agentic-skills-lifecycle-engine/src/asme/workflow.py
@/Volumes/Asylum/dev/agentic-skills-lifecycle-engine/src/asme/cli.py
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Wire confirmation_required end-to-end through lifecycle.transition and DomainState</name>
  <files>src/asme/lifecycle.py, tests/test_lifecycle.py</files>
  <behavior>
    - Test: a `NEEDS_GATE` state with `gate_phase="validation"`, `confirmation_required=False`,
      and a strict win (candidate score > best_score) transitions directly to the
      accept-and-advance path: consumes the val manifest (by "gate-validation"), sets
      `best_score` to the provisional score, sets `active_snapshot_hash` to
      `candidate_snapshot_hash`, then runs `_advance_iteration` (matching the existing
      confirmation-phase accept branch's tail behavior at lines 312-323, but sourced from
      the validation-phase provisional score/manifest instead of the confirmation ones).
    - Test: the same state with `confirmation_required=False` and a non-strict result
      (candidate <= best_score) takes the existing rejection branch unchanged (reject,
      consume manifest by "gate-validation-reject", `_advance_iteration`).
    - Test: `confirmation_required=True` (the default) is unaffected — the existing
      `test_paper_strict_gate_requires_fresh_confirmation` and
      `test_confirmation_preserves_both_scores_and_promotes_their_minimum` tests must
      keep passing verbatim.
    - Test: `transition_matrix()` still enumerates one disposition per state/operation
      pair (default `confirmation_required=True` seed keeps `test_hf_a09_total_state_operation_cross_product`
      green unchanged).
  </behavior>
  <action>
    Add `confirmation_required: bool = True` to `DomainState` (per D-01 as encoded in the
    settled design), placed near `max_iterations` in the dataclass field order. In
    `transition()`, operation `"gate"`, `gate_phase == "validation"` branch (currently
    lines 287-301): keep the existing behavior when `current.confirmation_required` is
    true (route to `NEEDS_VAL_CONFIRM` unchanged). When `current.confirmation_required`
    is false and `strict_win` is true, instead: verify
    `current.current_manifest_phase == "val"` and `current.current_manifest_hash is not None`
    (same guard as today), consume that manifest by `"gate-validation"`, then produce the
    accepted result via `_advance_iteration(replace(consumed, best_score=candidate,
    active_snapshot_hash=current.candidate_snapshot_hash))` — mirroring the confirmation
    accept branch's shape but using the validation-phase candidate score (there is no
    `min()` because there is only one score in off mode) and `current.candidate_snapshot_hash`
    guarded by the same "accepted candidate has no snapshot hash" check the confirmation
    branch uses. The non-strict (rejection) branch at validation phase is untouched in
    both modes — off mode still runs the same `else` rejection path when `strict_win` is
    false. Do not touch the confirmation-phase (`gate_phase == "confirmation"`) branch;
    off-mode domains never reach `NEEDS_VAL_CONFIRM` so that branch stays dead code for
    them. Update `transition_matrix()`'s seed `DomainState` only if the existing
    `best_score=0.0` seed with default `confirmation_required=True` no longer exercises
    every operation identically — verify by running the matrix test, and if row counts
    differ, add no new state values (matrix iterates `LifecycleState`, not
    `confirmation_required`, so no matrix changes are expected).
  </action>
  <verify>
    <automated>PYTHONPATH=src python3 -m pytest tests/test_lifecycle.py -q</automated>
  </verify>
  <done>tests/test_lifecycle.py passes with new off-mode accept/reject tests added and all pre-existing lifecycle tests unchanged and green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Persist confirmation_required through DomainWorkspace.initialize and recorded_domain, expose via CLI</name>
  <files>src/asme/workspace.py, src/asme/cli.py, tests/test_workspace.py, tests/test_cli.py</files>
  <behavior>
    - Test: `DomainWorkspace.initialize(domain=..., max_iterations=1, confirmation_required=False)`
      produces a `DomainState` with `confirmation_required is False`, and the on-disk
      `domain.json` record's top-level `confirmation_required` key is also `False`.
    - Test: calling `initialize` without `confirmation_required` defaults to `True` (both
      in the returned state and the domain record), so existing callers/tests that omit
      the keyword are unaffected.
    - Test: `_state_from_json` accepts a state mapping that has every current field except
      `confirmation_required` (simulating a pre-existing `asme.state.v1` record on disk)
      and produces a `DomainState` with `confirmation_required=True`; it still rejects a
      mapping with any other field missing, and still rejects a mapping with an unknown
      extra field.
    - Test: `recorded_domain()` (via `_read_recorded_domain`) raises `ContractError` when
      the on-disk domain record's `confirmation_required` differs from the authoritative
      state's `confirmation_required`, mirroring the existing `max_iterations` mismatch
      check at line 318-319 of workspace.py.
    - Test (CLI): `asme init ... --confirmation off` initializes a domain whose `status`
      reports `confirmation_required: false`; omitting `--confirmation` (or passing
      `required`) reports `confirmation_required: true`.
  </behavior>
  <action>
    In `workspace.py`, add a `confirmation_required: bool = True` keyword parameter to
    `DomainWorkspace.initialize`. Pass it into the `DomainState(...)` construction
    alongside `max_iterations`. Add `"confirmation_required": confirmation_required` to
    the `domain_record` dict next to `"max_iterations": max_iterations`. Include it in
    the mutation `arguments` dict passed to `self._mutation_metadata` (alongside
    `max_iterations`) so it is captured in the transaction's recorded arguments. In
    `_read_recorded_domain`, add a check next to the existing `max_iterations` comparison
    (line 318-319): if `raw.get("confirmation_required", True) != state.confirmation_required`,
    raise `ContractError("recorded domain confirmation switch differs from authoritative state")`
    — the `raw.get(..., True)` default handles domain records written before this change.
    In `_state_from_json`, keep exact-field-set checking via `fields(DomainState)`
    (unchanged mechanism at line 564-567) but before that comparison, if
    `"confirmation_required"` is absent from `raw`, copy `raw` to a mutable dict and set
    `raw["confirmation_required"] = True` — this is the one legacy-compatibility
    exception; do not relax the check for any other field. In `cli.py`, add
    `initialize.add_argument("--confirmation", choices=("required", "off"), default="required")`
    next to the existing `--visibility` argument (same style, line ~95). In `_initialize`,
    pass `confirmation_required=(args.confirmation != "off")` to
    `_workspace(args).initialize(...)`.
  </action>
  <verify>
    <automated>PYTHONPATH=src python3 -m pytest tests/test_workspace.py tests/test_cli.py -q</automated>
  </verify>
  <done>Workspace initialize/record/reload round-trips confirmation_required in both modes; legacy state JSON missing the field loads as required; record/state mismatch is refused; CLI --confirmation off is visible in status output.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Confirm workflow.gate() impact recording is correct for off-mode accept, and add an end-to-end off-mode route to the candidate test</name>
  <files>src/asme/workflow.py, tests/test_workflow_candidate.py</files>
  <behavior>
    - Test: extend `test_changed_candidate_requires_two_wins_and_records_terminal_impact`
      (or add a sibling test using the same fixture setup) with an
      `"accept-confirmation-off"` route: initialize the workspace with
      `confirmation_required=False`, drive one `val` phase with a passing output, call
      `workflow.gate()` once, and assert: the returned state is `LifecycleState.DONE`,
      `active_snapshot_hash == candidate_snapshot_hash`, `best_score == 1.0`, and the
      recorded `impact/history.json` entry has `outcome == "Accepted"` with
      `scores == [1.0]` (a single-element list, not the two-score `[1.0, 1.0]` the
      required-mode accept route produces).
    - Test: a companion `"reject-confirmation-off"` route with a failing `val` output
      asserts `outcome == "Rejected"` with `scores == [0.0]`, matching the existing
      required-mode reject route's shape exactly.
  </behavior>
  <action>
    Read `gate()` in `workflow.py` (lines 1303-1452) and confirm the existing branch at
    line 1413 (`if state.gate_phase == "validation": outcome = ImpactOutcome.REJECTED;
    scores = (float(state.provisional_score),)`) and the `elif next_state.active_snapshot_hash
    == state.candidate_snapshot_hash` branch already produce the correct outcome/score
    shape for off-mode's single-score accept and reject with no code change required,
    because `gate()` dispatches on `next_state.state`/`next_state.active_snapshot_hash`
    rather than on `confirmation_required` directly. Verify this by tracing: for an
    off-mode strict win, `transition()` (Task 1) returns a state whose `state` is
    `LifecycleState.DONE` (via `_advance_iteration`) and whose `active_snapshot_hash`
    equals the candidate hash, so `next_state.state is LifecycleState.NEEDS_VAL_CONFIRM`
    is false, `state.gate_phase == "validation"` is true — meaning the current code
    would take the `outcome = ImpactOutcome.REJECTED` branch unconditionally for any
    non-NEEDS_VAL_CONFIRM validation-phase result, which is wrong for the new off-mode
    accept case. Fix this: change the condition at line 1413 from
    `if state.gate_phase == "validation":` to
    `if state.gate_phase == "validation" and next_state.active_snapshot_hash != state.candidate_snapshot_hash:`
    (reject), and add an `elif state.gate_phase == "validation":` branch before the
    existing confirmation-phase `elif` that sets
    `outcome = ImpactOutcome.ACCEPTED; scores = (float(state.provisional_score),)` for the
    off-mode accept case. Leave the confirmation-phase branches (`elif
    next_state.active_snapshot_hash == state.candidate_snapshot_hash` /
    `else: outcome = ImpactOutcome.REJECTED_AFTER_CONFIRM`) unchanged — they are only
    reached when `state.gate_phase == "confirmation"`, which off-mode domains never enter.
  </action>
  <verify>
    <automated>PYTHONPATH=src python3 -m pytest tests/test_workflow_candidate.py -q</automated>
  </verify>
  <done>Off-mode accept records a single-score Accepted impact entry and switches the active snapshot; off-mode reject records a single-score Rejected impact entry and leaves the active snapshot unchanged; all pre-existing required-mode routes in the same test remain green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| study manifest -> lifecycle | The `confirmation_required` switch is caller-supplied at `init` time and persisted; any code path that can flip it after init, or that can promote a candidate without evaluating the flag correctly, weakens the promotion guarantee ADR-0003 exists to protect. |
| on-disk domain record -> in-memory state | `domain.json` is read back on every `status()`/`apply()` call; a record that disagrees with the authoritative state must be refused, not silently trusted (mirrors the existing `max_iterations` integrity check). |
| legacy state JSON -> `_state_from_json` | Pre-existing `asme.state.v1` records on disk predate this field; the loader must not either crash on them or silently invent unsafe defaults. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-par03-01 | Tampering | `lifecycle.transition` gate/validation branch | high | mitigate | Off mode still requires `strict_win` (`candidate > best_score`); no code path accepts a non-strict result regardless of `confirmation_required`. Task 1 tests pin the non-strict-off-mode reject case explicitly. |
| T-par03-02 | Elevation of Privilege | `DomainWorkspace.initialize` / `recorded_domain` | high | mitigate | `confirmation_required` is set once at `init` and stored in the immutable domain record; `_read_recorded_domain` refuses any run where the record and state disagree, so a run cannot silently switch modes mid-lifecycle by editing on-disk state alone (state mutation still goes through the transaction engine's hash-chained history). |
| T-par03-03 | Repudiation | domain record / event history | medium | mitigate | `confirmation_required` is written into `domain.json` at init (per ADR-0003's "recorded per run for reproducibility") and every `gate` transition still appends to `state.history`, so the mode used for a given promotion decision remains auditable after the fact. |
| T-par03-04 | Tampering | `_state_from_json` legacy compatibility path | low | accept | Treating a missing `confirmation_required` key as `True` (the stricter, two-win mode) fails closed: an old record can only be interpreted as *more* conservative than it might otherwise be, never less. |
| T-par03-SC | Tampering | npm/pip/cargo installs | n/a | accept | No new package-manager installs are introduced by this plan; no packages to audit. |
</threat_model>

<verification>
Run the full suite after all three tasks:
`PYTHONPATH=src timeout 900 python3 -m pytest -q -p no:cacheprovider`
Record the final summary line (pass/fail counts) in the SUMMARY.md. All pre-existing
tests must remain green; only net-new off-mode tests and the two edited assertions in
tests/test_workspace.py / tests/test_cli.py / tests/test_workflow_candidate.py should
show as new or changed in the diff.
</verification>

<success_criteria>
- `DomainState.confirmation_required` exists, defaults to `True`, and is included in the
  frozen dataclass's digest/serialization.
- Off mode (`confirmation_required=False`) accepts a strict validation win immediately
  (no `NEEDS_VAL_CONFIRM` detour), setting `best_score`/`active_snapshot_hash` from the
  single validation score, and rejects a non-strict result exactly as required mode does.
- Required mode (default, and legacy state records missing the field) is behaviorally
  identical to pre-change behavior.
- `domain.json` records `confirmation_required`; a record/state mismatch is refused.
- `asme init --confirmation {required,off}` round-trips through `status`.
- `workflow.gate()` records `Accepted`/`Rejected` impact entries with a single score for
  off-mode outcomes, `Accepted`/`Rejected`/`RejectedAfterConfirm` with two scores for
  required-mode outcomes, unchanged from today.
- Full suite passes: `PYTHONPATH=src timeout 900 python3 -m pytest -q -p no:cacheprovider`.
</success_criteria>

<output>
Create `.planning/quick/260922-lmm-par-03-confirmation-run-switch/260922-lmm-SUMMARY.md` when done.
</output>
