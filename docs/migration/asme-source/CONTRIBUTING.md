# Contributing

This repository is still a private development candidate. Code is MIT licensed and
docs are CC BY 4.0 (see LICENSE and NOTICE.md), but publication of this tree itself
remains owner-gated (Gate 4); no public release has occurred.

For local review work:

1. Create an isolated branch and linked worktree from the verified integration branch.
2. Keep runtime-neutral semantics in `src/asme`.
3. Keep runtime adapters thin. Do not copy lifecycle, scoring, gate, or transaction code
   into an adapter.
4. Add a failing test before changing behavior.
5. Run `python -m pytest` and `python scripts/stdlib_smoke.py` without network access.
6. Run the community safety and archive checks before proposing a release artifact.
7. Do not install, publish, commit, merge, or distribute on behalf of the owner without
   the corresponding action-time approval.

New capability claims require exact runtime-version evidence and negative tests. A config
setting or source inspection alone is not proof of isolation or trace fidelity.

