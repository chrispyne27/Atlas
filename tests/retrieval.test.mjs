import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {getTaskContext,resolveSeed} from '../public/retrieval.js';
import {verifyFreshness,serveRequest} from '../scripts/agent.mjs';
const indexPath=await fs.access('samples/aurora/.atlas/index.json').then(()=> 'samples/aurora/.atlas/index.json').catch(()=> 'public/generated/indexed-graph.json');
const graph=JSON.parse(await fs.readFile(indexPath,'utf8'));
const req={seeds:['REQ-UI-002'],task:'Normalize invalid viewport sizes',budget_chars:32000};
const context=getTaskContext(graph,req);
for(const name of ['aurora::RenderEngine::resize(Size)','aurora::Geometry::clampDimension(int)','aurora::WindowController::onSizeChanged(int, int)','Publish after layout'])assert.ok(context.items.some(i=>i.name===name),name);
assert.ok(!context.items.some(i=>i.name.includes('AssetCache')));
assert.deepEqual(context,getTaskContext(graph,req),'deterministic retrieval');
for(const budget of [2000,3000,5000,8000,16000,32000]){
  let p; try { p=getTaskContext(graph,{...req,budget_chars:budget}); } catch(e) { assert.equal(e.code,'BUDGET_TOO_SMALL'); assert.ok(budget<8000); continue; }
  assert.ok(JSON.stringify(p).length<=budget);
  assert.equal(p.serialized_chars,JSON.stringify(p).length);
  assert.equal(p.coverage.returned_items,p.items.length);
  assert.equal(p.coverage.omitted_for_budget,p.coverage.candidate_items-p.items.length);
}
assert.throws(()=>resolveSeed(graph,'aurora::Geometry::clampDimension'),e=>e.code==='AMBIGUOUS_SEED'&&e.details.candidates.length===2);
assert.throws(()=>resolveSeed(graph,'missing'),e=>e.code==='UNKNOWN_SEED');
assert.throws(()=>getTaskContext(graph,{seeds:['REQ-UI-002'],max_hops:-1}),e=>e.code==='INVALID_REQUEST');
assert.throws(()=>getTaskContext(graph,{seeds:['REQ-UI-002'],unexpected:true}),e=>e.code==='INVALID_REQUEST');
const bounded=getTaskContext(graph,{...req,max_nodes:5});assert.ok(bounded.items.length<=5);assert.equal(bounded.coverage.node_limit_reached,true);
const zero=getTaskContext(graph,{...req,max_hops:0});assert.equal(zero.items.length,1);
const temp=await fs.mkdtemp(path.join(os.tmpdir(),'atlas-freshness-'));
try{
 await fs.cp('samples/aurora',temp,{recursive:true});
 await verifyFreshness(temp,graph);
 await fs.appendFile(path.join(temp,'src/Geometry.cpp'),'\n// edited\n');
 await assert.rejects(()=>verifyFreshness(temp,graph),e=>e.code==='STALE_INDEX'&&e.details.changed_files.includes('src/Geometry.cpp'));
 await fs.copyFile('samples/aurora/src/Geometry.cpp',path.join(temp,'src/Geometry.cpp'));
 await fs.writeFile(path.join(temp,'include/Added.hpp'),'// new file');
 await assert.rejects(()=>verifyFreshness(temp,graph),e=>e.code==='STALE_INDEX');
 await fs.rm(path.join(temp,'include/Added.hpp'));
 await fs.rm(path.join(temp,'include/Geometry.hpp'));
 await assert.rejects(()=>verifyFreshness(temp,graph),e=>e.code==='STALE_INDEX');
}finally{await fs.rm(temp,{recursive:true,force:true});}
const served=await serveRequest('samples/aurora',indexPath,{operation:'get_task_context',arguments:req});assert.equal(served.freshness,'verified_local_inputs');
console.log('PASS: exact and overloaded identities, context relevance, deterministic budgets, omissions, traversal bounds, input validation, local freshness for edits/additions/deletions, and agent request path.');
