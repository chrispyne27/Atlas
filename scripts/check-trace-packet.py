#!/usr/bin/env python3
"""Repeatable CLI trace acceptance; synthetic authored claims, optional real F Prime."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atlas_engine.storage.store import connect, canonical, file_hash

PROJECT = Path(__file__).resolve().parents[1]
KINDS = ['invokes_annotated_helper', 'has_requirement_annotation', 'candidate_alias']


def fixture(folder):
    root = folder/'repo';root.mkdir()
    source = root/'trace.cpp'
    source.write_text('// SYNTHETIC: not compiled, executed or reviewed.\n'
        'void helper() { REQUIREMENT("DEMO-001"); }\n'
        'void nominal() { helper(); /* unresolved callback */ }\n'
        '// DEMO-001: illustrative requirement.\n'
        '// DEMO-ALIAS-001: unapproved alias.\n')
    path = folder/'trace.sqlite';db = connect(path)
    try:
        db.execute('BEGIN')
        db.execute("INSERT INTO repository VALUES ('r','synthetic')")
        db.execute("INSERT INTO snapshot VALUES ('s','r','synthetic-not-compiled','illustrative','hash','not-assessed','synthetic',1,'staging','fixed')")
        db.execute('INSERT INTO artifact VALUES (?,?,?,?)', ('s','repo/trace.cpp',file_hash(source),'authored'))
        db.execute("INSERT INTO build_target VALUES ('s','t','synthetic target','test')")
        db.execute("INSERT INTO compilation VALUES ('s','c','t','repo/trace.cpp','synthetic','[]','pending')")
        for eid, kind, name, line in [('test','test','Trace.Nominal',3),
                ('helper','symbol','helper',2), ('requirement','requirement','DEMO-001',4),
                ('alias','requirement','DEMO-ALIAS-001',5)]:
            db.execute('INSERT INTO entity VALUES (?,?,?,?,?,?)', ('s',eid,kind,'synthetic',eid,name))
            db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?)', ('s',eid,'authored','repo/trace.cpp',line,
                'synthetic trace acceptance fixture',canonical(dict(synthetic=True,not_compiler_derived=True,
                not_executed=True,not_requirement_verification=True,not_reviewed=True))))
            compilation = None if kind=='requirement' else 'c'
            db.execute('INSERT INTO occurrence VALUES (?,?,?,?,?,?,?,?,?)', ('s',eid,eid,compilation,'repo/trace.cpp',line,line,'description',eid))
        for rid, src, dst, kind, resolution, compilation in [
            ('01','test','helper','invokes_annotated_helper','resolved','c'),
            ('02','helper','requirement','has_requirement_annotation','resolved','c'),
            ('03','requirement','alias','candidate_alias','candidate',None),
            ('04','helper',None,'calls','unresolved','c')]:
            db.execute('INSERT INTO relation VALUES (?,?,?,?,?,?,?,?,?)',
                ('s',rid,src,dst,dst or 'unknown_callback',kind,resolution,compilation,src))
        db.execute('COMMIT')
    finally:db.close()
    return path, root


def run(module, args, commands):
    command = [sys.executable,'-m','atlas_engine.storage.'+module]+args
    commands.append(command)
    result = subprocess.run(command, cwd=PROJECT, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError(f'{module} failed: {result.stdout} {result.stderr}')
    return json.loads(result.stdout)


def check(path, root, snapshot, target, name, synthetic=False):
    commands = []
    db_before = file_hash(path)
    scope = ['--database',str(path),'--snapshot',snapshot,'--target',target]
    lookup = run('inspect',['lookup']+scope+['--value',name],commands)
    if len(lookup['items']) != 1:raise ValueError('Expected one exact seed; no fuzzy selection')
    seed = lookup['items'][0]['id']
    args = scope+['--entity',seed,'--repo-root',str(root)]
    # Synthetic additionally demonstrates unresolved calls; real slice deliberately
    # selects engineering association kinds, not every call in the helper.
    for kind in KINDS+(['calls'] if synthetic else []):args += ['--kind',kind]
    packet = run('trace_packet',args,commands)
    repeated = run('trace_packet',args,commands)
    if packet != repeated:raise ValueError('Stable packet comparison failed')
    if not packet['inspection_only'] or packet['context_eligible']:raise ValueError('Inspection flags changed')
    if len(canonical(packet).encode()) != packet['usage']['bytes']:raise ValueError('Byte count mismatch')
    if packet['usage']['bytes'] > packet['limits']['max_bytes']:raise ValueError('Budget exceeded')
    kinds = [r['kind'] for r in packet['relationships']]
    if not all(kind in kinds for kind in KINDS):raise ValueError('Expected trace associations missing')
    if synthetic and packet['unresolved_returned'] != 1:raise ValueError('Unresolved edge lost')
    if packet['candidates_returned'] != 1:raise ValueError('Unapproved alias lost')
    if not all(o['source']['status']=='available' for o in packet['occurrences']):
        raise ValueError('Expected fresh selected source excerpts')
    eid = packet['relationships'][0]['evidence_id']
    detail = run('details',['evidence']+scope+['--evidence',eid],commands)
    source = run('details',['source']+scope+['--evidence',eid,'--repo-root',str(root)],commands)
    if source['status'] != 'available':raise ValueError('Independent detail source failed')
    for occurrence in packet['occurrences']:
        key = occurrence['artifact_path']
        if not key.startswith('repo/'):raise ValueError('Unexpected source root in selected acceptance slice')
        if file_hash(root/key[5:]) != occurrence['source']['expected_hash']:
            raise ValueError('Source changed across CLI operations')
    if file_hash(path) != db_before:raise ValueError('Read-only DB byte check failed')
    return dict(status='passed',synthetic=synthetic,commands=commands,snapshot=packet['snapshot'],target=target,
        seed=seed,entities=[n['name'] for n in packet['entities']],
        relationships=[dict(kind=r['kind'],resolution=r['resolution'],provenance=r['provenance'],
                            applicability=r['applicability']) for r in packet['relationships']],
        usage=packet['usage'],omissions=packet['omissions'],
        source_statuses=[dict(artifact=o['artifact_path'],status=o['source']['status'],
                             expected_hash=o['source']['expected_hash']) for o in packet['occurrences']],
        detail_kind=detail['evidence']['kind'],db_sha256=db_before,db_bytes_unchanged=True,
        selected_source_hashes_unchanged=True,stable_repeat=True,inspection_only=True,context_eligible=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fprime-database',type=Path);parser.add_argument('--fprime-root',type=Path)
    args = parser.parse_args()
    if bool(args.fprime_database) != bool(args.fprime_root):parser.error('Supply both F Prime database and root')
    with tempfile.TemporaryDirectory(prefix='atlas-trace-acceptance-') as folder:
        path,root = fixture(Path(folder))
        result = dict(synthetic=check(path,root,'s','t','Trace.Nominal',True),
            limits='bounded inspection acceptance only; no parsing, execution, review, readiness or scale qualification',
            synthetic_paths='temporary; rerun this script to reproduce')
    if args.fprime_database:
        result['fprime'] = check(args.fprime_database.resolve(),args.fprime_root.resolve(),
            'bd6c4ddd353f4437a03812c834743c5c',
            'build/F-Prime/Svc/Health/CMakeFiles/Svc_Health_ut_exe.dir','Test.NominalTlm')
    else:result['fprime'] = dict(status='not_run',reason='explicit database/source roots not supplied')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
