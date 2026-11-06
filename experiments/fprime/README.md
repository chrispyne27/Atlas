> Current implementation summary: [architecture snapshot](../../docs/ARCHITECTURE_SNAPSHOT.md). Initial integration gaps below describe acquisition-time limitations; later SQLite work resolves some, not all. Experiment results remain scoped historical evidence.

# F Prime evaluation — acquisition checkpoint

Upstream: https://github.com/nasa/fprime.git, tag `v4.3.0`, commit
`7d8f579f159d2f7c2d4984d92828575e37f87fa6`.
GoogleTest submodule: `58d77fa8070e8cec2dc1ed015d66b454c8d78850`.

This is a local evaluation of unmodified upstream source, not an upstream
contribution, flight qualification, MISRA audit, or equivalence claim.
F Prime uses C++14. It exercises components, generated interfaces, operating
system abstractions, deployment composition and real component requirements.
It does not reproduce the customer's 24 applications or C++98/11 constraints.

## Reproduce acquisition and inventory

```sh
git clone --depth 1 --branch v4.3.0 --recurse-submodules --shallow-submodules https://github.com/nasa/fprime.git ../fprime
python scripts/fprime-audit.py ../fprime --output experiments/fprime/source-audit.json
cd ../fprime
python -m venv fprime-venv
. fprime-venv/bin/activate
pip install -r requirements.txt
cmake --preset fprime-ut
```

`source-audit.json` records physical lines (including comments and blanks),
not logical SLOC. The path-based split is 112,003 other C/C++ lines, 106,105
test C/C++ lines, and 14,034 FPP model lines. Generated build output and
GoogleTest are excluded. Five textual executable/deployment declarations
are not a count of resolved applications.

The limited Markdown extractor found 169 requirement rows and seven explicit
Health documentation verification claims. This is not exhaustive extraction.
Requirement identities must include repository and document/component scope;
IDs alone may not be globally unique. Documentation claims are retained as
claims, not promoted to executed verification or approved implementation links.

## Initial integration gaps

Atlas currently requires fixture-specific requirement/test manifests, accepts
only compilation `arguments` arrays, rejects multiple compilation entries per
source, and stores source bodies in its in-memory JSON graph. F Prime requires
normal CMake compilation databases, generated-header availability, configuration
identity, component/deployment membership and an external test runner.

The 1.7 GB customer index makes disk-backed storage and bounded queries a
prerequisite for scale integration. Source bodies should be loaded on demand;
the browser should fetch search results and neighborhoods rather than download
the complete index. Preserve generated communication types and provenance;
exclude irrelevant GUI implementation while retaining parsing dependencies.

Build and test results follow below.

## Executed baseline

Environment: Linux x86_64, Python 3.12.14, GCC 13.3.0, CMake 3.26.0,
Ninja 1.11.1.4, upstream-pinned FPP 3.3.0 and fprime-tools 4.3.0.
The upstream tracked files were not modified. Build artifacts remain local.

```sh
# In F Prime, with its venv active:
cmake --build build-fprime-automatic-native-ut --target Svc_Health_ut_exe Svc_CmdDispatcher_ut_exe -j 4
cmake -S TestDeploymentsProject -B build-atlas-ref -G Ninja -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_BUILD_TYPE=Debug
cmake --build build-atlas-ref --target Ref -j 4
ctest --test-dir build-fprime-automatic-native-ut -R 'Svc_(Health|CmdDispatcher)_ut_exe' --output-on-failure
ASAN_OPTIONS=detect_leaks=0 ctest --test-dir build-fprime-automatic-native-ut -R 'Svc_(Health|CmdDispatcher)_ut_exe' --output-on-failure
```

- Ref deployment: configured, generated and built successfully. Its executable
  was linked; no runtime/deployment integration test was performed.
- Health: all 11 GoogleTest cases passed in the initial run.
- Command Dispatcher: all 10 GoogleTest cases passed in the initial run.
- Both initial processes subsequently failed when LeakSanitizer reported that
  it cannot operate under ptrace in this environment. `ctest-default.xml` and
  `logs/fprime-tests.log` retain this failure rather than hiding it.
- Both executables passed CTest with `ASAN_OPTIONS=detect_leaks=0`.
  Address/undefined-behavior instrumentation was not removed. Leak checking
  remains unverified; this is not a clean run under all upstream defaults.
  See `ctest-no-leak.xml` and the second test log.
- This is selected-component evidence, not a full F Prime test-suite result,
  RTOS result or requirements verification approval.

## Compilation and parsing evidence

`build-probe.json` was produced by:

```sh
# In Atlas:
python -m venv .venv
.venv/bin/pip install -r requirements-indexer.txt
.venv/bin/python scripts/fprime-probe.py ../fprime --output experiments/fprime/build-probe.json
```

| Configuration | Compile entries | Distinct sources | Generated compile entries | Object targets |
| --- | ---: | ---: | ---: | ---: |
| Linux framework unit tests | 1,328 | 1,150 | 669 | 357 |
| Linux Ref deployment | 618 | 618 | 366 | 204 |

These are configured database entries, not counts of compiled files from the
selected build or independent applications. The unit-test configuration has
175 source paths with multiple entries. That directly exercises a limitation
of Atlas's existing one-entry-per-source representation.

Two handwritten implementation units were parsed using Atlas's existing
`parse_unit`, with zero diagnostics: Health (144 definitions, 147 direct call
observations, 28 unresolved observations) and Command Dispatcher (354, 236,
275 respectively). Counts include reachable header definitions and repeated
observations, not distinct repository entities. They are not additive across
translation units. Dynamic dispatch remains unresolved; FPP topology routing
needs explicit modeling beyond ordinary C++ direct calls.

The bounded probe parses trusted POSIX CMake command strings with `shlex`,
without executing them, and supplies the GCC builtin include directory to
libclang. Without that explicit include directory parsing failed on `stddef.h`.
This is a reproducible adapter probe, not production support for arbitrary
compilation databases or a full Atlas index.

## First traceability discrepancy

`Svc/Health/docs/sdd.md` defines HTH-001 through HTH-007 and associates test
*descriptions* with them. `Svc/Health/test/ut/HealthTester.cpp` annotates
ISF-HTH-001 through ISF-HTH-007 instead. These are candidate aliases requiring
review, not automatically equivalent identifiers. Command Dispatcher tests
explicitly annotate CD-001 through CD-004. The presence of an annotation and a
passing executable does not by itself prove requirement satisfaction.

Imported requirement text and excerpts remain attributed to F Prime at the
pinned revision; its license and notice are in `upstream-license/`.

## Next implementation milestone

Build a configuration-aware disk-backed importer and bounded retrieval API,
starting with these two components and Ref membership. Preserve generated
interface/type relationships, unresolved calls and mapping provenance. Import
requirements and explicit test annotations, surface the Health ID discrepancy,
and expose an inspectable method → requirement → test trace in the existing
private explorer without making the browser load the full index.

Human approval of an inferred alias, a test execution and an approved
verification claim must remain separate records. Do not infer critical-path
status from call-graph reachability. Scale ingestion only after this trace and
its stale-evidence behavior work end to end.
