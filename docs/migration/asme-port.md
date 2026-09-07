# ASME compatibility port into Lifecycle

Status on September 6, 2026 (local date): **compatibility import independently verified, four of four quick-plan requirements pass; Git integration remains pending**.

The destination is the isolated `feat/asme-hermes-parity-port` branch, based on
Lifecycle integration commit `19375806a748db16e706c70f49aa3bc83b142eb0`. All 122
designated source paths have been imported; three current-facing documents have
exact historical copies. The full destination suite finished with two documentation
failures; their corrections passed all seven affected checks. Current evidence is in
[the verification receipt](../evidence/asme-port-verification.json).

## Settled, pending, and deferred

Settled: preserve the complete existing engine, the `asme` Python namespace and
command, the `agent-skill-mastery-engine` distribution, Python `>=3.11`, and package
version `0.2.0`. Lifecycle remains the current project identity. This compatibility
import does not rename the Python API or change inherited behavior.

Resolved: the prior generic credential-pattern flag at `src/asme/observer_bridge.py`
was an ordinary observer phase constant. The redacted AST review established that
it was not a credential. The resumed import checked all 122 imported source files,
bound the single benign match to that exact constant, and found no unresolved hit.

Pending: Git integration and clean task-owned worktree closeout. Verified feature
commits, integration, and safe task-owned cleanup are now explicitly authorized by
the adopted goal; they follow successful review. The broader goal
also authorizes strict WikiSkill v1 implementation in separate feature streams.

The existing `test_current_tree_is_community_scan_clean` initially failed in the destination:
`build_projection` includes GSD planning files, and the unchanged safety scanner
rejects the quick plan's private absolute paths. This is a real packaging integration
failure. Eleven authored plan references now use equivalent portable paths; all
nine referenced files resolve, and the unchanged test and scanner pass. The full
suite was run without deselection. The separate packaging feature will address the
broader distribution boundary while preserving scanning of distributable contents.

The current-facing PROVENANCE rewrite initially omitted two exact fenced records that
the source registry still locates at canonical anchors. The inherited reconstruction
test failed even though the historical copy preserved the original bytes. Both
records are now restored at their canonical anchors with explicit historical
authority context, and the reconstruction test passes. Both initial failures remain
in the full-suite receipt; inherited tests and source code are unchanged.

Deferred from this mechanical import: claims-policy repair, autonomous role
execution, Hermes dispatch, benchmark integration, and paper experiments. Paid
execution and publication need approval. Original-source deletion remains subject
to a fresh lossless salvage audit and explicit action-time authorization.

## Source identity and preservation contract

The audited source checkout is `agent-skill-mastery-engine`, pinned at
`1137c6705fd844546d5588757a5a23d4007b20c4`. The source was clean during preflight:
129 tracked paths, zero untracked paths, and 91 ignored file paths. Ignored paths
were counted by Git without reading their contents. The source baseline suite can
create ignored caches, so 91 is an observation at preflight, not a permanent total.

The manifest accounts for all 129 tracked paths:

| Disposition | Source paths | Preservation requirement |
|---|---:|---|
| Exact canonical copies | 119 | Exact pinned bytes and Git executable modes |
| Revised current documents with exact historical copies | 3 | README, PROVENANCE, CONTRIBUTING; both destinations hash-bound |
| Retain source planning maps at source | 7 | Record hashes, modes, and private-planning exclusion; do not publish the maps |
| Additional exact historical copies | 3 | Preserve source README, PROVENANCE, and CONTRIBUTING before revising their current counterparts |

The additional three files are historical destinations for already counted source
paths; they do not increase the 129-path source inventory. The seven retained maps
are `ARCHITECTURE.md`, `CONCERNS.md`, `CONVENTIONS.md`, `INTEGRATIONS.md`, `STACK.md`,
`STRUCTURE.md`, and `TESTING.md` under source `.planning/codebase/`.

The [source manifest](asme-source-manifest.json) covers each tracked path exactly
once with its source Git mode and SHA256, canonical destination or retained-at-source
disposition, and historical destination where needed. It accounts for 125 destination
files: 119 exact canonical copies, three revised documents, and three exact historical
copies. Source history and ignored material remain at source; their relative path
inventory and six local commit identities are recorded without copying ambient state.

The source has six local commits after public tip
`c79097aea0da803b84f4f75db7395063b98d0705`. Those local changes are part of the
requested pin. The public v0.2.0 release does not establish that the entire pinned
local tree was published. The final manifest must retain the exact commit identities
and ancestry; copying current files cannot preserve Git history by itself.

## What exact compatibility preserves

| Surface | Contract carried forward | Implication |
|---|---|---|
| Python and CLI | `src/asme`, `asme = asme.cli:main`, existing command arguments and JSON output | Existing consumers keep their identifiers |
| Packaging | `pyproject.toml`, `setup.py`, `MANIFEST.in`, source registry and skill assets | Editable and built-package skill lookup retain their current rules |
| Skill payload | SKILL, PURPOSE, references, templates, bundled arithmetic and echo cartridges | The shipped materials remain attributable to the exact source |
| Engine | Role contracts, wiki updates, proposals, evaluation, snapshots, dependencies, transactions, staging and recovery | The existing execution model remains testable in the new home |
| Tests | Every inherited test file and test case | A full destination suite can expose migration regressions without changing expected behavior |
| Hermes | One read-only capability tool; zero dispatch | Importing an adapter does not enable model execution |
| License and attribution | LICENSE, NOTICE, CITATION, provenance, and locked source documents | MIT code and CC BY 4.0 documentation terms remain intact |

The verifier independently enumerates the pinned Git tree rather than accepting a
manifest count as truth. It checks source bytes and modes, exact copies, approved
current-document hashes and links to their historical copies, complete coverage,
and containment without symlink traversal. Its 36 synthetic tests pass, including
deliberate missing mappings, duplicate entries, altered bytes and executable modes,
source drift, unsafe paths, and symlinks. Independent review exposed three additional
false-pass cases, all reproduced before repair: a Git subdirectory with an empty
receipt, a receipt overriding planning-file retention, and staged source changes
with unchanged working bytes. The verifier now requires the Git top level,
enumerates the full tree, enforces retention independently of receipt fields, and
compares every index path, mode, stage, and blob ID against the pin. The independent
reviewer reran all 36 tests successfully and confirmed valid/refused synthetic CLI
cases, finding no additional material defect in that bounded verifier review.
The resumed verifier passed against the actual 129-path source and all 125 destination
files. Its destination content digest is
`00ead34220eca190d1ebac8c06618b2551d97807f7fc762b237df2219dcc6a57`.
The digest covers manifest destinations, SHA256 values, and Git modes, encoded as
sorted compact JSON. The pre-repair digest and current-document hashes remain
recorded as historical observations. Independent comparison passed before and
after the repairs, reproducing this final digest without calling the verifier.

This manifest freezes the mechanical import. Once later authorized features change
inherited source files, run the preservation verifier against the recorded import
commit in an isolated checkout. Do not rewrite original source hashes to make a
modified engine appear byte-identical. Later studies must bind their own engine
version and content digest. The original source repository remains part of the
reproduction inputs; an import receipt does not authorize deleting it.

## Method coverage and inherited limits

Source `docs/implementation-parity.md` contains all 106 SP rows and all 27 HF-A
criteria. These are inherited implementation assertions, not fresh independent
verification or controlled paper replication. The SP ledger labels 93 rows
`IMPLEMENTED`, five `PARTIAL`, two `BLOCKED`, and six `EXCLUDED`. HF-A01 through
HF-A27 contain 26 historical `PASS` labels and one `POLICY-GATED` label.

Every inherited exception is listed below:

| Row | Historical label | Boundary recorded in the source |
|---|---|---|
| SP-033 | PARTIAL | Inventory exists; the old A4 license/release gate remains in the ledger |
| SP-035 | BLOCKED | Paper attribution exists; prompt and license decisions remain described as awaiting A4 |
| SP-085 | PARTIAL | Nondeterministic adapter runs remain pending |
| SP-086 | PARTIAL | Fresh independent review of the repaired frozen candidate and Gate 2 artifact remains pending |
| SP-087 | BLOCKED | Old release license/date gate remains in the ledger |
| SP-088 | EXCLUDED | Core never appends to the shared Task Observer log |
| SP-089 | PARTIAL | Fresh external Gates 0 and 1 review remains pending |
| SP-092 | EXCLUDED | Skill retrieval and trigger quality are outside evolution v1 |
| SP-093 | EXCLUDED | Wiki pruning and archival have no operation |
| SP-094 | EXCLUDED | Live transcript or session-handle input is absent |
| SP-097 | EXCLUDED | Artifact-producing and environment-interactive domains are rejected |
| SP-098 | EXCLUDED | Semantic quality is an attested judgment, not mechanically proved |
| SP-103 | PARTIAL | Claude and Codex adapters remain future work |
| HF-A25 | POLICY-GATED | Historical architecture, licensing, and bounded-development decisions |

The public release receipt and source LICENSE establish facts that some historical
license/publication descriptions predate. Preservation means retaining those
descriptions byte-for-byte, with a current contextual explanation. It does not mean
silently rewriting the source matrices or declaring their other gates closed.

An actual isolated PEP517 build also exposed an inherited distribution gap. The
wheel and sdist built successfully and every archived file passed the unchanged
community scanner. All 37 source Python/JSON files matched in both archives, and
all nine wheel skill files matched. The sdist omitted all 14 arithmetic/echo
evaluation asset files because the inherited MANIFEST includes asset templates
but not their JSON, JSONL and text companions. The source checkout import preserves
all 14 files. Those 14 are the measured `assets/eval` omission subset, not the
complete distribution omission population: linked migration/evidence JSON and
the undeclared `locked/` directory also require distribution-boundary review.
Their distribution repair belongs to the separate packaging feature;
this import does not silently alter MANIFEST or claim a complete distribution fix.
The verification receipt retains the initial artifact hashes and records the
completed post-repair rebuild. The final declared PEP517 build passed in 49.305
seconds. Its wheel has 53 members; its sdist has 117 regular files within 135 total
members. Independent inspection rechecked the full archive inventories and hashes,
the unchanged safety scanner, all 37 runtime/data files, the final canonical docs,
and all nine wheel skill files. The final wheel also installed into an isolated
task-local target using `pip --no-index --no-deps`. Fresh subprocesses loaded its
module and skill root from that target, matched all nine skill files, and passed
CLI help and transition-matrix checks. The initial and final CLI output hashes
match. No live host profile or provider was used.

HF-A26, SP-095, and the historical suite count cannot establish scientific efficacy.
Source `claims.py` accepts caller-supplied run and bootstrap metadata, and its public
claim path does not reject `isolation_label="scripted-offline-fixture"`.
`tests/test_bootstrap.py::test_three_run_paper_comparable_claim_passes_end_to_end`
explicitly expects such scripted evidence to produce `paper_comparable`.
That is an inherited policy defect, preserved for compatibility and requiring a
separate regression repair. The completed paper audit's V03 probe independently
reproduced acceptance with three scripted, final-only runs and a real bootstrap
calculation. That reproducer proves a policy defect; it supplies no model-efficacy
evidence. The defect is intentionally unchanged in this byte-preserving import.

The narrow follow-up is to reject explicitly scripted evidence for public
comparability while preserving local acceptance and bootstrap calculations. Broader
comparability still needs verified evidence origins, benchmark and model identities,
protocol bindings, independent runs, held-out access checks, and actual bootstrap
artifacts. Caller-supplied labels and positive fixture scores do not supply them.

## Hermes boundary

The inherited adapter registers `wikiskill_capabilities` with status
`staging_only_dispatch_disabled`. Historical Plugin Doctor results concern an older
Hermes 0.20.5 environment. They do not establish the current installed host state.

The orchestrator's current upstream source audit is pinned to
`693641aa8b4359c602283bdbbc14041e03bc47bc`. The public request lacks an atomic exact
provider/no-fallback constraint, and child execution begins before the caller gets
the handle in
[subagent_lifecycle.py](https://github.com/NousResearch/hermes-agent/blob/693641aa8b4359c602283bdbbc14041e03bc47bc/agent/subagent_lifecycle.py#L44-L55)
and its
[launch path](https://github.com/NousResearch/hermes-agent/blob/693641aa8b4359c602283bdbbc14041e03bc47bc/agent/subagent_lifecycle.py#L225-L260).
[Delegate configuration](https://github.com/NousResearch/hermes-agent/blob/693641aa8b4359c602283bdbbc14041e03bc47bc/tools/delegate_tool_config.py#L372-L459)
does not supply the missing per-request guarantee. Empty toolsets inherit tools in
[delegate_tool_toolsets.py](https://github.com/NousResearch/hermes-agent/blob/693641aa8b4359c602283bdbbc14041e03bc47bc/tools/delegate_tool_toolsets.py#L61-L103),
and an allowlist on the public LLM surface does not suppress capacity-error fallback
in [auxiliary_client.py](https://github.com/NousResearch/hermes-agent/blob/693641aa8b4359c602283bdbbc14041e03bc47bc/agent/auxiliary_client.py#L6305-L6345).

Dispatch therefore remains disabled. This is an upstream source audit and an
inherited adapter constraint. No live profile, installation, provider request, or
current installed-host experiment was performed for this port.

## Lifecycle work still required

The active autonomous goal is exclusively WikiSkill v1. The compatibility import
supplies existing components; the paper audit still requires role execution, full
trajectory handling, skill evolution, native Hermes integration, real benchmark
support, held-out protocol, statistical analysis, and ablations. Implementation
coverage and experiments actually run must be recorded separately.

The previously planned ten-phase Lifecycle program remains preserved as background,
outside this goal. This import does not complete or reopen it:

| Roadmap phase | Remaining proof or implementation |
|---|---|
| 1. Public Project Contract | Integrate canonical public documents and source-grounded claim boundaries |
| 2. Canonical Schemas and Identity | Validate Lifecycle-wide schemas and bind studies to exact engine bytes |
| 3. Event Ledger and Study Controller | Demonstrate append-only study events and bounded deterministic control |
| 4. Security Admission | Enforce independently checked, default-deny admission for first-study roles and candidates |
| 5. Evidence, Candidates, and State | Implement typed bounded SKILL.state, trial/arm resets, and validated state patches |
| 6. ASME Salvage | Finish the import, exhaustive comparison, history/nontracked accounting, and independent audit |
| 7. Daedalus Host Adapter | Build and verify the explicit reference adapter |
| 8. Synthetic k-NN Study Harness | Run the frozen CPU-local paired study with hidden variants and traps |
| 9. Evaluation and Lifecycle Decisions | Demonstrate abstention, study-local promotion, and fresh independent confirmation |
| 10. Open-Source Distribution | Verify installation, exact-version pinning, and common contracts across at least two hosts |

No roadmap requirement or phase is marked complete by this report. The ASME
arithmetic and echo fixtures do not substitute for the planned k-NN experiment.

## Effort and review implications

The plan deliberately exceeds the ordinary 15-file quick-task heuristic: its
original 136 declared paths include a coherent 122-file source import. Resumption
adds fourteen explicit evidence/checkpoint/plan paths, for 150 declared paths.
The work is measured in
executable units: preflight and privacy classification; mechanical preservation and
manifest; adversarial verifier tests; full destination suite; smoke and CLI checks;
independent exhaustive comparison; documentation and timeline checks; final audit.

Preflight, mechanical preservation, the manifest, and verifier checks are complete.
The resumed verifier suite passed 36 tests in 7.06 seconds; independent review
reran them with 36 passes in 8.37 seconds, then independently passed all 43 focused
verifier and affected documentation checks in 125.92 seconds after the repairs.
The complete source suite passed 559
tests and skipped one. The complete destination suite recorded 593 passes, two
documentation failures, and one skip in 3984.88 seconds; after the two repairs,
all seven affected inherited checks passed in 1.90 seconds. A second complete suite
was not run for these documentation-only corrections. Preserving bytes limits review to the new
verifier and current documentation, but still requires exhaustive comparison and the
full inherited suite. Context cost is driven by the 129-path source inventory,
133 rows across two evidence tables, packaging contracts, contribution rules, and ten
future phase boundaries. File count is not a measure of newly implemented behavior.

The earlier source baseline was interrupted at 267 passed after 2,075.19 seconds
(34 minutes, 35 seconds), with exit 2 from KeyboardInterrupt. This is partial
verification, not a passing full suite or an application failure. The separate
source stdlib smoke passed with `phase=DONE`, `network_used=false`,
`trace_fidelity=final_only`, and `isolation=unsandboxed`. Its fixture score of 1.0
is a smoke result, not experimental efficacy.

The earlier 2 to 4 hour estimate was conditional on comparable local test throughput.
One interrupted source run alone consumed more than 34 minutes, so a reliable
remaining duration cannot be inferred from the completed mechanical copy. The two
full suites initially ran concurrently. The original source suite completed with
559 passing tests and one existing skip in 3926.15 seconds, exit 0; its revision and
clean status were reverified. The destination suite and targeted repairs are also
complete, with their distinct outcomes retained above. This estimate excludes
live Hermes and paper experiments, whose environment and provider requirements
are separate feature work.

The post-repair artifact rebuild, exhaustive archive inspection, and isolated
installed-wheel checks have passed. Their raw output and file-hash inventories
remain linked from the verification receipt. The independent review passed all
four quick-plan requirements with zero remaining gaps at 2026-09-07T02:22:48Z.
Git integration and clean task-owned closeout remain for the orchestrator.
The single existing skip is the wheel test's absent global setuptools dependency;
the declared isolated PEP517 build and actual installed-wheel checks cover that
distribution surface separately. Even after verification, the original source
must remain until a fresh lossless salvage audit and explicit action-time deletion
approval; its unmerged work and history must never be inferred disposable.
