#!/usr/bin/env python3
"""Bounded Linux/POSIX compilation probe; never executes compile-db commands."""
import argparse, collections, hashlib, json, pathlib, re, shlex, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from atlas_engine.indexer import compiler_arguments, parse_unit
p=argparse.ArgumentParser()
p.add_argument('repository',type=pathlib.Path)
p.add_argument('--output',required=True,type=pathlib.Path)
a=p.parse_args(); root=a.repository.resolve()
def relative(path):
    return str(pathlib.Path(path).relative_to(root))
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
builds={}
for name in ['build-fprime-automatic-native-ut','build-atlas-ref']:
    path=root/name/'compile_commands.json'
    entries=json.loads(path.read_text())
    sources=collections.Counter(relative(e['file']) for e in entries)
    targets=sorted({e.get('output','').split('CMakeFiles/')[-1].split('.dir/')[0] for e in entries})
    builds[name]={'compilation_entries':len(entries),'distinct_source_files':len(sources),'repeated_source_files':{k:v for k,v in sources.items() if v>1},'generated_entries':sum(pathlib.Path(e['file']).is_relative_to(root/name) for e in entries),'object_targets':targets,'database_sha256':digest(path)}
include=subprocess.check_output(['gcc','-print-file-name=include'],text=True).strip()
probes=[]
entries=json.loads((root/'build-fprime-automatic-native-ut/compile_commands.json').read_text())
for suffix in ['Svc/Health/HealthComponentImpl.cpp','Svc/CmdDispatcher/CommandDispatcherImpl.cpp']:
    entry=next(e for e in entries if e['file']==str(root/suffix))
    entry['arguments']=shlex.split(entry['command'],posix=True)
    source,args=compiler_arguments(entry,root)
    args+=['-isystem',include]
    unit=parse_unit(root,source,args)
    probes.append({'source':suffix,'source_sha256':digest(source),'configuration':'Linux Debug BUILD_UT C++14','counts':{k:len(v) for k,v in unit.items()},'diagnostics':unit['diagnostics'],'definition_locations':[{'id':n['id'],'name':n['name'],'path':n['path'],'line':n['line']} for n in unit['nodes'] if n['path']==suffix], 'unresolved':unit['unresolved']})
annotations=[]
for component in ['Health','CmdDispatcher']:
    for path in sorted((root/'Svc'/component/'test/ut').glob('*.cpp')):
        for n,line in enumerate(path.read_text().splitlines(),1):
            match=re.search(r'REQUIREMENT\("([^"]+)"\)',line)
            if match:
                annotations.append({'id':match[1],'path':relative(path),'line':n,'provenance':'upstream test annotation; not proof of satisfaction'})
result={'revision':subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),'builds':builds,'parser':'libclang 18.1.1 through existing Atlas parse_unit','normalization':'POSIX shlex for these trusted Linux CMake commands, no shell execution; GCC builtin include directory supplied explicitly','gcc_builtin_include':include,'probes':probes,'test_requirement_annotations':annotations,'limitations':['Counts include header definitions and generated dependencies; not a complete repository index.','Generated units not all built in unit-test configuration.','Direct C++ calls do not resolve all FPP port/topology routing or virtual dispatch.','No assertion of requirement satisfaction or reviewed mappings.']}
a.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'builds':{k:{f:v[f] for f in ['compilation_entries','distinct_source_files','generated_entries']} for k,v in builds.items()},'probes':[{k:v for k,v in x.items() if k in {'source','counts','diagnostics'}} for x in probes]},indent=2))
