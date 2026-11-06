"""Read-only offline pilot inventory. Emits JSON; never installs or loads libclang.

Run with the explicit interpreter intended for Atlas. Exit 0 means no observed
blockers, NOT qualified compatibility. Exit 1 means blocked; 2 is CLI misuse.
"""
import sys
sys.dont_write_bytecode = True

import argparse
import importlib.util
from importlib import metadata
import json
from pathlib import Path
import platform
import re
import shlex
import shutil

ROOT = Path(__file__).resolve().parents[1]


def read_os_release(path=Path('/etc/os-release')):
    """Parse data without sourcing shell text or executing substitutions."""
    result = {}
    with path.open(encoding='utf-8') as stream:
        text = stream.read(65537)
    if len(text) > 65536:
        raise ValueError('os-release exceeds inventory limit')
    for line in text.splitlines():
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        if key not in {'ID', 'VERSION_ID', 'PRETTY_NAME'}:
            continue
        parts = shlex.split(value, comments=False, posix=True)
        if len(parts) != 1 or key in result:
            raise ValueError('Malformed or duplicate OS field')
        result[key] = parts[0]
    return result


def sqlite_probe():
    """Exercise required SQLite capabilities using only an in-memory database."""
    import sqlite3
    db = sqlite3.connect(':memory:')
    try:
        db.executescript((ROOT / 'atlas_engine/storage/schema-v1.sql').read_text())
        if db.execute('PRAGMA foreign_keys').fetchone()[0] != 1:
            raise ValueError('SQLite foreign keys unavailable')
        if db.execute("SELECT json_valid('{}')").fetchone()[0] != 1:
            raise ValueError('SQLite JSON validation unavailable')
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('In-memory schema integrity failed')
        return {'status': 'observed', 'version': sqlite3.sqlite_version,
                'checks': ['schema creation', 'foreign keys enabled', 'json_valid', 'integrity']}
    finally:
        db.close()


def collect():
    facts = {'system': platform.system(), 'architecture': platform.machine(),
             'python': platform.python_version(), 'python_minor': list(sys.version_info[:2]),
             'interpreter': sys.executable, 'libc': list(platform.libc_ver()),
             'venv_active': sys.prefix != sys.base_prefix}
    try:
        facts['os'] = read_os_release()
    except (OSError, ValueError) as error:
        facts['os'] = {'error': type(error).__name__}
    try:
        facts['sqlite'] = sqlite_probe()
    except Exception as error:
        facts['sqlite'] = {'status': 'blocked', 'error': type(error).__name__}
    for name in ('venv', 'pip'):
        try:
            facts[name] = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            facts[name] = False
    facts['firefox_path'] = shutil.which('firefox') or shutil.which('firefox-esr')
    facts['firefox_version'] = 'not inspected; browser was not executed'
    try:
        facts['libclang'] = {'version': metadata.version('libclang'),
                            'scope': 'distribution metadata only; native bytes not loaded or verified'}
    except metadata.PackageNotFoundError:
        facts['libclang'] = {'version': None}
    except Exception as error:
        facts['libclang'] = {'version': None, 'error': type(error).__name__}
    facts['assets'] = {name: (ROOT / 'public' / name).is_file() for name in
                       ('local-trace.html', 'local-trace.css', 'local-trace.js')}
    try:
        pin = (ROOT / 'requirements-indexer.txt').read_text().strip()
        facts['parser_pin'] = pin.split('==')[1] if re.fullmatch(r'libclang==[0-9.]+', pin) else None
    except OSError:
        facts['parser_pin'] = None
    return facts


def assess(facts, mode):
    blockers = []
    pending = ['RHEL package provenance and exact RPM versions',
               'Firefox version and nine manual UI checks',
               'offline installation and recovery test',
               'real application scope and build compatibility']
    os_info = facts['os']
    if facts['system'] != 'Linux' or os_info.get('ID') != 'rhel' or not re.fullmatch(r'9(?:\.[0-9]+)*', os_info.get('VERSION_ID', '')):
        blockers.append('Host is not identified as the selected RHEL 9 target')
    if facts['architecture'] != 'x86_64':
        blockers.append('Host architecture does not match x86_64 wheel')
    if facts['python_minor'] != [3, 12]:
        pending.append('Selected interpreter differs from Python 3.12 candidate; qualify separately (not proof of incompatibility)')
    if facts['sqlite']['status'] != 'observed':
        blockers.append('Required SQLite capabilities or bundled schema unavailable')
    if not all(facts['assets'].values()):
        blockers.append('Local viewer assets missing')
    if not facts['firefox_path']:
        pending.append('Firefox not found on PATH; confirm an approved local browser installation')
    if mode == 'indexer':
        if facts['parser_pin'] is None:
            blockers.append('Repository parser version pin missing or malformed')
        elif facts['libclang'].get('version') != facts['parser_pin']:
            blockers.append('Selected interpreter lacks the pinned libclang distribution')
        pending.extend(['verify-indexer-environment.py native integrity/smoke check',
                        'compiler and generated-input provenance'])
        if not facts['venv'] or not facts['pip']:
            pending.append('venv/pip installation tooling unavailable; required for planned fresh-venv installation')
    return {'report_version': 1, 'mode': mode,
            'status': 'blocked' if blockers else 'requires_validation',
            'qualified': False, 'blockers': blockers, 'pending_validation': pending,
            'observations': facts,
            'scope': 'Read-only local prerequisites; no installation, network, subprocess, browser launch, native libclang load or repository indexing.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('viewer', 'indexer'), default='indexer')
    args = parser.parse_args()
    report = assess(collect(), args.mode)
    print(json.dumps(report, indent=2))
    return 1 if report['blockers'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
