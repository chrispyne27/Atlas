import unittest
from unittest.mock import patch
from pathlib import Path
import test_storage_engineering as fixtures
from atlas_engine.storage.engineering import import_engineering
from atlas_engine.storage.readiness import assess


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        fixtures.EngineeringImportTests.setUp(self)
        self.path = Path(self.db.execute('PRAGMA database_list').fetchone()[2])
        import_engineering(self.db, self.sid, ['Svc/Health'])

    def check(self, **kw):
        options = dict(snapshot=self.sid, target='build/CMakeFiles/app.dir',
                       components=['Svc/Health'], roots={'repo': self.root, 'build': self.build})
        options.update(kw)
        return assess(self.path, **options)

    def test_pending_parse_blocker_and_read_only(self):
        before = self.path.read_bytes()
        result = self.check()
        self.assertIn('selected_target_parses', result['blocking_codes'])
        self.assertNotIn('engineering_discovery', result['blocking_codes'])
        self.assertEqual(before, self.path.read_bytes())
        self.assertFalse(result['context_eligible'])

    def test_all_parsed_does_not_approve_toolchain_or_requirements(self):
        self.db.execute("UPDATE compilation SET state='parsed'")
        result = self.check()
        self.assertNotIn('selected_target_parses', result['blocking_codes'])
        self.assertIn('toolchain_identity', result['blocking_codes'])
        self.assertIn('publication_contract', result['blocking_codes'])
        self.assertEqual(result['verification']['requirement_satisfaction'], 'not_assessed')
        self.assertIn('candidate', result['relationship_resolution_counts'])

    def test_fresh_check_and_required_engineering_scope(self):
        (self.root / 'Svc/Health/test/ut/New.cpp').write_text('new test')
        result = self.check()
        self.assertIn('recorded_inputs', result['blocking_codes'])
        self.assertIn('engineering_discovery', result['blocking_codes'])
        result = self.check(components=['Svc/CmdDispatcher'])
        detail = next(c['detail'] for c in result['checks'] if c['code'] == 'engineering_discovery')
        self.assertEqual(detail['components']['Svc/CmdDispatcher'], 'not_imported')

    def test_failed_and_excluded_compilations_remain_blocking(self):
        for state in ('failed', 'excluded'):
            self.db.execute('UPDATE compilation SET state=?', (state,))
            self.assertIn('selected_target_parses', self.check()['blocking_codes'])

    def test_other_target_pending_does_not_change_selected_parse_coverage(self):
        self.db.execute("UPDATE compilation SET state='parsed'")
        self.db.execute("INSERT INTO build_target VALUES (?, 'other', 'other', 'test')", (self.sid,))
        self.db.execute("INSERT INTO compilation VALUES (?, 'other', 'other', 'repo/app.cpp', 'other', '[]', 'pending')", (self.sid,))
        self.assertNotIn('selected_target_parses', self.check()['blocking_codes'])

    def test_unknown_scope_and_database_change_rejected(self):
        with self.assertRaises(ValueError): self.check(target='unknown')
        with self.assertRaises(ValueError): self.check(components=[])
        with self.assertRaises(ValueError): self.check(components=['arbitrary/path'])
        from atlas_engine.storage import readiness
        original = readiness.audit
        def changed(*args, **kw):
            result = original(*args, **kw)
            self.db.execute("UPDATE snapshot SET revision='changed'")
            return result
        with patch.object(readiness, 'audit', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'Database changed'):
                self.check()


if __name__ == '__main__': unittest.main()
