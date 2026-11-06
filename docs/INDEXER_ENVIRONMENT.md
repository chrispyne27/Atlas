# Recreate and verify the indexer test environment

Runtime environments are disposable; source checkpoints and pinned requirements
are the recovery path. Do not infer that a cached interpreter or native library is
usable just because its directory exists.

From the Atlas checkout on Linux:

```sh
python3 -m venv .venv-validation
.venv-validation/bin/python -m pip install --no-cache-dir -r requirements-indexer.txt
.venv-validation/bin/python scripts/verify-indexer-environment.py
.venv-validation/bin/python -m unittest discover -s tests/engine -v
python3 scripts/check-storage-schema.py
ATLAS_PYTHON="$PWD/.venv-validation/bin/python" npm test
```

The verification script reads the repository's libclang pin, checks installed
hashed files against wheel RECORD sizes/checksums, then loads the native library
for a minimal C++98 parse with a resolved direct call. It exits nonzero on a
verification failure. `--report PATH` optionally writes a successful JSON report.
This detects file damage; it does not establish package authenticity or validate
all system headers, compiler binaries, environment variables or toolchain inputs.

If verification fails, repair/recreate the disposable environment using the pinned
requirement, then run the check again before native tests. Never treat tests that
did not execute as passing. Browser tests require their separate supported browser
workflow; these commands do not exercise the UI or bypass that requirement.

Chunk 13: the older `.venv` directory remained but its Python executable was absent
(dependent Python symlinks remained). A separate `.venv-validation` was created
without modifying that old environment. The new libclang 18.1.1 installation has
11 RECORD-verified files, including the 63,703,544-byte Linux native library.
The cause of the missing interpreter was not established.

All 59 engine tests (including 53 storage tests), four schema checks and four
JavaScript suites passed. The new verification script also rejected an intentionally
damaged temporary package-file copy before native loading; installed files were
not changed. Results are in `experiments/fprime/indexer-environment.json`.
F Prime binaries were not rebuilt/re-executed, and browser QA remains pending.
