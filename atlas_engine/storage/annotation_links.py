"""Join authored annotation lines to compiler definition spans, retaining uncertainty."""
import json
from pathlib import Path
from .store import canonical, digest, file_hash

PRODUCER = 'annotation-containment-1'


def link_annotations(db, snapshot_id, compilation_id):
    if db.in_transaction or db.execute('PRAGMA foreign_keys').fetchone()[0] != 1:
        raise ValueError('Need an idle connection with foreign keys enabled')
    marker = 'annotation-links:'+compilation_id
    db.execute('BEGIN IMMEDIATE')
    try:
        row = db.execute('SELECT c.source_path,c.state,s.state FROM compilation c JOIN snapshot s ON s.id=c.snapshot_id WHERE c.snapshot_id=? AND c.id=?',(snapshot_id,compilation_id)).fetchone()
        if not row or row[1]!='parsed' or row[2]!='staging':
            raise ValueError('Requires a parsed compilation in a staging snapshot')
        if db.execute('SELECT 1 FROM evidence WHERE snapshot_id=? AND id=?',(snapshot_id,marker)).fetchone():
            raise ValueError('Annotation linking already recorded for this compilation')
        scope = json.loads(db.execute("SELECT details_json FROM evidence WHERE snapshot_id=? AND id='import-scope'",(snapshot_id,)).fetchone()[0])
        roots = {k:Path(v).resolve(strict=True) for k,v in scope['roots'].items()}
        manifest=list(db.execute('SELECT path,content_hash FROM artifact WHERE snapshot_id=?',(snapshot_id,)))
        def verify():
            for key,expected in manifest:
                if key.startswith('external:'):
                    path=Path(key[len('external:'):])
                else:
                    label,relative=key.split('/',1); path=(roots[label]/relative).resolve(strict=True)
                    if not path.is_relative_to(roots[label]): raise ValueError('Artifact escaped root')
                if file_hash(path)!=expected: raise ValueError('Stale snapshot input: '+key)
        verify()
        # Only authored file-level annotations are inputs; derived relations cannot feed back.
        annotations=db.execute('''SELECT r.id,r.to_entity,r.target_spelling,e.id,e.artifact_path,e.line
            FROM relation r JOIN evidence e ON e.snapshot_id=r.snapshot_id AND e.id=r.evidence_id
            WHERE r.snapshot_id=? AND r.kind='annotates_requirement' AND e.kind='authored'
            AND e.artifact_path IN (SELECT artifact_path FROM compilation_input WHERE snapshot_id=? AND compilation_id=?)
            ORDER BY e.artifact_path,e.line,r.id''',(snapshot_id,snapshot_id,compilation_id)).fetchall()
        if not annotations: raise ValueError('No authored annotations in this compilation input set')
        counts={'matched':0,'ambiguous':0,'unmatched':0}
        for relation_id,requirement,spelling,annotation_evidence,path,line in annotations:
            candidates=db.execute('''SELECT o.id,o.entity_id,o.start_line,o.end_line,o.evidence_id
                FROM occurrence o JOIN entity n ON n.snapshot_id=o.snapshot_id AND n.id=o.entity_id
                WHERE o.snapshot_id=? AND o.compilation_id=? AND o.artifact_path=?
                AND o.role='definition' AND n.kind='symbol' AND o.start_line<=? AND o.end_line>=?
                ORDER BY o.start_line,o.end_line,o.id''',(snapshot_id,compilation_id,path,line,line)).fetchall()
            status='matched' if len(candidates)==1 else ('ambiguous' if candidates else 'unmatched')
            counts[status]+=1
            eid=marker+':'+digest(relation_id.encode())
            details={'status':status,'annotation_relation':relation_id,'annotation_evidence':annotation_evidence,
                     'compilation_id':compilation_id,'basis':'inclusive line containment in compiler definition spans',
                     'candidates':[dict(zip(('occurrence','entity','start_line','end_line','compiler_evidence'),c)) for c in candidates],
                     'annotation_activation':'not established','runnable_test_case':'not established',
                     'requirement_satisfaction':'not assessed','precision':'line-level; overlapping definitions stay ambiguous'}
            db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?)',
                       (snapshot_id,eid,'inferred',path,line,PRODUCER,canonical(details)))
            if status=='matched':
                db.execute('INSERT INTO relation VALUES (?,?,?,?,?,?,?,?,?)',
                    (snapshot_id,eid,candidates[0][1],requirement,spelling,'has_requirement_annotation','resolved',compilation_id,eid))
        verify()
        db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?)',
            (snapshot_id,marker,'inferred',row[0],None,PRODUCER,canonical(dict(counts,annotations=len(annotations),scope='one compilation input set',method='source-span association only'))))
        db.execute('COMMIT')
        return dict(counts,annotations=len(annotations),snapshot_id=snapshot_id,compilation_id=compilation_id,state='staging')
    except BaseException:
        if db.in_transaction: db.execute('ROLLBACK')
        raise
