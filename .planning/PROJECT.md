# Agentic Skills Lifecycle Engine

## What This Is

Agentic Skills Lifecycle Engine is an independently installable, open-source plugin
that helps supported AI runtimes acquire, test, retain, revise, and retire skills.
Lifecycle is the short project name. Daedalus is its first reference adapter and
proving host, not its owner.

The engine combines source-grounded knowledge, bounded skill state, controlled
experiments, reproducible evidence, and security gates. A shared installation may
serve several AI runtimes, but every host integration remains explicit and testable.

## Core Value

No skill is treated as improved unless a reproducible, controlled evaluation shows
that it helps without violating correctness or safety.

## Requirements

### Validated

(None yet. Research and experimental design exist, but the engine has not been
implemented or run.)

### Active

- [ ] Provide a runtime-neutral lifecycle core with explicit host adapters.
- [ ] Treat knowledge seeds, sources, provenance, and evidence quality as first-class
      inputs.
- [ ] Support a governed lifecycle for proposing, testing, promoting, rolling back,
      quarantining, and retiring skills.
- [ ] Record the exact plugin version and content digest used by every experiment.
- [ ] Support typed, bounded `SKILL.state` that resets at the declared experimental
      boundary and changes only through validated patches.
- [ ] Enforce default-deny access to candidate instructions, state, tools, and study
      artifacts.
- [ ] Build Daedalus as the first reference adapter without coupling the core to
      Daedalus.
- [ ] Run the first controlled study on a CPU-local synthetic k-nearest-neighbor task.
- [ ] Package the project for open-source installation across supported AI runtimes.
- [ ] Keep public journals explicit about what is observed, inferred, planned, and
      still unknown.

### Out of Scope

- Copywriting systems from NoeAI, RMBC, Great Leads, or Jon Benson are deferred until
  the lifecycle core proves its experimental contract.
- Ecosystem-scale and multi-agent performance claims are deferred until the remaining
  research queue has been read and tested.
- Daedalus-specific ownership of the engine is excluded because Lifecycle must remain
  independently installable and reusable.
- Continued development of the existing Agent Skill Mastery Engine is excluded after
  reusable code, contracts, tests, provenance, license obligations, and unique evidence
  are audited and salvaged.
- Public performance or self-improvement claims are excluded until live controlled
  evidence exists.

## Context

The initial design work was conducted inside a Daedalus research branch on 2026-09-03
and 2026-09-04. The research packet contains 19 primary paper seeds. Eighteen were read
end to end during the first pass, while ReasoningBank remains preserved in the packet.
The sources cover systems foundations, `SKILL.state`, knowledge acquisition, routing,
evaluation, operations, and security.

The first study is deliberately small. It compares a skill-enabled arm with a
target-skill-withheld arm on hidden variants of a CPU-local synthetic k-nearest-neighbor
task. Fresh isolated roles, a pinned model, a frozen offline packet, hidden task traps,
and an event ledger are part of the planned contract. Correctness is the hard gate;
efficiency is secondary. Promotion is study-local, and weak evidence requires
abstention.

No Lifecycle implementation or live study exists yet. The current evidence supports a
project definition and a falsifiable first experiment, not a claim that the engine
works.

## Constraints

- **Scientific integrity**: Absence of evidence is failure to promote, not permission
  to infer success.
- **Reproducibility**: Every study records the exact plugin version and content digest
  so a later reader can identify the bytes that produced the result.
- **Host independence**: The core cannot depend on Daedalus internals; integrations use
  explicit adapters.
- **Security**: Candidate skills and state operate under least privilege and default
  denial.
- **State**: `SKILL.state` is typed, bounded, validated, and reset at the declared arm
  or trial boundary.
- **Evidence**: Training traces alone do not establish skill quality; promotion needs a
  held-out evaluation and an auditable decision record.
- **Claims**: Public writing must distinguish research, design, implementation, run
  evidence, and release status.
- **Migration**: The temporary Agent Skill Mastery Engine cannot be deleted until a
  fresh lossless salvage audit passes and Dr. Mani authorizes deletion at action time.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use Agentic Skills Lifecycle Engine as the full project name and Lifecycle as the short name | Keeps the public identity precise while making ordinary references concise | Settled |
| Maintain Lifecycle as an independent open-source repository | Daedalus and other projects must be consumers rather than owners | Settled |
| Use a runtime-neutral core with explicit host adapters | Shared behavior belongs in one engine while host differences stay visible | Pending validation |
| Make Daedalus the first reference adapter and proving host | It provides a scientific operating environment without defining the whole product | Settled |
| Begin with a CPU-local synthetic k-nearest-neighbor study | The first experiment should test the lifecycle method without GPU cost or domain ambiguity | Pending execution |
| Pin plugin version and content digest in every study | Central updates must not erase the exact implementation used by an earlier result | Settled |
| Retire the existing Agent Skill Mastery Engine only after verified salvage | Prevents lost work, duplicate systems, and discarded provenance | Pending audit |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? Move them to Out of Scope with the reason.
2. Requirements validated? Move them to Validated with the phase reference.
3. New requirements emerged? Add them to Active.
4. Decisions to log? Add them to Key Decisions.
5. "What This Is" still accurate? Update it if the project has drifted.

**After each milestone** (via `$gsd-complete-milestone`):
1. Review every section.
2. Confirm that the Core Value still controls tradeoffs.
3. Audit Out of Scope reasons.
4. Update Context with verified project state.

---
*Last updated: 2026-09-04 after initialization*
