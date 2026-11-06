/** Pure graph-first retrieval shared by the browser and the local agent CLI.
 * The caller is responsible for freshness: local CLI hashes disk; browser declares a deployed snapshot.
 */
export class ContextError extends Error {
  constructor(code, message, details = {}) { super(message); this.code = code; this.details = details; }
}
const fail = (code, message, details) => { throw new ContextError(code, message, details); };
export function resolveSeed(graph, query) {
  const exact = graph.nodes.filter(n => n.id === query || n.signature === query);
  const matches = exact.length ? exact : graph.nodes.filter(n => n.name === query || n.fixture_id === query);
  if (!matches.length) fail('UNKNOWN_SEED', `No exact entity matches: ${query}`);
  if (matches.length > 1) fail('AMBIGUOUS_SEED', `Use a complete signature or entity ID: ${query}`, {candidates:matches.map(n=>n.signature || n.id)});
  return matches[0];
}
export function getTaskContext(graph, request = {}, {freshness='deployed_snapshot'} = {}) {
  if (graph.schema_version !== '1.0') fail('SCHEMA_MISMATCH', 'Unsupported graph schema.');
  const allowed = ['seeds','task','budget_chars','max_hops','max_nodes','detail'];
  for (const key of Object.keys(request)) if (!allowed.includes(key)) fail('INVALID_REQUEST',`Unknown request field: ${key}`);
  const {seeds=[], task='', budget_chars=16000, max_hops=3, max_nodes=60, detail='full'} = request;
  if (!Array.isArray(seeds) || !seeds.length || seeds.length>10 || seeds.some(s=>typeof s!=='string'||!s||s.length>500)) fail('INVALID_REQUEST','Supply 1–10 exact seed IDs or signatures.');
  if(typeof task!=='string'||task.length>2000) fail('INVALID_REQUEST','Task must be a string of at most 2000 characters.');
  for (const [name,value,low,high] of [['budget_chars',budget_chars,2000,128000],['max_hops',max_hops,0,4],['max_nodes',max_nodes,1,100]]) {
    if(!Number.isInteger(value)||value<low||value>high) fail('INVALID_REQUEST',`${name} must be an integer from ${low} through ${high}.`);
  }
  if(!['full','compact'].includes(detail)) fail('INVALID_REQUEST','detail must be full or compact.');
  const byId = new Map(graph.nodes.map(n=>[n.id,n]));
  const initial=[...new Set(seeds.map(s=>resolveSeed(graph,s).id))];
  if(initial.length>max_nodes) fail('INVALID_REQUEST','max_nodes must accommodate all seeds.');
  const adjacency=new Map();
  for(const e of graph.edges) {
    if(!['calls','implements','verifies','declared in'].includes(e.type)) continue;
    for(const [from,to,direction] of [[e.from,e.to,'outgoing'],[e.to,e.from,'incoming']]) {
      if(!adjacency.has(from)) adjacency.set(from,[]);
      adjacency.get(from).push({id:to,edge:e,direction});
    }
  }
  const selected = new Map(initial.map(id=>[id,{id,depth:0,reason:'Exact requested seed',via:null,priority:0}]));
  let frontier=[...initial], nodeLimit=false;
  for(let depth=1;depth<=max_hops&&frontier.length;depth++) {
    const proposals=[];
    for(const id of frontier) {
      const from=byId.get(id);
      // Evidence/tests/files are terminal: do not expand a test harness into the entire repository.
      if((from.kind==='test'||from.kind==='file')&&!initial.includes(id)) continue;
      for(const a of adjacency.get(id)||[]) {
        const target=byId.get(a.id);
        if(!target||target.harness||selected.has(a.id)) continue;
        if(a.edge.type==='declared in'&&a.direction==='incoming') continue;
        if(a.edge.type==='calls'&&a.direction==='incoming'&&target.path?.startsWith('tests/')&&target.kind!=='test') continue;
        const priority=target.kind==='requirement'?1:target.kind==='test'?4:a.edge.type==='implements'?2:a.edge.type==='declared in'?6:3;
        proposals.push({id:a.id,depth,priority,via:id,edge:a.edge.type,direction:a.direction,
          reason:target.kind==='requirement'?'Requirement constraining selected implementation':target.kind==='test'?'Linked executable verification fixture':a.edge.type==='implements'?'Explicit implementation mapping':a.edge.type==='declared in'?'Declaration and type context':a.direction==='incoming'?'Caller potentially affected by this change':'Existing callee that may be reused or affected'});
      }
    }
    proposals.sort((a,b)=>a.priority-b.priority||a.id.localeCompare(b.id));
    frontier=[];
    for(const p of proposals){if(selected.has(p.id))continue;if(selected.size>=max_nodes){nodeLimit=true;continue}selected.set(p.id,p);frontier.push(p.id)}
  }
  const ordered=[...selected.values()].sort((a,b)=>a.priority-b.priority||a.depth-b.depth||a.id.localeCompare(b.id));
  const unresolved=graph.unresolved.filter(u=>selected.has(u.owner));
  const packet={schema_version:'1.0',operation:'get_task_context',task,repository:graph.repository,
    freshness,request:{seeds,budget_chars,max_hops,max_nodes,detail},items:[],relationships:[],
    coverage:{candidate_items:selected.size,returned_items:0,omitted_for_budget:0,omitted_ids:[],node_limit_reached:nodeLimit,hop_limit:max_hops,complete:false},
    unresolved:{count:unresolved.length,samples:unresolved.slice(0,5)},
    warnings:['Graph reachability is potential impact, not proof of behavioral impact.','Requirements and verification links are authored mappings; inspect test evidence separately.','Character budget measures compact JSON characters, not model tokens.'],
    serialized_chars:0};
  if(freshness==='deployed_snapshot')packet.warnings.push('Build-time snapshot only. This browser cannot inspect the live repository or run a compiler.');
  const makeItem=c=>{const n=byId.get(c.id);return {id:n.id,kind:n.kind,name:n.signature||n.name,reason:c.reason,depth:c.depth,via:c.via,
    source:n.path?{path:n.path,line:n.line??null,end_line:n.end_line??null,content_hash:n.content_hash??graph.inputs[n.path]??null}:null,
    provenance:n.provenance||n.metadata?.provenance||'indexed repository',
    ...(detail==='full'||n.kind==='requirement'?{metadata:n.metadata||{}}:{}),...(n.constraints?{constraints:n.constraints}:{}),...(n.description&&(detail==='full'||n.kind==='requirement')?{description:n.description}:{}),...(n.code?{code:n.code}:{}),...(n.evidence?{test_evidence:n.evidence}:{})};};
  function finalize() {
    const ids=new Set(packet.items.map(i=>i.id));
    packet.relationships=graph.edges.filter(e=>ids.has(e.from)&&ids.has(e.to)&&['calls','implements','verifies','declared in'].includes(e.type)).map(e=>({from:e.from,to:e.to,type:e.type,provenance:e.provenance}));
    const omitted=ordered.filter(c=>!ids.has(c.id));
    packet.coverage.returned_items=ids.size;
    packet.coverage.omitted_for_budget=omitted.length;
    packet.coverage.omitted_ids=omitted.slice(0,8).map(c=>c.id);
    packet.coverage.complete=!omitted.length&&!nodeLimit; // Complete only within the explicitly bounded neighborhood.
    packet.serialized_chars=0;
    let previous=-1;
    while(previous!==packet.serialized_chars){previous=packet.serialized_chars;packet.serialized_chars=JSON.stringify(packet).length;}
  }
  // Reserve room for the honest omission/edge envelope by measuring the complete packet each time.
  for(const candidate of ordered){
    packet.items.push(makeItem(candidate));finalize();
    if(packet.serialized_chars>budget_chars){packet.items.pop();finalize();if(initial.includes(candidate.id))fail('BUDGET_TOO_SMALL','Requested seed does not fit as a complete item. Increase budget.',{seed:candidate.id});}
  }
  finalize();
  if(packet.serialized_chars>budget_chars)fail('BUDGET_TOO_SMALL','Context envelope exceeds the budget. Increase budget.');
  return packet;
}
