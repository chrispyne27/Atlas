> Export note — 2026-11-06: this package was prepared from commit
> `70861deabe1ba009000250d3d7d117479ee3c5fd`. The first checkpoint below is the
> current development handoff; later entries are historical. For this new Git
> repository, use your clone location and chosen remote instead of the historical
> managed-source recovery instructions. See [Git import guide](../GIT_IMPORT.md).

# Resume checkpoint — bounded SQLite inspection increment complete (2026-10-12)

Continued clean b8f3c0df7c15101f4d800869a810391017521174. No newer local work
was replaced. Approved architecture is unchanged; no rereview needed.

## Completed checkpoint 3

Added scripts/check-trace-packet.py: repeatable subprocess CLI lookup -> trace ->
independent evidence/source acceptance with a NEW temporary authored synthetic
fixture and optional explicit existing F Prime DB/source. Existing offline demo
unchanged. Committed exact commands/results in
experiments/fprime/sqlite-trace-packet-acceptance.json.

Both workflows passed: synthetic 4 entities / 4 relations / 9,597 JSON bytes;
F Prime Test.NominalTlm -> nominalTlm helper -> ISF-HTH-001 -> candidate HTH-001,
4 entities / 3 relations / 19,018 bytes. All selected source hashes matched;
DB bytes/selected source hashes unchanged; complete repeated packets equal.
The real slice explicitly filters other relationship kinds and preserves shared
applicability warnings. Candidate alias is terminal/unapproved. No requirement
satisfaction or execution claim is created. Flags remain inspection-only and
context-ineligible. No production runtime changes were needed this checkpoint.

The first bounded SQLite inspection trace-packet increment is COMPLETE for its
listed service/CLI acceptance gates. See SQLITE_TRACE_PACKET.md checkpoint 3
for reproduction commands, evidence mapping and limits. This is not full-repo,
current-context, publication, scale or target-platform acceptance.

## Tests and limits

41 tests passed on workspace Python: 20 trace tests including five core cases
repeated with source roots, five details, four inspection, six readiness, four
HTTP and two local-view asset/API tests. Used unittest discover -s tests/engine
with patterns test_storage_trace*.py, test_storage_details.py,
test_storage_inspect.py, test_storage_readiness.py, test_storage_http.py,
test_storage_local_view.py (acceptance-script regression run separately).
Added Linux/RTOS same-ID source isolation, shared/alternative occurrence selection,
150 distinct fanout endpoints, root escape/non-UTF8/root-unavailable handling,
and synthetic CLI regression. Two full CLI workflows additionally passed.
No fresh native parse/build/test, browser, RHEL or disconnected installer run.
Snapshots stay staging; missing provenance/scope/publication infrastructure and
old platform blockers remain. No general scale or savings claim.

## Next bounded task after user continuation

Proceed to migration item 2 in GRAPH_ARCHITECTURE.md: reproducible scoped ingestion
runner. Inspect current storage manifest/compiler code and tests; choose a bounded
first checkpoint for one explicit target/configuration, retaining unsupported
options, coverage/failure records and recovery. Measure indexing time/resource/hash
work rather than treating many independent parse calls as an orchestration policy.
Keep inspection/context eligibility separate. Toolchain/generator/application-scope,
publication/refresh and current-context migration remain later items.

## Recovery and scope

Checkout /path/to/workspace/atlas-site; managed Git authoritative.
Commit/push checkpoint and stop. Keep 5–6 minute chunks and hosting owner-private;
no deployment, access, HTTP route, loopback checks, schema or offline archive changes.
Real DB/source are disposable, pinned historical staging inputs. Reproduction script
requires their exact recorded snapshot, or an explicitly revised acceptance selection.

---
Historical checkpoints preserved below; latest instructions take precedence.

# Resume checkpoint — SQLite inspection packet details and CLI (2026-10-11)

Continued clean HEAD 202014b9435775df9b11d045740353ebe432d99a; preserved prior
work and approved architecture. Checkpoint 2 is implemented, full increment's
checkpoint 3 demonstration/acceptance remains pending. No architecture rereview.

## Completed

Trace packets now assemble bounded evidence details and one exact selected-target
or shared occurrence per retained entity, with hash/stat/root-checked source.
All detail reads remain in the original transaction and aggregate SQL budget.
Explicit source failure/budget statuses, original occurrence/compilation/span/hash,
truncated long spans, omitted alternative variants and evidence-reference detail
statuses preserve configuration/evidence distinctions. Source work is charged
across the request, including repeated reads. Flags remain inspection-only and
context-ineligible even for ready-labeled snapshots.

CLI: `python -m atlas_engine.storage.trace_packet --database PATH --snapshot ID
--target ID --entity ID [--repo-root PATH] [--build-root PATH]`. Actual option,
resource and response policy is documented in SQLITE_TRACE_PACKET.md checkpoint 2.
Small DetailInspector helper refactor supports this composition while preserving
public detail/HTTP semantics. No schema, HTTP route, viewer or dependency change.

## Validation

37 tests passed on workspace Python: 16 trace tests (including five core tests
repeated with roots), five details, four inspection, six readiness, four HTTP and
two local-view asset/API tests. Commands use unittest discover under tests/engine
with patterns test_storage_trace*.py, test_storage_details.py,
test_storage_inspect.py, test_storage_readiness.py, test_storage_http.py and
test_storage_local_view.py. New checks cover actual concurrent WAL mutation,
source failures/aggregate limits, precise source occurrence, Unicode delivery,
whole source/evidence byte omission, bounded spans and subprocess CLI errors.
An initial import failed on an indentation edit error; corrected before final
passing runs. No native parsing, browser, RHEL, disconnected install or real
F Prime trace acceptance run. No whole-repository freshness/scale claim.

## Next bounded checkpoint

Complete checkpoint 3: reproducible synthetic lookup -> trace -> evidence/source,
and real F Prime trace if its disposable database/source remain available. Read
SQLITE_TRACE_PACKET.md checkpoint 2 caveat: existing offline demo has unsupported
illustrative relation kinds; filtering is correct and must remain explicit.
Use genuine approved stored semantics with honest synthetic provenance for a
compatible trace rather than invent compiler/execution evidence. Check remaining
acceptance cases (shared/alternative occurrences, broader budget/fanout effects,
read-only input/source bytes) and record precise commands/results. Then assess
whether the first increment's gates are met before starting the ingestion runner.

## Recovery and scope

Checkout: /path/to/workspace/atlas-site; managed source Git remains
authoritative. Commit/push this checkpoint, no deployment/access changes. Hosting
stays private, loopback Host/Origin/token checks and offline archive unchanged.
Keep five-to-six-minute chunks, finish a coherent checkpoint, push and stop.
Existing target-host/provenance/scope/publication/readiness gaps remain open.

---
Historical checkpoints below preserved; latest instructions take precedence.

# Resume checkpoint — SQLite inspection trace core (2026-10-11)

Continued approved handoff cc69980ae528aa1235adf593ecc57945bd53c282.
Initial checkout was clean at that exact HEAD (one commit ahead of recorded
origin/main); no newer local work was present or replaced. Architecture remains
approved; do not repeat its review.

## Completed checkpoint 1

Added `atlas_engine/storage/trace_packet.py`: versioned read-only traversal core
for one exact seed/snapshot/target. Reuses Inspector visibility/change detection;
one transaction and aggregate SQL/row/work limits. Deterministic FIFO expansion,
configuration-bound edges, separate evidence/compilation IDs, terminal candidate
links, unresolved spelling, inclusion reasons, explicit bounded omissions and
exact compact UTF-8 delivery accounting. Always `inspection_only=true` and
`context_eligible=false`, including ready-labeled snapshots. No schema or shared
inspection/detail/readiness implementation changes.

Actual Python service and resource policy: SQLITE_TRACE_PACKET.md checkpoint 1.
Full evidence bodies, occurrences, source excerpts and CLI are explicitly pending;
core status labels do not imply these were assembled. No source I/O occurs.

## Validation

20 tests passed on current workspace Python: five new trace-core tests, four
storage inspection, five source/evidence detail, six readiness regressions.
Commands: `python -m unittest discover -s tests/engine -p '<filename>' -v`, with
`test_storage_trace_packet.py`, `test_storage_inspect.py`,
`test_storage_details.py`, `test_storage_readiness.py`.
One initial combined fanout/path test failed because the test's own fanout/byte
limits omitted the later path; separated that workload before checking the
resolved-path behavior, then all five core tests passed. Existing regressions
were unchanged and passed. No native parser, real F Prime demonstration, browser,
RHEL or disconnected installer run. No scale/whole-graph freshness claim.

## Next bounded checkpoint

Read current SQLITE_TRACE_PACKET.md and core/tests. Add bounded evidence/source
assembly and local CLI (checkpoint 2). Establish finite aggregate detail/source
file/read/hash limits first; reuse DetailInspector hash/stat/root semantics within
the coherent view rather than looping independently bounded detail calls.
Preserve exact compilation occurrences and distinct source failure statuses.
Then test assembled output budgets, actual mutation rejection, source failure
handling and reproducible CLI lookup -> trace -> evidence/source (checkpoint 3).
Do not advance the ingestion runner or current-context publication yet.

## Recovery and scope

Checkout remains /path/to/workspace/atlas-site, managed origin/main.
Git is authoritative. Temporary credentials/archives are not recovery records.
Source checkpoint commit/push is requested; no deployment or access change.
Hosted viewer, local Host/Origin/token protections and offline archive remain
unchanged. Keep five-to-six-minute chunks, commit/push, and stop. Existing RHEL,
toolchain/generator/application-scope and freshness/publication gaps remain.

---
Historical checkpoints below are preserved; next-action instructions superseded.

# Resume checkpoint — architecture accepted; implementation handoff (2026-10-09)

The project maintainer accepted the architecture review and requested durable records for a new
implementation thread. This handoff changes documentation only. No runtime,
schema, indexing, package, deployment or privacy changes were made.

## Read first and precedence

1. This current checkpoint (older entries below are historical).
2. [GRAPH_ARCHITECTURE.md](GRAPH_ARCHITECTURE.md): accepted target, reconciliation,
   migration order and deferred work.
3. [ADR 0004](decisions/0004-evidence-aware-retrieval-migration.md): accepted
   evidence/query decisions and relationship to ADRs 0001–0003.
4. [SQLITE_TRACE_PACKET.md](SQLITE_TRACE_PACKET.md): first implementation scope,
   response semantics, boundaries and acceptance gates.
5. [ARCHITECTURE_SNAPSHOT.md](ARCHITECTURE_SNAPSHOT.md): actual pre-review runtime,
   rationale, code map, prior tests and known gaps; then relevant code/tests.

The accepted direction supersedes the old pause-for-review and next-runner order.
It does not convert pending capabilities into implemented ones or remove current
freshness/readiness gates. The original implementation brief is reconciled by
these documents; do not restart the design from that brief or conversation memory.

## First task for the new implementation thread

Implement the bounded SQLite **inspection trace packet**, starting with one exact
seed/snapshot/target and the first coherent checkpoint in SQLITE_TRACE_PACKET.md.
Use High reasoning. Reuse the existing inspection/source semantics and keep
`inspection_only=true`, `context_eligible=false`. No schema change is expected.
Do not start the full ingestion runner, embeddings, publication or hosted viewer
integration as the first task. No new authorization is needed for routine design
choices within the user-requested implementation increment.

Work in roughly 5–6 minute chunks; finish a coherent checkpoint, update this file,
commit/push and stop for continuation. The architecture is approved; development
starts when The project maintainer supplies the continuation request in the new thread. This
architecture thread itself has not implemented the trace packet.

## Baseline and recovery

Reviewed source and clean pre-edit HEAD: dafa03b. The architecture handoff commit
is the commit introducing ADR 0004, GRAPH_ARCHITECTURE.md and SQLITE_TRACE_PACKET.md;
use the exact hash supplied with the handoff prompt (a commit cannot record its
own hash in its contents). Runtime baseline remains d5e44ad; package source is
2c8ee75. Verify current HEAD/status before editing; preserve any newer work.

Existing checkout: /path/to/workspace/atlas-site, branch main,
configured managed origin. F Prime: /path/to/workspace/fprime,
revision 7d8f579f159d2f7c2d4984d92828575e37f87fa6. If scratch is missing, recover
from the existing managed source repository; project identity is recorded in
.openai/hosting.json. Do not create a replacement Site. Local databases/venvs
are disposable, not the authoritative recovery record.

## Validation and blockers

Documentation handoff validation: relative links and Git whitespace/diff checked;
no runtime tests rerun because no runtime behavior changed. See the final Git
checkpoint for exact files. Previous recorded result: 91 engine tests + four
schema checks, installer/native smoke and synthetic launcher/API checks passed
on Ubuntu for extracted atlas-offline-2c8ee75.zip. The archive is unchanged.

Windows manual viewer checks passed for package 01a52fc. RHEL 9 exact minor,
approved Python/RPM set and Firefox version remain unknown; RHEL/Firefox and
network-disabled installation remain unvalidated. Prior network namespace and
browser approval restrictions must not be bypassed. None blocks CLI trace work.
SQLite publication/refresh/agent context remain unimplemented; all existing real
snapshots are staging. Toolchain, generator and application-scope evidence gaps
remain open. Keep recorded pilot outcomes and failed test-process evidence intact.

## Privacy and scope

Keep hosting owner-private. No deployment, tunnel, access change or weakening of
loopback Host/Origin/token checks is part of this increment. Use synthetic or
explicitly authorized repositories. Save source in Git; do not duplicate this
repository into Library or rebuild the offline archive for documentation changes.

---
Historical checkpoints follow; their next-action instructions are superseded.

# Resume checkpoint — PAUSED FOR ARCHITECTURE REVIEW (2026-10-01)

User requested a current project snapshot before a new architecture-review thread,
then a new implementation thread that consumes its decisions. Start with
**docs/ARCHITECTURE_SNAPSHOT.md**, including its thread-specific rationale and
lessons section. Runtime baseline d5e44ad. This checkpoint is
documentation only; no new indexing, deployment, or privacy changes.

Checkout was clean at handoff start; no implementation wrap-up required.
Last full validation: extracted 2c8ee75 archive, 91 engine tests + four schema
checks, fresh installer/native smoke and live demo/API passed on Ubuntu.
RHEL/Firefox and network-disabled installation still pending/blocked as documented.
Latest download remains atlas-offline-2c8ee75.zip; no archive rebuild needed.

Next action: architecture thread reads snapshot/code/current ADRs, compares the
user's incoming architecture guidance, and records explicit decisions, superseded
ADRs, migration implications, acceptance gates and ordered backlog in Git.
New implementation thread reads those outputs and this updated resume at the
handoff commit before coding. Do NOT automatically start the proposed scoped
indexing runner. Preserve private hosting, provenance distinctions and 5–6 minute
checkpointed chunks. Historical next-step instructions below are superseded.

---
Earlier checkpoints follow.

# Resume checkpoint — updated demo archive validated (2026-10-01 Denver)

Saved atlas-offline-2c8ee75.zip (24,823,377 bytes / 70 files) from source 2c8ee75.
It includes synthetic demo generator and README steps. The tested archive is
unchanged by this later documentation checkpoint. Full SHA-256/results are in
experiments/offline/demo-transfer-workspace.json and docs/OFFLINE_PILOT.md.

Extracted archive: 69 manifested hashes passed; fresh offline-wheel installer /
native smoke passed; 91 engine tests and four schema checks passed. Generated
demo and real launcher/API four-step trace, evidence/source/auth/read-only checks
passed. Server stopped, no tokens saved. Ubuntu only; RHEL/Firefox not run.
Network-disabled installation still blocked by namespace restriction, not passed.

Next user acceptance: approved RHEL machine preflight and README synthetic-demo
Firefox checklist. Exact RHEL minor, approved Python and Firefox versions pending.
Further bounded work: scope real-repository ingestion runner/build compatibility
without guessing target compiler flags. Keep 5–6 minute chunks, checkpoint/push
and stop. Hosted site unchanged. This is a pilot candidate, not qualification.

---
Earlier checkpoints follow.

# Resume checkpoint — reproducible synthetic demo (2026-10-01 Denver)

Added atlas_engine/storage/demo.py: stdlib-only NEW-directory generator for a
known Demo.Nominal -> helper -> method -> candidate requirement -> candidate
alias trace, plus unresolved callback. Source, SQLite DB, and DEMO.json produced.
All evidence explicitly synthetic/authored; compilation pending, snapshot staging,
no execution/review records. Logical DB/source reproducibility, non-overwrite,
query pagination and stale source suppression tested.

20 offline-workflow tests and four schema checks passed; no native suite or
RHEL/Firefox run. Updated package README has exact creation/launch/search steps.
Old a7cfba9 download is unchanged and DOES NOT contain the new generator.
Existing assembler engine allowlist includes it automatically in future builds.

Next chunk: rebuild/validate/save updated transfer archive with demo. Keep
5–6 minute chunks, commit/push/stop. Network-disabled installation remains
blocked by host namespace permissions; do not bypass. Hosting unchanged.

---
Earlier checkpoints follow.

# Resume checkpoint — live offline launcher/API checks (2026-09-30 Denver)

Added tests/engine/test_offline_launcher.py. Real shell subprocess serves a
synthetic SQLite trace using copied package runtime files in a path with spaces,
from outside package cwd. Tests lookup/paging/evidence/source, stale suppression,
auth/Host/Origin/write boundaries, unchanged DB bytes and restart token rotation.
Tokens remain memory-only and processes were stopped. No runtime changes needed.

All 16 offline-workflow tests and four schema checks passed. Evidence:
experiments/offline/launcher-workspace.json. Full native suite not rerun (temporary
parser environments gone). No RHEL/Firefox run; archive a7cfba9 unchanged.
Network-disabled install BLOCKED: unshare user/net namespace prerequisite denied
uid_map write (Operation not permitted); no isolated installation attempted.
Use an authorized disconnected validation host for that gate; do not claim passed.

Next bounded implementation: repeatable small sample-database creation and launch
workflow so the candidate has a known trace without requiring F Prime or private
code. RHEL preflight results / approved Python package selection still pending.
Keep 5–6 minute chunks, checkpoint/push and stop. Hosting unchanged.

---
Earlier checkpoints follow.

# Resume checkpoint — offline transfer archive (2026-09-30)

Built atlas-offline-a7cfba9.zip from source commit a7cfba9: 67 files / 24,800,682
bytes. Engine/viewer/tests/Aurora fixture, pinned wheel/license, SHA256SUMS,
SOURCE.json, README-FIRST.txt and shell launcher. No F Prime graph or OS Python.
Archive and source are distinct: subsequent documentation checkpoint records QA.
Archive SHA-256 and results: experiments/offline/transfer-workspace.json.

Extracted archive passed all hashes, fresh installer/native smoke, launcher help,
85 engine tests and four schema checks on Ubuntu. No RHEL/Firefox execution,
network-disabled test or live launcher browser session. Installer remains pilot
candidate. Download saved as atlas-offline-a7cfba9.zip. Source remains git-backed.

Next bounded chunk: network-disabled installation validation, and launcher/API
smoke with a reproducible small SQLite fixture. User's actual RHEL minor, approved
Python packages and Firefox version still pending. Keep 5–6 minute chunks and
commit/push/stop. Hosting unchanged. See docs/OFFLINE_PILOT.md.

---
Earlier checkpoints follow.

# Resume checkpoint — local-wheel offline installer (2026-09-30)

Added scripts/install-offline.py. Verifies the pinned x86_64 wheel before creating
a NEW venv with the explicitly chosen interpreter; no-index/no-cache/no-deps,
required-hash binary install, pip config disabled. Never replaces existing paths.
Runs installed RECORD verification then native C++98 smoke; retains failed new
venvs for diagnosis. Reports installation success separately from qualification.

Downloaded libclang 18.1.1 wheel: 24,515,943 bytes, exact lock SHA-256 matched.
Temporary input: /tmp/atlas-offline-wheelhouse (not durable; reacquire per docs).
Final environment: /tmp/atlas-offline-install-final. Native suite ran in equivalent
/tmp/atlas-offline-install-check. All 85 engine tests and four schema checks passed.
Evidence: experiments/offline/install-workspace.json. Ubuntu/Python 3.12.14 only;
network isolation and RHEL/Firefox checks remain pending. No deployment change.

Next bounded chunk: reproducible transfer archive/assembler with source, wheel,
licenses/checksums and launcher. Exact RHEL/Python RPM pins and target tests still
pending. Installer is implemented; complete installable transfer release is not.
Keep five-to-six-minute chunks, commit/push and stop. docs/OFFLINE_PILOT.md has
commands and limits. Previous native runtime was restored via this fresh install.

---
Earlier checkpoints follow.

# Resume checkpoint — offline target preflight (2026-09-30)

Completed scripts/offline-preflight.py (stdlib-only, read-only JSON output).
Separate viewer/indexer modes; observes OS/architecture, selected Python, SQLite
in-memory capabilities, local assets, pip/venv and Firefox PATH availability.
Indexer checks distribution metadata against the parser pin; never loads native
code. No installer/network/subprocess/browser use. Exit 0 means only
requires_validation, never qualified; exit 1 observed blockers, exit 2 CLI misuse.

Eight targeted tests and four schema checks passed. Real Ubuntu invocations
correctly blocked for OS mismatch; indexer additionally lacked libclang.
Evidence: experiments/offline/preflight-workspace.json. Native suite and RHEL /
Firefox checks not run; previous native interpreter still unavailable.

Next bounded chunk: acquire and hash-verify the pinned wheel, then implement
offline assembler/installer. Python/RHEL minor/Firefox exact versions pending.
No installable release yet. See docs/OFFLINE_PILOT.md for contract and gates.
Keep five-to-six-minute chunks, checkpoint/push and stop. Hosting unchanged.

---
Earlier checkpoints follow.

# Resume checkpoint — offline pilot inventory (2026-09-30)

User target: RHEL 9 / x86_64 / Firefox. Work in five-to-six-minute chunks,
commit/push and stop. Current priority is an offline one-application Linux pilot.

Added docs/OFFLINE_PILOT.md: runtime inventory, package contents, installation
contract and acceptance gates. Added requirements-indexer-linux-x86_64.lock with
the published SHA-256 for the existing libclang 18.1.1 x86_64 manylinux wheel.
Wheel bytes are not yet acquired/verified for an offline release. Python 3.12 is
a candidate (RHEL 9.4+ availability), not a finalized prerequisite; minor release
and installed Python/Firefox versions are pending. No RHEL/Firefox run performed.

Next chunk: read-only target preflight and package assembler/installer interface;
obtain/verify wheel artifacts. Do not claim an offline installer already exists.
Historical toolchain/generator provenance and publication work remains pending.
This workspace is Ubuntu; cached .venv-validation interpreter is missing again.
No native tests rerun for this documentation/lock change. Hosting unchanged.

---
Earlier checkpoints follow.

# Resume checkpoint — manual local viewer validation recorded

## Latest user result (2026-09-30)
The project maintainer tested atlas-local-test-01a52fc.zip on Windows 10 / Google Chrome (version
not supplied) / Python 3.14.5. All nine checklist sections passed, no errors:
connect/scope, search, follow/back, directions, evidence/source, paging, narrow
layout, keyboard/focus, and disconnect/reload session clearing.

The supplied local viewer checklist is COMPLETE for this package/environment.
Evidence: experiments/fprime/local-view-manual-validation.json; docs/LOCAL_API.md.
User-reported manual testing, not automated/assistant browser execution. Viewer
and HTTP/detail/inspection/store files are unchanged through c9e9d89. Do not claim
formal accessibility compliance, native Python 3.14 compatibility, large-repository
performance or requirement satisfaction from these checks. No code changes were
needed. Hosted site is unchanged; cloud browser skill rejection still applies.

## Next work
Continue from backend chunk 15: snapshot-bound parser/compiler binary identity
and configuration evidence, then generator provenance and scope/publication gates.
Manual viewer testing is no longer a blocker to planning viewer integration; keep
local live data and any hosted bounded sample clearly distinguished. Continue
five-to-six-minute chunks, commit/push, and keep hosting owner-private.

## Current code baseline
c9e9d89 before this documentation-only validation record. Prior backend result:
71 engine tests and four schema checks passed. No test rerun needed for this record.
Locations and detailed history follow.

---
Historical checkpoints below may say manual UI feedback is pending; superseded
by the completed manual result above.

# Resume checkpoint — disk-store chunk 15

## Constraints
Keep each chunk about five to six minutes, checkpoint/push, stop. Owner-private
hosting unchanged. User manual viewer feedback remains pending.

## Completed
- Explicit external-root mappings for freshness/readiness CLI only; defaults still
  do not read external paths. Mappings compute a relative suffix from a recorded
  POSIX prefix to an operator-selected local directory, then enforce containment.
- Recorded absolute paths are never opened directly. Existing hash/read budgets,
  regular-file checks and metadata rechecks apply. No HTTP/source route change.
- Results record roots and snapshot-bound status counts; matching SDK header bytes
  do not establish toolchain equivalence or grant context eligibility.
- Real F Prime report: all 302 external headers match in explicitly selected system
  include roots; all 473 recorded artifact hashes match. Still incomplete because
  old engineering directory membership is not recorded; toolchain identity blocked.
- Six new tests; full 71 engine tests (65 storage) and four schema checks passed.
- See docs/EXTERNAL_INPUTS.md and experiments/fprime/storage-external-inputs.json.
- Active SQLite graph and viewer package remain unchanged. No deployment/browser QA.

## Next bounded backend work
Bind parser/compiler binary identity and relevant configuration to a verified,
versioned snapshot toolchain manifest. This chunk implemented only external-input
mapping/hash checks, not that manifest. Then generator input/output binding and
scope/publication gates. Do not remove readiness blockers based on header hashes.
Address manual local viewer test feedback when it arrives.

## Locations
Atlas /path/to/workspace/atlas-site
F Prime /path/to/workspace/fprime
Active .atlas/fprime-rebuilt.sqlite, all staging. Runtime .venv-validation.
Pinned upstream 7d8f579f159d2f7c2d4984d92828575e37f87fa6.
User package 01a52fc remains valid; cloud browser-control rejection must not be bypassed.

---
Previous checkpoints follow.

# Resume checkpoint — disk-store chunk 14

## Constraints
Work about five to six minutes per chunk, checkpoint/push and stop. Keep hosted
site owner-private and unchanged. Manual local viewer feedback is still pending.

## Completed this chunk
- New read-only CLI atlas_engine/storage/readiness.py assesses one exact target
  and explicit engineering components using a NEW recorded-input audit.
- Explains parse, freshness, engineering discovery, toolchain, generator, scope
  completeness and publication blockers. Never grants context eligibility.
- Target parse coverage stays distinct from conservative whole-snapshot freshness.
  Candidate/unresolved counts remain labeled; requirement/test/review verification
  is separately not_assessed. No runtime route or snapshot state was changed.
- Real Health UT assessment: two parsed / three pending target compilations;
  all seven checks blocked. Report experiments/fprime/storage-readiness.json.
- Six new tests; all 65 engine tests (59 storage) and four schema checks passed
  in .venv-validation. Browser interaction and new binary executions not performed.
- Contract and next policy: docs/READINESS.md.

## Next bounded backend work
Implement snapshot-bound, explicitly selected toolchain/external-input evidence,
with before/after hashes and approved root mapping. Do not follow arbitrary DB
absolute paths or equate the environment package check with toolchain provenance.
Then generator input/output binding and scoped completeness/publication contracts.
Alternatively fix any issues from user's manual viewer test when available.

## Locations
Atlas /path/to/workspace/atlas-site
F Prime /path/to/workspace/fprime
Active DB .atlas/fprime-rebuilt.sqlite (staging); membership-only probe is separate.
Pinned upstream revision 7d8f579f159d2f7c2d4984d92828575e37f87fa6.
User package 01a52fc remains valid for UI checks; cloud browser rejection remains.

---
Previous checkpoints follow.

# Resume checkpoint — disk-store chunk 13

## Constraints
Continue in bounded five-to-six-minute chunks; checkpoint/push and stop.
Hosting remains owner-private and unchanged. User will manually test the viewer.

## Completed
- Restored pinned libclang 18.1.1 in .venv-validation (old .venv Python executable
  missing; cause unknown). Existing old native library was not assumed corrupt.
- Added scripts/verify-indexer-environment.py: verifies installed wheel RECORD
  hashes/sizes before loading native code, then checks a C++98 direct-call parse.
- Verified 11 package files and native library size 63,703,544 bytes. A tampered
  temporary file was rejected; installed package files were not modified.
- Full 59 engine tests (53 storage), four schema checks and four JavaScript suites
  passed, including actual libclang indexing/helper/case-linking regressions.
- Recovery instructions: docs/INDEXER_ENVIRONMENT.md. Evidence report:
  experiments/fprime/indexer-environment.json.
- No UI changes, production deployment or F Prime binary test rerun this chunk.

## Next bounded backend work
Define explicit generator/toolchain input policy and completeness gates before
snapshot publication or agent-context eligibility. Existing partial snapshot stays
staging. Do not treat matching recorded files/directories as complete task context.
Alternatively address user manual UI feedback when available. Their package from
01a52fc is still valid; browser-control rejection remains and must not be bypassed.

## Locations
Atlas /path/to/workspace/atlas-site
F Prime /path/to/workspace/fprime
Active graph .atlas/fprime-rebuilt.sqlite; membership-only probe is separate.
Pinned upstream revision 7d8f579f159d2f7c2d4984d92828575e37f87fa6.

---
Previous checkpoints follow.

# Resume checkpoint — disk-store chunk 12

## Constraints
Keep chunks about five to six minutes, then checkpoint and stop. Owner-private
hosting unchanged. User is performing manual UI checks when available.

## Completed this chunk
- Engineering adapter v2 records versioned, bounded directory membership for
  Health/CmdDispatcher docs/*.md and test/ut/*.cpp (immediate entries only).
- Before/after discovery detects concurrent additions/removals and rolls back import.
- Recorded-input audit checks membership before/after hashes; old markers explicitly
  report not_recorded. No historical backfill, snapshot promotion or context approval.
- F Prime probe .atlas/fprime-membership-probe.sqlite is NEW inventory/engineering
  only: 14 pending compilations, both discovery manifests match. This is NOT the
  active graph. See experiments/fprime/storage-membership.json and docs/STORAGE.md.
- Active graph .atlas/fprime-rebuilt.sqlite unchanged. User package at 01a52fc remains
  valid for UI testing. Hosted viewer unchanged. Browser QA still pending/blocked.
- 41 non-native storage/API tests + four schema checks passed. Native parsing was
  not rerun; previous .venv is absent.

## Next bounded work
Choose explicit generator/toolchain input policy and completeness gates, or
restore the pinned native-parser environment and run compiler/linking regressions
against the new engineering adapter. Avoid claiming publication eligibility until
those gates and scope semantics are defined. Directory discovery is deliberately
narrow and does not validate contents of otherwise unparsed Markdown documents.
Await user's manual viewer feedback; do not bypass the browser-control rejection.

## Locations and history
Atlas /path/to/workspace/atlas-site
F Prime /path/to/workspace/fprime
Upstream revision 7d8f579f159d2f7c2d4984d92828575e37f87fa6.
Earlier checkpoints and manual package details follow.

---
# Resume checkpoint — disk-store chunk 11

## Session constraint
Work in bounded five-to-six-minute chunks, commit/push, then stop until asked.
Keep hosting private; this chunk is backend-only with no deployment.

## Completed this chunk
- New read-only CLI: atlas_engine/storage/freshness.py. Audits recorded repo/build
  artifacts for one snapshot with streaming hashes and file/total/item budgets.
- Reports stale, incomplete or recorded_inputs_match. Always context_eligible=false.
  No snapshot publication or requirement approval. External paths are not read.
- Real UT report: 171 matching repo/build artifacts; 302 unchecked external inputs;
  incomplete. Five parsed compilations, nine pending (Ref is a separate snapshot).
- Seven new regression tests; all 34 non-native storage/API tests and four schema
  checks passed. See STORAGE.md for guarantees and limitations.
- Prior native-parser virtual environment disappeared. Do not imply the native
  suite was rerun this chunk. Standard-library checks remain runnable.

## User browser validation
User will manually test when able. Delivered atlas-local-test-01a52fc.zip contains
viewer/API from 01a52fc, copied SQLite store, 171 hash-matching source files,
licenses, Windows/Python launcher and checklist. No compiler or pip dependencies.
Package API smoke passed on Linux; Windows launcher/browser interaction unverified.
Latest backend audit is intentionally separate; user's test package stays valid.
Cloud browser QA blocked: Sites requires unavailable control-browser skill;
automatic review rejected an alternate tab attachment. Do not bypass that rejection.
Hosted site remains unchanged, owner-private; browser/visual QA remains pending.

## Next bounded backend work
Define and record selected engineering-directory membership and generator inputs
so additions/removals can invalidate traces; current audit covers recorded files
only. Then establish explicit external/toolchain policy and completeness gates
before any publication or agent-context eligibility. Do not silently call a
recorded-input match a fresh, complete graph. Await user's UI test feedback.

## Locations
Atlas: /path/to/workspace/atlas-site
F Prime: /path/to/workspace/fprime
Active DB: .atlas/fprime-rebuilt.sqlite (all snapshots staging).
Pinned upstream revision: 7d8f579f159d2f7c2d4984d92828575e37f87fa6.
Recover Atlas from its managed remote if scratch disappears; rebuild sample per
experiments/fprime/README.md. Do not rely on local caches/virtual environments.

---
Previous checkpoint follows for local-view details.

# Resume checkpoint — disk-store chunk 10

## Historical checkpoint workflow
Use bounded checkpoints, leaving time to commit and record progress. Do not treat
one checkpoint as authorization to complete the whole remaining milestone.

## Completed
- Focused local Atlas trace view: public/local-trace.html/.css/.js, served at the
  loopback API root through an explicit three-file allowlist. Existing hosted
  explorer is unchanged. No generic directory/file serving was added.
- Exact search, results, incoming/outgoing relationships, pagination, back history,
  evidence/source panels, candidate/unresolved notices and connect/disconnect flow.
- Token memory only; source/data use textContent; API authorization still required.
- All 39 storage/API tests + four schema checks pass. Build and JS syntax passed.
- Browser interactions, layout/accessibility and visual QA NOT yet performed.
- Active working DB remains .atlas/fprime-rebuilt.sqlite; all snapshots staging.

## Next bounded chunk
Validate the new local trace view with an appropriate local browser test workflow.
Managed Sites cloud preview uses terminal.local and cannot reach the deliberately
127.0.0.1-only adapter without weakening Host/Origin constraints; don't weaken them.
Review applicable browser/preview skill guidance before choosing the workflow.
Test connect, exact lookup, follow/back, incoming/outgoing, multi-page old/new rows,
evidence after navigation, source statuses, disconnect (no stored token), and narrow
viewport. Fix defects, record screenshots if available, then checkpoint. No private
hosting change has been made; decide clearly labeled hosted snapshot vs live local
experience only after this local flow is validated.

Later: full viewer integration, freshness/publication, execution evidence with
binary binding, remaining scoped parsing and large-codebase performance work.

## Time budget
User authorized this bounded local-view chunk. Save/push and stop before the next
browser-validation or deployment chunk. Keep the existing privacy settings.

## Locations
Atlas checkout: /path/to/workspace/atlas-site
F Prime checkout: /path/to/workspace/fprime
Pinned F Prime commit: 7d8f579f159d2f7c2d4984d92828575e37f87fa6
Managed source project ID is in .openai/hosting.json. Push source checkpoints
without opting into automatic publication. Existing hosted explorer remains v0.3.
If scratch disappears, recover Atlas from its managed Git remote and recreate
F Prime using experiments/fprime/README.md. Do not rely on local build caches.
