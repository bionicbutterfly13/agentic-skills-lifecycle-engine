---
phase: quick-260906-omm
verified: 2026-09-07T02:32:28Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
review_stage: final_compatibility_port_only
staged_style_check:
  exit_code: 2
  warning_count: 13
  source_index_worktree_byte_equality: verified_for_all_13_files
  disposition: inherited_formatting_preserved
re_verification:
  previous_verified: 2026-09-07T01:20:27Z
  previous_status: gaps_found
  previous_score: 2/4
  gaps_closed: 2
  gaps_remaining: 0
gaps: []
---

# ASME compatibility port: independent verification

**Verdict: PASS for the compatibility import quick task.** All four quick-plan truths are verified. The pinned engine, source history accounting, executable verifier, current documentation and preliminary timeline draft meet this bounded port contract. This verdict does not complete WikiSkill parity, the broader Phase 1 package boundary, empirical studies, live Hermes integration, or the substantial Substack article.

The full destination run finished with **593 passed, two failed and one skipped**. Both documentation failures were repaired, then the executor passed seven affected checks and this reviewer independently passed 43 focused checks. The complete destination suite was not rerun after those repairs, and is not relabeled as passing. Actual isolated PEP 517 builds, exhaustive archive-member checks and an offline installed-wheel probe supply package runtime evidence independently of the inherited conditional build-test skip.

**Recorded formatting limitation:** final `git diff --cached --check` exits 2 with 13 warnings. Independent comparison proves that all 13 staged files and their working copies exactly match the pinned source blobs. The bounded import verdict remains PASS with this inherited formatting warning; the staged whitespace check remains failed. No source bytes, whitespace rules or tests were changed to suppress it.

The reviewer did not author the imported source, migration verifier, tests or current port documents. Writes are restricted to this verification report. Production code, inherited tests, original source, main and other worktrees are unchanged by this review.

## Findings

1. **CLOSED, original blocker: canonical provenance records were missing.** [The inherited reconstruction test](../../../tests/test_governance_dependencies_gate2.py) requires the exact fenced records under `Current development authority` and `Owner attribution requirement` in canonical [PROVENANCE.md](../../../PROVENANCE.md). Both records now match the preserved historical bytes and registry-bound SHA256 values. A1/A5 and A4 locators, the source registry and inherited tests are unchanged. The current document explicitly identifies the old authority as historical and superseded. The executor's seven-check repair receipt and the reviewer's fresh 43-check run pass the original failing node.
2. **CLOSED, original blocker: authored plan references reached the private-path scanner.** [build_projection](../../../src/asme/package.py) includes the source tree, including planning artifacts. Eleven new PLAN references were converted to equivalent portable forms: seven source context links, two GSD context links, and two worktree/source descriptions. The nine referenced files resolve; source identity and execution meaning are retained. The unchanged inherited full-tree test passes in both fresh focused runs. The original failure remains in [destination-pytest.json](destination-pytest.json); neither scanner nor production tests were weakened.
3. **CLOSED, original evidence gap: complete suite outcomes and final identities are available.** The source suite completed with 559 passed and one skipped. The destination executed all 596 collected cases across 32 modules, with the two documentation regressions recorded above. The final independent comparison still accounts for all 129 source paths and 125 preserved destination files. The earlier interrupted source run at 267 passing tests remains historical partial evidence.
4. **Inherited scientific limitation, separate repair:** the unchanged public-claim policy accepts explicitly scripted, final-only evidence in its existing bootstrap test. This import must not treat that label as experimental proof. The WikiSkill roadmap assigns the claims repair separately, before new experiments.
5. **Broader Phase 1 integration dependency:** the exact port precedes a separately reviewed package-artifact boundary feature, then audit/workstream integration. Historical audit commands and pinned source links must remain exact. The actual source archive omits 14 files specifically under `assets/eval`; this is not the complete omission population. The inherited Markdown-only docs rule also omits linked migration/evidence JSON, and `locked/` is not declared. The source checkout preserves these materials. Runtime/skill compatibility passes, but complete public distribution membership and document dependency closure remain for the separate packaging feature.
6. **CLOSED, original build-evidence gap; inherited pytest skip remains disclosed.** Importing `setuptools.command.sdist` in the pytest environment failed because setuptools is absent, and the inherited wheel test skipped in both complete runs. The orchestrator subsequently used the declared official isolated PEP 517 frontend and setuptools build backend, successfully building an sdist and wheel from that sdist before and after the documentation repairs. Final wheel installation into an isolated task-owned target and real CLI subprocesses passed. This supplies actual build/runtime proof; it does not assert that the skipped pytest test ran or that all source-distribution omissions were repaired.

No additional material bypass was found in the authored verifier within the examined path, digest, index, disposition and CLI checks. This is a bounded review, not a claim that every conceivable adversarial input has been tested.

## Observable truths

| # | Quick-plan truth | Status | Evidence |
|---|------------------|--------|----------|
| 1 | Complete pinned engine and inherited suite retain CLI, package identity, bundled assets and Hermes boundary | VERIFIED | All production/test/asset bytes match the pin; complete suite outcomes, repaired inherited checks, actual final package builds and installed-wheel CLI probes establish compatibility. Inherited distribution omissions and dispatch-disabled behavior are preserved and disclosed. |
| 2 | Every tracked path has a preservation disposition; history and nontracked material remain accounted for without source deletion | VERIFIED | Independent Git tree/index/blob comparison covers all 129 paths, 125 destination files, six unique local commits and the complete nontracked inventory. |
| 3 | Fresh full destination results and independent comparison distinguish inherited behavior from regressions | VERIFIED | Both full outcomes are retained; two destination-only documentation failures are repaired without changing inherited tests, with fresh seven-check and independent 43-check receipts. Final source comparison and archive hashes pass. |
| 4 | Preliminary blog uses primary timeline evidence and describes performance/live Hermes as unproved | VERIFIED within preliminary-draft scope | Primary arXiv submission and GitHub release records refreshed; interval, root inventory and current links checked; substantial post remains a later deliverable. |

## Independent source preservation evidence

Pin: `1137c6705fd844546d5588757a5a23d4007b20c4`. The reviewer independently invoked Git and read its blob bytes; this comparison did not import or call `verify_asme_port.py`.

| Population | Observed result |
|------------|-----------------|
| Pinned tracked paths | 129, exactly equal to manifest mapping keys |
| Source index | Exact paths, Git modes, blob IDs and stage-zero entries match the pin |
| Source working files | All 129 byte contents and executable modes match pinned blobs |
| Exact canonical imports | 119 |
| Revised canonical documents | 3, each linked to its exact historical copy and bound to its current hash |
| Exact historical documents | 3: README, PROVENANCE, CONTRIBUTING |
| Retained source planning maps | 7, absent from destination at those source-relative paths |
| Preserved destination files | 125 |
| Source untracked files | 0, exact inventory match |
| Source ignored files | 91, exact path-set match; contents were not read |
| Unique local commits after recorded public tip | 6, exact ordered commit-set match |
| Source tracked status | Clean |
| Destination links to source | No checked destination is a symlink or a hardlink to its original source file |

The independently recomputed final destination content digest is:

```text
00ead34220eca190d1ebac8c06618b2551d97807f7fc762b237df2219dcc6a57
```

Scope: sorted compact JSON containing every manifest destination path, SHA256 and Git mode. This is not a digest of every authored planning/evidence file or a final release identity. The independently observed pre-repair digest remains historical evidence: `ead997d49425bde6c42d2d9fe7d87107382ec5b7954374f5a6c5d5c0557c58b2`. Only authorized current-document content changed within that digest population; all inherited production/test files remain exact.

The canonical restored records have SHA256 values `c8966236b915aee64067f03ae28a7d6028c31b171b3b8e7c771ef2e7fed6e809` (development authority) and `8245fd2d7d6205935cd948b9af01a199d82f24118854192580c75237e3e13ac8` (owner attribution). The reviewer separately extracted both fenced records and compared them byte-for-byte with their historical counterparts.

## Verification and test quality

| Check | Result | Scope |
|-------|--------|-------|
| Independent full Git tree/index/blob/destination comparison | PASS | All 129 source mappings, source status, destination containment/modes and history/nontracked preservation |
| Reviewer command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tests/test_asme_port.py` | 36 passed in 8.37 seconds, exit 0 | Authored verifier only; no full-suite claim |
| Fresh reviewer focused command, reproduced below | 43 passed in 125.92 seconds, exit 0 | All 36 verifier tests, both original failed inherited nodes and all five release-surface tests after document repairs |
| Reviewer direct inherited-claim probe | Exit 0; three scripted final-only runs still yield `allowed=true`, `label=paper_comparable` with 1,200 bootstrap resamples | Reused the existing bootstrap fixture data and invoked the production claim function directly; zero provider calls; confirms the preserved defect |
| [Destination smoke receipt](destination-smoke.json) | Exit 0; DONE; 28.359 seconds | Scripted, final-only, unsandboxed, network false; no efficacy claim |
| [CLI help receipt](destination-help.json) | Exit 0; 7.9 seconds | Preserved command surface |
| [Transition matrix receipt](destination-matrix.json) | Exit 0; 8.725 seconds | Preserved deterministic lifecycle surface |
| [Destination collection](destination-collection.json) | 596 tests, 32 modules, exit 0 | All 560 inherited tests plus 36 verifier tests; collection format gives module counts |
| [Complete source suite receipt](../../../docs/evidence/asme-port-verification.json) | 559 passed, one skipped, 3926.15 seconds, exit 0 | Orchestrator execution receipt inspected; exact start/end timestamps were not captured and remain null; clean pinned source independently rechecked |
| [Complete destination suite](destination-pytest.json) | 593 passed, two failed, one skipped, 3984.88 seconds, exit 1 | Full 596-case run, no deselection; raw failures retained; no post-repair full-suite pass claimed |
| [Executor documentation repair checks](destination-doc-repairs.json) | Seven passed in 1.90 seconds, exit 0 | Both original failed tests and five public-document checks |
| [Initial official build and installed probe](260906-omm-build-inspection.json) | Successful isolated PEP 517 sdist/wheel, archive inspection, offline installed CLI probe | Historical pre-repair artifacts; distinct from final build |
| [Final official build](destination-final-build.json) | Exit 0, 49.305 seconds | Declared PEP 517 sdist and wheel-from-sdist; preserved raw build log SHA256 independently checked |
| [Final archive inspection](destination-final-build-inspection.json) | Exit 0, 7.318 seconds; independently confirmed all recorded members and bytes | Wheel 53 regular members; sdist 135 total members, 117 regular files; full-archive community safety passes |
| [Final offline wheel installation](destination-final-wheel-install.json) | Exit 0, 16.213 seconds | `pip --no-index --no-deps --target` into a task-owned isolated directory, no host profile or global installation |
| [Final installed-wheel probe](destination-final-wheel-probe.json) | Exit 0, 11.06 seconds; version 0.2.0; CLI help and matrix exit 0 | Module is inside isolated target, nine skill companions match; reviewer independently compared all 37 installed runtime/data files and nine skill files; zero provider calls |
| Five authored documents | 27 local links resolve; no public em dashes | README, PROVENANCE, CONTRIBUTING, migration report and preliminary blog |
| This review report | Passes unchanged `scan_community_safety`; unstaged report-edit whitespace check passes | Portable report paths; this does not claim the complete staged import passes its whitespace check |
| Final complete staged whitespace check | `git diff --cached --check` exits 2, 13 inherited warnings | All 13 staged and working files independently match their exact pinned source blobs; full inventory below |

The new verifier tests use temporary files and a synthetic Git view to exercise positive preservation and deliberate negative mutations. Expected source bytes are independently defined fixture inputs, not values generated by the verifier. The assertions check exact error behavior, byte/mode drift, coverage equality, containment and CLI exit/status, rather than file existence alone. No skip, xfail or disabled-only requirement test was found in the authored test module.

The independent real-Git comparison complements those mocked Git tests. It confirms the actual import against the original repository and does not rely on the verifier's own acceptance result. All inherited test files are byte-identical to the pinned source.

Fresh independent focused command, run from the port worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tests/test_asme_port.py tests/test_governance_dependencies_gate2.py::test_current_authority_and_attribution_sources_are_hash_reconstructable tests/test_workspace_hermes_adapter.py::test_current_tree_is_community_scan_clean tests/test_release_surface.py
```

The final archive checks enumerate every member, reject duplicate/unsafe paths and nonregular nondirectory members, compare the complete regular-file path/hash sets with the receipts, and scan every file using the unchanged production scanner. Both archives contain all 37 runtime Python/JSON files with current checkout bytes. The wheel contains all nine skill companions; the sdist's three revised canonical documents and LICENSE, NOTICE and CITATION match their final checkout bytes. This verifies the stated archive contents, not an exhaustive intended-distribution inventory.

| Final artifact | SHA256 |
|----------------|--------|
| Wheel | `9855a00556bfd34f0999e231218994cf04772f5b1a5aa8a8d05db9b44125e418` |
| Source distribution | `de5d315a668aba5046e1bcebd18ba5070c8c98a4c38addadfeb23e7f59b60aab` |
| Preserved raw final build log | `e6884c034e85ded4dc3388bdcb49dbd76d8b48ee36d380279c657d4335150ef7` |

The final installed CLI stdout hashes are `ffca3a9d1082308f5e8aaff9f420c7800e22a21f3b0096cd706c88f90e03b5b8` for help and `e1f417c1f56cde04f5bcf11e473775c99be252c8253a6b13590692f151704651` for the transition matrix. They match the initial installed CLI probe. Build artifacts and raw logs remain task-owned verification evidence for orchestrator preservation before worktree cleanup.

### Complete staged formatting findings

The earlier unstaged check did not inspect newly added files before staging. The final staged check does, and its exit 2 is retained. The reviewer parsed the full output, required exactly 13 distinct warned paths, resolved each through the preservation manifest, and compared the staged blob (`git show :path`) and working file against `git show` of the corresponding source path at `1137c6705fd844546d5588757a5a23d4007b20c4`. Every comparison is byte-identical. Twelve warnings concern an existing extra EOF blank line; the remaining warning is the original two-space Markdown hard break in historical PROVENANCE.

| Destination path | Line | Inherited warning |
|------------------|-----:|-------------------|
| `SECURITY.md` | 14 | New blank line at EOF |
| `assets/index.md.tmpl` | 4 | New blank line at EOF |
| `assets/inference-prompt.txt.tmpl` | 12 | New blank line at EOF |
| `assets/log.md.tmpl` | 2 | New blank line at EOF |
| `assets/pattern.md.tmpl` | 14 | New blank line at EOF |
| `assets/skill-impact.md.tmpl` | 9 | New blank line at EOF |
| `docs/migration/asme-source/CONTRIBUTING.md` | 21 | New blank line at EOF |
| `docs/migration/asme-source/PROVENANCE.md` | 32 | Two-space Markdown hard break |
| `references/fidelity.md` | 33 | New blank line at EOF |
| `scripts/extractors/answer_tag.py` | 41 | New blank line at EOF |
| `scripts/scorers/exact_match.py` | 24 | New blank line at EOF |
| `tests/conftest.py` | 50 | New blank line at EOF |
| `tests/test_crash_oracle.py` | 252 | New blank line at EOF |

The two historical document destinations map to their original root-level source documents; every other path maps unchanged. Correcting these styles during this import would violate the explicitly authorized byte-preservation contract. The finding is an inherited formatting limitation, not a new runtime regression or an unverified preservation claim. No additional runtime tests were needed for this report-only evidence update. The orchestrator retains the failed check and complete per-file equality/hash evidence in the existing verification receipt.

## Package, attribution and inherited matrices

`pyproject.toml` retains the `agent-skill-mastery-engine` distribution, version `0.2.0`, Python `>=3.11` requirement and `asme = asme.cli:main`. `setup.py`, `MANIFEST.in`, package assets, source registry and the thin Hermes plugin are exact imports. LICENSE, NOTICE and CITATION bytes are unchanged: MIT applies to code, and the preserved notice/license records CC BY 4.0 documentation, methodology and templates with attribution and a non-binding project-link request.

All 106 SP rows and 27 HF-A rows were parsed, checked for exact ID coverage and read. Their inherited labels are 93 IMPLEMENTED, five PARTIAL, two BLOCKED and six EXCLUDED; HF-A has 26 PASS and one POLICY-GATED. Every exception appears in the current migration report:

```text
SP-033 SP-035 SP-085 SP-086 SP-087 SP-088 SP-089
SP-092 SP-093 SP-094 SP-097 SP-098 SP-103 HF-A25
```

These historical labels are not current independent scientific or live-runtime verification. Some old license/release statements predate the actual public ASME release; current documents explain that history without rewriting the source matrices.

The preserved Hermes plugin registers only `wikiskill_capabilities`, returns `staging_only_dispatch_disabled`, and exposes no launch operation. No installed Hermes profile or provider was used during this review. The unchanged `claims.py` public path does not check the supplied trace-fidelity or isolation fields; the inherited scripted acceptance test explicitly expects `paper_comparable`. That remains a known follow-up, not a new port regression.

## Timeline and document checks

The [primary arXiv record](https://arxiv.org/abs/2608.27454v1) was refreshed and records submission at 2026-08-27 17:59:11 UTC. The [GitHub v0.2.0 release](https://github.com/bionicbutterfly13/agent-skill-mastery-engine/releases/tag/v0.2.0) was refreshed through `gh api`, confirming release ID 381020408, publication at 2026-09-02 06:29:14 UTC, draft false and prerelease false. Their difference is 477,003 seconds, or 5 days, 12 hours, 30 minutes and 3 seconds.

The recorded root commit has no parents and exactly 88 files, including 29 Python files under its original source namespace and 24 test Python files including conftest. Git author and committer dates agree with the timeline receipt. The GitHub repository creation timestamp was also refreshed. The recorded CreateEvent/PushEvent entries remain historical receipt evidence; this reviewer did not re-fetch the complete event feed.

The preliminary blog makes the supported within-week claim and explicitly leaves a three-day push and Google's code-release date unproved. It distinguishes the imported implementation, software fixtures, live runtime, empirical outcomes and publication. Its second-paper link is background only; the active implementation scope remains WikiSkill v1.

## Acceptance boundaries and remaining work

The two original blockers are closed by inspected document repairs and fresh behavioral checks. No unresolved compatibility-port defect was found. The source, source registry, inherited tests, scanners, package identity and runtime behavior remain preserved. All seven quick-plan artifacts are substantive and wired: the declared entry point loads the imported CLI; the verifier checks the real manifest against Git; and the draft links the timestamped evidence. The parent's narrow PROJECT update accurately distinguishes this import from unproved broader requirements; root STATE remains unchanged.

The following are not covered by this PASS:

1. A clean post-repair execution of the entire destination suite. Complete pre-repair execution plus focused post-repair checks are the actual evidence.
2. Complete public source-distribution membership, archive document dependency closure and separation of internal planning/evidence. The 14 omitted evaluation assets are one measured subset, not every omission. The separately planned package-boundary feature must address this without weakening generic candidate scanning or discarding historical receipts.
3. WikiSkill's empirical claims policy, full trajectories, role execution, live Hermes dispatch, benchmark experiments, statistical results or ablations. The scripted claim-admission defect remains explicitly assigned to the next scientific-integrity phase.
4. The substantial Substack post, publication, or a claim that ASME was pushed within three days of Google's code release. Only the separately evidenced within-week paper-submission-to-release interval is supported.
5. Commit, integration, post-merge checks and clean task-owned worktree/branch removal. Those are the orchestrator's authorized next actions and need fresh action-time checks. Original-source deletion is not authorized by this report.

### Decision coverage

No standalone quick CONTEXT.md exists. The quick PLAN's settled decisions were checked directly: compatibility identity, source pin, isolated ownership, history/license preservation and evidence-scoped writing are represented. Its old no-commit wording is expressly superseded by the September 6 resume authority and the user's adopted autonomous goal. Paid execution, publication and source deletion remain gated.

### Reproduction of the independent file comparison

Run the following Python from the port worktree root, with the preserved original source as its named sibling. It is read-only and prints hashes/counts, not source contents.

```python
from pathlib import Path
import subprocess,hashlib,json,stat,collections
source=Path("../agent-skill-mastery-engine").resolve()
target=Path.cwd().resolve()
pin="1137c6705fd844546d5588757a5a23d4007b20c4"
def git(*args):
 r=subprocess.run(["git","-C",str(source),*args],capture_output=True,check=True)
 return r.stdout
assert git("rev-parse","HEAD").decode().strip()==pin
assert Path(git("rev-parse","--show-toplevel").decode().strip()).resolve()==source
tree={}
for row in git("ls-tree","--full-tree","-rz",pin).split(b"\0"):
 if row:
  meta,p=row.split(b"\t",1)
  mode,kind,oid=meta.decode().split()
  assert kind=="blob" and mode in ("100644","100755")
  tree[p.decode()]=(mode,oid)
index={}
for row in git("ls-files","--stage","-z").split(b"\0"):
 if row:
  meta,p=row.split(b"\t",1)
  mode,oid,stage=meta.decode().split()
  assert stage=="0" and p.decode() not in index
  index[p.decode()]=(mode,oid)
assert tree==index
manifest=json.loads((target/"docs/migration/asme-source-manifest.json").read_text())
entries=manifest["entries"]
assert manifest["source_revision"]==pin
assert len(entries)==len(tree)==129
lookup={e["source_path"]:e for e in entries}
assert len(lookup)==len(entries) and set(lookup)==set(tree)
order=sorted(tree)
proc=subprocess.run(["git","-C",str(source),"cat-file","--batch"],input="".join(tree[p][1]+"\n" for p in order).encode(),capture_output=True,check=True)
data=proc.stdout; offset=0; fingerprints=[]; count=collections.Counter(); source_fingerprints=[]
for name in order:
 end=data.index(b"\n",offset)
 oid,kind,size=data[offset:end].decode().split()
 offset=end+1; size=int(size)
 blob=data[offset:offset+size]; offset+=size
 assert data[offset:offset+1]==b"\n"; offset+=1
 mode,expected_oid=tree[name]
 assert kind=="blob" and oid==expected_oid
 expected=hashlib.sha256(blob).hexdigest()
 e=lookup[name]
 assert e["sha256"]==expected and e["git_mode"]==mode
 original=source/name
 assert original.is_file() and not original.is_symlink() and original.read_bytes()==blob
 assert ("100755" if original.stat().st_mode & stat.S_IXUSR else "100644")==mode
 source_fingerprints.append({"path":name,"sha256":expected,"git_mode":mode})
 if name.startswith(".planning/codebase/"):
  assert e["disposition"]=="retained_at_source" and e["destination"] is None and e["reason"]
  assert not (target/name).exists()
  count["retained_planning"]+=1
  continue
 assert e["destination"]==name
 if name in ("README.md","PROVENANCE.md","CONTRIBUTING.md"):
  assert e["disposition"]=="historical_copy_with_current_document"
  assert e["historical_destination"]=="docs/migration/asme-source/"+name
  historical=target/e["historical_destination"]
  assert historical.read_bytes()==blob
  current=target/name
  assert hashlib.sha256(current.read_bytes()).hexdigest()==e["current_sha256"]
  assert ("]("+e["historical_destination"]+")").encode() in current.read_bytes()
  targets=[(name,e["current_sha256"]),(e["historical_destination"],expected)]
  count["current_documents"]+=1; count["exact_historical"]+=1
 else:
  assert e["disposition"]=="copied_exact"
  assert (target/name).read_bytes()==blob
  targets=[(name,expected)]
  count["exact_canonical"]+=1
 for name2,sha in targets:
  path=target/name2
  assert path.is_file() and not path.is_symlink()
  assert not any(p.is_symlink() for p in path.parents if p.is_relative_to(target))
  assert path.resolve().is_relative_to(target)
  assert ("100755" if path.stat().st_mode & stat.S_IXUSR else "100644")==mode
  assert path.stat().st_ino != original.stat().st_ino or path.stat().st_dev != original.stat().st_dev
  fingerprints.append({"path":name2,"sha256":sha,"git_mode":mode})
assert offset==len(data)
identity=hashlib.sha256(json.dumps(sorted(fingerprints,key=lambda r:r["path"]),sort_keys=True,separators=(",",":")).encode()).hexdigest()
untracked=[r.decode() for r in git("ls-files","--others","--exclude-standard","-z").split(b"\0") if r]
ignored=[r.decode() for r in git("ls-files","--others","--ignored","--exclude-standard","-z").split(b"\0") if r]
print(json.dumps({"status":"PASS","source_revision":pin,"source_index_equals_pin":True,"source_tracked_paths":len(tree),"source_work_bytes_and_modes_equal_pin":True,"dispositions":dict(count),"preserved_destinations":len(fingerprints),"destination_content_digest":identity,"untracked_count_now":len(untracked),"ignored_count_now":len(ignored),"source_tracked_status":git("status","--porcelain","--untracked-files=no").decode(),"no_copied_source_planning":True,"no_hardlink_to_source":True},indent=2))

```
