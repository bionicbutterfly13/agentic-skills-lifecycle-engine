# Independent review protocol

This protocol lets a reviewer assess Agent Skill Mastery Engine without installing it, changing
the candidate, or treating self-authored ledgers as proof.

## Reviewer independence

The reviewer must record:

- the candidate tree hash or file-manifest hash reviewed;
- whether the reviewer authored any reviewed implementation;
- every external source artifact supplied for Gate 0 and its supplied SHA-256;
- the exact commands executed and their exit codes; and
- every check not executed, with a reason.

A reviewer who changes implementation or tests becomes an implementer. A new reviewer
must inspect the resulting frozen candidate.

## Hard boundaries

The review is read-only. Do not:

- install the candidate into Hermes, Claude, Codex, or any live skill root;
- install missing dependencies or replace an unavailable official command with a
  different build path;
- edit tests, assertions, source matrices, capability labels, or the candidate;
- commit, merge, publish, distribute, upload, or create a public repository;
- infer approval from a historical plan, transcript, status file, or passing test; or
- include private source locations or source content in a public report.

Return `BLOCKED` for a required unavailable input. Do not convert the missing check into
a pass.

## Gate 0: source and architecture fidelity

The owner supplies the locked source packet, architecture contract, source-parity matrix,
acceptance matrix, paper audit, Claude development-history audit, and original Codex audit
analysis outside the public candidate.

1. Recompute each supplied SHA-256 and compare it with the handoff.
2. Verify the source-parity matrix contains exactly `SP-001` through `SP-106`, once
   each.
3. Verify the acceptance matrix contains exactly `HF-A01` through `HF-A27`, once each.
4. For every source row, trace the named implementation evidence or classify it
   `MISSING`, `CONTRADICTED`, `POLICY-GATED`, or `EXCLUDED-WITH-REASON`.
5. Check that paper facts, direct owner decisions, architecture defaults, Claude
   proposals, Codex findings, and runtime evidence remain separately labelled.
6. Check that the local method does not claim literal paper reproduction, sandboxing,
   unseen evaluation, paper-complete traces, or validated comparative performance
   without the required evidence.

Do not accept `docs/implementation-parity.md` as proof by itself. It is the index of
claims to verify against code, tests, and locked sources.

## Gate 1: implementation and adapter

Run from the candidate package root:

```bash
python -m pytest -q
python -m compileall -q src adapters scripts tests
python scripts/stdlib_smoke.py
PYTHONPATH=src python -m asme --version
```

Expected current local evidence:

- 470 collected tests;
- stdlib smoke reaches `DONE` with `network_used: false`;
- CLI version is `0.1.0`; and
- compileall exits zero.

Review the code paths behind the checks, especially:

- role-specific inputs and held-out-answer boundaries;
- extractor/scorer failure and score validity;
- strict improvement, confirmation, rollback, and persistent wiki behavior;
- transaction intent, dependency binding, output-plan binding, and recovery;
- snapshot pointer, mirror, validated/untested route exclusivity, and archive equality;
- capability claims and provider/model fail-closed policy; and
- absence of live installation, Task Observer mutation, and paid-service routes.

Before Gate 2, a preparer can compute the candidate projection identity without writing
a staged tree or archive. Set the three task-specific variables to reviewer-supplied
paths, then record the exact stdout in the review record:

```bash
PYTHONPATH=src python -m asme candidate-manifest \
  --source-root "$REVIEW_CANDIDATE_SOURCE" \
  --compatibility "$REVIEW_COMPATIBILITY_RECORD" \
  --attribution "$REVIEW_ATTRIBUTION_RECORD"
```

The command must report `live_mutation: false`. Its `tree_sha256` identifies the
in-memory projection, including the generated `bundle-manifest.json`. It does not prove
that a staged tree or archive exists, so it cannot make Gate 2 pass by itself.

When Hermes Agent 0.20.5 is available, run its official temporary-runtime validator:

```bash
hermes plugins doctor --ci adapters/hermes_plugin
```

Require one registered tool, zero hooks, and no errors. In an uninstalled source checkout,
record the expected warning that the declared `asme` Python dependency is
missing. Hermes must not install it automatically. Invoke
`wikiskill_capabilities` only when the exact Hermes version supplies a documented,
isolated handler-invocation path. Require `live_mutation: false`, a
`fail_closed_provider_route_lock` evidence item with `passed: false`, and no claim
stronger than `unknown` plus `unsandboxed`. If no public isolated invocation path
exists, record that dynamic check as `BLOCKED`; do not install the plugin, call private
Hermes APIs, or dispatch a model as a substitute. The official Doctor result still proves
discovery and registration only.

## Gate 2: frozen staged artifact

Gate 2 starts only after a preparer supplies:

- one frozen staged tree;
- its normalized path-byte manifest and tree SHA-256;
- the corresponding deterministic archive;
- the capability-report hash;
- the validated or approved-untested route record; and
- the Gate 2 comparator-policy hash.

The reviewer must work from a copy or read-only mount. Verify:

1. staged membership exactly matches the manifest;
2. every path is normalized, relative, regular, and non-symlinked;
3. every staged byte hash matches the archive member;
4. the archive has no extra, missing, duplicate, absolute, backslash, dot, or dotdot
   member;
5. capability-derived labels match the supplied report;
6. deterministic comparator mismatches fail;
7. allowed nondeterministic score or impact differences are report-only; and
8. no file changed after the frozen tree hash.

If no frozen staged artifact exists, Gate 2 is `BLOCKED`, not failed and not passed.

## Build and legal gates

The official Python distribution check is:

```bash
python -m build
```

If the `build` module is unavailable, report `BLOCKED: official build dependency
unavailable`. Do not install it or use a manual archive as a substitute without
action-time approval.

No release can pass while A4 is unresolved. Confirm:

- no `LICENSE` or `LICENSE.txt` exists;
- package metadata has no license claim or release date;
- NOTICE, PROVENANCE, and CITATION metadata preserve attribution without granting rights;
  and
- publication and distribution remain explicitly unauthorized.

## Report format

For every criterion, record:

| Field | Required value |
|---|---|
| ID | `SP-nnn`, `HF-Ann`, or reviewer finding ID |
| Status | `PROVEN`, `CONTRADICTED`, `MISSING`, `BLOCKED`, or `EXCLUDED-WITH-REASON` |
| Evidence | File and line, test node, command output, or immutable artifact hash |
| Scope | Exact claim the evidence supports |
| Finding | None, or the concrete mismatch |
| Required action | Minimal correction or named approval |

The final verdict must list Gate 0, Gate 1, Gate 2, build, legal, and live-runtime status
separately. A local code pass does not imply release approval.
