# Public source distribution contract

Lifecycle retains the `agent-skill-mastery-engine` distribution at version 0.2.0,
the `asme` package and command, and Python 3.11 or later. `MANIFEST.in` is the
single public source inventory: `global-exclude *` followed by one literal
`include path` per source file. Unknown directives, duplicate entries, missing
sources and unclassified files fail the build.

The source archive includes runtime code and data, Hermes adapter files,
templates, both complete toy evaluation cartridges, scripts, tests, references,
locked methodology records, licenses and public documentation dependencies.
The wheel continues to carry the runtime and its existing skill companions.
The 14 previously omitted files count only arithmetic and echo evaluation
assets; the explicit inventory also covers linked JSON and locked records.

`.planning` and agent workflow trees stay internal. The exact historical audit
files `docs/research/wikiskill-code-parity.md` and
`docs/evidence/wikiskill-parity-audit.json` stay internal individually. The exact
unpublished preliminary draft `docs/public/2026-09-06-from-wikiskill-to-lifecycle.md`
also stays internal. Other documents in these directories receive the same
inclusion and safety checks as every public source. The checker reports each
excluded file or operational tree and its reason. Git, virtual environments,
build output and recognized caches are operational state.

Historical documents under `docs/migration/asme-source` retain their exact
imported bytes. The unchanged [import manifest](migration/asme-source-manifest.json)
declares their original source-root locations. Their relative dependencies are
checked in that original context and mapped to the preserved public destination;
fragment-only links remain local. Companions are not duplicated under the archive
directory. Ordinary documents resolve links relative to their distributed paths.

`scripts/verify_distribution.py` loads this checkout's `src/asme` directly and
refuses a foreign, already-loaded ASME package. Both setuptools hooks and the
standalone checker use the same local source. No Git repository, editable
installation, ambient `PYTHONPATH`, or internal planning directory is required
when rebuilding an extracted source archive.

The hooks check complete source membership before copying, and actual copied
bytes afterwards. Archive verification checks every member before extraction,
including metadata, path normalization, duplicates, special file types, unknown
files and missing files. Wheel `RECORD` hashes and sizes must match every member.
Backend-generated `PKG-INFO`, `setup.cfg` and the exact egg-info files are checked
separately from literal sources. Metadata must preserve project identity, the
README description, license notices, entry points and pure Python wheel tags.
The backend's `SOURCES.txt` records the literal public sources. The sdist hook
validates that list, then adds exactly five validated egg-info files to the copy
inputs. Setuptools generates the root `PKG-INFO` and `setup.cfg` itself.
Present generated metadata is validated by `--check-source` as well, including
source-list coverage, exact entry points and identity. Recognized metadata
versions 2.1 through 2.4 retain strict field and description checks; older
setuptools metadata can omit `Dynamic: license-file`. The legacy `bdist_wheel`
layout may put the same two license files at the dist-info root. Mixed layouts,
unknown fields and altered license bytes fail.

Each source archive has exactly one root: the normalized
`agent_skill_mastery_engine-0.2.0` or the declared legacy
`agent-skill-mastery-engine-0.2.0`. These spellings derive from the project name
and version. Mixing the two roots, using a different project or version, or
placing a regular file at the root fails. The archive filename does not establish
its internal identity.

Tar directories must be mode 0755. Source-file permissions must match the source;
generated metadata may be 0644 or 0664. Privileged permission bits and all link
types fail. Only finite `mtime` and exact `path` PAX fields are accepted, with
decoded owner and PAX values scanned. Global PAX extensions and ZIP archive or
member comments, extra fields and unsupported flags fail. Verification receipts
record every member's mode as well as its bytes. Compressed byte noise is not
treated as textual source content.

The generic candidate projection and community scanner are unchanged. A private
path in a candidate's ordinary `docs/evidence` or `docs/research` still fails.
Project-specific distribution selection does not relax that scanner.

From a source checkout:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_distribution.py --source . --check-source
PYTHONDONTWRITEBYTECODE=1 python3 -m build --outdir build/package-boundary-verification
PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_distribution.py --source . --artifacts build/package-boundary-verification
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 python3 scripts/stdlib_smoke.py
```

These checks establish packaging integrity and offline behavior. Toy fixtures
do not establish model performance, Hermes runtime isolation, WikiSkill parity
or a public release. The import manifest remains a receipt for the immutable
import commit; intentional later packaging changes receive separate evidence.

Legacy metadata, wheel-license placement and archive-root compatibility have
source-backed regression fixtures. They do not establish that setuptools 68 was
built or executed. Actual build receipts identify the backend version used for
each artifact; a fixture result and a real backend build remain separate evidence.
Run receipts also distinguish a completed suite, inherited skips and an
interrupted run. The internal development records hold artifact hashes and raw
log references without changing the public files after their build verification.
