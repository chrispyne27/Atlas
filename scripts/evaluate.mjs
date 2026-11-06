import fs from 'node:fs/promises';
import {getTaskContext} from '../public/retrieval.js';
import {verifyFreshness} from './agent.mjs';
const before=JSON.parse(await fs.readFile('experiments/before-index.json','utf8'));
const beforeContext=JSON.parse(await fs.readFile('experiments/before-context.json','utf8'));
const after=JSON.parse(await fs.readFile('samples/aurora/.atlas/index.json','utf8'));
await verifyFreshness('samples/aurora',after);
const afterContext=getTaskContext(after,{seeds:['REQ-UI-002'],task:'Normalize viewport resizing while preserving layout and event requirements. Reuse existing mechanisms.',budget_chars:32000},{freshness:'verified_local_inputs'});
const required=['REQ-UI-002','REQ-EVT-001','aurora::RenderEngine::resize(Size)','aurora::UILayer::relayout(Size)','aurora::LayoutEngine::resolve(Size)','aurora::Geometry::clampDimension(int)','aurora::WindowController::onSizeChanged(int, int)','aurora::EventBus::publish(const ViewportChanged &)',...before.nodes.filter(n=>n.kind==='test'&&n.fixture_id!=='TEST-cacheEvicts').map(n=>n.signature)];
const oracle=required.map(q=>before.nodes.find(n=>n.id===q||n.signature===q));
if(oracle.some(n=>!n))throw Error('Invalid evaluation oracle');
const baselinePaths=[],baselineTexts=[];
for(const [p]of Object.entries(before.inputs)){
 let text=await fs.readFile('samples/aurora/'+p,'utf8');if(p==='src/RenderEngine.cpp')text=await fs.readFile('experiments/RenderEngine.before.cpp','utf8');
 if(/resize|viewport/i.test(text)){baselinePaths.push(p);baselineTexts.push(text);}
}
const selected=new Set(beforeContext.items.map(i=>i.id));
const baselineFound=oracle.filter(n=>baselinePaths.includes(n.path));
const beforeTests=JSON.parse(await fs.readFile('experiments/before-tests.json','utf8'));
const afterTests=JSON.parse(await fs.readFile('experiments/after-tests.json','utf8'));
const refresh=JSON.parse(await fs.readFile('experiments/after-refresh-index.json','utf8'));
if(beforeTests.source_fingerprint!==before.repository.fingerprint||afterTests.source_fingerprint!==after.repository.fingerprint)throw Error('Test evidence does not match evaluated source snapshots');
const report={milestone:'One requirement-aligned C++ change with graph-selected context',task:'Normalize viewport resize dimensions consistently',
 methodology:'One authored fixture and one task. The assistant inspected graph-selected context and made the recorded fix. This is not a blinded or autonomous-agent productivity benchmark. Baseline is case-insensitive resize|viewport text search followed by reading complete matching input files. Oracle was explicitly selected for this task.',
 oracle:oracle.map(n=>({id:n.id,name:n.signature||n.name})),
 comparison:{graph:{oracle_found:oracle.filter(n=>selected.has(n.id)).length,oracle_total:oracle.length,selected_items:beforeContext.items.length,source_code_chars:beforeContext.items.reduce((a,i)=>a+(i.code?.length||0),0),serialized_packet_chars:beforeContext.serialized_chars},text_search:{oracle_found:baselineFound.length,oracle_total:oracle.length,matched_files:baselinePaths,source_chars:baselineTexts.join('\n').length,missing:oracle.filter(n=>!baselinePaths.includes(n.path)).map(n=>n.signature||n.name)}},
 before:{fingerprint:before.repository.fingerprint,passed:beforeTests.passed,total:beforeTests.total},
 after:{fingerprint:after.repository.fingerprint,passed:afterTests.passed,total:afterTests.total},
 refresh:refresh.parse_stats,stale_rejection:JSON.parse(await fs.readFile('experiments/stale-rejection.json','utf8')),
 limits:['No model-token measurement: all sizes are characters.','The structured graph packet includes provenance and relationships; its overhead can exceed raw file reads on this tiny fixture.','Source-code character counts exclude context metadata and requirement text.','Tests show fixture behavior only; no large-codebase scaling claim.','There are unresolved/implicit references; the index does not silently invent their targets.']};
await verifyFreshness('samples/aurora',after);
await fs.writeFile('experiments/after-context.json',JSON.stringify(afterContext,null,2)+'\n');
await fs.mkdir('public/generated',{recursive:true});
await fs.writeFile('public/generated/indexed-graph.json',JSON.stringify(after,null,2)+'\n');
await fs.writeFile('public/generated/task-report.json',JSON.stringify(report,null,2)+'\n');
await fs.writeFile('experiments/evaluation.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({comparison:report.comparison,before:report.before,after:report.after,refresh:report.refresh},null,2));
