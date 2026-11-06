import json,unittest
from pathlib import Path
import test_storage_inspect as fixtures
from atlas_engine.storage.details import DetailInspector,DETAIL_BYTES
from atlas_engine.storage.store import digest,canonical

class DetailTests(unittest.TestCase):
    def setUp(self):
        fixtures.InspectionTests.setUp(self)
        self.root=self.path.parent/'repo';self.root.mkdir();self.source=self.root/'test.cpp'
        self.source.write_text('first\nsecond\nthird\n')
        self.writer.execute("UPDATE artifact SET content_hash=?",(digest(self.source.read_bytes()),))
        self.details=DetailInspector(self.path);self.addCleanup(self.details.close)
        self.args=dict(snapshot='s',target='A',evidence='ev')
    def read(self,**kw):return self.details.source(**self.args,roots={'repo':self.root},**kw)

    def test_bounded_verified_span_and_provenance(self):
        r=self.read(start=2,end=2)
        self.assertEqual(r['text'],'second\n');self.assertTrue(r['hash_verified'])
        self.assertEqual(self.details.evidence(**self.args)['evidence']['kind'],'inferred')
        self.assertTrue(r['inspection_only'])

    def test_stale_and_missing_never_return_text(self):
        self.source.write_text('changed\n');r=self.read();self.assertEqual(r['status'],'stale');self.assertIsNone(r['text'])
        self.source.unlink();r=self.read();self.assertEqual(r['status'],'unavailable');self.assertIsNone(r['text'])

    def test_explicit_roots_and_symlink_escape(self):
        r=self.details.source(**self.args,roots={});self.assertEqual(r['status'],'unavailable')
        outside=self.path.parent/'outside.cpp';outside.write_text('secret')
        self.source.unlink();self.source.symlink_to(outside)
        r=self.read();self.assertEqual(r['reason'],'path escaped supplied root');self.assertIsNone(r['text'])

    def test_limits_and_large_evidence(self):
        with self.assertRaises(ValueError):self.read(start=1,end=201)
        self.writer.execute('UPDATE evidence SET details_json=?',(json.dumps({'large':'x'*DETAIL_BYTES}),))
        r=self.details.evidence(**self.args)
        self.assertEqual(r['evidence']['details_status'],'over_limit')
        self.assertLessEqual(len(canonical(r).encode()),DETAIL_BYTES)
        self.source.write_text('x'*(DETAIL_BYTES+1))
        self.writer.execute('UPDATE artifact SET content_hash=?',(digest(self.source.read_bytes()),))
        self.assertEqual(self.read()['status'],'over_limit')

    def test_target_restriction_and_external_source(self):
        self.writer.execute("INSERT INTO evidence VALUES ('s','private','compiler','repo/test.cpp',1,'test','{}')")
        self.writer.execute("INSERT INTO occurrence VALUES ('s','private','root','A','repo/test.cpp',1,1,'definition','private')")
        with self.assertRaisesRegex(ValueError,'not attached'):
            self.details.evidence(snapshot='s',target='B',evidence='private')
        self.writer.execute("INSERT INTO artifact VALUES ('s','external:/tmp/system.h','hash','external')")
        self.writer.execute("UPDATE evidence SET artifact_path='external:/tmp/system.h' WHERE id='ev'")
        self.assertEqual(self.read()['status'],'unavailable')

if __name__=='__main__':unittest.main()
