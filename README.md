# Agentic Skills Lifecycle Engine

Agentic Skills Lifecycle Engine, shortened to Lifecycle, is an independent project
for acquiring, evaluating, revising, and retaining agent skills. This checkout
contains the compatibility import of Agent Skill Mastery Engine (ASME) at source
revision `1137c6705fd844546d5588757a5a23d4007b20c4`.

The Python package `asme`, CLI `asme`, distribution
`agent-skill-mastery-engine`, Python `>=3.11` requirement, and version `0.2.0`
are preserved during the import. These compatibility names do not indicate a new
Lifecycle release.

## Verified scope and remaining work

The mechanical import preserves the existing runtime, tests, assets, contracts,
and licensing. Its [manifest](docs/migration/asme-source-manifest.json) accounts for
all 129 tracked source paths. The [migration report](docs/migration/asme-port.md)
and [command receipt](docs/evidence/asme-port-verification.json) record verification
status and limits.

Strict parity with [WikiSkill v1](https://arxiv.org/abs/2608.27454v1) is the active
implementation objective. Importing ASME does not establish that parity or reproduce
the paper's experimental results. The inherited claims policy can label scripted
fixtures `paper_comparable`; that known defect remains unchanged in this
compatibility import and requires a separate repair.

The Hermes adapter exposes a read-only capability tool with dispatch disabled.
No live Hermes execution, host isolation, benchmark improvement, or installation
into a host skill root is established by this import. The existing workflow uses strict
validation plus a second confirmation gate, a local extension beyond the paper's
single strict validation decision.

## Run from a checkout

The runtime uses the Python standard library. With Python and pytest already
available, run the complete offline suite and smoke check:

```sh
python3 -m pytest
python3 scripts/stdlib_smoke.py
PYTHONPATH=src python3 -m asme --help
PYTHONPATH=src python3 -m asme transition-matrix
```

The smoke check is a scripted software fixture. Its score is not experimental
evidence. No package installation or provider request is needed for these checks.

## Existing engine

The imported core owns sealed text-domain splits, immutable skill snapshots,
subprocess extraction and scoring, sampled training evidence, wiki updates,
single-skill proposals, validation and confirmation, transaction recovery, and
staged delivery. Runtime adapters remain thin.

Read [SKILL.md](SKILL.md) for the existing agent-facing workflow and
[references/integration.md](references/integration.md) for adapter boundaries.
The [historical source README](docs/migration/asme-source/README.md) preserves the
original commands, installation instructions, and snapshot-era status statements.
Historical instructions do not authorize installation or publication.

## Provenance and contribution

ASME's public [v0.2.0 release](https://github.com/bionicbutterfly13/agent-skill-mastery-engine/releases/tag/v0.2.0)
was published September 2, 2026, within a week of WikiSkill v1's submission.
The [timeline receipt](docs/evidence/asme-github-timeline.json) supports this narrow
claim. It does not prove a push within three days or Google's code-release date.

See [PROVENANCE.md](PROVENANCE.md), [CONTRIBUTING.md](CONTRIBUTING.md),
[LICENSE](LICENSE), and [NOTICE.md](NOTICE.md). Code is MIT licensed; documentation,
methodology, and templates carry CC BY 4.0 terms. Attribution and the non-binding
project-page link request remain intact.
