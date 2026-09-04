# Stack Research

**Status:** Design input, not an implementation decision
**Source baseline:** Daedalus Phase 6 research completed 2026-09-03 and corrected 2026-09-04

## Recommendation

Keep the Lifecycle core runtime-neutral at the contract boundary. Select an
implementation language only after the first adapter contract and distribution targets
are settled. The current evidence does not justify choosing Python, TypeScript, or a
packaging channel yet.

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
