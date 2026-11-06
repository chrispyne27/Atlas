import unittest
from unittest.mock import patch
import test_storage_inspect as fixtures
from atlas_engine.storage.trace_packet import TracePacketInspector, PacketBudgetError
from atlas_engine.storage.store import canonical


class TracePacketTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.InspectionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.reader = TracePacketInspector(self.fixture.path)
        self.addCleanup(self.reader.close)
        self.writer = self.fixture.writer

    def packet(self, **kwargs):
        return self.reader.packet(**dict(snapshot='s', target='A', entity='root', **kwargs))

    def relation(self, rid, source, endpoint, kind='calls', resolution='resolved'):
        self.writer.execute('INSERT INTO relation VALUES (?,?,?,?,?,?,?,?,?)',
            ('s', rid, source, endpoint, endpoint, kind, resolution, 'A', 'ev'))

    def test_scope_semantics_and_cycle(self):
        self.relation('cycle', 'child', 'root')
        self.relation('candidate-bridge', 'req', 'child')
        result = self.packet()
        self.assertEqual({e['id'] for e in result['relationships']}, {'a', 'b', 'c', 'cycle'})
        self.assertEqual(len(result['entities']), 3)
        candidate = next(e for e in result['relationships'] if e['id'] == 'c')
        self.assertEqual(candidate['traversal'], 'terminal')
        self.assertIn('unverified', candidate['applicability'])
        self.assertEqual(result['unresolved_returned'], 1)
        self.assertTrue(all(e['provenance'] == 'inferred' for e in result['relationships']))
        self.assertEqual(result, self.packet())
        self.assertTrue(result['inspection_only'])
        self.assertFalse(result['context_eligible'])
        self.writer.execute("UPDATE snapshot SET state='ready'")
        self.assertFalse(self.packet()['context_eligible'])

    def test_limits_unicode_and_no_dangling_endpoints(self):
        self.writer.execute("UPDATE entity SET name=?", ('龍'*2048,))
        for i in range(300):
            self.relation(f'fanout{i:04}', 'root', 'child')
        result = self.packet(max_edges=500, max_bytes=18000)
        self.assertLessEqual(len(canonical(result).encode()), 18000)
        self.assertEqual(len(canonical(result).encode()), result['usage']['bytes'])
        self.assertTrue(any('byte_limit' in x for x in result['omissions']))
        ids = {n['id'] for n in result['entities']}
        self.assertTrue(all(e['from_entity'] in ids and (e['to_entity'] is None or e['to_entity'] in ids)
                            for e in result['relationships']))
        rows = self.packet(max_edges=500, max_bytes=256*1024)
        self.assertTrue(any('adjacency_row_limit' in x for x in rows['omissions']))
        self.assertLessEqual(rows['usage']['rows'], 1000)
        for options, reason in [({'max_depth':0}, 'depth_limit'),
                                ({'max_nodes':1}, 'node_limit'), ({'max_edges':1}, 'edge_limit')]:
            self.assertTrue(any(reason in x for x in self.packet(**options)['omissions']))
        with self.assertRaises(PacketBudgetError) as raised:
            self.packet(max_bytes=1)
        self.assertEqual(raised.exception.response['error'], 'packet_budget_too_small')

    def test_request_validation_readonly_and_change_rejection(self):
        before = self.fixture.path.read_bytes()
        self.packet(direction='both')
        self.assertEqual(before, self.fixture.path.read_bytes())
        for options in [dict(kinds=['VERIFIES']), dict(max_nodes=True), dict(max_depth=4), dict(direction='sideways')]:
            with self.assertRaises(ValueError):
                self.packet(**options)
        with self.assertRaises(TypeError):
            self.packet(unknown=True)
        with patch.object(self.reader, '_version', side_effect=['before', 'after']):
            with self.assertRaisesRegex(ValueError, 'Database changed'):
                self.packet()
        self.assertFalse(self.reader.db.in_transaction)

    def test_aggregate_limits_and_candidate_then_resolved_path(self):
        from atlas_engine.storage.trace_packet import WORK_LIMITS
        with patch.dict(WORK_LIMITS, rows=2):
            result = self.packet()
        self.assertEqual(result['usage']['rows'], 2)
        self.assertTrue(any('aggregate_row_limit' in x for x in result['omissions']))
        with patch.dict(WORK_LIMITS, sql_statements=4):
            with self.assertRaisesRegex(ValueError, 'statement budget'):
                self.packet()
        with patch.dict(WORK_LIMITS, sql_seconds=0):
            # Force enough VM operations to invoke the progress handler.
            for i in range(300):
                self.relation(f'work{i}', 'root', 'child')
            with self.assertRaisesRegex(ValueError, 'work/time budget'):
                self.packet()
        self.writer.execute("DELETE FROM relation WHERE id LIKE 'work%'")
        self.relation('requirement-path', 'child', 'req')
        self.relation('after-resolved', 'req', 'root')
        self.assertIn('after-resolved', {e['id'] for e in self.packet(max_edges=500)['relationships']})

    def test_unknown_kind_and_configuration_isolation(self):
        self.relation('unknown', 'root', 'child', kind='future_relation')
        result = self.packet()
        self.assertNotIn('unknown', {e['id'] for e in result['relationships']})
        self.assertTrue(any('relationship_kind_filtered' in x for x in result['omissions']))
        self.writer.execute("INSERT INTO snapshot VALUES ('other','r','other-rev','rtos','hash','gcc','test',1,'staging','now')")
        self.writer.execute("INSERT INTO build_target VALUES ('other','A','A','test')")
        self.writer.execute("INSERT INTO entity VALUES ('other','root','symbol','scope','root','different')")
        self.assertEqual(self.packet()['snapshot']['configuration_key'], 'linux')
        self.assertNotIn('hidden', {e['id'] for e in result['relationships']})


if __name__ == '__main__':
    unittest.main()
