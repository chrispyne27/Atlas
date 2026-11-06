import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import test_storage_trace_packet as fixtures
from atlas_engine.storage.store import digest, canonical
from atlas_engine.storage.trace_details import DETAIL_LIMITS


class TraceDetailTests(fixtures.TracePacketTests):
    def setUp(self):
        super().setUp()
        self.root = self.fixture.path.parent/'repo'
        self.root.mkdir()
        self.source = self.root/'test.cpp'
        self.source.write_text('first\nsecond\nthird\n')
        self.writer.execute('UPDATE artifact SET content_hash=?', (digest(self.source.read_bytes()),))

    def packet(self, **kwargs):
        kwargs.setdefault('roots', {'repo': self.root})
        return super().packet(**kwargs)

    def test_exact_occurrence_and_evidence_details(self):
        self.writer.execute("INSERT INTO occurrence VALUES ('s','other-target','root','B','repo/test.cpp',3,3,'definition','ev')")
        result = self.packet()
        occurrence = next(o for o in result['occurrences'] if o['entity_id'] == 'root')
        self.assertEqual(occurrence['compilation_id'], 'A')
        self.assertEqual(occurrence['source']['text'], 'first\nsecond\n')
        self.assertEqual(occurrence['source']['expected_hash'], digest(self.source.read_bytes()))
        self.assertTrue(occurrence['source']['hash_verified'])
        self.assertNotIn('other-target', {o['id'] for o in result['occurrences']})
        self.assertEqual(result['evidence'][0]['kind'], 'inferred')
        self.assertLessEqual(result['usage']['source_bytes'], result['limits']['source_bytes'])
        self.assertEqual(result['usage']['bytes'], len(canonical(result).encode()))

    def test_source_failures_and_aggregate_work(self):
        self.source.write_text('changed\n')
        self.assertTrue(all(o['source']['status'] == 'stale' for o in self.packet()['occurrences']))
        self.source.unlink()
        self.assertTrue(all(o['source']['status'] == 'missing' for o in self.packet()['occurrences']))
        self.source.write_text('first\nsecond\nthird\n')
        with patch.dict(DETAIL_LIMITS, source_files=1):
            result = self.packet()
        self.assertEqual(result['usage']['source_files'], 1)
        self.assertIn('budget_omitted', {o['source']['status'] for o in result['occurrences']})
        with patch.dict(DETAIL_LIMITS, source_bytes=4, source_hash_bytes=4):
            result = self.packet()
        self.assertEqual(result['usage']['source_files'], 0)
        with patch.dict(DETAIL_LIMITS, evidence_calls=0):
            result = self.packet()
        self.assertFalse(result['evidence'])
        self.assertTrue(all(r['evidence_details_status'] == 'budget_omitted' for r in result['relationships']))
        with patch.dict(DETAIL_LIMITS, source_calls=0):
            self.assertEqual(self.packet()['usage']['source_files'], 0)

    def test_external_oversized_and_truncated_span(self):
        self.writer.execute("INSERT INTO artifact VALUES ('s','external:/system.h','hash','external')")
        self.writer.execute("UPDATE occurrence SET artifact_path='external:/system.h'")
        self.assertTrue(all(o['source']['status'] == 'external_unavailable' for o in self.packet()['occurrences']))
        self.writer.execute("UPDATE occurrence SET artifact_path='repo/test.cpp',end_line=250")
        self.source.write_text('line\n'*250)
        self.writer.execute('UPDATE artifact SET content_hash=? WHERE path=?', (digest(self.source.read_bytes()), 'repo/test.cpp'))
        result = self.packet()
        self.assertTrue(all(o['source']['span_truncated'] for o in result['occurrences']))
        self.assertTrue(all(o['source']['returned_lines'] == 200 for o in result['occurrences']))
        with self.source.open('wb') as stream:
            stream.truncate(16*1024*1024+1)
        self.assertTrue(all(o['source']['status'] == 'over_limit' for o in self.packet()['occurrences']))

    def test_delivery_budget_omits_whole_source_and_evidence(self):
        self.source.write_text('龍'*2000+'\nsecond\n')
        self.writer.execute('UPDATE artifact SET content_hash=?', (digest(self.source.read_bytes()),))
        self.writer.execute('UPDATE evidence SET details_json=?', (json.dumps({'note':'x'*20000}),))
        before = self.source.read_bytes()
        result = self.packet(max_bytes=9000)
        self.assertLessEqual(len(canonical(result).encode()), 9000)
        self.assertTrue(any('source_byte_limit' in reason for reason in result['omissions']))
        self.assertTrue(any('evidence_byte_limit' in reason for reason in result['omissions']))
        self.assertTrue(all(o['source']['text'] is None for o in result['occurrences']))
        self.assertEqual(before, self.source.read_bytes())

    def test_actual_wal_mutation_rejected(self):
        self.writer.execute('PRAGMA journal_mode=WAL')
        original = self.reader._source_item
        mutated = False
        def change(*args, **kwargs):
            nonlocal mutated
            result = original(*args, **kwargs)
            if not mutated:
                self.writer.execute("UPDATE snapshot SET revision='concurrent-change'")
                mutated = True
            return result
        with patch.object(self.reader, '_source_item', side_effect=change):
            with self.assertRaisesRegex(ValueError, 'Database changed'):
                self.packet()
        self.assertFalse(self.reader.db.in_transaction)

    def test_shared_and_alternative_occurrences_and_configuration(self):
        self.writer.execute("INSERT INTO occurrence VALUES ('s','z-alternate','root','A','repo/test.cpp',3,3,'definition','ev')")
        result = self.packet()
        occurrence = next(o for o in result['occurrences'] if o['entity_id']=='root')
        self.assertEqual(occurrence['id'], 'o')
        self.assertTrue(occurrence['other_variants_observed'])
        self.assertEqual(occurrence['source']['text'], 'first\nsecond\n')
        shared = next(o for o in result['occurrences'] if o['entity_id']=='req')
        self.assertIsNone(shared['compilation_id'])
        self.assertIn('unverified', shared['applicability'])
        other = self.root/'other.cpp';other.write_text('rtos only\n')
        d = self.writer
        d.execute("INSERT INTO snapshot VALUES ('rtos','r','different-rev','rtos','hash','other','test',1,'staging','now')")
        d.execute("INSERT INTO build_target VALUES ('rtos','A','A','test')")
        d.execute('INSERT INTO artifact VALUES (?,?,?,?)', ('rtos','repo/other.cpp',digest(other.read_bytes()),'authored'))
        d.execute("INSERT INTO compilation VALUES ('rtos','A','A','repo/other.cpp','different','[]','parsed')")
        d.execute("INSERT INTO entity VALUES ('rtos','root','symbol','scope','root','RTOS root')")
        d.execute("INSERT INTO evidence VALUES ('rtos','ev','authored','repo/other.cpp',1,'rtos','{}')")
        d.execute("INSERT INTO occurrence VALUES ('rtos','o','root','A','repo/other.cpp',1,1,'definition','ev')")
        other_packet = self.reader.packet(snapshot='rtos',target='A',entity='root',roots={'repo':self.root})
        self.assertEqual(other_packet['snapshot']['configuration_key'], 'rtos')
        self.assertEqual(other_packet['occurrences'][0]['source']['text'], 'rtos only\n')
        self.assertFalse(other_packet['relationships'])
        self.assertEqual(result, self.packet())

    def test_root_escape_and_non_utf8_never_return_source(self):
        outside = self.root.parent/'outside.cpp';outside.write_text('outside')
        self.source.unlink();self.source.symlink_to(outside)
        result = self.packet()
        self.assertTrue(all(o['source']['text'] is None for o in result['occurrences']))
        self.assertTrue(all(o['source']['reason']=='path escaped supplied root' for o in result['occurrences']))
        self.source.unlink();self.source.write_bytes(b'\xff\n')
        self.writer.execute('UPDATE artifact SET content_hash=?', (digest(self.source.read_bytes()),))
        result = self.packet()
        self.assertTrue(all(o['source']['text'] is None for o in result['occurrences']))
        self.assertTrue(all(o['source']['reason']=='source is not UTF-8' for o in result['occurrences']))
        self.assertTrue(all(o['source']['status']=='root_unavailable' for o in self.packet(roots={})['occurrences']))

    def test_high_fanout_node_selection_with_distinct_endpoints(self):
        for i in range(150):
            eid = f'fan{i:03}'
            self.writer.execute('INSERT INTO entity VALUES (?,?,?,?,?,?)', ('s',eid,'symbol','scope',eid,eid))
            self.relation(eid, 'root', eid)
        result = self.packet(max_bytes=256*1024)
        self.assertEqual(len(result['entities']), 50)
        self.assertTrue(any('node_limit' in r for r in result['omissions']))
        self.assertEqual(result, self.packet(max_bytes=256*1024))
        self.assertLessEqual(result['usage']['sql_statements'], result['limits']['sql_statements'])
        self.assertLessEqual(result['usage']['rows'], result['limits']['rows'])
        self.assertLessEqual(result['usage']['bytes'], result['limits']['max_bytes'])

    def test_cli_success_and_structured_budget_error(self):
        args = [sys.executable, '-m', 'atlas_engine.storage.trace_packet', '--database', str(self.fixture.path),
                '--snapshot', 's', '--target', 'A', '--entity', 'root', '--repo-root', str(self.root)]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads(result.stdout)
        self.assertTrue(packet['occurrences'])
        self.assertFalse(packet['context_eligible'])
        failed = subprocess.run(args+['--max-bytes', '1'], capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(json.loads(failed.stdout)['error'], 'packet_budget_too_small')


if __name__ == '__main__':
    unittest.main()
