# Quick 260906-tz7: Bounded F-05 recovery

## GSD entry and authority

The native `workflows/quick/steps/quick-verification.md` Step 6.5 routes `gaps_found` to re-running an executor to fix the gaps. The parent ran `GSD_RUNTIME=codex node /Users/manisaintvictor/.claude/gsd-core/bin/gsd-tools.cjs query verification.status .planning/quick/260906-tz7-define-and-verify-the-explicit-public-so --pick status`; it returned `gaps_found`.

Dr. Mani's adopted autonomous goal already authorizes completing reviewed repairs, followed by regression testing, independent review and integration. The parent selects the documented repair route. Accepting the feature with known gaps is not authorized by the goal. No new permission or changed dependency is needed.

The original executor stopped Task 2 at its three-auto-fix limit and returned a complete checkpoint. Do not resume that open-ended auto-fix loop or reset its attempt history. This is the supervisor's separately scoped recovery task R1 for the one remaining independently reproduced finding. Original failures, corrections and interrupted full-suite evidence remain preserved. The same task-owned feature branch/worktree remains isolated; no code changes occur in main.

## Frozen input and ownership

- Worktree: existing `agentic-skills-lifecycle-engine-package-boundary`.
- Branch: `fix/portable-package-boundary`.
- HEAD: `9ed2f5aa11074ad62e7b196e4ac20bbe16742e76`.
- Helper SHA256: `a0762abb69cf43d3cfd15c19cb79aa35d1bd4c09da56b98d4ebb67516434362c`.
- Test SHA256: `bb4dfb4819352c53fad6001a96a92f09be3984deffaa585ddc9eb83188d51918`.
- Source ownership: only `scripts/verify_distribution.py` and `tests/test_distribution.py`.
- Evidence output: append-only new R1 command receipts/logs under task-owned ignored `build/package-boundary-logs`, plus new `260906-tz7-GAP-REPAIR-RESULT.json` in this quick directory.
- No other source, documentation, manifest, dependency, original evidence, review report or root planning edits. No commits, full-suite run, final build or integration during R1.

The original executor and reviewer have returned; no tests or builds remain active. Other features/sessions still exist: preserve their files and branches. Parent owns later Task 3 continuation, final review, commits and cleanup.

## Required reading

Read AGENTS.md, CONTRIBUTING.md, the original 260906-tz7-PLAN.md, its SUMMARY.md checkpoint, and VERIFICATION.md correction checkpoint. Inspect the helper's `_identity` and complete `verify_sdist` execution path, plus the existing `_sdist` test fixture and archive tests before editing.

F-05's independently checked primary source is [setuptools 68 DistributionMetadata](https://raw.githubusercontent.com/pypa/setuptools/v68.0.0/setuptools/_distutils/dist.py). Its `get_fullname` preserves the declared hyphenated project name. Current supported backends may produce the normalized underscore name. No actual setuptools 68 build has been run; the regression fixture must remain labeled a fixture.

## R1: Preserve supported archive identity without admitting mixed roots

1. Add a failing regression for a complete valid source archive rooted at `agent-skill-mastery-engine-0.2.0`. Preserve a positive test for `agent_skill_mastery_engine-0.2.0`. Use independently specified expected spellings and the existing complete payload fixture; do not construct expected identities through the implementation under test. Preserve executable source modes and all existing assertions.
2. Accept exactly one archive root equal to either the declared project name plus version or its existing normalized name plus version. Derive the two permitted identities from the existing project identity, select the actual single root from validated archive member names, and preserve one-root consistency for every member. Do not accept arbitrary normalization, guessed names or a root merely matching an archive filename.
3. Explicitly test rejection of mixed permitted roots in one archive, wrong project name, wrong version, traversal or absolute member names, a regular file occupying the root, and an empty archive. Preserve all current membership, content, metadata, PAX, ZIP, mode, symlink/hardlink and scanner checks. Invalid archives must raise the existing ContractError rather than leak an unrelated exception caused by an unset root.
4. Run the R1 tests RED before the behavioral correction, preserve that complete command output, then run the same tests GREEN plus the complete existing distribution test file. A nonzero exit, zero collected tests or an unexpected skip/deselection is a failure; report the exact scope and any inherited skip. Do not shorten tests to get a pass. A clear failing test permits one targeted correction; otherwise return the exact blocker.

Use the installed pytest with `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider` and explicit R1 node selection, followed by `tests/test_distribution.py`. Record actual commands, UTC start/finish, exit status, selected counts, elapsed time, before/after source hashes and raw-log hashes in the R1 result. The exact new node names must be recorded after creation, not invented as already-existing paths.

Run `git diff --check` after the correction. Report only the two owned source-file changes and the new R1 evidence. The historical import manifest, original generic scanner, namespace/version/dependency constraints, and other feature files must remain byte-identical to this checkpoint.

## Return and remaining gates

Return R1's actual result and final hashes without declaring the package feature complete. The parent will independently re-check F-05, then resume original Task 3: finalize public documentation before final builds, run the complete frozen-source suite and smoke, verify final source/wheel archives and extracted-source rebuild/tests, refresh current/import accounting and obtain the reviewer's final verdict. No prior partial run or pre-correction archive may substitute for that evidence.
