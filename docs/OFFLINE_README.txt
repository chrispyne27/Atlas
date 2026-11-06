ATLAS OFFLINE PILOT CANDIDATE — RHEL 9 / x86_64 / Firefox

This archive supplies Atlas sources, viewer assets, tests, an Aurora fixture,
and the pinned libclang wheel/license. It is not yet RHEL-qualified.
It does not contain Python/RHEL RPMs, Firefox, or the F Prime sample database.
Use your approved Python installation. Python 3.12 is the current candidate;
other versions require separate qualification. No internet is needed by the
installer, but a network-disabled acceptance run is still pending.

1. Extract the ZIP to a user-writable directory and cd into atlas-offline.
2. Verify transferred contents before executing scripts:
     sha256sum -c SHA256SUMS
   Compare the ZIP's own SHA-256 with the separately supplied checkpoint report.
   Checksums detect changed bytes; they are not a digital signature.
3. Collect prerequisites using the explicit interpreter intended for Atlas:
     python3.12 -B scripts/offline-preflight.py --mode viewer
   Exit 1 reports blockers; exit 0 still means compatibility validation pending.
4. Create a NEW environment (an existing .venv will be rejected):
     python3.12 -B scripts/install-offline.py --wheelhouse wheelhouse --venv .venv
5. Check the installed parser and schema:
     .venv/bin/python -B scripts/offline-preflight.py --mode indexer
     .venv/bin/python -B scripts/check-storage-schema.py
   Optional engine tests require a C++ compiler for some fixtures:
     .venv/bin/python -B -m unittest discover -s tests/engine -v
6. For a known SYNTHETIC trace without F Prime or private code:
     .venv/bin/python -B -m atlas_engine.storage.demo --output "$PWD/demo-data"
     sh scripts/start-local.sh --database "$PWD/demo-data/demo.sqlite" \
       --snapshot synthetic-demo-v1 --target synthetic-demo-target \
       --repo-root "$PWD/demo-data/repo"
   The output directory must be new. Search exactly Demo.Nominal. Follow the
   illustrative call to Demo.Helper, then Demo.Value, then candidate requirement
   DEMO-001 and its candidate alias. Demo.Helper also has an unresolved callback.
   Everything is hand-authored demonstration data, not compiler/test evidence.
   The viewer defaults to 50 rows per page; this small demo will not show More.

   Alternatively, inspect an EXISTING compatible Atlas SQLite graph using its scope
   and absolute database/repository paths:
     sh scripts/start-local.sh --database /path/to/graph.sqlite \
       --snapshot SNAPSHOT_ID --target TARGET_ID --repo-root /path/to/repository
   Set ATLAS_PYTHON to an absolute interpreter path if you used another venv.
   Do not type placeholder IDs literally. For help:
     sh scripts/start-local.sh --help
   This archive does not yet provide a one-command index of your repository.
7. Open the printed 127.0.0.1 URL in Firefox on this same machine; enter the token
   shown in the terminal. Keep tokens out of reports/screenshots. Ctrl-C stops it.

See docs/OFFLINE_PILOT.md for scope and pending acceptance gates, and
LOCAL_API.md in docs for viewer operation. Installation does not establish
requirement satisfaction, complete indexing, or target-build compatibility.
