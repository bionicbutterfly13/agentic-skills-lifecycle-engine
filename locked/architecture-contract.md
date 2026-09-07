# Portable WikiSkill architecture contract

Status: PROPOSED FOR GATE A. No implementation, installation, publication, or distribution is authorized.

Canonical intake: `source-of-truth-packet-v2.md`, SHA-256 `699bf60f7e7975a58ae23c7a2daafb9236a9ecefa397bb83c27c3f3868e04e68`.
Governing historical proposal: Revision 8, SHA-256 `04fdf55687de91e67b92ed739a6691904880925417f114ad67640d55d4460bf9`.
Historical validation status: `NEEDS REVISION`. Revision 8 has no Codex plan review and no `SOUND` verdict.

## 1. Architectural decision

Build one runtime-neutral WikiSkill core and project it into Hermes, Claude Code, and Codex through thin adapters. Hermes is the first executable orchestration target. Claude and Codex adapters may translate discovery, invocation, tool, transcript, and approval surfaces, but may not duplicate lifecycle semantics or persistence logic.

The core owns evidence, schemas, deterministic state, transactions, validation, provenance, packaging inputs, and conformance fixtures. An adapter owns only runtime discovery metadata, task dispatch, capability measurement, transcript normalization, approval translation, and runtime-specific staging. No adapter owns a fork of the state machine.

This contract deliberately changes four unresolved Revision 8 mechanics before implementation:

1. Record transaction intent before creating any object in a core-owned root. This removes unowned pre-transaction residue.
2. Reset of a corrupt or unparseable train manifest deletes every derived train artifact for that phase, including raw traces and aliases, while retaining submitted `.out.md` files for correction. This gives one owner for raw evidence.
3. Add a real, one-time `seed-observations` transition before baseline. It is optional, transaction-bound, provenance-bearing, and reversible before baseline finalization.
4. Make Gate 1 use multiset terminology and add explicit missing-class, blank-reason, duplicate-tuple, and trailing-JSON negative fixtures.

These changes close the four textual contradictions identified in packet v2. They do not claim runtime correctness.

## 2. Source-of-truth hierarchy

Apply the first applicable source, without allowing a lower source to rewrite a higher one:

1. Dr. Mani's active direct instruction and action-time approval record.
2. Gate A decisions and later approved architecture decision records for this system.
3. This architecture contract and its two companion matrices.
4. The WikiSkill paper for claims about the paper's method, results, scope, limitations, and CC BY 4.0 source material.
5. Original Codex reports for Codex finding identity, severity, and historical closure state.
6. Verified runtime documentation and installed-runtime behavior for current Hermes, Claude, and Codex capabilities.
7. Executed conformance, validation, recovery, and packaging evidence for what the implementation actually does.
8. Revision 8 for the text of the final Claude proposal only.
9. Derived audits and memory as navigation aids only.

Every normative requirement record must carry `source_class`, `source_locator`, `decision_status`, and `supersedes`. Allowed `source_class` values are `DIRECT`, `GATE_A`, `ARCHITECTURE`, `PAPER`, `CODEX`, `RUNTIME`, `PLAN_PROPOSAL`, and `TEST_EVIDENCE`.

## 3. Current runtime facts and portability boundary

### 3.1 Installed versions inspected

- Hermes Agent `v0.20.5 (2026.8.19)`, upstream `8ca812fe`, local `aae27234` with carried commits.
- Claude Code `2.1.251`.
- Codex CLI `0.151.0`.

These versions are evidence baselines, not permanent compatibility promises.

### 3.2 Shared agentskills baseline

The portable package uses the agentskills-compatible minimum:

- one required `SKILL.md`;
- YAML frontmatter with canonical `name`, `description`, semantic `version`, license, and package metadata;
- Markdown procedure;
- optional `references/`, `scripts/`, `assets/`, `templates/`, and `examples/` resources;
- relative references that close inside the canonical package;
- a canonical manifest containing every package file and hash.

Runtime-only frontmatter is generated into adapter projections. It is not inserted into the canonical semantic package unless all supported runtimes accept it without changing behavior.

### 3.3 Verified runtime differences

Hermes:

- Skills are progressively disclosed through metadata, `skill_view`, and support-file reads.
- Local, external, and trusted project skill roots have explicit precedence.
- `skill_manage` can stage skill writes when `skills.write_approval` is enabled; skill writes always stage under that gate.
- Kanban is durable and task-scoped; `delegate_task` is process-local and non-durable.
- Delegated children have fresh context, inherit parent toolsets, and cannot grant themselves new toolsets.
- Current Hermes skill creation accepts package support directories and supplies profile-scoped skill roots.

Claude Code:

- Skills use `.claude/skills/<name>/SKILL.md` or plugin `skills/` projections.
- Claude supports `disable-model-invocation`, `user-invocable`, `allowed-tools`, `context: fork`, and `agent` metadata.
- `allowed-tools` is permission metadata, not proof of filesystem non-observation.
- `context: fork` isolates conversation context, not necessarily all filesystem or answer access.
- `--restricted` can narrow file and command surfaces, but the adapter must prove the exact launched mode before claiming enforcement.

Codex:

- The installed CLI discovers configured skills, including shared `.agents/skills` entries and configured skill paths.
- The installed CLI exposes sandbox modes, approval policies, stable hooks, plugins, multi-agent capability, and skill search.
- Workspace roots and permission profiles are runtime controls, but a skill description cannot prove they were active for a specific rollout.
- The canonical portable package may live in `.agents/skills`; Codex-specific projection and plugin metadata remain adapter-owned.

### 3.4 Task Observer relation

Task Observer remains a separate system and is not modified.

- Task Observer discovers reusable signals from live work and reviewed observations.
- WikiSkill compiles declared task-set rollouts, never implicit live-session capture.
- Task Observer's validated optimization remains one profile, one target skill, reviewed observations only, hidden validation, strict held-out improvement with no regression, and `ACCEPT_FOR_HUMAN_REVIEW` only.
- WikiSkill promotion does not equal Task Observer acceptance, skill installation, publication, or distribution.
- Named Task Observer observations may enter WikiSkill only through the explicit pre-baseline seed transition and only after a human names the literal observation IDs and target domain.
- Routine WikiSkill telemetry stays in WikiSkill state and logs. Only reusable methodology signals are eligible for Task Observer observations.

## 4. Component architecture

```text
Declared task set + answers + approved optional observation IDs
                         |
                         v
+---------------------------------------------------------------+
| Runtime-neutral core                                           |
| schemas | seals | state machine | txn/recovery | scoring       |
| traces | wiki | snapshots | validation | provenance | package |
+---------------------------------------------------------------+
          ^                    ^                    ^
          | typed port         | typed port         | typed port
+---------+--------+  +--------+---------+  +-------+----------+
| Hermes adapter   |  | Claude adapter  |  | Codex adapter    |
| Kanban/delegate  |  | skill/fork/tools|  | skill/sandbox    |
| skill approvals  |  | permissions     |  | hooks/approvals  |
+------------------+  +-----------------+  +------------------+
          |
          v
Staging candidate -> human install gate -> optional distribution gate
```

### 4.1 Core modules

Engineering may choose file names, but these ownership boundaries are binding:

1. `contract`: versioned schemas, enums, source labels, capability labels, and invariants.
2. `domain`: declared task and answer ingestion, split validation, seal creation, drift checks.
3. `evidence`: runtime event normalization, output binding, trace fidelity labels, provenance markers.
4. `lifecycle`: total state machine and command preconditions.
5. `transaction`: intent-first transaction records, replay, cleanup, equality oracle.
6. `wiki`: sampling, mechanical pattern grammar, attestations, index replacement, log and impact history.
7. `skills`: immutable snapshots, candidate construction, strict promotion, rollback, pointer and mirror rules.
8. `evaluation`: extractor and scorer subprocess contracts, invalid-evidence handling, aggregate scores.
9. `package`: canonical manifest, staged tree, archive grammar, hashes, compatibility metadata.
10. `conformance`: runtime-neutral fixtures and adapter capability tests.

The core must not import Hermes, Claude, or Codex modules; read their live config; invoke a model; call a network service; write to a live runtime skill directory; or infer approval from conversation prose.

### 4.2 Adapter port

Each adapter implements the following conceptual operations with typed request and result records:

- `discover_capabilities(runtime_version) -> CapabilityReport`
- `prepare_rollout(RolloutSpec) -> RuntimeJobSpec[]`
- `dispatch_rollouts(RuntimeJobSpec[]) -> RuntimeJobHandle[]`
- `collect_rollout(RuntimeJobHandle) -> CapturedExecution`
- `run_role(RoleSpec) -> RoleExecution`
- `request_phase_approval(ApprovalRequest) -> ApprovalRecord | NoDecision`
- `stage_skill(CanonicalPackage, Route) -> StagedProjection`
- `verify_projection(StagedProjection) -> ProjectionReport`

No adapter may directly mutate core state. It submits immutable results to core commands. The core validates hashes and performs the transition.

## 5. Canonical data contracts

### 5.1 Capability report

Required fields:

```text
runtime_id, runtime_version, adapter_version, observed_at
model_provider, model_id, provider_is_openai_backed
conversation_isolation: enforced | procedural | none | unknown
filesystem_isolation: enforced | procedural | none | unknown
tool_isolation: enforced | procedural | none | unknown
held_out_answer_isolation: enforced | procedural | none | unknown
wiki_isolation: enforced | procedural | none | unknown
trace_fidelity: paper_complete | observable_transcript | final_only | unknown
captured_events[]
approval_surface[]
write_roots[]
network_policy
claims_allowed[]
claims_forbidden[]
evidence[]
```

A capability is `enforced` only when a runtime control and a negative conformance test prove it for the exact launched configuration. Prompt instructions alone are `procedural`. Missing evidence is `unknown`, never upgraded by analogy.

### 5.2 Declared task records

Task and answer files remain separate. Required task fields are `task_id` and `input`. Required answer fields are `task_id`, `expected`, and split marker. Train, validation, and test are nonempty and disjoint by task ID and normalized input-content hash.

The adapter receives a `RolloutSpec` containing task input, rendered prompt, active skill content, tool profile, runtime policy, and expected capture schema. It never receives the expected answer, answer-file path, wiki path for inference, or another split's records.

### 5.3 Captured execution and result binding

`CapturedExecution` contains:

```text
execution_id, runtime_id, runtime_version, adapter_version
job_spec_hash, prompt_hash, active_snapshot_hash
started, finished, termination
captured_events[], returned_output, returned_output_hash
trace_fidelity, isolation_labels, capability_report_hash
```

The core derives prediction only from `returned_output`. Extractor timeout, nonzero exit, malformed output, empty output, or ambiguous output marks the task evidence invalid. Scorer timeout, nonzero exit, non-finite value, or value outside `[0,1]` also marks evidence invalid. Infrastructure failure never becomes a numeric score.

### 5.4 Provenance classes

Keep these classes physically and logically distinct:

- source paper text and prompts;
- direct product decisions and approval records;
- original Codex reports;
- historical plan proposals;
- declared tasks and answers;
- runtime-captured outputs;
- derived traces and wiki pages;
- candidate skill snapshots;
- staged runtime projections;
- executed validation evidence.

Every derived artifact carries source hashes, producer version, runtime and adapter identity when applicable, and the governing contract version.

## 6. Capability and threat model

### 6.1 Trusted components

- Local user and explicit approval records.
- Core code after Engineering review and executed tests.
- Declared extractor and scorer only within the Gate A-approved trusted-domain v1 if Gate A approves that scope.
- Runtime binaries only for the behavior actually measured by conformance tests.

### 6.2 Untrusted or fallible components

- Model outputs, including Maintainer and Proposer JSON.
- Task inputs and returned transcripts.
- Skill instructions and runtime metadata.
- Plug-ins, hooks, and external skill directories unless separately reviewed.
- Filesystem state that can drift, contain symlinks, or be concurrently modified.
- Adapter self-reports without runtime evidence.
- Nondeterministic evaluation outcomes.

### 6.3 Threats and controls

| Threat | Required control |
|---|---|
| Held-out answer leakage | Separate roots, adapter omission, marker propagation tests, runtime-specific negative access test, truthful label |
| Wiki leakage into inference | Omit wiki from job spec, restrict runtime roots when supported, negative access test, truthful label |
| Prompt or trace injection | Treat content as data, schema-validate role outputs, no control instructions from task content |
| Symlink/path escape | Identifier grammar, normalized paths, realpath containment, reject symlinks and unsafe archive members |
| Concurrent or partial writes | Per-domain lock, intent-first transaction, atomic replace, idempotent replay, whole-root equality oracle |
| Score manipulation | Output-hash binding, trusted extractor/scorer seal, timeout, finite range, fail closed |
| Provenance laundering | Source class and locator on every requirement, immutable original sources, distinct derived artifacts |
| Adapter semantic drift | Generated adapters, canonical manifest hash, cross-runtime conformance suite, no handwritten semantic copies |
| Unapproved live mutation | Core cannot write live skill roots; staged projections only; runtime-native approval plus human gate |
| Paid or non-OpenAI routing | Provider allowlist checked before dispatch; no fallback to a disallowed provider; no network service in core |
| Public overclaim | Claim policy separates local acceptance from paper comparative evidence and blocks unsupported fidelity labels |

## 7. Fidelity and isolation policy

Until a Gate A choice raises the floor, the proposed default is truthful degradation:

- `paper_complete` means reasoning, tool calls, tool outputs, and final answer are all captured and bound.
- `observable_transcript` means the runtime-visible subset is captured and enumerated.
- `final_only` means only returned final text is captured.
- `unsandboxed` is mandatory when any relevant isolation boundary is procedural, absent, or unknown.
- `unseen` is forbidden unless held-out answer inaccessibility is enforced and negatively tested for that run configuration.

Hermes v0.20.5 default adapter label: `observable_transcript`, `unsandboxed`, because delegated children inherit parent toolsets and adapter-level per-child capability reduction is not established.

Claude Code 2.1.251 default adapter label: `observable_transcript`, `unsandboxed`. `context: fork` is context isolation, not filesystem proof. A restricted-mode projection may earn narrower claims only after conformance tests.

Codex CLI 0.151.0 default adapter label: `observable_transcript`, `unsandboxed` unless the exact sandbox, workspace roots, permission profile, and negative access tests are recorded. Sandbox mode alone does not prove answer and wiki separation if both are inside allowed roots.

## 8. Lifecycle state machine

### 8.1 States

```text
UNINITIALIZED
NEEDS_OPTIONAL_SEED
NEEDS_BASELINE_RUN
NEEDS_TRAIN_RUN
NEEDS_WIKI
NEEDS_PROPOSAL
NEEDS_VAL_RUN
NEEDS_GATE
NEEDS_VAL_CONFIRM
DONE
```

`NEEDS_OPTIONAL_SEED` permits exactly one of `seed-observations` or `skip-seed`. No other pre-baseline path exists.

### 8.2 Required transitions

| Operation | From | Required result |
|---|---|---|
| `init` | UNINITIALIZED | seal, empty snapshot, `NEEDS_OPTIONAL_SEED` |
| `seed-observations` | NEEDS_OPTIONAL_SEED | transaction-bound pages/index/log with named observation provenance, then `NEEDS_BASELINE_RUN` |
| `skip-seed` | NEEDS_OPTIONAL_SEED | approval-independent no-seed record, then `NEEDS_BASELINE_RUN` |
| baseline prepare/ingest/finalize | NEEDS_BASELINE_RUN | invalid stays; valid sets `R_best`; perfect baseline goes DONE; otherwise k=1 train |
| train prepare/ingest | NEEDS_TRAIN_RUN | valid manifest and raw publication lead to NEEDS_WIKI; invalid stays |
| sample/apply-wiki | NEEDS_WIKI | sampled input, validated attestation, persistent wiki, consume train, NEEDS_PROPOSAL |
| proposer-context/apply-proposal | NEEDS_PROPOSAL | create/patch to candidate and NEEDS_VAL_RUN; no-action advances k |
| val prepare/ingest/gate | NEEDS_VAL_RUN then NEEDS_GATE | non-win rejects; strict win becomes provisional and NEEDS_VAL_CONFIRM |
| confirm prepare/ingest/gate | NEEDS_VAL_CONFIRM then NEEDS_GATE | accept only if both aggregates exceed prior best; otherwise reject; advance k |
| abandon | candidate-bearing states | consume or delete owned manifests, reject candidate, advance k |
| test prepare/ingest | DONE, validated route only | immutable test evidence, state remains DONE |
| export | DONE, validated route | staged candidate only, never install |
| package-untested | DONE, untested route plus action-time approval | explicitly untested staged candidate only, never install |
| reset-manifest | owning phase, invalid or unparseable and unconsumed only | delete manifest, sidecars, derived raw/aliases for train; keep `.out.md`; same phase |
| recover | any state with transaction | replay or clean exactly the owned plan |
| status | any | read-only |

Every operation not listed for a state is refused. Every error path has a stable error class and leaves state and owned roots byte-identical unless a pending transaction is intentionally recoverable.

### 8.3 Paper and local rule separation

Paper rules retained as paper facts:

- empty skill and wiki baseline;
- active skills injected into inference;
- wiki excluded from training inference;
- sample limits 5 failures, 3 passes, 15,000 characters per trace view;
- Maintainer then Proposer order;
- Proposer reads at least four traces when proposing a change;
- one create, patch, or no-action proposal;
- strict aggregate `>` acceptance;
- rejected candidate rolls back skills only, never wiki;
- impact history persists;
- train, validation, and test remain disjoint.

Local rules are labelled `ARCHITECTURE` or `GATE_A`, including deterministic sort order, confirmation, transaction format, markers, snapshots, delivery routes, package grammar, and runtime adapters.

## 9. Deterministic transactions and recovery

### 9.1 Intent-first protocol

For every state-changing operation:

1. Acquire the per-domain lock.
2. Verify seal, state, arguments, preconditions, negative-existence predicates, and all dynamic input hashes.
3. Derive a deterministic transaction ID from operation, state revision, arguments, and input hashes.
4. Atomically write `state.txn` before creating any file or directory in a core-owned mutable or content-addressed root.
5. The transaction record contains immutable replay inputs or embedded output bytes, deterministic temp names, planned deletions, planned entry IDs, planned target roots, and planned next state.
6. Materialize outputs in write order. Large objects are rebuilt from immutable replay inputs or copied from a transaction-owned temp path named in the record, then published by hash.
7. Atomically commit pointer, route, ledger, consumption, and next-state changes in one final state write that clears `txn`.
8. Release the lock.

No object may be published before step 4. This supersedes Revision 8's prepublication-before-transaction rule.

### 9.2 Recovery

`recover` is eligible whenever `txn` is present. A separate startup cleanup may delete deterministic transaction temp paths whose transaction is absent only when their names and ownership can be proven from the domain namespace. It may not garbage-collect arbitrary content-addressed objects.

Recovery is idempotent and needs no mutable external input. It either completes the recorded transaction or returns a fail-closed corruption result without changing authoritative pointers.

### 9.3 Equality oracle

With a fixed clock, crash-then-recover must equal uninterrupted execution across:

- the whole domain tree excluding the lock file and transaction temp roots;
- parsed state excluding only the transient `txn` field, canonically serialized;
- snapshot roots, active pointer, and disposable mirror;
- raw traces and aliases;
- wiki, logs, and impact history with no duplicate entry IDs;
- staging and archive roots, with no extra temp entries;
- route and delivery ledger.

Every declared crash point and every state-changing operation receives an equality fixture. Pre-intent, post-intent, first-output, mid-output, publication, and pre-commit boundaries must be represented where applicable.

## 10. Validation gates

### Gate 0: architecture and source integrity

- Verify source hashes and provenance inventory.
- Verify every binding Revision 8 rule is mapped in `source-parity-matrix.md`.
- Verify all HF-A01 through HF-A27 are mapped in `acceptance-matrix.md`.
- Record Gate A choices and consequences.
- Independent Architect review required before Engineering.

### Gate 1: deterministic core and adapter conformance

- Schema, path, split, seal, drift, and symlink tests.
- Output binding and fail-closed extractor/scorer tests.
- Complete state transition, invalid, reset, abandon, terminal, route, and refusal fixtures.
- Intent-first crash recovery equality for every owned root.
- Snapshot, pointer, mirror, and corruption tests.
- Sampling limits and deterministic-local ordering tests.
- Mechanical pattern grammar and semantic-judgment separation.
- Explicit missing-class, blank-reason, duplicate-tuple, trailing-JSON, and multiset fixtures.
- Marker collision, legal correct-answer, copied-record, and paraphrase-limit fixtures.
- Dependency drift fixture for every matrix cell.
- Staging and archive path-byte equality tests.
- Adapter capability tests for actual versions and launch modes.
- OpenAI provider allowlist and forbidden-fallback tests.
- Core network prohibition test.

### Gate 2: staged package review

- Read-only staged tree bound to canonical package and adapter hashes.
- Every reference exists; no secret or nonportable path; no build residue.
- License and attribution files match Gate A.
- Runtime projection contains no independent lifecycle semantics.
- Deterministic bindings must match and fail on mismatch.
- Nondeterministic LLM outcomes are report-only unless a deterministic fixture governs them.
- No archive or staged-tree mutation after the reviewed hash.

### Gate 3: installation

Separate action-time human approval per runtime and target profile. Installation reads the Gate 2 report, exact hashes, destination, rollback bundle, and compatibility report. No blanket approval across runtimes.

### Gate 4: publication or distribution

Separate action-time human approval after licensing, private-data, attribution, and redistribution review. Gate 3 does not imply Gate 4.

## 11. Hermes-first orchestration

Hermes is the control plane, not part of the core state machine.

1. One durable Kanban parent card represents an evolution run and carries project, corpus, subsystem, workspace, and exclusions.
2. Phase cards depend on prior durable artifacts. A phase that cannot safely replay from core state must not be delegated.
3. Independent task rollouts may use `delegate_task` inside the active worker only when losing the child on session/process stop is acceptable and the parent can deterministically retry by immutable job ID.
4. Durable cross-profile work, review, and approvals use Kanban, not delegation.
5. Each child receives only goal, immutable job spec, prompt text, output destination contract, and prohibitions. No hidden conversation context is assumed.
6. The Hermes adapter collects only returned summaries or explicitly observable events and records the actual capture class.
7. Skill mutation uses staged canonical packages. If `skills.write_approval` is enabled, `skill_manage` must produce a pending write and human review. Regardless of config, WikiSkill itself never calls `skill_manage` against a live skill during evolution.
8. Engineering and review are different Kanban cards or same-card review lifecycle according to the pre-created task graph. The implementation worker cannot self-approve.
9. Per-task model routing must explicitly set an allowed OpenAI-backed provider and model. No implicit provider fallback.
10. No paid API or service may be introduced. If execution would incur a new paid charge, the phase blocks before dispatch.

## 12. Claude adapter

The Claude adapter is a generated projection containing:

- Claude-compatible frontmatter and invocation metadata;
- optional `context: fork` and least-privilege `allowed-tools` declarations;
- a launcher or procedure that passes only the immutable core job spec and prompt text;
- result normalization into `CapturedExecution`;
- capability report generation and truthful labels;
- staging only, never direct installation.

It may not embed the core state machine in `SKILL.md`, assume `allowed-tools` proves filesystem isolation, claim paper-complete traces, or run while the OpenAI-only routing control is active unless the exact Claude runtime session is demonstrably backed by an approved OpenAI provider. With the inspected native Claude Code configuration, execution is therefore dormant under the current OpenAI-only control; only static projection and conformance review are allowed.

## 13. Codex adapter

The Codex adapter is a generated projection containing:

- agentskills-compatible metadata for configured `.agents/skills` or Codex projection roots;
- explicit sandbox, approval, workspace-root, hook, and model-provider requirements;
- a launcher or procedure that passes only the immutable job spec and prompt text;
- result normalization into `CapturedExecution`;
- capability evidence for the exact CLI version and launch flags;
- staging only, never direct installation.

Codex sandbox and workspace permissions must keep answer and wiki roots outside rollout-visible roots to earn enforced isolation. Hook presence is not coverage; trusted hook state and negative access tests are required. Native Codex is compatible with the OpenAI-only routing constraint when its provider and model identity are recorded and allowed.

## 14. Package, update, and compatibility contract

### 14.1 Canonical package

The canonical package includes:

- semantic `SKILL.md`;
- source and adaptation attribution;
- license files selected at Gate A;
- canonical `bundle-manifest.json` with schema version and per-file SHA-256;
- core schemas and compatibility declaration;
- references and templates;
- implementation and test assets after Engineering;
- adapter generator inputs, not installed adapter copies.

### 14.2 Versions

Track independently:

- `contract_version` for schemas and lifecycle;
- `core_version` for implementation;
- `package_version` for semantic skill content;
- `adapter_version` per runtime;
- `runtime_min_tested`, `runtime_max_tested`, and exact `runtime_tested` values.

Use semantic versioning. A breaking schema or state-machine change requires a contract major version and an explicit migration. Runtime versions outside the tested range are `unknown`, not silently supported.

### 14.3 Update rules

- Generate projections deterministically from one canonical package.
- Refuse overwrite when a live projection's recorded canonical hash differs from the expected previous hash.
- Preserve a complete rollback bundle.
- Run migration against a copy, then replay and equality tests before staging.
- Never update three semantic copies independently.
- Installation, replacement, deletion of old copies, and publication remain separate approvals.

## 15. Provenance and licensing

- The paper is CC BY 4.0 and must be attributed by title, authors, arXiv ID, version, and adaptation notice when paper material is redistributed.
- Verbatim paper prompts, if Gate A permits redistribution, remain clearly marked source material under CC BY 4.0 and separate from local instructions.
- Original transcript, original Codex reports, and historical plan are read-only evidence and are not packaged by default.
- New core and adapter code license is unresolved until Gate A.
- No source license is inferred for new code.
- Private paths, personal data, secrets, opaque signatures, and unnecessary process records are excluded from packages.

## 16. Gate A decisions for Dr. Mani

These five decisions are intentionally not assumed.

### A1. Fidelity floor

Recommended default: allow adapters with narrower evidence and procedural isolation only when labelled `observable_transcript` and `unsandboxed`; require enforced isolation for any `unseen` or paper-equivalent claim.

Consequence if approved: Hermes-first implementation can proceed with truthful limitations. Consequence if paper-complete capture is mandatory: Hermes, Claude, and Codex execution blocks until each runtime can capture the full event stream and enforce answer/wiki isolation.

Decision: [ ] approve recommended default  [ ] require paper-complete/enforced  [ ] revise

### A2. Local acceptance and public claims

Recommended default: local candidate acceptance requires strict aggregate improvement plus one fresh confirmation and no infrastructure-invalid evidence. Any public comparative-performance claim requires the paper's three complete runs and paired-bootstrap protocol or must explicitly disclaim comparability.

Consequence if approved: local evolution remains practical without laundering local confirmation into a paper-level claim. Consequence if rejected: specify the replacement local gate and public-evidence rule before Engineering.

Decision: [ ] approve recommended default  [ ] revise

### A3. Portable v1 task scope

Recommended default: approve trusted-domain, text-output tasks with `none|read` tool profiles; exclude artifact-producing and environment-interactive tasks until a later contract version.

Consequence if approved: core schemas can remain narrow and deterministic. Consequence if broadened: Gate 1 must add artifact identity, environment reset, side-effect isolation, and non-text scoring contracts before implementation.

Decision: [ ] approve recommended default  [ ] broaden with stated scope  [ ] revise

### A4. Licensing and prompt redistribution

Recommended default: license new shared-core and adapter code under MIT; license documentation and local methodology under CC BY 4.0; include verbatim paper prompts only in a separately attributed CC BY 4.0 source appendix, not mixed into original local prose.

Consequence if approved: package boundaries and notices are deterministic. Consequence if a private-only or different license is chosen: distribution remains blocked until package metadata and notices reflect it.

Decision: [ ] approve recommended default  [ ] choose other licenses  [ ] exclude verbatim prompts  [ ] revise

### A5. Implementation authorization

Recommended default: after independent contract review confirms all matrices, authorize Engineering to implement only the runtime-neutral core and Hermes adapter in an isolated worktree. Claude and Codex adapters remain subsequent conformance lanes. Installation and publication remain separately prohibited.

Consequence if approved: Engineering may execute the packet in section 17. Consequence if not approved: all work stops at architecture artifacts.

Decision: [ ] authorize bounded implementation  [ ] revise contract  [ ] reject implementation

## 17. Exact implementation packet for Engineering

### Architectural Decision

Implement one runtime-neutral WikiSkill core plus a Hermes adapter. Generate later runtime adapters from the same core contract. Do not port Revision 8 as a Claude-specific program and do not create runtime-specific state machines.

### Scope and affected areas

In scope:

- a new isolated project/worktree selected by Chief of Staff or Engineering;
- versioned core schemas and immutable records defined in this contract;
- deterministic lifecycle, intent-first transactions, recovery, snapshots, wiki, evaluation, and staging;
- Hermes Kanban/delegation orchestration adapter;
- adapter capability report and conformance fixtures;
- tests satisfying `acceptance-matrix.md` and Gate 1;
- documentation and separate staged package artifacts.

Out of scope:

- editing installed Task Observer;
- editing live Hermes, Claude, or Codex skills/config;
- live installation;
- Claude or Codex executable adapters before their later cards;
- publication or distribution;
- live transcript mining;
- retrieval, triggering, wiki pruning, or automated archival;
- artifact-producing or environment-interactive domains unless Gate A changes A3;
- paid services or non-OpenAI model routing.

### Contract and interface specification

- Implement the adapter port in section 4.2 and records in section 5.
- Keep the core free of runtime imports, model calls, network calls, and live skill-root writes.
- Make every state-changing command use section 9's intent-first protocol.
- Implement section 8's total transition table, including `seed-observations`, `skip-seed`, corrected reset/raw ownership, both delivery routes, and explicit refusal paths.
- Bind predictions to captured output hashes and fail closed on extractor/scorer failure.
- Keep paper facts, local architecture, Gate A decisions, runtime evidence, and Codex history separately labelled.
- Treat adapter labels as measured capability output, not configuration claims.

### Config and cartridge requirements

Generic core configuration:

- domain ID, K, prompt template, extractor, scorer, tool profile;
- declared task and answer sources;
- runtime adapter ID and version;
- allowed OpenAI provider/model list;
- timeouts, sampling limits, fixed-clock test input;
- staging root, with live skill roots forbidden;
- claim policy and Gate A decisions;
- license policy and prompt inclusion policy.

Project or domain cartridge:

- task/answer files and their hashes;
- domain-specific prompt template, extractor, and scorer;
- optional human-approved Task Observer observation IDs;
- runtime launch policy constrained by the generic schema.

Do not hardcode a client, domain, task corpus, offer, runtime path, model, or date into shared code.

### Constraints and failure modes

- No pre-transaction writes to owned roots.
- No repair-in-place after sealed input drift; create a new domain identity.
- No score from invalid infrastructure evidence.
- No candidate publication containing a provenance marker.
- No claim stronger than the recorded capability report.
- No provider fallback outside the allowed OpenAI list.
- No new paid dependency or service.
- No live install, publication, or distribution path in the core.
- A crash must be recoverable or fail closed without pointer change.
- A source or adapter hash mismatch blocks overwrite.

### Acceptance criteria and verification gates

1. All HF-A01 through HF-A27 pass with criterion-level evidence.
2. Every row in `source-parity-matrix.md` has an implementation disposition and test or review proof.
3. Gate 1 passes from a clean environment with no network.
4. Crash-then-recover equals uninterrupted execution for every state-changing operation and declared crash boundary.
5. Hermes adapter emits truthful capability labels and refuses disallowed provider/model routing.
6. A real bounded smoke domain reaches DONE or truthfully reports no accepted skill; nondeterministic scores are reported, not asserted.
7. Staged package hashes and archive member path-byte hashes agree.
8. No file under a live Hermes, Claude, Codex, or Task Observer skill/config root is modified.
9. Independent Architect review passes before any installation request.
10. Engineering hands off exact changed files, test commands and results, artifact hashes, residual risks, and rollback paths.

## 18. Criterion-level Gate A checklist

Gate A passes only when every item is checked and an approval record names the contract hashes:

- [ ] Historical status remains labelled `NEEDS REVISION`; no `SOUND` claim.
- [ ] Source plan and packet hashes match the locked values.
- [ ] One shared core and thin-adapter boundary approved.
- [ ] Source hierarchy approved.
- [ ] Task Observer remains distinct and unmodified.
- [ ] Declared task sets, not live sessions, are the only raw input source.
- [ ] Capability report and truthful fidelity labels approved.
- [ ] A1 fidelity-floor decision recorded.
- [ ] A2 local acceptance and public-claim decision recorded.
- [ ] A3 v1 task-scope decision recorded.
- [ ] A4 code/docs/prompt licensing decision recorded.
- [ ] A5 implementation authorization decision recorded.
- [ ] Intent-first transaction change approved.
- [ ] Corrupt train reset/raw ownership change approved.
- [ ] Real pre-baseline observation-seeding transition approved.
- [ ] Gate 1 class-coverage/multiset fixture correction approved.
- [ ] OpenAI-only routing and no-paid-services constraint approved.
- [ ] Claude execution remains dormant while it cannot satisfy OpenAI-only routing.
- [ ] Core is prohibited from network and live skill-root writes.
- [ ] Staging, installation, and publication are separate gates.
- [ ] Package/update compatibility contract approved.
- [ ] All 27 HF-A rows are present in `acceptance-matrix.md`.
- [ ] Every binding plan rule is mapped in `source-parity-matrix.md`.
- [ ] Independent Architect contract review is assigned before Engineering.
- [ ] No implementation, installation, or publication is inferred from Gate A unless A5 explicitly authorizes the bounded Engineering scope.

## 19. Evidence stop

This contract establishes a proposed system shape and Engineering-ready interfaces. It does not establish implementation correctness, runtime conformance, installation, publication, distribution, paper-equivalent traces, enforced isolation, or performance improvement.
