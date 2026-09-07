# WikiSkill source parity matrix

Status: PROPOSED FOR GATE A. This matrix maps every binding rule family in Revision 8. A row marked `CHANGED` supersedes the plan text only if Gate A approves the architecture contract. A row marked `EXCLUDED` states why it is not part of portable v1.

Legend:

- `CORE`: runtime-neutral shared core owns semantics.
- `H`: Hermes adapter owns translation or orchestration.
- `CL`: Claude adapter owns translation or runtime evidence.
- `CX`: Codex adapter owns translation or runtime evidence.
- `CHANGED`: architecture corrects or narrows Revision 8 with reason.
- `EXCLUDED`: deliberately outside portable v1 with reason.
- `GATE A`: unresolved human decision.

| ID | Revision 8 locator | Binding rule | CORE | H | CL | CX | Disposition and reason |
|---|---|---|---|---|---|---|---|
| SP-001 | 1-3 | Revision 8 is the final historical proposal after Round 7, with future Codex gates still required. | provenance/status | display | display | display | CHANGED: retain `NEEDS REVISION`; remove any implication that Revision 8 is validated or binding without Gate A. |
| SP-002 | 5 | Trusted domains, text output, `none|read`, trusted extractor/scorer, no harness network/LLM. | scope/schema | enforce route | project | sandbox policy | GATE A A3. Recommended portable v1 retains the narrow scope. |
| SP-003 | 5 | Plug-ins are unsandboxed trusted user code with timeouts. | subprocess contract | invoke | invoke | invoke | Retained only if A3 approves trusted-domain v1; capability and threat labels required. |
| SP-004 | 5 | Artifact-producing and environment-interactive tasks are out of scope. | schema refusal | refuse | refuse | refuse | GATE A A3; retained by default because side-effect identity/reset contracts are absent. |
| SP-005 | 5 | Sealed plug-in or task drift creates a new domain; no repair in place. | seal/domain identity | report | report | report | CORE. Prevents ambiguous evidence lineage. |
| SP-006 | 9-14 | Paper and video source claims remain source-labelled; standalone skill, declared task set, procedure/prompts/harness depth, persistent domain workspaces. | provenance/config | native paths | projection | projection | CHANGED: portable config replaces Claude-only path as semantic truth; runtime paths are adapter config. |
| SP-007 | 18 | Claim that every paper role had exactly `read_file` and `finish`. | role evidence labels | no claim | no claim | no claim | CHANGED: paper establishes the exact pair only for Proposer. No adapter copies the broader claim. |
| SP-008 | 18 | Inference has no wiki access; Claude isolation is procedural and results are `unsandboxed`, never `unseen`. | capability schema | prove/label | prove/label | prove/label | CORE rule, adapter proof. Truthful degradation retained. |
| SP-009 | 19 | Claude returned message is narrower than paper full event stream and labelled `observable_transcript`. | capture schema | enumerate events | enumerate events | enumerate events | CORE taxonomy. Each adapter records actual fidelity. |
| SP-010 | 20 | Maintainer and Proposer run in Claude main agent and are unsandboxed. | role port | Hermes role job | Claude projection | Codex role job | CHANGED: main-agent placement is Claude-specific, not core. Every runtime labels actual role isolation. |
| SP-011 | 21 | One fresh confirmation replaces paper three-run/bootstrap for local acceptance. | acceptance policy | orchestrate | orchestrate | orchestrate | GATE A A2. Recommended local rule retained but never represented as a paper rule. |
| SP-012 | 22 | Four semantic qualities are agent judgments; harness proves only structure, provenance, and labels. | grammar/attestation | role output | role output | role output | CORE. No mechanical semantic-proof claim. |
| SP-013 | 26-28 | Raw traces, wiki, impact history, patterns, skills/PURPOSE, plus local iteration/state/snapshot artifacts. | canonical layout/schema | path mapping | path mapping | path mapping | CORE semantic ownership; runtime roots are adapters. |
| SP-014 | 26 | Resolve paper `logs.md`/`log.md` inconsistency by using `log.md` and recording it. | provenance note | project | project | project | Retained as explicit local choice. |
| SP-015 | 32 | Initialize empty skills and empty wiki; baseline validation. | lifecycle | dispatch | dispatch | dispatch | CORE, PAPER. |
| SP-016 | 33 | Iterate k=1..K; stop at perfect best score. | lifecycle | route | route | route | CORE, PAPER. |
| SP-017 | 34 | Roll out every train task with full active skills and no wiki. | job spec | delegate/Kanban | fork/job | sandbox/job | CORE plus adapter isolation proof. |
| SP-018 | 35 | Sample max five failures, up to three passes, 15,000 characters per view. | sampler | none | none | none | CORE, PAPER. |
| SP-019 | 36 | Maintainer receives sampled logs and current wiki; creates/patches pages, replaces index, appends log; no pattern cap. | wiki schema | role orchestration | role orchestration | role orchestration | CORE semantics, adapter role execution. |
| SP-020 | 36 | Pattern content rules: description, root cause, commands, known solutions, success/failure, no duplicates, 10-30 lines, generalizable. | mechanical subset | judgments | judgments | judgments | CORE separates parser-enforced fields from semantic attestations. |
| SP-021 | 37 | Proposer receives index, impact history, all train outcomes including ground truth, active skills; reads evidence on demand; four traces before change; create/patch/no-action. | role input/proposal schema | role orchestration | role orchestration | role orchestration | CORE. Four-trace rule applies only when proposing a change. |
| SP-022 | 38 | Strict aggregate validation greater than best; rejection rolls back skill only; wiki persists; impact appended. | lifecycle/evaluation | route | route | route | CORE, PAPER. |
| SP-023 | 39 | Disjoint final test; validated export requires baseline/final test; separately labelled untested route needs action-time approval. | route state/package | approval bridge | approval bridge | approval bridge | CORE local policy plus human gate. No route equals installation. |
| SP-024 | 43-53 | Task Observer comparison remains accurate and systems stay distinct. | integration contract | surface | surface | surface | CORE boundary. Task Observer is not modified. |
| SP-025 | 45 | WikiSkill raw evidence comes from declared task sets, not Task Observer live work. | input policy | reject implicit capture | same | same | CORE, DIRECT. |
| SP-026 | 46-47 | WikiSkill adds iterative pattern/index and proposer-readable impact history without changing Task Observer archives or optimizer packets. | artifact model | none | none | none | CORE. Complementary systems. |
| SP-027 | 48-50 | Wiki access policies and validation gates differ; WikiSkill acceptance is not Task Observer acceptance or installation. | gate labels | native approvals | native approvals | native approvals | CORE plus adapter approval translation. |
| SP-028 | 51-52 | WikiSkill has scores, not Task Observer confidence; no automatic wiki pruning/archive. | schema | none | none | none | CORE. Retrieval/pruning remain excluded. |
| SP-029 | 54 | Human-named Task Observer observations may seed k=0 pages with provenance and internal/public boundary. | seed schema/state | approval record | approval record | approval record | CHANGED: real `seed-observations` pre-baseline transition replaces nonexistent k=0 `apply-wiki`. |
| SP-030 | 54 | Evolved skills leave only via validated or explicitly untested staging; human installs. | package/routes | approval surface | approval surface | approval surface | CORE staging, adapters project. No direct live write. |
| SP-031 | 54 | Log Task Observer observation only for reusable signal; routine telemetry stays in WikiSkill. | integration event | optional adapter note | same | same | Retained boundary; not invocation telemetry. |
| SP-032 | 56-76 | Historical Claude staging and installed paths. | canonical package | Hermes staging root | Claude staging projection | Codex staging projection | CHANGED: no Claude path in core. Every destination is adapter config and installation is later. |
| SP-033 | 61-76 | Bundle includes SKILL, license, manifest, paper references, algorithm, integration, fidelity, verification, harness, extractor/scorer, templates, tests. | package manifest | projection | projection | projection | CORE package inventory after Engineering, subject to A4 for license/prompts. |
| SP-034 | 62 | Version/date/short description/numbered triggers. | package metadata | Hermes metadata | Claude metadata | Codex metadata | CHANGED: canonical metadata plus generated runtime fields; runtime-specific trigger syntax not shared truth. |
| SP-035 | 63-65 | CC BY 4.0 paper attribution and verbatim prompt appendix. | provenance/package | project | project | project | GATE A A4. Prompts remain separately attributed if redistributed. |
| SP-036 | 68 | Paper notes include ablation, Table 4, log naming, limitations. | reference/provenance | project | project | project | CORE documentation, with paper locators. |
| SP-037 | 69 | Fidelity reference carries five limitations and labels. | capability policy | projection | projection | projection | CORE canonical taxonomy, generated runtime facts. |
| SP-038 | 70, 244 | Verification README names external reports; reports remain outside bundle. | verification manifest | report | report | report | CORE pointer only; do not package private audit corpus. |
| SP-039 | 71-75, 215 | Stdlib-only harness, deterministic extractor/scorer, templates, unittest, no model/network in core. | implementation constraint | orchestration only | orchestration only | orchestration only | CORE. Adapter runtime model calls are outside core. |
| SP-040 | 80 | Identifier grammar, path containment, symlink rejection. | path validator | no override | no override | no override | CORE. |
| SP-041 | 81 | Domain seal hashes tasks, answers, template, extractor, scorer; verify before mutation; K>=1; nonempty splits; collision-checked markers; seal hash in manifests. | domain/seal | report | report | report | CORE. |
| SP-042 | 82 | Separate task/answer JSONL; disjoint task IDs and input hashes; nonempty train/val/test. | schema/ingest | omit answers | omit answers | omit answers | CORE plus adapter isolation. |
| SP-043 | 83-86 | Ground-truth and prediction provenance classes; leak markers; candidate scan; stdout excludes answers/markers. | evidence/provenance | capture | capture | capture | CORE. Markers detect propagation, not access. |
| SP-044 | 87-92 | Role-specific evidence boundary: inference prompt only; Maintainer no expected; Proposer train expected; extractor/scorer narrow; main role avoids val/test answers. | role/job schemas | enforce/label | enforce/label | enforce/label | CORE request minimization; adapters prove or label filesystem isolation. |
| SP-045 | 93 | Run directories, sidecar schema, create/identical-skip/mismatch-refuse, fixed clock, immutable manifest, state-only consumption. | run/evidence schema | normalize capture | normalize capture | normalize capture | CORE. Runtime timestamps enter only through captured record then fixed canonical clock rules. |
| SP-046 | 94 | Extractor/scorer subprocess timeout and output grammar; invalid evidence never scores or advances. | evaluation | none | none | none | CORE, fail closed. |
| SP-047 | 95 | Train raw traces publish only for valid manifest; alias current k. | raw evidence txn | none | none | none | CHANGED: reset of corrupt/unparseable train also deletes all derived raw/aliases before corrected ingest. |
| SP-048 | 96 | Immutable complete snapshots; length-framed tree hash; temp publish; corruption refusal; active pointer sole truth; disposable mirror hash/rebuild. | snapshots | read projection | read projection | read projection | CORE. |
| SP-049 | 97 | State fields, consumption, provisional, route, ledger, seal, history, txn. | state schema | display | display | display | CORE. Add contract/state revision and optional-seed disposition. |
| SP-050 | 97 | Valid manifest consumed once; invalid/unparseable reset only unconsumed; exclusive durable delivery route. | state invariants | route | route | route | CORE. |
| SP-051 | 98 | Deterministic sample by sorted task ID. | sampler | none | none | none | CORE, labelled local rather than paper fact. |
| SP-052 | 99-103 | Total transition table and `init` behavior. | lifecycle | invoke | invoke | invoke | CHANGED: `init` enters `NEEDS_OPTIONAL_SEED`, then explicit seed/skip before baseline. |
| SP-053 | 104-107 | Baseline prepare, ingest, reset, finalize and perfect-baseline branch. | lifecycle | rollouts | rollouts | rollouts | CORE. Reset ownership corrected by SP-047. |
| SP-054 | 108-111 | Train prepare/ingest, sample, apply-wiki. | lifecycle/wiki | rollouts/role | rollouts/role | rollouts/role | CORE. |
| SP-055 | 112-114 | Proposer context; create/patch candidate; no-action impact and k advance. | lifecycle/skills | role | role | role | CORE. |
| SP-056 | 115-120 | Validation, provisional win, fresh confirmation, strict two-run acceptance, min accepted score, rejection branches. | lifecycle/evaluation | fresh jobs | fresh jobs | fresh jobs | GATE A A2 for local confirmation; paper attribution remains separate. |
| SP-057 | 121 | Abandon candidate from all candidate-bearing states, consuming valid and deleting invalid evidence. | lifecycle/txn | invoke | invoke | invoke | CORE. |
| SP-058 | 122-125 | DONE test, export, and package-untested route transitions and idempotency. | lifecycle/package | approval | approval | approval | CORE. Installation remains absent. |
| SP-059 | 126-129 | Recover pending transaction; status read-only; all other commands refuse pending transaction. | transaction | display | display | display | CORE. |
| SP-060 | 131-157 | P1-P23 terminal-path fixtures. | conformance fixtures | run Hermes paths | later projection | later projection | CORE fixtures. Correct malformed outputs, never sealed plug-ins. Add seed/skip fixtures and corrected reset/raw cases. |
| SP-061 | 159 | Per-domain lock and self-contained transaction. | transaction | no bypass | no bypass | no bypass | CORE. |
| SP-062 | 159, 283 | Large objects published before txn and unreferenced objects GC'd by recover. | transaction | none | none | none | CHANGED: transaction intent must exist before any owned-root object; deterministic replay inputs rebuild large objects. Closes pre-txn residue. |
| SP-063 | 159 | Atomic state write, ordered outputs/deletions, entry IDs, pointer/route commit, lazy mirror, deterministic IDs. | transaction | none | none | none | CORE, subject to intent-first ordering. |
| SP-064 | 160-173 | Named fault-injection points for every state-changing operation. | conformance | none | none | none | CORE. Expand to pre-intent/post-intent boundaries where applicable. |
| SP-065 | 175 | Fixed-clock equality oracle across domain, state projection, staging, archives, and no residue. | recovery oracle | none | none | none | CORE. Expanded to all owned roots, raw aliases, route/ledger, and pre-intent cleanup. |
| SP-066 | 176 | Pattern page grammar, ordered unique headings, evidence JSON, unique-match sequential patches. | parser/patcher | role output | role output | role output | CORE. |
| SP-067 | 177-185 | Input-bound attestation, class coverage, trace lists, quoted-command multiset, section content, dedup disposition, judgment reasons, line count. | parser/attestation | role output | role output | role output | CORE. Semantic reasons are recorded, not mechanically validated. |
| SP-068 | 177-181 vs 236 | Gate 1 test inventory for class coverage and evidence tuples. | conformance | none | none | none | CHANGED: explicitly test missing class, blank reason, duplicate tuple, trailing JSON; use multiset consistently. |
| SP-069 | 186-204 | Command dependency table covers dynamic inputs/outputs plus args, state, clock, and negative existence. | dependency matrix | adapter job inputs | adapter job inputs | adapter job inputs | CORE drives one drift fixture per cell. Runtime job-spec hash is an added adapter dependency. |
| SP-070 | 206-213 | CLI command set, impact schemas, staging and archive mechanics, no live Claude write, explicit untested stamp. | command/API/package | Hermes projection | Claude projection | Codex projection | CHANGED: command semantics are core API; runtime CLI wrappers are generated. No live runtime write anywhere. |
| SP-071 | 212 | Validated export writes unsandboxed label and scores; normalized archive; staged/archive path-byte equality. | package/claim | projection | projection | projection | CORE. Label comes from capability report, not hardcoded Claude assumption. |
| SP-072 | 213 | Untested route token plus action-time approval and four untested labels. | package/approval record | native gate | native gate | native gate | CORE mechanical guard plus adapter human approval. Token alone is insufficient. |
| SP-073 | 217-227 | Per-iteration orchestration procedure and exactly one DONE delivery route; human installs. | workflow contract | Kanban/delegate | skill/fork | sandbox/multi-agent | CHANGED: orchestration is adapter-owned, lifecycle order is core-owned. |
| SP-074 | 219-223 | Use 2+ independent rollout workers or none, prompt text only, fresh confirm workers, main role produces JSON. | job policy | delegate batch | fork/jobs | multi-agent/jobs | CHANGED: core requires independent job identities and immutable inputs; exact worker count is adapter policy, default 2+ or sequential fresh jobs. |
| SP-075 | 224-227 | Validated route default; untested only on action-time approval before test preparation; install by human. | route/approval | translate | translate | translate | CORE. |
| SP-076 | 229 | Preflight checks prompt-only input, no held-out answer read, PURPOSE citations, and current approval. | conformance/approval | prove/label | prove/label | prove/label | CHANGED: runtime evidence and negative tests replace self-attestation where possible; unresolved boundaries remain labelled. |
| SP-077 | 233-240 | Gate 1 paths, splits, sampling, wiki, snapshots, transactions, phase, scoring, and provenance tests. | conformance | adapter suite | adapter suite | adapter suite | CORE deterministic suite plus per-runtime boundary tests. |
| SP-078 | 236 | Wiki negative fixtures and tuple equality wording. | conformance | none | none | none | CHANGED as SP-068 to align tests with binding grammar. |
| SP-079 | 237 | Crash fixture for each crash point; no-extra-temp equality; pending-transaction refusal; status no-write. | conformance | none | none | none | CORE, expanded for intent-first protocol. |
| SP-080 | 238 | Every command refused outside allowed phase; P1-P23; K=0 refusal; reset and provisional errors. | conformance | wrapper parity | wrapper parity | wrapper parity | CORE. Add optional-seed phase cases. |
| SP-081 | 239 | Extractor/scorer error fixtures, strict greater-than sequences, untouched skill preservation, rejection leaves active skill and wiki hashes unchanged. | conformance | none | none | none | CORE. |
| SP-082 | 240 | Marker propagation fixtures, correct prediction equality allowed, copied record rejected, paraphrase limitation explicit. | conformance/claim | capture | capture | capture | CORE. |
| SP-083 | 241 | Export/package refusal, route exclusivity, staging idempotency, sweep, manifest regeneration, archive normalization and tamper detection. | conformance/package | projection | projection | projection | CORE. Runtime install roots are explicitly outside tests. |
| SP-084 | 242 | Command preflight once on toy domains, branch-exclusive paths in fresh domains. | conformance | Hermes smoke | later smoke | later smoke | CORE fixtures plus adapter smoke. |
| SP-085 | 243 | Real arithmetic smoke, mechanical pass, nondeterministic scores reported, Gate 2 deterministic mismatch failure. | smoke/claim policy | execute first | later | later | CORE criteria, adapter run. No performance claim. |
| SP-086 | 244 | Fixed delivery order: checks, verification pointer, sweep, manifest, scans, staged hash, read-only Gate 2, archive equality, freeze, no post-hash writes. | package pipeline | stage | stage | stage | CORE. Publication remains later. |
| SP-087 | 244 | Description, version/date, license, references, no em dashes. | package lint | projection | projection | projection | CORE package lint. Runtime metadata may add only generated fields. |
| SP-088 | 245 | Task Observer observation for reusable build signals with live log numbering. | integration event | optional explicit handoff | optional | optional | CHANGED: not automatic from core. Separate Task Observer procedure owns shared-log mutation and approvals. |
| SP-089 | 247-256 | Codex Gates 0a, 0b, 1, 2; external reports; fresh domains; deterministic/report-only triage. | validation governance | Kanban review | projection review | Codex review | CHANGED: Gate 0 architecture/source, Gate 1 core+adapter, Gate 2 staged package. Codex is evidence lane, not semantic owner. |
| SP-090 | 249 | Historical Codex CLI mechanics and external audit directory. | evidence locator | job config | none | gate runner | CHANGED: current installed CLI contract and OpenAI routing govern execution; historical flags are not permanent core semantics. |
| SP-091 | 258-260 | Do not modify Task Observer. | boundary | enforce | enforce | enforce | EXCLUDED from write scope by direct decision. |
| SP-092 | 261 | Skill retrieval or triggering. | none | none | none | none | EXCLUDED: paper did not evaluate it; not needed for evolution v1. |
| SP-093 | 262 | Wiki pruning or archival. | none | none | none | none | EXCLUDED: paper limitation and persistence requirement. |
| SP-094 | 263 | Live session transcript mining. | reject source | reject | reject | reject | EXCLUDED by direct decision. |
| SP-095 | 264 | Three independent runs and paired bootstrap in local v1. | claim policy | none | none | none | GATE A A2: excluded from local gate by default, required for paper-comparable public claims. |
| SP-096 | 265 | Sandboxed subagents or full event streams unavailable in Claude plan. | capability labels | prove/label | prove/label | prove/label | CHANGED: not globally excluded; adapters may earn stronger capability through runtime evidence. |
| SP-097 | 266 | Artifact-producing and environment-interactive domains. | schema refusal | refuse | refuse | refuse | GATE A A3; excluded by recommended v1. |
| SP-098 | 267 | Mechanical proof of commandness, root-cause adequacy, semantic dedup, generalizability. | judgment labels | role attests | role attests | role attests | EXCLUDED as mechanical claims; recorded as semantic judgments. |
| SP-099 | 269-285 | Reconciliation history and claims that all Round 7 changes were adopted. | provenance only | display | display | display | CHANGED: history retained; closure corrected to 1 textual close, 4 partial, 5 operationally unverified. |
| SP-100 | 283 | Unparseable train with raw cannot arise. | recovery rule | none | none | none | CHANGED: it can arise after corruption. Reset atomically deletes all derived raw/aliases for the phase, then corrected ingest recreates them. |
| SP-101 | 283 | Observation seeding is ordinary k=0 apply-wiki. | lifecycle | approval | approval | approval | CHANGED: explicit `seed-observations` transition in `NEEDS_OPTIONAL_SEED`, with rollback before baseline. |
| SP-102 | 287 | Paper locator checklist and source fidelity. | provenance tests | none | none | none | CORE source checks, using locked current extraction locators rather than stale historical line numbers. |
| SP-103 | current control | One shared core, Hermes first, thin Claude/Codex adapters. | all semantics | first adapter | later adapter | later adapter | CORE architecture mandate. No three implementations. |
| SP-104 | current control | OpenAI-backed providers only. | provider policy | `openai-codex` allowlist | dormant unless OpenAI-backed | native OpenAI allowlist | CHANGED relative to Claude-only plan. No implicit fallback. |
| SP-105 | current control | No paid services. | no network/service dependencies | refuse new paid route | refuse | refuse | CORE/control-plane constraint. Existing local runtime access does not authorize a new charge. |
| SP-106 | current control | No live installation, code, publication, or distribution during architecture. | no live-write API | no `skill_manage` live write | no install | no install | Retained non-authorization. Architecture outputs only. |

## Coverage assertion

The matrix covers Revision 8 substantive ranges 1-287 through status, scope, fidelity, paper facts, Task Observer composition, package layout, every schema family, every transition family, P1-P23, transaction and crash rules, pattern and attestation grammar, dependency rows, command and procedure contracts, all verification gates, all stated exclusions, and the reconciliation section. It also maps the four packet-v2 contradictions and current Hermes-first controls.

No row claims implementation or test completion.
