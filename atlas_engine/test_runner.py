"""Build and execute the trusted, authored fixture only. Does not execute arbitrary manifest commands."""
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import json
from .indexer import inventory, fingerprint, atomic_json


def run_tests(repo, output=None):
    root = Path(repo).resolve()
    inputs = inventory(root)
    compiler = os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++')
    if not compiler:
        raise RuntimeError('Install g++ or clang++, or set CXX to its executable.')
    fixtures = json.loads((root / 'test_manifest.json').read_text())
    sources = sorted(root.glob('src/*.cpp')) + sorted(root.glob('tests/*.cpp'))
    with tempfile.TemporaryDirectory(prefix='atlas-native-') as temporary:
        executable = Path(temporary) / ('aurora-tests.exe' if os.name == 'nt' else 'aurora-tests')
        command = [compiler, '-std=c++11', '-Wall', '-Wextra', '-Werror', '-I' + str(root / 'include'), *map(str, sources), '-o', str(executable)]
        built = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if built.returncode:
            raise RuntimeError('C++ compilation failed:\n' + built.stderr)
        results = []
        for fixture in fixtures:
            ran = subprocess.run([str(executable), fixture['argument']], capture_output=True, text=True, timeout=10)
            results.append({'id': fixture['id'], 'symbol': fixture['symbol'], 'role': fixture['role'], 'status': 'passed' if ran.returncode == 0 else 'failed', 'exit_code': ran.returncode, 'requirements': fixture['requirements']})
    if inventory(root) != inputs:
        raise RuntimeError('Sources changed during test execution; evidence discarded.')
    result = {'source_fingerprint': fingerprint(inputs), 'executed_at': datetime.now(timezone.utc).isoformat(), 'compiler': subprocess.check_output([compiler, '--version'], text=True).splitlines()[0], 'compile_flags': ['-std=c++11', '-Wall', '-Wextra', '-Werror'], 'tests': results, 'passed': sum(t['status'] == 'passed' for t in results), 'total': len(results)}
    atomic_json(root / '.atlas' / 'test-results.json', result)
    if output:
        atomic_json(output, result)
    return result
