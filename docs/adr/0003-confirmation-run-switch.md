# ADR-0003: Confirmation-run switch

Status: accepted 2026-09-22

## Context

The paper's Algorithm 1 promotes a skill after a single validation run showing a strict
improvement. The project's promotion process instead requires independent confirmation
before promotion.

## Decision

Add a study-manifest switch for the confirmation run. The switch is off for runs
labelled paper_comparable, which keep a single validation run with a strict comparison
matching Algorithm 1. The switch is on for production promotion, which requires two
strict wins with the promotion score set to the minimum of the validation and
confirmation scores.

## Consequences

Paper-comparable runs and production-promotion runs use different manifests. The switch
value must be recorded per run for reproducibility.
