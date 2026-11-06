"""Install the pinned Linux x86_64 parser into a NEW venv from local wheel bytes.

Run with the chosen Python interpreter. No downloads or system-package changes.
A successful install is not RHEL qualification. Failed new environments are kept
for diagnosis; existing destinations are never changed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WHEEL = 'libclang-18.1.1-py2.py3-none-manylinux2010_x86_64.whl'


def verify_wheel(wheelhouse, root=ROOT):
    lock = root / 'requirements-indexer-linux-x86_64.lock'
    lines = [s.strip() for s in lock.read_text().splitlines() if s.strip() and not s.lstrip().startswith('#')]
    if len(lines) != 1:
        raise ValueError('Expected exactly one locked requirement')
    match = re.fullmatch(r'libclang==18\.1\.1 --hash=sha256:([0-9a-f]{64})', lines[0])
    if not match or (root / 'requirements-indexer.txt').read_text().strip() != 'libclang==18.1.1':
        raise ValueError('Parser version or lock format differs from installer contract')
    path = wheelhouse.resolve(strict=True) / WHEEL
    if path.is_symlink() or not path.is_file():
        raise ValueError('Expected a regular, non-symlink pinned wheel')
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block); size += len(block)
            if size > 64 * 1024 * 1024:
                raise ValueError('Wheel exceeds size budget')
    if digest.hexdigest() != match[1]:
        raise ValueError('Wheel SHA-256 differs from repository lock')
    return {'filename': WHEEL, 'sha256': digest.hexdigest(), 'bytes': size}


def clean_environment():
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(('PYTHON', 'PIP_')) and key not in {'VIRTUAL_ENV', '__PYVENV_LAUNCHER__'}}
    # Disable inherited pip config files, including global target/prefix settings.
    environment['PIP_CONFIG_FILE'] = os.devnull
    return environment


def install(destination, wheelhouse):
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ValueError('This wheel installer targets Linux x86_64 only')
    # Reject existing paths (including dangling symlinks) before any mutation.
    destination = Path(os.path.abspath(destination))
    if os.path.lexists(destination):
        raise ValueError('Destination already exists; choose a new environment directory')
    wheelhouse = wheelhouse.resolve(strict=True)
    wheel = verify_wheel(wheelhouse)
    environment = clean_environment()
    destination.mkdir()  # atomic reservation; parent must already exist
    python = destination / 'bin/python'
    subprocess.run([sys.executable, '-I', '-m', 'venv', str(destination)],
                   env=environment, check=True, timeout=120)
    subprocess.run([str(python), '-I', '-m', 'pip', '--isolated', '--disable-pip-version-check',
                    'install', '--no-index', '--no-cache-dir', '--no-deps', '--only-binary=:all:',
                    '--require-hashes', '--find-links', str(wheelhouse),
                    '-r', str(ROOT / 'requirements-indexer-linux-x86_64.lock')],
                   env=environment, check=True, timeout=120)
    # Freshly installed library is loaded only after its RECORD integrity check.
    checked = subprocess.run([str(python), '-I', str(ROOT / 'scripts/verify-indexer-environment.py')],
                             env=environment, check=True, timeout=60, capture_output=True, text=True)
    result = {'status': 'installed_and_smoke_checked', 'qualified': False,
              'wheel': wheel, 'native_check': json.loads(checked.stdout),
              'scope': 'Local parser environment only; RHEL, Firefox, build compatibility and offline-network isolation require separate validation.'}
    (destination / 'atlas-install-report.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheelhouse', required=True, type=Path)
    parser.add_argument('--venv', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = install(args.venv, args.wheelhouse)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('Offline installation failed: ' + str(error), file=sys.stderr)
        print('No existing destination was replaced. If a new directory was created, it is retained for diagnosis.', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
