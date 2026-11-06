/** Local agent tools. No network server and no execution of manifest-supplied commands. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
import {getTaskContext,resolveSeed,ContextError} from '../public/retrieval.js';
const exec=promisify(execFile);
const project=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const ignored=new Set(['.git','.atlas','build','dist','node_modules','__pycache__']);
const extensions=new Set(['.cpp','.cc','.cxx','.c','.h','.hpp','.hh','.hxx']);
const manifests=new Set(['compile_commands.json','requirements.json','test_manifest.json']);
export const toolDefinitions=[
 {name:'lookup_symbol',description:'Exact ID/signature lookup, or bounded name/path substring discovery. Returns compiler IDs, spans and provenance.',arguments:{query:'string',exact:'boolean (default true)',limit:'1..30'}},
 {name:'get_task_context',description:'Requirements, reusable callees, callers, tests and code with reasons and omissions under a JSON character budget.',arguments:{seeds:'exact IDs/signatures[]',task:'string',budget_chars:'2000..128000',max_hops:'0..4',max_nodes:'1..100',detail:'full|compact'}},
 {name:'traverse_dependencies',description:'Bounded directional traversal over explicitly selected relationship types; reachability is potential impact.',arguments:{seed:'exact ID/signature',direction:'incoming|outgoing|both',types:'relationship types[]',max_hops:'0..4',max_nodes:'1..100'}},
 {name:'refresh_index',description:'Reparse changed translation units and atomically replace the index; no arbitrary commands.',arguments:{}}
];
export async function verifyFreshness(repo,graph) {
 const root=await fs.realpath(repo),actual={};
 async function walk(directory){for(const ent of await fs.readdir(directory,{withFileTypes:true})){
  if(ignored.has(ent.name))continue;
  const full=path.join(directory,ent.name);
  // Directory symlinks are not followed. Source symlinks must remain inside the root.
  if(ent.isDirectory()){await walk(full);continue;}
  if(!extensions.has(path.extname(ent.name))&&!manifests.has(ent.name))continue;
  const real=await fs.realpath(full),relative=path.relative(root,real);
  if(relative==='..'||relative.startsWith('..'+path.sep)||path.isAbsolute(relative))throw new ContextError('UNSAFE_SOURCE','Source escaped repository.');
  actual[path.relative(root,full).split(path.sep).join('/')]=hash(await fs.readFile(full));
 }}
 await walk(root);
 const changed=[...new Set([...Object.keys(actual),...Object.keys(graph.inputs)])].filter(p=>actual[p]!==graph.inputs[p]).sort();
 if(changed.length)throw new ContextError('STALE_INDEX','Repository inputs changed. Reindex before retrieval.',{changed_files:changed});
}
const fail=(s)=>{throw new ContextError('INVALID_REQUEST',s)};
function fields(a,allowed){if(!a||typeof a!=='object'||Array.isArray(a))fail('Arguments must be an object.');for(const k of Object.keys(a))if(!allowed.includes(k))fail('Unknown argument: '+k)}
function integer(n,low,high){if(!Number.isInteger(n)||n<low||n>high)fail(`Expected integer ${low}..${high}.`)}
function summary(n,g){return {id:n.id,name:n.signature||n.name,kind:n.kind,source:{path:n.path??null,line:n.line??null,end_line:n.end_line??null,content_hash:n.content_hash??g.inputs[n.path]??null},provenance:n.provenance||n.metadata?.provenance||'indexed repository'}}
export async function dispatchTool(repo,indexPath,message){
 if(!message||typeof message!=='object'||Array.isArray(message))fail('Request must be an object.');
 const op=message.operation,a=message.arguments??{};
 if(op==='list_tools'){fields(a,[]);return {protocol:'atlas-jsonl/1',tools:toolDefinitions}}
 if(op==='refresh_index'){
  fields(a,[]);
  try{const {stdout}=await exec(process.env.ATLAS_PYTHON||'python',['-m','atlas_engine','index','--repo',path.resolve(repo),'--output',path.resolve(indexPath)],{cwd:project,timeout:120000,maxBuffer:4*1024*1024});return JSON.parse(stdout)}
  catch(e){throw new ContextError('INDEX_FAILED','Index refresh failed.',{diagnostic:(e.stderr||e.message).slice(0,8000)})}
 }
 if(!toolDefinitions.some(t=>t.name===op))throw new ContextError('UNKNOWN_OPERATION','Unknown tool: '+op);
 let graph;try{graph=JSON.parse(await fs.readFile(indexPath,'utf8'))}catch(e){if(e.code==='ENOENT')throw new ContextError('INDEX_MISSING','Run refresh_index first.');throw e}
 await verifyFreshness(repo,graph);
 if(graph.schema_version!=='1.0')throw new ContextError('SCHEMA_MISMATCH','Unsupported graph schema.');
 let result;
 if(op==='get_task_context')result=getTaskContext(graph,a,{freshness:'verified_local_inputs'});
 if(op==='lookup_symbol'){
  fields(a,['query','exact','limit']);const {query,exact=true,limit=20}=a;
  if(typeof query!=='string'||!query.trim()||query.length>500||typeof exact!=='boolean')fail('Supply a nonempty query and boolean exact.');integer(limit,1,30);
  const matches=exact?[resolveSeed(graph,query)]:graph.nodes.filter(n=>[n.id,n.signature,n.name,n.path].some(v=>v?.toLowerCase().includes(query.toLowerCase())));
  result={operation:op,repository:graph.repository,freshness:'verified_local_inputs',items:matches.slice(0,limit).map(n=>summary(n,graph)),total_matches:matches.length,truncated:matches.length>limit};
 }
 if(op==='traverse_dependencies'){
  fields(a,['seed','direction','types','max_hops','max_nodes']);const {seed,direction='incoming',types=['calls','includes'],max_hops=2,max_nodes=40}=a;
  if(typeof seed!=='string'||!['incoming','outgoing','both'].includes(direction))fail('Invalid seed or direction.');integer(max_hops,0,4);integer(max_nodes,1,100);
  const supported=['calls','includes','implements','verifies','declared in','defined in','depends on'];
  if(!Array.isArray(types)||!types.length||types.some(t=>!supported.includes(t)))fail('Invalid relationship types.');
  const initial=resolveSeed(graph,seed),selected=new Map([[initial.id,{node:initial,depth:0,via:null,reason:'Exact requested seed'}]]),byId=new Map(graph.nodes.map(n=>[n.id,n]));let frontier=[initial.id],limited=false;
  for(let depth=1;depth<=max_hops;depth++){const next=[];for(const id of frontier)for(const edge of graph.edges){if(!types.includes(edge.type))continue;let other=null;if(direction!=='incoming'&&edge.from===id)other=edge.to;if(direction!=='outgoing'&&edge.to===id)other=edge.from;if(!other||selected.has(other))continue;if(selected.size>=max_nodes){limited=true;continue}selected.set(other,{node:byId.get(other),depth,via:id,reason:edge.type+' '+direction});next.push(other)}frontier=next;}
  result={operation:op,repository:graph.repository,freshness:'verified_local_inputs',items:[...selected.values()].map(({node,...rest})=>({...summary(node,graph),...rest})),relationships:graph.edges.filter(e=>types.includes(e.type)&&selected.has(e.from)&&selected.has(e.to)),coverage:{node_limit_reached:limited,hop_limit:max_hops},warning:'Bounded reachability is potential impact, not complete behavioral analysis.'};
 }
 await verifyFreshness(repo,graph);return result;
}
export async function handleRequest(repo,indexPath,message,{logPath}={}){
 const started=performance.now();let response;
 try{response={id:message?.id??null,result:await dispatchTool(repo,indexPath,message)}}catch(e){response={id:message?.id??null,error:{code:e.code||'INVALID_REQUEST',message:e.message,details:e.details||{}}}}
 if(logPath){await fs.mkdir(path.dirname(logPath),{recursive:true});await fs.appendFile(logPath,JSON.stringify({schema_version:'1.0',recorded_at:new Date().toISOString(),request:message,response,elapsed_ms:Math.round((performance.now()-started)*1000)/1000,response_chars:JSON.stringify(response).length})+'\n')}
 return response;
}
