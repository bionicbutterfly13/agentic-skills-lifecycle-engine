# From WikiSkill to Lifecycle: a release within a week

Mani Saint-Victor, MD

September 6, 2026

**Unpublished preliminary timeline draft.** The mechanical Lifecycle import exists. Its full destination test run exposed two documentation regressions; their corrections passed all seven affected checks, and the rebuilt package passed archive and isolated installation checks. This early manuscript preserves the development timeline; the substantial Substack article follows verified WikiSkill v1 parity and actual experimental outcomes. It makes no live Hermes installation or experimental replication claim.

Agent Skill Mastery Engine, or ASME, had a public v0.2.0 release within a week of the WikiSkill paper's submission. The [arXiv submission record](https://arxiv.org/abs/2608.27454v1) and [GitHub release record](https://api.github.com/repos/bionicbutterfly13/agent-skill-mastery-engine/releases/381020408) establish that timeline. They don't show that a skill improved or that ASME reproduced the paper's results.

WikiSkill gave ASME its research starting point. In [WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution](https://arxiv.org/html/2608.27454v1), researchers affiliated with Google Research and Virginia Tech describe separate layers for execution traces, accumulated knowledge, and executable skills. Candidate skills face validation and rollback, while the wiki persists.

What interests me is what survives a failed proposal. A skill change can be rejected while the wiki retains useful knowledge from the attempt, giving the next proposal a record to learn from. That makes a failed candidate worth examining. It doesn't make the candidate effective. Keeping those two judgments separate is central to the direction of Agentic Skills Lifecycle Engine, shortened to Lifecycle.

A separate paper, [Towards a Systems Foundation for Agentic Skills: Architecture, Lifecycle, and Security](https://arxiv.org/abs/2608.29596), remains a background reference. The current implementation goal is exclusively the first paper, WikiSkill v1.

The dates deserve a precise account. All times below are UTC. The [timeline receipt](../evidence/asme-github-timeline.json) preserves the primary-source URLs, identifiers, and calculation inputs checked on September 6.

| Record | Timestamp | What it establishes |
| --- | --- | --- |
| WikiSkill v1 submission | 2026-08-27 17:59:11 | arXiv's recorded submission time |
| ASME root commit `c20a4fd` | 2026-09-01 05:54:16 | Git author and committer timestamps |
| ASME repository creation | 2026-09-01 06:00:39 | GitHub's repository creation record |
| CreateEvent `19626958334` | 2026-09-01 06:00:50 | GitHub's recorded creation of `main` |
| PushEvent `19724824535` | 2026-09-01 14:11:23 | GitHub's recorded push from `c20a4fd` to `a8d5de2` |
| v0.2.0 publication | 2026-09-02 06:29:14 | Publication of a release with `draft=false` and `prerelease=false` |

The [root commit](https://github.com/bionicbutterfly13/agent-skill-mastery-engine/commit/c20a4fd72e120209c819b33a3209c2ac85af7275) contains 88 files, including 29 Python source modules and 23 test modules, plus `conftest.py`. Those are inventory counts, not a test result. Its Git timestamps also aren't evidence of when GitHub received it. Repository creation, the observed events, and release publication each record a different event; the receipt keeps them separate.

The checked August 27-30 events and August 27-31 commit searches did not establish a three-day push. That limited search also cannot establish that no earlier activity existed elsewhere. These records don't establish Google's code-release date, so they cannot support an interval measured from that date.

The compatibility import into Lifecycle preserves ASME's existing command and package interfaces, tests, bundled assets, contracts, and historical documents while the development home changes. All 129 source paths are accounted for, including seven planning maps retained at source. The [migration report](../migration/asme-port.md) records the import and remaining checks; fresh execution results belong in the [evidence directory](../evidence/).

Lifecycle's [project design](../../.planning/PROJECT.md) keeps the core independent of its reference hosts. Preserving the existing implementation gives the WikiSkill work a concrete starting point. The recorded full runs and corrective checks establish the compatibility baseline. Independent review passed all four requirements of the bounded import plan; Git integration remains pending.

For Hermes, the existing ASME adapter exposes read-only capabilities with live dispatch disabled. Before an experiment launches, its model/provider route and permitted tools must be fixed and enforced. The upstream audit found routes that can change provider and selections that can inherit tools, so the proposed port keeps dispatch disabled. The [migration report's pinned source references](../migration/asme-port.md) document those findings. They establish source behavior at the audited revision, not an installed-runtime check or a live experiment.

Attribution and licensing travel with the implementation. The import contract retains ASME's MIT license for code, CC BY 4.0 terms for documentation and methodology, notices, citations, and provenance. WikiSkill's [CC BY 4.0 paper license](https://arxiv.org/html/2608.27454v1) remains part of that lineage. Historical source documents must remain recoverable, including snapshot-era private or unpublished declarations, while current documentation distinguishes those statements from the verified public ASME release.

An inherited claims-policy defect makes this evidence boundary concrete. ASME's `claims.py` does not check the isolation label on its public claim path. An existing test supplies `scripted-offline-fixture` evidence and expects `allowed=true` with `paper_comparable`; the completed paper audit independently reproduced that acceptance. A fixture supplies scripted inputs or outputs for checking software behavior; it cannot establish that a model reproduced WikiSkill's benchmark performance. This draft makes no replication claim. The mechanical import preserves this behavior for a separate regression repair under the WikiSkill parity goal.
