# Implementation parity

This ledger maps every row in the locked 106-row source parity matrix to current
development-tree evidence. `IMPLEMENTED` means the named contract exists and has focused
tests. `PARTIAL` means required evidence or a named fixture remains. `BLOCKED` requires a
project-owner decision. `EXCLUDED` is an intentional contract boundary.

The ledger is not an independent review and does not authorize installation or release.

## Evidence keys

- `GOV`: `governance.py`, `NOTICE.md`, `PURPOSE.md`
- `DOM`: `domain.py`, `cartridge.py`, domain and cartridge tests
- `CAP`: `contract.py`, `adapter.py`, capability and role-boundary tests
- `FLOW`: `lifecycle.py`, `workflow.py`, workflow and lifecycle tests
- `WIKI`: `wiki.py`, `seed.py`, Maintainer and seed tests
- `TXN`: `transaction.py`, `workspace.py`, transaction and recovery tests
- `PKG`: `snapshot.py`, `package.py`, `delivery.py`, archive and staging tests
- `CLI`: `cli.py`, CLI tests and `scripts/stdlib_smoke.py`
- `HERMES`: `adapters/hermes_plugin`, read-only adapter tests, and Hermes Agent
  0.20.5 Plugin Doctor evidence
- `CLAIM`: `claims.py`, Gate 2 and public-claim tests
- `DOC`: `SKILL.md`, `README.md`, `PURPOSE.md`, `references/`
- `PENDING`: named acceptance coverage or external review still missing

## HF-A criterion evidence

This table records current implementation and test evidence for all 27 locked acceptance
criteria. It is not an external Gate 1 signoff. `PASS` means the criterion's local
contract is implemented and covered by the passing 515-test suite. Independent review is
separate evidence: the completed pre-repair review returned `SOUND WITH REQUIRED
CORRECTIONS`; the post-repair adversarial review (2026-08-31) confirmed RIR-01, RIR-02,
and RIR-03 closed. `POLICY-GATED` means code preserves the unresolved decision instead of
inventing approval.

| Criterion | Status | Current evidence |
|---|---|---|
| HF-A01 | PASS | `test_hf_a01_revision_8_status_never_becomes_sound` keeps Revision 8 at `NEEDS REVISION`. |
| HF-A02 | PASS | `RequirementRef`, governance source classes, and `test_hf_a02_paper_attribution_and_local_rules_stay_distinct`. |
| HF-A03 | PASS | Original Codex findings remain source-labelled; `test_hf_a03_adapters_do_not_fork_core_semantics` prevents adapter reinterpretation. |
| HF-A04 | PASS | Lifecycle, snapshot, wiki, and impact tests cover empty baseline, strict wins, rollback, persistent wiki, and impact history. |
| HF-A05 | PASS | `CapabilityReport` separates four fidelity levels; missing events prevent stronger labels. |
| HF-A06 | PASS | Role specs and `test_hf_a06_role_tools_are_role_specific_and_sorted` prevent a universal `read_file` or `finish` claim. |
| HF-A07 | PASS | Isolation dimensions fail closed to `unsandboxed`; the Hermes 0.20.5 probe reports unknown held-out and wiki isolation and does not dispatch. |
| HF-A08 | PASS | Real extractor/scorer fixtures bind output hashes and turn timeout, malformed, nonfinite, and out-of-range results into invalid evidence without scores. |
| HF-A09 | PASS | The state-operation cross-product and P1-P23 terminal fixtures cover deterministic transitions and refusals. |
| HF-A10 | PASS | Corrupt-train reset removes owned derived evidence and re-ingests a corrected output to the clean-run hashes. |
| HF-A11 | PASS | Intent-first transaction-v2, 169 crash cases, recover-twice equality, exact output-plan binding, and legacy-v1 recovery are covered. |
| HF-A12 | PASS | Immutable snapshots, the sole active pointer, hash verification, and disposable mirror rebuild are tested. |
| HF-A13 | PASS | Sampling enforces five failures, three passes, 15,000 characters, and locally attributed deterministic ordering. |
| HF-A14 | PASS | Role-payload schemas allow train truth only for Proposer and reject held-out truth and answer-path leakage. |
| HF-A15 | PASS | Wiki parsing enforces mechanical grammar while storing semantic qualities as attestations. |
| HF-A16 | PASS | Dedicated negative fixtures cover missing class, blank reason, duplicate tuple, trailing JSON, and multiset counts. |
| HF-A17 | PASS | Collision, literal propagation, legal-answer equality, and marker-free paraphrase limitations are tested. |
| HF-A18 | PASS | An independently authored 105-cell inventory covers 14 operations. Every cell mutates a real pre-intent dependency, and the engine binds dynamic reads, absences, arguments, state, clock, routes, seals, replay sources, and exact output plans. Lineage: the pre-repair review contradicted this criterion (synthetic mutation); the repair replaced it with real operation-path fixtures, confirmed closed by the post-repair adversarial review. |
| HF-A19 | PASS | Validated and untested routes are durable, exclusive, approval-bound, and separately labelled. |
| HF-A20 | PASS | Projection/archive tests reject unsafe members and require normalized path-byte equality and tamper detection. |
| HF-A21 | PASS | Gate 2 fails deterministic bindings and reports nondeterministic score differences without treating them as deterministic failures. |
| HF-A22 | PASS | `NEEDS_OPTIONAL_SEED` supports one approved named seed or skip, visibility checks, rollback, and recovery. Seed IDs propagate through proposer context into the exact sorted `PURPOSE.md` `origin_observations` list and validated delivery. |
| HF-A23 | PASS | Staging leaves declared live roots and Task Observer byte-identical; no installation path exists in the core. |
| HF-A24 | PASS | Domain APIs accept declared task sets and refuse session or transcript handles. |
| HF-A25 | POLICY-GATED | A2 and A3 remain explicit provisional architecture defaults; A4 remains unresolved; A5 authorizes only bounded worktree development. |
| HF-A26 | PASS | Local acceptance and paper-comparable claims are separate; the latter requires three complete runs and paired bootstrap evidence. |
| HF-A27 | PASS | Approval records require lowercase SHA-256 values, aware non-future timestamps, expiry, one phase, exact runtime and destination binding, and single use. Untested delivery persists the consumed approval in the same transaction and refuses identity, hash, record, or replay drift; no live approval has been fabricated. |

## Row ledger

| Row | Disposition | Evidence or remaining gap |
|---|---|---|
| SP-001 | IMPLEMENTED | GOV retains `NEEDS REVISION` and forbids a `SOUND` claim. |
| SP-002 | IMPLEMENTED | DOM enforces trusted text, text output, and `none` or `read`. |
| SP-003 | IMPLEMENTED | DOM treats cartridge programs as trusted; CAP records unsandboxed limits. |
| SP-004 | IMPLEMENTED | DOM refuses artifact-producing and interactive task classes. |
| SP-005 | IMPLEMENTED | DOM seal drift blocks mutation; no repair-in-place API exists. |
| SP-006 | IMPLEMENTED | DOC and DOM replace runtime paths with portable configuration. |
| SP-007 | IMPLEMENTED | CAP assigns tools per role and makes no broader paper claim. |
| SP-008 | IMPLEMENTED | FLOW excludes wiki and answers from inference jobs; CAP labels boundaries. |
| SP-009 | IMPLEMENTED | CAP has four trace-fidelity levels bound to captured events. |
| SP-010 | IMPLEMENTED | CAP makes role placement and isolation adapter evidence. |
| SP-011 | IMPLEMENTED | FLOW requires a fresh confirmation; GOV labels it local. |
| SP-012 | IMPLEMENTED | WIKI validates structure and provenance, then stores judgment reasons. |
| SP-013 | IMPLEMENTED | FLOW, WIKI, TXN, and PKG own the layered artifacts. |
| SP-014 | IMPLEMENTED | WIKI writes canonical `log.md`; DOC records the local choice. |
| SP-015 | IMPLEMENTED | FLOW starts from empty snapshot and wiki, then runs baseline. |
| SP-016 | IMPLEMENTED | FLOW iterates through K and ends early on a perfect best score. |
| SP-017 | IMPLEMENTED | FLOW injects active skills and excludes the wiki from train jobs. |
| SP-018 | IMPLEMENTED | WIKI enforces 5 failure, 3 success, and 15,000-character limits. |
| SP-019 | IMPLEMENTED | WIKI applies create, patch, index replacement, and log append. |
| SP-020 | IMPLEMENTED | WIKI separates parser checks from stored semantic attestations. |
| SP-021 | IMPLEMENTED | FLOW builds train-only Proposer context and requires four traces for change. |
| SP-022 | IMPLEMENTED | FLOW uses strict improvement, preserves wiki, and records impact. |
| SP-023 | IMPLEMENTED | FLOW and PKG require paired test evidence or approved untested staging. |
| SP-024 | IMPLEMENTED | DOC and code contain no Task Observer mutation path. |
| SP-025 | IMPLEMENTED | DOM accepts declared files only; no session-history input exists. |
| SP-026 | IMPLEMENTED | WIKI and impact history are local to the domain workspace. |
| SP-027 | IMPLEMENTED | FLOW acceptance and PKG staging remain distinct from installation. |
| SP-028 | IMPLEMENTED | FLOW records scores and exposes no pruning operation. |
| SP-029 | IMPLEMENTED | WIKI seed packets are named, approved, visibility-safe, and reversible. |
| SP-030 | IMPLEMENTED | PKG has validated and untested staging only. |
| SP-031 | IMPLEMENTED | A validated export can emit one read-only `pending_human_review` observation candidate. Task Observer or another external procedure owns confidence, acceptance, and any shared-log write. |
| SP-032 | IMPLEMENTED | CLI requires caller-supplied workspace and forbidden live roots. |
| SP-033 | PARTIAL | Inventory exists, but A4 blocks a project license file and release bundle. |
| SP-034 | IMPLEMENTED | SKILL has the canonical name, bounded `Use when` description, three-part version, ISO update date, and numbered concrete triggers. A4 remains a separate license gate. |
| SP-035 | BLOCKED | Paper attribution exists; verbatim prompts and project license await A4. |
| SP-036 | IMPLEMENTED | Paper notes retain the 48.7/63.7/60.9 ablation, Table 4 ranges, `logs.md`/`log.md` inconsistency, and four stated limitations without claiming reproduction. |
| SP-037 | IMPLEMENTED | DOC defines fidelity, isolation, marker, and claim limits. |
| SP-038 | IMPLEMENTED | Verification pointer names completed and pending evidence without private reports. |
| SP-039 | IMPLEMENTED | Runtime is stdlib-only; real extractor, scorer, templates, and smoke exist. |
| SP-040 | IMPLEMENTED | DOM, TXN, snapshot, and archive paths reject escapes and symlinks. |
| SP-041 | IMPLEMENTED | Seal, K, splits, and rehash checks exist; omitted split markers become unique collision-checked random 32-hex values sealed into the domain record. |
| SP-042 | IMPLEMENTED | DOM enforces one answer per task, disjoint IDs and inputs, and nonempty splits. |
| SP-043 | IMPLEMENTED | FLOW separates prediction artifacts, scans markers, and keeps CLI output narrow. |
| SP-044 | IMPLEMENTED | CAP and FLOW construct role-specific inputs; only train truth reaches Proposer. |
| SP-045 | IMPLEMENTED | Run records and immutable manifests exist; every core mutation records a normalized system or explicit fixed-clock value in its transaction intent. |
| SP-046 | IMPLEMENTED | Real subprocess failures produce invalid evidence and no score. |
| SP-047 | IMPLEMENTED | Valid train ingest publishes raw and aliases; reset removes derived copies and the rejected capture while retaining `.out.md` until a corrected capture replaces it. |
| SP-048 | IMPLEMENTED | Exact length-framed snapshots, sole active pointer, verification, and mirror rebuild exist. |
| SP-049 | IMPLEMENTED | Versioned state contains manifest, route, ledger, seed, candidate, and txn fields. |
| SP-050 | IMPLEMENTED | Manifest consumption and durable route exclusivity are enforced. |
| SP-051 | IMPLEMENTED | WIKI sorts task IDs before bounded sampling and labels it local. |
| SP-052 | IMPLEMENTED | Lifecycle is total and init enters the optional-seed phase. |
| SP-053 | IMPLEMENTED | Baseline prepare, ingest, reset, finalize, and perfect branch execute. |
| SP-054 | IMPLEMENTED | Train prepare, ingest, sample, and apply-wiki execute. |
| SP-055 | IMPLEMENTED | Proposer context, create, patch, no-action, and impact execute. |
| SP-056 | IMPLEMENTED | Validation, confirmation, min accepted score, and both rejection branches execute. |
| SP-057 | IMPLEMENTED | Candidate abandonment consumes valid or deletes invalid owned evidence. |
| SP-058 | IMPLEMENTED | DONE tests, route latch, staging, and same-identity replay exist. |
| SP-059 | IMPLEMENTED | Recover replays recorded intent; status is read-only; pending writes fail closed. |
| SP-060 | IMPLEMENTED | P1-P23 execute as separate scored terminal fixtures, including invalid-output repair, four abandon positions, multi-iteration outcomes, both delivery routes, and route conflict. |
| SP-061 | IMPLEMENTED | TXN uses a per-domain lock and self-contained intent record. |
| SP-062 | IMPLEMENTED | Intent precedes every owned-root write; replay embeds deterministic bytes. |
| SP-063 | IMPLEMENTED | Ordered writes and deletions precede the atomic final state commit. |
| SP-064 | IMPLEMENTED | All 24 core state-changing operation names execute at all 7 declared crash boundaries in the fixed-clock crash-oracle matrix. |
| SP-065 | IMPLEMENTED | The fixed-clock oracle compares state, route, ledger, domain, snapshots, mirror, raw, runs, wiki, impact, staging, archives, and transaction residue against uninterrupted execution. |
| SP-066 | IMPLEMENTED | WIKI enforces headings, evidence JSON, and unique sequential patch targets. |
| SP-067 | IMPLEMENTED | WIKI enforces input hash, class coverage, trace lists, tuple multiset, and reasons. |
| SP-068 | IMPLEMENTED | Missing class, blank reason, duplicate tuple, and trailing JSON tests exist. |
| SP-069 | IMPLEMENTED | The versioned matrix binds every workflow command to its dynamic reads, tree membership, negative-existence predicates, state-derived values, and exact write/deletion/next-state output plan before intent. All matrix operations have a real binding path; recovery validates the recorded replay source and output plan. Lineage: contradicted pre-repair, repaired with real operation-path drift fixtures, confirmed closed post-repair. |
| SP-070 | IMPLEMENTED | CLI covers lifecycle, staging, recovery, and archive verification with no install. |
| SP-071 | IMPLEMENTED | Validated delivery binds both test manifests to the supplied capability-report hash and derives exact package labels from that report. |
| SP-072 | IMPLEMENTED | Untested status, document labels, route, and hash-bound approval are required. |
| SP-073 | IMPLEMENTED | Core owns order, adapter owns orchestration, human installation is absent. |
| SP-074 | IMPLEMENTED | Core jobs require fresh identities; the Hermes adapter takes the allowed zero-worker branch and an AST/runtime fixture proves it exposes no launch or delegation surface. |
| SP-075 | IMPLEMENTED | Test preparation latches validated route; untested route needs approval first. |
| SP-076 | IMPLEMENTED | Prompt-only role inputs, held-out boundaries, PURPOSE citations, and current approvals are core-checked. The Hermes active-context probe labels unresolved isolation, reports no provider route lock, and selects zero workers before any model request. |
| SP-077 | IMPLEMENTED | The 515-test suite passes on Python 3.14.6, all 27 HF-A criteria have criterion-level evidence, stdlib smoke and conservative plugin probes pass on Python 3.11.15 through 3.14.6, and Hermes 0.20.5 Plugin Doctor passes with one tool and zero hooks. Lineage: contradicted pre-repair over HF-A18 and timeout evidence; both repairs confirmed closed by the post-repair adversarial review. |
| SP-078 | IMPLEMENTED | WIKI negative fixtures use multiset wording and behavior. |
| SP-079 | IMPLEMENTED | Every operation-boundary fixture proves pending-operation refusal, recover-twice idempotence, exact tree equality, and no transaction residue. |
| SP-080 | IMPLEMENTED | State-operation cross-product, P1-P23, corrected reset paths, and exhaustive missing, valid, consumed, ambiguous, symlink, and wrong-phase reset errors execute. |
| SP-081 | IMPLEMENTED | Extractor/scorer errors, strict scores, rollback, and wiki persistence are tested. |
| SP-082 | IMPLEMENTED | Marker propagation, legal answer equality, copied marker, and paraphrase limits are tested. |
| SP-083 | IMPLEMENTED | Route refusal, sweep, manifest, normalized archive, and tamper tests exist. |
| SP-084 | IMPLEMENTED | Fresh temporary domains exercise mutually exclusive branches and smoke. |
| SP-085 | PARTIAL | Real bounded smoke and deterministic Gate 2 exist; nondeterministic adapter runs are pending. |
| SP-086 | PARTIAL | Staging order and hash readback exist. The first independent review returned `SOUND WITH REQUIRED CORRECTIONS`; a fresh read-only review of the repaired frozen candidate and Gate 2 artifact remains pending. |
| SP-087 | BLOCKED | Package lint and no-em-dash checks are possible; release license/date await A4. |
| SP-088 | EXCLUDED | Core never appends to Task Observer. It can print a review-only candidate with `shared_log_write_allowed: false`; an explicit external procedure owns any later action. |
| SP-089 | PARTIAL | Gate 2 comparator exists and the initial independent review identified required corrections. Fresh external Gates 0 and 1 review of the repaired candidate is pending. |
| SP-090 | IMPLEMENTED | DOC treats historical CLI flags as nonbinding and uses current adapter contracts. |
| SP-091 | IMPLEMENTED | No Task Observer import, path, write, or invocation exists. |
| SP-092 | EXCLUDED | Skill retrieval and trigger quality are outside evolution v1. |
| SP-093 | EXCLUDED | Wiki pruning and archival have no operation. |
| SP-094 | EXCLUDED | No live transcript or session-handle input exists. |
| SP-095 | IMPLEMENTED | CLAIM requires three runs and paired bootstrap only for paper-comparable claims. |
| SP-096 | IMPLEMENTED | CAP permits stronger labels only from measured adapter evidence. |
| SP-097 | EXCLUDED | DOM rejects artifact-producing and environment-interactive domains. |
| SP-098 | EXCLUDED | Semantic quality is stored as judgment, never mechanically proved. |
| SP-099 | IMPLEMENTED | GOV and DOC preserve corrected historical status without claiming closure. |
| SP-100 | IMPLEMENTED | Corrupt train reset deletes raw traces and aliases before corrected ingest. |
| SP-101 | IMPLEMENTED | Explicit seed and rollback replace nonexistent k=0 apply-wiki. |
| SP-102 | IMPLEMENTED | DOC cites the primary paper and separates paper facts from local rules. |
| SP-103 | PARTIAL | One shared core and thin Hermes adapter exist; Claude and Codex adapters are future work. |
| SP-104 | IMPLEMENTED | CAP requires exact OpenAI-backed provider and model allowlists with no fallback. |
| SP-105 | IMPLEMENTED | Runtime core has no network client or paid dependency. |
| SP-106 | IMPLEMENTED | Live install, commit, merge, publication, and distribution remain outside this tree. |

## Current release blockers

1. A4 exact license instrument and prompt-inclusion decision. Free community use,
   attribution, and a project-page link to manysaintvictormd.com are required.
2. Add dispatch-bound negative tests if a future Hermes provider-lock API permits role execution.
3. Complete independent staged-package review and external validation reports.
4. Independent post-implementation review and Gate 2 over a frozen staged artifact.
5. Claude Code and Codex adapters if cross-runtime execution is included in the release.
