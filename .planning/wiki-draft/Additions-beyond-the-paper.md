# Additions beyond the paper

Lifecycle implements the WikiSkill method described in Tang et al. (arXiv 2608.27454, CC BY 4.0). This page lists every place Lifecycle deviates from or extends the paper. Each entry states what the paper does, what Lifecycle does, and why the change was made.

## Confirmation-run switch

What the paper does: Algorithm 1 promotes a skill after a single validation run showing a strict improvement.

What Lifecycle does: adds a study-manifest switch. Runs labelled paper_comparable keep the paper's single validation run with a strict comparison, so method parity holds. Production promotion instead requires two strict wins, with the promotion score set to the minimum of the validation and confirmation scores.

Why: a single run risks promoting a skill that only helped by chance. The switch keeps the paper-comparable path unmodified for parity claims while adding a stricter bar for any promotion meant for real use.

Status: implemented 2026-09-22. `asme init --confirmation off` gives the paper's single-run gate; the default, `required`, keeps two strict wins with the lower score recorded. The setting is sealed in the domain record, and the impact history refuses an accepted entry whose score count does not match the domain's mode. See src/asme/lifecycle.py and src/asme/workflow.py.

## Transaction journal with digest binding

What the paper does: does not specify an append-only record binding each run to the exact skill bytes evaluated.

What Lifecycle does: logs every read, write, and decision to a transaction journal, with each entry bound to a content digest of the skill package in play.

Why: without a digest-bound journal, a later reader cannot confirm which exact bytes produced a given result, which conflicts with the project's reproducibility requirement.

Status: implemented. See src/asme/transaction.py and src/asme/snapshot.py; every operation records intent before mutation and binds reads and writes to content digests.

## Wiki Maintainer attestation field

What the paper does: does not require an explicit attestation from the wiki-maintaining role.

What Lifecycle does: adds an attestation field the Wiki Maintainer role must fill when committing a skill change to the wiki.

Why: creates an auditable point of accountability for wiki-side changes, separate from the paper's four-role loop.

Status: implemented. See the attestation validation in src/asme/wiki.py, which requires class coverage and per-pattern evidence bound to the sampled trace IDs.

## Detective-mode flag (single-shot ablation)

What the paper does: does not ablate the Proposer's reasoning mode.

What Lifecycle does: runs the Proposer in detective mode by default, a multi-turn ReAct loop that reads the wiki and prior traces (at least four traces read before proposing), with every read logged in the transaction journal. A study flag allows running the Proposer single-shot instead, as a local ablation.

Why: the paper never tested whether multi-turn reading helps the Proposer, so its effectiveness is unproven. The ablation flag lets Lifecycle test that assumption instead of taking it on faith.

Status: implemented 2026-09-23. See scripts/run_proposer.py, with offline tests in tests/test_run_proposer.py. Detective mode (`--mode detective`, the default) runs a multi-turn ReAct loop against a virtual, read-only filesystem built only from `workflow.proposer_context()`'s train-only payload (wiki pages, train traces, active skill), exposed through a `read_file` tool call; any path outside that set, including a validation- or test-split id or a path-traversal attempt, is refused and logged rather than served. A `finish()` call is refused once and must be retried if fewer than 4 distinct traces were read, or if the proposal cites a trace_id never actually read via `read_file`; a second insufficient `finish()` raises. Every read attempt, successful or refused, is journaled to a persisted reads log (path, sha256 of the content returned, turn number). `--mode single-shot` is the local ablation flag: one call with the full context payload, no tool loop, no retry on a malformed response.

## Maintainer driver's retry policy

What the paper does: Algorithm 1 does not specify a retry mechanic for a malformed Wiki Maintainer response; a single call is implied.

What Lifecycle does: `scripts/run_maintainer.py` retries a Wiki Maintainer call up to 3 attempts total, re-prompting with the validator's own `ContractError` text appended after the first failure. Every raw attempt is persisted under the run directory regardless of outcome.

Why: bounded resilience against transient model formatting errors (a slightly malformed JSON object, a missing field), not a paper mechanism. The bound is small and fixed so a persistently broken model still fails loudly rather than looping.

Status: implemented 2026-09-23. See `MAX_ATTEMPTS = 3` in scripts/run_maintainer.py, with scenario tests in tests/test_run_maintainer.py covering first-try success, retry-then-success, and exhausted retries.

## Driver-inserted context_hash (Proposer only)

What the paper does: does not specify who computes the binding hash between a Proposer's context and its decision, since the paper has no `context_hash` field at all.

What Lifecycle does: `scripts/run_proposer.py` never asks the model to compute `context_hash`; the model's `finish()` payload (detective mode) or single-shot response is not trusted to supply it correctly, since it cannot reliably reproduce the exact byte-canonical `proposer_context()` representation. The driver computes `sha256` of the exact context bytes itself and inserts (overwrites) `context_hash` mechanically before calling `workflow.apply_proposal`. This applies to the Proposer path only; the Maintainer contract has no `context_hash` field and this mechanic does not apply there.

Why: a model-supplied hash is a claim the model could get wrong or never has enough information to compute exactly; a driver-computed hash is a mechanical binding that cannot drift from the actual input. `asme.proposal.validate_proposal`'s own equality check against the true context hash remains a second, independent gate even if the driver-side overwrite were ever removed.

Status: implemented 2026-09-23. See the `# Driver-inserted: mechanical binding the model cannot compute.` comment in scripts/run_proposer.py's detective-mode `finish` handling, and `test_detective_context_hash_is_always_driver_computed` in tests/test_run_proposer.py.

## Direct local-model adapter

What the paper does: assumes an OpenAI-routed model as the Inference Agent runtime (inherited into this codebase from the prior ASME implementation, not paper-mandated).

What Lifecycle does: adds a direct adapter for a bare local model (tested against Ollama on the development machine, running hermes3 and deepseek-r1) as the first Inference Agent runtime. Host adapters for Hermes, Codex, and Claude Code are planned after the loop is proven on the local adapter.

Why: removes a paid-provider dependency for the first vertical study and keeps host integration explicit and separate from core orchestration, per the project's host-independence constraint.

Status: implemented 2026-09-22. See adapters/direct, with offline contract tests in tests/test_direct_adapter.py. It reports final_only fidelity and refuses the sandboxed and unseen labels, because it cannot constrain the model server it talks to.

## Seed observations

What the paper does: does not specify a mechanism for injecting starting observations into a new wiki before any trial has run.

What Lifecycle does: adds seed observations as an explicit input to bootstrap a wiki's initial state.

Why: gives a new study a documented, inspectable starting point instead of an empty or implicitly seeded wiki.

Status: implemented. See src/asme/seed.py and the seed transitions in src/asme/lifecycle.py; seeding is optional, transaction-bound, and reversible before the baseline is finalized.

## Staging archive

What the paper does: does not define a holding area between an evaluated candidate and its promotion.

What Lifecycle does: adds a staging archive that holds candidate skills and their evidence records after evaluation and before a promotion decision is finalized.

Why: separates "evaluated" from "promoted" as distinct, auditable states, consistent with the project's requirement that promotion needs an auditable decision record.

Status: implemented. See src/asme/delivery.py and src/asme/package.py; export stages a verified skill archive and never installs into a live runtime skill root.

## Answer-budget guard in the inference prompt

What the paper does: the LiveMath inference prompt (Appendix E.1) asks the model to think step by step and place the final answer in answer tags, with no instruction about running out of output budget.

What Lifecycle does: adds one sentence telling the model to stop reasoning and commit to its best current choice rather than exhausting its output budget, because a response with no answer tag scores nothing.

Why: a measured run on qwen3.5:4b spent an entire 3072-token budget inside its reasoning block and emitted no answer tag, producing an invalid manifest after 26 minutes. The engine correctly refused to score it, but the trial yielded no evidence at all. The guard converts a wasted trial into a usable one.

Effect on parity: this is a deviation from the paper's prompt text. Any run labelled paper_comparable must use the verbatim prompt in .planning/paper-prompts/E1-inference-agent-prompts.md instead, and accept the resulting truncation rate as part of the measurement.

Status: implemented 2026-09-22 in scripts/build_livemath_cartridge.py.
