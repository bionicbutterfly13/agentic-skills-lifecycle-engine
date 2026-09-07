---
phase: quick-260906-omm
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified:
  - ".gitignore"
  - "CHANGELOG.md"
  - "CITATION.cff"
  - "CONTRIBUTING.md"
  - "docs/migration/asme-source/CONTRIBUTING.md"
  - "LICENSE"
  - "MANIFEST.in"
  - "NOTICE.md"
  - "PROVENANCE.md"
  - "docs/migration/asme-source/PROVENANCE.md"
  - "PURPOSE.md"
  - "README.md"
  - "docs/migration/asme-source/README.md"
  - "SECURITY.md"
  - "SKILL.md"
  - "adapters/hermes_plugin/README.md"
  - "adapters/hermes_plugin/__init__.py"
  - "adapters/hermes_plugin/plugin.yaml"
  - "assets/PURPOSE.md.tmpl"
  - "assets/SKILL.md.tmpl"
  - "assets/eval/arithmetic/answers.jsonl"
  - "assets/eval/arithmetic/cartridge.json"
  - "assets/eval/arithmetic/prompt.txt"
  - "assets/eval/arithmetic/rollouts/run-1/baseline.jsonl"
  - "assets/eval/arithmetic/rollouts/run-1/confirmation.jsonl"
  - "assets/eval/arithmetic/rollouts/run-1/validation.jsonl"
  - "assets/eval/arithmetic/tasks.jsonl"
  - "assets/eval/echo/answers.jsonl"
  - "assets/eval/echo/cartridge.json"
  - "assets/eval/echo/prompt.txt"
  - "assets/eval/echo/rollouts/run-1/baseline.jsonl"
  - "assets/eval/echo/rollouts/run-1/confirmation.jsonl"
  - "assets/eval/echo/rollouts/run-1/validation.jsonl"
  - "assets/eval/echo/tasks.jsonl"
  - "assets/index.md.tmpl"
  - "assets/inference-prompt.txt.tmpl"
  - "assets/log.md.tmpl"
  - "assets/pattern.md.tmpl"
  - "assets/skill-impact.md.tmpl"
  - "docs/implementation-parity.md"
  - "docs/license-decision.md"
  - "locked/acceptance-matrix.md"
  - "locked/architecture-contract.md"
  - "locked/source-parity-matrix.md"
  - "pyproject.toml"
  - "references/fidelity.md"
  - "references/integration.md"
  - "references/paper-notes.md"
  - "references/verification/README.md"
  - "references/verification/independent-review-protocol.md"
  - "scripts/extractors/answer_tag.py"
  - "scripts/install_claude_skill.py"
  - "scripts/scorers/exact_match.py"
  - "scripts/scorers/numeric_tolerance.py"
  - "scripts/stdlib_smoke.py"
  - "setup.py"
  - "src/asme/__init__.py"
  - "src/asme/__main__.py"
  - "src/asme/adapter.py"
  - "src/asme/bootstrap.py"
  - "src/asme/canonical.py"
  - "src/asme/cartridge.py"
  - "src/asme/claims.py"
  - "src/asme/cli.py"
  - "src/asme/clock.py"
  - "src/asme/contract.py"
  - "src/asme/data/source-registry.json"
  - "src/asme/delivery.py"
  - "src/asme/dependencies.py"
  - "src/asme/domain.py"
  - "src/asme/evalreport.py"
  - "src/asme/evaluation.py"
  - "src/asme/evidence.py"
  - "src/asme/evolution_eval.py"
  - "src/asme/gate2.py"
  - "src/asme/governance.py"
  - "src/asme/impact.py"
  - "src/asme/integration.py"
  - "src/asme/lifecycle.py"
  - "src/asme/manifest.py"
  - "src/asme/observer_bridge.py"
  - "src/asme/package.py"
  - "src/asme/proposal.py"
  - "src/asme/seed.py"
  - "src/asme/skill_assets.py"
  - "src/asme/skill_install.py"
  - "src/asme/skill_safety.py"
  - "src/asme/snapshot.py"
  - "src/asme/source_registry.py"
  - "src/asme/transaction.py"
  - "src/asme/wiki.py"
  - "src/asme/workflow.py"
  - "src/asme/workspace.py"
  - "tests/conftest.py"
  - "tests/test_bootstrap.py"
  - "tests/test_builtin_cartridge_programs.py"
  - "tests/test_cartridge.py"
  - "tests/test_cli.py"
  - "tests/test_cli_eval_bridge.py"
  - "tests/test_clock.py"
  - "tests/test_contract_adapter.py"
  - "tests/test_crash_oracle.py"
  - "tests/test_delivery.py"
  - "tests/test_domain_evaluation_manifest.py"
  - "tests/test_evalreport.py"
  - "tests/test_evolution_eval.py"
  - "tests/test_governance_dependencies_gate2.py"
  - "tests/test_integration_bridge.py"
  - "tests/test_lifecycle.py"
  - "tests/test_observer_bridge.py"
  - "tests/test_proposal.py"
  - "tests/test_release_surface.py"
  - "tests/test_reset_errors.py"
  - "tests/test_seed.py"
  - "tests/test_skill_assets.py"
  - "tests/test_skill_install.py"
  - "tests/test_skill_safety.py"
  - "tests/test_snapshot_package.py"
  - "tests/test_stdlib_smoke.py"
  - "tests/test_terminal_paths.py"
  - "tests/test_transaction.py"
  - "tests/test_wiki.py"
  - "tests/test_workflow.py"
  - "tests/test_workflow_candidate.py"
  - "tests/test_workspace_hermes_adapter.py"
  - "docs/migration/asme-source-manifest.json"
  - "scripts/verify_asme_port.py"
  - "tests/test_asme_port.py"
  - "docs/evidence/asme-port-verification.json"
  - "docs/evidence/asme-github-timeline.json"
  - "docs/migration/asme-port.md"
  - "docs/public/2026-09-06-from-wikiskill-to-lifecycle.md"
  - ".planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/260906-omm-PLAN.md"
  - ".planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/260906-omm-SUMMARY.md"
  - ".planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/260906-omm-PRE-RESUME-STATE.md"
  - ".planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/destination-collection.json"
  - ".planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/destination-help.json"
  - ".planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/destination-matrix.json"
  - ".planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/destination-smoke.json"
  - ".planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/destination-pytest.json"
  - ".planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/260906-omm-build-inspection.json"
  - ".planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/destination-doc-repairs.json"
  - ".planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/destination-final-build.json"
  - ".planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/260906-omm-inspect-build.py"
  - ".planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/destination-final-build-inspection.json"
  - ".planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/destination-final-wheel-install.json"
  - ".planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/destination-final-wheel-probe.json"
  - ".planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/260906-omm-VERIFICATION.md"
  - ".planning/PROJECT.md"
  - ".planning/STATE.md"
autonomous: true
requirements: [SALV-01, SALV-02, SALV-03, PROJ-01, PROJ-02, PROJ-03, DOCS-02]
must_haves:
  truths:
    - "Lifecycle runs the complete pinned ASME engine and inherited test suite with the same CLI, package identity, bundled assets, and Hermes capability boundary."
    - "Every one of the 129 tracked source paths has a verified byte-and-mode-preserving destination, exact historical copy, or explicit retained-at-source disposition; source history and nontracked material remain accounted for without deleting ASME."
    - "Fresh destination test results and an independent source-equivalence check distinguish inherited behavior from migration regressions."
    - "The September 6 blog links primary papers and timestamped GitHub evidence, uses the supported within-a-week claim, and describes paper-comparable performance and live Hermes dispatch as unproved."
  artifacts:
    - path: src/asme/cli.py
      provides: "Preserved asme CLI contract"
    - path: adapters/hermes_plugin/__init__.py
      provides: "Preserved read-only Hermes capability integration"
    - path: docs/migration/asme-source-manifest.json
      provides: "Complete source-to-destination receipt with pinned revision, SHA256, Git mode, and disposition"
    - path: scripts/verify_asme_port.py
      provides: "Read-only migration verification with explicit failure exit"
    - path: docs/evidence/asme-port-verification.json
      provides: "Fresh full-suite, smoke, compatibility, and independent inventory evidence"
    - path: docs/evidence/asme-github-timeline.json
      provides: "Primary-source timeline records and reproducible elapsed-time calculation"
    - path: docs/public/2026-09-06-from-wikiskill-to-lifecycle.md
      provides: "Source-backed unpublished blog draft"
  key_links:
    - from: pyproject.toml
      to: src/asme/cli.py
      via: "Preserved asme = asme.cli:main entry point and source layout"
      pattern: "asme.cli:main"
    - from: scripts/verify_asme_port.py
      to: docs/migration/asme-source-manifest.json
      via: "Re-enumeration of the pinned source and exact destination hashes and modes"
      pattern: "sha256"
    - from: docs/public/2026-09-06-from-wikiskill-to-lifecycle.md
      to: docs/evidence/asme-github-timeline.json
      via: "Dated primary-source links and explicitly scoped timeline claims"
      pattern: "2026-09-02"
---

<objective>
Port the existing Agent Skill Mastery Engine into Agentic Skills Lifecycle Engine with complete runtime and package parity, independently checked migration evidence, and a documented, source-backed account of the Google-paper timeline.

Purpose: Preserve the working implementation and Hermes-specific boundary while making Lifecycle the canonical development home. The user asked to finish the port, preserve parity, branch each feature, document the implications, and write with proof.
Output: A lossless compatibility import, executable integrity verifier, current verification receipts, migration report, current README and provenance context, and an unpublished September 6 blog draft.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
Resume authority (September 6, 2026): the adopted autonomous WikiSkill v1 goal
supersedes D-06's former no-commit/no-merge limits. Verified feature commits,
integration, and safe removal of clean merged task-owned lanes are authorized;
paid execution, publication, and original-source deletion remain gated. This
executor prepares the import for independent review before committing. The prior
observer phase-constant scanner hit was conclusively classified by redacted AST
review as a non-credential. It is not a current blocker. Root PROJECT.md and
STATE.md are owned by the orchestrator for consolidation into the official
wikiskill-v1 workstream because another session owns overlapping main state.
The orchestrator archived the prior paused root STATE, restored the task-owned
root STATE to its integration baseline, and made a narrow PROJECT.md factual
update acknowledging the imported engine and offline verification.
The earlier two-paper blog is a preliminary historical draft; current work is
strictly WikiSkill v1 and the substantial post follows verified parity outcomes.

@AGENTS.md
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@../agent-skill-mastery-engine/CONTRIBUTING.md
@../agent-skill-mastery-engine/pyproject.toml
@../agent-skill-mastery-engine/setup.py
@../agent-skill-mastery-engine/tests/test_release_surface.py
@../agent-skill-mastery-engine/docs/implementation-parity.md
@../agent-skill-mastery-engine/locked/source-parity-matrix.md
@../agent-skill-mastery-engine/adapters/hermes_plugin/README.md

This is the native GSD quick task 260906-omm in --validate mode, initialized by the orchestrator using @opengsd/gsd-core 1.12.0. It is not execution of all ten roadmap phases. No quick CONTEXT.md or RESEARCH.md was supplied. The decisions below record the explicit user direction and the orchestrator's bounded import contract; they do not reopen settled project decisions.

Mechanical-import scope exception: the original plan declared 136 files; resumption adds fourteen explicit evidence/checkpoint/plan paths for 150 declared paths, exceeding the ordinary 15-file planning heuristic. The user's complete port requires preserving the coherent source package, so the full inventory remains visible: 122 existing files are copied with exact bytes and modes, and seven source planning files receive retained-at-source dispositions. Authored changes are limited to the migration verifier and its tests, current documentation, evidence receipts, and planning state. The independent plan checker verified all 129 source mappings with zero uncovered imports and returned no correctness, security, or contract blockers. This exception does not waive the complete inherited suite, independent source comparison, negative verifier tests, or any admission or publication gate.

Settled:
- D-01: Preserve the existing engine's complete behavior while porting into Lifecycle; retain the asme Python namespace, asme CLI, agent-skill-mastery-engine distribution identity, Python >=3.11 contract, and version 0.2.0 for compatibility during this import.
- D-02: Work only in the current worktree (agentic-skills-lifecycle-engine-asme-port) on feat/asme-hermes-parity-port, based on verified integration commit 19375806a748db16e706c70f49aa3bc83b142eb0. Other sessions own dirty main STATE/PITFALLS/PAPER-PARITY files and other public-post drafts. Preserve those lanes.
- D-03: Source is the clean sibling repository ../agent-skill-mastery-engine at 1137c6705fd844546d5588757a5a23d4007b20c4, with 129 tracked paths and six commits ahead of the published remote tip. Reverify before importing; do not silently change the pin.
- D-04: Preserve source code, tests, assets, locked contracts, provenance, and licensing. Account for all source tracked paths, Git history, untracked files, and ignored files; do not copy ambient runtime state, credentials, or repositories wholesale.
- D-05: Document the verified timeline and implications in the requested blog. An unverified three-day claim cannot replace the measured GitHub timestamps.
- D-06: No commit, push, merge, installation, deletion, live provider request, or publication is authorized by this task. User constraints override the GSD automatic commit settings and executor defaults.

Pending, surfaced explicitly:
- Source claims.py reportedly accepts scripted-offline-fixture evidence as paper_comparable. The orchestrator identified this inherited defect. Confirm with source references and an isolated reproducer, report it as an inherited claims-policy blocker, and request/prepare a separate narrowly scoped regression repair. Do not alter inherited tested semantics in this compatibility import or treat its labels as proof of performance.
- The Hermes plugin exposes a read-only capability tool with dispatch disabled. Historical Plugin Doctor evidence does not prove current installed/runtime behavior.
- Source documentation includes historical private/unpublished declarations despite a verified public GitHub release. Preserve original bytes and distinguish snapshot-era declarations from current evidence.
- Source baseline pytest is running under the orchestrator. Use its final result as a baseline only after completion; do not invent a passing count.

Deferred from this task's implementation:
- New host adapters, namespace/distribution rename, live Hermes dispatch, provider experiments, paid runs, package installation, release/publication, and the remaining Lifecycle study/state/security roadmap are separate feature streams.
- Source deletion stays blocked even after this port. A receipt and preserved source history do not by themselves authorize retirement.

Interfaces and compatibility anchors:
- pyproject.toml declares project.scripts asme = "asme.cli:main"; pytest uses pythonpath = ["src"] and testpaths = ["tests"].
- src/asme/cli.py exports main(argv: Sequence[str] | None = None) -> int.
- setup.py build_py copies the root skill payload into asme/skill; MANIFEST.in and src/asme/skill_assets.py define shipping behavior. Preserve both editable and built-package expectations.
- Existing release tests require every PUBLIC_ARTIFACTS entry, 106 SP rows, 27 HF-A rows, MIT plus CC BY 4.0 obligations, the NOTICE distribution-gate wording, and no em dashes in public prose.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Import the complete pinned source with an auditable lossless receipt</name>
  <files>
.gitignore, CHANGELOG.md, CITATION.cff, docs/migration/asme-source/CONTRIBUTING.md, LICENSE, MANIFEST.in, NOTICE.md, docs/migration/asme-source/PROVENANCE.md, PURPOSE.md, docs/migration/asme-source/README.md, SECURITY.md, SKILL.md, adapters/hermes_plugin/README.md, adapters/hermes_plugin/__init__.py, adapters/hermes_plugin/plugin.yaml, assets/PURPOSE.md.tmpl, assets/SKILL.md.tmpl, assets/eval/arithmetic/answers.jsonl, assets/eval/arithmetic/cartridge.json, assets/eval/arithmetic/prompt.txt, assets/eval/arithmetic/rollouts/run-1/baseline.jsonl, assets/eval/arithmetic/rollouts/run-1/confirmation.jsonl, assets/eval/arithmetic/rollouts/run-1/validation.jsonl, assets/eval/arithmetic/tasks.jsonl, assets/eval/echo/answers.jsonl, assets/eval/echo/cartridge.json, assets/eval/echo/prompt.txt, assets/eval/echo/rollouts/run-1/baseline.jsonl, assets/eval/echo/rollouts/run-1/confirmation.jsonl, assets/eval/echo/rollouts/run-1/validation.jsonl, assets/eval/echo/tasks.jsonl, assets/index.md.tmpl, assets/inference-prompt.txt.tmpl, assets/log.md.tmpl, assets/pattern.md.tmpl, assets/skill-impact.md.tmpl, docs/implementation-parity.md, docs/license-decision.md, locked/acceptance-matrix.md, locked/architecture-contract.md, locked/source-parity-matrix.md, pyproject.toml, references/fidelity.md, references/integration.md, references/paper-notes.md, references/verification/README.md, references/verification/independent-review-protocol.md, scripts/extractors/answer_tag.py, scripts/install_claude_skill.py, scripts/scorers/exact_match.py, scripts/scorers/numeric_tolerance.py, scripts/stdlib_smoke.py, setup.py, src/asme/__init__.py, src/asme/__main__.py, src/asme/adapter.py, src/asme/bootstrap.py, src/asme/canonical.py, src/asme/cartridge.py, src/asme/claims.py, src/asme/cli.py, src/asme/clock.py, src/asme/contract.py, src/asme/data/source-registry.json, src/asme/delivery.py, src/asme/dependencies.py, src/asme/domain.py, src/asme/evalreport.py, src/asme/evaluation.py, src/asme/evidence.py, src/asme/evolution_eval.py, src/asme/gate2.py, src/asme/governance.py, src/asme/impact.py, src/asme/integration.py, src/asme/lifecycle.py, src/asme/manifest.py, src/asme/observer_bridge.py, src/asme/package.py, src/asme/proposal.py, src/asme/seed.py, src/asme/skill_assets.py, src/asme/skill_install.py, src/asme/skill_safety.py, src/asme/snapshot.py, src/asme/source_registry.py, src/asme/transaction.py, src/asme/wiki.py, src/asme/workflow.py, src/asme/workspace.py, tests/conftest.py, tests/test_bootstrap.py, tests/test_builtin_cartridge_programs.py, tests/test_cartridge.py, tests/test_cli.py, tests/test_cli_eval_bridge.py, tests/test_clock.py, tests/test_contract_adapter.py, tests/test_crash_oracle.py, tests/test_delivery.py, tests/test_domain_evaluation_manifest.py, tests/test_evalreport.py, tests/test_evolution_eval.py, tests/test_governance_dependencies_gate2.py, tests/test_integration_bridge.py, tests/test_lifecycle.py, tests/test_observer_bridge.py, tests/test_proposal.py, tests/test_release_surface.py, tests/test_reset_errors.py, tests/test_seed.py, tests/test_skill_assets.py, tests/test_skill_install.py, tests/test_skill_safety.py, tests/test_snapshot_package.py, tests/test_stdlib_smoke.py, tests/test_terminal_paths.py, tests/test_transaction.py, tests/test_wiki.py, tests/test_workflow.py, tests/test_workflow_candidate.py, tests/test_workspace_hermes_adapter.py, README.md, PROVENANCE.md, CONTRIBUTING.md, docs/migration/asme-source-manifest.json, scripts/verify_asme_port.py, tests/test_asme_port.py
  </files>
  <behavior>
    - The verifier accepts a complete pinned-source mapping with exact content hashes and Git modes.
    - It rejects a missing source path, duplicate mapping, changed destination bytes, changed executable mode, escaped destination, symlink traversal, or source revision mismatch.
    - Historical copies satisfy source preservation only when their bytes and modes match the pinned source; modified current-facing docs must point to those exact historical copies.
    - Nontracked files are inventoried by path and classification without loading runtime state or credential-bearing contents.
  </behavior>
  <action>Per D-01 through D-04, first recheck worktree ownership, destination status, source HEAD/status/ref ancestry, and the complete NUL-delimited tracked inventory. Preserve the verified integration base and stop on unowned destination collisions or source drift. Mechanically import the 122 runtime, package, test, and public-document tracked paths with their exact bytes and modes at matching relative destinations. The seven source .planning/codebase maps contain machine-local details: retain them at their original source paths without copying them into distributable docs, record SHA256 and Git mode with disposition retained_at_source and a private-planning exclusion reason, and do not read or expose any credential-like value. Preserve Lifecycle planning. Keep exact historical copies of source README.md, PROVENANCE.md, and CONTRIBUTING.md under docs/migration/asme-source before changing their current-facing counterparts in Task 3. Preserve NOTICE.md, LICENSE, CITATION.cff, SKILL.md, PURPOSE.md, packaging files, all adapters/assets/references/scripts/src/tests, and both parity matrices. Scan the complete to-be-imported tracked content for credential-like material and public-document private paths without printing matching values; stop that surface on a hit. Enumerate all untracked and ignored paths without copying or reading ambient runtime state, record their retained/excluded dispositions and counts, and record exact local/remote history identities and unique local commits without copying .git. Use a deterministic JSON receipt with source revision, relative paths, SHA256, Git mode, canonical destination or null for retained-at-source records, historical destination where applicable, and explicit disposition for every tracked source path. Add a stdlib-only read-only verifier at scripts/verify_asme_port.py taking --source, --source-revision, and --check; it must independently enumerate source Git paths, compare the receipt's complete set, validate safe containment, verify hashes and modes including the seven retained source records, and exit nonzero on any mismatch. Write negative tests before its implementation, preserve every inherited test unchanged, and avoid new dependencies. Per D-06, do not stage, commit, install, touch live profiles, or remove the original repository.</action>
  <verify>
    <automated>python3 -m pytest tests/test_asme_port.py && python3 scripts/verify_asme_port.py --source ../agent-skill-mastery-engine --source-revision 1137c6705fd844546d5588757a5a23d4007b20c4 --check && git diff --check</automated>
  </verify>
  <done>Every one of the freshly enumerated 129 pinned tracked source paths has exactly one preservation disposition, source bytes and modes are accounted for, all runtime/tests/assets retain their original contracts, nontracked material and unique history remain recorded and retained, and the verifier's negative cases pass. The source repository remains unchanged. Mechanical copying does not imply any live-runtime or paper-performance claim.</done>
</task>

<task type="auto">
  <name>Task 2: Independently verify the full imported engine and record its actual parity boundary</name>
  <files>docs/evidence/asme-port-verification.json, docs/migration/asme-port.md, .planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/260906-omm-VERIFICATION.md</files>
  <action>Per D-01, D-03, and D-04, obtain the source baseline's completed full pytest and stdlib-smoke results, then run python3 -m pytest and python3 scripts/stdlib_smoke.py from the isolated destination without provider calls or network access. Preserve the full collected suite, including packaging, archive, release-surface, built-in cartridge, and Hermes adapter tests; do not deselect tests or treat a narrower smoke check as full verification. If the available test environment lacks a dependency, report the exact missing package and stop that check instead of installing it. Run CLI --help and transition-matrix with PYTHONPATH=src; record exit codes and actual interpreter identity. Have an independent reviewer or fresh checker enumerate the full pinned source tree and compare all bytes/modes to destinations without trusting the migration script's own conclusions; inspect the complete 106-row SP and 27-row HF-A matrices and name all inherited PARTIAL/EXCLUDED/BLOCKED boundaries. Record commands, scope, timestamps, exit codes, collected/passed/failed/skipped totals, source revision, and destination content digest in docs/evidence/asme-port-verification.json. Confirm the inherited scripted-offline-fixture claims-policy issue with a bounded offline reproducer and exact source/test references, separating that pre-existing blocker from migration regressions. Document that fixture success, legacy parity-table labels, historical Plugin Doctor results, and source equivalence do not prove controlled paper replication, current live Hermes dispatch, or all Lifecycle roadmap requirements. On a genuine port regression, make one targeted repair only if the cause is clear and no compatibility semantics change; otherwise report the failure and stop the affected verification. No source tests may be weakened.</action>
  <verify>
    <automated>python3 -m pytest && python3 scripts/stdlib_smoke.py && PYTHONPATH=src python3 -m asme --help && PYTHONPATH=src python3 -m asme transition-matrix && python3 scripts/verify_asme_port.py --source ../agent-skill-mastery-engine --source-revision 1137c6705fd844546d5588757a5a23d4007b20c4 --check && git diff --check</automated>
  </verify>
  <done>The complete destination suite and stdlib smoke have fresh recorded outcomes compared with the source baseline; an independent exhaustive inventory check confirms imported equivalence. The report distinguishes passed checks, unverified runtime behavior, and the inherited claims-policy defect. A failure remains visible and cannot be relabeled as a pass; no benchmark result or live Hermes operation is claimed.</done>
</task>

<task type="auto">
  <name>Task 3: Write the timeline-backed blog and current migration documentation</name>
  <files>README.md, PROVENANCE.md, CONTRIBUTING.md, docs/migration/asme-source-manifest.json, docs/migration/asme-port.md, docs/evidence/asme-github-timeline.json, docs/public/2026-09-06-from-wikiskill-to-lifecycle.md, .planning/PROJECT.md, .planning/STATE.md, .planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/260906-omm-SUMMARY.md</files>
  <action>Per D-05, preserve a compact primary-source timeline receipt at docs/evidence/asme-github-timeline.json using the orchestrator's verified GitHub/arXiv records and refetch any claim whose primary record is absent. Include the actual source URLs and relevant fields only, without credentials or unrelated account events. WikiSkill arXiv 2608.27454 was submitted 2026-08-27T17:59:11Z; the ASME repository was created 2026-09-01T06:00:39Z; root commit c20a4fd72e120209c819b33a3209c2ac85af7275 has timestamp 2026-09-01T05:54:16Z and 88 files including 29 Python source modules and 23 test modules (24 Python files under tests when conftest.py is included); GitHub CreateEvent 19626958334 created main at 2026-09-01T06:00:50Z; PushEvent 19724824535 at 2026-09-01T14:11:23Z links that root to a8d5de202ec0a56f9a675fad4ca93d6b182e9053; release 381020408 and ReleaseEvent 14260277947 prove v0.2.0 published 2026-09-02T06:29:14Z with draft=false and prerelease=false. Compute elapsed time with datetime arithmetic: the release is 5 days 12 hours 30 minutes 3 seconds after paper submission. Distinguish commit timestamp, observed GitHub event, repository creation, release publication, paper submission, and Google's code release; the last has not been established by these records. The checked August 27-30 events and August 27-31 commit searches did not prove a three-day push, so do not claim one or infer nonexistence outside that search scope. Draft docs/public/2026-09-06-from-wikiskill-to-lifecycle.md with the verified within-a-week framing, both WikiSkill and Towards a Systems Foundation for Agentic Skills (arXiv 2608.29596), original attribution/license obligations, the specific Hermes read-only boundary, the relationship between the existing engine and Lifecycle, and what importing it preserves. Keep it a draft; publication is not authorized. Update canonical README/PROVENANCE/CONTRIBUTING to identify Lifecycle, explain the preserved compatibility identifiers, link historical source copies, distinguish published ASME evidence from this uncommitted port, and retain current owner approval requirements. Keep original notice/license/citation obligations intact. Complete docs/migration/asme-port.md with exhaustive source/import/parity accounting, confirmed test evidence, decisions and their implications, the inherited claims-policy blocker, and an effort assessment in executable work units/context cost; do not invent a duration for unfinished work. Update only this worktree's PROJECT and STATE to reflect the verified import and this quick task, leaving other roadmap requirements and deferred work open. Update the receipt's approved documentation destinations while preserving exact historical-source hashes. The orchestrator owns STATE updates if another active writer appears. Per D-02, do not edit or duplicate the other session's introducing-lifecycle.md or 2026-09-04-building-lifecycle.md. Per D-06, no automatic commit, merge, cleanup, or publication.</action>
  <verify>
    <automated>python3 scripts/verify_asme_port.py --source ../agent-skill-mastery-engine --source-revision 1137c6705fd844546d5588757a5a23d4007b20c4 --check && python3 -m pytest tests/test_release_surface.py tests/test_asme_port.py && python3 -m json.tool docs/evidence/asme-github-timeline.json && python3 -m json.tool docs/evidence/asme-port-verification.json && git diff --check</automated>
  </verify>
  <done>The unpublished blog and canonical docs directly link the verified primary evidence and both papers, use a supported within-a-week claim, identify the unsupported three-day assertion, and separate implementation/test/release/runtime/performance status. Original source documents remain recoverable byte-for-byte. The quick-task summary records actual results and remaining authorization boundaries without declaring the ten-phase Lifecycle program complete.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| ASME source checkout to Lifecycle worktree | Imported content, symlinks, historical docs, executable modes, and runtime debris can cross project boundaries. |
| Local and GitHub evidence to public prose | Commit dates and fixture outputs can be mistaken for public release timing or experimental efficacy. |
| Staged Hermes adapter to live host | Migration evidence does not authorize installation, model dispatch, or provider access. |
| Task-owned worktree to other writing streams | Main and other feature lanes contain user-owned work that must remain untouched. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-260906-01 | Tampering | Import and source receipt | mitigate | Pin source revision, enumerate every tracked path, reject source drift, preserve SHA256 and Git modes, and compare through an independent checker. |
| T-260906-02 | Information disclosure | Untracked/ignored state and imported docs | mitigate | Inventory nontracked paths without reading sensitive runtime contents; scan all imported tracked bytes without printing secret matches; stop on a match. |
| T-260906-03 | Elevation of privilege | Paths, symlinks, and Hermes plugin | mitigate | Enforce relative contained destination paths, reject link traversal, preserve disabled dispatch, and perform no install/provider action. |
| T-260906-04 | Repudiation | Timeline and verification receipts | mitigate | Record primary URLs, event/release IDs, revision/content identity, exact command outcomes, and separate authored dates from observed GitHub events. |
| T-260906-05 | Tampering | Other-session main and public drafts | mitigate | Restrict every write to the assigned branch/worktree and exact owned files; do not reconcile another session's dirty state here. |
| T-260906-06 | Spoofing | Paper-comparable claim labels | mitigate | Reproduce and report the inherited offline-fixture acceptance defect; forbid benchmark/performance claims based on its labels and retain a separate repair requirement. |
| T-260906-SC | Tampering | Package installations | accept | No package-manager installation or dependency addition is in scope; report missing local test dependencies rather than substituting an install. |
</threat_model>

<verification>
Run the automated commands attached to each task using the existing test-capable interpreter. The complete inherited suite is mandatory even if its execution exceeds one minute; poll without hiding failures and preserve progress reporting. Source baseline and destination results are separate records. This runtime/package import is not a declaration that the full source repository is disposable or that its history and private material have been salvaged. The independent verifier must check the full tracked-path set and both source parity matrices, not a sample or merely the manifest's claimed count. Use readback/link/date checks for prose and JSON parsing for receipts. Never count archived notes, static source review, fixture tests, or the existence of an imported adapter as live runtime or paper-replication evidence.

The final working-tree audit must show no source modifications, no write to main/other worktrees, no new credential exposure, and only task-owned changes. Do not clean up this uncommitted/unmerged lane. Integration and removal require the user's explicit action-time approval and fresh checks.
</verification>

<source_audit>
## Multi-source coverage audit

| Source | ID | Item in this quick task | Task | Coverage |
|--------|----|-------------------------|------|----------|
| GOAL | Quick request | Port ASME with complete parity and write using verified evidence | 1, 2, 3 | COVERED |
| GOAL | Phase 6 goal | Preserve verified reusable ASME value and provenance without authorizing deletion | 1, 2, 3 | COVERED for the compatibility import; phase completion is not asserted |
| REQ | SALV-01 | Enumerate code, contracts, tests, provenance, licenses, history, untracked material | 1, 2 | COVERED |
| REQ | SALV-02 | Migrate compatible assets with provenance and checks | 1, 2 | COVERED |
| REQ | SALV-03 | Block source deletion pending fresh audit and action-time approval | 1, 3 | COVERED |
| REQ | PROJ-01 | Canonical Lifecycle identity and compatibility names | 3 | COVERED |
| REQ | PROJ-02, DOCS-02 | Separate research, design, implementation, execution, release, and pending work | 2, 3 | COVERED |
| REQ | PROJ-03 | Link relevant primary-source lineage | 3 | COVERED for this article and port; complete phase research coverage is not asserted |
| RESEARCH | Source contribution and release contract | stdlib core, thin adapters, full pytest/smoke, exact artifact and license preservation | 1, 2, 3 | COVERED |
| RESEARCH | Orchestrator primary-source findings | GitHub event/release identities, paper date, root tree, unsupported three-day claim | 3 | COVERED |
| RESEARCH | Source compatibility findings | 106 SP rows, 27 HF-A rows, disabled Hermes dispatch, inherited claims-policy defect | 2, 3 | COVERED |
| CONTEXT | D-01 | Complete compatibility without silent renaming or behavior changes | 1, 2 | COVERED |
| CONTEXT | D-02 | Isolated branch/worktree and distinct blog destination | 1, 3 | COVERED |
| CONTEXT | D-03, D-04 | Pinned source, exhaustive inventory, lossless preservation, source retention | 1, 2 | COVERED |
| CONTEXT | D-05 | Proof-backed blog and implications | 3 | COVERED |
| CONTEXT | D-06 | No commit, push, merge, install, delete, provider request, or publication | 1, 2, 3 | COVERED |

No quick CONTEXT.md/RESEARCH.md exists; the delegated source findings and decision contract above supply those inputs. DOCS-01's September 3-4 journal belongs to a separate writing stream and is excluded rather than reauthored. All other roadmap requirements remain assigned to their existing phases. The claims-policy behavior repair is explicitly identified as a separate required follow-up, not silently implemented or declared fixed by this lossless port.
</source_audit>

<success_criteria>
- The complete ASME runtime, tests, and package implementation is available and runnable from the isolated Lifecycle worktree with preserved compatibility behavior and exact source lineage.
- Every source tracked path is covered, and source history/nontracked material remain accounted for and untouched.
- Full-suite, smoke, CLI, release-surface, and independent inventory results are recorded without weakening checks.
- The inherited claims-policy defect and Hermes execution limits remain explicit, with no unsupported performance, installation, or release claim.
- The new draft blog uses primary links and the verified release interval; current docs distinguish historical ASME documents from verified publication and current uncommitted port state.
- No other workstream is overwritten, no source is removed, and no unauthorized external or Git publication action occurs.
</success_criteria>

<output>
Create .planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/260906-omm-SUMMARY.md with actual commands, results, evidence paths, source/destination identities, inherited blockers, and approval boundaries. The independent verifier creates .planning/quick/260906-omm-port-asme-into-lifecycle-with-complete-f/260906-omm-VERIFICATION.md. The orchestrator records the quick task in this worktree's STATE only after verification. Do not update ROADMAP phase completion or commit any files.
</output>
