"""Scoped F Prime authored requirements and textual test annotations.

Associations are source-file level, not executable-test or satisfaction claims.
"""
import json
import re
from pathlib import Path
from .store import canonical, digest, file_hash
from .membership import capture

ADAPTER = 'fprime-engineering-2'
ROW = re.compile(r'^\s*\|?\s*([A-Z][A-Z0-9_-]*-\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|?\s*$')
NONCODE = re.compile(r'R"(?P<delimiter>[^ ()\\\t\r\n]{0,16})\(.*?\)(?P=delimiter)"|//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',re.S)


def annotations(text):
    """Simple literal REQUIREMENT calls, excluding strings/comments.

    Preprocessor conditions are not evaluated: this is authored text evidence.
    """
    masked = NONCODE.sub(lambda m: ''.join('\n' if c=='\n' else ' ' for c in m[0]),text)
    for match in re.finditer(r'\bREQUIREMENT\s*\(',masked):
        literal = re.match(r'\s*"([A-Z][A-Z0-9_-]*-\d+)"\s*\)',text[match.end():])
        if literal:
            yield text.count('\n',0,match.start())+1,literal[1]


def import_engineering(db, snapshot_id, components):
    if db.in_transaction or db.execute('PRAGMA foreign_keys').fetchone()[0] != 1:
        raise ValueError('Need an idle connection with foreign keys enabled')
    selected = sorted(set(components))
    if not selected or any(c not in {'Svc/Health','Svc/CmdDispatcher'} for c in selected):
        raise ValueError('This adapter supports explicit Svc/Health and Svc/CmdDispatcher scopes only')
    row = db.execute("SELECT details_json FROM evidence WHERE snapshot_id=? AND id='import-scope'",(snapshot_id,)).fetchone()
    if row is None: raise ValueError('Snapshot import scope missing')
    scope = json.loads(row[0]); roots={k:Path(v).resolve(strict=True) for k,v in scope['roots'].items()}
    def physical(key):
        if key.startswith('external:'): return Path(key[len('external:'):])
        label,rel=key.split('/',1); path=(roots[label]/rel).resolve(strict=True)
        if not path.is_relative_to(roots[label]): raise ValueError('Artifact escaped named root')
        return path
    stats={'definitions':0,'annotations':0,'test_source_files':0,'reference_only_requirements':0,'candidate_aliases':0}
    db.execute('BEGIN IMMEDIATE')
    try:
        state=db.execute('SELECT state FROM snapshot WHERE id=?',(snapshot_id,)).fetchone()
        if not state or state[0]!='staging': raise ValueError('Engineering import requires a staging snapshot')
        for key,expected in db.execute('SELECT path,content_hash FROM artifact WHERE snapshot_id=?',(snapshot_id,)):
            if file_hash(physical(key))!=expected: raise ValueError('Stale snapshot input: '+key)
        def add_file(relative):
            key='repo/'+relative; path=physical(key)
            raw=path.read_bytes(); hashed=digest(raw)
            old=db.execute('SELECT content_hash FROM artifact WHERE snapshot_id=? AND path=?',(snapshot_id,key)).fetchone()
            if old and old[0]!=hashed: raise ValueError('Artifact conflicts with snapshot: '+key)
            db.execute('INSERT OR IGNORE INTO artifact VALUES (?,?,?,?)',(snapshot_id,key,hashed,'authored'))
            return key,raw.decode('utf-8')
        def entity(kind,namespace,key,name):
            eid=digest(canonical([kind,namespace,key]).encode())
            db.execute('INSERT OR IGNORE INTO entity VALUES (?,?,?,?,?,?)',(snapshot_id,eid,kind,namespace,key,name))
            return eid
        def evidence(eid,kind,path,line,details):
            db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?)',(snapshot_id,eid,kind,path,line,ADAPTER,canonical(details)))
        def occurrence(oid,eid,path,line,role,ev):
            db.execute('INSERT INTO occurrence VALUES (?,?,?,?,?,?,?,?,?)',(snapshot_id,oid,eid,None,path,line,line,role,ev))
        discoveries = {}
        for component in selected:
            marker='engineering:'+component
            if db.execute('SELECT 1 FROM evidence WHERE snapshot_id=? AND id=?',(snapshot_id,marker)).fetchone():
                raise ValueError('Component already imported; use a new snapshot: '+component)
            discoveries[component] = capture(roots['repo'], component)
            doc=component+'/docs/sdd.md'; doc_key,text=add_file(doc)
            namespace='requirement-document:'+doc
            definitions={}
            for line_number,line in enumerate(text.splitlines(),1):
                match=ROW.match(line)
                if not match: continue
                rid=match[1]
                if rid in definitions: raise ValueError('Duplicate requirement definition: '+rid)
                eid=entity('requirement',namespace,rid,rid); definitions[rid]=eid
                ev=marker+':definition:'+rid
                evidence(ev,'authored',doc_key,line_number,{'role':'requirement definition','verification_method':match[3].strip().rstrip('|').strip(),'satisfaction':'not assessed'})
                occurrence(ev,eid,doc_key,line_number,'definition',ev)
                stats['definitions']+=1
            if not definitions: raise ValueError('No supported requirement rows: '+doc)
            referenced=set(); aliases=set(); files=[]
            test_dir=physical('repo/'+component+'/test/ut')
            for source in sorted(test_dir.glob('*.cpp')):
                # Resolve before deriving the relative path to reject escaped symlinks.
                source=source.resolve(strict=True)
                if not source.is_relative_to(roots['repo']): raise ValueError('Test source escaped repository')
                relative=source.relative_to(roots['repo']).as_posix()
                key,content=add_file(relative); files.append(key)
                found=list(annotations(content))
                if not found: continue
                test=entity('test','test-source:'+component,relative,relative)
                stats['test_source_files']+=1
                for ordinal,(line_number,rid) in enumerate(found):
                    requirement=entity('requirement',namespace,rid,rid)
                    ev=marker+':annotation:'+digest(canonical([key,ordinal,line_number,rid]).encode())
                    details={'literal_id':rid,'association_granularity':'test source file',
                             'configuration_activation':'not evaluated','executable_case':'not resolved',
                             'has_definition':rid in definitions,'satisfaction':'not assessed'}
                    evidence(ev,'authored',key,line_number,details)
                    occurrence(ev,test,key,line_number,'annotation',ev)
                    # This records exactly that the authored source mentions the ID.
                    db.execute('INSERT INTO relation VALUES (?,?,?,?,?,?,?,?,?)',
                               (snapshot_id,ev,test,requirement,rid,'annotates_requirement','resolved',None,ev))
                    stats['annotations']+=1
                    if rid not in definitions:
                        referenced.add(rid)
                        occurrence(ev+':reference',requirement,key,line_number,'annotation',ev)
                        candidate=rid.removeprefix('ISF-')
                        if candidate!=rid and candidate in definitions and rid not in aliases:
                            alias=marker+':alias:'+rid
                            evidence(alias,'inferred',key,line_number,{'reason':'Removing ISF- yields an exact ID in the selected document','review':'required','equivalence':'not established'})
                            db.execute('INSERT INTO relation VALUES (?,?,?,?,?,?,?,?,?)',
                                (snapshot_id,alias,requirement,definitions[candidate],candidate,'candidate_alias','candidate',None,alias))
                            aliases.add(rid); stats['candidate_aliases']+=1
            stats['reference_only_requirements']+=len(referenced)
            evidence(marker,'authored',doc_key,None,{'scope':component,'adapter':ADAPTER,
                     'requirement_document':doc_key,'test_files':files,'test_granularity':'source file',
                     'discovery':discoveries[component],
                     'review_decisions_created':0,'implementation_links_created':0})
        manifest=list(db.execute('SELECT path,content_hash FROM artifact WHERE snapshot_id=? ORDER BY path',(snapshot_id,)))
        for key,expected in manifest:
            if file_hash(physical(key))!=expected: raise ValueError('Input changed during engineering import: '+key)
        for component, discovery in discoveries.items():
            if capture(roots['repo'], component) != discovery:
                raise ValueError('Directory membership changed during engineering import: '+component)
        db.execute('UPDATE snapshot SET input_manifest_hash=? WHERE id=?',
                   (digest(canonical({'scope':scope['targets'],'artifacts':manifest}).encode()),snapshot_id))
        db.execute('COMMIT')
        return dict(stats,snapshot_id=snapshot_id,state='staging',components=selected)
    except BaseException:
        if db.in_transaction: db.execute('ROLLBACK')
        raise
