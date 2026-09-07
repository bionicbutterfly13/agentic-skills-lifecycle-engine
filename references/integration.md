# Runtime-neutral integration

## Shared core boundary

The `asme` Python package owns contracts and state. A runtime adapter may:

1. Probe its exact runtime and emit a `CapabilityReport`.
2. Receive a hash-bound `AdapterJob` for one fresh session.
3. Return one `CapturedExecution` bound to the job, prompt, snapshot, output, and
   capability report.
4. Provide deterministic adapter files for staging.

An adapter may not fork lifecycle, evaluation, wiki, snapshot, gate, recovery, or package
semantics.

Validated delivery takes the exact `CapabilityReport` used by both test manifests. It
refuses if either manifest has another capability hash, the compatibility record names a
different adapter or untested runtime version, or README/PURPOSE labels differ from the
report's measured trace fidelity and isolation claim.

The optional CLI `--clock` input is a deterministic test control. When supplied, the
core normalizes it to UTC and records it in every mutation intent; adapters must still
preserve their own captured execution start and finish times.

## Task Observer and Claudeception-derived benefit bridge

Task Observer remains responsible for watching live work, assigning confidence,
clustering observations, and applying its own deprecation and archive rules. Its
immediate authoring path preserves the useful behavior formerly supplied by
Claudeception: a verified, non-obvious discovery can become a skill without waiting for
a weekly review. WikiSkill serves a different job, declared-task evolution against
sealed train, validation, and test evidence.

The systems exchange explicit records only. WikiSkill never scans Task Observer state,
writes its shared observation log, mines ambient sessions, or installs a skill. An
external reviewer or adapter owns every transfer between them.

| Benefit | Disposition | Portable contract |
|---|---|---|
| `live_reusable_signal_observation` | `task_observer_owned` | Task Observer decides whether a live event is reusable and records its evidence. WikiSkill does not observe live work. |
| `reviewed_observation_seed` | `explicit_approval_bound_input_bridge` | A human names observation IDs and supplies a visibility-safe packet plus its hash-bound approval before baseline evidence exists. |
| `create_patch_no_action` | `shared_semantic_analog` | Task Observer authoring and the WikiSkill proposer both preserve create, patch, or no-action outcomes, while keeping their separate evidence and gate rules. |
| `version_date_trigger_authoring` | `wikiskill_staging_lint` | Every staged evolved skill must provide three-part versioning, a canonical date, a bounded `Use when` description, and at least two concrete numbered triggers. |
| `verified_reusable_content` | `shared_evidence_outcome` | Task Observer requires a verified discovery; WikiSkill requires an accepted active impact, final test manifests, and validated delivery identity before it emits a candidate. |
| `current_research` | `external_adapter_or_human_review` | Research is supplied through declared resources or external review. The runtime-neutral core has no network client and cannot silently refresh claims. |
| `confidence_and_clustering` | `task_observer_owned` | WikiSkill retains measured scores and trace provenance but does not translate them into Task Observer confidence or clustering decisions. |
| `deprecation_and_archival` | `task_observer_owned` | Task Observer retains its observation lifecycle. WikiSkill keeps its paper-faithful accumulating wiki and immutable run evidence. |
| `wikiskill_observation_candidate` | `explicit_review_only_output_bridge` | A validated export may produce one compact `pending_human_review` record with `shared_log_write_allowed` set to false. |
| `delivery_hygiene` | `shared_staging_gate_human_install` | Both workflows sweep staged bundles and stop before installation. A human owns any later live-runtime action. |

### Reviewed input bridge

1. A human selects the exact Task Observer observation IDs for one domain.
2. An external procedure creates a seed packet and separate approval record.
3. Run `asme seed-observations --packet <packet.json> --approval
   <approval.json>` before baseline evidence exists.
4. The core records the consumed approval and seed manifest. Pattern pages and evolved
   `PURPOSE.md` files preserve the sorted `origin_observations` list.

### Review-only output bridge

After a validated export, run:

```sh
asme observation-candidate \
  --domain <domain-id> \
  --domain-root <domain-root> \
  --skill <skill-name>
```

The command is read-only and prints JSON. It refuses unless the active snapshot has one
accepted impact, both final test manifests, one validated delivery identity, valid skill
authoring metadata, and valid seed provenance. Its output has
`review_status: pending_human_review` and `shared_log_write_allowed: false`. A human then
decides whether an external Task Observer workflow should accept, reject, or rewrite the
candidate. The WikiSkill core does not perform that decision or write.

### Hermes metacognitive boundary

Hermes reflection, compact recall, lesson distillation, and any deeper synthesis service
remain external learning systems. They may propose reviewed inputs or consume an approved
candidate through their own versioned JSON adapters. WikiSkill never writes their memory,
stores raw reflection transcripts, or turns a reflection into training evidence without
an explicitly declared task set.

## Update-safe Hermes shape

The Hermes integration is a standalone user plugin plus optional shell orchestration. It
does not patch the Hermes repository, vendor an upstream file, or depend on a private
internal import for state semantics. A Hermes update can replace upstream code without
overwriting the core package.

After any Hermes update:

1. Run the capability probe against the new exact version.
2. Run adapter conformance and negative route tests.
3. Add the version to compatibility metadata only if those tests pass.
4. Keep dispatch disabled if the provider route cannot fail closed.

A hook or shell script may call `asme` commands outside the plugin. It must
not infer success from exit code alone: read the JSON result, preserve job hashes, and
return a contract-valid capture. Scripts must not read ambient session history or write a
live skill root.

## Claude Code and Codex

Claude Code and Codex adapters should implement the same adapter port. They should remain
thin projections over the core, with runtime-specific capability evidence and no copied
state machine. No Claude Code or Codex execution adapter is included in this development
scope.
