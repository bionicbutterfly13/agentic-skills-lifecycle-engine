# ADR-0001: Method parity target

Status: accepted 2026-09-22

## Context

The 2026-09-22 WikiSkill parity grill considered three possible parity targets for
Lifecycle's first study: (a) method parity, running the paper's four roles with the
paper's own prompts on one domain without claiming numeric results; (b) one-benchmark
empirical parity, a numeric comparison against the paper's reported results; and (c) full
five-benchmark reproduction of the paper.

## Decision

Method parity (a) is the target now. The loop must run the paper's four roles with the
paper's prompts on one domain, and no performance numbers may be claimed from this work.
One-benchmark empirical parity (b) is revisited only after one real end-to-end
method-parity run has completed. Full reproduction (c) is not scheduled.

## Consequences

No performance numbers may be claimed until an empirical-parity run happens. The loop
must run the paper's four roles with the paper's prompts on one domain before any parity
claim, empirical or otherwise, is made.
