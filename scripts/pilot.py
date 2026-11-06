#!/usr/bin/env python3
"""Prepare matched trials; independently evaluate submitted source. Never simulates model runs."""
import argparse, json, shutil, subprocess, sys, difflib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atlas_engine.indexer import build_index, inventory, fingerprint, atomic_json
from atlas_engine.test_runner import run_tests
ROOT=Path(__file__).resolve().parents[1]
TASKS=[
 {'id':'cache','title':'Reject invalid cache IDs','kind':'Bug fix','seed':'REQ-RES-003',
 'prompt':'Fix REQ-RES-003: only nonnegative resource IDs are valid. Negative IDs must never be present and inserting one must not consume a slot or change FIFO eviction order. Preserve capacity four and duplicate insertion behavior. Reuse existing mechanisms where appropriate.',
 'oracles':['aurora::AssetCache::insert(int)','aurora::AssetCache::contains(int)','aurora::AssetCache::capacity()'],
 'checks':[
 ('empty-negative','AssetCache c; return !c.contains(-1) && !c.contains(-200);'),
 ('invalid-does-not-evict','AssetCache c; for(int i=1;i<=4;++i)c.insert(i); c.insert(-2); return c.contains(1)&&c.contains(4)&&!c.contains(-2);'),
 ('zero-is-valid','AssetCache c; c.insert(0); return c.contains(0)&&!c.contains(-1);'),
 ('duplicate-preserves-fifo','AssetCache c;for(int i=0;i<4;++i)c.insert(i);c.insert(0);c.insert(4);return !c.contains(0)&&c.contains(1)&&c.contains(4);'),
 ('invalid-preserves-order','AssetCache c;c.insert(1);c.insert(-10);c.insert(2);c.insert(3);c.insert(4);c.insert(5);return !c.contains(1)&&c.contains(2)&&c.contains(5);'),
 ('extreme-negative','AssetCache c;c.insert((-2147483647-1));c.insert(2147483647);return !c.contains((-2147483647-1))&&c.contains(2147483647)&&c.capacity()==4;')]},
 {'id':'limit','title':'Lower the shared dimension ceiling','kind':'Requirement change','seed':'REQ-UI-002',
 'prompt':'Implement the revised REQ-UI-002: supported dimensions are now inclusive 1..4096. Apply the shared policy consistently to both numeric overloads, viewport, direct layout, and resize events. Update obsolete expectations in visible tests and comments. Preserve exactly one event per request and existing public interfaces; do not duplicate normalization policy.',
 'oracles':['aurora::Geometry::clampDimension(int)','aurora::Geometry::clampDimension(float)','aurora::RenderEngine::resize(Size)','aurora::LayoutEngine::resolve(Size)','aurora::EventBus::publish(const ViewportChanged &)'],
 'checks':[
 ('integer-boundaries','return Geometry::clampDimension(4096)==4096&&Geometry::clampDimension(4097)==4096&&Geometry::clampDimension(0)==1;'),
 ('float-policy','return Geometry::clampDimension(5000.5f)==4096.0f&&Geometry::clampDimension(25.5f)==25.5f&&Geometry::clampDimension(-0.1f)==1.0f;'),
 ('integer-extremes','return Geometry::clampDimension(2147483647)==4096&&Geometry::clampDimension((-2147483647-1))==1;'),
 ('direct-layout','LayoutEngine l;Rect r=l.resolve(Size{8000,0});return r.width==4096&&r.height==1;'),
 ('window-event-consistency','EventBus e;UILayer u;RenderEngine r(e,u);WindowController w(r);w.onSizeChanged(7000,-5);return r.viewport().width==4096&&u.bounds().width==4096&&e.lastSize().width==4096&&e.lastSize().height==1&&e.count()==1;'),
 ('repeated-still-emits','EventBus e;UILayer u;RenderEngine r(e,u);r.resize(Size{9000,2});r.resize(Size{9000,2});return e.count()==2&&e.lastSize().width==4096;')]},
 {'id':'events','title':'Suppress unchanged normalized resizes','kind':'Cross-component change','seed':'REQ-EVT-001',
 'prompt':'Implement revised REQ-EVT-001: compare a requested size after applying the shared normalization policy. If that normalized size equals the current viewport, leave layout unchanged and emit no event. Otherwise update viewport and layout, then publish exactly one matching event. Preserve REQ-UI-002 and the WindowController path. A fresh viewport is 1x1, so a request normalizing to 1x1 is a no-op.',
 'oracles':['aurora::RenderEngine::resize(Size)','aurora::Geometry::clampDimension(int)','aurora::UILayer::relayout(Size)','aurora::EventBus::publish(const ViewportChanged &)','aurora::WindowController::onSizeChanged(int, int)'],
 'checks':[
 ('initial-normalized-noop','EventBus e;UILayer u;RenderEngine r(e,u);r.resize(Size{0,-9});return e.count()==0&&r.viewport().width==1&&u.bounds().height==1;'),
 ('repeat-noop','EventBus e;UILayer u;RenderEngine r(e,u);r.resize(Size{200,300});r.resize(Size{200,300});return e.count()==1;'),
 ('normalize-before-comparison','EventBus e;UILayer u;RenderEngine r(e,u);r.resize(Size{8192,1});r.resize(Size{90000,-4});return e.count()==1&&r.viewport().width==8192;'),
 ('height-change-emits','EventBus e;UILayer u;RenderEngine r(e,u);r.resize(Size{200,300});r.resize(Size{200,301});return e.count()==2&&e.lastSize().height==301&&u.bounds().height==301;'),
 ('window-path','EventBus e;UILayer u;RenderEngine r(e,u);WindowController w(r);w.onSizeChanged(0,0);w.onSizeChanged(50,60);w.onSizeChanged(50,60);return e.count()==1&&r.viewport().width==50&&u.bounds().height==60;'),
 ('noop-leaves-layout','EventBus e;UILayer u;RenderEngine r(e,u);r.resize(Size{400,500});u.relayout(Size{10,20});r.resize(Size{400,500});return e.count()==1&&u.bounds().width==10&&u.bounds().height==20;')]}
]
def prepare_repo(dest,task):
 shutil.copytree(ROOT/'samples/aurora',dest,ignore=shutil.ignore_patterns('.atlas'))
 reqs=json.loads((dest/'requirements.json').read_text())
 if task['id']=='cache':
  reqs[2]['text']+=' Only nonnegative IDs are valid. Invalid insertions do not change storage or FIFO order; negative queries return false. Duplicate insertions do not advance eviction order.'
  reqs[2]['symbols']+=['aurora::AssetCache::contains(int)']
 elif task['id']=='limit':reqs[0]['text']=reqs[0]['text'].replace('8192','4096')+' Both integer and float Geometry::clampDimension overloads follow this range.'
 else:
  reqs[1]['text']='Normalize requested dimensions first. If both match the current viewport, do not change layout or emit an event. Otherwise update viewport and layout before publishing exactly one matching event.'
  reqs[1]['constraints']=['Compare normalized dimensions, including against the initial 1x1 viewport.','Preserve existing public interfaces and shared dimension policy.']
 atomic_json(dest/'requirements.json',reqs)

def acceptance(repo,task,temp):
 temp.mkdir(parents=True,exist_ok=True);source=temp/'acceptance.cpp';binary=temp/'acceptance'
 lines=['#include "RenderEngine.hpp"','#include "AssetCache.hpp"','#include <cstdlib>','using namespace aurora;']
 for i,(_,body) in enumerate(task['checks']):lines.append('bool check%d(){%s}'%(i,body))
 lines+=['int main(int argc,char**argv){if(argc!=2)return 2;switch(std::atoi(argv[1])){']
 for i in range(len(task['checks'])):lines.append('case %d:return check%d()?0:1;'%(i,i))
 lines+=['default:return 2;}}'];source.write_text('\n'.join(lines))
 command=['g++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(repo/'include'),*map(str,sorted((repo/'src').glob('*.cpp'))),str(source),'-o',str(binary)]
 built=subprocess.run(command,capture_output=True,text=True,timeout=60)
 if built.returncode:return {'passed':0,'total':len(task['checks']),'compile_error':built.stderr,'checks':[]}
 results=[]
 for i,(name,_) in enumerate(task['checks']):
  ran=subprocess.run([str(binary),str(i)],capture_output=True,timeout=5)
  results.append({'name':name,'passed':ran.returncode==0})
 return {'passed':sum(c['passed'] for c in results),'total':len(results),'checks':results}

def prepare(work):
 if work.exists():raise SystemExit('Refusing to overwrite existing trials: '+str(work))
 work.mkdir(parents=True)
 for task in TASKS:
  baseline=work/'baselines'/task['id'];prepare_repo(baseline,task)
  before=acceptance(baseline,task,work/'checks'/('before-'+task['id']))
  for arm in ['atlas','search']:
   run=work/(task['id']+'-'+arm);repo=run/'repo';shutil.copytree(baseline,repo)
   graph=build_index(repo) if arm=='atlas' else None
   config={'id':run.name,'arm':arm,'task_id':task['id'],'prompt':task['prompt'],'seed':task['seed'],'initial_fingerprint':fingerprint(inventory(repo)),'before_acceptance':before,'model':'inherited session model (no override)','reasoning':'inherited session setting (no override)','initial_parse':graph['parse_stats'] if graph else None,'status':'prepared'}
   atomic_json(run/'run.json',config)
 print(json.dumps({'prepared':[p.name for p in work.iterdir() if (p/'run.json').exists()]}))

def collect(work):
 out=ROOT/'experiments/pilot';out.mkdir(exist_ok=True)
 report={'schema_version':'1.0','title':'Controlled agent pilot','tasks':[{k:v for k,v in t.items() if k!='checks'} for t in TASKS],
 'method':{'arms':['Atlas tools plus file tools','File listing, literal text search, and source reads'],'runs_per_task_per_arm':1,'fresh_context':True,'tool_call_limit':40,'model':'inherited session model; no overrides','reasoning':'inherited session setting; no overrides','measurement':'JSON response characters and elapsed tool time; not model tokens or reasoning time','limitations':['Three small synthetic tasks with one run per arm; descriptive observations, not statistical evidence.','Both arms use logged wrappers, not unrestricted shell search.','Agent access boundaries are instruction-enforced; shared filesystem is not a security sandbox.','No model-token usage or provider reasoning telemetry is available.','Oracle coverage measures exposure to source, not whether the agent understood it.','Initial indexing and post-edit indexing are reported separately; shared host timing is noisy.','Atlas runs were instructed to demonstrate stale rejection and refresh; those extra workflow calls are separated from pre-edit discovery.','The requirement-change task mentions both numeric overloads, but the original graph links only the integer call path; agents may need supplemental discovery.']},'runs':[]}
 for task in TASKS:
  baseline=work/'baselines'/task['id']
  graph=build_index(baseline)
  for arm in ['atlas','search']:
   run=work/(task['id']+'-'+arm);config=json.loads((run/'run.json').read_text());repo=run/'repo'
   logs=[json.loads(s) for s in (run/'transcript.jsonl').read_text().splitlines() if s.strip()] if (run/'transcript.jsonl').exists() else []
   submission=json.loads((run/'submission.json').read_text()) if (run/'submission.json').exists() else None
   accepted=acceptance(repo,task,work/'checks'/run.name)
   try:visible=run_tests(repo)
   except Exception as e:visible={'passed':0,'total':8,'error':str(e)}
   try: final=build_index(repo)
   except Exception as e: final={'repository':{'fingerprint':fingerprint(inventory(repo))},'parse_stats':{'error':str(e)}}
   first_edit=next((i for i,r in enumerate(logs) if r['request']['operation']=='apply_edit' and 'result' in r['response']),len(logs))
   found=[];found_before=[]
   for name in task['oracles']:
    node=next(n for n in graph['nodes'] if n.get('signature')==name)
    seen=False
    for record_number,record in enumerate(logs):
     result=record['response'].get('result',{})
     if any(i.get('name')==name and i.get('code') for i in result.get('items',[])):seen=True
     source=result.get('source',{})
     if source.get('path')==node['path'] and source.get('line',0)<=node['line'] and source.get('end_line',0)>=node['end_line']:seen=True
    if seen:found.append(name)
    for record in logs[:first_edit]:
     result=record['response'].get('result',{});source=result.get('source',{})
     if any(i.get('name')==name and i.get('code') for i in result.get('items',[])) or (source.get('path')==node['path'] and source.get('line',0)<=node['line'] and source.get('end_line',0)>=node['end_line']):
      found_before.append(name);break
   patch=''
   for p in sorted(repo.rglob('*')):
    if p.is_file() and '.atlas' not in p.parts and (baseline/p.relative_to(repo)).exists():
     rel=p.relative_to(repo);old=(baseline/rel).read_text().splitlines(True);new=p.read_text().splitlines(True)
     patch+=''.join(difflib.unified_diff(old,new,fromfile='a/'+str(rel),tofile='b/'+str(rel)))
   (out/(run.name+'.patch')).write_text(patch)
   shutil.copyfile(run/'transcript.jsonl',out/(run.name+'.jsonl')) if logs else None
   retrieval={'get_task_context','lookup_symbol','traverse_dependencies','list_files','search_text','read_file'}
   reads=[r for r in logs if r['request']['operation'] in retrieval]
   record={**config,'status':'completed' if submission else 'not_submitted','acceptance':accepted,'visible_tests':visible,'submission':submission,
    'instructions':(run/'INSTRUCTIONS.md').read_text() if (run/'INSTRUCTIONS.md').exists() else None,
    'pre_edit_retrieval_chars':sum(r['response_chars'] for r in logs[:first_edit] if r['request']['operation'] in retrieval),
    'pre_edit_oracle':{'found':found_before,'missed':[n for n in task['oracles'] if n not in found_before],'total':len(task['oracles'])},
    'stale_rejections':sum(r['response'].get('error',{}).get('code')=='STALE_INDEX' for r in logs),
    'refreshes':[r['response']['result']['parse_stats'] for r in logs if r['request']['operation']=='refresh_index' and 'result' in r['response']],
    'tool_calls':len(logs),'tool_output_chars':sum(r['response_chars'] for r in logs),'retrieval_output_chars':sum(r['response_chars'] for r in reads),
    'tool_elapsed_ms':round(sum(r['elapsed_ms'] for r in logs),2),'retrieval_elapsed_ms':round(sum(r['elapsed_ms'] for r in reads),2),
    'oracle':{'found':found,'missed':[n for n in task['oracles'] if n not in found],'total':len(task['oracles'])},
    'final_fingerprint':final['repository']['fingerprint'],'evaluation_refresh':final['parse_stats'],'transcript':logs,'patch':patch}
   report['runs'].append(record)
 atomic_json(out/'report.json',report);atomic_json(ROOT/'public/generated/pilot-report.json',report)
 print(json.dumps([{k:r[k] for k in ['id','status','acceptance','retrieval_output_chars','oracle']} for r in report['runs']],indent=2))

def replay(work):
 """Recheck recorded edits and held-out tests. This is not a new model run."""
 if work.exists():raise SystemExit('Refusing to overwrite: '+str(work))
 work.mkdir(parents=True)
 report=json.loads((ROOT/'experiments/pilot/report.json').read_text());results=[]
 for recorded in report['runs']:
  task=next(t for t in TASKS if t['id']==recorded['task_id']);repo=work/recorded['id'];prepare_repo(repo,task)
  if fingerprint(inventory(repo))!=recorded['initial_fingerprint']:raise RuntimeError('Baseline changed; cannot faithfully replay '+recorded['id'])
  for record in recorded['transcript']:
   if record['request']['operation']!='apply_edit' or 'result' not in record['response']:continue
   edit=record['request']['arguments'];p=(repo/edit['path']).resolve()
   if not p.is_relative_to(repo.resolve()):raise ValueError('Edit escaped trial')
   text=p.read_text();count=text.count(edit['before'])
   if count<1 or count!=1 and not edit.get('all'):raise ValueError('Recorded edit no longer applies')
   p.write_text(text.replace(edit['before'],edit['after'],-1 if edit.get('all') else 1))
  if fingerprint(inventory(repo))!=recorded['final_fingerprint']:raise RuntimeError('Final source mismatch')
  accepted=acceptance(repo,task,work/'checks'/recorded['id']);visible=run_tests(repo)
  if accepted['checks']!=recorded['acceptance']['checks']:raise RuntimeError('Acceptance outcome changed')
  results.append({'id':recorded['id'],'fingerprint_matches':True,'acceptance':accepted,'visible_tests':{'passed':visible['passed'],'total':visible['total']}})
 atomic_json(work/'replay-results.json',results)
 print(json.dumps({'replayed_runs':len(results),'acceptance_passed':sum(r['acceptance']['passed'] for r in results),'acceptance_total':sum(r['acceptance']['total'] for r in results),'new_model_runs':False}))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('operation',choices=['prepare','collect','replay']);parser.add_argument('--work',type=Path,required=True);a=parser.parse_args()
 {'prepare':prepare,'collect':collect,'replay':replay}[a.operation](a.work.resolve())
