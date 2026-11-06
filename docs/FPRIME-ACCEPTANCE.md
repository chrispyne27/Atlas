# F Prime trace milestone: acceptance gates

The first post-review increment has separate inspection-only gates in
[SQLITE_TRACE_PACKET.md](SQLITE_TRACE_PACKET.md). Passing them does not satisfy
all broader milestone gates below; see [ADR 0004](decisions/0004-evidence-aware-retrieval-migration.md).

Pinned source: v4.3.0 / 7d8f579f159d2f7c2d4984d92828575e37f87fa6.
Start with Health, Command Dispatcher and evidence-backed Ref membership.
This is a scoped integration, not full F Prime or customer-repository coverage.

1. **Configuration identity:** import two configurations and multiple commands
   for one source without collapsing occurrences. Queries select a configuration
   and target; no Linux evidence appears as RTOS verification. Resolve application
   membership from build evidence, not file paths or component-name guesses.
2. **Engineering trace:** start at an indexed Health method, retrieve its resolved
   and unresolved downstream relationships, relevant requirements and linked tests
   with inclusion reasons and source spans. Method/requirement links absent from
   authored data remain missing or explicitly proposed; no invented approved link.
3. **Existing-repository discrepancy:** retain HTH-001 and ISF-HTH-001 as different
   identities; show a candidate alias and its rationale. Human review is a separate
   record. Merely importing the test annotation must not approve the alias.
4. **Execution evidence:** retain the original failed processes despite passing
   cases and the successful runs with leak detection disabled. Show binary/source
   binding if known, otherwise mark evidence linkage incomplete. Never fabricate
   missing historical binary hashes from newly rebuilt executables.
5. **Source and freshness:** load method text on demand and verify content hash.
   Change a dependency in an isolated fixture: current-context retrieval rejects
   stale data; rebuild publishes a coherent replacement. Interrupted import leaves
   the prior snapshot usable. Historical review evidence never moves automatically.
6. **Bounds and omissions:** high-fanout fixture forces pagination/truncation with
   stable ordering and no silent loss. Inspect query plans for indexed adjacency;
   measure request latency, server peak memory and response bytes. Browser startup
   and neighborhood requests must not download or deserialize the full index.
   Source texts must not be duplicated into graph rows.
7. **Human review:** viewer and agent service return the same scoped trace. Viewer
   distinguishes authored, compiler-derived, inferred, executed and reviewed facts;
   shows metadata provenance, critical-path classification and unknowns. Existing
   exploration views continue working. Preserve owner-private hosting.
8. **Scale evidence:** after the scoped trace passes, expand F Prime ingestion and
   record source/TU counts, generated proportions, DB size, indexing time and peak
   RSS. Report actual numbers; this sample cannot prove support for 24 applications
   or a 1.7 GB customer index. Packet size is secondary to relevant context quality.

Schema smoke checks cover only snapshot referential integrity, repeated source
compilation identity and preservation of unresolved relationships. They do not
satisfy the importer, runtime, browser, freshness or performance gates above.
