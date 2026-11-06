import json
import shutil
import tempfile
import unittest
from pathlib import Path
from atlas_engine.indexer import build_index

FIXTURE = Path(__file__).resolve().parents[2] / 'samples' / 'aurora'
class IndexerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='atlas-test-')
        self.root = Path(self.temp.name) / 'repo'
        shutil.copytree(FIXTURE, self.root, ignore=shutil.ignore_patterns('.atlas'))
    def tearDown(self):
        self.temp.cleanup()
    def test_resolved_overloads_and_source_spans(self):
        g = build_index(self.root)
        lookup = {n.get('signature'): n for n in g['nodes'] if n.get('signature')}
        integer = lookup['aurora::Geometry::clampDimension(int)']
        floating = lookup['aurora::Geometry::clampDimension(float)']
        layout = lookup['aurora::LayoutEngine::resolve(Size)']
        self.assertNotEqual(integer['id'], floating['id'])
        self.assertTrue(any(e['from']==layout['id'] and e['to']==integer['id'] and e['type']=='calls' for e in g['edges']))
        self.assertFalse(any(e['from']==layout['id'] and e['to']==floating['id'] for e in g['edges']))
        for n in g['nodes']:
            if n.get('code') and n['kind'] != 'file':
                lines=(self.root/n['path']).read_text().splitlines()
                self.assertIn(n['code'], '\n'.join(lines[n['line']-1:n['end_line']]))
        ids={n['id'] for n in g['nodes']}
        self.assertTrue(all(e['from'] in ids and e['to'] in ids for e in g['edges']))
    def test_noop_source_and_header_invalidation(self):
        first=build_index(self.root)
        self.assertEqual(len(first['parse_stats']['parsed']),6)
        self.assertEqual(len(build_index(self.root)['parse_stats']['reused']),6)
        p=self.root/'src/RenderEngine.cpp';p.write_text(p.read_text()+'\n// change\n')
        self.assertEqual(build_index(self.root)['parse_stats']['parsed'],['src/RenderEngine.cpp'])
        p=self.root/'include/Geometry.hpp';p.write_text(p.read_text()+'\n// header change\n')
        changed=build_index(self.root)['parse_stats']['parsed']
        self.assertEqual(len(changed),5)
        self.assertNotIn('src/AssetCache.cpp',changed)
    def test_added_file_and_configuration_invalidate(self):
        build_index(self.root)
        (self.root/'include/NewHeader.hpp').write_text('// new membership\n')
        self.assertEqual(len(build_index(self.root)['parse_stats']['parsed']),6)
        p=self.root/'compile_commands.json';entries=json.loads(p.read_text())
        entries[0]['arguments'].insert(1,'-DATLAS_TEST=1');p.write_text(json.dumps(entries))
        self.assertEqual(len(build_index(self.root)['parse_stats']['parsed']),6)
    def test_invalid_manifest_does_not_overwrite_good_snapshot(self):
        good=build_index(self.root)
        p=self.root/'requirements.json';reqs=json.loads(p.read_text());reqs[0]['symbols']=['doesNotExist()'];p.write_text(json.dumps(reqs))
        with self.assertRaisesRegex(ValueError,'Unknown or ambiguous'):
            build_index(self.root)
        self.assertEqual(json.loads((self.root/'.atlas/index.json').read_text())['repository'],good['repository'])
    def test_compiler_errors_fail_and_dynamic_calls_are_explicit(self):
        p=self.root/'src/RenderEngine.cpp';p.write_text(p.read_text()+'\nvoid indirect(void (*fn)()) { fn(); }\nstruct Interface { virtual void draw() = 0; };\nvoid dispatch(Interface& i) { i.draw(); }\n')
        g=build_index(self.root)
        self.assertTrue(any(u['reason']=='Dynamic dispatch' for u in g['unresolved']))
        self.assertTrue(any(u['reason']=='Unresolved or indirect call' for u in g['unresolved']))
        p.write_text(p.read_text()+'\nthis is not C++;\n')
        with self.assertRaisesRegex(ValueError,'Compiler errors'):
            build_index(self.root)
    def test_stale_test_evidence_is_not_reused(self):
        g=build_index(self.root)
        (self.root/'.atlas/test-results.json').write_text(json.dumps({'source_fingerprint':'wrong','tests':[{'id':'TEST-zeroResize','status':'passed'}]}))
        g=build_index(self.root)
        self.assertFalse(g['test_evidence']['current'])
        self.assertFalse(any(n.get('evidence') for n in g['nodes']))

if __name__=='__main__': unittest.main()
