# Roadmap: Agentic Skills Lifecycle Engine

## Overview

Lifecycle moves from a public, source-grounded project contract to immutable core
identities, deterministic study control, security admission, evidence-backed skill
creation, a Daedalus adapter, and one controlled synthetic study. Only after the study
and confirmation gates work does v1 package the engine and demonstrate a second host
adapter.

## Phases

- [ ] **Phase 1: Public Project Contract** - Establish the canonical identity, evidence
  boundaries, source lineage, introduction, and first research journal.
- [ ] **Phase 2: Canonical Schemas and Identity** - Define validated records and stable
  content identities for every lifecycle artifact.
- [ ] **Phase 3: Event Ledger and Study Controller** - Record immutable transitions and
  enforce finite deterministic study execution.
- [ ] **Phase 4: Security Admission** - Enforce default-deny capabilities, separate
  admission gates, and fail-closed decisions.
- [ ] **Phase 5: Evidence, Candidates, and State** - Build the evidence-backed candidate
  path and bounded `SKILL.state` mutation contract.
- [ ] **Phase 6: ASME Salvage** - Audit and migrate only verified reusable assets without
  authorizing deletion.
- [ ] **Phase 7: Daedalus Host Adapter** - Connect Daedalus through the public host
  contract while preserving Lifecycle semantics.
- [ ] **Phase 8: Synthetic k-NN Study Harness** - Build the frozen paired-arm fixture and
  isolated role environments.
- [ ] **Phase 9: Evaluation and Lifecycle Decisions** - Apply correctness-first gates,
  scoped promotion, rollback, and independent confirmation.
- [ ] **Phase 10: Open-Source Distribution** - Package Lifecycle independently and prove
  the adapter contract with a second host.

## Phase Details

### Phase 1: Public Project Contract
**Goal:** Establish one canonical public account of what Lifecycle is, what research
supports it, and what has not been built.
**Mode:** mvp
**Depends on:** Nothing
**Requirements:** PROJ-01, PROJ-02, PROJ-03, DOCS-01, DOCS-02
**Success Criteria** (what must be TRUE):
  1. A reader can identify the full name, short name, ownership boundary, and Daedalus's
   role from canonical repository files.
  2. A reader can trace architectural claims to the reviewed primary-source packet.
  3. The project introduction and dated journal distinguish research and design from
   implementation, run evidence, and release status.
**Plans:** 2 plans

Plans:
- [ ] 01-01: Establish repository contract, provenance map, and contribution boundary.
- [ ] 01-02: Draft and verify the public introduction and first Lifecycle journal.

### Phase 2: Canonical Schemas and Identity
**Goal:** Make every lifecycle artifact machine-validatable and content-addressed.
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** CORE-02, CORE-03, EVID-03
**Success Criteria** (what must be TRUE):
  1. Invalid source, evidence, skill, permission, state, study, event, and decision records
   are rejected with explicit errors.
  2. Identical canonical bytes produce the same digest and any byte change produces a new
   identity that invalidates prior approval.
  3. A study manifest resolves the exact Lifecycle version and content digest for each
   arm.
**Plans:** 2 plans

Plans:
- [ ] 02-01: Define schemas, canonical serialization, and validation contracts.
- [ ] 02-02: Implement content identity, version pins, and approval invalidation tests.

### Phase 3: Event Ledger and Study Controller
**Goal:** Provide deterministic orchestration and an immutable record of every study
transition.
**Mode:** mvp
**Depends on:** Phase 2
**Requirements:** EVID-02, STUD-06
**Success Criteria** (what must be TRUE):
  1. Every lifecycle transition is written to an append-only event ledger before journal
   projection.
  2. The controller enforces a declared iteration cap and stops on success, futility, or
   safety failure.
  3. Replaying the same event sequence reconstructs the same study state or fails with an
   explicit integrity error.
**Plans:** 2 plans

Plans:
- [ ] 03-01: Implement event schemas, append-only storage, and deterministic replay.
- [ ] 03-02: Implement the finite study state machine and stopping rules.

### Phase 4: Security Admission
**Goal:** Prevent undeclared effects and unresolved risk before candidate execution or
promotion.
**Mode:** mvp
**Depends on:** Phase 3
**Requirements:** SECU-01, SECU-02, SECU-03, SECU-04
**Success Criteria** (what must be TRUE):
  1. Roles and candidates receive no capability unless the study manifest declares it.
  2. Retrieval, trust, license, policy, compatibility, and runtime admission return
   separate auditable verdicts.
  3. Missing or uncertain evidence fails closed before mutation or execution.
  4. The first-study package validator rejects executable payloads and undeclared effects.
**Plans:** 2 plans

Plans:
- [ ] 04-01: Implement manifests, capability ceilings, and separate admission gates.
- [ ] 04-02: Build adversarial fixtures and fail-closed security contract tests.

### Phase 5: Evidence, Candidates, and State
**Goal:** Turn bounded training evidence into one immutable candidate with safe,
validated execution state.
**Mode:** mvp
**Depends on:** Phase 4
**Requirements:** EVID-01, EVID-04, LIFE-01, LIFE-03, STAT-01, STAT-02, STAT-03
**Success Criteria** (what must be TRUE):
  1. Maintainers can add only source-grounded claims with provenance and evidence quality.
  2. Candidate creation can inspect scored training traces but cannot access validation or
   confirmation evidence.
  3. Weak or contradictory evidence produces abstention rather than a candidate promotion.
  4. State patches are bounded, validated, auditable, and reset for every paired arm and
   fresh trial.
**Plans:** 3 plans

Plans:
- [ ] 05-01: Implement the evidence-backed knowledge and claim store.
- [ ] 05-02: Implement immutable candidate construction and abstention rules.
- [ ] 05-03: Implement typed `SKILL.state`, validated patches, resets, and tests.

### Phase 6: ASME Salvage
**Goal:** Preserve all verified reusable ASME value inside Lifecycle without losing
provenance or authorizing premature deletion.
**Mode:** mvp
**Depends on:** Phase 5
**Requirements:** SALV-01, SALV-02, SALV-03
**Success Criteria** (what must be TRUE):
  1. The audit enumerates code, contracts, tests, provenance, license obligations, unique
   evidence, history, and untracked material.
  2. Every migrated asset has a canonical Lifecycle destination, provenance record, and
   passing compatibility check.
  3. ASME deletion remains blocked until a fresh lossless audit and Dr. Mani's action-time
   approval exist.
**Plans:** 2 plans

Plans:
- [ ] 06-01: Perform the lossless ASME inventory, provenance, and license audit.
- [ ] 06-02: Migrate and verify compatible assets; produce the deletion gate report.

### Phase 7: Daedalus Host Adapter
**Goal:** Make Daedalus the first consumer of Lifecycle through the public adapter
contract.
**Mode:** mvp
**Depends on:** Phase 6
**Requirements:** CORE-01, DAED-01, DAED-02, DAED-03
**Success Criteria** (what must be TRUE):
  1. Daedalus discovers and invokes Lifecycle without the core importing Daedalus.
  2. Study identities, permissions, state resets, events, and failures cross the adapter
   without silent translation.
  3. The Lifecycle core installs and passes its tests without the Daedalus repository.
**Plans:** 2 plans

Plans:
- [ ] 07-01: Freeze the host adapter contract and build its conformance suite.
- [ ] 07-02: Implement and verify the Daedalus adapter.

### Phase 8: Synthetic k-NN Study Harness
**Goal:** Build one reproducible paired-arm study that can falsify whether a candidate
skill adds value.
**Mode:** mvp
**Depends on:** Phase 7
**Requirements:** STUD-01, STUD-02, STUD-03, STUD-05
**Success Criteria** (what must be TRUE):
  1. The study runs locally on CPU without paid providers or live web access.
  2. Skill-enabled and target-withheld arms receive the same hidden task variants, support
   skills, pinned model, and frozen packet.
  3. Training, validation, and confirmation data remain separated and hidden traps are
   deterministic.
  4. Solver, Wiki Maintainer, Skill Proposer, and Evaluator begin in fresh isolated
   sessions with declared artifacts only.
**Plans:** 3 plans

Plans:
- [ ] 08-01: Build hidden k-NN variants, traps, scorers, and frozen packets.
- [ ] 08-02: Implement paired assignment, role isolation, and leakage checks.
- [ ] 08-03: Run synthetic harness qualification without making a skill-efficacy claim.

### Phase 9: Evaluation and Lifecycle Decisions
**Goal:** Convert study evidence into scoped, reversible decisions and require fresh
confirmation.
**Mode:** mvp
**Depends on:** Phase 8
**Requirements:** LIFE-02, LIFE-04, STUD-04, STUD-07
**Success Criteria** (what must be TRUE):
  1. Methodological correctness controls acceptance and efficiency is reported only after
   correctness passes.
  2. Every candidate decision records evidence for promotion, rejection, rollback,
   quarantine, or retirement.
  3. Promotion remains inside the sealed study scope until independent confirmation
   passes.
  4. A fresh confirmation can reject an earlier validation success without corrupting the
   evidence ledger.
**Plans:** 2 plans

Plans:
- [ ] 09-01: Implement deterministic outcome evaluation and scoped lifecycle decisions.
- [ ] 09-02: Execute the authorized first study and independent confirmation.

### Phase 10: Open-Source Distribution
**Goal:** Release an independently installable Lifecycle package and demonstrate the
host contract beyond Daedalus.
**Mode:** mvp
**Depends on:** Phase 9
**Requirements:** DIST-01, DIST-02, DIST-03
**Success Criteria** (what must be TRUE):
  1. A user can install a released Lifecycle version without cloning Daedalus.
  2. A shared installation serves supported hosts while each study pins exact versions and
   digests.
  3. A second host adapter passes the same conformance suite before demonstrated
   cross-runtime support is claimed.
**Plans:** 2 plans

Plans:
- [ ] 10-01: Select distribution targets and build reproducible release packaging.
- [ ] 10-02: Implement a second adapter, run conformance tests, and prepare the release.

## Progress

**Execution Order:** Phases execute in numeric order from 1 through 10.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Public Project Contract | 0/2 | Not started | - |
| 2. Canonical Schemas and Identity | 0/2 | Not started | - |
| 3. Event Ledger and Study Controller | 0/2 | Not started | - |
| 4. Security Admission | 0/2 | Not started | - |
| 5. Evidence, Candidates, and State | 0/3 | Not started | - |
| 6. ASME Salvage | 0/2 | Not started | - |
| 7. Daedalus Host Adapter | 0/2 | Not started | - |
| 8. Synthetic k-NN Study Harness | 0/3 | Not started | - |
| 9. Evaluation and Lifecycle Decisions | 0/2 | Not started | - |
| 10. Open-Source Distribution | 0/2 | Not started | - |

