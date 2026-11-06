import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from atlas_engine.storage import connect, import_manifest
from atlas_engine.storage.compiler import parse_compilation, parsing_arguments
from atlas_engine.storage import compiler


class CompilerStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'repo'; self.build=self.root/'build'; self.build.mkdir(parents=True)
        self.header=self.root/'api.hpp'
        self.header.write_text('struct Base { virtual int run() = 0; };\nint helper();\n')
        self.source=self.root/'app.cpp'
        self.source.write_text('#include "api.hpp"\nint helper() { return VALUE; }\nint work(Base& b) { return helper() + b.run(); }\n')
        self.manifest=self.build/'compile_commands.json'
        self.manifest.write_text(json.dumps([dict(directory=str(self.build),file=str(self.source),
            output='CMakeFiles/app.dir/app.cpp.o',arguments=['c++','-std=c++14',f'-DVALUE={v}','-c',str(self.source)]) for v in (1,2)]))
        self.db=connect(Path(self.temp.name)/'store.sqlite'); self.addCleanup(self.db.close)
        result=import_manifest(self.db,repository=self.root,build_root=self.build,compilation_database=self.manifest,
            repository_id='test',source_uri='test',revision='test',configuration_key='test',toolchain_fingerprint='test',targets=['app'])
        self.sid=result['snapshot_id']
        self.ids=[r[0] for r in self.db.execute('SELECT id FROM compilation ORDER BY id')]

    def test_variants_spans_direct_and_virtual_calls(self):
        for cid in self.ids: parse_compilation(self.db,self.sid,cid)
        helper=self.db.execute("SELECT id FROM entity WHERE name='helper'").fetchone()[0]
        self.assertEqual(self.db.execute("SELECT count(DISTINCT compilation_id) FROM occurrence WHERE entity_id=? AND role='definition'",(helper,)).fetchone()[0],2)
        self.assertEqual(self.db.execute("SELECT count(*) FROM relation WHERE resolution='resolved'").fetchone()[0],2)
        self.assertEqual(self.db.execute("SELECT count(*) FROM relation WHERE resolution='unresolved'").fetchone()[0],2)
        self.assertEqual(self.db.execute("SELECT count(*) FROM compilation_input WHERE artifact_path='repo/api.hpp'").fetchone()[0],2)
        self.assertEqual(self.db.execute('SELECT state FROM snapshot').fetchone()[0],'staging')
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(),[])
        with self.assertRaisesRegex(ValueError,'Only pending'):
            parse_compilation(self.db,self.sid,self.ids[0])

    def test_header_change_rejects_next_parse(self):
        parse_compilation(self.db,self.sid,self.ids[0])
        before=self.db.execute('SELECT count(*) FROM occurrence').fetchone()[0]
        self.header.write_text('int helper(); // changed\n')
        with self.assertRaisesRegex(ValueError,'Stale snapshot input'):
            parse_compilation(self.db,self.sid,self.ids[1])
        self.assertEqual(self.db.execute('SELECT count(*) FROM occurrence').fetchone()[0],before)
        self.assertEqual(self.db.execute('SELECT state FROM compilation WHERE id=?',(self.ids[1],)).fetchone()[0],'failed')

    def test_compiler_error_retains_diagnostic_without_graph(self):
        # A new header is not known at manifest-import time; compiler failure is real.
        self.header.write_text('this is invalid c++ syntax;\n')
        with self.assertRaisesRegex(ValueError,'Compiler diagnostics'):
            parse_compilation(self.db,self.sid,self.ids[0])
        self.assertEqual(self.db.execute('SELECT count(*) FROM occurrence').fetchone()[0],0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM evidence WHERE id LIKE '%:failure'").fetchone()[0],1)

    def test_mutation_during_parse_rolls_back(self):
        original=compiler.file_hash
        reads=0
        def changing(path):
            nonlocal reads
            if path==self.header:
                reads+=1
                if reads==2: self.header.write_text('int different;\n')
            return original(path)
        with patch.object(compiler,'file_hash',side_effect=changing):
            with self.assertRaisesRegex(ValueError,'Dependency changed'):
                parse_compilation(self.db,self.sid,self.ids[0])
        self.assertEqual(self.db.execute('SELECT count(*) FROM entity').fetchone()[0],0)

    def test_unsupported_driver_options_rejected(self):
        for arg in ['-fplugin=bad.so','-Xclang',';','@flags','-Wl,evil']:
            with self.assertRaises(ValueError):
                parsing_arguments(['c++',arg],self.build,self.source,[])

if __name__=='__main__': unittest.main()
