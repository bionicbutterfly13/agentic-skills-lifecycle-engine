# Agent Skill Mastery Engine

Agent Skill Mastery Engine is a runtime-neutral implementation of the experience-to-skill
evolution method described in the WikiSkill paper. One shared core owns evidence,
scoring, the persistent wiki, immutable skill snapshots, strict promotion, recovery,
and staging. Runtime adapters translate only measured capabilities and captured jobs.

This project was formerly named Askesis and published as the distribution
`askesis-agent-skill-mastery-engine`; the import package and CLI were `askesis`.

## Current status

This tree is a development candidate. It does not install itself into Hermes, Claude
Code, or Codex; `asme install` is an explicit, user-run step that copies only Agent Skill Mastery Engine's
own skill files (see [Install for Claude Code](#install-for-claude-code)). The tree has
not been approved for publication or distribution.
The historical Claude Revision 8 remains `NEEDS REVISION`; this implementation does
not claim a Codex `SOUND` verdict.

The current Hermes adapter reports `unknown` trace fidelity and `unsandboxed` before
role dispatch. Current verified public Hermes APIs do not provide an atomic provider
route lock with no fallback, so this adapter refuses role dispatch before any model
request. Provider-hidden reasoning cannot be relabelled as a paper-complete trace.

## What works

- Sealed, text-only train, validation, and test domains with collision-checked provenance
  markers generated for splits that omit them.
- Optional named observation seed with approval, visibility checks, and rollback.
- Prompt-only jobs bound to exact capability, provider, model, and snapshot records.
- Real subprocess extractors and scorers with no synthetic failure score.
- Deterministic train sampling and evidence-attested wiki changes.
- One create, patch, or no-action skill proposal.
- Strict validation plus fresh confirmation before promotion.
- Accepted, rejected, confirmation-rejected, no-action, and abandoned impact records.
- Invalid-manifest reset, intent-first recovery, staged archives, and archive readback.
- Pre-intent dependency rehashing plus an exact output-plan hash for every workflow command.
- Capability-bound package labels plus validated and explicitly untested staging routes.
  Neither route installs anything; the only install verb covers Agent Skill Mastery Engine's own skill.
- Staging lint for version, date, concrete triggers, and inherited observation provenance.
- A read-only observation candidate bridge that preserves Task Observer ownership and
  requires human review before any shared learning record is written.

## Boundaries

- Raw evidence comes from declared task and answer files, never live-session mining.
- The core has no network client and cannot write to live runtime skill roots.
- Task Observer, Hindsight, Second Mind, Hermes reflection, and external knowledge vaults
  remain separate systems. Optional observation seeds require explicit IDs, provenance,
  and hash-bound approval. Validated WikiSkill output can only produce a review candidate;
  it cannot write another system's memory or observation log.
- Only exact OpenAI-backed provider and model allowlists are accepted for prepared jobs.
- Candidate skills are staged only. Installation and publication are separate human
  approval gates. `asme install` never touches a staged candidate; it installs only
  Agent Skill Mastery Engine's own `SKILL.md` and companions and refuses staging and archive sources.
- Code is MIT licensed; docs, methodology, and templates are CC BY 4.0 (selected
  2026-09-01, Gate A decision A4, Option A). Projects using this work are asked, as a
  non-binding request, to link to manysaintvictormd.com on their project page.
  Publication of this tree remains a separate owner approval gate. See
  [NOTICE.md](NOTICE.md).
- Paper-derived method and locally authored algorithms are separated in
  [PROVENANCE.md](PROVENANCE.md); it records attribution without claiming legal novelty.

## Install for Claude Code

The published package carries Agent Skill Mastery Engine's own agent skill (`SKILL.md`, `PURPOSE.md`,
`NOTICE.md`, `LICENSE`, and `references/`). Installing it is a two-step, user-run
action; nothing is installed as a side effect of `pip` or `uv`.

```sh
uv tool install agent-skill-mastery-engine
asme install
```

`asme install` copies only those skill files into `~/.claude/skills/asme`. Pass
`--target DIR` for another skill directory, `--dry-run` to print the plan without
writing, and `--force` to replace an existing `asme` skill directory. The verb
refuses any `--source` under a staging or archive root and any staged bundle, so an
evolved candidate can never be installed this way. From a development checkout,
`python scripts/install_claude_skill.py` does the same job.

`uv tool install` places the `asme` entry point in `~/.local/bin`; add that
directory to `PATH` if `asme --version` is not found.

Verify:

```sh
asme --version
asme install --dry-run
ls ~/.claude/skills/asme
```

After a restart, Claude Code lists `asme` among its available skills.

Uninstall:

```sh
rm -r ~/.claude/skills/asme
uv tool uninstall agent-skill-mastery-engine
```

## Development checkout

Use an isolated environment. This installs the Python package for development; it does
not install a generated agent skill into any runtime.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m pytest
python scripts/stdlib_smoke.py
asme --help
```

The runtime package uses only the Python standard library. Pytest is needed only for the
development suite.

## Workflow

```text
init
  -> seed-observations | skip-seed
  -> baseline prepare / record / ingest / finalize
  -> train prepare / record / ingest / sample
  -> apply-wiki -> proposer-context -> apply-proposal
  -> validation -> gate -> confirmation -> gate
  -> test-baseline and test-final
  -> export to staging
```

Every command emits JSON. `status` is read-only. `recover` replays only a recorded
transaction. `reset-manifest` deletes invalid unconsumed evidence and the rejected
capture, but preserves its `.out.md` for audit until a corrected capture replaces it.
`export` and `package-untested` write only to the domain's staging and archive roots.

Read [SKILL.md](SKILL.md) for agent-facing operation, [references/integration.md](references/integration.md)
for adapter rules, and [references/verification/README.md](references/verification/README.md)
before interpreting a test result as a runtime claim.
