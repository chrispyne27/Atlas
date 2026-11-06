import unittest
from unittest.mock import patch
import test_storage_details as fixtures
from atlas_engine.storage import freshness


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        fixtures.DetailTests.setUp(self)

    def audit(self, **kwargs):
        return freshness.audit(self.path, snapshot='s', roots={'repo': self.root}, **kwargs)

    def test_matching_is_read_only_and_not_context_approval(self):
        before = self.path.read_bytes()
        result = self.audit()
        self.assertEqual(result['status'], 'recorded_inputs_match')
        self.assertFalse(result['context_eligible'])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(result['snapshot']['state'], 'staging')

    def test_changed_and_missing(self):
        self.source.write_text('changed')
        self.assertEqual(self.audit()['counts']['changed'], 1)
        self.source.unlink()
        self.assertEqual(self.audit()['status'], 'stale')
        self.assertEqual(self.audit()['counts']['missing'], 1)

    def test_external_and_unsupplied_root_are_not_fresh(self):
        result = freshness.audit(self.path, snapshot='s', roots={})
        self.assertEqual(result['status'], 'incomplete')
        self.writer.execute("INSERT INTO artifact VALUES ('s','external:/tmp/private','hash','external')")
        self.assertEqual(self.audit()['counts']['not_checked'], 1)
        self.assertEqual(self.audit()['status'], 'incomplete')

    def test_escape_and_nonregular(self):
        outside = self.path.parent / 'outside'; outside.write_text('private')
        self.source.unlink(); self.source.symlink_to(outside)
        self.assertEqual(self.audit()['counts']['outside_root'], 1)
        self.source.unlink(); self.source.mkdir()
        self.assertEqual(self.audit()['counts']['not_regular'], 1)

    def test_budgets_report_incomplete(self):
        self.assertEqual(self.audit(max_file_bytes=1)['status'], 'incomplete')
        self.assertEqual(self.audit(max_total_bytes=1)['bytes_hashed'], 0)
        self.writer.execute("INSERT INTO artifact VALUES ('s','repo/z.cpp','hash','authored')")
        result = self.audit(max_artifacts=1)
        self.assertTrue(result['more_artifacts']); self.assertEqual(result['status'], 'incomplete')
        with self.assertRaises(ValueError): self.audit(max_artifacts=0)

    def test_change_after_hash_is_detected(self):
        original = freshness.hash_input
        def change(path, allowance):
            result = original(path, allowance)
            path.write_text('a later edit')
            return result
        with patch.object(freshness, 'hash_input', side_effect=change):
            result = self.audit()
        self.assertEqual(result['status'], 'stale')
        self.assertEqual(result['changed_after_check_count'], 1)

    def test_unknown_snapshot_and_new_files(self):
        with self.assertRaises(ValueError):
            freshness.audit(self.path, snapshot='unknown', roots={})
        (self.root / 'new-requirements.md').write_text('new requirement')
        result = self.audit()
        self.assertEqual(result['status'], 'recorded_inputs_match')
        self.assertFalse(result['context_eligible'])
        self.assertIn('newly added files', result['limitations'][0])


if __name__ == '__main__': unittest.main()
