"""Source-declared GoogleTest case identity, compiled wrapper and direct helper links."""
import json
import re
from pathlib import Path
from .engineering import NONCODE
from .store import canonical, digest, file_hash


def declarations(text):
    masked=NONCODE.sub(lambda m: ''.join('\n' if c=='\n' else ' ' for c in m[0]),text)
    for m in re.finditer(r'\bTEST\s*\(\s*([A-Za-z_]\w*)\s*,\s*([A-Za-z_]\w*)\s*\)',masked):
        yield text.count('\n',0,m.start())+1,m[1],m[2]


def map_test_cases(db,snapshot_id,compilation_id):
    if db.in_transaction or db.execute('PRAGMA foreign_keys').fetchone()[0]!=1:
        raise ValueError('Need an idle connection with foreign keys enabled')
    marker='gtest-cases:'+compilation_id
    db.execute('BEGIN IMMEDIATE')
    try:
        row=db.execute('SELECT c.source_path,c.target_id,c.state,s.state FROM compilation c JOIN snapshot s ON s.id=c.snapshot_id WHERE c.snapshot_id=? AND c.id=?',(snapshot_id,compilation_id)).fetchone()
        if not row or row[2]!='parsed' or row[3]!='staging': raise ValueError('Requires parsed compilation in staging snapshot')
        if db.execute('SELECT 1 FROM evidence WHERE snapshot_id=? AND id=?',(snapshot_id,marker)).fetchone(): raise ValueError('Cases already mapped')
        roots=json.loads(db.execute("SELECT details_json FROM evidence WHERE snapshot_id=? AND id='import-scope'",(snapshot_id,)).fetchone()[0])['roots']
        def physical(key):
            if key.startswith('external:'): return Path(key[len('external:'):])
            label,rel=key.split('/',1);base=Path(roots[label]).resolve();p=(base/rel).resolve(strict=True)
            if not p.is_relative_to(base): raise ValueError('Artifact escaped root')
            return p
        manifest=list(db.execute('SELECT path,content_hash FROM artifact WHERE snapshot_id=?',(snapshot_id,)))
        def verify():
            for key,hashed in manifest:
                if file_hash(physical(key))!=hashed: raise ValueError('Stale snapshot input: '+key)
        verify()
        counts={'declared':0,'mapped':0,'ambiguous':0,'unmatched':0,'helper_links':0}
        for line,suite,case in declarations(physical(row[0]).read_text()):
            counts['declared']+=1
            name=suite+'.'+case; namespace='gtest-target:'+row[1]
            tid=digest(canonical(['test',namespace,name]).encode())
            db.execute('INSERT OR IGNORE INTO entity VALUES (?,?,?,?,?,?)',(snapshot_id,tid,'test',namespace,name,name))
            wrapper=suite+'_'+case+'_Test::TestBody'
            matches=db.execute('''SELECT o.id,o.entity_id,e.name FROM occurrence o JOIN entity e ON e.snapshot_id=o.snapshot_id AND e.id=o.entity_id
                WHERE o.snapshot_id=? AND o.compilation_id=? AND o.artifact_path=? AND o.role='definition' AND o.start_line=?''',(snapshot_id,compilation_id,row[0],line)).fetchall()
            matches=[m for m in matches if m[2]==wrapper or m[2].endswith('::'+wrapper)]
            status='mapped' if len(matches)==1 else ('ambiguous' if matches else 'unmatched');counts[status]+=1
            ev=marker+':'+str(line)
            details={'test_name':name,'macro':'TEST','wrapper_matches':matches,'status':status,
                     'identity_basis':'source TEST declaration plus compiled TestBody span/name',
                     'execution':'not performed','binary_registration':'not checked','compilation_id':compilation_id}
            db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?)',(snapshot_id,ev,'inferred',row[0],line,'gtest-source-1',canonical(details)))
            db.execute('INSERT INTO occurrence VALUES (?,?,?,?,?,?,?,?,?)',(snapshot_id,ev,tid,compilation_id,row[0],line,line,'annotation',ev))
            if status!='mapped': continue
            body=matches[0][1]
            db.execute('INSERT INTO relation VALUES (?,?,?,?,?,?,?,?,?)',(snapshot_id,ev,tid,body,wrapper,'test_body','resolved',compilation_id,ev))
            # Only direct calls to helpers with annotation associations in the SAME target.
            links=db.execute('''SELECT DISTINCT call.id,call.to_entity,annotation.compilation_id
                FROM relation call JOIN relation annotation ON annotation.snapshot_id=call.snapshot_id AND annotation.from_entity=call.to_entity
                JOIN compilation helper ON helper.snapshot_id=annotation.snapshot_id AND helper.id=annotation.compilation_id
                WHERE call.snapshot_id=? AND call.compilation_id=? AND call.from_entity=? AND call.kind='calls'
                  AND call.resolution='resolved' AND annotation.kind='has_requirement_annotation' AND helper.target_id=?''',
                (snapshot_id,compilation_id,body,row[1])).fetchall()
            for call_id,helper,helper_compilation in links:
                eid=ev+':helper:'+digest(canonical([call_id,helper_compilation]).encode())
                db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?)',(snapshot_id,eid,'inferred',row[0],line,'gtest-source-1',canonical({'wrapper_evidence':ev,'direct_call_relation':call_id,'helper_compilation':helper_compilation,'satisfaction':'not assessed'})))
                db.execute('INSERT INTO relation VALUES (?,?,?,?,?,?,?,?,?)',(snapshot_id,eid,tid,helper,None,'invokes_annotated_helper','resolved',compilation_id,eid));counts['helper_links']+=1
        if not counts['declared']: raise ValueError('No supported TEST declarations')
        verify()
        db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?)',(snapshot_id,marker,'inferred',row[0],None,'gtest-source-1',canonical(counts)))
        db.execute('COMMIT');return dict(counts,snapshot_id=snapshot_id,compilation_id=compilation_id,state='staging')
    except BaseException:
        if db.in_transaction: db.execute('ROLLBACK')
        raise
