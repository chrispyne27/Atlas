# Atlas graph architecture and migration

Accepted direction: 2026-10-09, following user approval of the architecture review.
Normative rationale: [ADR 0004](decisions/0004-evidence-aware-retrieval-migration.md).
This document describes the target and ordered migration, not completed features.
Current implementation baseline: dafa03b; [snapshot](ARCHITECTURE_SNAPSHOT.md).
Current implementation checkpoint and next task: [RESUME.md](RESUME.md).

## Objective and retained design

Given an engineering task, retrieve a small, trustworthy, relevant slice of the
repository, with evidence and omissions. Support agents with limited context and
weaker local models, as well as human engineering review. Core operation must
remain local and usable in air-gapped environments.

Retain configuration-aware entities/occurrences, selected compiler extraction,
SQLite indexed adjacency, explicit engineering evidence, and on-demand source.
The target pipeline is local adapters -> scoped staging snapshots -> validation
and publication -> bounded structural queries plus separate discovery -> context
construction -> agents and viewer. Partial inspection is available before
publication; it makes no current/complete-context guarantee.

A narrow service contract should cover exact lookup, typed directional neighbors,
evidence, source, bounded trace assembly and, later, refresh. Do not create a
universal graph-store framework or separate database server speculatively.

## Reconciliation with the brief

| Area | Existing implementation | Accepted disposition |
| --- | --- | --- |
| Graph-first retrieval | Exact symbols/requirements, direct calls, authored links | Preserve; retain literal/name discovery for disconnected targets |
| Identity | Compiler USRs, scoped requirements/tests, separate occurrences and compilations | Preserve; defer rename continuity; never merge configuration variants |
| Typed graph | Typed entity/evidence tables; relation kinds are open strings | Add semantic validation as operations need it; no wholesale ontology expansion |
| Provenance | Separate compiler/build/authored/inferred/execution/review kinds | Preserve; keep resolution, applicability, freshness and review independent |
| AST scope | Selected function declarations/definitions and calls | Preserve; add types/data use for concrete communication-struct tasks |
| Generated code | Origin labels and output/dependency hashes | Add producer/model/configuration/input-output binding; retain parse inputs even when excluding bodies |
| Incrementality | Legacy TU cache; SQLite dependency records and serial ingestion | Implement SQLite refresh lifecycle; measure accumulated hashing cost |
| Freshness | Input/membership audits and conservative readiness blockers | Separate inspection, historical and current-context modes; do not silently mix generations |
| Context packets | Legacy bounded character-budget packets | Build SQLite inspection packet first; migrate current-context only after gates |
| Query bounds | Indexed paginated inspection, SQL/byte/source limits | Add aggregate traversal/work/source limits, not just per-page caps |
| Requirement changes | Scoped engineering observations | Later propagate needs-review with evidence, never automatic falsity |
| Negative knowledge/reviews | relation_review schema | Later implement authorized rejection/review workflow; absence is not rejection |
| Execution | Schema and separate experimental logs | Later bind source/build/configuration/binary; preserve failed processes and environment changes |
| Temporal graph/diffs | Snapshot records | Defer history/delta infrastructure until workload justifies it |
| Vectors | Not implemented | Defer; establish structural/discovery baseline first |
| Offline deployment | Local engine/viewer and transfer candidate | Retain; RHEL/Firefox and disconnected installation remain open validation gates |

## Gaps that matter for the target repository

Application membership is not object-target naming. Establish build-backed
membership before claiming impact across approximately 24 applications. Preserve
Linux/RTOS separation and explicit cross-configuration comparison. Generated
communication types require type/data-use relationships; function calls alone
cannot establish their impact. F Prime is an authentic evaluation repository,
not proof of customer C++98/C++11, MISRA or RTOS compatibility.

Source remains implementation authority, requirements remain in their originating
system, and Git remains source history. Atlas records scoped observations and
engineering claims. Review records must bind evidence and revision; a future
carry-forward mechanism requires revalidation.

## Ordered migration and exit gates

| Order | Work | Gate before progressing to stronger claims |
| --- | --- | --- |
| 1 | Bounded SQLite inspection trace packet (completed 2026-10-12) | SQLITE_TRACE_PACKET.md acceptance; no current-context eligibility |
| 2 | Reproducible scoped ingestion runner | Explicit target/configuration, unsupported options and coverage, recoverable failures; measured time/RSS/disk/hash work |
| 3 | Toolchain/generator provenance and application scope | Verified selected inputs and declared membership/exclusions; no invented historical evidence |
| 4 | Publication and dependency-driven refresh | Coherent scoped replacement, previous usable snapshot retained on failure, dirty/untracked/membership/config changes handled |
| 5 | Freshness-checked SQLite agent context and consumer migration | Stale current-context rejection, bounded shared service, parity for required legacy behaviors and explicit differences |
| 6 | Engineering/type/data-use expansion | End-to-end tasks demonstrate need; separate execution/review evidence; requirement changes trigger review |
| 7 | Semantic retrieval and broader scale evaluation | Measured improvement over structural plus literal discovery at acceptable local resource cost |

This is a dependency order, not authorization to complete every row in one turn.
Target-host validation can run when the host is available; do not hold the first
inspection increment hostage to unrelated platform qualification. Application
scope can first be explicitly declared, but declarations must not be mislabeled
as build-proven membership. Stronger claims require the corresponding gate.

Keep legacy JSON consumers until equivalent required workflows pass. Share query
semantics without forcing the small JSON fixture to adopt the whole disk schema.
Rebuild indexes from reproducible source rather than assuming safe automatic data
conversion. Do not add a schema migration framework until an actual change needs
it; then specify compatibility and reindex/version behavior explicitly.

## Evaluation and resource policy

Evaluate task correctness, unsupported claims, missed relevant dependencies,
retrieval work/latency, index time, peak RSS, disk size and package size together.
Report budget units. Use representative high-fanout and multi-configuration cases,
not just total lines of code. Relevance per token is a useful goal but does not
replace task outcomes or evidence coverage.

The recorded three-task pilot achieved equal held-out success, with Atlas using
43–51% more before-edit response characters. It does not establish general savings.
An unused overload also demonstrated the need for non-graph discovery. Preserve
those findings ([PILOT.md](PILOT.md)); do not rewrite them to fit the new direction.

Current parsing rechecks accumulated artifacts around each compilation. Measure
this potential scaling cost before multiplying the operation across a large
repository. Source-detail calls also need aggregate limits when assembled into a
packet. Byte/result caps alone are not work or memory caps.

## Deferred work

Dedicated graph databases, full AST persistence, universal graph abstractions,
full temporal delta storage, automatic rename matching, multi-agent write
coordination, broad AI inference and comprehensive engineering ontologies remain
deferred. Add local embeddings only when discovery measurements justify them.

## Documentation ownership

- This document: durable target, gaps and ordered migration.
- docs/decisions/: significant decisions and tradeoffs, with supersession links.
- SQLITE_TRACE_PACKET.md: first increment contract and acceptance gates.
- ARCHITECTURE_SNAPSHOT.md: preserved October 1 implementation evidence/history.
- RESUME.md: latest checkpoint, tests, blockers, next bounded task.
- AGENT_INTERFACE.md and FPRIME-ACCEPTANCE.md: current interface and broader gates;
  update actual behavior when implemented, not when merely planned.
