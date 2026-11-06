import json
import tempfile
import unittest
from pathlib import Path
from atlas_engine.storage import connect, import_manifest
from atlas_engine.storage.engineering import annotations, import_engineering


class EngineeringImportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'repo'; self.build=self.root/'build'; self.build.mkdir(parents=True)
        source=self.root/'app.cpp'; source.write_text('int app;')
        manifest=self.build/'compile_commands.json'
        manifest.write_text(json.dumps([dict(directory=str(self.build),file=str(source),output='CMakeFiles/app.dir/app.cpp.o',arguments=['c++','-c',str(source)])]))
        self.db=connect(Path(self.temp.name)/'db.sqlite'); self.addCleanup(self.db.close)
        self.sid=import_manifest(self.db,repository=self.root,build_root=self.build,compilation_database=manifest,
            repository_id='test',source_uri='test',revision='test',configuration_key='test',toolchain_fingerprint='test',targets=['app'])['snapshot_id']
        for component in ['Health','CmdDispatcher']:
            folder=self.root/'Svc'/component
            (folder/'docs').mkdir(parents=True); (folder/'test/ut').mkdir(parents=True)
            (folder/'docs/sdd.md').write_text('Requirement | Description | Verification Method\nHTH-001 | Shall do something | Unit Test\n')
            (folder/'test/ut/Test.cpp').write_text('REQUIREMENT("HTH-001");\nREQUIREMENT("ISF-HTH-001");\n')

    def test_authored_links_candidate_aliases_and_scoped_identity(self):
        result=import_engineering(self.db,self.sid,['Svc/Health','Svc/CmdDispatcher'])
        self.assertEqual(result['definitions'],2)
        self.assertEqual(result['annotations'],4)
        self.assertEqual(result['candidate_aliases'],2)
        self.assertEqual(result['reference_only_requirements'],2)
        self.assertEqual(self.db.execute("SELECT count(*) FROM entity WHERE external_key='HTH-001'").fetchone()[0],2)
        self.assertEqual(self.db.execute("SELECT count(*) FROM relation WHERE kind='candidate_alias' AND resolution='candidate'").fetchone()[0],2)
        self.assertEqual(self.db.execute('SELECT count(*) FROM relation_review').fetchone()[0],0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM test_run').fetchone()[0],0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM relation WHERE kind IN ('implements','verifies')").fetchone()[0],0)
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertEqual(self.db.execute('SELECT state FROM snapshot').fetchone()[0],'staging')

    def test_annotation_lexer_excludes_comments_and_strings(self):
        source='''// REQUIREMENT("FAKE-001");
/* REQUIREMENT("FAKE-002"); */
const char* x = "REQUIREMENT(\\"FAKE-003\\")";
const char* r = R"tag(
 REQUIREMENT("FAKE-004");
)tag";
 REQUIREMENT("REAL-001");
'''
        self.assertEqual(list(annotations(source)),[(7,'REAL-001')])

    def test_duplicate_import_fails_without_new_rows(self):
        import_engineering(self.db,self.sid,['Svc/Health'])
        before=self.db.execute('SELECT count(*) FROM evidence').fetchone()[0]
        with self.assertRaisesRegex(ValueError,'already imported'):
            import_engineering(self.db,self.sid,['Svc/CmdDispatcher','Svc/Health'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM evidence').fetchone()[0],before)
        self.assertEqual(self.db.execute("SELECT count(*) FROM evidence WHERE id='engineering:Svc/CmdDispatcher'").fetchone()[0],0)

    def test_duplicate_definition_rolls_back_everything(self):
        doc=self.root/'Svc/Health/docs/sdd.md'
        doc.write_text(doc.read_text()+'HTH-001 | conflicting text | Inspection\n')
        with self.assertRaisesRegex(ValueError,'Duplicate requirement'):
            import_engineering(self.db,self.sid,['Svc/Health'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM entity').fetchone()[0],0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM artifact WHERE path LIKE '%sdd.md'").fetchone()[0],0)

    def test_stale_inputs_and_ready_snapshot_rejected(self):
        import_engineering(self.db,self.sid,['Svc/Health'])
        doc=self.root/'Svc/Health/docs/sdd.md'; doc.write_text(doc.read_text()+'\nchanged')
        with self.assertRaisesRegex(ValueError,'Stale snapshot'):
            import_engineering(self.db,self.sid,['Svc/CmdDispatcher'])
        self.db.execute("UPDATE snapshot SET state='ready'")
        with self.assertRaisesRegex(ValueError,'staging'):
            import_engineering(self.db,self.sid,['Svc/CmdDispatcher'])

if __name__=='__main__': unittest.main()
