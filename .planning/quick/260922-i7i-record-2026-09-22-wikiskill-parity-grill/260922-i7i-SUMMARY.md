---
phase: quick
plan: 260922-i7i
subsystem: docs
tags: [adr, requirements, wikiskill, glossary, wiki]

requires: []
provides:
  - Five dated ADRs (0001-0005) recording the 2026-09-22 WikiSkill parity grill's Q1-Q5 settled decisions
  - Repo-root CONTEXT.md glossary of eight WikiSkill parity terms
  - REQUIREMENTS.md WikiSkill Method Parity section with PAR-01..PAR-07
  - docs/wiki-draft/ (Home.md, Additions-beyond-the-paper.md) committed to the repo
affects: [wikiskill-implementation, phase-planning]

actuals:
  tokens: 2875
  tasks: 3
  commits: 1

tech-stack:
  added: []
  patterns:
    - "ADR format: title, Status line, Context/Decision/Consequences sections"

key-files:
  created:
    - docs/adr/0001-method-parity-target.md
    - docs/adr/0002-local-model-direct-adapter.md
    - docs/adr/0003-confirmation-run-switch.md
    - docs/adr/0004-detective-mode-proposer.md
    - docs/adr/0005-verbatim-paper-prompts.md
    - CONTEXT.md
    - docs/wiki-draft/Home.md
    - docs/wiki-draft/Additions-beyond-the-paper.md
  modified:
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Recorded Q1-Q5 grill decisions as five separate ADRs rather than one combined document, matching the plan's one-decision-per-file structure"
  - "PAR-07 states the corrected, non-stale blocker: repo is public with origin configured and wiki enabled; publication waits only on materializing the wiki git repository via one browser-created page, not on repo visibility"

requirements-completed: [PAR-01, PAR-02, PAR-03, PAR-04, PAR-05, PAR-06, PAR-07]

coverage:
  - id: D1
    description: "Five ADRs (0001-0005) record the grill's Q1-Q5 settled decisions, each sourced only from the ledger"
    requirement: "PAR-01"
    verification:
      - kind: other
        ref: "test -f docs/adr/000{1,2,3,4,5}-*.md && grep -l 'Status: accepted 2026-09-22' docs/adr/000*.md | wc -l"
        status: pass
    human_judgment: false
  - id: D2
    description: "CONTEXT.md glossary defines all eight grill terms without implementation detail"
    verification:
      - kind: other
        ref: "test -f CONTEXT.md && grep -c '^## ' CONTEXT.md"
        status: pass
    human_judgment: false
  - id: D3
    description: "REQUIREMENTS.md has a new WikiSkill Method Parity section with PAR-01..PAR-07 checkbox rows"
    requirement: "PAR-01,PAR-02,PAR-03,PAR-04,PAR-05,PAR-06,PAR-07"
    verification:
      - kind: other
        ref: "grep -c '^### WikiSkill Method Parity' .planning/REQUIREMENTS.md"
        status: pass
    human_judgment: false
  - id: D4
    description: "docs/wiki-draft/ (Home.md, Additions-beyond-the-paper.md) ships unchanged in the same commit"
    requirement: "PAR-07"
    verification:
      - kind: other
        ref: "diff against pre-existing main-repo copies; byte-identical"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-09-22
status: complete
---

# Quick Task 260922-i7i: Record 2026-09-22 WikiSkill Parity Grill Decisions

**Five ADRs, a repo-root glossary, and seven new requirement rows persisting the WikiSkill parity grill's settled decisions from session scratchpad into versioned docs.**

## Performance

- **Duration:** 15 min
- **Tasks:** 3
- **Files created:** 8
- **Files modified:** 1

## Accomplishments

- Recorded Q1-Q5 settled decisions (method parity target, local direct adapter, confirmation-run switch, detective-mode Proposer, verbatim paper prompts) as five dated, accepted ADRs under `docs/adr/`
- Created a repo-root `CONTEXT.md` glossary defining Method Parity, Empirical Parity, Confirmation Run, Paper-Comparable Run, Detective Mode, Ablation, Direct Adapter, and Study Manifest
- Added a new "WikiSkill Method Parity" section to `.planning/REQUIREMENTS.md` with PAR-01 through PAR-07, each row tracing to the ADR that recorded the decision
- Committed the already-drafted GitHub wiki pages (`docs/wiki-draft/Home.md`, `docs/wiki-draft/Additions-beyond-the-paper.md`) unchanged, alongside the new docs

## Task Commits

All three tasks (ADRs, CONTEXT.md/REQUIREMENTS.md, wiki-draft staging) were combined into a single commit per this plan's explicit "single commit" constraint:

1. **docs: record WikiSkill parity decisions** - see commit hash in final response

## Files Created/Modified

- `docs/adr/0001-method-parity-target.md` - Method parity target ADR
- `docs/adr/0002-local-model-direct-adapter.md` - Local-model direct adapter ADR
- `docs/adr/0003-confirmation-run-switch.md` - Confirmation-run switch ADR
- `docs/adr/0004-detective-mode-proposer.md` - Detective-mode Proposer ADR
- `docs/adr/0005-verbatim-paper-prompts.md` - Verbatim paper prompts ADR
- `CONTEXT.md` - Repo-root glossary of eight grill terms
- `.planning/REQUIREMENTS.md` - New WikiSkill Method Parity section, PAR-01..PAR-07
- `docs/wiki-draft/Home.md` - Wiki home page (unchanged, staged)
- `docs/wiki-draft/Additions-beyond-the-paper.md` - Wiki deviations page (unchanged, staged)

## Decisions Made

- One ADR per settled decision (Q1-Q5), not a combined document, matching the plan's `files_modified` list and per-decision traceability requirement.
- PAR-07's wording reflects the orchestrator's correction: the ledger's "no git remote" note is stale. The repository is public at https://github.com/bionicbutterfly13/agentic-skills-lifecycle-engine with origin configured and the wiki enabled. The only remaining blocker is that GitHub has not yet materialized the wiki git repository, which requires creating one page in the browser first. Publication itself remains a separate approval, per the ledger's Closed section.

## Deviations from Plan

None - plan executed exactly as written, with PAR-07's wording adjusted per the orchestrator's explicit correction (not a deviation from the plan's own instructions, since the plan's Task 2 action text for PAR-07 predates the correction and the correction is authoritative for this run).

## Issues Encountered

None.

## Known Stubs

None. All five ADRs, the glossary, and the requirement rows are complete prose sourced from the ledger; the wiki-draft pages are already-complete drafts pending publication (explicitly marked "not yet implemented" / "drafted... pending publication approval" in their own content, which is intentional per the ledger's Closed section, not a stub needing future resolution by this repo's code).

## User Setup Required

None - no external service configuration required by this task. Separately, wiki publication (creating the first page in the GitHub browser UI to materialize the wiki repository) remains a manual step for Dr. Mani, per the plan's explicit deferral and PAR-07's stated blocker.

## Next Phase Readiness

- PAR-01..PAR-07 are recorded but not yet phase-mapped in the Traceability table, per the plan's explicit instruction to leave them unmapped rather than invent a phase number.
- Wiki publication is the one remaining manual step, not part of this task's scope.

---
*Task: 260922-i7i*
*Completed: 2026-09-22*
