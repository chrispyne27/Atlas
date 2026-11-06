import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_storage_engineering as fixtures
from atlas_engine.storage import engineering, membership
from atlas_engine.storage.freshness import audit


class MembershipTests(unittest.TestCase):
    def setUp(self):
        fixtures.EngineeringImportTests.setUp(self)
        self.path = Path(self.db.execute('PRAGMA database_list').fetchone()[2])
        self.test_dir = self.root / 'Svc/Health/test/ut'

    def check(self):
        return audit(self.path, snapshot=self.sid, roots={'repo': self.root, 'build': self.build})

    def test_capture_import_and_unchanged_audit(self):
        engineering.import_engineering(self.db, self.sid, ['Svc/Health'])
        result = self.check()
        self.assertEqual(result['status'], 'recorded_inputs_match')
        self.assertEqual(result['engineering_directory_membership'][0]['status'], 'matched')
        self.assertFalse(result['context_eligible'])

    def test_new_test_detected_without_changing_old_files(self):
        engineering.import_engineering(self.db, self.sid, ['Svc/Health'])
        (self.test_dir / 'NewTest.cpp').write_text('REQUIREMENT("HTH-001");')
        result = self.check()
        self.assertEqual(result['status'], 'stale')
        self.assertNotIn('changed', result['counts'])
        self.assertEqual(result['engineering_directory_membership'][0]['status'], 'changed')

    def test_new_requirement_document_and_removed_directory(self):
        engineering.import_engineering(self.db, self.sid, ['Svc/Health'])
        p = self.root / 'Svc/Health/docs/additional.md'; p.write_text('new requirements')
        self.assertEqual(self.check()['status'], 'stale')
        p.unlink()
        (self.test_dir / 'Test.cpp').unlink(); self.test_dir.rmdir()
        self.assertEqual(self.check()['engineering_directory_membership'][0]['status'], 'missing_directory_or_member')

    def test_old_snapshot_is_unknown_not_silently_backfilled(self):
        engineering.import_engineering(self.db, self.sid, ['Svc/Health'])
        marker = self.db.execute("SELECT details_json FROM evidence WHERE id='engineering:Svc/Health'").fetchone()[0]
        data = json.loads(marker); del data['discovery']
        self.db.execute("UPDATE evidence SET details_json=? WHERE id='engineering:Svc/Health'", (json.dumps(data),))
        result = self.check()
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['engineering_directory_membership'][0]['status'], 'not_recorded')

    def test_mid_import_addition_rolls_back(self):
        original = engineering.capture; calls = 0
        def changing(root, component):
            nonlocal calls
            calls += 1
            if calls == 2:
                (self.test_dir / 'Added.cpp').write_text('new test')
            return original(root, component)
        with patch.object(engineering, 'capture', side_effect=changing):
            with self.assertRaisesRegex(ValueError, 'membership changed'):
                engineering.import_engineering(self.db, self.sid, ['Svc/Health'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM entity').fetchone()[0], 0)

    def test_bounded_discovery_and_escape(self):
        with patch.object(membership, 'MAX_ENTRIES', 0):
            with self.assertRaisesRegex(ValueError, 'budget'):
                membership.capture(self.root, 'Svc/Health')
        outside = self.root.parent / 'secret.cpp'; outside.write_text('secret')
        (self.test_dir / 'Escaped.cpp').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'escaped'):
            membership.capture(self.root, 'Svc/Health')

    def test_mid_audit_addition_and_unselected_files(self):
        engineering.import_engineering(self.db, self.sid, ['Svc/Health'])
        (self.test_dir / 'notes.txt').write_text('not selected by adapter')
        self.assertEqual(self.check()['status'], 'recorded_inputs_match')
        from atlas_engine.storage import freshness
        original = freshness.hash_input
        def changing(path, allowance):
            (self.test_dir / 'Added.cpp').write_text('new test')
            return original(path, allowance)
        with patch.object(freshness, 'hash_input', side_effect=changing):
            self.assertEqual(self.check()['status'], 'stale')


if __name__ == '__main__': unittest.main()
