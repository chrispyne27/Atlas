"""Verify installed libclang files against wheel metadata before a native smoke parse.

This detects local missing/truncated/changed files, not package authenticity.
Run with the interpreter that will execute Atlas tests.
"""
import argparse
import base64
import hashlib
from importlib.metadata import distribution
import json
from pathlib import Path
import platform
import sys


def verify():
    expected = (Path(__file__).resolve().parents[1] / 'requirements-indexer.txt').read_text().strip()
    if not expected.startswith('libclang==') or '\n' in expected:
        raise ValueError('Expected exactly one pinned libclang requirement')
    dist = distribution('libclang')
    if dist.version != expected.split('==')[1]:
        raise ValueError('Installed libclang differs from the repository pin')
    checked = []; native = []
    for entry in dist.files or []:
        if not entry.hash:
            continue
        path = dist.locate_file(entry)
        if not path.is_file():
            raise ValueError('Missing installed file: ' + str(entry))
        h = hashlib.new(entry.hash.mode)
        total = 0
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(block); total += len(block)
        actual = base64.urlsafe_b64encode(h.digest()).rstrip(b'=').decode('ascii')
        if actual != entry.hash.value or (entry.size is not None and total != entry.size):
            raise ValueError('Installed file fails wheel RECORD verification: ' + str(entry))
        checked.append(str(entry))
        if 'clang/native/' in str(entry).replace('\\', '/') and path.suffix in {'.so', '.dll', '.dylib'}:
            native.append({'file': str(entry), 'bytes': total, 'record_hash': entry.hash.mode + ':' + actual})
    if not native:
        raise ValueError('No hash-verified bundled native library found')
    # Load native code only after the package files passed verification.
    from clang import cindex
    unit = cindex.Index.create().parse('atlas-smoke.cpp', args=['-std=c++98'],
        unsaved_files=[('atlas-smoke.cpp', 'int helper() { return 1; } int caller() { return helper(); }')])
    if any(d.severity >= cindex.Diagnostic.Error for d in unit.diagnostics):
        raise ValueError('Native C++98 smoke parse produced errors')
    calls = [n for n in unit.cursor.walk_preorder() if n.kind == cindex.CursorKind.CALL_EXPR]
    if not any(n.referenced and n.referenced.spelling == 'helper' for n in calls):
        raise ValueError('Native smoke parse did not resolve helper call')
    return {'status': 'passed', 'python': platform.python_version(), 'platform': platform.system(),
            'libclang': dist.version, 'record_verified_files': len(checked), 'native_libraries': native,
            'smoke': 'C++98 parse and resolved direct call',
            'scope': 'Installed files match wheel metadata; not an authenticity or whole-environment guarantee.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    try:
        result = verify()
    except Exception as error:
        print('Indexer environment verification failed: ' + str(error), file=sys.stderr)
        return 1
    content = json.dumps(result, indent=2) + '\n'
    if args.report:
        args.report.write_text(content)
    print(content, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
