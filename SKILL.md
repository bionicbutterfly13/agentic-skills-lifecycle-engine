---
name: asme
description: Evolve text-only agent skills from declared task sets using sealed evidence, persistent wiki patterns, strict validation, and staging-only delivery. Use when running controlled experience-to-skill experiments, never live-session mining or automatic installation.
version: 0.1.0
last_updated: 2026-08-31
---

# Agent Skill Mastery Engine

Use the runtime-neutral CLI for state and evidence. Use a runtime adapter only for
capability measurement and fresh-session execution. The adapter never owns scoring,
promotion, or packaging.

## Triggers

1. A user asks to evolve a reusable skill from a declared train, validation, and test set.
2. A user asks to reproduce or study the WikiSkill method with truthful capability labels.
3. A user asks to stage an evolved skill for review without installing it.
4. A maintainer needs deterministic recovery, evidence manifests, or cross-runtime parity.

## Required order

1. Read [PURPOSE.md](PURPOSE.md) and [references/fidelity.md](references/fidelity.md).
2. Run `asme status` for an existing domain. Never infer its phase.
3. For a new domain, declare every task, answer, prompt, extractor, scorer, tool profile,
   visibility, read resource, and iteration limit at `init`.
4. Choose exactly one pre-baseline path: `skip-seed` or a human-approved
   `seed-observations` packet.
5. Use the phase reported by `status`. Do not skip Maintainer, Proposer, validation,
   confirmation, or test gates.
6. Before staging, require each evolved `SKILL.md` to have three-part versioning, a
   canonical update date, a bounded `Use when` description, and at least two concrete
   numbered triggers. Require its `PURPOSE.md` to preserve the exact sorted
   `origin_observations` inherited from approved seed evidence.
7. Stage with `export` only after both test manifests pass. Supply the exact capability
   report used by both manifests; delivery derives trace and isolation labels from it.
   `package-untested` needs a separate hash-bound approval and explicit untested labels.
8. After a validated export, `observation-candidate` may print one review-only reusable
   signal. It cannot write Task Observer or any shared log. Stop at staging: no command
   installs an evolved candidate. `asme install` copies only Agent Skill Mastery Engine's own `SKILL.md`
   and companions into a Claude Code skill directory and refuses staging and archive
   sources.

For conformance and crash-equality runs, pass the same timezone-aware `--clock` value to
every CLI command. The core records that value in each transaction intent.

## Runtime rules

- Require an exact OpenAI-backed provider and model allowlist before preparing jobs.
- Launch each inference or confirmation task in a fresh runtime session.
- Treat `unknown`, `final_only`, `observable_transcript`, and `paper_complete` as measured
  labels, never preferences.
- Add `unsandboxed` whenever any isolation boundary is procedural, absent, or unknown.
- Never call a fallback provider outside the exact allowlist.
- Never mine ambient chats, Hindsight, Task Observer, a vault, or session history as raw
  WikiSkill evidence.

## Hermes

Read [adapters/hermes_plugin/README.md](adapters/hermes_plugin/README.md). The current
Hermes plugin exposes a read-only capability report. Role dispatch is disabled because
the verified public API does not provide an atomic provider route lock with no fallback.
Do not bypass that refusal. A separate shell wrapper may orchestrate core CLI commands,
but it must return a contract-valid captured execution and pass the same route checks.

## References

- [Method and paper boundary](references/paper-notes.md)
- [Capability and claim labels](references/fidelity.md)
- [Runtime-neutral integration](references/integration.md)
- [Implementation parity](docs/implementation-parity.md)
- [Verification status](references/verification/README.md)
