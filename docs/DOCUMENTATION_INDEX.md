# Atlas documentation index

This index accompanies the November 6, 2026 source export at `70861de`.
Repository documents retain their original milestone dates. For current status,
start with the newest entry in `RESUME.md`, not an older milestone overview.

## Start here

| Document | Purpose |
| --- | --- |
| [Git import guide](../GIT_IMPORT.md) | Archive contents, fresh repository setup, development checks and export scope |
| [Resume](RESUME.md) | Completed SQLite inspection checkpoint and the next bounded task |
| [Project brief](PROJECT.md) | Original product purpose and graph-first objective |
| [Graph architecture](GRAPH_ARCHITECTURE.md) | Accepted target, retained design and migration gates |
| [SQLite trace packet](SQLITE_TRACE_PACKET.md) | Implemented read-only packet contract, budget semantics and acceptance evidence |
| [Architecture snapshot](ARCHITECTURE_SNAPSHOT.md) | Earlier implementation baseline, technical rationale and unresolved limitations |

## Architecture decisions

| Record | Subject |
| --- | --- |
| [ADR 0001](decisions/0001-graph-first-context.md) | Legacy graph-first context design |
| [ADR 0002](decisions/0002-controlled-agent-pilot.md) | Controlled agent pilot and interface |
| [ADR 0003](decisions/0003-configuration-aware-disk-store.md) | Configuration-aware disk store |
| [ADR 0004](decisions/0004-evidence-aware-retrieval-migration.md) | Accepted evidence-aware retrieval and migration direction |
| [Original architecture brief](reference/ORIGINAL_GRAPH_ARCHITECTURE_BRIEF.md) | Historical design input, reconciled by the accepted architecture and ADR 0004 |

## Interfaces and operation

| Document | Subject |
| --- | --- |
| [Agent interface](AGENT_INTERFACE.md) | Existing legacy JSON tools, evidence and retrieval boundaries |
| [Storage](STORAGE.md) | SQLite schema, configuration and ingestion behavior |
| [Local API](LOCAL_API.md) | Bounded inspection API, loopback access controls and local viewer |
| [Readiness](READINESS.md) | Inspection/current-context boundaries and outstanding gates |
| [External inputs](EXTERNAL_INPUTS.md) | Explicit external input mapping and audit limitations |
| [Indexer environment](INDEXER_ENVIRONMENT.md) | Recreating and verifying pinned native parser dependencies |
| [Offline pilot](OFFLINE_PILOT.md) | Transfer, platform requirements and remaining qualification |
| [Offline README](OFFLINE_README.txt) | Instructions for the separately assembled offline bundle |

## Evaluation and supporting evidence

| Location | Subject |
| --- | --- |
| [Pilot](PILOT.md) | Recorded agent comparison, methodology and replay |
| [Milestone validation](VALIDATION-0.3.md) | Earlier prototype validation |
| [F Prime acceptance](FPRIME-ACCEPTANCE.md) | Acceptance goals and explicit limits |
| [F Prime evaluation](../experiments/fprime/README.md) | Pinned upstream inputs and reproduction details |
| `experiments/fprime/sqlite-trace-packet-acceptance.json` | Recorded synthetic and F Prime checkpoint-3 traces |
| `experiments/pilot/` | Authored task runs, tool records, patches and report |
| `experiments/offline/` | Historical installer, launcher and transfer evidence |
| [Export manifest](../EXPORT_MANIFEST.json) | Export baseline, source-file changes and checks performed |

Older instructions to review the architecture or implement the first trace packet
are historical. The accepted migration and latest handoff supersede them. Broader
agent-orchestration discussions are separate design work and are not represented
here as implemented Atlas functionality or approved Atlas requirements.
