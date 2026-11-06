# Atlas Git import guide

Prepared November 6, 2026 from source commit
`70861deabe1ba009000250d3d7d117479ee3c5fd`
(“Validate SQLite inspection trace packets end to end”). The local working tree
was clean, and the live source remote's `main` branch matched this commit.

This is a source snapshot for a **fresh Git repository**. The ZIP does not contain
the old `.git` directory, commit history, remote credentials, or managed hosting
identity. All 174 remaining tracked project files are included, together with
the original architecture brief and this handoff documentation.

## Import into your repository

Extract the ZIP, then open a terminal inside the extracted `atlas` folder:

```sh
git init -b main
git add .
git commit -m "Import Atlas checkpoint 70861de"
```

Create an empty repository with your preferred Git host. Use its repository URL
in place of `YOUR_REPOSITORY_URL` below:

```sh
git remote add origin YOUR_REPOSITORY_URL
git push -u origin main
```

These commands start a new history; the source commit above identifies the old
baseline, but will not exist as a commit in the new repository. This export did
not publish, push, or change access to the existing Atlas site.

## What is included

| Location | Contents |
| --- | --- |
| `atlas_engine/` | Legacy C++ indexer and test runner; SQLite graph storage, ingestion, inspection, evidence/source detail, trace packets and loopback API |
| `public/` | Original web explorer, generated demonstration snapshots, and local SQLite trace viewer |
| `tests/` | Python engine tests and JavaScript graph, retrieval, pilot and browser checks |
| `samples/aurora/` | Authored C++ fixture, compilation database, requirements and test mappings |
| `scripts/` | Agent interface, reproduction, validation, offline packaging and local launch tools |
| `docs/` | Architecture, decisions, requirements/evidence boundaries, setup, local API and current development handoff |
| `experiments/` | Recorded synthetic pilot runs, F Prime evaluation evidence, offline validation records and upstream notices |
| `docs/reference/ORIGINAL_GRAPH_ARCHITECTURE_BRIEF.md` | Original architecture input; accepted ADRs and the current handoff take precedence |
| `EXPORT_MANIFEST.json`, `CHECKSUMS.sha256` | Baseline, export-only changes, validation scope and file checksums |

The dependency manifests and locks are included. Installed dependencies, virtual
environments, generated build directories, local databases, and external F Prime
source/build trees are excluded. This ZIP is a developer handoff, not the older
offline installer bundle with bundled wheels. Existing license and notice files
are retained; no new Atlas license was assigned during export.

## Current development state

The first bounded SQLite inspection trace-packet increment is complete through
checkpoint 3. It provides a read-only service/CLI with bounded traversal,
evidence/source details, deterministic output, configuration isolation and
explicit omissions. Packets remain `inspection_only=true` and
`context_eligible=false`.

The legacy JSON agent workflow and the SQLite inspection workflow coexist.
Current-context publication, full agent migration, scoped ingestion orchestration
and broader platform/scale qualification remain unfinished. Historical reports
do not establish current whole-repository freshness or requirement satisfaction.

Read these documents in order before continuing development:

1. `docs/RESUME.md` — newest checkpoint and next bounded task.
2. `docs/GRAPH_ARCHITECTURE.md` — accepted target and migration order.
3. `docs/decisions/0004-evidence-aware-retrieval-migration.md` — accepted rationale.
4. `docs/SQLITE_TRACE_PACKET.md` — implemented contract, validation and limits.
5. `docs/ARCHITECTURE_SNAPSHOT.md` — earlier baseline and rationale; historical.

The next task recorded in the current handoff is a reproducible scoped ingestion
runner for one explicit target/configuration, preserving coverage, unsupported
options, failure records and recovery. Start from the existing implementation
and tests. Older documents that still describe the trace packet as pending are
historical; use the newest `RESUME.md` entry and `SQLITE_TRACE_PACKET.md` for status.

## Quick static preview

From the extracted repository root, using Python 3:

```sh
python -m http.server 4173 --bind 127.0.0.1 --directory public
```

Open `http://127.0.0.1:4173`. This serves the original generated demonstration
explorer. Use `docs/LOCAL_API.md` for the separate SQLite viewer and its authenticated
loopback API. The static preview does not create or connect to a SQLite database.

## Developer environment and checks

Python 3, Node.js and a C++ compiler are used by the project. Native indexing also
requires the pinned libclang wheel. Follow `docs/INDEXER_ENVIRONMENT.md` to create
and verify that environment. The existing agent setup documentation specifies
Python 3.10+; the export checks used Python 3.12.14. Host-specific native and
offline prerequisites are documented separately.

These checks do not need libclang or a browser installation:

```sh
python scripts/check-storage-schema.py
python scripts/check-trace-packet.py
node tests/model.test.mjs
node tests/retrieval.test.mjs
node tests/pilot-report.test.mjs
node scripts/build.mjs
```

The trace check creates a temporary synthetic fixture and does not claim a fresh
F Prime run. The build copies static assets to `dist/`.

After installing and verifying native dependencies, the broader checks are:

```sh
python -m unittest discover -s tests/engine -v
npm test
```

`npm test` includes native-indexer integration; it is not a dependency-free check.
Optional live development and browser tests use the versions pinned in
`package-lock.json`; `npm ci` installs those packages. Follow the browser setup
requirements in the existing README before `npm run test:browser`.

## Export adjustments and evidence

Application logic and test logic were preserved. Export-only changes replace
personal names with a project role, replace the web avatar initials with `AT`,
remove personal account-usage discussion, add handoff navigation, and normalize
historical checkout paths in documentation. Existing hosting identity is omitted,
and `.gitignore` also excludes hosting identity and local environment files.
`EXPORT_MANIFEST.json` records every changed source file and its hashes.

Historical experiment logs retain their original temporary execution paths for
evidence. They are not install locations. One manual-validation record has its
tester name replaced with a project role; its reported results are unchanged.
Personal conversation history was not exported. Synthetic task prompts and tool
records already committed under `experiments/` are retained for reproducibility.

`CHECKSUMS.sha256` covers all delivered files except itself. A system with
`sha256sum` can check the extracted tree with `sha256sum -c CHECKSUMS.sha256`.
The export was checked for archive integrity, safe extraction paths and file
checksum agreement. The included validation record states which runtime checks
were performed; broader historical test results remain in their original reports.
