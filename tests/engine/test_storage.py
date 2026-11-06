import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from atlas_engine.storage import connect, import_manifest
from atlas_engine.storage import store


class ManifestImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.build = self.root / 'build'
        self.build.mkdir(parents=True)
        self.source = self.root / 'shared.cpp'
        self.source.write_text('int value() { return 1; }\n')
        self.manifest = self.build / 'compile_commands.json'
        self.path = Path(self.temp.name) / 'atlas.sqlite'
        self.db = connect(self.path)
        self.addCleanup(self.db.close)
        self.options = dict(repository=self.root,build_root=self.build,
            compilation_database=self.manifest,repository_id='fixture',source_uri='local:fixture',
            revision='fixture-revision',configuration_key='linux',toolchain_fingerprint='gcc-test',targets=['A','B'])

    def entry(self, target='A', define='1', source=None):
        return dict(directory=str(self.build),file=str(source or self.source),
            output=f'CMakeFiles/{target}.dir/shared.cpp.o',
            arguments=['c++',f'-DVALUE={define}','-c',str(source or self.source)])

    def write(self, entries):
        self.manifest.write_text(json.dumps(entries))

    def test_identity_dedup_and_staging(self):
        self.write([self.entry(),self.entry(),self.entry(define='2'),self.entry('B')])
        result = import_manifest(self.db,**self.options)
        self.assertEqual(result['compilations'],3)
        self.assertEqual(result['duplicate_entries'],1)
        self.assertEqual(result['state'],'staging')
        self.assertEqual(self.db.execute('SELECT count(DISTINCT source_path) FROM compilation').fetchone()[0],1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM entity').fetchone()[0],0)
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertEqual(self.db.execute("SELECT count(*) FROM compilation WHERE state='pending'").fetchone()[0],3)

    def test_failed_import_preserves_existing_snapshot(self):
        self.write([self.entry(),self.entry('B')])
        first = import_manifest(self.db,**self.options)
        self.db.execute("UPDATE snapshot SET state='ready' WHERE id=?",(first['snapshot_id'],))
        self.write([self.entry(),self.entry('B',source=self.root/'missing.cpp')])
        with self.assertRaises(FileNotFoundError):
            import_manifest(self.db,**self.options)
        self.assertEqual(self.db.execute('SELECT id,state FROM snapshot').fetchall(),[(first['snapshot_id'],'ready')])
        self.assertEqual(self.db.execute('SELECT count(*) FROM compilation').fetchone()[0],2)

    def test_changed_input_rolls_back(self):
        self.write([self.entry(),self.entry('B')])
        original = store.file_hash
        reads = 0
        def changing(path):
            nonlocal reads
            if path == self.source:
                reads += 1
                if reads == 2:
                    self.source.write_text('int value() { return 2; }\n')
            return original(path)
        with patch.object(store,'file_hash',side_effect=changing):
            with self.assertRaisesRegex(ValueError,'Input changed'):
                import_manifest(self.db,**self.options)
        self.assertEqual(self.db.execute('SELECT count(*) FROM snapshot').fetchone()[0],0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM repository').fetchone()[0],0)

    def test_command_is_not_executed_and_configuration_isolated(self):
        marker = self.root / 'should-not-exist'
        e = self.entry()
        del e['arguments']
        e['command'] = f"c++ -c '{self.source}' ; touch '{marker}'"
        self.write([e,self.entry('B')])
        first = import_manifest(self.db,**self.options)
        second = import_manifest(self.db,**dict(self.options,configuration_key='rtos'))
        self.assertFalse(marker.exists())
        self.assertNotEqual(first['snapshot_id'],second['snapshot_id'])
        self.assertEqual(self.db.execute('SELECT count(DISTINCT configuration_key) FROM snapshot').fetchone()[0],2)

    def test_missing_scope_and_response_files_rejected(self):
        self.write([self.entry()])
        with self.assertRaisesRegex(ValueError,'not found'):
            import_manifest(self.db,**self.options)
        e = self.entry(); e['arguments'].append('@flags.txt')
        self.write([e,self.entry('B')])
        with self.assertRaisesRegex(ValueError,'Response files'):
            import_manifest(self.db,**self.options)
        self.assertEqual(self.db.execute('SELECT count(*) FROM snapshot').fetchone()[0],0)

    def test_generated_origin_and_external_escape(self):
        generated = self.build/'generated.cpp'; generated.write_text('int generated;')
        self.write([self.entry(source=generated),self.entry('B')])
        import_manifest(self.db,**self.options)
        self.assertEqual(self.db.execute("SELECT origin FROM artifact WHERE path='build/generated.cpp'").fetchone()[0],'generated')
        external = Path(self.temp.name)/'external.cpp'; external.write_text('int external;')
        self.write([self.entry(source=external),self.entry('B')])
        with self.assertRaisesRegex(ValueError,'outside declared'):
            import_manifest(self.db,**self.options)

    def test_reopen_and_unknown_schema(self):
        other = connect(self.path)
        self.assertEqual(other.execute('PRAGMA foreign_keys').fetchone()[0],1)
        other.close()
        self.db.execute('PRAGMA user_version=99')
        with self.assertRaisesRegex(ValueError,'Unsupported'):
            connect(self.path)
        self.assertEqual(self.db.execute('PRAGMA user_version').fetchone()[0],99)

if __name__ == '__main__':
    unittest.main()
