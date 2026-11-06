#!/usr/bin/env node
/** Local agent entry point with explicit refresh. JSONL protocol is not MCP. */
import path from 'node:path';
import readline from 'node:readline';
import {fileURLToPath} from 'node:url';
import {dispatchTool,handleRequest} from './tools.mjs';
export {verifyFreshness} from './tools.mjs';
export const serveRequest=dispatchTool;
async function main(){
  const args=process.argv.slice(2);const operation=args.shift();
  let repo='samples/aurora',indexPath=null,logPath=null,request={seeds:[]};
  while(args.length){const flag=args.shift(),value=args.shift();if(value===undefined)throw Error('Missing value for '+flag);
    if(flag==='--detail')request.detail=value;else if(flag==='--log')logPath=value;else if(flag==='--repo')repo=value;else if(flag==='--index')indexPath=value;else if(flag==='--seed')request.seeds.push(value);else if(flag==='--task')request.task=value;else if(flag==='--budget-chars')request.budget_chars=Number(value);else if(flag==='--max-hops')request.max_hops=Number(value);else if(flag==='--max-nodes')request.max_nodes=Number(value);else throw Error('Unknown argument: '+flag);}
  indexPath??=path.join(repo,'.atlas','index.json');
  if(operation==='context'){const response=await handleRequest(repo,indexPath,{operation:'get_task_context',arguments:request},{logPath});if(response.error){process.stderr.write(JSON.stringify(response)+'\n');process.exitCode=2}else process.stdout.write(JSON.stringify(response.result)+'\n');}
  else if(operation==='serve'){
    const rl=readline.createInterface({input:process.stdin,crlfDelay:Infinity});
    for await(const line of rl){if(!line.trim())continue;let message;try{if(line.length>16384)throw Error('Request exceeds 16KB');message=JSON.parse(line);const response=await handleRequest(repo,indexPath,message,{logPath});process.stdout.write(JSON.stringify(response)+'\n');}catch(error){process.stdout.write(JSON.stringify({id:message?.id??null,error:{code:error.code||'INVALID_REQUEST',message:error.message,details:error.details||{}}})+'\n');}}
  } else throw Error('Usage: node scripts/agent.mjs context|serve --repo PATH [--seed ID] [--budget-chars N]');
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(error=>{process.stderr.write(JSON.stringify({error:{code:error.code||'ERROR',message:error.message,details:error.details||{}}})+'\n');process.exitCode=2;});
