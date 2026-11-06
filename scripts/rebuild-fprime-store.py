"""Rebuild the scoped staging experiment from source; writes a NEW SQLite file."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atlas_engine.storage import connect,import_manifest
from atlas_engine.storage.compiler import parse_compilation
from atlas_engine.storage.engineering import import_engineering
from atlas_engine.storage.annotation_links import link_annotations
from atlas_engine.storage.test_cases import map_test_cases
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--database',type=Path,required=True);p.add_argument('--system-include',required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
if a.database.exists(): p.error('Refusing to overwrite existing database')
db=connect(a.database)
report={'snapshots':[],'parses':[],'engineering':[],'helper_associations':[],'cases':[]}
try:
 for config,build,targets,sources in [
  ('linux-debug-ut','build-fprime-automatic-native-ut',['Svc_Health','Svc_Health_ut_exe','Svc_CmdDispatcher','Svc_CmdDispatcher_ut_exe'],['HealthComponentImpl.cpp','HealthTester.cpp','CommandDispatcherTester.cpp','HealthTestMain.cpp','CommandDispatcherTestMain.cpp']),
  ('linux-debug-ref','build-atlas-ref',['Svc_Health','Svc_CmdDispatcher'],['HealthComponentImpl.cpp'])]:
  result=import_manifest(db,repository=a.repo,build_root=a.repo/build,compilation_database=a.repo/build/'compile_commands.json',repository_id='nasa-fprime',source_uri='https://github.com/nasa/fprime.git',revision='7d8f579f159d2f7c2d4984d92828575e37f87fa6',configuration_key=config,toolchain_fingerprint='gcc-13.3.0-cxx14-fpp-3.3.0',targets=targets)
  report['snapshots'].append(result);sid=result['snapshot_id']
  rows=db.execute('SELECT id,source_path FROM compilation WHERE snapshot_id=?',(sid,)).fetchall()
  for cid,source in rows:
   if Path(source).name in sources:
    report['parses'].append(dict(parse_compilation(db,sid,cid,[a.system_include]),source=source))
  if config.endswith('-ut'):
   report['engineering'].append(import_engineering(db,sid,['Svc/Health','Svc/CmdDispatcher']))
   for cid,source in rows:
    if Path(source).name in ['HealthTester.cpp','CommandDispatcherTester.cpp']:
     report['helper_associations'].append(link_annotations(db,sid,cid))
   for cid,source in rows:
    if Path(source).name in ['HealthTestMain.cpp','CommandDispatcherTestMain.cpp']:
     report['cases'].append(map_test_cases(db,sid,cid))
 report['integrity_check']=db.execute('PRAGMA integrity_check').fetchall()
 report['foreign_key_check']=db.execute('PRAGMA foreign_key_check').fetchall()
finally: db.close()
# Reopen to validate the actual saved file, not only the writer's view.
check=connect(a.database)
report['reopened_integrity_check']=check.execute('PRAGMA integrity_check').fetchall();check.close()
a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'cases':report['cases'],'integrity':report['reopened_integrity_check']},indent=2))
