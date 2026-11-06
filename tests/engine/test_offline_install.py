import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('offline_install', Path(__file__).resolve().parents[2] / 'scripts/install-offline.py')
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class OfflineInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = b'wheel-byte-fixture'
        (self.root / installer.WHEEL).write_bytes(self.data)
        (self.root / 'requirements-indexer.txt').write_text('libclang==18.1.1\n')
        (self.root / 'requirements-indexer-linux-x86_64.lock').write_text(
            'libclang==18.1.1 --hash=sha256:' + hashlib.sha256(self.data).hexdigest())

    def test_hash_and_tamper(self):
        self.assertEqual(installer.verify_wheel(self.root, self.root)['bytes'], len(self.data))
        (self.root / installer.WHEEL).write_bytes(b'damaged')
        with self.assertRaises(ValueError): installer.verify_wheel(self.root, self.root)

    def test_missing_and_symlink_wheel(self):
        path = self.root / installer.WHEEL; path.unlink()
        with self.assertRaises(ValueError): installer.verify_wheel(self.root, self.root)
        path.symlink_to(self.root / 'requirements-indexer.txt')
        with self.assertRaises(ValueError): installer.verify_wheel(self.root, self.root)

    def test_lock_rejects_extra_requirements_and_changed_pin(self):
        lock = self.root / 'requirements-indexer-linux-x86_64.lock'
        original = lock.read_text()
        for content in (original + '\nother-package==1', 'libclang==18.1.1 --index-url https://example.invalid'):
            lock.write_text(content)
            with self.assertRaises(ValueError): installer.verify_wheel(self.root, self.root)
        lock.write_text(original)
        (self.root / 'requirements-indexer.txt').write_text('libclang==17.0.6')
        with self.assertRaises(ValueError): installer.verify_wheel(self.root, self.root)

    def test_existing_destination_never_runs_commands(self):
        with patch.object(installer.platform, 'system', return_value='Linux'), patch.object(installer.platform, 'machine', return_value='x86_64'), patch.object(installer.subprocess, 'run') as run:
            for path in (self.root, self.root / 'dangling'):
                if path != self.root: path.symlink_to(self.root / 'absent')
                with self.assertRaises(ValueError): installer.install(path, self.root)
            run.assert_not_called()

    def test_bad_wheel_does_not_create_destination(self):
        target = self.root / 'new-venv'
        with patch.object(installer.platform, 'system', return_value='Linux'), patch.object(installer.platform, 'machine', return_value='x86_64'), patch.object(installer.subprocess, 'run') as run:
            with self.assertRaises(ValueError): installer.install(target, self.root)
            self.assertFalse(target.exists()); run.assert_not_called()

    def test_environment_removes_python_and_pip_overrides(self):
        with patch.dict(installer.os.environ, {'PYTHONPATH': 'untrusted', 'PIP_INDEX_URL': 'remote', 'VIRTUAL_ENV': 'old', 'PATH': '/bin'}, clear=True):
            self.assertEqual(installer.clean_environment(), {'PATH': '/bin', 'PIP_CONFIG_FILE': installer.os.devnull})
