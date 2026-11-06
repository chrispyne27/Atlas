import assert from 'node:assert/strict';
import {nodes,byId,edges,requirements,model,stages} from '../public/data.js';
assert.equal(new Set(nodes.map(n=>n.id)).size,nodes.length,'entity IDs are unique');
for(const e of edges){assert.ok(byId[e.from],e.from);assert.ok(byId[e.to],e.to)}
for(const r of requirements){for(const method of r.methods){assert.ok(edges.some(e=>e.from===method&&e.to===r.id&&e.type==='implements'))}if(r.test){assert.ok(edges.some(e=>e.from===r.test&&e.to===r.id&&e.type==='verifies'))}assert.equal(r.status,!r.methods.length?'Unlinked':r.test?'Covered':'Partial')}
assert.equal(requirements.filter(r=>r.status==='Covered').length,4);
const base=model({});const twice=model({loc:2000000});assert.equal(twice.full,base.full*2);assert.equal(twice.disk,base.disk*2);
assert.ok(model({workers:8}).full<base.full);assert.ok(model({workers:8}).memory>base.memory);
assert.ok(model({fanout:9}).incremental>base.incremental);
assert.ok(model({enabled:stages.map(s=>s.id)}).full>base.full);
assert.equal(model({changed:30,fanout:10}).affected,100);
for(const w of [1,4,16])for(const loc of [100000,10000000])for(const changed of [1,30]){const m=model({workers:w,loc,changed,fanout:10});assert.ok(m.full>0&&m.memory>0&&m.disk>0);assert.ok(m.incremental<=m.full+2.00001)}
console.log('PASS: graph integrity, requirement coverage, scale, worker and dependency tradeoffs, invalidation bounds.');
