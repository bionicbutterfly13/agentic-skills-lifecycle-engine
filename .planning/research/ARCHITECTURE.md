# Architecture Research

**Status:** Proposed boundary derived from the reviewed systems, state, learning,
evaluation, operations, and security papers

## Component boundaries

1. **Knowledge layer** stores source-grounded claims, provenance, confidence, and
   evidence links.
2. **Candidate builder** converts bounded evidence into an immutable skill package.
3. **Admission layer** freezes bytes, calculates identity digests, checks licenses and
   policy, and rejects unresolved risk.
4. **Host adapter** translates a supported runtime's skill discovery, permissions,
   execution, and event interfaces.
5. **Study controller** creates paired arms, resets state, enforces caps, and records
   every transition.
6. **Evaluator** scores deterministic outcomes first and keeps model judgment
   diagnostic rather than decisive.
7. **Registry** records lifecycle status, compatibility, evidence, dependencies,
   promotion scope, rollback, quarantine, and retirement.
8. **Journal exporter** projects immutable events into human-readable research notes
   without becoming the source of truth.

## Data flow

```text
sources -> evidence-backed wiki -> candidate package -> freeze and admission
       -> host adapter -> paired study -> evaluator -> scoped lifecycle decision
       -> registry and event ledger -> journal projection
```

## Trust boundary

Model roles may propose claims, candidate edits, and state patches. Deterministic code
validates those proposals and owns all mutations, hashes, permissions, experimental
assignment, stopping, and promotion decisions.

## Build order

1. Define schemas and immutable identities.
2. Implement the event ledger and deterministic controller.
3. Implement candidate admission and capability checks.
4. Implement the Daedalus adapter.
5. Build the synthetic k-nearest-neighbor study fixture.
6. Add evaluation, scoped promotion, rollback, and journaling.
7. Verify a second host adapter before claiming runtime neutrality in practice.

