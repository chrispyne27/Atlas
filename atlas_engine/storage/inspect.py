"""Bounded, read-only inspection of staged graphs; not current-context retrieval."""
import argparse
import base64
import json
import sqlite3
import time
from pathlib import Path
from .store import canonical, digest

MAX_BYTES=256*1024

class Inspector:
    def __init__(self,path):
        self.path=Path(path).resolve(strict=True)
        self.db=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA query_only=ON')
        self.db.execute('PRAGMA foreign_keys=ON')
        if self.db.execute('PRAGMA user_version').fetchone()[0]!=1:
            self.close();raise ValueError('Unsupported schema')

    def close(self): self.db.close()

    def _version(self):
        # Conservative local-file change detector; any DB write invalidates cursors.
        values=[]
        for p in (self.path,Path(str(self.path)+'-wal')):
            try:
                s=p.stat();values.append([s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns])
            except FileNotFoundError:values.append(None)
        return digest(canonical(values).encode())

    @staticmethod
    def _visibility(alias):
        return f'''(EXISTS (SELECT 1 FROM occurrence o JOIN compilation c ON c.snapshot_id=o.snapshot_id AND c.id=o.compilation_id
            WHERE o.snapshot_id={alias}.snapshot_id AND o.entity_id={alias}.id AND c.target_id=:target)
          OR EXISTS (SELECT 1 FROM relation r JOIN compilation c ON c.snapshot_id=r.snapshot_id AND c.id=r.compilation_id
            WHERE r.snapshot_id={alias}.snapshot_id AND r.from_entity={alias}.id AND c.target_id=:target)
          OR EXISTS (SELECT 1 FROM relation r JOIN compilation c ON c.snapshot_id=r.snapshot_id AND c.id=r.compilation_id
            WHERE r.snapshot_id={alias}.snapshot_id AND r.to_entity={alias}.id AND c.target_id=:target)
          OR ({alias}.kind IN ('requirement','test') AND EXISTS (SELECT 1 FROM occurrence o
            WHERE o.snapshot_id={alias}.snapshot_id AND o.entity_id={alias}.id AND o.compilation_id IS NULL)))'''

    def page(self,*,snapshot,target,operation,value,direction='out',field='name',kind=None,limit=50,cursor=None):
        if operation not in ('lookup','neighbors') or direction not in ('in','out') or field not in ('name','id'):
            raise ValueError('Unsupported query options')
        if type(limit)!=int or not 1<=limit<=200:raise ValueError('Limit must be 1..200')
        if not all(isinstance(v,str) and 0<len(v)<=2048 for v in (snapshot,target,value)):
            raise ValueError('Snapshot, target and value must be nonempty strings up to 2048 characters')
        if kind is not None and (not isinstance(kind,str) or len(kind)>128):raise ValueError('Invalid kind filter')
        version=self._version()
        request=dict(snapshot=snapshot,target=target,operation=operation,value=value,direction=direction,field=field,kind=kind)
        binding=digest(canonical([request,version]).encode())
        after=['','']
        if cursor:
            try:
                if not isinstance(cursor,str) or len(cursor)>8192:raise ValueError()
                decoded=json.loads(base64.urlsafe_b64decode(cursor.encode()))
                if decoded['binding']!=binding:raise ValueError()
                after=decoded['after']
                if not isinstance(after,list) or len(after)!=2 or not all(isinstance(x,str) and len(x)<=2048 for x in after):raise ValueError()
            except Exception as error:raise ValueError('Cursor invalid or database/query changed') from error
        deadline=time.monotonic()+0.5; ticks=0
        def stop():
            nonlocal ticks
            ticks+=1
            return ticks>=2000 or time.monotonic()>deadline
        self.db.set_progress_handler(stop,1000)
        self.db.execute('BEGIN')
        try:
            snap=self.db.execute('SELECT id,revision,configuration_key,state,input_manifest_hash FROM snapshot WHERE id=?',(snapshot,)).fetchone()
            if not snap:raise ValueError('Unknown snapshot')
            if not self.db.execute('SELECT 1 FROM build_target WHERE snapshot_id=? AND id=?',(snapshot,target)).fetchone():raise ValueError('Unknown target in snapshot')
            params=dict(snapshot=snapshot,target=target,value=value,kind=kind,first=after[0],last=after[1],limit=limit+1)
            if operation=='lookup':
                sql=f'''SELECT e.id,e.kind,substr(e.scope,1,2048) AS scope,substr(e.external_key,1,2048) AS external_key,
                    substr(e.name,1,2048) AS name, (length(e.scope)>2048 OR length(e.external_key)>2048 OR length(e.name)>2048) AS fields_truncated,
                    e.name AS sort_first,e.id AS sort_last
                    FROM entity e WHERE e.snapshot_id=:snapshot AND e.{field}=:value
                    AND (:kind IS NULL OR e.kind=:kind) AND (e.name,e.id)>(:first,:last)
                    AND {self._visibility('e')} ORDER BY e.name,e.id LIMIT :limit'''
            else:
                if not self.db.execute(f'SELECT 1 FROM entity e WHERE e.snapshot_id=:snapshot AND e.id=:value AND {self._visibility("e")}',params).fetchone():
                    raise ValueError('Entity is absent from selected target/shared scope')
                column='from_entity' if direction=='out' else 'to_entity'
                sql=f'''SELECT r.id,r.from_entity,r.to_entity,r.kind,r.resolution,r.compilation_id,
                    substr(r.target_spelling,1,2048) AS target_spelling,r.evidence_id,e.kind AS provenance,
                    substr(e.artifact_path,1,2048) AS artifact_path,e.line,substr(e.producer,1,2048) AS producer,
                    (length(coalesce(r.target_spelling,''))>2048 OR length(coalesce(e.artifact_path,''))>2048 OR length(e.producer)>2048) AS fields_truncated,
                    CASE WHEN r.compilation_id IS NULL THEN 'snapshot-shared; target applicability unverified' ELSE 'selected target compilation' END AS applicability,
                    r.kind AS sort_first,r.id AS sort_last
                    FROM relation r JOIN evidence e ON e.snapshot_id=r.snapshot_id AND e.id=r.evidence_id
                    LEFT JOIN compilation c ON c.snapshot_id=r.snapshot_id AND c.id=r.compilation_id
                    WHERE r.snapshot_id=:snapshot AND r.{column}=:value AND (:kind IS NULL OR r.kind=:kind)
                    AND (r.kind,r.id)>(:first,:last) AND (r.compilation_id IS NULL OR c.target_id=:target)
                    ORDER BY r.kind,r.id LIMIT :limit'''
            rows=self.db.execute(sql,params)
            response={'inspection_only':True,'snapshot':dict(snap),'target':target,
                'freshness':'not checked against current source','scope':'partial staged graph; shared authored evidence is not target verification',
                'items':[],'truncated':False,'truncation_reason':None,'next_cursor':None,
                'limits':{'items':limit,'bytes':MAX_BYTES,'query_vm_steps':2000000,'query_seconds':0.5},
                'counts_scope':'returned page only; no exhaustive coverage claim'}
            last=None;reason=None
            for record in rows:
                item=dict(record);key=[item.pop('sort_first'),item.pop('sort_last')]
                if any(len(x)>2048 for x in key):raise ValueError('Oversized pagination key')
                if len(response['items'])>=limit:reason='item_limit';break
                # Reserve space for cursor and metadata; full evidence bodies are intentionally not loaded.
                if len(canonical(response).encode())+len(canonical(item).encode())+12000>MAX_BYTES:
                    reason='byte_limit';break
                response['items'].append(item);last=key
            if reason:
                if last is None:raise ValueError('First item exceeds response budget')
                response['truncated']=True;response['truncation_reason']=reason
                response['next_cursor']=base64.urlsafe_b64encode(canonical({'binding':binding,'after':last}).encode()).decode()
            response['unresolved_in_page']=sum(x.get('resolution')=='unresolved' for x in response['items'])
            response['candidates_in_page']=sum(x.get('resolution')=='candidate' for x in response['items'])
            self.db.execute('COMMIT')
            if self._version()!=version:raise ValueError('Database changed during inspection; retry')
            if len(canonical(response).encode())>MAX_BYTES:raise ValueError('Response budget exceeded')
            return response
        except sqlite3.OperationalError as error:
            if 'interrupted' in str(error):raise ValueError('Query work budget exceeded; narrow the query') from error
            raise
        finally:
            self.db.set_progress_handler(None,0)
            if self.db.in_transaction:self.db.execute('ROLLBACK')


def main():
    p=argparse.ArgumentParser(description='Read-only inspection; not freshness-validated agent context')
    p.add_argument('operation',choices=['lookup','neighbors']);p.add_argument('--database',required=True)
    p.add_argument('--snapshot',required=True);p.add_argument('--target',required=True);p.add_argument('--value',required=True)
    p.add_argument('--field',choices=['name','id'],default='name');p.add_argument('--direction',choices=['in','out'],default='out')
    p.add_argument('--kind');p.add_argument('--limit',type=int,default=50);p.add_argument('--cursor')
    a=vars(p.parse_args());reader=Inspector(a.pop('database'))
    try:print(canonical(reader.page(**a)))
    finally:reader.close()

if __name__=='__main__':main()
