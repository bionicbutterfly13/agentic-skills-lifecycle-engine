# Verification status

## Completed locally

- Runtime-neutral unit and integration suite: 470 collected tests, exit code 0 on
  Python 3.14.6 in the current repaired tree.
- The stdlib smoke and CLI version path pass under locally installed Python 3.11.15,
  3.12.11, 3.13.12, and 3.14.6. Pytest is available only under 3.14 in the current
  environment, so the complete suite has not run under the other three interpreters.
  The thin Hermes plugin imports and returns the same conservative
  `unknown`/`unsandboxed`, non-OpenAI-backed report under all four interpreters.
- The extractor and scorer each use the same fixed 30-second evaluator constant. The
  workflow and CLI expose no timeout override, and the stdlib smoke uses that evaluator.
  Regression tests reject the former CLI override and verify both subprocess calls.
- All 106 locked source-parity rows have exactly one implementation-ledger entry.
- All 140 local `locked/...` registry locators resolve inside the candidate to one exact
  source-matrix row or architecture section, and the three copies match recorded hashes.
- Real subprocess extractor and scorer path.
- Baseline, train, Maintainer, Proposer, validation, confirmation, test, reset, and
  terminal outcome paths.
- Intent-first transaction and deterministic recovery fixtures.
- All 105 independently inventoried dependency cells across 14 operations have real
  operation-path pre-intent mutation tests, including arguments, state, clock, sealed
  files, routes, exact output plans, transient in-memory `PlannedValue` bindings, and
  recovery-source corruption.
- Snapshot, staging, archive readback, private-path scan, and live-root non-mutation.
- A stdout-only `candidate-manifest` command computes deterministic projection file
  hashes, the generated bundle-manifest hash, and the projected tree hash without
  writing a staged tree or release artifact.
- A read-only `observation-candidate` command emits only a human-review record after a
  validated export. It cannot read or write Task Observer state, and it preserves exact
  seed provenance, skill version, update date, description, triggers, accepted impact,
  test manifests, and delivery identity.
- Thin Hermes capability plugin with dispatch disabled.
- Hermes Agent 0.20.5's official `plugins doctor --ci` runtime path discovered the
  standalone manifest, imported `__init__.py`, registered exactly one declared tool and
  zero hooks, and reported no errors. The uninstalled checkout produces the expected
  warning for its declared `asme` Python dependency; Hermes does not install
  it automatically. A separate isolated test harness using the Doctor's
  temporary-runtime context invoked that registered tool and measured the public
  lifecycle surface as present, the fail-closed provider route lock as absent, the
  allowed labels as `unknown` and `unsandboxed`, and `live_mutation` as false. The
  official Doctor result is plugin-contract evidence; the handler invocation is
  version-specific test evidence. Neither is a live installation or provider-route proof.
- Public prose scan: no private absolute paths and no em dashes.
- A primary-source license decision brief compares MIT, Apache-2.0, CPAL-1.0,
  Attribution Assurance, and custom-license paths without granting rights or weakening
  the unresolved A4 gate.
- A public-safe independent-review protocol separates Gate 0 source fidelity, Gate 1
  implementation evidence, Gate 2 frozen-artifact review, official build, legal, and
  live-runtime status.
- The first independent implementation review returned `SOUND WITH REQUIRED CORRECTIONS`.
  Its accepted findings drove the current repairs; that report is not a pass for the
  changed candidate, which requires a fresh reviewer.

## Not completed

- Fresh installed-skill activation test.
- Independent post-implementation Architect review.
- Live Hermes conformance against a provider route lock.
- Claude Code or Codex execution adapter conformance.
- Publication, distribution, installation, or community release.
- An exact project license instrument. The owner requires free community use,
  attribution, and a project-page link to manysaintvictormd.com; no license grant has
  been applied.
- An official wheel and source-distribution build. None of the locally installed Python
  3.11.15, 3.12.11, 3.13.12, or 3.14.6 interpreters contains the `build` module, and no
  dependency was installed as a fallback.

Do not convert an unchecked item into a claim based on source inspection or a passing
narrow test.

Reviewer handoff: [independent-review-protocol.md](independent-review-protocol.md).
