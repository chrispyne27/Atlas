# ADR 0004: Evidence-aware retrieval and SQLite migration

Status: accepted direction, 2026-10-09. The project maintainer approved the architecture review
and requested durable documentation for a separate implementation thread.
Implementation remains pending; this acceptance does not assert completed behavior.

## Context

Review baseline: dafa03b; runtime baseline documented at d5e44ad. Atlas has a
legacy JSON agent/context path and a configuration-aware SQLite inspection path.
The October architecture brief is reconciled guidance, not a replacement design.
See [architecture](../GRAPH_ARCHITECTURE.md) and the historical
[implementation snapshot](../ARCHITECTURE_SNAPSHOT.md).

## Decision

Retain SQLite as the initial local store, compiler USRs, scoped engineering
identities, compilation-specific occurrences, explicit unresolved/candidate
relations, on-demand hash-checked source, and bounded indexed queries. Complete
the retrieval migration incrementally; do not introduce a new graph engine.

Use a shared service contract for bounded graph retrieval and context construction.
Agents and the viewer should ultimately consume the same semantics. Keep exact
and literal/name discovery available independently of structural expansion;
semantic retrieval may later return candidates, never dependency proof.

Keep these evidence dimensions separate:

- producer/method and evidence kind;
- endpoint resolution (resolved, unresolved, candidate);
- configuration and target applicability;
- source/input freshness;
- engineering review decision and actor;
- confidence, when supported and meaningfully calibrated.

Do not replace them with a scalar authority hierarchy or infer approval from a
resolved endpoint. Compiler observations apply to recorded inputs/configuration;
a passing test is execution evidence, not automatic requirement satisfaction.

Support distinct retrieval modes. Partial staging inspection remains useful and
must retain explicit unknowns. Current-context retrieval eventually requires
coherent publication and freshness checks for a declared scope. Historical
retrieval must label its revision and source availability. Background processing
must not silently combine incompatible revisions or configurations.

The first SQLite packet is inspection-only. It must report
`inspection_only=true` and `context_eligible=false`; source excerpt hashes do not
upgrade whole-graph freshness. Reusing this packet in a tool does not confer
current-context guarantees. Existing readiness gates stay in force.

Use exact serialized delivery budgets with explicit units. Initial SQLite packets
use UTF-8 bytes; legacy character budgets retain their original semantics.
Model-token budgets require an identified local tokenizer and must include the
whole serialized package. Do not label characters or bytes as tokens.

Incremental indexing must account for content, membership, compilation options,
external inputs, generators, parser/toolchain identity and engineering sources.
Git diffs are only one trigger. Retain previous usable snapshots on refresh
failure. Requirements changes should request review, not declare artifacts wrong.

Keep schema extensions driven by retrieval needs. Add relationship validation
at service boundaries; preserve unknown kinds in storage but do not silently
traverse them. Production lineage, authorship and ownership are distinct future
metadata dimensions; do not force HUMAN/AI/GENERATED/THIRD_PARTY into one enum.

## Relationship to previous ADRs

- ADR 0001 remains the legacy graph/context baseline. Its shared human/agent
  semantics remain the target; they are not yet implemented across both paths.
- ADR 0002 remains the accepted legacy tool protocol and evaluation methodology.
  No MCP claim, new model dependency or revised pilot result is introduced.
- ADR 0003 remains the disk-store design. This ADR supplements its evidence,
  retrieval-mode and migration semantics. It supersedes any interpretation that
  publication must precede explicitly labeled inspection packets, or that its
  old next-chunk order requires an ingestion runner before context work.
  Current-context freshness, configuration separation and publication obligations
  are not relaxed. Ready-snapshot immutability is a target; staging is mutable.

No earlier ADR is wholly superseded. Historical validation records remain intact.

## Alternatives and tradeoffs

Replacing SQLite or materializing the complete AST adds migration and operational
cost without measured benefit. Finishing all publication infrastructure before
any packet delays retrieval feedback. An inspection-first packet provides that
feedback but requires persistent, explicit limits on what it establishes.

One authority score would simplify filtering but conflate extraction, review and
freshness. Separate dimensions cost some response/schema complexity while
preserving the evidence distinctions required by the target environment.

The legacy path remains supported until SQLite equivalents pass migration gates;
this temporarily duplicates workflows. Prefer rebuilding reproducible inputs to
creating a general legacy-JSON converter. Do not promise cross-revision entity
continuity, scale, context savings or target-platform qualification yet.

## Consequences and validation

Implement the [first increment](../SQLITE_TRACE_PACKET.md), then the ordered
migration in GRAPH_ARCHITECTURE.md. Preserve target isolation, unknowns, explicit
source failures, deterministic selection, aggregate query/work/output limits and
read-only behavior. Evaluate task success and missed dependencies alongside cost
and packet size. Existing pilot results establish no general token savings.
