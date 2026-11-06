"""Scoped libclang ingestion. No compiler processes or stored commands are run."""
import json
from importlib.metadata import version
from pathlib import Path
from .store import canonical, digest, file_hash
from ..indexer import qualified


def parsing_arguments(argv, cwd, source, system_includes):
    if not argv or Path(argv[0]).name not in {'c++','g++','gcc','cc','clang','clang++'}:
        raise ValueError('Unsupported compiler or wrapper')
    result = []; i = 1
    while i < len(argv):
        arg = argv[i]; i += 1
        if arg in ('-o','-MF','-MT','-MQ'):
            if i == len(argv): raise ValueError('Missing output option value')
            i += 1; continue
        if arg in ('-c','-MD','-MMD','-MP'): continue
        if arg in ('-I','-isystem','-iquote','-include','-imacros'):
            if i == len(argv): raise ValueError('Missing include option value')
            result.extend([arg,str((cwd/argv[i]).resolve())]); i += 1; continue
        if arg.startswith('-I'):
            result.append('-I'+str((cwd/arg[2:]).resolve())); continue
        if arg == '-D':
            if i == len(argv): raise ValueError('Missing macro definition')
            result.extend([arg,argv[i]]); i += 1; continue
        if arg.startswith(('-D','-U','-std=','-W')) or arg in {
            '-g','-g0','-g1','-g2','-g3','-O0','-O1','-O2','-O3','-Os',
            '-pedantic','-pthread','-fPIC','-fPIE','-fno-exceptions','-fno-rtti',
            '-fprofile-arcs','-ftest-coverage','-fsanitize=address,undefined,leak'}:
            # Driver/linker pass-through is not part of the supported subset.
            if arg.startswith(('-Wl,','-Wa,','-Wp,')):
                raise ValueError('Unsupported compiler pass-through option')
            result.append(arg); continue
        if not arg.startswith('-') and (cwd/arg).resolve() == source: continue
        raise ValueError('Unsupported compiler argument: '+arg)
    for directory in system_includes:
        path = Path(directory).resolve(strict=True)
        if not path.is_dir(): raise ValueError('System include must be a directory')
        result.extend(['-isystem',str(path)])
    return result


def parse_compilation(db, snapshot_id, compilation_id, system_includes=()):
    from clang.cindex import Index, CursorKind, Diagnostic
    if db.in_transaction or db.execute('PRAGMA foreign_keys').fetchone()[0] != 1:
        raise ValueError('Need an idle connection with foreign keys enabled')
    row = db.execute('SELECT c.source_path,c.arguments_json,c.state,s.state FROM compilation c JOIN snapshot s ON s.id=c.snapshot_id WHERE c.snapshot_id=? AND c.id=?',(snapshot_id,compilation_id)).fetchone()
    if not row or row[3] != 'staging' or row[2] not in ('pending','failed'):
        raise ValueError('Only pending/failed compilations in staging snapshots can be parsed')
    scope = json.loads(db.execute("SELECT details_json FROM evidence WHERE snapshot_id=? AND id='import-scope'",(snapshot_id,)).fetchone()[0])
    roots = sorted([(k,Path(v).resolve(strict=True)) for k,v in scope['roots'].items()],key=lambda x:len(x[1].parts),reverse=True)
    def physical(key):
        label, relative = key.split('/',1)
        base = dict(roots)[label]; path = (base/relative).resolve(strict=True)
        if not path.is_relative_to(base): raise ValueError('Artifact escaped named root')
        return path
    def identify(path):
        path = Path(str(path)).resolve(strict=True)
        for label,base in roots:
            if path.is_relative_to(base):
                return label+'/'+path.relative_to(base).as_posix(),path,'generated' if label=='build' else 'authored'
        return 'external:'+path.as_posix(),path,'external'
    def tracked(path):
        if path is None: return False
        return any(Path(str(path)).resolve().is_relative_to(base) for _,base in roots)
    command = None
    for record in db.execute("SELECT details_json FROM evidence WHERE snapshot_id=? AND id LIKE 'command:%'",(snapshot_id,)):
        value = json.loads(record[0])
        if value['compilation_id'] == compilation_id:
            command = value; break
    if command is None: raise ValueError('Compilation command evidence missing')
    source = physical(row[0]); cwd = physical(command['directory'])
    args = parsing_arguments(json.loads(row[1]),cwd,source,system_includes)
    producer = 'libclang-'+version('libclang')
    attempt = 'parse:'+compilation_id
    db.execute('BEGIN IMMEDIATE')
    try:
        # Recheck after obtaining writer lock.
        current = db.execute('SELECT c.state,s.state FROM compilation c JOIN snapshot s ON s.id=c.snapshot_id WHERE c.snapshot_id=? AND c.id=?',(snapshot_id,compilation_id)).fetchone()
        if current[0] not in ('pending','failed') or current[1] != 'staging':
            raise ValueError('Compilation state changed')
        for key,expected in db.execute('SELECT path,content_hash FROM artifact WHERE snapshot_id=?',(snapshot_id,)):
            path = Path(key[len('external:'):]) if key.startswith('external:') else physical(key)
            if file_hash(path) != expected: raise ValueError('Stale snapshot input: '+key)
        index = Index.create()
        discovery = index.parse(str(source),args=args)
        inputs = {Path(str(i.include)).resolve() for i in discovery.get_includes()} | {source}
        hashes = {p:file_hash(p) for p in inputs}
        del discovery
        tu = index.parse(str(source),args=args)
        observed = {Path(str(i.include)).resolve() for i in tu.get_includes()} | {source}
        diagnostics = [str(d) for d in tu.diagnostics]
        if any(d.severity >= Diagnostic.Error for d in tu.diagnostics):
            raise ValueError('Compiler diagnostics: '+'\n'.join(diagnostics))
        if observed != inputs: raise ValueError('Dependency set changed during parse')
        for path,hashed in hashes.items():
            key,_,origin = identify(path)
            previous = db.execute('SELECT content_hash FROM artifact WHERE snapshot_id=? AND path=?',(snapshot_id,key)).fetchone()
            if previous and previous[0] != hashed: raise ValueError('Dependency conflicts with snapshot: '+key)
            db.execute('INSERT OR IGNORE INTO artifact VALUES (?,?,?,?)',(snapshot_id,key,hashed,origin))
            db.execute('INSERT OR IGNORE INTO compilation_input VALUES (?,?,?)',(snapshot_id,compilation_id,key))
        # Parse summary also captures system include overrides and explicit boundaries.
        db.execute('INSERT OR REPLACE INTO evidence VALUES (?,?,?,?,?,?,?)',
            (snapshot_id,attempt,'compiler',row[0],None,producer,canonical({'arguments':args,'diagnostics':diagnostics,'dependency_count':len(inputs),'scope':'function declarations/definitions and direct calls; external bodies omitted'})))
        kinds = {CursorKind.FUNCTION_DECL,CursorKind.CXX_METHOD,CursorKind.CONSTRUCTOR,CursorKind.DESTRUCTOR,CursorKind.FUNCTION_TEMPLATE}
        count = {'occurrences':0,'calls':0,'unresolved':0,'dependencies':len(inputs)}
        sequence = 0
        def entity(cursor):
            usr = cursor.get_usr()
            if not usr: return None
            eid = digest(('symbol:'+usr).encode())
            db.execute('INSERT OR IGNORE INTO entity VALUES (?,?,?,?,?,?)',
                       (snapshot_id,eid,'symbol','clang-usr',usr,qualified(cursor)))
            return eid
        def walk(cursor, owner=None):
            nonlocal sequence
            if cursor.kind != CursorKind.TRANSLATION_UNIT and not tracked(cursor.location.file): return
            if cursor.kind in kinds:
                eid = entity(cursor)
                if not eid: return
                start,end = cursor.extent.start,cursor.extent.end
                if start.file and end.file and str(start.file)==str(end.file) and start.line>0:
                    sequence += 1
                    key,_,_ = identify(start.file)
                    if db.execute('SELECT 1 FROM artifact WHERE snapshot_id=? AND path=?',(snapshot_id,key)).fetchone():
                        db.execute('INSERT INTO occurrence VALUES (?,?,?,?,?,?,?,?,?)',
                            (snapshot_id,compilation_id+':occ:'+str(sequence),eid,compilation_id,key,start.line,end.line,
                             'definition' if cursor.is_definition() else 'declaration',attempt))
                        count['occurrences'] += 1
                if not cursor.is_definition(): return
                owner = eid
            elif cursor.kind == CursorKind.CALL_EXPR and owner:
                ref = cursor.referenced
                dynamic = ref and ref.kind == CursorKind.CXX_METHOD and ref.is_virtual_method()
                target = entity(ref) if ref and ref.kind in kinds and not dynamic else None
                sequence += 1
                evidence_id = compilation_id+':call:'+str(sequence)
                path,_,_ = identify(cursor.location.file)
                reason = 'virtual dispatch' if dynamic else ('direct compiler reference' if target else 'indirect or unresolved call')
                db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?)',
                    (snapshot_id,evidence_id,'compiler',path,cursor.location.line,producer,canonical({'reason':reason,'compilation_id':compilation_id})))
                db.execute('INSERT INTO relation VALUES (?,?,?,?,?,?,?,?,?)',
                    (snapshot_id,evidence_id,owner,target,cursor.spelling or '<unknown>','calls',
                     'resolved' if target else 'unresolved',compilation_id,evidence_id))
                count['calls' if target else 'unresolved'] += 1
            for child in cursor.get_children(): walk(child,owner)
        walk(tu.cursor)
        for path,hashed in hashes.items():
            if file_hash(path)!=hashed: raise ValueError('Dependency changed during parse: '+str(path))
        db.execute("UPDATE compilation SET state='parsed' WHERE snapshot_id=? AND id=?",(snapshot_id,compilation_id))
        # Input manifest grows with observed dependency artifacts; snapshot remains staging.
        manifest = list(db.execute('SELECT path,content_hash FROM artifact WHERE snapshot_id=? ORDER BY path',(snapshot_id,)))
        for key, expected in manifest:
            path = Path(key[len('external:'):]) if key.startswith('external:') else physical(key)
            if file_hash(path) != expected:
                raise ValueError('Snapshot input changed during parse: '+key)
        db.execute('UPDATE snapshot SET input_manifest_hash=? WHERE id=?',
                   (digest(canonical({'scope':scope['targets'],'artifacts':manifest}).encode()),snapshot_id))
        db.execute('COMMIT')
        return dict(count,snapshot_id=snapshot_id,compilation_id=compilation_id,state='parsed',snapshot_state='staging')
    except BaseException as error:
        if db.in_transaction: db.execute('ROLLBACK')
        # Keep diagnostics without any partial graph rows; never alter a ready snapshot.
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM snapshot WHERE id=? AND state='staging'",(snapshot_id,)).fetchone():
            db.execute("UPDATE compilation SET state='failed' WHERE snapshot_id=? AND id=? AND state IN ('pending','failed')",(snapshot_id,compilation_id))
            db.execute('INSERT OR REPLACE INTO evidence VALUES (?,?,?,?,?,?,?)',
                (snapshot_id,attempt+':failure','compiler',row[0],None,producer,canonical({'error':str(error)})))
        db.execute('COMMIT')
        raise
