import unittest
from unittest.mock import patch
import test_storage_details as fixtures
from atlas_engine.storage.freshness import audit
from atlas_engine.storage.store import digest
from atlas_engine.storage.external_roots import ExternalRoots, mapping_argument


class ExternalRootTests(unittest.TestCase):
    def setUp(self):
        fixtures.DetailTests.setUp(self)
        self.sdk = self.path.parent / 'sdk'; self.sdk.mkdir()
        self.header = self.sdk / 'message.h'; self.header.write_text('struct Message { int value; };')
        self.key = 'external:/recorded/sdk/message.h'
        self.writer.execute('INSERT INTO artifact VALUES (?,?,?,?)',
                            ('s', self.key, digest(self.header.read_bytes()), 'external'))

    def read(self, mappings=(), **kwargs):
        return audit(self.path, snapshot='s', roots={'repo': self.root}, external_roots=mappings, **kwargs)

    def test_unmapped_is_not_read_and_mapped_relocation_matches(self):
        from atlas_engine.storage import freshness
        with patch.object(freshness, 'hash_input', wraps=freshness.hash_input) as hashed:
            result = self.read()
        self.assertEqual(result['external_inputs']['counts'], {'not_checked': 1})
        self.assertEqual([c.args[0] for c in hashed.call_args_list], [self.source])
        before = self.path.read_bytes()
        result = self.read([('/recorded/sdk', self.sdk)])
        self.assertEqual(result['status'], 'recorded_inputs_match')
        self.assertEqual(result['external_inputs']['counts'], {'matched': 1})
        self.assertFalse(result['context_eligible'])
        self.assertEqual(before, self.path.read_bytes())

    def test_changed_missing_and_budgets(self):
        mapped = [('/recorded/sdk', self.sdk)]
        self.assertEqual(self.read(mapped, max_file_bytes=1)['status'], 'incomplete')
        self.header.write_text('different version')
        self.assertEqual(self.read(mapped)['status'], 'stale')
        self.header.unlink()
        self.assertEqual(self.read(mapped)['external_inputs']['counts'], {'missing': 1})

    def test_symlink_escape_never_hashed(self):
        outside = self.path.parent / 'secret'; outside.write_text('private')
        self.header.unlink(); self.header.symlink_to(outside)
        result = self.read([('/recorded/sdk', self.sdk)])
        self.assertEqual(result['external_inputs']['counts'], {'outside_root': 1})

    def test_traversal_and_prefix_lookalikes_not_mapped(self):
        for key in ['external:/recorded/sdk/../secret', 'external:/recorded/sdk-other/message.h',
                    'external:relative/message.h']:
            self.writer.execute('UPDATE artifact SET path=? WHERE path=?', (key, self.key)); self.key = key
            self.assertEqual(self.read([('/recorded/sdk', self.sdk)])['external_inputs']['counts'], {'not_checked': 1})

    def test_invalid_and_overbroad_mappings(self):
        for prefix in ['/', 'relative', '/recorded/../sdk', '/recorded//sdk']:
            with self.assertRaises(ValueError): ExternalRoots([(prefix, self.sdk)])
        with self.assertRaises(ValueError): ExternalRoots([('/sdk', '/')])
        with self.assertRaises(ValueError): ExternalRoots([('/sdk', self.sdk)] * 2)
        with self.assertRaises(ValueError): ExternalRoots([('/sdk', self.sdk)] * 17)
        with self.assertRaises(ValueError): mapping_argument('missing separator')

    def test_longest_prefix_and_explicit_nested_mapping(self):
        alternate = self.path.parent / 'alternate'; alternate.mkdir()
        policy = ExternalRoots([('/recorded', alternate), ('/recorded/sdk', self.sdk)])
        self.assertEqual(policy.locate(self.key), (self.header, self.sdk))
        self.assertEqual(mapping_argument('/recorded/sdk=' + str(self.sdk)), ('/recorded/sdk', str(self.sdk)))


if __name__ == '__main__': unittest.main()
