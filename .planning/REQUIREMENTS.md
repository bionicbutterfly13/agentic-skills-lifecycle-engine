# Requirements: Agentic Skills Lifecycle Engine

**Defined:** 2026-09-04
**Core Value:** No skill is treated as improved unless a reproducible, controlled
evaluation shows that it helps without violating correctness or safety.

## v1 Requirements

### Project Contract

- [ ] **PROJ-01**: A contributor can identify Agentic Skills Lifecycle Engine as the
  full project name and Lifecycle as its short name from canonical repository files.
- [ ] **PROJ-02**: A contributor can distinguish verified research, proposed design,
  implemented behavior, run evidence, and release status.
- [ ] **PROJ-03**: A reader can trace the initial architecture and experimental choices
  to the reviewed primary-source packet.

### Core Contracts

- [ ] **CORE-01**: A host can integrate with Lifecycle through a documented adapter
  contract without importing Daedalus-specific core behavior.
- [ ] **CORE-02**: Lifecycle can validate canonical schemas for sources, evidence,
  skills, permissions, state, studies, events, and lifecycle decisions.
- [ ] **CORE-03**: Lifecycle can create stable content identities from canonical bytes
  and invalidate prior approval after any byte change.

### Evidence

- [ ] **EVID-01**: A maintainer can record source-grounded claims with provenance,
  evidence quality, and immutable source references.
- [ ] **EVID-02**: Every study transition is written to an append-only machine-readable
  event ledger before a human-readable journal projection is produced.
- [ ] **EVID-03**: Every study records the exact Lifecycle version and content digest
  used by each arm.
- [ ] **EVID-04**: Candidate creation can use scored training traces while held-out
  validation and confirmation evidence remain inaccessible.

### Skill Lifecycle

- [ ] **LIFE-01**: Lifecycle can build one immutable candidate skill from bounded,
  evidence-backed changes.
- [ ] **LIFE-02**: Lifecycle can record proposed, admitted, rejected, promoted,
  rolled-back, quarantined, and retired states with supporting evidence.
- [ ] **LIFE-03**: Lifecycle abstains from promotion when evidence is weak,
  contradictory, incomplete, or outside the declared study scope.
- [ ] **LIFE-04**: A promotion is limited to the sealed study scope until an independent
  confirmation authorizes broader use.

### Skill State

- [ ] **STAT-01**: A skill can declare a small typed `SKILL.state` schema with explicit
  bounds and allowed fields.
- [ ] **STAT-02**: State resets for every fresh trial and paired arm unless a future
  protocol explicitly authorizes another boundary.
- [ ] **STAT-03**: A model may propose a state patch, but deterministic code applies it
  only after schema, size, transition, and permission validation.

### Security

- [ ] **SECU-01**: Every role and candidate begins with a default-deny capability
  ceiling and receives only declared study permissions.
- [ ] **SECU-02**: Retrieval relevance, trust, license, policy, compatibility, and
  runtime admission are evaluated as separate gates.
- [ ] **SECU-03**: Missing evidence, uncertain checks, residual obligations, or an
  incomplete inspection cause admission or promotion to fail closed.
- [ ] **SECU-04**: First-study candidate packages contain only declared instructions,
  references, and state schemas, with no executable payload or undeclared effect.

### Daedalus Adapter

- [ ] **DAED-01**: Daedalus can discover and invoke Lifecycle through the first explicit
  host adapter.
- [ ] **DAED-02**: The adapter preserves Lifecycle study identities, permissions,
  state-reset boundaries, events, and failure status without silent translation.
- [ ] **DAED-03**: Daedalus remains a consumer and proving host; the Lifecycle core can
  be installed and tested without the Daedalus repository.

### First Study

- [ ] **STUD-01**: A contributor can run a CPU-local synthetic k-nearest-neighbor study
  without paid providers or live web access.
- [ ] **STUD-02**: Each paired trial compares a skill-enabled arm with a
  target-skill-withheld arm under identical support skills and a pinned model.
- [ ] **STUD-03**: Training, validation, and confirmation use separated data; validation
  includes hidden task variants and deterministic hidden traps.
- [ ] **STUD-04**: Methodological correctness is a hard gate and efficiency is reported
  only after correctness passes.
- [ ] **STUD-05**: Solver, Wiki Maintainer, Skill Proposer, and Evaluator run in fresh,
  isolated sessions with only their declared artifacts and permissions.
- [ ] **STUD-06**: The controller enforces a predeclared finite iteration cap and stops
  early on success, futility, or safety failure.
- [ ] **STUD-07**: An independent confirmation determines whether an accepted candidate
  survives fresh execution before any broader claim is allowed.

### Distribution and Documentation

- [ ] **DIST-01**: A user can install a released Lifecycle version independently of
  Daedalus through a documented distribution mechanism.
- [ ] **DIST-02**: A shared installation can serve supported AI runtimes while studies
  continue to pin exact versions and digests.
- [ ] **DIST-03**: At least two host adapters pass the same core contract suite before
  the project claims demonstrated cross-runtime support.
- [ ] **DOCS-01**: The repository contains a public project introduction and a dated
  journal article describing the 2026-09-03 and 2026-09-04 research and design work.
- [ ] **DOCS-02**: Public documentation labels unimplemented architecture and unrun
  studies as plans rather than accomplishments.

### ASME Salvage

- [ ] **SALV-01**: A fresh audit enumerates reusable ASME code, contracts, tests,
  provenance, license obligations, unique evidence, Git history, and untracked files.
- [ ] **SALV-02**: Only verified, compatible assets are migrated into canonical
  Lifecycle locations with provenance preserved.
- [ ] **SALV-03**: ASME deletion remains blocked until the lossless audit passes,
  migrated assets are verified, ownership is clear, and Dr. Mani gives action-time
  approval.

### WikiSkill Method Parity

- [ ] **PAR-01**: A contributor can confirm the current study targets method parity
  (paper's four roles, paper's prompts, one domain, no numbers claimed) per ADR-0001,
  with empirical parity deferred until a real end-to-end run.
- [x] **PAR-02**: The Inference Agent can run against a bare local model through a
  direct adapter speaking any OpenAI-compatible endpoint, per ADR-0002, without a paid
  provider.
- [x] **PAR-03**: A study manifest can switch the confirmation run off for
  paper_comparable runs and on (two strict wins, score = min(val, confirm)) for
  production promotion, per ADR-0003.
- [ ] **PAR-04**: The Skill Proposer can run in detective mode (multi-turn ReAct,
  journaled reads, >=4 traces read before proposing) by default, with a single-shot
  ablation flag for testing that default, per ADR-0004.
- [x] **PAR-05**: The paper's prompts (Appendix E.1-E.3) are copied verbatim into
  references/paper-prompts/ with CC BY 4.0 attribution, with local additions kept in a
  separate wrapper layer, per ADR-0005.
- [ ] **PAR-06**: The first study domain is LiveMath-like (LiveMathematicianBench-style
  single-step math items) with tool mode none, iteration cap K=8, and early stop when
  R_best=1.0.
- [x] **PAR-07**: A GitHub wiki page titled "Additions beyond the paper" lists every
  Lifecycle deviation or extension from the WikiSkill paper (confirmation-run switch,
  transaction journal, digest binding, attestation field, detective-mode flag, direct
  adapter, seed observations, staging archive), drafted at docs/wiki-draft/. The
  repository is public and the wiki is enabled; publication waits only on materializing
  the wiki git repository, which requires creating one page in the GitHub browser UI
  first.

## v2 Requirements

### Ecosystem Scale

- **ECOS-01**: Lifecycle can retrieve and rerank compatible skills from a large noisy
  registry without treating relevance as permission.
- **ECOS-02**: Lifecycle can maintain cross-skill dependencies, redundancy, conflicts,
  and retirement evidence across a shared registry.
- **ECOS-03**: Multi-agent studies can test whether knowledge and skills transfer across
  roles without leaking held-out evidence.

### Domain Adapters

- **COPY-01**: Lifecycle can evaluate copywriting skills derived from NoeAI, RMBC,
  Great Leads, and Jon Benson tools after the core experimental contract is validated.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automatic global promotion from one study | A local pass does not establish general utility or safety |
| Unbounded autonomous self-modification | It breaks identity, auditability, and least privilege |
| Live web access during frozen evaluation | It permits leakage and changes the experimental environment |
| Daedalus ownership of Lifecycle | Lifecycle must remain independently installable and reusable |
| Broad self-improvement claims before live evidence | Architecture and synthetic fixtures do not establish product efficacy |
| Immediate ASME deletion | Salvage, provenance, license, history, and ownership checks are incomplete |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROJ-01 | Phase 1 | Pending |
| PROJ-02 | Phase 1 | Pending |
| PROJ-03 | Phase 1 | Pending |
| CORE-01 | Phase 7 | Pending |
| CORE-02 | Phase 2 | Pending |
| CORE-03 | Phase 2 | Pending |
| EVID-01 | Phase 5 | Pending |
| EVID-02 | Phase 3 | Pending |
| EVID-03 | Phase 2 | Pending |
| EVID-04 | Phase 5 | Pending |
| LIFE-01 | Phase 5 | Pending |
| LIFE-02 | Phase 9 | Pending |
| LIFE-03 | Phase 5 | Pending |
| LIFE-04 | Phase 9 | Pending |
| STAT-01 | Phase 5 | Pending |
| STAT-02 | Phase 5 | Pending |
| STAT-03 | Phase 5 | Pending |
| SECU-01 | Phase 4 | Pending |
| SECU-02 | Phase 4 | Pending |
| SECU-03 | Phase 4 | Pending |
| SECU-04 | Phase 4 | Pending |
| DAED-01 | Phase 7 | Pending |
| DAED-02 | Phase 7 | Pending |
| DAED-03 | Phase 7 | Pending |
| STUD-01 | Phase 8 | Pending |
| STUD-02 | Phase 8 | Pending |
| STUD-03 | Phase 8 | Pending |
| STUD-04 | Phase 9 | Pending |
| STUD-05 | Phase 8 | Pending |
| STUD-06 | Phase 3 | Pending |
| STUD-07 | Phase 9 | Pending |
| DIST-01 | Phase 10 | Pending |
| DIST-02 | Phase 10 | Pending |
| DIST-03 | Phase 10 | Pending |
| DOCS-01 | Phase 1 | Pending |
| DOCS-02 | Phase 1 | Pending |
| SALV-01 | Phase 6 | Pending |
| SALV-02 | Phase 6 | Pending |
| SALV-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 39 total
- Mapped to phases: 39
- Unmapped: 0

---
*Requirements defined: 2026-09-04*
*Last updated: 2026-09-04 after initial roadmap creation*
