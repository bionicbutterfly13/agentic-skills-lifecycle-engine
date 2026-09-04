# Feature Research

**Status:** Synthesis of the reviewed primary-source packet, not shipped capability

## Table stakes

- Source and provenance records for knowledge entering the lifecycle
- Explicit skill package identity, version, digest, permissions, and compatibility
- Candidate creation from bounded evidence
- Paired evaluation against a declared baseline or withheld-skill arm
- Deterministic acceptance gates with abstention on weak evidence
- Promotion, rollback, quarantine, retirement, and audit history
- Runtime mediation under default-deny capabilities
- Exact study manifests and immutable result artifacts
- Typed, bounded execution state with validated patches
- Explicit host adapters for discovery, loading, execution, and journaling

## Differentiators to test

- Persistent wiki knowledge that improves candidate quality on held-out tasks
- Contrastive extraction from matched successes and failures
- State that preserves long-horizon performance with less context
- Confirmation runs that distinguish durable improvement from sample overfit
- Cross-runtime reuse without hiding host-specific behavior
- An evidence graph connecting sources, claims, candidate changes, tests, and decisions

## Anti-features

- Automatic global promotion from one passing study
- Unbounded self-editing or state mutation
- Live web access inside frozen evaluation arms
- Retrieval relevance treated as execution permission
- Training-task replay treated as proof of generalization
- A universal adapter that silently guesses host behavior
- Public self-improvement claims based on architecture or synthetic fixtures alone

## First vertical slice

The first slice tests one candidate skill on hidden variants of a CPU-local synthetic
k-nearest-neighbor task. It includes a skill-enabled arm and a target-withheld arm,
identical support skills, fresh sessions, a frozen offline packet, hidden traps, and a
correctness-first acceptance rule.

