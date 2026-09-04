# Project Research Summary

## Research basis

Lifecycle begins from a 19-seed primary-source packet assembled in Daedalus. Eighteen
papers were reviewed end to end during the first pass, with ReasoningBank preserved in
the packet. The set includes systems foundations, `SKILL.state`, ACES, secure agent
skills, WikiSkill, SkillCAT, SkillRouter, SkillOps, TRUSS, SkillRet, Skills in the Wild,
SkillsBench, SkillLearnBench, MaliciousSkillBench, Agent Skill Security, SkillGuard,
Runtime Skill Audit, and CaMeL.

This directory synthesizes that work for project initialization. It is not a new paper
review, and it does not convert proposed methods into implemented capability.

## Key Findings

### Stack

The stable choice is a runtime-neutral contract with explicit adapters. The language,
package channel, schema technology, and initial supported-host list remain open because
those choices change compatibility and distribution behavior.

### Features

The minimum useful system is larger than a skill generator. It needs source provenance,
immutable candidates, paired evaluation, deterministic gates, bounded state, security
admission, a registry, rollback, and an auditable event ledger.

### Architecture

Models propose knowledge, candidate changes, and state patches. Deterministic code owns
mutation, identity, permissions, experimental assignment, stopping, evaluation, and
lifecycle transitions. Daedalus connects through the first host adapter.

### Principal risk

The easiest failure is to make an impressive self-editing demo and mistake it for
evidence of improvement. Lifecycle must preserve the negative result: if the paired
study cannot attribute benefit to the candidate skill, the skill does not advance.

## Implications for Roadmap

- Start with schemas, identities, events, and gates before adding autonomous generation.
- Use the CPU-local synthetic k-nearest-neighbor study as the first end-to-end slice.
- Keep promotion study-local until independent confirmation exists.
- Delay broad distribution claims until at least two host adapters satisfy the same
  contract tests.
- Audit and salvage ASME only after the new canonical boundaries are explicit.

## Sources

The canonical source analysis currently remains in the Daedalus Phase 6 research
artifacts on branch `docs/agentic-skills-lifecycle-research`. Primary papers are
identified there by author and arXiv version. Those artifacts should be migrated with
their provenance before Daedalus's temporary research branch is retired.
