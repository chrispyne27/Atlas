import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {dispatchTool,handleRequest} from '../scripts/tools.mjs';
import {getTaskContext} from '../public/retrieval.js';
const temp=await fs.mkdtemp(path.join(os.tmpdir(),'atlas-tools-')),repo=path.join(temp,'repo'),index=path.join(repo,'.atlas/index.json'),log=path.join(temp,'calls.jsonl');
await fs.cp('samples/aurora',repo,{recursive:true});
try {
 await fs.mkdir(path.dirname(index),{recursive:true});await fs.copyFile('public/generated/indexed-graph.json',index);
 const graph=JSON.parse(await fs.readFile(index,'utf8'));
 const request=(operation,args={})=>dispatchTool(repo,index,{operation,arguments:args});
 assert.equal((await request('list_tools')).tools.length,4);
 const exact=await request('lookup_symbol',{query:'aurora::Geometry::clampDimension(int)'});
 assert.equal(exact.items.length,1);assert.equal(exact.items[0].source.path,'src/Geometry.cpp');
 await assert.rejects(()=>request('lookup_symbol',{query:'aurora::Geometry::clampDimension'}),e=>e.code==='AMBIGUOUS_SEED');
 const fuzzy=await request('lookup_symbol',{query:'clampDimension',exact:false,limit:1});assert.equal(fuzzy.total_matches,2);assert.ok(fuzzy.truncated);
 const incoming=await request('traverse_dependencies',{seed:'aurora::Geometry::clampDimension(int)',direction:'incoming',types:['calls'],max_hops:1});
 assert.ok(incoming.items.some(n=>n.name==='aurora::RenderEngine::resize(Size)'));
 assert.ok(incoming.items.some(n=>n.name==='aurora::LayoutEngine::resolve(Size)'));
 assert.ok(!incoming.items.some(n=>n.name.includes('AssetCache')));
 const outgoing=await request('traverse_dependencies',{seed:'aurora::Geometry::clampDimension(int)',direction:'outgoing',types:['calls'],max_hops:1});assert.equal(outgoing.items.length,1);
 assert.ok((await request('traverse_dependencies',{seed:'REQ-UI-002',direction:'both',types:['implements'],max_nodes:1})).coverage.node_limit_reached);
 for(const args of [{seed:'REQ-UI-002',types:['made-up']},{seed:'REQ-UI-002',max_hops:9},{query:'x',exact:'false'}])await assert.rejects(()=>request(args.query?'lookup_symbol':'traverse_dependencies',args),e=>e.code==='INVALID_REQUEST');
 const full=getTaskContext(graph,{seeds:['REQ-UI-002'],budget_chars:64000});
 const compact=getTaskContext(graph,{seeds:['REQ-UI-002'],budget_chars:64000,detail:'compact'});
 assert.ok(compact.serialized_chars<full.serialized_chars);
 assert.deepEqual(compact.items.map(n=>n.id),full.items.map(n=>n.id));
 for(const item of compact.items){const f=full.items.find(n=>n.id===item.id);assert.equal(item.code,f.code);assert.deepEqual(item.source,f.source);assert.equal(item.reason,f.reason);if(item.kind==='requirement')assert.deepEqual(item.metadata,f.metadata)}
 await fs.appendFile(path.join(repo,'src/Geometry.cpp'),'\n// Tool refresh integration test\n');
 for(const operation of ['lookup_symbol','traverse_dependencies','get_task_context']){
  const response=await handleRequest(repo,index,{id:operation,operation,arguments:{}},{logPath:log});assert.equal(response.error.code,'STALE_INDEX');
 }
 const refresh=await request('refresh_index');assert.equal(refresh.parse_stats.translation_units,6);
 const fresh=await request('get_task_context',{seeds:['REQ-UI-002'],detail:'compact',budget_chars:32000});assert.equal(fresh.freshness,'verified_local_inputs');
 assert.notEqual(fresh.repository.fingerprint,graph.repository.fingerprint);
 const noop=await request('refresh_index');assert.equal(noop.parse_stats.reused.length,6);
 const stable=await fs.readFile(index,'utf8');
 await fs.appendFile(path.join(repo,'src/Geometry.cpp'),'\nnot valid C++\n');
 await assert.rejects(()=>request('refresh_index'),e=>e.code==='INDEX_FAILED');assert.equal(await fs.readFile(index,'utf8'),stable);
 const records=(await fs.readFile(log,'utf8')).trim().split('\n').map(JSON.parse);
 assert.equal(records.length,3);for(const r of records)assert.equal(r.response_chars,JSON.stringify(r.response).length);
 console.log('PASS: agent discovery, directional traversal, bounds, compact evidence preservation, freshness across all queries, refresh, parse failure preservation, and error logging.');
}finally{await fs.rm(temp,{recursive:true,force:true})}
