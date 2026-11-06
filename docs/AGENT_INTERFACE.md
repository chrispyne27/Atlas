> Current status (2026-10-01): This document describes the legacy JSON agent path, not equivalent SQLite agent integration. See [ARCHITECTURE_SNAPSHOT.md](ARCHITECTURE_SNAPSHOT.md). Architecture accepted 2026-10-09; the planned SQLite inspection packet is specified in [SQLITE_TRACE_PACKET.md](SQLITE_TRACE_PACKET.md) and ADR 0004. It is not yet implemented.

# Agent integration: local tools and pilot

## Setup
Python 3.10+, Node 18+, and g++ or clang++ with a working linker are required. The libclang Python wheel provides the parser library; native tests also require a C++ compiler. Windows can use a native LLVM/MinGW installation; WSL is not required. Set CXX to the compiler executable if needed.

From the repository root, install the parser in your Python environment:

```
python -m pip install -r requirements-indexer.txt
python -m atlas_engine index --repo samples/aurora
python -m atlas_engine test --repo samples/aurora
python -m atlas_engine index --repo samples/aurora
```

The final index joins the executed results to the exact source fingerprint. A changed source snapshot never inherits passing results from the previous snapshot.

## One-shot context

```
node scripts/agent.mjs context --repo samples/aurora --seed REQ-UI-002 --budget-chars 32000 --max-hops 3
```

A seed can be a requirement ID, compiler USR, exact qualified signature, or unique qualified name. Overloaded names are rejected with candidates. Requirements can lead to implementations, linked test fixtures, related constraints, callers, callees, and declaration headers. Test nodes and files are terminal context, preventing a common test harness from expanding into the whole codebase. Component display groupings do not drive agent retrieval.

## Persistent JSONL process

```
node scripts/agent.mjs serve --repo samples/aurora
```

Send one request per line:

```json
{"id":1,"operation":"get_task_context","arguments":{"seeds":["REQ-UI-002"],"task":"Normalize viewport resizing consistently","budget_chars":32000,"max_hops":3,"max_nodes":60}}
```

Responses contain either `result` or a structured `error` carrying `code`, `message`, and `details`. Each request reloads the snapshot and verifies local input hashes. Queries do not edit source. The explicit `refresh_index` operation invokes the fixed local indexer; no caller-supplied command is accepted. This is a local JSONL adapter, not MCP/HTTP. An agent can use the CLI through its normal terminal tool or connect a process adapter.

## Tools and recording

`list_tools` returns the available operations and argument descriptions. The process supports:

| Operation | Arguments | Result |
|---|---|---|
| `lookup_symbol` | `query`, optional `exact` (default true), `limit` | Identities, source spans/hashes, provenance; ambiguity is an error for exact queries |
| `get_task_context` | `seeds`, `task`, `budget_chars`, `max_hops`, `max_nodes`, `detail` | Budgeted complete excerpts with reasons, constraints, edges and omissions |
| `traverse_dependencies` | `seed`, `direction`, `types`, `max_hops`, `max_nodes` | Bounded incoming/outgoing/both reachability with predecessor and provenance |
| `refresh_index` | No arguments | New fingerprint, parse/reuse counts, or a structured indexing error |

All graph queries reject stale source; lookup and traversal do not silently bypass this gate. Directory contents remain subject to the existing local snapshot/concurrency limitations.

```sh
node scripts/agent.mjs serve --repo samples/aurora --log artifacts/agent-session.jsonl
```

The optional log captures exact requests/responses, timestamps, response character counts and time spent inside the tool. Treat logs as source-bearing artifacts. A caller connects through its normal subprocess or terminal facility; no API key or model vendor is built into Atlas. The pilot in [PILOT.md](PILOT.md) demonstrates actual coding agents using this adapter, alongside ordinary file tools.

`detail: "compact"` suppresses generic method descriptions and non-requirement metadata while retaining complete excerpts, source hashes, provenance, requirements/constraints, and evidence. It does not deduplicate overlapping file/method excerpts yet. One-shot context also accepts `--detail compact` and `--log PATH`.

## Context contract
- Full source excerpts are included atomically; omitted snippets are not silently truncated.
- Each item provides identity, source span/hash, provenance, selection reason, and its predecessor in traversal.
- Returned relationships identify their provenance. Requirements and tests are explicit authored mappings.
- Budgets are compact JSON **character** counts, not tokenizer estimates. Pretty printing adds formatting characters.
- `coverage.complete` means all candidates within the configured traversal fit; it does not prove complete repository impact. `node_limit_reached`, budget omissions, and unresolved references remain explicit.
- Unknown IDs, ambiguous symbols, bad arguments, insufficient budgets, and stale input hashes are errors.
- Freshness is checked twice per request, but there is no filesystem lock. Verify the fingerprint again before applying a change in a concurrent editing workflow.

## Index scope
`compile_commands.json` must use `arguments` arrays; command-string quoting and duplicate configurations are rejected. Compiler plugins/response files are unsupported. Source and local include files are hashed; external/system headers are not versioned in this first milestone. The libclang package version and compilation configuration participate in cache identity. A compatible Clang configuration is required; MSVC-specific flags are not translated.

This is a direct-call source graph. Virtual/indirect calls and referenced declarations without indexed authored definitions are listed separately; no dynamic target set is invented. Local compiler parse errors stop index publication. Incremental updates reparse affected translation units; they do not incrementally update individual AST nodes. Hash inventory and context preparation still scan the small input snapshot.

## Evidence and replay

```
python scripts/reproduce.py
python -m unittest discover -s tests/engine -v
npm test
```

Replay uses a disposable fixture copy, restores the recorded baseline, reproduces four acceptance failures, retrieves context, applies the previously authored source change, checks stale-index rejection, refreshes one of six translation units, and confirms all eight tests pass. It is not a new autonomous model run. The comparison in `experiments/evaluation.json` is one explicit task-oracle experiment, not a general productivity benchmark.

## Publishing a fresh browser snapshot

After indexing and executing the fixture tests, run `node scripts/evaluate.mjs` to regenerate `public/generated/` and `npm run build` to copy static assets. The Site remains a static inspection UI; source indexing and native tests run locally. The browser and agent CLI import the same `public/retrieval.js`. Browser queries declare `deployed_snapshot`; only local verified queries declare `verified_local_inputs`.
