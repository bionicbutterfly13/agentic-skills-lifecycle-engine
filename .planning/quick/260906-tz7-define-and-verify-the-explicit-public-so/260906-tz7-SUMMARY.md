---
phase: quick
plan: 260906-tz7
subsystem: packaging
status: validation-passed-pending-independent-review
requires:
  - phase: 260906-omm
    provides: Verified immutable ASME compatibility import
provides:
  - Complete explicit public source inventory and strict archive verification
affects: [PORT-01, wikiskill-v1]
requirements-completed: []
tech-stack:
  added: []
  patterns: [literal source inventory, local build-helper bootstrap, complete archive verification]
key-files:
  created: [scripts/verify_distribution.py, tests/test_distribution.py, docs/distribution.md]
  modified: [MANIFEST.in, setup.py, tests/test_workspace_hermes_adapter.py]
---

# Quick 260906-tz7: Public distribution validation passed

The implementation selects 133 public source files, restores all 14 evaluation assets and document dependencies, preserves generic candidate scanning, and checks archive members, metadata and permissions. All six implementation review findings have been corrected. The complete final project suite passed 678 cases with 1 inherited skip; every one of the 679 collected cases is accounted for. Final independent approval and integration remain pending.

## Task status

| Task | Result |
| --- | --- |
| 1: Adversarial regressions | RED receipts retained. The final distribution file passed all 83 cases after the separate R1 repair. |
| 2: Inventory and build hooks | Implemented and independently reviewed. R1 closes the remaining legacy source-root compatibility gap. |
| 3: Real distribution verification | All required execution gates pass, including the complete frozen-source suite and post-run source/archive seal. Final independent decision remains pending. |

## Verified final artifact gates

The [evidence receipt](260906-tz7-EVIDENCE.json) contains exact commands, raw-log hashes, every archive member and mode, 133 public source comparisons, all 125 imported destination comparisons and the generated artifact inventory. The independent verifier owns [VERIFICATION.md](260906-tz7-VERIFICATION.md); the executor has not edited it.

| Gate | Observed result |
| --- | --- |
| Final root PEP517 build | Passed in 55.23 seconds; actual sdist and wheel, declared isolated setuptools backend. |
| Source archive | 140 regular files and 26 directories; complete membership, content, metadata and mode checks passed. |
| Wheel | 53 members, including 37 runtime/data files and 9 existing skill companions; complete checks passed. |
| Independent source families | All runtime, assets, adapter, script, test, reference and locked-record files checked; all 14 evaluation files present and byte-identical. |
| Extracted source rebuild | Passed in 33.01 seconds without Git, internal planning or PYTHONPATH. |
| Rebuilt wheel | All 53 member bytes and permission modes identical to the final wheel; ZIP timestamps differ. |
| Offline installed wheel | Local no-index/no-dependency installation; 46 runtime/skill members match, 9 skill companions resolve, and isolated CLI help/version/transition-matrix commands pass. |
| Extracted tests | 129 passed, 1 inherited skip, 1 expected duplicate-member warning; 276.01 seconds pytest time. |
| Root and extracted stdlib smoke | Both returned DONE with score 1.0, no network use, unsandboxed isolation and final-only traces. These are toy results. |
| Source/document comparison | All 133 public files match checkout, source archive and extracted source; 28 documentation/notice/citation surfaces included. |
| Preservation | All 14 protected surfaces unchanged; all 125 import destinations accounted: 122 unchanged and 3 intentional feature changes. |
| Immutable import verifier | Fresh 129-source/125-destination pass against a 159-file snapshot bound to the actual import commit. |
| Feature whitespace | Ordinary cached check passed for the eight feature files in an isolated temporary Git index; the real index remained byte-identical. |
| Complete project suite | 678 passed, 1 skipped, 1 warning; 3472.02 seconds pytest time, 3476.4283 seconds wrapper time; exit 0. All 679 collected cases accounted for, no deselections. |
| Post-run seal | All 141 frozen files, 14 protected surfaces, 125 import destinations, 133 public archive/extracted files and all three final archive hashes rechecked unchanged. |

Python 3.14.6, build 1.6.0, pip 26.2.1 and pytest 9.1.1 were observed. The built wheel records `Generator: setuptools (84.0.0)`. The declaration remains `setuptools>=68`; no dependency was added or globally installed. The inherited wheel fixture skips because setuptools is not globally importable. It does not replace the two mandatory real builds.

The complete run started 2026-09-07T04:08:50.163341Z and ended 2026-09-07T05:06:46.705776Z. The exact inherited skip is `tests/test_skill_assets.py::test_built_wheel_carries_the_skill_files`, reported at line 73: `setuptools is not importable in this environment`. The one warning is `UserWarning: Duplicate name: 'asme/cli.py'` from `tests/test_distribution.py::test_distribution_wheel_adversarial[duplicate]`, the intentional duplicate-member refusal fixture. No test was restarted or deselected in the final run. No execution sessions remain active.

## Source freeze and sequencing

Public documentation was finalized before the root build. That build finished before generated egg-info was frozen and before the full suite started. The reviewer independently confirmed all 141 regular freeze entries and seven opaque classifications. Later operations used separate extracted/install output directories. Frozen source and public documentation have not changed.

After the suite finished, the seal compared the collected node list with all passing nodes and the single inherited skipped node. It rechecked every frozen and protected file, all imported destinations and final artifact hashes. The complete post-run source checker passed and produced the same result hash as the pre-run source check.

| Surface | SHA256 |
| --- | --- |
| Freeze receipt | `186a1cd02c8b7290808fd4522182aaac685a2b56c58d6a29de21dd95f29ef572` |
| scripts/verify_distribution.py | `b4fe75aa23731cf094c597e6f51dddee31805e62c70642e3cd5a17e3566484b4` |
| tests/test_distribution.py | `9a3a8e1170e434fefea37f78bcb5b7ecf40dcf0690124c95dc1b5e7d2e1bf16e` |
| docs/distribution.md | `e0ce0545977c870a54f8748550236ff76107a2314ac78bd6157cf55433957599` |
| Final wheel | `691a5481d12bb6e3e66dacbc10e270d3db949cccc38f5e99e5dda6eb9067cef3` |
| Final sdist | `9e17299616f0086810302daa4220900545745fa1963bbeefe19e629f262e563d` |
| Collection raw log | `ab1ba8cfce22a0ac67e8f0b3aa77e3d7484647d2891394b023f874e414ba6b5a` |
| Complete suite raw log | `3d1c8ff465a60c1d45079495e97d1ed1cd37f84a58a779ad0f045979bb26d44a` |
| Post-run seal result | `0aabb0ea9f2ce8bfd7d907ca6b14bb145607f75c20fddbcd5a5db245cd72aa64` |
| Collection command receipt | `f0b0dc140c634373380a2fbd453e190ab74d10b656068c469484c1080cf662b7` |
| Complete suite command receipt | `9f3b3208549404d38a32812a547b2487af32e09c2e8a5955cd998b1e7fd7a877` |
| Post-run seal command receipt | `27b87693ce1d952e0afe5c1180831bce025376268abae96cb66d6332f6b98fdd` |

## Deviations and preserved failures

1. Backend source-list generation required a targeted hook correction. The actual failed build and RED regressions remain preserved.
2. Independent review found unscanned archive transport metadata, permissive mode checks, unvalidated present generated metadata, legacy metadata/layout compatibility and an excluded-draft fixture assumption. The grouped correction added explicit refusal and compatibility cases without changing the generic scanner.
3. A late global-PAX overwrite probe required checking global headers after all members were parsed. Both the initially malformed probe and the valid failing probe remain preserved.
4. Task 2 reached the GSD executor's three-attempt limit. The protocol states:

   > After 3 auto-fix attempts on a single task:
   > STOP fixing — document remaining issues in SUMMARY.md under "Deferred Issues"
   > Continue to the next task (or return checkpoint if blocked)

   That loop remains stopped. The parent created the separately scoped [R1 repair](260906-tz7-GAP-REPAIR.md), retaining RED 1 failed/16 passed, GREEN 17 passed and the full 83-case distribution pass. The reviewer independently passed 17 cases in 62.75 seconds.
5. The initial supplementary evidence counter used nonexistent `evals/` and reported 0. The complete 133-source comparison already covered those bytes. A separate corrected receipt enumerates `assets/eval/` and asserts the exact 14 expected files; the original counter and receipt remain preserved.
6. The snapshot evidence harness initially compared POSIX 0664 directly with Git 100644. The parent confirmed the unchanged import verifier's executable-bit contract. The corrected harness checks Git mode and records actual POSIX mode separately; strict current-source mode checks remain. The original harness and failing receipt remain preserved.
7. A no-index whitespace diagnostic returned 1 with no warning text, while the harness expected 0. Controlled clean/whitespace probes and [Git's documented exit semantics](https://git-scm.com/docs/git-diff) explain that result. The authoritative check uses an ordinary cached diff in a separate index, covers the exact eight feature files and preserves the real index. The failed diagnostic remains preserved. This was Task 3's third harness correction; no further automatic fix loop was opened.

The pre-correction full run stopped by an explicitly authorized interrupt after 306 passing tests, exit 2 and 811.76 seconds, remains incomplete. Earlier extracted tests returned 93 passed, 1 skipped and 1 draft-fixture failure. Those historical results have not been relabeled as final passes or erased.

The original staged import's exit 2 and 13 inherited whitespace warnings also remain recorded without changing imported bytes or Git whitespace rules. Current feature checks introduce no new whitespace warnings. A bounded scan of all six changed implementation/test/doc files found no TODO, FIXME, placeholder or coming-soon markers.

## Evidence limits and integration ownership

Modern/legacy metadata, wheel-license placement and both exact source-root spellings have primary-source-backed compatibility fixtures. An actual setuptools 68 build was not run. Packaging checks and toy smoke results do not establish empirical WikiSkill parity, model performance, hosted Hermes isolation or a public release.

The unchanged import manifest remains bound to `ec3571e87f955403a3208a9ce0016f6f382a9b90`. Current branch `fix/portable-package-boundary` remains at `9ed2f5aa11074ad62e7b196e4ac20bbe16742e76`, incorporating integration input `78b3d82ff708a6d522650629ed01970a52b678cf`. No executor commits were made. Root STATE.md, runtime/scanner files and the original ASME source remain unchanged.

The parent owns final independent approval, commits, merge, post-merge checks, artifact preservation and removal of only the clean merged worktree/branch. The `.gsd/dispatch-isolation-sentinel.json` is operational state to preserve during that closeout.

The parent-authorized review probe under `build/phase1-unseeded-review-20260907` is separately identified in the generated-output inventory. Its 14 files demonstrate local unseeded initialization and baseline job preparation only. No role jobs, models, providers or evaluations ran in that probe; it does not extend the packaging verdict into empirical parity.

The final build-output inventory contains 806 regular files and 52 complete raw logs at its recorded capture. It includes those 14 reviewer-probe files and excludes only the evidence compiler's own output to avoid self-reference. It is separate from the parent's later exhaustive preservation inventory, which will also cover the operational sentinel after all writers stop.

## TDD gate and commit ownership

Actual RED and GREEN runs are retained, including the separate R1 regression. No executor commits were created because the parent explicitly retained all commit, merge and cleanup ownership. Individual RED/GREEN commit gates therefore remain absent from this branch's history; the evidence does not imply otherwise.

## Deferred Issues

No implementation or execution gate remains open. The final independent decision, integration and cleanup remain parent-owned. Raw generated evidence must be retained with matching hashes before the worktree is removed; the parent will capture a fresh exhaustive inventory after all writers stop.

## Self-Check: execution evidence passed; final review pending

The source, evidence receipt, R1 result and independent report exist. All 679 collected cases and final source/archive hashes are accounted for. The complete suite, extracted suite, real builds, installation probe, smoke, source accounting and whitespace checks have recorded outcomes. This execution record does not mark PORT-01, WikiSkill parity or parent-owned integration complete.
