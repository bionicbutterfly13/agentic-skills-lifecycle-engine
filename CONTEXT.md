# Context

Glossary of WikiSkill parity terms used across this project's ADRs and requirements.

## Method Parity

Running the paper's four roles with the paper's prompts on one domain, without claiming
any numeric results.

## Empirical Parity

A one-benchmark numeric comparison against the paper's reported results, revisited only
after a real end-to-end method-parity run has completed.

## Confirmation Run

The second, independent evaluation pass required before production promotion, scored as
the minimum of the validation and confirmation runs, requiring two strict wins.

## Paper-Comparable Run

A run labelled paper_comparable in the study manifest that keeps Algorithm 1's single
validation run with a strict comparison and skips the confirmation run.

## Detective Mode

The Proposer's default multi-turn ReAct behavior: reading at least 4 traces from the
wiki and prior runs, with every read logged in the transaction journal, before
proposing a change.

## Ablation

A study flag that turns off a default, such as running the Proposer single-shot instead
of detective mode, to test whether the default actually helps, since the paper never
tested it either way.

## Direct Adapter

The adapter connecting Lifecycle straight to a bare local model (Ollama) instead of
routing through a host runtime like Hermes, Codex, or Claude Code.

## Study Manifest

The declared configuration for one study run, including which switches (confirmation
run on/off, ablation on/off) apply to that run.
