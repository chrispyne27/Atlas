# Offline pilot: RHEL 9 / x86_64 / Firefox

Status: dependency inventory and packaging contract, 2026-09-30. No installer or
RHEL-qualified release exists yet. User confirmed the OS family, architecture and
browser. Exact RHEL minor release, installed Python and Firefox versions remain
unknown. First scope: one application's Linux configuration, read-only inspection.
RTOS parsing and all-application impact analysis require separate acceptance.

## Runtime inventory and decisions

| Layer | Dependency / pin | Distribution decision |
| --- | --- | --- |
| Viewer and HTTP API | Python standard library, including sqlite3; three local-trace assets | Ship Atlas source and assets; no pip packages required for inspection |
| Native indexing | libclang==18.1.1, Python bindings and bundled shared library | Ship the exact x86_64 manylinux wheel in a hash-locked wheelhouse |
| Python | Candidate: explicit python3.12 with venv and pip | Use approved RHEL packages, record exact RPM versions; do not copy this workspace's virtual environment |
| Native loader | glibc/loader libraries from target OS | Resolve on the target; never copy Ubuntu system libraries into the package |
| Parsing inputs | compile_commands.json, selected source/generated files, system/SDK headers, macros and language flags | Supplied by the user's existing build; preserve target/configuration identity |
| Browser | Locally installed Firefox; version pending | All nine local-view manual checks must be repeated on RHEL/Firefox |
| Build/test tooling | Existing compiler/build system; Git for optional legacy revision metadata | Needed for generating build inputs or compiling fixtures, not to serve an existing SQLite graph |
| Web development only | Node, Vite 8.3.0, Playwright 1.62.1 | Exclude from offline runtime; local-trace assets are already plain HTML/CSS/JS |

Python 3.12 is a candidate because prior native validation used that interpreter
family. RHEL defaults to Python 3.9; Red Hat documents 3.11 from RHEL 9.2 and 3.12
from 9.4. Do not silently invoke system python3 or declare Python 3.9 incompatible
without testing it. If 3.12 is unavailable on the approved machine, qualify an
available interpreter separately. The previous viewer package requested Python
3.10+, but that is not a native-indexer qualification on RHEL.

Source inspection found only clang.cindex as a third-party engine import. The
SQLite schema must accompany the Python files at
atlas_engine/storage/schema-v1.sql. The HTTP server resolves public/local-trace.html,
.css and .js relative to the checkout, so preserve that directory layout. There
are no remote asset references in those three assets in this baseline.

The existing installed x86_64 libclang WHEEL metadata declares manylinux2010.
readelf reports dependencies on libdl.so.2, librt.so.1, libpthread.so.0, libm.so.6,
libc.so.6 and ld-linux-x86-64.so.2. These observations are not a RHEL loader test.
The exact candidate wheel and its published SHA-256 are pinned in
requirements-indexer-linux-x86_64.lock; original requirements-indexer.txt remains
the cross-platform version pin. The lock is not evidence of a downloaded artifact.

## Package contents

- Atlas source at an exact commit, schema, three viewer assets, scripts for
  environment/schema checks, fixtures and relevant tests; retain relative paths.
- Original libclang wheel, hash lock, third-party license texts including
  Apache-2.0 WITH LLVM-exception, and provenance/notice inventory for every shipped
  component. Resolve Atlas redistribution terms before release. Include F Prime
  and GoogleTest licenses if shipping their sample material.
- Release manifest: Atlas commit, file SHA-256 values, wheel filename/hash,
  selected Python/pip RPM versions and source, target platform, and validation
  report versions. Verify archive bytes before transfer and after extraction.
- Offline installer and launcher (next implementation): explicit interpreter,
  local venv, no online fallback, no system Python replacement, user-writable data
  directory, and the existing 127.0.0.1-only service/token behavior.
- Optional small sample graph plus exactly matching source and scope report;
  separate it from any user-created repository index. No confidential files leave
  the user's environment.

Obtain Python/pip RPMs and their dependency closure through the organization's
approved RHEL media/repository route if they are absent. Exact RPM pins require
the selected RHEL minor release and package set; do not bundle arbitrary RPMs or
claim the Python stack is fully pinned yet. pip is installation tooling, not a
running Atlas dependency. No compiler, CMake or F Prime generator is implicitly
provided by the libclang wheel.

## Offline installation contract (not yet an implemented installer)

On a connected packaging host obtain only the pinned binary wheel, compare its
SHA-256 with the lock, preserve its licenses, then build a checksum manifest.
On the isolated target, verify the transferred files and create a fresh venv using
the explicitly selected interpreter. Install using the local wheelhouse:

```sh
.venv/bin/python -m pip --isolated install --no-index --no-cache-dir \
  --find-links wheelhouse --only-binary=:all: --require-hashes \
  -r requirements-indexer-linux-x86_64.lock
.venv/bin/python scripts/verify-indexer-environment.py
.venv/bin/python scripts/check-storage-schema.py
```

The future installer must fail if prerequisites or wheel bytes are missing or
wrong. No pip upgrade/download fallback. Test with external networking unavailable
but loopback enabled, and an empty pip cache. Record loader resolution and exact
Python/SQLite/native-library versions. Installed wheel RECORD verification catches
damage; it does not replace transferred-artifact hash/provenance verification.

## Acceptance gates

1. Clean RHEL 9 x86_64 installation: record minor release, Python/pip RPMs, glibc,
   SQLite and Firefox versions; install from approved local artifacts without
   network access or privileged application installation.
2. Native smoke: package hashes, shared-library load, C++98 direct-call parse;
   engine/schema regressions with the existing compiler available for fixture
   tests. Record missing prerequisites as blocked, never as passing.
3. Real build compatibility: select one application/configuration and capture its
   genuine compile commands, generated inputs and headers. The current parser
   accepts only a restricted flag set and compiler names; wrappers, response files
   and cross-toolchain flags require explicit adaptation. Do not drop flags to
   make parsing succeed. Check zero/error diagnostics and known symbol/call cases.
4. Freshness/recovery: changed/missing source and external headers, new requirement
   or test files, interrupted import rollback, and repeatable rebuild in a new
   database. Retain staging/partial-scope and unresolved evidence labels.
5. Firefox: connect, exact search, follow/back, directions, evidence/source clearing,
   paging, narrow layout, keyboard focus and disconnect/reload. Same-machine
   127.0.0.1 URL; preserve Host/Origin protections and memory-only tokens. Capture
   failures without exposing session tokens. Existing Windows/Chrome results do
   not satisfy this gate.
6. Pilot review: engineers compare several known method/requirement/test traces;
   measure index duration, peak memory, database size and query latency for this
   scope. No requirement satisfaction or full-repository readiness inferred.

## Current evidence and next chunk

Inventory inspected at baseline 09ab18b. Workspace is Ubuntu 24.04, not RHEL.
The old .venv-validation interpreter is unavailable in this session even though
package metadata/native bytes remain; no new native regression pass is claimed.
Prior 71 engine tests/four schema checks and user Windows validation remain
historical evidence only. This change adds documentation and an artifact lock.

Next bounded chunk: implement a read-only target preflight and offline package
assembler/installer interface, with explicit incomplete/missing prerequisite
reporting. Obtain wheel bytes and verify the lock before calling the package
ready. RHEL execution and Firefox validation remain separate pending gates.
Snapshot-bound toolchain/generator provenance and publication gates from the
previous roadmap remain required; this packaging work does not implement them.

## Primary sources checked 2026-09-30

- Red Hat Python versions/packages:
  https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/installing_and_using_dynamic_programming_languages/index
- libclang 18.1.1 wheel tags, published hashes and license:
  https://pypi.org/project/libclang/18.1.1/

## Implemented target preflight (chunk 2)

Run from the extracted Atlas checkout with the interpreter intended for Atlas:

```sh
python3.12 -B scripts/offline-preflight.py --mode viewer
python3.12 -B scripts/offline-preflight.py --mode indexer
```

Use another explicitly selected interpreter if that is what the target provides;
Python 3.12 remains a candidate, not a prerequisite installed by this script.
Output is JSON on stdout. Redirect it to a chosen file only when you want a saved
report. Exit 1 means observed blockers; exit 0 means requires_validation, never
qualified compatibility; exit 2 denotes argument misuse. The script does not
install anything, access the network, execute subprocesses, open Firefox, load
libclang, inspect user repositories, or write an on-disk database. Bytecode writing
is disabled. SQLite schema/JSON/foreign-key/integrity checks use :memory: only.

Indexer mode checks installed libclang metadata against requirements-indexer.txt.
Metadata presence is not binary integrity or loader compatibility. Viewer mode
does not require libclang, pip or venv. pip/venv presence is only discovery, not
proof a new environment can be created or used offline. Firefox is located on
PATH only; custom installations remain a manual check and no version is inferred.
A non-candidate Python version calls for separate qualification, not a claim that
it is incompatible. OS identity is read from /etc/os-release without shell sourcing.

Evidence: experiments/offline/preflight-workspace.json. Both real invocations
returned exit 1 on Ubuntu as expected; viewer mode reports the platform mismatch,
indexer mode additionally reports absent libclang in the selected interpreter.
Eight focused tests and four schema checks passed. Native indexing and RHEL /
Firefox execution were not run. The next chunk is acquiring/verifying the wheel
and building the offline assembler/installer; these remain unimplemented.

## Implemented local-wheel installer (chunk 3)

This section supersedes earlier statements that the installer and wheel retrieval
are unimplemented. A complete transfer archive/assembler is still pending.

The exact pinned wheel was downloaded and its SHA-256 verified. The wheel is a
temporary packaging input, not committed binary content. If absent, reacquire on
the connected packaging host using the existing hash lock:

```sh
python3 -m pip --isolated download --no-deps --only-binary=:all: \
  --platform manylinux2010_x86_64 --python-version 312 --implementation py \
  --abi none --require-hashes -r requirements-indexer-linux-x86_64.lock \
  --dest /path/to/wheelhouse
```

From a checkout with the wheelhouse transferred, use the explicitly chosen Python:

```sh
python3.12 -B scripts/install-offline.py \
  --wheelhouse /path/to/wheelhouse --venv /path/to/new-atlas-venv
```

The destination's parent must exist; the destination itself must not. Existing
paths, including dangling symlinks, are rejected. Wheel version/bytes/hash are
checked before creating the environment. The installer uses the chosen Python's
venv/ensurepip, then installs only from the local wheelhouse with no index, no
cache, no dependencies, binary-only and required hashes. Python/pip environment
overrides are stripped; pip configuration files are disabled. No system Python
or packages are changed. No automatic pip upgrade or online fallback exists.
Subprocesses have timeouts. Failed new environments are retained for diagnosis;
a retry uses a new destination after the cause has been addressed.

After installation, the existing integrity verifier checks wheel RECORD hashes
before loading libclang for its C++98 smoke parse. Success records
atlas-install-report.json inside the new environment with qualified=false.
This installs the parser environment only: run Atlas from the source checkout.
It is not a packaged application launcher or a RHEL support declaration.

Evidence: experiments/offline/install-workspace.json. Final installer completed
successfully on Ubuntu/Python 3.12.14; the installed parser resolved the C++98 call.
All 85 engine tests (including 14 offline-preflight/installer tests) and four
schema checks passed. The test used local installation flags, but the host network
was not disabled: clean-host network-isolation acceptance is still pending.
RHEL/Firefox, exact RPM pins, source/license manifest, complete transfer archive,
and installer interruption/network-isolation tests remain pending.
Next chunk: assemble a reproducible transfer archive including wheel and licenses,
checksums, Atlas sources and a launcher; retain these acceptance limitations.

## Transfer archive (chunk 4)

scripts/assemble-offline.py builds a deterministic ZIP from a clean committed
checkout and the verified wheel. It uses committed bytes, an explicit source
allowlist, fixed member ordering/timestamps/modes, and rejects existing outputs.
SHA256SUMS covers all other archive files. SOURCE.json records the source commit
and wheel hash. The wheel's own upstream license is included. The archive excludes
F Prime data, repositories, secrets, git metadata, Python/RHEL RPMs and Firefox.
Atlas's notice creates no new source license.

Build on the packaging host:

```sh
python3 -B scripts/assemble-offline.py --wheelhouse /path/to/wheelhouse \
  --output /path/to/new-atlas-offline.zip
```

Candidate atlas-offline-a7cfba9.zip contains 67 files, including SHA256SUMS.
See experiments/offline/transfer-workspace.json for the full archive SHA-256 and
source commit. Follow README-FIRST.txt after extraction. The shell launcher is
invoked using sh scripts/start-local.sh, so ZIP extractor permission handling
is not required. It serves an existing compatible SQLite graph; this package
has no F Prime graph and no one-command user-repository ingestion workflow.

Extracted-copy validation passed: all manifested hashes, fresh local-wheel
installation and native smoke, launcher help, 85 engine tests and four schema
checks. This was Ubuntu, not RHEL, and networking was not disabled. Archive
assembly and the installed-runtime tests are separate from Firefox validation.
Next chunk: test installation with networking disabled and exercise the local
launcher against a small reproducible SQLite fixture; actual RHEL acceptance
and exact approved Python RPM selection remain pending.

## Live launcher validation (chunk 5)

New tests/engine/test_offline_launcher.py exercises the actual shell launcher as
a child process with runtime files copied into a directory containing spaces.
The parent working directory is outside the package and PYTHON* overrides are
removed. A synthetic staging SQLite fixture supplies explicit snapshot/target
scope; this is not fresh compiler/F Prime evidence. Port 0 selects a loopback
port without a check-then-bind race. Startup output is held only in memory and
never included in reports or assertion messages. Processes are stopped on cleanup.

Passed: static assets; authenticated config/lookup; paged relationships; evidence;
hash-verified source; changed-source suppression; absent token, Host/Origin and
write rejection; unchanged database SHA-256; restart token rotation and old-token
rejection. All 16 offline-workflow tests and four schema checks passed on Ubuntu.
No runtime changes were required; atlas-offline-a7cfba9.zip remains unchanged.
This session copied the same runtime files rather than extracting the saved ZIP.

Network-disabled installation remains BLOCKED here. The prerequisite command
`unshare --user --map-root-user --net true` exited 1 because uid_map writes are not
permitted. No installation ran inside an isolated namespace, and no privilege
workaround was attempted. Run this acceptance gate on an authorized disconnected
VM/host with the approved local prerequisites and transferred wheel, empty pip
cache and loopback enabled; retain installer/native-check logs and host isolation
evidence. A proxy setting or failed Internet request alone is not isolation proof.
RHEL/Firefox acceptance also remains pending. Native regression tests were not
rerun in this chunk because prior temporary environments are absent.

Evidence: experiments/offline/launcher-workspace.json. Reproduce local tests:

```sh
python3 -B -m unittest discover -s tests/engine -p 'test_offline*.py' -v
python3 -B scripts/check-storage-schema.py
```

Next bounded implementation: a repeatable small sample-database creation command
and launch instructions so the offline candidate can exercise a known trace
without depending on an existing F Prime database or private repository.

## Reproducible synthetic demo (chunk 6)

The new standard-library command creates a NEW directory containing demo.sqlite,
repo/demo.cpp and DEMO.json. No compiler, pip package, F Prime checkout or private
repository is required. Run from the Atlas checkout/package root:

```sh
python3 -B -m atlas_engine.storage.demo --output "$PWD/demo-data"
ATLAS_PYTHON="$(command -v python3)" sh scripts/start-local.sh \
  --database "$PWD/demo-data/demo.sqlite" --snapshot synthetic-demo-v1 \
  --target synthetic-demo-target --repo-root "$PWD/demo-data/repo"
```

Select the explicit target interpreter instead of python3 if needed. Open the
printed loopback URL and search exactly Demo.Nominal. Follow Demo.Helper then
Demo.Value then candidate DEMO-001 then candidate DEMO-ALIAS-001; the helper also
has an explicitly unresolved unknown_callback. Incoming navigation and evidence
source excerpts work. This demo is too small for the viewer's default 50-row
pagination; query tests exercise smaller page limits instead.

All relationships/evidence are authored synthetic examples. Compilation remains
pending, snapshot remains staging, source occurrences use description roles,
requirement mappings remain candidates, and no test runs or human approvals exist.
A resolved illustrative edge means a fixture endpoint exists, not that a compiler
resolved a real call. Source hashes verify these illustrative bytes only.
Existing destinations/symlinks are rejected. On an unexpected creation error,
an incomplete new directory may remain; success is indicated by DEMO.json.
Reproducibility tests compare logical SQL dumps and source bytes, not SQLite
binary layouts across versions. DEMO.json includes the chosen absolute paths.

All 20 offline-workflow tests and four schema checks passed. The previous download
atlas-offline-a7cfba9.zip does NOT contain this command. The assembler's existing
engine allowlist will include it in the next archive build. No new download or
RHEL/Firefox validation is claimed by this checkpoint.
Next bounded chunk: rebuild and validate the transfer archive with the demo, then
save the updated download and its checksum. Network-disabled installation remains
blocked on this workspace; use an authorized isolated validation host for that gate.

## Updated downloadable demo archive (chunk 7)

atlas-offline-2c8ee75.zip supersedes the earlier candidate for demo testing.
Source commit: 2c8ee75cbb92560727303eda909c150416241d37.
Size: 24,823,377 bytes; 70 files, including the 69-entry SHA256SUMS manifest.
Archive SHA-256:
6fa7533c6d5516dfed7cf6ec73f193a1d50ec87c9bfc45f71fcec258855fcc65

This package includes the new synthetic demo creation command and updated
README-FIRST.txt. It retains the pinned wheel, license, scripts and viewer.
The embedded documentation records history up to the source commit; this later
validation record is outside the archive so the tested bytes remain unchanged.

After extraction, all 69 manifested hashes matched; a fresh parser installation
passed RECORD integrity and C++98 smoke. All 91 engine tests and four schema
checks passed from the extracted package. Its demo command created a new fixture,
and its real shell launcher served the illustrative four-step trace and verified
source over HTTP from outside the package working directory. Anonymous API access
was rejected, database bytes stayed unchanged, and the server was stopped. No
token was saved. Evidence: experiments/offline/demo-transfer-workspace.json.

These results are Ubuntu/native/API validation, not a Firefox browser run or
RHEL qualification. Networking was not disabled. The prior namespace restriction
still blocks that gate here. The user can now follow README-FIRST.txt on an
approved RHEL validation machine using their explicitly selected Python.
Next acceptance input: RHEL preflight output and the synthetic-demo Firefox
checklist. Next implementation work can address scoped real-repository ingestion
once compile-command/build details are available; do not broaden compiler flags
or imply compatibility without evidence.
