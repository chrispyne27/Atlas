> Current status (2026-10-01): This document includes historical milestone status; later implementation supersedes earlier pending-feature statements. See [ARCHITECTURE_SNAPSHOT.md](ARCHITECTURE_SNAPSHOT.md). New implementation is paused for architecture review.

# Local disk-store status and usage

The v1 store currently imports a **scoped compilation inventory** into SQLite.
The scoped compiler operation below adds function symbols, calls and dependency
inputs. It does not publish ready snapshots, serve graph queries, migrate old
index.json files, or connect the browser to the database.
Python's standard library is sufficient for this inventory step.

```sh
mkdir -p .atlas
python -m atlas_engine.storage init --database .atlas/fprime-staging.sqlite
python -m atlas_engine.storage import-manifest \
  --database .atlas/fprime-staging.sqlite \
  --repository ../fprime \
  --build-root ../fprime/build-fprime-automatic-native-ut \
  --compilation-database ../fprime/build-fprime-automatic-native-ut/compile_commands.json \
  --repository-id nasa-fprime \
  --source-uri https://github.com/nasa/fprime.git \
  --revision 7d8f579f159d2f7c2d4984d92828575e37f87fa6 \
  --configuration-key linux-debug-ut \
  --toolchain-fingerprint gcc-13.3.0-cxx14-fpp-3.3.0 \
  --target Svc_Health --target Svc_Health_ut_exe \
  --target Svc_CmdDispatcher --target Svc_CmdDispatcher_ut_exe
```

For the Ref inventory, change the build root/database to `build-atlas-ref`,
configuration to `linux-debug-ref`, and select only `Svc_Health` and
`Svc_CmdDispatcher`. Build prerequisites are in experiments/fprime/README.md.
The resulting scoped evidence is recorded in storage-inventory.json there.

## Implemented guarantees
- Foreign keys enabled on each connection; unsupported schema versions rejected.
- Atomic initialization and import. Failed imports roll back all their rows;
  previous snapshots are untouched. Successful imports create a new staging ID.
- Commands stored as data, never executed. `arguments` arrays or POSIX-quoted
  `command` strings supported. Original entry and ordinal retained as evidence.
- Same source can belong to multiple object targets or command variants. Exact
  target/source/command duplicates share one compilation row with separate
  original-entry evidence. Sources and build files use named-root identities.
- Source files hashed in 1 MiB blocks; hashes checked again before commit.
  Source bodies are not stored in graph tables. Symlink escapes outside declared
  roots are rejected. Generated files under build root are marked generated.
- Target scope must be explicit. Missing targets, selected source files or changed
  inputs fail the import. Unselected unbuilt generated files are not imported.

## Current limits
The full compilation database is loaded in memory with a hard 32 MiB input cap.
This is not a loader for the user's 1.7 GB graph JSON. At inventory-import time only selected source files and the database itself are
hashed, and compilation rows stay pending. The separate parse operation below
extends this to observed dependency headers; generator inputs and linked libraries
are not yet discovered.

`revision` and `toolchain-fingerprint` are operator-supplied labels, not verified
fingerprints. Arguments retain original absolute paths and order in the hash;
relocating a checkout can change compilation IDs. Working directory is included.
Named-root artifact paths are portable; argument normalization is deliberately
conservative until compiler-aware handling exists. Response files are rejected.
Windows command-string quoting, compiler wrappers, shell operators and plugin
semantics are not interpreted by this inventory; a future parser must validate
or reject them before attempting compiler analysis. Never run stored commands.

CMake's `output` field must expose `CMakeFiles/<target>.dir/` for selected entries.
Targets are stored as kind `other`; this is not proof of application or library
membership. No target-dependency edges are fabricated. Paths within the repository
but outside its designated build root are treated as authored by this initial
adapter; other generated roots require a later explicit origin policy.

Final hash checks detect changes observed during import, not later mutations.
Runtime freshness checks remain pending. No schema migration or read-only HTTP
service is implemented. The SQL contract still relies on the future service for
ready-snapshot immutability, authorized reviews and evidence-kind semantics.

## Validation

```sh
python scripts/check-storage-schema.py
python -m unittest discover -s tests/engine -p test_storage.py -v
```

Four schema checks and seven importer tests cover repeated compilation commands,
exact duplicates, configuration separation, rollback after partial writes,
changed source detection, generated source identity, root escapes, missing scope,
response-file rejection, safe command storage and reopening/version handling.

## Scoped compiler ingestion (chunk 3)

The next operation parses one pending/failed compilation in a staging snapshot
using pinned libclang (`pip install -r requirements-indexer.txt`). Select its ID
from the local database; no public API or graph browser is available yet.

```sh
.venv/bin/python -m atlas_engine.storage parse-compilation \
  --database .atlas/fprime-staging.sqlite \
  --snapshot SNAPSHOT_ID --compilation COMPILATION_ID \
  --system-include /usr/lib/gcc/x86_64-linux-gnu/13/include
```

That explicit include path is specific to the tested Linux GCC installation.
The parser validates a narrow driver/flag subset and never invokes stored
commands. Wrappers, shell operators, response files and plugin/pass-through flags
are rejected. Unsupported flags require deliberate adapter work, not stripping
until a misleading parse succeeds.

A discovery pass identifies dependencies, then their hashes are captured before
a second parse. Dependency-set and hash checks reject observed concurrent changes;
known snapshot inputs are checked before and after ingestion. This is not an OS
filesystem snapshot or protection against adversarial change-and-restore races.
External system headers are hashed and recorded with origin `external`; their
bodies are excluded from AST traversal. Their absolute paths are host-specific.

Function declarations/definitions are stored as occurrences tied to compilations.
Calls have compilation-specific evidence and caller/callee logical identities.
Compiler-resolved external callees can exist without a local definition. Virtual
and indirect calls remain unresolved. No source bodies are copied into the DB.
Dependencies currently mean translation-unit input membership, not file-to-file
include edges. Type layouts, FPP routing, application membership, macro-generated
cross-file spans and complete language semantics remain outside this adapter.

Successful compilations become `parsed`; snapshots stay `staging`. On parse
failure partial graph changes roll back and the compilation is marked failed with
a diagnostic record. Retrying a failed compilation is allowed; re-parsing a parsed
one is rejected. Header changes require a new coherent snapshot, not mutation of
already recorded artifacts. Ready publication and query-time freshness are still
pending. Snapshot input hashes now include discovered dependencies and target scope.

`experiments/fprime/storage-parsing.json` records two actual Health parses: Ref
and UT. Counts include declarations and definitions in repository/build headers;
they are not distinct method counts or a complete F Prime graph.

```sh
.venv/bin/python -m unittest discover -s tests/engine -p 'test_storage*.py' -v
python scripts/check-storage-schema.py
```

Twelve storage/import/compiler tests plus four schema checks cover compilation
variants, direct/unresolved calls, dependency invalidation, concurrent mutation,
compiler-error rollback and unsupported compiler options. Authored requirements and annotations are imported by the separate operation
below; executed verification evidence is not yet imported into this graph.

## Authored engineering import (chunk 4)

```sh
python -m atlas_engine.storage import-engineering \
  --database .atlas/fprime-staging.sqlite --snapshot SNAPSHOT_ID \
  --component Svc/Health --component Svc/CmdDispatcher
```

This narrow adapter imports Markdown requirement rows from each component's
`docs/sdd.md` and literal `REQUIREMENT("ID")` annotations from `test/ut/*.cpp`.
It is scoped explicitly to these two F Prime components. Definitions retain
source hashes/spans and declared verification methods. Requirement identity is
scoped to the selected document, so identical IDs in different documents do not
collapse. Full requirement text remains in the source, not duplicated in rows.

The test entity currently represents an **annotated source file**, not a runnable
GoogleTest case. Each annotation is an occurrence and an `annotates_requirement`
relation with authored provenance. `resolved` means the referenced ID entity is
identified; it is not a coverage or satisfaction assertion. IDs absent from the
selected document are reference-only entities with annotation occurrences and no
definition occurrence. No implementation link is inferred from component location.

Health's ISF-HTH-* references are distinct from its HTH-* definitions. Prefix
matching creates seven `candidate_alias` relations with inferred evidence and
resolution `candidate`. There are no approval records and no automatic ID merging.
A reviewer must establish equivalence before consumers treat them as aliases.

Comments, ordinary strings and raw strings are excluded from annotation scanning.
Preprocessor activation is **not** evaluated; annotations remain textual evidence,
including when imported into a snapshot where the test is not compiled. Nonliteral
macro arguments, other test frameworks, arbitrary requirement-table formats and
executable test/helper associations are outside this adapter. Directory membership
changes also need explicit freshness policy before snapshots can be published.

Engineering import is atomic and restricted to staging snapshots. Duplicate
requirement definitions, repeated component import, stale known artifacts or
changed inputs roll back all changes. Re-import into a new snapshot after edits.
Existing stored artifacts are checked before/after; added source files are not
implicitly pulled into a previously imported scope.

The actual UT snapshot import is recorded in
`experiments/fprime/storage-engineering.json`: 12 definitions, 11 annotations in
two source files, seven reference-only IDs and seven candidate aliases. It has
zero review decisions and zero execution records. Seventeen storage tests plus
four schema checks pass, including comment/string false matches, scoped IDs,
atomic duplicate rejection and stale/ready-snapshot rejection.

## Annotation-to-helper associations (chunk 5)

After importing engineering evidence and parsing a test helper compilation:

```sh
python -m atlas_engine.storage link-annotations \
  --database .atlas/fprime-staging.sqlite \
  --snapshot SNAPSHOT_ID --compilation COMPILATION_ID
```

This operation joins authored annotation lines against compiler definition spans
in **one compilation** and its input files. With exactly one containing definition,
it adds `has_requirement_annotation` from the method to the referenced requirement.
The relation retains compilation identity and inferred evidence pointing to both
the original annotation and the compiler occurrence. The original source-file
association remains intact; this derived relation cannot feed back into matching.

No match produces an `unmatched` evidence record; multiple overlapping definitions
produce `ambiguous` evidence with candidate occurrences and no method link. This
conservative line-level policy can leave same-line or nested definitions ambiguous.
It does not guess the innermost method or discard alternate compilation variants.

A matched relation means **source-span containment only**. The annotation may be
inside an inactive preprocessor branch within an otherwise compiled function.
Activation is not established; neither a runnable GoogleTest case nor requirement
satisfaction is inferred. `resolved` refers to the method/requirement identities,
not a verification judgment. Health aliases remain unapproved candidate relations.

Linking requires a parsed compilation and staging snapshot, checks input hashes
before and after, and writes atomically. Repeat linking for the same compilation
is rejected; import all applicable authored annotations first. It does not publish
the snapshot or support incremental remapping after source edits.

The real Health and Command Dispatcher helper files parsed and linked successfully:
all 11 annotations matched uniquely across eight helper methods (seven Health
helpers and Command Dispatcher's `runNominalDispatch`). The report is
`experiments/fprime/storage-test-helpers.json`. Twenty-one storage tests and four
schema checks pass, including overlapping spans, unmatched annotations, preservation
of compilation variants, stale-source rejection and unchanged authored evidence.

## GoogleTest case mapping and rebuild (chunk 6)

`map-test-cases --database DB --snapshot ID --compilation ID` recognizes simple
source `TEST(Suite, Case)` declarations and matches each to a unique compiled
`Suite_Case_Test::TestBody` definition at the same source line. Case entities are
scoped to the build target; wrapper and helper symbols remain separate entities.
Comments/strings are excluded. TEST_F, parameterized/custom macros, macro definitions
in the same file and generalized registration discovery are not supported.

`test_body` links retain the source declaration and matched compiler occurrence.
`invokes_annotated_helper` requires a resolved direct call from that wrapper and
an annotated helper compilation belonging to the same object target. Evidence
retains the direct-call relation and helper compilation. Multiple helper variants
remain separate evidence; no single behavioral implementation is selected.
Unmatched/inactive declarations and ambiguous wrappers retain diagnostic evidence
without a wrapper link. Snapshot inputs are checked before/after the atomic write.

The scoped F Prime result maps all 21 source-declared cases to compiled wrappers,
with eight links to annotated helpers (seven Health, one Command Dispatcher).
These are source/AST identities, not confirmation of binary registration or a new
execution result. No test_run records, verification approvals or alias approvals
are created. Snapshots remain staging. Twenty-four storage tests plus four schema
checks pass, including target isolation and ambiguous/unmatched wrapper behavior.

A follow-up integrity check found the previous local working DB malformed. The
cause was not established. It was retained locally; do not use it. Source commits
and reports were intact. `scripts/rebuild-fprime-store.py` recreated the experiment
from source in a new DB and verified both in-connection and reopened integrity.

```sh
.venv/bin/python scripts/rebuild-fprime-store.py --repo ../fprime \
  --database .atlas/fprime-rebuilt.sqlite \
  --system-include /usr/lib/gcc/x86_64-linux-gnu/13/include \
  --report experiments/fprime/storage-test-cases.json
```

The script refuses to overwrite an existing DB; choose a new filename on rerun.
It imports the two scoped configurations, parses the six selected TUs, imports
engineering data, joins helpers and maps cases. The report contains new snapshot
IDs; older reports describe the prior experiment, not IDs in this rebuilt store.
The active local store is now `.atlas/fprime-rebuilt.sqlite`.

## Bounded read-only inspection (chunk 7)

```sh
python -m atlas_engine.storage.inspect lookup \
  --database .atlas/fprime-rebuilt.sqlite --snapshot SNAPSHOT_ID \
  --target EXACT_TARGET_ID --value Test.NominalTlm
python -m atlas_engine.storage.inspect neighbors \
  --database .atlas/fprime-rebuilt.sqlite --snapshot SNAPSHOT_ID \
  --target EXACT_TARGET_ID --value ENTITY_ID --direction out --limit 10
```

`lookup` matches exact `name` (default) or `id`, with optional kind filtering.
`neighbors` supports incoming/outgoing adjacency and an optional relation-kind
filter. Responses carry source revision, configuration and snapshot state; they
are **inspection only**, including when the selected graph is still staging.
Current-source freshness is not checked. Do not use this operation as approved,
current task context. There is no HTTP endpoint or hosted viewer integration yet.

The DB is opened with SQLite `mode=ro` and `query_only=ON`; missing stores are
not created. Every query requires exact snapshot and build-target IDs. Compiler
relationships are filtered to that target. Shared authored requirements, file-level
annotations and candidate aliases remain visible with an explicit notice that
target applicability is unverified. Lookup may return multiple same-name entities;
consumers must choose an identity, never silently collapse them.

Pages default to 50 and cap at 200 items and 256 KiB serialized JSON. Oversized
text fields are clipped at 2048 characters with `fields_truncated`; evidence body
JSON and source bodies are not loaded. Provenance includes evidence ID, kind,
producer, source path and line. Counts describe the returned page, not full
coverage. Unresolved calls and candidates retain their original resolution state.

Continuation tokens bind filters, snapshot, target and a local database-file
version (main/WAL file identity, size and modification/change times). Any observed
DB change invalidates the cursor. This is conservative local inspection behavior,
not a cryptographic authorization token or portable database revision mechanism.
Tokens are not reusable after copying/restoring the store. Concurrent observed
changes during a query trigger a retry error; immutable published snapshot tokens
are future work. Paging orders entities by name/ID and relations by kind/ID.

SQLite progress callbacks stop a query after approximately 2 million VM steps or
0.5 seconds, checked every 1000 steps. This bounds SQL work but is not a hard wall-
clock deadline for filesystem I/O. Work-budget errors return no misleading partial
results. Item/byte limits instead return explicit truncation and continuation.
Queries use indexed entity lookup and incoming/outgoing adjacency; a test verifies
the outgoing query plan uses relation_out. This is not a large-codebase benchmark.

The recorded real trace in storage-inspection.json follows Test.NominalTlm into
its annotated helper, ISF-HTH-001 and its **candidate** HTH-001 alias. A one-item
page exercises continuation. Sixteen non-native storage tests and four schema checks
cover read-only behavior, target isolation, changed/filter-mismatched cursors,
byte truncation and indexed adjacency as well as prior importer behavior.

Validation limitation: the full storage-suite rerun terminated with process exit
135 after seven tests when reaching native-parser-dependent checks. The cause is
not established. The sixteen non-native storage checks and four schema checks
passed separately; do not report the entire 28-test storage suite as revalidated.

## Evidence and source details (chunk 8)

```sh
python -m atlas_engine.storage.details evidence \
  --database .atlas/fprime-rebuilt.sqlite --snapshot SNAPSHOT_ID \
  --target TARGET_ID --evidence EVIDENCE_ID
python -m atlas_engine.storage.details source \
  --database .atlas/fprime-rebuilt.sqlite --snapshot SNAPSHOT_ID \
  --target TARGET_ID --evidence EVIDENCE_ID --repo-root ../fprime \
  --start 138 --end 146
```

Evidence must be attached to an occurrence or relation visible in the selected
target or shared snapshot scope. Retrieval is read-only and preserves provenance.
Raw and serialized evidence details are capped at 64 KiB; oversized bodies return
`details_status=over_limit` rather than silently cutting JSON. Source excerpts are
restricted to explicitly supplied repo/build roots and hash-bound artifact paths.
External system headers cannot be read through this operation. Escapes outside
supplied roots, missing paths and unreadable/non-UTF-8 files return unavailable.

Source spans are at most 200 lines; serialized responses cap at 64 KiB. A source
file must fit a 16 MiB read cap. The entire bounded file is hashed before returning
any excerpt, with before/after stat checks. Changed content returns stale with
no text. Oversized content returns over_limit with no text. Hash verification is
for this artifact only; it does not establish current graph freshness or prevent
adversarial filesystem change-and-restore races. No HTTP service is added.

The prior native-parser crash was reproduced while loading libclang. Its local
shared library was 30,411,776 bytes versus 63,703,544 bytes in the package RECORD,
and its hash failed. Reinstalling pinned libclang 18.1.1 with `--force-reinstall
--no-cache-dir` restored the expected size/hash. The cause of the truncation is
unknown; this does not establish the cause of the earlier database corruption.
Native smoke parsing and the full regression suite now pass: 33 storage tests and
four schema checks. storage-details.json records a real Health evidence/excerpt
response and the repaired native library checksum result. Earlier failed-run
reports remain historical records, not current validation status.

## Local HTTP adapter (chunk 9)
A loopback-only, read-only adapter now exposes bounded queries, evidence and source
inspection with fixed scope/roots and per-process authorization. See LOCAL_API.md
for the contract and constraints. All 37 storage tests and four schema checks pass.
The hosted viewer is unchanged; static local viewer serving is not implemented yet.


## Recorded-input freshness audit (chunk 11)

```sh
python -m atlas_engine.storage.freshness \
  --database .atlas/fprime-rebuilt.sqlite \
  --snapshot bd6c4ddd353f4437a03812c834743c5c \
  --repo-root ../fprime \
  --build-root ../fprime/build-fprime-automatic-native-ut
```

This standard-library CLI audits recorded artifacts across one snapshot. It opens
SQLite read-only and never promotes or modifies the snapshot. Status is `stale`
when changed/missing inputs or observed concurrent edits are found; `incomplete`
when any recorded input cannot be checked or a budget is exhausted; otherwise
`recorded_inputs_match`. Every result retains `context_eligible: false`.
A matching result does not mean all compilations were parsed or requirements met.
Compilation-state counts are reported separately.

Only explicit repo/build roots are read. External paths stored in the database
are reported as not checked, never followed. Paths escaping supplied roots and
nonregular files are excluded. Hashing streams in at most 1 MiB blocks; defaults
cap the scan at 10,000 artifact rows, 16 MiB per file and 256 MiB total read bytes.
Reports retain at most 50 problem examples (and expose truncation). These are
work/data bounds, not a hard wall-clock deadline on a slow filesystem.

Before/after file metadata and a final metadata pass detect observed edits during
the audit. Observed database changes reject the report. This is not an atomic
filesystem snapshot and cannot exclude adversarial change-and-restore races.
New files, directory membership, external toolchain files, undiscovered generator
inputs, binary identity and requirement verification remain outside this check.
This CLI is not yet called by the viewer/API or used as an agent retrieval gate.

The real UT snapshot report is `experiments/fprime/storage-freshness.json`:
171 repo/build artifacts match, 302 external artifacts remain unchecked, so the
result is incomplete. Five compilations are parsed and nine pending in this
snapshot; the separate Ref snapshot is not included in that count.

Validation: seven new audit tests cover changes/missing inputs, explicit roots,
external paths, escapes, nonregular files, budgets, edits after hashing and
read-only semantics. Native compiler tests were not rerun in this chunk because
the prior `.venv` no longer exists. This audit has no libclang dependency.


## Engineering directory membership (chunk 12)

New engineering imports use `fprime-engineering-2` and record a versioned discovery
manifest in each component's authored import marker. The explicit Health and
Command Dispatcher scopes select immediate `docs/*.md` and `test/ut/*.cpp` entries.
Discovery records both logical and resolved member paths. It is nonrecursive and
caps each directory at 1,000 examined entries, rejecting escaped symlinks, missing
members, nonregular members and oversized paths. This does not add support for
parsing requirements in arbitrary documents: the requirement parser still reads
only `docs/sdd.md`; other Markdown filenames are membership/invalidation evidence.

Discovery is compared again before the engineering transaction commits. An observed
addition/removal/retargeting rolls back the import. The freshness audit compares
recorded discovery before and after hashing: changed membership makes the audit
stale even if all old file hashes still match. Missing roots, unavailable discovery
or missing recorded manifests cannot yield an overall complete match. Older
engineering markers report `not_recorded`; no historical baseline is invented.

Files outside these exact scopes (other suffixes, nested subdirectories, other
components, generator inputs) remain outside this policy. Changes to unparsed
Markdown contents are not checked merely because its filename was discovered.
This remains an observation-based check, not an atomic filesystem snapshot or
an approved requirement verification. No publication, API/UI or eligibility change.

`experiments/fprime/storage-membership.json` records a new inventory/engineering-only
F Prime probe in `.atlas/fprime-membership-probe.sqlite`: both component discovery
manifests match, with all 14 compilations still pending and context_eligible=false.
The active parsed DB `.atlas/fprime-rebuilt.sqlite` was not modified; its original
engineering markers correctly report membership not recorded.

Seven new tests cover file additions, missing folders, old markers, scope exclusions,
entry budgets, escaped symlinks, mid-import rollback and mid-audit changes. All 41
non-native storage/API tests and four schema checks pass. Native parsing and
browser interactions were not exercised in this chunk.
