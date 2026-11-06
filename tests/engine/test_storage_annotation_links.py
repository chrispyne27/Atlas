import json
import tempfile
import unittest
from pathlib import Path
from atlas_engine.storage import connect, import_manifest
from atlas_engine.storage.compiler import parse_compilation
from atlas_engine.storage.engineering import import_engineering
from atlas_engine.storage.annotation_links import link_annotations


class AnnotationLinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'repo'; self.build=self.root/'build'; self.build.mkdir(parents=True)
        comp=self.root/'Svc/Health'; (comp/'docs').mkdir(parents=True); (comp/'test/ut').mkdir(parents=True)
        (comp/'docs/sdd.md').write_text('HTH-001 | Shall work | Unit Test\nHTH-002 | Shall also work | Unit Test\n')
        self.source=comp/'test/ut/Tester.cpp'
        self.source.write_text('''#define REQUIREMENT(x) ((void)0)
void helper() {
 REQUIREMENT("HTH-001");
}
#if 0
REQUIREMENT("HTH-002");
#endif
''')
        manifest=self.build/'compile_commands.json'
        manifest.write_text(json.dumps([dict(directory=str(self.build),file=str(self.source),output='CMakeFiles/tests.dir/Tester.cpp.o',arguments=['c++',f'-DVARIANT={v}','-c',str(self.source)]) for v in (1,2)]))
        self.db=connect(Path(self.tmp.name)/'store.sqlite'); self.addCleanup(self.db.close)
        self.sid=import_manifest(self.db,repository=self.root,build_root=self.build,compilation_database=manifest,repository_id='r',source_uri='r',revision='r',configuration_key='c',toolchain_fingerprint='t',targets=['tests'])['snapshot_id']
        self.ids=[r[0] for r in self.db.execute('SELECT id FROM compilation ORDER BY id')]
        for cid in self.ids: parse_compilation(self.db,self.sid,cid)
        import_engineering(self.db,self.sid,['Svc/Health'])

    def test_unique_and_unmatched_preserved_per_compilation(self):
        for cid in self.ids:
            result=link_annotations(self.db,self.sid,cid)
            self.assertEqual((result['matched'],result['unmatched'],result['ambiguous']),(1,1,0))
        self.assertEqual(self.db.execute("SELECT count(DISTINCT compilation_id) FROM relation WHERE kind='has_requirement_annotation'").fetchone()[0],2)
        self.assertEqual(self.db.execute("SELECT count(*) FROM relation WHERE kind='annotates_requirement'").fetchone()[0],2)
        self.assertEqual(self.db.execute('SELECT count(*) FROM relation_review').fetchone()[0],0)
        for value, in self.db.execute("SELECT details_json FROM evidence WHERE producer='annotation-containment-1' AND line IS NOT NULL"):
            self.assertEqual(json.loads(value)['annotation_activation'],'not established')
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_ambiguous_spans_do_not_create_links(self):
        row=self.db.execute("SELECT * FROM occurrence WHERE compilation_id=? AND role='definition'",(self.ids[0],)).fetchone()
        duplicate=list(row); duplicate[1]='overlapping-definition'
        self.db.execute('INSERT INTO occurrence VALUES (?,?,?,?,?,?,?,?,?)',duplicate)
        result=link_annotations(self.db,self.sid,self.ids[0])
        self.assertEqual((result['ambiguous'],result['matched']),(1,0))
        self.assertEqual(self.db.execute("SELECT count(*) FROM relation WHERE kind='has_requirement_annotation'").fetchone()[0],0)

    def test_stale_source_rolls_back_and_duplicate_is_rejected(self):
        link_annotations(self.db,self.sid,self.ids[0])
        with self.assertRaisesRegex(ValueError,'already recorded'):
            link_annotations(self.db,self.sid,self.ids[0])
        self.source.write_text(self.source.read_text()+'// changed\n')
        with self.assertRaisesRegex(ValueError,'Stale snapshot'):
            link_annotations(self.db,self.sid,self.ids[1])
        self.assertEqual(self.db.execute('SELECT count(*) FROM evidence WHERE id=?',('annotation-links:'+self.ids[1],)).fetchone()[0],0)

    def test_unparsed_or_ready_scope_rejected(self):
        self.db.execute("UPDATE compilation SET state='pending' WHERE id=?",(self.ids[0],))
        with self.assertRaisesRegex(ValueError,'parsed compilation'):
            link_annotations(self.db,self.sid,self.ids[0])
        self.db.execute("UPDATE snapshot SET state='ready'")
        with self.assertRaisesRegex(ValueError,'staging snapshot'):
            link_annotations(self.db,self.sid,self.ids[1])

if __name__=='__main__': unittest.main()
