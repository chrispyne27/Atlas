# Current project status — accepted architecture, implementation handoff

The architecture review was accepted on 2026-10-09. Read [RESUME.md](RESUME.md),
[GRAPH_ARCHITECTURE.md](GRAPH_ARCHITECTURE.md),
[ADR 0004](decisions/0004-evidence-aware-retrieval-migration.md), and
[SQLITE_TRACE_PACKET.md](SQLITE_TRACE_PACKET.md) before development.
The first task is a bounded SQLite inspection trace packet. It is not implemented
yet. The historical [snapshot](ARCHITECTURE_SNAPSHOT.md) describes the unchanged
runtime baseline. The older pause-for-review and runner-first backlog are superseded.

Chronological milestones below are preserved history, not current feature status.

---

# Atlas project brief

Enable AI agents to be primary contributors to very large codebases through accurate, bounded, current development context. Symbols and dependency graphs provide structure; requirements, tests, and engineering metadata provide intent and evidence. Vectors will help discover entry points, never establish dependency facts. The web explorer remains a human inspection surface over the same information agents receive.

## Agreed constraints
- Preserve the explorer, requirements views, and pipeline teaching model.
- Keep hosting owner-private. No public publication without explicit approval.
- Use synthetic or explicitly authorized repositories only.
- Version source, requirements, schemas, tests, and decisions in Git.
- Bind indexes and evidence to source fingerprints and revisions.
- Prove one complete development task before expanding infrastructure.
- Distinguish compiler-derived facts, explicit authored links, executed tests, and modeled estimates.

## First implementation milestone
Index a small compilable C++ rendering fixture. Retrieve context for REQ-UI-002. Reuse its existing normalization helper to correct resize handling. Run actual tests, reject stale retrieval, and incrementally refresh affected translation units. Inspect the extracted snapshot and context in the existing explorer.

## Acceptance
Exact symbol identities and source spans; compiler-derived direct calls; explicit requirement/test provenance; deterministic context budgets with reasons and omissions; stale-snapshot rejection; header invalidation; failing acceptance tests before the fix and passing tests after; honest task-oracle and payload-size comparisons.

## Current scope boundaries
One local repository and build configuration, serial parsing, JSON snapshots and translation-unit cache. No vector embeddings, graph database, production-scale benchmark, autonomous agent orchestration, or complete C++ dynamic-dispatch analysis. The hosted UI inspects build-time data; local CLI performs indexing and test execution. JSONL agent access is not an MCP server.

## Milestone 0.3 delivered
Four local agent operations, exact logging, optional compact packets, and six independent agent trials (three tasks × two arms) with held-out acceptance checks. Inspect the recorded context/patches in the Agent pilot view. Both arms passed; Atlas exposed more authored relevant context while using more response characters. See PILOT.md and ADR 0002. The next priority is staged retrieval on a larger, more discriminating fixture, not a claim of proven scaling or savings.

## Current priority: existing large repositories
The primary measure is whether an agent finds the applicable requirements,
constraints, downstream methods and tests without rediscovering them on each
request. Context volume is supporting evidence, not the main objective.
The explorer also serves human traceability and verification review, including
engineering metadata and explicitly authored critical-path classifications.

The confidential target has approximately 150k production, 150k test and 600k
generated lines, 24 applications, C++98 backend/C++11 frontend, Linux and an
embedded RTOS, and MISRA/safety-critical constraints. Generated GUI code is
mostly out of scope; communication structs remain important. F Prime is the
authorized public evaluation repository; the synthetic fixture remains useful
for controlled requirements and older-language tests. See experiments/fprime.
Configuration identity and evidence provenance must survive ingestion. A Linux
test pass is not RTOS verification. Authored and inferred mappings, human review
and actual execution evidence must remain distinguishable. A 1.7 GB index.json
reported by the user requires disk-backed queries and on-demand browser data.

## Disk-store chunk 1
The initial executable SQLite schema and ADR 0003 now define the next storage
contract. This is not yet a replacement for the JSON runtime. Four structural
integrity checks pass; ingestion, freshness enforcement, bounded APIs and viewer
integration are pending. See FPRIME-ACCEPTANCE.md and RESUME.md. Work in roughly
five-to-six-minute chunks and save/push before stopping for the user's next turn.

## Disk-store chunk 2
The local SQLite inventory importer now preserves target/command variants and
atomically writes staging snapshots. Four schema checks and seven importer tests
pass. A scoped F Prime import contains 18 compilation entries in two configurations;
this is not a parsed graph. See STORAGE.md and experiments/fprime/storage-inventory.json.

## Disk-store chunk 3
Scoped libclang ingestion now records compilation-specific function occurrences,
calls, unresolved dispatch and dependency hashes. Health parsed in Ref and UT
configurations; all snapshots remain staging. Twelve storage/compiler tests and
four schema checks pass. Requirements import and bounded retrieval remain pending.

## Disk-store chunk 4
Scoped engineering import preserves requirement definitions, test-source annotations
and candidate ID aliases with separate provenance. The real import has 12 definitions,
11 annotations and seven candidate aliases; no inferred verification approvals.
Seventeen storage tests and four schema checks pass. Snapshots remain staging.

## Disk-store chunk 5
All 11 scoped test annotations now link to unique compiler-indexed helper spans,
with separate inferred containment evidence and retained authored annotations.
Ambiguity and missing matches remain explicit; runnable test identity and
satisfaction are not inferred. Twenty-one storage tests and four schema checks pass.

## Disk-store chunk 6
Source-declared GoogleTest identities now map to compiler wrappers and direct
annotated helpers within the same object target: 21 cases, eight helper links.
Twenty-four storage tests and four schema checks pass. A corrupted local working
DB was rebuilt from source; reopened integrity passed. See STORAGE.md and RESUME.md.

## Disk-store chunk 7
Bounded read-only lookup and adjacency inspection now work against the staged
SQLite trace. Target filters, cursor invalidation, provenance summaries, SQL work
budgets and explicit truncation are tested. Twenty-eight storage tests and four
schema checks pass. Freshness-validated task context and viewer integration remain pending.

## Disk-store chunk 8
Bounded evidence and hash-checked source excerpts now work locally. Stale/missing
source never appears as current text, and external paths are excluded. The truncated
libclang installation was repaired and checksum-verified; all 33 storage tests and
four schema checks pass. Local HTTP/viewer integration remains pending.

## Disk-store chunk 9
A local read-only HTTP adapter now serves the bounded inspection operations with
fixed DB/source roots, selected target/snapshot, loopback binding and authorization.
Real F Prime HTTP smoke checks and all 41 checks pass. Viewer integration is next.

## Disk-store chunk 10
A focused local trace view now uses the bounded HTTP API, with explicit staging,
provenance and source-freshness notices. Static serving is allowlisted and tokens
remain in memory. All 43 storage/schema checks pass; browser QA is pending. The
private hosted explorer remains unchanged.
