import sqlite3,tempfile,unittest
from pathlib import Path
from atlas_engine.storage import connect
from atlas_engine.storage.inspect import Inspector,MAX_BYTES
from atlas_engine.storage.store import canonical

class InspectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'store.sqlite';self.writer=connect(self.path);self.addCleanup(self.writer.close)
        d=self.writer
        d.execute("INSERT INTO repository VALUES ('r','test')")
        d.execute("INSERT INTO snapshot VALUES ('s','r','rev','linux','hash','gcc','test',1,'staging','now')")
        d.execute("INSERT INTO artifact VALUES ('s','repo/test.cpp','hash','authored')")
        d.execute("INSERT INTO evidence VALUES ('s','ev','inferred','repo/test.cpp',1,'test','{}')")
        for target in ['A','B']:
            d.execute('INSERT INTO build_target VALUES (?,?,?,?)',('s',target,target,'test'))
            d.execute('INSERT INTO compilation VALUES (?,?,?,?,?,?,?)',('s',target,target,'repo/test.cpp',target,'[]','parsed'))
        for eid in ['root','child','req']:
            d.execute('INSERT INTO entity VALUES (?,?,?,?,?,?)',('s',eid,'requirement' if eid=='req' else 'symbol','scope',eid,eid))
        d.execute("INSERT INTO occurrence VALUES ('s','o','root','A','repo/test.cpp',1,2,'definition','ev')")
        d.execute("INSERT INTO occurrence VALUES ('s','q','req',NULL,'repo/test.cpp',1,1,'definition','ev')")
        rows=[('a','calls','resolved','child','A'),('b','calls','unresolved',None,'A'),('c','candidate_alias','candidate','req',None),('hidden','calls','resolved','child','B')]
        for rid,kind,resolution,to,comp in rows:
            d.execute('INSERT INTO relation VALUES (?,?,?,?,?,?,?,?,?)',('s',rid,'root',to,'name',kind,resolution,comp,'ev'))
        self.reader=Inspector(self.path);self.addCleanup(self.reader.close)
    def query(self,**options):
        return self.reader.page(**dict(dict(snapshot='s',target='A',operation='neighbors',value='root'),**options))

    def test_pagination_provenance_and_target_isolation(self):
        page=self.query(limit=2);self.assertTrue(page['truncated'])
        second=self.query(limit=2,cursor=page['next_cursor'])
        items=page['items']+second['items'];self.assertEqual({x['id'] for x in items},{'a','b','c'})
        self.assertEqual(len(items),3);self.assertFalse(second['truncated'])
        self.assertTrue(any(x['resolution']=='candidate' for x in items))
        self.assertTrue(any(x['resolution']=='unresolved' for x in items))
        self.assertTrue(all(x['provenance']=='inferred' for x in items))
        self.assertTrue(page['inspection_only']);self.assertEqual(page['snapshot']['state'],'staging')

    def test_cursor_filter_or_database_change_rejected(self):
        cursor=self.query(limit=1)['next_cursor']
        with self.assertRaisesRegex(ValueError,'Cursor'):self.query(limit=1,cursor=cursor,target='B')
        self.writer.execute("UPDATE evidence SET producer='changed'")
        with self.assertRaisesRegex(ValueError,'Cursor'):self.query(limit=1,cursor=cursor)

    def test_readonly_lookup_and_bad_scope(self):
        with self.assertRaises(sqlite3.OperationalError):self.reader.db.execute('DELETE FROM entity')
        self.assertEqual(self.query(operation='lookup',value='req')['items'][0]['id'],'req')
        with self.assertRaisesRegex(ValueError,'Unknown target'):self.query(target='other')
        with self.assertRaises(ValueError):self.query(limit=201)
        with self.assertRaises(FileNotFoundError):Inspector(self.path.parent/'missing.db')

    def test_byte_limit_and_indexed_adjacency(self):
        self.writer.execute('BEGIN')
        for i in range(180):
            self.writer.execute('INSERT INTO relation VALUES (?,?,?,?,?,?,?,?,?)',('s',f'large{i:03}','root','child','x'*4000,'calls','resolved','A','ev'))
        self.writer.execute('COMMIT')
        statements=[];self.reader.db.set_trace_callback(statements.append)
        result=self.query(limit=200)
        self.assertEqual(result['truncation_reason'],'byte_limit')
        self.assertLessEqual(len(canonical(result).encode()),MAX_BYTES)
        self.assertTrue(any(x['fields_truncated'] for x in result['items']))
        sql=next(x for x in statements if 'SELECT r.id,r.from_entity' in x)
        plan=self.writer.execute('EXPLAIN QUERY PLAN '+sql).fetchall()
        self.assertTrue(any('relation_out' in str(x) for x in plan),plan)

if __name__=='__main__':unittest.main()
