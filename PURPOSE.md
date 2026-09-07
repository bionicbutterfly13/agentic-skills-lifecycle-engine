# Purpose and status

Agent Skill Mastery Engine is a runtime-neutral, staging-only implementation inspired by the
WikiSkill experience-to-skill evolution method. It keeps the state machine, evidence,
scoring, wiki, snapshots, promotion, recovery, and packaging in one shared core. Runtime
adapters translate only measured capabilities and captured executions.

## Development status

- package_status: development_candidate_not_installed
- test_evaluation: development_suite_passed_515_tests
- skill_activation_test: not_run
- task_observer_input_bridge: explicit_approval_bound
- task_observer_output_bridge: pending_human_review_only
- shared_observation_log_write: forbidden
- hermes_dispatch: disabled_fail_closed
- hermes_trace_fidelity: unknown
- hermes_isolation: unsandboxed
- paper_complete_claim: false
- live_installation: authorized_by_owner_2026-09-02_claude_code_and_evoscientist_skill_dirs
- license: mit_code_ccby4_docs_selected_20260901_gate_a_option_a
- publication: blocked_pending_gate_4_owner_approval
- distribution: blocked_pending_gate_4_owner_approval

The local test suite proves the tested core contracts. It does not prove performance
improvement, paper-equivalent traces, runtime isolation, installed skill behavior, or
compatibility with an untested Hermes, Claude Code, or Codex version.

## Non-goals

- No ambient session mining.
- No automatic modification of Task Observer, Hindsight, Second Mind, or a knowledge vault.
- No replacement of Task Observer's live observation, confidence, clustering, immediate
  skill authoring, deprecation, or archive responsibilities.
- No network client, paid service, provider fallback, or live skill-root write by the
  evolution core. The only installer, `asme install`, copies Agent Skill Mastery Engine's own skill files
  and never an evolved candidate.
- No claim that the historical Claude Revision 8 was approved or received a Codex
  `SOUND` verdict. Its retained status is `NEEDS REVISION`.
