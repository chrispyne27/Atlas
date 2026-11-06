"""Bounded provenance and hash-checked source for local staged inspection."""
import argparse
from contextlib import contextmanager
import io
import json
import time
from pathlib import Path
from .inspect import Inspector
from .store import canonical, digest

DETAIL_BYTES=64*1024
SOURCE_FILE_BYTES=16*1024*1024

class DetailInspector(Inspector):
    @contextmanager
    def _read(self,snapshot,target):
        if not all(isinstance(x,str) and 0<len(x)<=2048 for x in (snapshot,target)):
            raise ValueError('Invalid snapshot/target')
        version=self._version();deadline=time.monotonic()+0.5;ticks=0
        def stop():
            nonlocal ticks
            ticks+=1;return ticks>=2000 or time.monotonic()>deadline
        self.db.set_progress_handler(stop,1000);self.db.execute('BEGIN')
        try:
            snap=self.db.execute('SELECT id,revision,configuration_key,state FROM snapshot WHERE id=?',(snapshot,)).fetchone()
            if not snap or not self.db.execute('SELECT 1 FROM build_target WHERE snapshot_id=? AND id=?',(snapshot,target)).fetchone():
                raise ValueError('Unknown snapshot or target')
            yield dict(snap)
            self.db.execute('COMMIT')
            if self._version()!=version:raise ValueError('Database changed during inspection')
        finally:
            self.db.set_progress_handler(None,0)
            if self.db.in_transaction:self.db.execute('ROLLBACK')

    def _evidence(self,snapshot,target,evidence,query=None):
        query=query or self.db.execute
        if not isinstance(evidence,str) or not 0<len(evidence)<=2048:raise ValueError('Invalid evidence ID')
        # Evidence must be attached to an occurrence/relation visible in this target.
        visible=query('''SELECT 1 FROM evidence e WHERE e.snapshot_id=? AND e.id=? AND (
            EXISTS (SELECT 1 FROM relation r LEFT JOIN compilation c ON c.snapshot_id=r.snapshot_id AND c.id=r.compilation_id
                WHERE r.snapshot_id=e.snapshot_id AND r.evidence_id=e.id AND (r.compilation_id IS NULL OR c.target_id=?))
            OR EXISTS (SELECT 1 FROM occurrence o LEFT JOIN compilation c ON c.snapshot_id=o.snapshot_id AND c.id=o.compilation_id
                WHERE o.snapshot_id=e.snapshot_id AND o.evidence_id=e.id AND (o.compilation_id IS NULL OR c.target_id=?)))''',
            (snapshot,evidence,target,target)).fetchone()
        if not visible:raise ValueError('Evidence not attached to selected target/shared scope')
        row=query('''SELECT id,kind,substr(artifact_path,1,2048) AS artifact_path,line,substr(producer,1,2048) AS producer,
            length(CAST(details_json AS BLOB)) AS detail_bytes,
            CASE WHEN length(CAST(details_json AS BLOB))<=? THEN details_json ELSE NULL END AS body,
            (length(coalesce(artifact_path,''))>2048 OR length(producer)>2048) AS fields_truncated
            FROM evidence WHERE snapshot_id=? AND id=?''',(DETAIL_BYTES,snapshot,evidence)).fetchone()
        result=dict(row);body=result.pop('body');result['details']=json.loads(body) if body is not None else None
        result['details_status']='available' if body is not None else 'over_limit'
        return result

    def evidence(self,*,snapshot,target,evidence):
        with self._read(snapshot,target) as snap:
            item=self._evidence(snapshot,target,evidence)
            result={'inspection_only':True,'snapshot':snap,'target':target,'freshness':'not checked against source',
                    'applicability':'selected target or snapshot-shared; not verification','evidence':item}
            # JSON escaping and an existing nested document can exceed raw size.
            if len(canonical(result).encode())>DETAIL_BYTES:
                item['details']=None;item['details_status']='over_limit'
            return result

    def source(self,*,snapshot,target,evidence,roots,start=None,end=None):
        with self._read(snapshot,target) as snap:
            item=self._evidence(snapshot,target,evidence)
            return self._source_item(snap,target,item,roots,start,end)

    def _source_item(self,snap,target,item,roots,start=None,end=None,query=None,budget=None):
        query=query or self.db.execute
        snapshot=snap['id']
        evidence=item['id']
        result={'inspection_only':True,'snapshot':snap,'target':target,'evidence_id':evidence,
                'status':'unavailable','text':None,'freshness_scope':'this artifact only; graph freshness not established'}
        key=item['artifact_path'];result['artifact_path']=key
        if not key or '/' not in key or item['fields_truncated'] or key.startswith('external:'):
            result['reason']='external, missing or oversized source path';return result
        label,relative=key.split('/',1)
        if label not in ('repo','build') or label not in roots:
            result['reason']='source root not explicitly supplied';return result
        expected=query('SELECT content_hash FROM artifact WHERE snapshot_id=? AND path=?',(snapshot,key)).fetchone()
        if not expected:result['reason']='artifact absent';return result
        start=item['line'] or 1 if start is None else start
        end=min(start+39,start+199) if end is None else end
        if type(start)!=int or type(end)!=int or start<1 or end<start or end-start+1>200:
            raise ValueError('Source span must be 1..200 lines with a positive start')
        result.update(start_line=start,end_line=end,expected_hash=expected[0])
        try:
            root=Path(roots[label]).resolve(strict=True);path=(root/relative).resolve(strict=True)
            if not path.is_relative_to(root):result['reason']='path escaped supplied root';return result
            before=path.stat()
            if not path.is_file():result['reason']='not a regular file';return result
            if before.st_size>SOURCE_FILE_BYTES:result['status']='over_limit';return result
            read_cap=SOURCE_FILE_BYTES+1
            if budget is not None:
                limits,usage=budget
                available=min(limits['source_bytes']-usage['source_bytes'],
                              limits['source_hash_bytes']-usage['source_hash_bytes'])
                if usage['source_files']>=limits['source_files'] or before.st_size>=available:
                    result['status']='budget_omitted';return result
                read_cap=min(read_cap,available)
                usage['source_files']+=1
            with path.open('rb') as stream:raw=stream.read(read_cap)
            if budget is not None:usage['source_bytes']+=len(raw)
            after=path.stat()
        except (OSError,RuntimeError):result['reason']='source missing or unreadable';return result
        if len(raw)>SOURCE_FILE_BYTES:result['status']='over_limit';return result
        if budget is not None:usage['source_hash_bytes']+=len(raw)
        actual_hash=digest(raw)
        if (before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or actual_hash!=expected[0]:
            result['status']='stale';return result
        parts=[];size=0
        for line_number,line in enumerate(io.BytesIO(raw),1):
            if line_number>end:break
            if line_number>=start:
                size+=len(line)
                if size>DETAIL_BYTES:result['status']='over_limit';return result
                parts.append(line)
        if not parts:result['reason']='span beyond end of file';return result
        try:text=b''.join(parts).decode('utf-8')
        except UnicodeDecodeError:result['reason']='source is not UTF-8';return result
        result.update(status='available',text=text,hash_verified=True,returned_lines=len(parts))
        if len(canonical(result).encode())>DETAIL_BYTES:
            result.update(status='over_limit',text=None)
        return result


def main():
    p=argparse.ArgumentParser(description='Read-only bounded evidence/source inspection')
    p.add_argument('operation',choices=['evidence','source'])
    for key in ['database','snapshot','target','evidence']:p.add_argument('--'+key,required=True)
    p.add_argument('--repo-root');p.add_argument('--build-root');p.add_argument('--start',type=int);p.add_argument('--end',type=int)
    a=p.parse_args();reader=DetailInspector(a.database)
    try:
        args=dict(snapshot=a.snapshot,target=a.target,evidence=a.evidence)
        result=reader.evidence(**args) if a.operation=='evidence' else reader.source(**args,roots={k:v for k,v in [('repo',a.repo_root),('build',a.build_root)] if v},start=a.start,end=a.end)
        print(canonical(result))
    finally:reader.close()

if __name__=='__main__':main()
