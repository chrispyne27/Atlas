"""Read-only audit of recorded inputs, not approval of current agent context."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat

from .inspect import Inspector
from .store import canonical
from .membership import COMPONENTS, compare
from .external_roots import ExternalRoots, mapping_argument

MAX_ARTIFACTS = 10000
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_EXAMPLES = 50


def signature(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def hash_input(path, allowance):
    # Reject special files before opening; nonblocking open also avoids a FIFO
    # blocking if a local file is replaced between stat and open.
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        return 'not_regular', None, 0
    if before.st_size > allowance:
        return 'over_limit', None, 0
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode):
            return 'not_regular', None, 0
        if signature(before) != signature(opened):
            return 'changed_during_check', None, 0
        h = hashlib.sha256()
        used = 0
        while used < allowance:
            block = stream.read(min(1024 * 1024, allowance - used))
            if not block:
                break
            h.update(block)
            used += len(block)
        after = os.fstat(stream.fileno())
    if signature(before) != signature(after) or signature(before) != signature(path.stat()):
        return 'changed_during_check', None, used
    return h.hexdigest(), signature(before), used


def audit(database, *, snapshot, roots, external_roots=(), max_artifacts=MAX_ARTIFACTS,
          max_file_bytes=MAX_FILE_BYTES, max_total_bytes=MAX_TOTAL_BYTES):
    for value, cap in ((max_artifacts, MAX_ARTIFACTS), (max_file_bytes, MAX_FILE_BYTES),
                       (max_total_bytes, MAX_TOTAL_BYTES)):
        if type(value) is not int or not 1 <= value <= cap:
            raise ValueError('Invalid audit budget')
    if not isinstance(snapshot, str) or not 0 < len(snapshot) <= 2048:
        raise ValueError('Invalid snapshot')
    if set(roots) - {'repo', 'build'}:
        raise ValueError('Only explicit repo/build roots are supported')
    roots = {k: Path(v).resolve(strict=True) for k, v in roots.items()}
    if any(not p.is_dir() for p in roots.values()):
        raise ValueError('Source root must be a directory')
    external_policy = ExternalRoots(external_roots)
    reader = Inspector(database)
    try:
        version = reader._version()
        reader.db.execute('BEGIN')
        snap = reader.db.execute('SELECT id,revision,configuration_key,state FROM snapshot WHERE id=?', (snapshot,)).fetchone()
        if not snap:
            raise ValueError('Unknown snapshot')
        states = dict(reader.db.execute('SELECT state,count(*) FROM compilation WHERE snapshot_id=? GROUP BY state', (snapshot,)))
        discovery = []; discovery_inputs = []
        for component in sorted(COMPONENTS):
            marker = reader.db.execute('SELECT substr(details_json,1,2097153) FROM evidence WHERE snapshot_id=? AND id=?',
                                       (snapshot, 'engineering:' + component)).fetchone()
            if marker:
                if len(marker[0]) > 2097152:
                    discovery.append({'component': component, 'status': 'over_limit'})
                    continue
                recorded = json.loads(marker[0]).get('discovery')
                discovery_inputs.append((len(discovery), component, recorded))
                discovery.append(compare(roots.get('repo'), component, recorded))
        counts = Counter(); external_counts = Counter(); examples = []; checked = []; used = 0; visited = 0

        def record(key, status):
            counts[status] += 1
            if key.startswith('external:'):
                external_counts[status] += 1
            if status != 'matched' and len(examples) < MAX_EXAMPLES:
                examples.append({'artifact': key[:2048], 'status': status})

        rows = reader.db.execute('SELECT path,content_hash FROM artifact WHERE snapshot_id=? ORDER BY path LIMIT ?', (snapshot, max_artifacts + 1))
        more = False
        for key, expected in rows:
            if visited == max_artifacts:
                more = True
                break
            visited += 1
            if len(key) > 2048:
                record(key, 'not_checked'); continue
            if key.startswith('external:'):
                located = external_policy.locate(key)
                if located is None:
                    record(key, 'not_checked'); continue
                original, base = located
            elif key.startswith(('repo/', 'build/')):
                label, relative = key.split('/', 1)
                if label not in roots:
                    record(key, 'root_not_supplied'); continue
                base = roots[label]; original = base / relative
            else:
                record(key, 'not_checked'); continue
            if used >= max_total_bytes:
                record(key, 'over_limit'); continue
            try:
                path = original.resolve(strict=True)
                if not path.is_relative_to(base):
                    record(key, 'outside_root'); continue
                value, stamp, size = hash_input(path, min(max_file_bytes, max_total_bytes - used))
                used += size
                if stamp is None:
                    record(key, value); continue
                checked.append((key, original, path, stamp))
                record(key, 'matched' if value == expected else 'changed')
            except FileNotFoundError:
                record(key, 'missing')
            except (OSError, RuntimeError):
                record(key, 'unreadable')
        # Catch observed changes to early files while later files were hashed.
        unstable = []
        for key, original, path, stamp in checked:
            try:
                if original.resolve(strict=True) == path and signature(path.stat()) == stamp:
                    continue
            except (OSError, RuntimeError):
                pass
            unstable.append(key)
        for index, component, recorded in discovery_inputs:
            after = compare(roots.get('repo'), component, recorded)
            if discovery[index]['status'] == 'matched':
                discovery[index] = after
        reader.db.execute('COMMIT')
        if reader._version() != version:
            raise ValueError('Database changed during audit; retry')
        mismatch = any(counts[k] for k in ('changed', 'missing', 'changed_during_check')) or bool(unstable)
        mismatch = mismatch or any(item['status'] in ('changed', 'missing_directory_or_member') for item in discovery)
        complete = not more and visited > 0 and counts['matched'] == visited and not unstable
        complete = complete and all(item['status'] == 'matched' for item in discovery)
        return {'inspection_only': True, 'context_eligible': False, 'snapshot': dict(snap),
                'checked_at': datetime.now(timezone.utc).isoformat(),
                'status': 'stale' if mismatch else ('recorded_inputs_match' if complete else 'incomplete'),
                'compilation_states': states, 'visited_artifacts': visited, 'more_artifacts': more,
                'engineering_directory_membership': discovery,
                'external_inputs': {'policy': 'explicit-root-mappings-v1',
                                    'roots': external_policy.describe(), 'counts': dict(external_counts)},
                'counts': dict(counts), 'bytes_hashed': used, 'examples': examples,
                'examples_truncated': sum(v for k, v in counts.items() if k != 'matched') > len(examples),
                'changed_after_check': unstable[:MAX_EXAMPLES], 'changed_after_check_count': len(unstable),
                'limitations': ['Recorded inputs and recorded engineering directories only; newly added files outside those scopes are not checked.',
                    'Only explicitly mapped external inputs are checked. Toolchain identity, generator inputs and binaries are not validated.',
                    'Not an atomic filesystem snapshot; change-and-restore races are not excluded.',
                    'No publication, requirement approval, test execution or graph completeness assertion.']}
    finally:
        reader.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--repo-root')
    parser.add_argument('--build-root')
    parser.add_argument('--external-root', action='append', default=[], type=mapping_argument,
                        metavar='RECORDED_PREFIX=LOCAL_DIRECTORY')
    args = parser.parse_args()
    result = audit(args.database, snapshot=args.snapshot, external_roots=args.external_root,
                   roots={k: v for k, v in [('repo', args.repo_root), ('build', args.build_root)] if v})
    print(canonical(result))


if __name__ == '__main__':
    main()
