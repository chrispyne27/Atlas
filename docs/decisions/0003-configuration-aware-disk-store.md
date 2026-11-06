# ADR 0003: configuration-aware disk storage

Status: accepted design with partial implementation. Current implementation/status is
recorded in ../ARCHITECTURE_SNAPSHOT.md (2026-10-01); import, parsing, bounded
inspection and local viewer are implemented. Publication, agent task context and
other completeness guarantees remain pending. Original milestone wording below
is preserved as design history, not current completion status.

See [ADR 0004](0004-evidence-aware-retrieval-migration.md) (accepted 2026-10-09)
for evidence semantics, inspection-first migration and updated implementation
order. This ADR remains accepted; historical next-chunk ordering is superseded.

## Purpose
Serve accurate requirement, downstream-method and test context without loading
the entire repository graph into an agent or browser. The user's 1.7 GB JSON
index is evidence that monolithic delivery is unsuitable, not a benchmark of
this design. Preserve the current private explorer and agent interface.

## Storage and identity
Use SQLite for the first local, air-gap-compatible disk store. This choice
avoids requiring a database server; it is not a claim of measured scale.
`atlas_engine/storage/schema-v1.sql` is executable DDL, not a runtime migration.
All connections must enable foreign keys. Do not open arbitrary database paths
from browser requests. Concurrent readers and a single importing writer are the
initial service model; deployment storage/persistence still needs validation.

A repository has immutable snapshots identified by revision, full input manifest,
configuration key, toolchain fingerprint, schema and indexer versions. Revision
alone is insufficient for dirty files or generated inputs. Configuration keys
include platform, ABI/toolchain, language mode and build options. Linux and RTOS
snapshots stay separate; cross-configuration comparison must be explicit.

A snapshot contains build targets and evidence-backed target dependencies.
Compilation identity includes target, source path and normalized command hash.
Never deduplicate by source path alone: F Prime's UT database repeats 175 paths.
Normalize checkout/build prefixes using named roots while preserving defines,
include ordering, working-directory semantics and toolchain inputs. Retain
original commands in local evidence; never execute compile-database strings.

Entities carry logical identity (compiler USR where available). Requirements
use repository + document/component scope + authored ID, and tests use framework
+ suite/case identity. Definitions, declarations and annotations are separate
occurrences with source hash/span and compilation identity. Conflicting bodies
remain separate occurrences. Snapshot-scoped foreign keys forbid mixing graphs.
Calls and dependencies retain compilation identity and provenance; unresolved
virtual/indirect calls remain visible. FPP routing requires distinct evidence;
do not turn a generated call or port name into an assumed topology connection.

Source bodies are absent from graph rows. An on-demand source provider reads a
hash-verified checkout or content-addressed blob. Missing or changed content
returns an explicit unavailable/stale result, never the current file mislabeled
as historical source. Requirements and test annotations likewise retain spans.
Generated interfaces/communication types keep origin, generator/model evidence
and dependency hashes. Excluded generated GUI bodies may still be parse inputs.

## Evidence and engineering metadata
Compiler/build facts, authored claims, inference, execution and review are
separate evidence kinds. A resolved relation identifies endpoints, not truth
of a requirement-satisfaction claim. Candidate aliases are explicit relations;
Health's HTH-* and ISF-HTH-* identifiers must not be silently merged.

Test execution records bind binary hash, configuration, environment/options and
logs. Case outcomes are separate from executable outcomes: passing assertions
can coexist with a failed process (as observed with LeakSanitizer). Missing
case-level evidence stays unknown. Disabling leak detection is retained in the
run environment. Execution never creates a reviewed verification claim.

Reviews append decisions with actor and evidence bound to the exact snapshot
and relation. Carrying a decision across revisions requires revalidation.
Metadata accepts typed JSON values with provenance, allowing constraints and
critical-path classifications without hard-coding customer fields. The service
must validate field types, conflicting values and authorized review actors;
the SQL schema does not implement authorization or infer critical-path status.

## Freshness and publication
Import one compilation at a time into a staging snapshot. Store dependency
hashes through artifact/compilation_input records and record failures/exclusions.
Publish ready only after the declared import scope is accounted for and final
input hashes still match. "Ready" means internally consistent for that scope,
not complete analysis of every dependency. Retain the prior ready snapshot on
failure. A current-context request checks freshness and fails closed on changed
inputs; historical requests return their revision and availability explicitly.
Schema state transitions, immutable ready snapshots, evidence-kind semantics
and import-completeness checks belong to the service, not solely SQL constraints.

## Bounded query contract (next chunks)
Expose symbol lookup, source spans, directional neighbors and task traces using
the same service for agents and the viewer. Requests select snapshot and target;
ambiguous target/symbol matches require selection rather than silent merging.
The server enforces caps: initial defaults 50 items/page, maximum 200; trace
maximum 200 entities, 500 relations, depth 3 and 256 KiB serialized response.
These are starting policy values, not measured optimal settings. Source spans
have separate caps. Page cursors bind snapshot, filters and deterministic order.

Every response includes snapshot/configuration, source freshness, declared scope,
unresolved counts, inclusion reasons, truncation reason and continuation cursor
where continuation is supported. Graph bounds never imply that omitted paths
or absent links do not exist. Query work must be bounded with indexed adjacency
and cancellation; limiting serialized results alone is insufficient.

The existing static hosting cannot directly query a local SQLite file. A local
service is the first integration target for air-gap use. Hosted integration must
verify supported authenticated backend/storage capabilities or use explicitly
labeled bounded snapshots; do not expose an unauthenticated local tunnel or
claim a static export is live access to the full graph.

## Validation and next work
See `docs/FPRIME-ACCEPTANCE.md`. This chunk validates structural invariants only.
Importer, freshness enforcement, query caps, viewer integration and performance
measurements remain pending. Existing JSON consumers stay supported until the
new bounded service passes the trace acceptance gates.
