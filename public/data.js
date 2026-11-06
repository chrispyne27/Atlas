import * as illustrated from './illustrated.js';
export const {stages,model}=illustrated;
export let nodes=illustrated.nodes, symbols=illustrated.symbols, requirements=illustrated.requirements,
  tests=illustrated.tests, components=illustrated.components, edges=illustrated.edges, byId=illustrated.byId;
export let activeDataset='illustrated',activeGraph=null;
let indexedPromise;
export function loadIndexedGraph(){
  indexedPromise??=fetch('/generated/indexed-graph.json').then(r=>{if(!r.ok)throw Error('The indexed fixture could not be loaded.');return r.json();}).catch(e=>{indexedPromise=null;throw e});
  return indexedPromise;
}
export async function setDataset(id){
  if(id==='indexed'){
    const graph=await loadIndexedGraph();
    if(graph.schema_version!=='1.0')throw Error('Unsupported index schema.');
    activeGraph=graph;nodes=graph.nodes;edges=graph.edges;
    symbols=nodes.filter(n=>n.kind==='method');requirements=nodes.filter(n=>n.kind==='requirement');
    tests=nodes.filter(n=>n.kind==='test');components=nodes.filter(n=>n.kind==='component');
    byId=Object.fromEntries(nodes.map(n=>[n.id,n]));activeDataset='indexed';
  }else{
    ({nodes,symbols,requirements,tests,components,edges,byId}=illustrated);activeGraph=null;activeDataset='illustrated';
  }
}
