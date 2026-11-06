#!/usr/bin/env node
/** Logged tools used identically by both pilot arms; graph tools are enabled only for Atlas. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
import {dispatchTool} from './tools.mjs';
const exec=promisify(execFile),project=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const [runDirectory,encoded]=process.argv.slice(2);
const run=path.resolve(runDirectory),config=JSON.parse(await fs.readFile(path.join(run,'run.json'),'utf8')),repo=path.join(run,'repo');
const request=JSON.parse(encoded),log=path.join(run,'transcript.jsonl'),started=performance.now();
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
let response;
async function files(){const output=[];for(const dir of ['src','include','tests'])for(const name of await fs.readdir(path.join(repo,dir)))output.push(dir+'/'+name);return [...output,'requirements.json','test_manifest.json','compile_commands.json'].sort()}
async function file(p){if(typeof p!=='string'||!(await files()).includes(p))throw Error('Path must be a listed repository file.');const root=await fs.realpath(repo),real=await fs.realpath(path.join(repo,p));if(!real.startsWith(root+path.sep))throw Error('Path escaped repository.');return real}
try{
 const prior=await fs.readFile(log,'utf8').catch(()=>''),calls=prior.trim()?prior.trim().split('\n').length:0;
 if(calls>=40)throw Error('Trial tool call limit (40) reached.');
 const op=request.operation,a=request.arguments||{};let result;
 if(['lookup_symbol','get_task_context','traverse_dependencies','refresh_index','list_tools'].includes(op)){
  if(config.arm!=='atlas')throw Error('Graph tools are unavailable in the text-search arm.');
  result=await dispatchTool(repo,path.join(repo,'.atlas/index.json'),request);
 }else if(op==='list_files')result={files:await files()};
 else if(op==='read_file'){
  const p=await file(a.path),text=await fs.readFile(p,'utf8'),lines=text.split('\n'),start=a.start_line??1,end=a.end_line??lines.length;
  if(!Number.isInteger(start)||!Number.isInteger(end)||start<1||end<start||end-start>500)throw Error('Read at most 501 lines per call.');
  result={source:{path:a.path,line:start,end_line:Math.min(end,lines.length),content_hash:hash(text)},code:lines.slice(start-1,end).join('\n')};
 }else if(op==='search_text'){
  const queries=a.queries||[a.query];if(!Array.isArray(queries)||!queries.length||queries.length>8||queries.some(q=>typeof q!=='string'||!q||q.length>200))throw Error('Supply 1..8 nonempty literal queries.');
  const matches=[];for(const p of await files()){const text=await fs.readFile(await file(p),'utf8');text.split('\n').forEach((line,i)=>{if(queries.some(q=>line.toLowerCase().includes(q.toLowerCase())))matches.push({path:p,line:i+1,text:line})})}
  result={matches:matches.slice(0,100),total_matches:matches.length,truncated:matches.length>100};
 }else if(op==='apply_edit'){
  if(!/^(src|include|tests)\//.test(a.path))throw Error('Only fixture source, headers and visible tests may be edited.');
  const p=await file(a.path),before=await fs.readFile(p,'utf8');
  if(typeof a.before!=='string'||!a.before||typeof a.after!=='string')throw Error('Supply nonempty before and string after.');
  const count=before.split(a.before).length-1;if(count!==1&&!a.all)throw Error('Expected exactly one match; found '+count);if(!count)throw Error('No matching text.');
  const after=a.all?before.split(a.before).join(a.after):before.replace(a.before,a.after);
  await fs.writeFile(p,after);result={path:a.path,replacements:count,before_hash:hash(before),after_hash:hash(after)};
 }else if(op==='run_tests'){
  try{const {stdout}=await exec(process.env.ATLAS_PYTHON||'python',['-m','atlas_engine','test','--repo',repo],{cwd:project,timeout:90000,maxBuffer:1024*1024});result=JSON.parse(stdout)}catch(e){if(e.stdout?.trim().startsWith('{'))result=JSON.parse(e.stdout);else throw Error((e.stderr||e.message).slice(0,8000))}
 }else if(op==='finish'){
  if(typeof a.summary!=='string'||!Array.isArray(a.affected_symbols))throw Error('Supply summary and affected_symbols.');
  await fs.writeFile(path.join(run,'submission.json'),JSON.stringify(a,null,2));result={submitted:true};
 }else throw Error('Unknown tool: '+op);
 response={id:request.id??null,result};
}catch(e){response={id:request.id??null,error:{code:e.code||'TOOL_ERROR',message:e.message,details:e.details||{}}}}
const record={schema_version:'1.0',recorded_at:new Date().toISOString(),request,response,elapsed_ms:Math.round((performance.now()-started)*1000)/1000,response_chars:JSON.stringify(response).length};
await fs.appendFile(log,JSON.stringify(record)+'\n');process.stdout.write(JSON.stringify(response)+'\n');
