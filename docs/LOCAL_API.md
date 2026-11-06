# Local read-only inspection API (v1)

This is a loopback development adapter for the existing bounded SQLite inspection
operations. It is not a hosted backend, a published/complete index, a production
multi-user service or a source-freshness-validated agent context service.

## Launch

```sh
python -m atlas_engine.storage.http \
  --database .atlas/fprime-rebuilt.sqlite --snapshot SNAPSHOT_ID \
  --target TARGET_ID --repo-root ../fprime --port 8765
```

Use exact IDs from the rebuilt store/report. Database, snapshot, target and optional
repo/build roots are fixed at startup. No request may override filesystem paths,
snapshot or target. To change scope, launch a separately configured server.

The process binds exclusively to `127.0.0.1` and prints its URL and a random
per-process bearer token to the local terminal. Clients send that token in the
Authorization header. Never put it in URLs, commit it, or store it in a report.
Restarting rotates it. The API does not create a tunnel or publish a site.

## Routes

All routes use GET and return JSON. Include `Authorization: Bearer TOKEN`.

| Route | Required parameters | Optional parameters |
| --- | --- | --- |
| `/api/config` | None | None |
| `/api/lookup` | `value` | `field=name\|id`, `kind`, `limit`, `cursor` |
| `/api/neighbors` | `value` (entity ID) | `direction=in\|out`, `kind`, `limit`, `cursor` |
| `/api/evidence` | `evidence` (evidence ID) | None |
| `/api/source` | `evidence` (evidence ID) | `start`, `end` |

Config describes the selected startup scope and inspection limitations. Other
routes preserve the underlying query/evidence/source response contracts described
in STORAGE.md. `status=stale`, `unavailable` and `over_limit` source results are
successful inspection responses with no source text, not claims of current content.
Client navigation can follow returned entity/evidence IDs and continuation cursors.
There is no graph-wide download endpoint, write operation or file-serving endpoint.

## Request and response boundaries

- Exact Host must match `127.0.0.1:PORT`; an Origin header, when present, must be
  that exact HTTP origin. Cross-site fetches are denied. No CORS permission headers
  are emitted. The private hosted page cannot directly call this local API.
- Unknown/repeated query parameters and request bodies are rejected. Maximum URI
  length is 16 KiB; underlying item, response-byte, SQL work and source-file limits
  remain in force. HTTP responses are capped at 256 KiB and marked no-store/nosniff.
- POST/PUT/PATCH/DELETE/HEAD/OPTIONS are rejected; missing/wrong tokens return 401,
  wrong Host/Origin returns 403, unknown routes 404, invalid parameters 400, and
  unsupported methods 405. Database/I/O failures return a generic 503 without
  local exception traces. Query-budget exhaustion may be 400 or 503 depending on
  which underlying inspection operation reports it.
- One request runs at a time with a small listen backlog and a five-second socket
  timeout. This bounds concurrency, not total service latency on a slow filesystem.
  It is not intended for exposure to other machines or adversarial traffic.
- Each data request opens a fresh read-only SQLite connection. Token values, URLs,
  query strings and source responses are not logged by the adapter.

## Viewer integration contract

The local viewer must be served from this same origin (the focused local view
now has an explicit static allowlist) and hold the token only in memory. It should first read config and
show staging/incomplete scope, selected target and freshness limitations. Then it
can perform exact lookup, request one neighborhood/page at a time, and fetch
provenance/source only when opened. Preserve candidate and unresolved labels,
explicit omissions and shared-evidence applicability notices. Never imply that a
matched test helper or passing test is an approved requirement verification.

The existing hosted viewer remains unchanged. Live local integration and any
bounded hosted sample must be labeled distinctly; do not silently point a hosted
page at the user's local service or enable wildcard cross-origin access.

## Validation

`tests/engine/test_storage_http.py` exercises actual loopback requests, pagination,
source freshness, method rejection, authentication, Host/Origin checks and fixed
path/scope restrictions. The real smoke report is
`experiments/fprime/storage-http.json`. All five routes returned 200 against the
Health trace, pagination was exercised, and the excerpt hash matched. The test
server was shut down afterward; no background service is being promised.

The full suite has 37 storage tests plus four schema checks, all passing.

## Local trace view (chunk 10)

The loopback server now serves a focused Atlas trace view at `/`. Only these static
assets are allowed: local-trace.html, local-trace.js and local-trace.css. They do
not contain the session token and require no token to load. All `/api/*` routes
still require authorization. No generic public-directory or repository serving
is enabled; unknown paths, traversal and asset query strings are rejected.

Launch the server as above, open its printed 127.0.0.1 URL in the same machine's
browser, and enter the token from the terminal. The view refuses connection from
other hostnames. It keeps the token in memory only; disconnect/reload clears it.
The original hosted explorer and its existing views are not modified by this route.

Supported flow: connect; exact-name search (Health example: Test.NominalTlm);
select a match; follow outgoing/incoming relationships; page through results;
open provenance and a hash-verified source excerpt; navigate back or disconnect.
Staging/freshness/partial-scope notices, candidate aliases, unresolved links and
shared applicability remain visible. Relationship data and source are inserted
with textContent, not interpreted as HTML. Source-file freshness remains separate
from graph freshness and requirement satisfaction.

The view uses Atlas's established dark/mint palette and responsive columns. Static
serving and API tests passed, as did the static build and JS syntax check. At that
checkpoint, browser interaction, accessibility and visual review were pending.
The subsequent user-reported manual validation is recorded below; no private
deployment was made.
The managed preview's cloud-browser route is incompatible with this deliberately
loopback-only service; do not relax Host/Origin checks or expose its token just to
make that route reachable. Manual testing uses the packaged viewer and API on the same local computer.

Existing JavaScript regression suites also passed with
`ATLAS_PYTHON="$PWD/.venv/bin/python" npm test`. Running without that environment
selection initially failed because the system Python lacks libclang metadata;
this was an interpreter-selection issue, not a test assertion failure.


## User-reported manual validation — 2026-09-30

Project maintainer tested `atlas-local-test-01a52fc.zip` on Windows 10, Google Chrome
(version not supplied), and Python 3.14.5. All nine supplied checklist sections
passed: connect/scope notice, exact search, follow/back navigation, incoming/outgoing
relationships, evidence/source clearing, pagination with earlier/new rows, narrow
layout, keyboard/focus, and session clearing on disconnect/reload. No errors were
reported. The trace was Test.NominalTlm; paging used
`testing::internal::ParameterizedTestSuiteInfo::RegisterTests`.

The local-view checklist is now complete for that package and reported environment.
The three viewer assets and HTTP/detail/inspection/store modules are unchanged from
01a52fc through c9e9d89. Evidence is in
`experiments/fprime/local-view-manual-validation.json`. These are user-reported
manual checks, not an assistant-operated browser run, a formal accessibility audit,
or a native-indexer compatibility test for Python 3.14.5. The cloud browser skill
blocker remains separate; no workaround, deployment or privacy change occurred.
