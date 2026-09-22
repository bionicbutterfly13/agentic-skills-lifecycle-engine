# ADR-0004: Detective-mode Proposer

Status: accepted 2026-09-22

## Context

The paper never ablates the Proposer's reasoning mode, so whether multi-turn reading
before proposing a change actually helps is unproven either way.

## Decision

The Proposer defaults to detective mode: a multi-turn ReAct loop that reads the wiki and
prior traces via read_file, reading at least 4 traces before proposing, with every read
logged in the transaction journal. A study flag can force single-shot mode instead, as a
local ablation.

## Consequences

Detective mode is the parity-claim default. Any parity claim made using the single-shot
ablation flag must say so explicitly, since the paper never validated single-shot mode
either way.
