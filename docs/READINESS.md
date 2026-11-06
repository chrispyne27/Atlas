> Current status (2026-10-01): This document includes historical milestone status; later implementation supersedes earlier pending-feature statements. See [ARCHITECTURE_SNAPSHOT.md](ARCHITECTURE_SNAPSHOT.md). New implementation is paused for architecture review.

# Snapshot readiness assessment

The disk-store inspection APIs can show partial, staging graphs. Before a future
agent retrieval service claims that context is current and complete for a chosen
scope, it needs explicit input and completeness checks. This assessment explains
the current blockers; it does not publish snapshots or change access permissions.

```sh
python -m atlas_engine.storage.readiness \
  --database .atlas/fprime-rebuilt.sqlite \
  --snapshot bd6c4ddd353f4437a03812c834743c5c \
  --target build/F-Prime/Svc/Health/CMakeFiles/Svc_Health_ut_exe.dir \
  --component Svc/Health \
  --repo-root ../fprime \
  --build-root ../fprime/build-fprime-automatic-native-ut
```

Select an exact target and one or more explicit engineering components. Component
selection is an operator declaration, not an inferred application/target mapping.
The CLI computes a new freshness audit rather than trusting a saved report. It
opens the store read-only and rejects observed DB changes across the assessment.
Its initial SQL metadata phase has a two-million-step/0.5-second work budget;
the filesystem audit retains its own item/byte bounds, not a hard I/O deadline.

| Check | Current interpretation |
| --- | --- |
| Recorded inputs | All recorded snapshot inputs must match; other targets' inputs conservatively remain in scope. |
| Selected target parses | At least one compilation and every compilation parsed. Pending, failed and excluded entries block an unqualified completeness claim. |
| Engineering discovery | Each explicitly selected component must have a matching recorded directory manifest. Old or absent markers remain unknown. |
| Toolchain identity | Blocked: operator fingerprint labels and host paths are not verified toolchain identities. |
| Generator provenance | Blocked when generated artifacts are recorded: output hashes do not bind them to generator inputs/version/options. |
| Scope completeness | Blocked: application boundaries, source exclusions and full discovery policy remain undefined. |
| Publication contract | Blocked: immutable publication and retrieval-time freshness enforcement remain unimplemented. |

Each check provides a status, evidence summary and next action. The overall
result remains `blocked`, `inspection_only=true`, `context_eligible=false`.
Even a row labeled `ready` in the database cannot bypass missing contracts.
This CLI does not change the existing viewer or enable/disable a retrieval route.
Partial inspection remains useful; the blockers apply to the proposed guarantee
of current, complete task context rather than to browsing labeled partial data.

## Toolchain and generator policy to implement next

Toolchain evidence must bind the actual selected parser/compiler versions and
binaries, relevant flags/configuration, and an explicit approved set of external
include roots with their recorded inputs. Never read arbitrary absolute paths from
an imported database just because they are marked external. The environment
verification helper checks package integrity on this machine; it is not a substitute
for a snapshot-bound toolchain record or cross-compilation target identity.

Generated outputs need declared producer identity, invocation/configuration and
input hashes, plus evidence that the output belongs to that invocation. Matching
output bytes alone cannot establish this relationship. A later exclusion policy
may omit GUI output, while preserving communication structs and anything needed
for selected methods' dependency/requirement traces. No exclusion policy is granted
by this assessment. Existing stored compiler commands remain data, never executed.

## Verification is a separate question

Candidate aliases and unresolved calls are counted and must retain their labels.
They are not automatically treated as missing toolchain evidence or false
requirements. A resolved edge identifies entities; it does not prove satisfaction.
The report explicitly leaves requirement satisfaction, executable test evidence
and review approval `not_assessed`. A future requirement-verification assessment
must preserve source/build/target/binary identity and reviewer provenance.

## Recorded validation

`experiments/fprime/storage-readiness.json` assesses the existing Health UT target:
two parsed and three pending compilations. The old snapshot has no engineering
directory manifest, unchecked external inputs, and generated artifacts without
generator provenance. All seven readiness checks remain blocked as expected.
Relationship counts include shared authored scope and template/header calls; they
are not requirement coverage or distinct production-method counts.

Six new tests cover read-only behavior, pending/failed/excluded parses, selected
target isolation, fresh directory checks, missing component scope, explicit
toolchain/publication blockers and observed DB changes. Full regression results:
65 engine tests (59 storage) and four schema checks passed. Browser testing remains
pending. No site deployment, snapshot promotion or test execution claim was added.
