# First implementation increment: bounded SQLite inspection trace packet

Status: approved implementation scope, 2026-10-09; traversal core implemented
2026-10-11; evidence/source assembly and CLI implemented in checkpoint 2.
Bounded inspection increment complete with checkpoint 3 acceptance on 2026-10-12.
Current-context, publication and broader migration remain pending.
Depends on [ADR 0004](decisions/0004-evidence-aware-retrieval-migration.md).
Recommended reasoning: High. Work in 5–6 minute checkpointed chunks; stop after
each coherent chunk rather than attempting the whole migration.

## Problem and outcome

SQLite stores real scoped graph evidence, but its APIs only expose individual
inspection pages/details. Add one local CLI operation assembling a bounded trace
for one exact entity ID, snapshot ID and target ID. This is the first reusable
retrieval building block, not a current-context or verification approval service.

Reuse storage/inspect.py and storage/details.py semantics and existing target
visibility rules. A small internal refactor is acceptable if required for one
coherent read and aggregate budgets. Do not simply loop over independently
bounded pages and call the resulting operation bounded.

No schema migration, hosted/UI change, refresh implementation, inferred link
creation, tokenization dependency or snapshot promotion belongs in this increment.
Keep legacy JSON interfaces working unchanged. CLI syntax and module filename
are implementation choices; record the actual runnable command when implemented.

## Request and traversal

- Require database, exact snapshot, exact target and exact entity ID. Reuse lookup
  separately; no fuzzy seed selection or silently chosen overload in this slice.
- Support an explicit direction (out/in/both), a documented small relationship
  allowlist, max_depth, max_nodes, max_edges and max_bytes. Reject unknown request
  fields/kinds and invalid/oversized values consistently.
- Initial policy: depth 3, 50 entities, 100 relations, 64 KiB UTF-8 serialized JSON
  by default; hard maxima depth 3, 200 entities, 500 relations, 256 KiB. These are
  starting limits, not measured optimal settings; document any evidence-based
  change before implementation diverges from ADR 0003's maxima.
- Map the allowlist to actual stored semantics: calls, test_body,
  invokes_annotated_helper, has_requirement_annotation, annotates_requirement and
  candidate_alias are existing candidates. Inspect producer code before choosing
  defaults. Do not rename annotation links to IMPLEMENTS or VERIFIES.
- Traverse resolved endpoints. Candidate links may be returned but are terminal
  by default; they must not silently become traversal bridges. Unresolved edges
  retain target spelling/evidence and have no invented endpoint. Unknown stored
  kinds are not expanded; report filtering without asserting exhaustive counts.
- Deduplicate visited entities and relation IDs, preserving separate evidence and
  compilation occurrences. Deterministically order exploration and selection.
  Keep shared authored evidence's target-applicability warning.

## Response contract

Use an explicit packet schema version, distinct from SQLite schema version.
Include snapshot/revision/configuration/target, declared scope and a fixed
`inspection_only=true`, `context_eligible=false`. Report whole-graph freshness as
not established. Never promote those flags because snippets match or a DB state
label says ready.

Include entities/relationships, evidence references and bounded useful evidence
details, inclusion paths/reasons, source statuses, unresolved/candidate summaries,
limits, usage and omission reasons. Count scopes must identify returned/visited
material; bounded exploration cannot know every omitted entity. Avoid one
unqualified `complete` flag. Keep exact source identity/span/hash with each
returned excerpt and do not combine variants into one body.

Use DetailInspector's bounded hash-checked source behavior. Stale, missing,
external-unavailable, oversized or budget-omitted source must have distinct
statuses. Never substitute current text for historical text. Include a whole
selected excerpt or an explicit bounded span with truncation labeling; do not
silently cut strings to fit the budget. Selection of one occurrence must expose
that other variants were not necessarily returned.

Measure the complete compact JSON response in UTF-8 bytes, including warnings,
provenance, limits and omission metadata. If even the seed and required envelope
cannot fit, return a structured budget error. A byte count is not a token count.
A first version may return a bounded non-resumable packet with omission reasons;
do not fabricate continuation cursors for a traversal that cannot resume safely.

## Coherence and aggregate work

Keep a coherent database view for the whole operation or reject detected DB
changes across its constituent reads. Existing DB/WAL change detection is a local
observation, not a cryptographic snapshot identity. Source stat/hash checks do not
lock the filesystem or establish atomic whole-repository freshness.

Enforce aggregate SQL work/time and service-call/page/row limits across traversal
and detail assembly, plus aggregate source file/byte/hash limits. Choose and
record finite defaults and maxima before coding; retain existing per-call caps.
Count repeated I/O work or safely reuse request-local verified results. Tests must
show high fanout, cycles and repeated pages cannot cause unbounded work. Explain
whether time limits govern SQL or total processing; do not claim a hard filesystem
I/O deadline. No full-graph load or global scan solely to count omissions.

## Acceptance gates

1. Two configurations/targets sharing entities never mix compilation-bound edges
   or source occurrences. Shared evidence retains unverified applicability.
2. Candidate aliases, unresolved calls and inferred/helper annotations keep their
   original semantics. No inferred satisfaction or execution claims appear.
3. Cycles terminate; high fanout triggers explicit deterministic omissions under
   depth/entity/edge/byte and aggregate work/source limits.
4. Identical input and deterministic budgets produce stable selection/order.
   Timing-limited truncation is explicitly labeled; do not promise identical
   results under varying runtime load.
5. Stale/missing/oversized source is never returned as valid current text.
   Observed database changes cause rejection; previous read APIs still work.
6. Entire serialized packet fits its declared budget, including non-ASCII text.
   Undersized budgets fail explicitly; no dangling unlabeled references.
7. Database bytes and source files remain unchanged. Inspection flags remain
   fixed for staging and even an artificially ready-labeled test snapshot.
8. A reproducible synthetic trace demonstrates CLI lookup -> trace -> evidence /
   source. Use the real F Prime trace if available, keeping missing links explicit;
   synthetic success is not a substitute for real-repository acceptance.

Inspect existing storage test fixtures first. Add meaningful tests for the new
composition semantics and run affected inspection/detail/readiness regressions.
Run broader suites only for shared changes or required gates. Record exactly
what ran, skipped or failed; native-parser/RHEL/browser results must not be implied.

## Suggested bounded checkpoints

1. Implement the versioned packet/traversal core with explicit limits and focused
   tests for identity, relation semantics and termination. If the full CLI/source
   slice does not fit the timebox, leave a coherent tested core and precise resume.
2. Add bounded evidence/source assembly and CLI; test total output/work limits,
   source failures and mutation detection.
3. Demonstrate end-to-end use, check affected regressions, and document actual
   commands/results. Only then mark this increment complete and select the next
   GRAPH_ARCHITECTURE.md migration item with the user.

At each checkpoint: inspect git diff, commit/push source without deployment,
update RESUME.md with implemented versus pending behavior, and stop. Preserve
owner-private hosting and all local Host/Origin/token boundaries. Read current
browser capability guidance only if a later task actually needs browser QA.

## Checkpoint 1 actual service (2026-10-11)

`atlas_engine.storage.trace_packet.TracePacketInspector(database).packet(...)`
requires keyword arguments `snapshot`, `target`, `entity`. Optional `direction`
is out/in/both; `kinds` defaults to all six producer-backed kinds listed above.
Unknown keywords/kinds, booleans used as numeric limits, and oversized limits are
rejected. The public CLI is intentionally pending checkpoint 2.

Version 1 core uses a single read transaction plus the existing DB/WAL version
observation. It never calls independently bounded pages. FIFO expansion orders
out before in, then each adjacency by stored kind and relation ID. Candidate
endpoints are retained but their links are terminal; an independent resolved
path can still schedule the same endpoint. Unresolved targets retain spelling
and evidence references. Relationships retain compilation ID and evidence kind,
producer/path/line, including the shared applicability warning. Full evidence
bodies, occurrences and source excerpts are not assembled yet; their statuses
explicitly say so. No source files are opened and no variants are merged.

Depth/node/edge/byte defaults and maxima are unchanged from the approved policy.
Fixed aggregate work defaults equal hard maxima: 500 SQL statements, 1,000
adjacency rows observed (including duplicates, filtered rows and lookahead),
200 accepted-to-inspection rows per directional adjacency plus one lookahead,
2,000,000 SQLite VM steps, and a 0.5-second request deadline checked by the SQL
progress handler every 1,000 steps. Node/scope SQL rows are additionally bounded
by statement/node limits; `usage.rows` specifically counts adjacency rows.
The deadline includes intervening Python processing, but is only enforced when
SQLite invokes its progress handler; it is not a hard total-processing or I/O
deadline. Aggregate work/time exhaustion rejects the packet; row caps return
explicit non-exhaustive omissions. Source file/read/hash limits are zero for
this core. Checkpoint 2 must set finite aggregate source and detail limits before
adding those operations, retaining existing per-call caps.

Compact canonical JSON UTF-8 byte accounting includes its own usage counter.
The core reserves 2 KiB for final counters and finite omission reasons; selection
can therefore leave unused delivery space. Seed/envelope/reserve failure raises
`PacketBudgetError` with structured `.response`; the future CLI must expose that
error separately because a tiny requested budget cannot fit even an error.
Edges and newly required endpoints are accepted or omitted together. Inclusion
parents refer to earlier retained material. No traversal cursor is advertised.

Validation: five new core tests plus 15 existing inspection/detail/readiness
regressions passed. Tests cover cycles, fanout, terminal candidates subsequently
reached by a resolved path, target/snapshot isolation, inferred evidence labels,
Unicode and exact delivery size, node/edge/depth/row/statement/time bounds,
unknown-kind filtering, read-only bytes, detected version changes and ready-state
ineligibility. Mutation rejection uses the existing detector with injected
before/after versions; concurrent writer stress remains pending. No native parser,
real F Prime trace demonstration, browser or RHEL validation was performed here.

## Checkpoint 2 actual detail assembly and CLI (2026-10-11)

The same service now accepts optional `roots={'repo': ..., 'build': ...}`; unknown
root labels are rejected. Entry point:

```sh
python -m atlas_engine.storage.trace_packet --database /absolute/store.sqlite \
  --snapshot EXACT_SNAPSHOT_ID --target EXACT_TARGET_ID --entity EXACT_ENTITY_ID \
  --repo-root /absolute/repository --build-root /absolute/build
```

Replace uppercase IDs and paths with exact lookup results/operator-selected roots.
Optional flags: `--direction out|in|both`, repeated `--kind KIND`, `--max-depth`,
`--max-nodes`, `--max-edges`, `--max-bytes`. Output is compact canonical JSON;
`usage.bytes` measures JSON UTF-8 bytes excluding the CLI's framing newline.
Exit 0 returns a packet; exit 2 returns a structured inspection/budget error
(or argparse usage error for invalid syntax). Error envelopes are outside tiny
requested packet budgets. No stdin request protocol or HTTP route is added.

Detail assembly is part of the original transaction, using shared DetailInspector
helpers with the trace's aggregate SQL counter/progress handler. No nested
transaction, independent page loop, freshness promotion or file mutation occurs.
Fixed detail defaults/maxima, declared in trace_details.py before implementation:
50 evidence calls and retained items; 256 KiB of charged selected serialized
evidence (including items later omitted for packet size); 50 retained occurrences;
20 source helper calls; eight file-open attempts; 32 MiB each actual source bytes
read and bytes hashed. Repeated file work is charged again. No verified-file cache.
Evidence calls each retain the existing 64 KiB body/result cap; the call limit
also bounds body loading/serialization when selected evidence bytes are exhausted.
Occurrence queries return at most two rows per considered entity, so observed
occurrence rows are bounded by twice max_nodes; usage reports them separately.
Existing 16 MiB source file, 200-line and 64 KiB excerpt caps remain in force.
The SQL deadline is still progress-handler-enforced, not a hard filesystem deadline.

One occurrence per entity is chosen deterministically: definition role first,
then compilation ID and occurrence ID, filtered to selected target/shared scope.
The exact occurrence ID, compilation, artifact path and original span remain in
the packet. Other variants are explicitly not promised; bounded lookahead labels
observed alternatives. Source is read at that occurrence's path/span, never an
unrelated evidence span. At most 200 lines of a longer span are selected with
`span_truncated=true`; available excerpts retain expected artifact hash.

Source statuses distinguish available, stale, missing, external_unavailable,
root_unavailable, over_limit, budget_omitted and other unavailable reasons. Whole
source text is removed when delivery bytes do not fit; bounded identity/span
metadata remains. Evidence references each label available/over_limit or
budget_omitted detail status, so omitted evidence bodies are not dangling claims.
Counters/omissions and all retained details are included in final byte accounting.
Small shared-helper refactor preserves existing detail/API behavior; malformed
source paths without a slash now return unavailable instead of a split error.

Validation: 37 tests passed: 16 trace tests (five core tests also rerun with source
roots), five details, four inspection, six readiness, four HTTP and two local-view
asset/API checks. New checks include exact target occurrence source, aggregate
source/evidence limits, full-body byte omission/non-ASCII delivery, source failure
statuses, explicitly truncated spans, CLI subprocess success/budget error and an
actual concurrent WAL writer during source assembly causing packet rejection.
An initial test import caught an indentation edit error; fixed before passing runs.
No browser, native parser, RHEL or real F Prime end-to-end validation was performed.

Checkpoint 3 remains: reproduce lookup -> trace -> evidence/source using an
appropriate synthetic trace and the real F Prime database if available. Existing
offline demo relations include illustrative_call/candidate_implementation, which
are deliberately outside the approved trace allowlist; do not silently relabel
these observations or expand unknown kinds merely to obtain a longer demo trace.
Check additional acceptance edge cases and record exact commands/results before
marking the complete increment done. No ingestion/publication work starts here.

## Checkpoint 3 acceptance and reproduction (2026-10-12)

The first bounded SQLite **inspection** increment is complete. This conclusion
applies to the service, CLI and listed bounded acceptance cases, not full-repository
coverage, readiness, requirement satisfaction or platform/scale qualification.
Recorded result: [sqlite-trace-packet-acceptance.json](../experiments/fprime/sqlite-trace-packet-acceptance.json).

Run from the repository root (stdlib-only; no native parser needed):

```sh
python scripts/check-trace-packet.py
python scripts/check-trace-packet.py --fprime-database .atlas/fprime-rebuilt.sqlite \
  --fprime-root /path/to/workspace/fprime
```

The first command creates a NEW temporary controlled fixture and removes it after
CLI lookup -> trace -> independent evidence/source checks. All links are authored
synthetic claims with explicit not-compiled/not-executed/not-reviewed evidence;
compilation remains pending, snapshot staging. It does not relabel or replace the
existing offline demo. Its supported association trace ends in a terminal candidate
alias and separately retains an unresolved callback. Successive packet JSON is
identical; DB bytes and selected source hashes remain unchanged. Synthetic packet:
4 entities, 4 relationships, 9,597 JSON UTF-8 bytes, 26 SQL statements, 896 bytes
read/hashed (same file reread four times and charged each time).

The second command checks the existing pinned staging F Prime UT snapshot
bd6c4ddd353f4437a03812c834743c5c, exact target and lookup `Test.NominalTlm`.
It uses explicit invokes_annotated_helper/has_requirement_annotation/candidate_alias
filters. Returned trace: Test.NominalTlm -> Svc::HealthTester::nominalTlm ->
ISF-HTH-001 -> candidate HTH-001. Four entities, three relationships, 19,018 bytes,
32 SQL statements and 62,731 source bytes read/hashed; all four selected excerpts
match hashes. Shared evidence retains its applicability warning. Additional helper
relationships are explicitly filtered, not claimed absent; no execution or
approved satisfaction link is inferred. Candidate traversal is terminal.

The report retains exact CLI argument arrays, snapshot/configuration identity,
evidence kinds, scope warnings, omissions, source hashes, usage and read-only/stable
repeat checks. Synthetic paths are ephemeral; rerun the script for reproduction.
The real DB/source are disposable recovered inputs, not part of this report or
an updated offline archive. This command targets the specific recorded fixture;
a different snapshot requires an explicitly updated acceptance selection.

| Gate | Bounded validation evidence |
| --- | --- |
| Configuration/target isolation | Separate same-ID Linux/RTOS source and selected target tests; shared applicability warnings preserved |
| Evidence distinctions | Real inferred helper/annotation and candidate-alias trace; synthetic authored/unresolved trace; no promotion |
| Termination/aggregate bounds | Cycles, 150 distinct fanout endpoints, row/statement/time/file/read/hash caps and deterministic omissions |
| Stable selection | Full repeated CLI packet equality for synthetic and F Prime; deterministic fanout/alternative occurrence tests |
| Source/mutation safety | Stale/missing/oversized/non-UTF8/root/symlink checks and actual WAL-writer rejection; old APIs pass |
| Delivery bounds/references | Unicode exact compact JSON accounting; whole-body omissions; structured undersized-budget error; evidence statuses |
| Read-only/flags | DB byte equality and selected source hash equality; source bytes unchanged in tests; ready-labeled snapshots stay ineligible |
| Reproduction | Both CLI workflows above passed and reports committed; synthetic-only workflow has a subprocess regression |

41 tests passed: 20 trace tests (five core cases rerun with source roots), five
details, four inspection, six readiness, four HTTP and two local-view asset/API
checks. No production runtime changes were needed in this checkpoint. No fresh
native parse/build/test execution, browser, RHEL or disconnected installation was
performed. Existing toolchain/generator/application-scope and publication blockers
remain. Next migration item is the scoped ingestion runner; finish this checkpoint
and wait for the user's continuation rather than implementing it in this chunk.
