import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from atlas_engine.storage.demo import create, SNAPSHOT, TARGET
from atlas_engine.storage.details import DetailInspector


class OfflineDemoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'demo with spaces'
        self.report = create(self.output)
        self.reader = DetailInspector(self.output / 'demo.sqlite'); self.addCleanup(self.reader.close)

    def test_trace_preserves_evidence_and_ambiguity(self):
        scope = dict(snapshot=SNAPSHOT, target=TARGET)
        found = self.reader.page(**scope, operation='lookup', value='Demo.Nominal')
        self.assertEqual(found['items'][0]['id'], 'test')
        for start, end in [('test','helper'), ('helper','value'), ('value','requirement'), ('requirement','alias')]:
            page = self.reader.page(**scope, operation='neighbors', value=start)
            self.assertIn(end, [r['to_entity'] for r in page['items']])
            self.assertTrue(all(r['provenance']=='authored' for r in page['items']))
        first = self.reader.page(**scope, operation='neighbors', value='helper', limit=1)
        last = self.reader.page(**scope, operation='neighbors', value='helper', limit=1, cursor=first['next_cursor'])
        self.assertEqual(last['items'][0]['resolution'], 'unresolved')
        candidate = self.reader.page(**scope, operation='neighbors', value='value')['items'][0]
        self.assertEqual(candidate['resolution'], 'candidate')
        source = self.reader.source(**scope, evidence='demo-evidence-helper', roots={'repo':self.output/'repo'})
        self.assertTrue(source['hash_verified']); self.assertIn('helper()', source['text'])
        (self.output/'repo/demo.cpp').write_text('changed')
        stale = self.reader.source(**scope, evidence='demo-evidence-helper', roots={'repo':self.output/'repo'})
        self.assertEqual(stale['status'], 'stale'); self.assertIsNone(stale['text'])

    def test_no_invented_compilation_execution_or_review(self):
        with sqlite3.connect(self.output/'demo.sqlite') as db:
            self.assertEqual(db.execute('SELECT DISTINCT state FROM compilation').fetchall(), [('pending',)])
            self.assertEqual(db.execute('SELECT state FROM snapshot').fetchone()[0], 'staging')
            for table in ('test_run','test_result','relation_review'):
                self.assertEqual(db.execute('SELECT count(*) FROM '+table).fetchone()[0],0)
            for (data,) in db.execute('SELECT details_json FROM evidence'):
                self.assertTrue(json.loads(data)['synthetic'])

    def test_existing_directory_and_symlink_rejected(self):
        before = (self.output/'demo.sqlite').read_bytes()
        with self.assertRaises(FileExistsError): create(self.output)
        self.assertEqual(before, (self.output/'demo.sqlite').read_bytes())
        link = self.root/'link'; link.symlink_to(self.root/'missing')
        with self.assertRaises(FileExistsError): create(link)

    def test_reproducible_database_and_sources(self):
        other = self.root/'other'; create(other)
        self.assertEqual((self.output/'repo/demo.cpp').read_bytes(), (other/'repo/demo.cpp').read_bytes())
        with sqlite3.connect(self.output/'demo.sqlite') as a, sqlite3.connect(other/'demo.sqlite') as b:
            self.assertEqual(list(a.iterdump()), list(b.iterdump()))
