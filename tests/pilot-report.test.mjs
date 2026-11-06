import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const saved=await fs.readFile('experiments/pilot/report.json','utf8');
assert.equal(await fs.readFile('public/generated/pilot-report.json','utf8'),saved,'deployed evidence matches recorded evidence');
const report=JSON.parse(saved);assert.equal(report.runs.length,6);
for(const task of report.tasks){
 const arms=report.runs.filter(r=>r.task_id===task.id);assert.equal(arms.length,2);assert.equal(arms[0].initial_fingerprint,arms[1].initial_fingerprint,'paired runs must start from identical source');
 for(const run of arms){
  assert.equal(run.status,'completed');assert.ok(run.tool_calls<=40);assert.equal(run.tool_calls,run.transcript.length);assert.ok(run.instructions.includes(run.prompt));
  const logs=(await fs.readFile('experiments/pilot/'+run.id+'.jsonl','utf8')).trim().split('\n').map(JSON.parse);assert.deepEqual(logs,run.transcript);
  assert.equal(run.tool_output_chars,logs.reduce((s,r)=>s+JSON.stringify(r.response).length,0));
  assert.equal(run.acceptance.passed,run.acceptance.checks.filter(c=>c.passed).length);
  assert.equal(run.acceptance.total,run.acceptance.checks.length);
  assert.equal(run.pre_edit_oracle.found.length+run.pre_edit_oracle.missed.length,run.pre_edit_oracle.total);
  if(run.arm==='search')assert.ok(!logs.some(r=>['get_task_context','refresh_index','lookup_symbol','traverse_dependencies'].includes(r.request.operation)));
  if(run.arm==='atlas'){
   assert.ok(run.stale_rejections>0);assert.ok(run.refreshes.length>0);
   for(const r of logs)if(r.response.result?.operation==='get_task_context'){
    const p=r.response.result;assert.equal(p.serialized_chars,JSON.stringify(p).length);assert.ok(p.serialized_chars<=p.request.budget_chars);assert.ok(p.items.every(i=>i.reason&&i.provenance));
   }
  }
 }
}
console.log('PASS: paired baselines, complete recorded runs, transcript/export integrity, real response sizes, arm separation, bounded context, and freshness evidence.');
