# Contributing to Lifecycle

Lifecycle is the current development home for the imported Agent Skill Mastery
Engine. The [exact source contribution protocol](docs/migration/asme-source/CONTRIBUTING.md)
is preserved for historical context, including its earlier private-candidate
status. ASME has a verified public v0.2.0 release; this import does not constitute
a new Lifecycle publication.

1. Read AGENTS.md and the active GSD plan before editing. Start work through the
   repository's GSD workflow.
2. Create a separate feature branch and linked worktree from the verified current
   integration branch. Preserve other sessions' work.
3. Keep runtime-neutral behavior in `src/asme` and adapters thin. Preserve the
   compatibility namespace, CLI, distribution, and version unless an approved
   feature explicitly changes them.
4. Add a failing regression test before behavioral changes. Preserve existing
   tests and do not weaken checks to obtain a pass.
5. Run the complete `python3 -m pytest` suite and
   `python3 scripts/stdlib_smoke.py` offline. Record the exact scope and outcome;
   synthetic fixtures are not empirical model evidence.
6. Require independent review and the community-safety/archive checks before
   release claims. Capability claims need measured runtime-version evidence and
   negative tests; source inspection alone does not prove isolation or trace fidelity.
7. Commit and merge only within the user's authorized work. The current WikiSkill
   v1 goal explicitly authorizes verified feature commits, integration, and removal
   of clean, merged, task-owned branches and worktrees. Paid execution and
   publication require approval. The original ASME repository cannot be deleted
   without a fresh lossless salvage audit and explicit action-time authorization.

Code is MIT licensed. Documentation, methodology, and templates are CC BY 4.0;
preserve the obligations in [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
