import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('offline_preflight', Path(__file__).resolve().parents[2] / 'scripts/offline-preflight.py')
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


class OfflinePreflightTests(unittest.TestCase):
    def facts(self):
        return {'system': 'Linux', 'architecture': 'x86_64',
                'os': {'ID': 'rhel', 'VERSION_ID': '9.4'}, 'python_minor': [3, 12],
                'sqlite': {'status': 'observed'}, 'assets': {'html': True},
                'firefox_path': '/usr/bin/firefox', 'libclang': {'version': '18.1.1'},
                'parser_pin': '18.1.1', 'venv': True, 'pip': True}

    def test_matching_observations_never_qualify_host(self):
        result = preflight.assess(self.facts(), 'indexer')
        self.assertEqual(result['status'], 'requires_validation')
        self.assertFalse(result['qualified'])
        self.assertTrue(result['pending_validation'])

    def test_platform_mismatch_blocks(self):
        for key, value in [('architecture', 'aarch64'), ('system', 'Windows'),
                           ('os', {'ID': 'ubuntu', 'VERSION_ID': '24.04'}),
                           ('os', {'ID': 'rhel', 'VERSION_ID': '90'}), ('os', {'error': 'OSError'})]:
            facts = self.facts(); facts[key] = value
            with self.subTest(key=key, value=value):
                self.assertEqual(preflight.assess(facts, 'indexer')['status'], 'blocked')

    def test_viewer_does_not_require_parser_or_install_tools(self):
        facts = self.facts(); facts.update(libclang={'version': None}, parser_pin=None, venv=False, pip=False)
        self.assertEqual(preflight.assess(facts, 'viewer')['blockers'], [])
        self.assertTrue(preflight.assess(facts, 'indexer')['blockers'])

    def test_wrong_parser_and_missing_capabilities(self):
        for key, value in [('libclang', {'version': '17.0.6'}),
                           ('sqlite', {'status': 'blocked'}), ('assets', {'html': False})]:
            facts = self.facts(); facts[key] = value
            self.assertTrue(preflight.assess(facts, 'indexer')['blockers'])

    def test_default_python_and_missing_firefox_are_unqualified_not_incompatible(self):
        facts = self.facts(); facts.update(python_minor=[3, 9], firefox_path=None)
        result = preflight.assess(facts, 'viewer')
        self.assertEqual(result['blockers'], [])
        self.assertTrue(any('qualify separately' in item for item in result['pending_validation']))
        self.assertTrue(any('not found on PATH' in item for item in result['pending_validation']))

    def test_os_release_is_data_and_rejects_duplicate_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'os-release'
            path.write_text('ID=rhel\nVERSION_ID="9.4"\nPRETTY_NAME="$(touch /never-run)"\n')
            self.assertEqual(preflight.read_os_release(path)['PRETTY_NAME'], '$(touch /never-run)')
            path.write_text('ID=rhel\nID=ubuntu\n')
            with self.assertRaises(ValueError):
                preflight.read_os_release(path)
            path.write_text('X' * 65537)
            with self.assertRaises(ValueError):
                preflight.read_os_release(path)

    def test_sqlite_probe_uses_only_memory(self):
        import sqlite3
        original = sqlite3.connect
        with patch.object(sqlite3, 'connect', wraps=original) as connect:
            self.assertEqual(preflight.sqlite_probe()['status'], 'observed')
            connect.assert_called_once_with(':memory:')

    def test_assessment_does_not_mutate_observations(self):
        facts = self.facts(); before = copy.deepcopy(facts)
        preflight.assess(facts, 'indexer')
        self.assertEqual(facts, before)
