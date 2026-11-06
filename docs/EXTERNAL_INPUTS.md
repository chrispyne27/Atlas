# Explicit external-header checks

The freshness and readiness CLIs can verify recorded external headers through
operator-selected mappings. Their default remains no external filesystem reads.
No HTTP/source-excerpt route accepts these mappings or exposes external contents.

Example for the current Linux F Prime evaluation:

```sh
python -m atlas_engine.storage.freshness \
  --database .atlas/fprime-rebuilt.sqlite \
  --snapshot bd6c4ddd353f4437a03812c834743c5c \
  --repo-root ../fprime \
  --build-root ../fprime/build-fprime-automatic-native-ut \
  --external-root /usr/include=/usr/include \
  --external-root /usr/lib/gcc/x86_64-linux-gnu/13/include=/usr/lib/gcc/x86_64-linux-gnu/13/include
```

The same repeatable flag is accepted by `atlas_engine.storage.readiness`. Each
mapping is `RECORDED_POSIX_PREFIX=LOCAL_DIRECTORY`. A relocated SDK can map a
recorded `/opt/sdk/include` prefix to a different local directory; matching bytes
are still checked against the original snapshot's hashes. Select the roots
deliberately, not by automatically copying arbitrary paths out of an imported DB.
This adapter accepts POSIX recorded identities; Windows-native recorded path
identities need a separate policy rather than guessed conversion.

The recorded absolute path is never resolved or opened directly. The mapper
computes a relative suffix under an explicitly selected prefix, joins that suffix
to the local root, then verifies the resolved path remains within it. Prefix
matching respects path components; traversal and nonnormalized paths are not
mapped. Most-specific mappings take precedence. Duplicate prefixes, filesystem
root mappings and more than 16 mappings are rejected. Normal filesystem file and
path races remain subject to the audit's documented observation-based limits.

Mapped files share the audit's existing item, per-file and aggregate byte budgets,
streaming hash checks, regular-file checks and final metadata recheck. Unmapped
files remain `not_checked`. Reports include selected roots and external status
counts, tied to the selected snapshot, without source contents. They do not write
the database, bless a relocated SDK, or establish whole-toolchain equivalence.

## Results and limitations

The real Health UT readiness report in `experiments/fprime/storage-external-inputs.json`
found all 302 recorded external headers matching under the two roots above.
Combined with 171 repository/build files, all 473 recorded artifact hashes match.
The audit still reports incomplete because the old engineering import has no
directory-membership baseline. The toolchain-identity readiness check remains
blocked: parser/compiler binary identity and configuration are not yet bound to
a verified snapshot manifest. Generator provenance and completeness gates remain.

Six new tests cover default-deny external reads, SDK relocation, changed/missing
files, byte limits, symlink escapes, traversal/prefix confusion, invalid broad
mappings and most-specific-root selection. All 71 engine tests (65 storage) and
four schema checks pass. No browser validation, site deployment or binary test
execution was performed in this chunk; the local viewer package is unchanged.
