"""Build a deterministic pilot ZIP from a clean committed checkout and pinned wheel."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXACT = {'requirements-indexer.txt', 'requirements-indexer-linux-x86_64.lock',
         'public/local-trace.html', 'public/local-trace.css', 'public/local-trace.js',
         'scripts/install-offline.py', 'scripts/offline-preflight.py',
         'scripts/verify-indexer-environment.py', 'scripts/check-storage-schema.py',
         'scripts/start-local.sh', 'docs/OFFLINE_PILOT.md', 'docs/LOCAL_API.md',
         'docs/OFFLINE_README.txt'}


def selected(path):
    return path in EXACT or path.startswith(('atlas_engine/', 'tests/engine/', 'samples/aurora/'))


def write_zip(output, payload):
    # Fixed ordering, timestamps and permissions; never overwrite an existing file.
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(payload.items()):
            if name.startswith('/') or '..' in Path(name).parts or '\n' in name or '\\' in name:
                raise ValueError('Unsafe archive member')
            entry = zipfile.ZipInfo('atlas-offline/' + name, (1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (0o100755 if name.endswith('.sh') else 0o100644) << 16
            archive.writestr(entry, data)


def assemble(wheelhouse, output):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(ROOT), *args])
    if git('status', '--porcelain').strip():
        raise ValueError('Commit or clear checkout changes before assembling')
    revision = git('rev-parse', 'HEAD').decode().strip()
    spec = importlib.util.spec_from_file_location('offline_install', ROOT / 'scripts/install-offline.py')
    installer = importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)
    wheel = installer.verify_wheel(wheelhouse)
    payload = {}
    for name in git('ls-tree', '-r', '--name-only', revision).decode().splitlines():
        if selected(name):
            payload[name] = git('show', revision + ':' + name)
    if not EXACT.issubset(payload):
        raise ValueError('Required transfer files missing from source commit')
    wheel_bytes = (wheelhouse / installer.WHEEL).read_bytes()
    if hashlib.sha256(wheel_bytes).hexdigest() != wheel['sha256']:
        raise ValueError('Wheel changed during assembly')
    payload['wheelhouse/' + installer.WHEEL] = wheel_bytes
    import io
    with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as archive:
        names = [n for n in archive.namelist() if n.endswith('.dist-info/LICENSE.TXT')]
        if len(names) != 1:
            raise ValueError('Expected one upstream wheel license')
        payload['licenses/libclang-LICENSE.TXT'] = archive.read(names[0])
    payload['README-FIRST.txt'] = payload.pop('docs/OFFLINE_README.txt')
    payload['SOURCE.json'] = (json.dumps({'commit': revision, 'target': 'RHEL 9 x86_64 / Firefox',
        'qualified': False, 'wheel': wheel, 'contents': 'Atlas engine/viewer/tests, Aurora fixture, libclang wheel; no F Prime database, OS Python, RPMs or browser'}, indent=2) + '\n').encode()
    payload['licenses/ATLAS-NOTICE.txt'] = b'Atlas project source for the requesting user\'s internal pilot. This notice grants no new license. No third-party Atlas source license was found in the source checkout. libclang retains its accompanying upstream license.\n'
    payload['SHA256SUMS'] = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n'
        for name, data in sorted(payload.items())).encode()
    write_zip(output, payload)
    return {'source_commit': revision, 'archive': output.name, 'bytes': output.stat().st_size,
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'payload_files': len(payload), 'qualified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheelhouse', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(assemble(args.wheelhouse.resolve(), args.output), indent=2))
