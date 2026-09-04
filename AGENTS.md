<!-- GSD:project-start source:PROJECT.md -->

## Project

**Agentic Skills Lifecycle Engine**

Agentic Skills Lifecycle Engine is an independently installable, open-source plugin
that helps supported AI runtimes acquire, test, retain, revise, and retire skills.
Lifecycle is the short project name. Daedalus is its first reference adapter and
proving host, not its owner.

The engine combines source-grounded knowledge, bounded skill state, controlled
experiments, reproducible evidence, and security gates. A shared installation may
serve several AI runtimes, but every host integration remains explicit and testable.

**Core Value:** No skill is treated as improved unless a reproducible, controlled evaluation shows
that it helps without violating correctness or safety.

### Constraints

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
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## Recommendation

## Required technical properties

- Deterministic orchestration owns freeze, digest, admission, evaluation, promotion, rollback, and stopping decisions.
- Host adapters translate runtime-specific skill discovery, invocation, permissions, event emission, and installation into stable core contracts.
- Immutable artifacts and append-only events preserve the identity of candidates, evaluations, and decisions.
- Schemas validate skill packages, permissions, evidence records, state patches, and study manifests before mutation.
- Tests must run locally without paid providers for the first vertical study.
- Distribution must support a shared installation while allowing each experiment to pin an exact version and content digest.

## Decisions still required

- Core implementation language and supported versions
- Package and plugin distribution channels
- Initial supported host list beyond Daedalus
- Schema technology and canonical serialization rules
- Local artifact store and event-ledger format

## Avoid

- Coupling the core package to Daedalus internals
- Treating an LLM's self-assessment as a promotion decision
- Loading mutable skills without digest verification
- Choosing a package ecosystem before supported-host requirements are explicit

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
