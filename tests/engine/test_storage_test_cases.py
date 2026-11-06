import json,tempfile,unittest
from pathlib import Path
from atlas_engine.storage import connect,import_manifest
from atlas_engine.storage.compiler import parse_compilation
from atlas_engine.storage.engineering import import_engineering
from atlas_engine.storage.annotation_links import link_annotations
from atlas_engine.storage.test_cases import map_test_cases,declarations

class TestCaseMappingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)/'repo';build=root/'build';build.mkdir(parents=True)
        comp=root/'Svc/Health';(comp/'docs').mkdir(parents=True);(comp/'test/ut').mkdir(parents=True)
        (comp/'docs/sdd.md').write_text('HTH-001 | Shall work | Unit Test\n')
        # Minimal macro expansion tests the adapter; upstream F Prime tests use real GoogleTest.
        (root/'macros.hpp').write_text('#define REQUIREMENT(x) ((void)0)\n#define TEST(s,n) class s##_##n##_Test { public: void TestBody(); }; void s##_##n##_Test::TestBody()\n')
        source=comp/'test/ut/Cases.cpp';source.write_text('#include "macros.hpp"\nvoid helper() { REQUIREMENT("HTH-001"); }\nTEST(Suite, Case) { helper(); }\n#if 0\nTEST(Suite, DisabledSource) {}\n#endif\n')
        manifest=build/'compile_commands.json';manifest.write_text(json.dumps([dict(directory=str(build),file=str(source),output=f'CMakeFiles/{t}.dir/Cases.cpp.o',arguments=['c++','-I'+str(root),'-c',str(source)]) for t in ['A','B']]))
        self.db=connect(Path(self.temp.name)/'db');self.addCleanup(self.db.close)
        self.sid=import_manifest(self.db,repository=root,build_root=build,compilation_database=manifest,repository_id='r',source_uri='r',revision='r',configuration_key='c',toolchain_fingerprint='t',targets=['A','B'])['snapshot_id']
        self.ids=[r[0] for r in self.db.execute('SELECT id FROM compilation ORDER BY id')]
        for cid in self.ids:parse_compilation(self.db,self.sid,cid)
        import_engineering(self.db,self.sid,['Svc/Health'])
        for cid in self.ids:link_annotations(self.db,self.sid,cid)

    def test_wrapper_case_and_target_bound_helper(self):
        result=map_test_cases(self.db,self.sid,self.ids[0])
        self.assertEqual((result['declared'],result['mapped'],result['unmatched'],result['helper_links']),(2,1,1,1))
        self.assertEqual(self.db.execute('SELECT count(*) FROM test_run').fetchone()[0],0)
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(),[])
        with self.assertRaisesRegex(ValueError,'already mapped'):map_test_cases(self.db,self.sid,self.ids[0])

    def test_ambiguous_wrapper_creates_no_call_link(self):
        row=list(self.db.execute("SELECT o.* FROM occurrence o JOIN entity e ON e.snapshot_id=o.snapshot_id AND e.id=o.entity_id WHERE o.compilation_id=? AND o.role='definition' AND e.name='Suite_Case_Test::TestBody'",(self.ids[0],)).fetchone());row[1]='ambiguous'
        self.db.execute('INSERT INTO occurrence VALUES (?,?,?,?,?,?,?,?,?)',row)
        result=map_test_cases(self.db,self.sid,self.ids[0])
        self.assertEqual((result['ambiguous'],result['helper_links']),(1,0))

    def test_comments_and_strings_are_not_cases(self):
        self.assertEqual(list(declarations('// TEST(Fake, One)\n"TEST(Fake, Two)";\nTEST(Real, Case) {}')),[(3,'Real','Case')])

if __name__=='__main__':unittest.main()
