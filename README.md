> Git export — 2026-11-06, source checkpoint `70861de`.
> Start with [GIT_IMPORT.md](GIT_IMPORT.md) for setup, Git migration, and current
> status, and [the documentation index](docs/DOCUMENTATION_INDEX.md) for design
> records. The milestone overview below describes the earlier web/JSON prototype;
> the later SQLite inspection work is documented in [RESUME.md](docs/RESUME.md)
> and [SQLITE_TRACE_PACKET.md](docs/SQLITE_TRACE_PACKET.md).

# Atlas · Graph-first context for coding agents

Atlas helps agents find focused, requirement-aware context in code repositories. It also provides a private web explorer for humans to inspect the graph and the context an agent receives.

## Current milestone (0.3)
- Logged agent tools for symbol discovery, requirement-aware context, dependency traversal and explicit refresh.
- Six independent coding-agent runs across three paired tasks, with held-out checks, patches, and inspectable retrieval records.
- **Agent pilot** view compares outcomes and context overhead; [results and replay instructions](docs/PILOT.md).
- Real libclang indexing of a small, compilable C++ fixture: stable symbol identities, overload resolution, direct calls, file includes, source spans, and explicit unresolved references.
- Versioned requirements and test mappings, with native test evidence tied to source fingerprints.
- Bounded graph-first retrieval through a CLI and local JSONL process. The browser uses the same retrieval implementation.
- Incremental translation-unit parsing, source freshness rejection, and a replayable requirement-aligned resize fix.
- Existing illustrated explorer and hypothetical pipeline lab retained alongside the new indexed fixture.

Start with [the project brief](docs/PROJECT.md), [architecture decision](docs/decisions/0001-graph-first-context.md), and [agent setup/interface](docs/AGENT_INTERFACE.md).

## Web interface
Run `npm start` (or `npm run dev` for live reload) and open http://localhost:4173. Choose **Agent pilot** to inspect recorded agent work, or **Indexed C++ fixture** / **Agent context** to inspect extracted data and retrieve a context packet. The illustrated sandbox remains available. Native compilation/indexing is local; the hosted site displays a generated snapshot.

Run `npm test` for graph/model/retrieval checks. Run `npm run build` for static assets. Browser tests require Playwright and a Chromium installation; use `npm run test:browser`. `ATLAS_PLAYWRIGHT_PATH` and `ATLAS_CHROMIUM_PATH` optionally point to preinstalled tools.

## Honest boundaries
No vector retrieval, graph database, complete C++ dynamic-call analysis, million-line benchmark, or a production autonomous-agent orchestration service yet. The fixture and its requirements are authored sample data; its code really compiles and the recorded tests really execute. Link coverage alone is not compliance. Pipeline-lab estimates remain hypothetical. The task experiment measures one deliberately small scenario; metadata overhead makes its complete graph packet larger than raw matching file text.

Custom UI metadata is browser-local and exportable, separate from versioned engineering manifests. Private access is enforced by Sites hosting. All content is synthetic and no confidential repository is connected.
