# Atlas architecture review handoff — 2026-10-01

## Authority and pause point

This is the current implementation snapshot for the architecture-review thread
and its successor implementation thread. Inspected baseline: **d5e44ad** (full
source through the validated offline demo package). This handoff is a subsequent
documentation-only commit; use the commit supplied with the handoff to read it.
No new architecture guidance from the user's original conversation has been
provided to this implementation thread yet. Do not infer or pre-approve it.

The user requested architecture review before deeper indexing work. **Pause the
proposed scoped indexing runner and other new runtime/schema work until the
review's decisions are recorded and the user resumes implementation.** No code
was left uncommitted at the start of this handoff. Nothing needs to be completed
before review. Pending validation is recorded below, not a blocker to review.

Read in order: this document; schema-v1.sql and modules linked below; ADRs 0001–0003;
READINESS.md; FPRIME-ACCEPTANCE.md; OFFLINE_PILOT.md; relevant evidence reports.
PROJECT.md, STORAGE.md and RESUME.md retain chronological history; older entries
saying a now-implemented feature is pending are not current status.

## Product objective and user constraints

Atlas should supply relevant, bounded, current context so agents can contribute
to large existing codebases. Graph traversal provides dependency structure;
requirements/tests/engineering metadata provide intent and evidence. Vectors are
planned for fuzzy entry-point discovery, not as proof of dependencies. Human
inspection and requirements review are also important. Relevant context quality
is primary; packet size is secondary. Potential dependency impact is not proof
of behavioral change or requirement satisfaction.

User-reported target: about 150k production + 150k test + 600k generated lines;
approximately 24 applications, mostly C++98 backend and some C++11 frontend,
MISRA/safety-critical, largely single-threaded; Linux development/test plus an
embedded RTOS. Generated GUI implementation is mostly ignorable, but shared
communication structs and parser dependencies matter. No confidential source
has been supplied. Actual application membership, toolchain flags, requirement
formats and test conventions still need evidence/adapters.

Offline pilot host: **RHEL 9 x86_64, Firefox**. Exact RHEL minor release, approved
Python/RPM set and Firefox version are unknown. Python 3.12 is a candidate, not
a universal RHEL 9 prerequisite; the preflight does not pronounce other versions
incompatible. Hosting must remain owner-private. The local API remains loopback
only with fixed roots, Host/Origin enforcement and session tokens. Work in roughly
5–6 minute chunks, commit/push and stop; the user controls continuation.

## There are two implemented paths, not a completed migration

| Path | What actually runs | Boundary |
| --- | --- | --- |
| Legacy JSON prototype | atlas_engine/indexer.py and test_runner.py; scripts/agent.mjs and tools.mjs; public/retrieval.js; original hosted explorer | Single repo/configuration fixture workflow, in-memory graph/JSON, TU cache, four JSONL agent operations and bounded context packets. No MCP server. |
| SQLite/local trace path | atlas_engine/storage/*; public/local-trace.html/.js/.css | Scoped staging ingestion, compilation-specific graph/evidence, bounded read-only inspection, on-demand source and loopback viewer. No SQLite task-context assembler/refresh/publication workflow yet. |

The original hosted explorer remains unchanged by the SQLite/offline chunks.
The F Prime trace is local, not connected to the hosted explorer. Browser no
longer needs the entire graph for the local SQLite viewer. This addresses the
architecture of the reported 1.7 GB index.json loading problem; scale performance
has NOT been established. JSON-to-SQLite migration is not implemented. Avoid
assuming legacy context/freshness guarantees automatically apply to SQLite.

## Storage and identity: implemented versus intended

Authoritative DDL: [schema-v1.sql](../atlas_engine/storage/schema-v1.sql).

| Tables / area | Implemented meaning and remaining limits |
| --- | --- |
| repository, snapshot | Snapshot-scoped graph with revision/configuration/input hash/schema/indexer/toolchain fields. Revision and toolchain fingerprint are operator labels, not verified binary identities. Snapshots remain staging. |
| artifact, compilation, compilation_input | Named-root paths/hashes, origin, target/source/command variants and dependency inputs. Exact duplicate commands deduplicate; source-path-only deduplication is avoided. Paths/command normalization remain conservative. |
| build_target, target_dependency | Explicit object-target selection; CMake output-path target extraction. Target dependency table exists, but importer does not populate an application/build dependency graph. Object targets are not proven executable membership. |
| entity, occurrence | Logical compiler USR or scoped engineering identity separated from compilation-specific source spans/roles. Not a complete type/layout/macro/symbol model. |
| relation, evidence | Directed indexed adjacency; resolved, unresolved and candidate states; separate compiler/build/authored/inferred/execution/review evidence kinds. Evidence kind is not enforced truth/authorization policy by itself. |
| relation_review, metadata | Schema structures exist; persistent authorized review/typed metadata/conflict and revision-carry workflows are not implemented. Browser prototype annotations are not authoritative shared reviews. |
| test_run, test_result | Schema exists; selected historical executable results live in experiment reports, not a source/build/binary-bound SQLite execution ingestion workflow. |

Foreign keys enforce snapshot association. Query state and byte/work budgets are
implemented in services; full immutability/publication/semantic evidence rules
are NOT enforced by the schema. No schema migration framework. Bodies are absent
from SQLite graph rows; source is read on demand from a hash-matching checkout.
There is no implemented content-addressed source blob store or cross-snapshot
content deduplication despite that being a useful intended direction.

## Runtime map and operational limits

| Module / entry point | Implemented behavior |
| --- | --- |
| storage/store.py; python -m atlas_engine.storage | Initialize schema, atomic scoped compile-manifest import. Reads full compile database with 32 MiB cap. Supports arguments arrays/POSIX command strings as data; does not execute them. Requires selected target/files; CMake output target extraction. |
| storage/compiler.py; parse-compilation | Serial libclang ingestion for one compilation; definitions/declarations, direct calls, unresolved virtual/indirect calls, headers/hashes. Restricted compiler/flag allowlist; unsupported wrappers/options rejected. Rollback and failed diagnostic on parse error. No automatic parsing orchestrator. |
| engineering.py, membership.py | Narrow F Prime Health/CmdDispatcher adapter: docs/sdd.md requirement rows and test/ut/*.cpp annotations; directory membership for selected immediate docs/*.md and test/ut/*.cpp. Not a general engineering importer. |
| annotation_links.py, test_cases.py | Unique containing compiled helper spans, explicit ambiguity; source-declared GoogleTest wrappers/direct helper calls scoped by object target. Containment/call association is not execution or verification. |
| inspect.py | Exact lookup and incoming/outgoing adjacency; explicit snapshot/target, shared evidence caveats, pagination. Default 50/max 200 items, 256 KiB; clipped fields labeled. SQLite progress budget around 2 million VM steps / 0.5 s, not a hard filesystem deadline. |
| details.py | Evidence and source details capped separately (64 KiB, at most 200 lines; source file cap 16 MiB). Whole-file hash and observed stat checks; stale/missing/oversize paths return no misleading source. Explicit repo/build roots only. |
| freshness.py, external_roots.py | Bounded read-only audit of recorded files, selected engineering directory membership and explicitly mapped external roots. Not complete discovery or an atomic filesystem snapshot. Not wired into inspection requests as a current-context gate. |
| readiness.py | Explains parse/input/discovery/toolchain/generator/scope/publication blockers. Always inspection-only/context-ineligible today; cannot publish or approve requirements. |
| http.py; scripts/start-local.sh | Standard-library single-process loopback HTTP with fixed startup DB/target/snapshot/source roots, GET-only API, random in-memory bearer token, exact Host/Origin checks, three static assets. No tunnel, hosted backend or multi-user authentication system. |
| storage/demo.py | Synthetic authored illustrative trace for offline installation/UI checks; staging/pending, zero executions/reviews. No native parser required to generate it. |

Cursor identity binds query filters and local DB/WAL metadata; observed changes
invalidate cursors. This is not a portable cryptographic snapshot token. Source
hash checks do not establish whole-graph freshness. External freshness mappings
do not make external headers available through the source HTTP endpoint.

## Real and synthetic evidence

F Prime pinned v4.3.0 / **7d8f579f159d2f7c2d4984d92828575e37f87fa6**;
GoogleTest **58d77fa8070e8cec2dc1ed015d66b454c8d78850**. It uses C++14 and is an
architectural evaluation candidate, not an exact C++98/11/MISRA/24-app surrogate.
See experiments/fprime/README.md and committed reports/logs for reproduction.

- Ref executable built; no Ref runtime integration test. Selected Health and
  Command Dispatcher cases: 21 assertions/cases passed, initial processes failed
  under unsupported LeakSanitizer tracing; reruns passed with detect_leaks=0.
  Both outcomes retained; not a full F Prime/RTOS/default-sanitizer pass.
- Inventory found 169 documented requirement rows; scoped import contains 12
  definitions, 11 test annotations and seven candidate HTH-* / ISF-HTH-* aliases.
  IDs are not merged or approved. Eleven annotations map to eight helpers;
  21 source-declared cases map to test bodies, eight cases link to helpers.
- Real bounded trace: Test.NominalTlm -> helper -> ISF-HTH-001 -> candidate HTH-001.
  This does not establish complete method -> requirement -> executed verification.
- Saved external-input audit matched 302 external headers plus 171 repository/build
  files. Old discovery evidence and toolchain/generator completeness remain missing.
- Local disposable .atlas/fprime-rebuilt.sqlite metadata inspected for this handoff:
  UT 14 compilations (5 parsed/9 pending); Ref 4 (1 parsed/3 pending). Both staging.
  3,718 entity, 10,570 occurrence, 8,703 relation rows; target_dependency,
  test_run, test_result and relation_review each empty. These are cross-snapshot
  row counts, not distinct method counts or fresh/complete validation.

The synthetic Demo.Nominal trace is separate: hand-authored illustrative links,
pending compilation, candidate requirement/alias and unresolved callback. It
provides no compiler, execution, or verification evidence for F Prime or user code.

## Validation and artifacts as of this checkpoint

Latest full result: **91 engine tests + four schema checks passed** from the
extracted offline package on Ubuntu/Python 3.12.14. This includes native parsing,
not just schema tests. Hash verification, fresh local-wheel installation, C++98
smoke and live synthetic launcher/API trace passed; server stopped, no tokens saved.
Evidence: experiments/offline/demo-transfer-workspace.json. No new runtime tests
were needed for this documentation-only handoff; these are the recorded results.

User manual result: all nine viewer checks passed for package 01a52fc on Windows
10 / Chrome / Python 3.14.5, with no errors (local-view-manual-validation.json).
It does not qualify native indexing under that Python version or RHEL/Firefox.
Original browser automation was blocked by unavailable required skill/approval;
manual validation was recorded separately, not represented as assistant browser QA.

Latest downloadable candidate: **atlas-offline-2c8ee75.zip**, source commit
2c8ee75cbb92560727303eda909c150416241d37; 24,823,377 bytes, 70 files.
SHA-256: `6fa7533c6d5516dfed7cf6ec73f193a1d50ec87c9bfc45f71fcec258855fcc65`.
Includes engine/viewer/tests, Aurora fixture, synthetic generator, libclang wheel,
license, checksums, README and installer/launcher. No OS Python/RPMs, Firefox,
private code or F Prime DB. libclang pin 18.1.1; wheel lock is committed.
The latest Git baseline d5e44ad adds validation documentation after package source;
do not confuse archive version with current source checkpoint.

RHEL/Firefox validation is pending. Actual network-disabled installation was NOT
run: host denied unshare uid_map setup. Local-wheel/no-index flags alone are not
network-isolation proof. Use an authorized isolated validation host; do not bypass
the restriction. Exact platform prerequisites and repository compatibility remain
unknown. Temporary wheelhouses/venvs can disappear; recreate from the lock.

## Backlog proposed before architecture review (not authorization to proceed)

1. RHEL preflight, approved Python/RPM selection, isolated installation, Firefox
   synthetic-demo checklist; preserve validation scope and errors.
2. A scoped import/parse orchestration command selecting one real application
   configuration, with unsupported options, incomplete coverage and recovery
   reported. Existing individual commands work; this proposed runner is unbuilt.
3. Verified snapshot-bound parser/compiler/configuration identity, generator
   input/output provenance, explicit application membership and generated scope.
4. Coherent ready publication, immutable/historical identity and freshness-gated
   retrieval/rebuild lifecycle; preserve previous usable snapshot on failure.
5. SQLite agent task-context assembly, inclusion reasons/omissions, staged
   retrieval and refresh integration equivalent to/learning from legacy tools.
6. General requirement/test adapters, source/build/binary-bound execution evidence,
   persistent reviewed mappings and extensible typed engineering metadata.
7. Larger ingestion/performance study: time, peak RSS, disk size, latency, fanout,
   configuration variants. No scale SLA or vector subsystem exists yet.

Order is provisional. Review may change boundaries, schema and priorities. Do
not finish this list before considering the new architecture guidance.

## Thread-specific rationale and lessons to preserve

These notes explain prior choices and tradeoffs. They are not new architecture
approvals or evidence that an unimplemented mechanism works.

- **SQLite was a practical first disk store, not a final graph-engine mandate.**
  It supports the local/air-gapped pilot without a database server. The essential
  move was away from monolithic delivery toward indexed, bounded queries and
  on-demand source. A dedicated graph database is neither required by the word
  "graph" nor ruled out by this prototype. Reassess storage against measured
  workloads, identity semantics and operational constraints.
- **The graph is already real, but the end-to-end agent migration is incomplete.**
  Legacy JSON tools still own task-context packing and refresh. SQLite provides
  parsed relationships and bounded human inspection. Keeping both paths allowed
  incremental validation; it is not an intended permanent split in authority.
  The review should choose a shared semantic contract and migration boundary.
- **Partial inspection is a deliberate useful mode.** Staging graphs can support
  exploration and compatibility testing with visible omissions. Readiness gates
  restrict claims of current/complete agent context; they should not be interpreted
  as a demand to finish all verification infrastructure before a limited pilot.
  A successful pilot still does not establish requirement satisfaction.
- **The recent packaging work was a deployment-learning step.** It followed the
  user's request to prepare for an air-gapped repository. It does not mean core
  architecture, agent-context retrieval or application membership are finished,
  or that packaging should dominate the next implementation backlog.
- **The two test repositories have different jobs.** F Prime supplies authentic
  generated interfaces, compile variants and existing engineering documentation.
  Aurora and the synthetic demo supply controlled behavior, language/trace cases
  and install/UI checks. A synthetic demo pass cannot replace real ingestion;
  F Prime's C++14 results cannot establish customer C++98/11/RTOS compatibility.
- **Conservative parsing is intentional.** Unsupported compiler arguments and
  ambiguous mappings remain explicit instead of being dropped or guessed. The
  cost is narrower initial coverage. Generalization should preserve diagnostic
  evidence and semantics, not merely increase successful-parse counts.
- **App identity is more than configuration or object-target identity.** Preserving
  compilation variants solved one prerequisite. It did not yet answer which of
  the user's 24 applications consume a shared struct, nor what behavior changes.
  Struct/type use and build/deployment membership remain central review topics.
- **Engineering observations must not silently become verification claims.**
  Requirement references, containing helpers, runnable case identities, executed
  results and approved mappings are distinct. The real Health identifier mismatch
  and sanitizer process failures are useful cases to preserve during redesign.
- **Checksums and recovery are practical lessons, not root-cause conclusions.**
  A prior SQLite working file was rebuilt after corruption; a truncated libclang
  file was replaced; temporary environments repeatedly disappeared. Sources,
  locks, reports and rebuild scripts are the durable recovery path. We have not
  established why those incidents occurred or linked their causes.
- **Timeboxing changed delivery granularity, not acceptance criteria.** Work
  used bounded checkpoints with commits and resume notes for each handoff.
  Repeated small checkpoints should not be mistaken for independent architecture
  approval or full-feature completeness.

For the next implementation thread: make the architecture review's accepted
priorities explicit, preserve old tests as evidence where still applicable, and
add migration tests for semantics that change. Do not treat the old backlog order,
SQLite schema, package runtime candidate or current conservative scope as immutable
user requirements. Keep the actual user constraints and provenance guarantees
separate from revisable implementation choices.

## Questions and outputs for architecture review

Compare incoming guidance against code and ADRs. Explicitly assess graph schema
and evidence semantics; symbol/occurrence/configuration/application identity;
source storage/deduplication; generated/model relationships; current versus
historical context; provenance/reviews; query/agent contracts; scale and migration.
Identify which mechanisms to retain, extend, replace, defer or retire. Preserve
user constraints and evidence distinctions; changes to accepted decisions need
rationale, migration/compatibility consequences and testable acceptance criteria.

Expected durable outputs: new numbered ADR(s) with status and supersession links;
an architecture gap/transition plan; a dependency-ordered implementation backlog;
and an updated RESUME.md naming the first bounded task, risks and validation gates.
Do not rewrite historical results to fit a new design. Label proposals separately
from user-approved decisions. Do not imply permission to deploy or change privacy.

The successor implementation thread should first read this snapshot, the new
review outputs, and the updated RESUME.md at the supplied commit. Verify git
status before edits. It should not resume the old indexing plan by default.

## Recovery and navigation

Repository: atlas-site in the shared workspace, Git branch main; managed remote
is already configured as origin. Commit/push is the durable source checkpoint;
local caches/builds/venvs/databases are disposable. If checkout is absent, recover
from the authorized managed source repository. Do not rely on conversation memory
or historical scratch paths as the sole specification.

- docs/decisions/0001-graph-first-context.md: legacy graph/context design.
- docs/decisions/0002-controlled-agent-pilot.md and docs/PILOT.md: pilot methodology.
- docs/decisions/0003-configuration-aware-disk-store.md: intended SQLite contract.
- docs/STORAGE.md, LOCAL_API.md, EXTERNAL_INPUTS.md, READINESS.md: runtime details.
- docs/FPRIME-ACCEPTANCE.md: broader acceptance gates, not a completed checklist.
- scripts/rebuild-fprime-store.py and experiments/fprime/README.md: rebuild path.
- scripts/offline-preflight.py, install-offline.py, assemble-offline.py,
  verify-indexer-environment.py; docs/OFFLINE_PILOT.md: packaging/recovery.
