const NUMBER = /[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[Ee][-+]?\d+)?/g;

const DEFS = {
  1:{n:8,solid:true,faces:[['q4',[0,1,2,3]],['q4',[4,7,6,5]],['q4',[0,4,5,1]],['q4',[1,5,6,2]],['q4',[2,6,7,3]],['q4',[3,7,4,0]]],edges:[[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]]},
  2:{n:6,solid:true,faces:[['t3',[0,2,1]],['t3',[3,4,5]],['q4',[0,1,4,3]],['q4',[1,2,5,4]],['q4',[2,0,3,5]]],edges:[[0,1],[1,2],[2,0],[3,4],[4,5],[5,3],[0,3],[1,4],[2,5]]},
  3:{n:4,solid:true,faces:[['t3',[0,2,1]],['t3',[0,1,3]],['t3',[1,2,3]],['t3',[2,0,3]]],edges:[[0,1],[1,2],[2,0],[0,3],[1,3],[2,3]]},
  4:{n:20,solid:true,faces:[['q8',[0,1,2,3,8,9,10,11]],['q8',[4,7,6,5,19,18,17,16]],['q8',[0,4,5,1,12,16,13,8]],['q8',[1,5,6,2,13,17,14,9]],['q8',[2,6,7,3,14,18,15,10]],['q8',[3,7,4,0,15,19,12,11]]],edges:[[0,8,1],[1,9,2],[2,10,3],[3,11,0],[4,16,5],[5,17,6],[6,18,7],[7,19,4],[0,12,4],[1,13,5],[2,14,6],[3,15,7]]},
  5:{n:15,solid:true,faces:[['t6',[0,2,1,8,7,6]],['t6',[3,4,5,12,13,14]],['q8',[0,1,4,3,6,10,12,9]],['q8',[1,2,5,4,7,11,13,10]],['q8',[2,0,3,5,8,9,14,11]]],edges:[[0,6,1],[1,7,2],[2,8,0],[3,12,4],[4,13,5],[5,14,3],[0,9,3],[1,10,4],[2,11,5]]},
  6:{n:10,solid:true,faces:[['t6',[0,2,1,6,5,4]],['t6',[0,1,3,4,8,7]],['t6',[1,2,3,5,9,8]],['t6',[2,0,3,6,7,9]]],edges:[[0,4,1],[1,5,2],[2,6,0],[0,7,3],[1,8,3],[2,9,3]]},
  7:{n:3,shell:true,faces:[['t3',[0,1,2]]],edges:[[0,1],[1,2],[2,0]]},
  8:{n:6,shell:true,faces:[['t6',[0,1,2,3,4,5]]],edges:[[0,3,1],[1,4,2],[2,5,0]]},
  9:{n:4,shell:true,faces:[['q4',[0,1,2,3]]],edges:[[0,1],[1,2],[2,3],[3,0]]},
  10:{n:8,shell:true,faces:[['q8',[0,1,2,3,4,5,6,7]]],edges:[[0,4,1],[1,5,2],[2,6,3],[3,7,0]]},
  11:{n:2,line:true,edges:[[0,1]]},
  12:{n:3,line:true,edges:[[0,2,1]]},
};
const CORNERS={t3:3,t6:3,q4:4,q8:4};
const FACE_EDGES={
  t3:[[0,1],[1,2],[2,0]],
  t6:[[0,3,1],[1,4,2],[2,5,0]],
  q4:[[0,1],[1,2],[2,3],[3,0]],
  q8:[[0,4,1],[1,5,2],[2,6,3],[3,7,0]],
};

let cancelled=false;
self.onmessage=async e=>{
  if(e.data?.type==='cancel'){cancelled=true;return;}
  if(e.data?.type!=='load')return;
  cancelled=false;
  try{await load(e.data.file);}catch(err){if(!cancelled)self.postMessage({type:'error',message:err?.stack||String(err)});}
};
const progress=(value,phase,detail='')=>self.postMessage({type:'progress',value,phase,detail});
const numbers=line=>(line.slice(3).match(NUMBER)||[]).map(Number);

async function load(file){
  progress(1,'Reading FRD',file.name);
  const state={nodes:new Map(),elements:[],fields:[],mode:null,element:null,field:null,rowId:null,rowValues:[],stepId:1,frameId:1,frameValue:0,pendingStep:null,pendingFrame:null,frameMap:new Map(),blockIndex:0};
  const reader=file.stream().getReader(),decoder=new TextDecoder();let carry='',read=0,lastReport=0;
  while(true){
    if(cancelled){reader.cancel();return;}
    const {value,done}=await reader.read();if(done)break;
    read+=value.byteLength;carry+=decoder.decode(value,{stream:true});
    const lines=carry.split(/\r?\n/);carry=lines.pop()||'';
    for(const line of lines)parseLine(state,line);
    const p=4+48*(read/Math.max(file.size,1));if(p-lastReport>0.5){lastReport=p;progress(p,'Reading and parsing FRD',`${formatBytes(read)} / ${formatBytes(file.size)}`);}
  }
  carry+=decoder.decode();if(carry)parseLine(state,carry);finishState(state);
  progress(54,'Compacting mesh',`${state.nodes.size.toLocaleString()} nodes · ${state.elements.length.toLocaleString()} elements`);
  await microYield();
  const compact=compactMesh(state);
  progress(64,'Extracting result surface','Building exterior FE faces and topology');await microYield();
  const geometry=buildGeometry(compact);
  progress(79,'Preparing result fields',`${state.fields.length} output blocks`);await microYield();
  const fields=packFields(state.fields,compact.idToIndex,compact.nodeIds.length);
  progress(92,'Transferring to GPU thread','Finalizing typed arrays');
  const payload={type:'done',file:{name:file.name,size:file.size},nodeIds:compact.nodeIds,positions:compact.positions,elementIds:compact.elementIds,elementTypes:compact.elementTypes,elementOffsets:compact.elementOffsets,elementConnectivity:compact.elementConnectivity,geometry,fields};
  const transfer=[compact.nodeIds.buffer,compact.positions.buffer,compact.elementIds.buffer,compact.elementTypes.buffer,compact.elementOffsets.buffer,compact.elementConnectivity.buffer,geometry.meshLines.buffer,geometry.boundaryLines.buffer,geometry.pathSegments.buffer,geometry.lineElements.buffer,geometry.lineElementIds.buffer];
  for(const batch of Object.values(geometry.batches)){transfer.push(batch.nodes.buffer,batch.elements.buffer);}
  for(const field of fields)transfer.push(field.values.buffer);
  self.postMessage(payload,transfer);
}
function microYield(){return new Promise(r=>setTimeout(r,0));}
function formatBytes(n){if(n<1024)return `${n} B`;if(n<1048576)return `${(n/1024).toFixed(1)} KiB`;return `${(n/1048576).toFixed(1)} MiB`;}
function finishRow(s){if(s.field&&s.rowId!=null)s.field.rows.set(s.rowId,s.rowValues.slice());}
function finishState(s){if(s.mode==='elements'&&s.element)s.elements.push(s.element);if(s.field){finishRow(s);s.fields.push(s.field);}s.element=null;s.field=null;}
function parseLine(s,line){
  if(line.startsWith('    1PSTEP')){const v=(line.match(NUMBER)||[]).map(Number).map(x=>x|0);if(v.length>=3){s.pendingFrame=v.at(-2);s.pendingStep=v.at(-1);}return;}
  if(line.startsWith('    2C')){s.mode='nodes';return;}if(line.startsWith('    3C')){s.mode='elements';return;}
  if(line.startsWith('  100C')){const t=line.trim().split(/\s+/),rawStep=parseInt(t[1]||'1',10)||1;s.frameValue=Number(t[2]||0)||0;if(s.pendingStep!=null){s.stepId=s.pendingStep;s.frameId=s.pendingFrame||1;}else{s.stepId=rawStep;const key=`${s.stepId}|${s.frameValue}`;if(!s.frameMap.has(key)){let n=1;for(const k of s.frameMap.keys())if(k.startsWith(`${s.stepId}|`))n++;s.frameMap.set(key,n);}s.frameId=s.frameMap.get(key);}s.mode='results';return;}
  if(line.startsWith(' -4')){if(s.field){finishRow(s);s.fields.push(s.field);}const t=line.trim().split(/\s+/);s.field={name:t[1]||`FIELD_${s.blockIndex+1}`,components:[],rows:new Map(),step:s.stepId,frame:s.frameId,value:s.frameValue,index:++s.blockIndex};s.rowId=null;s.rowValues=[];return;}
  if(line.startsWith(' -5')&&s.field){const t=line.trim().split(/\s+/);if(t[1])s.field.components.push(t[1]);return;}
  if(line.trim()==='-3'){if(s.mode==='elements'&&s.element){s.elements.push(s.element);s.element=null;}if(s.mode==='results'&&s.field){finishRow(s);s.fields.push(s.field);s.field=null;s.rowId=null;s.rowValues=[];}s.mode=null;return;}
  if(s.mode==='nodes'&&line.startsWith(' -1')){const v=numbers(line);if(v.length>=4)s.nodes.set(v[0]|0,[v[1],v[2],v[3]]);return;}
  if(s.mode==='elements'){if(line.startsWith(' -1')){if(s.element)s.elements.push(s.element);const v=numbers(line);s.element={id:v[0]|0,type:v[1]|0,nodes:[]};}else if(line.startsWith(' -2')&&s.element)s.element.nodes.push(...numbers(line).map(x=>x|0));return;}
  if(s.mode==='results'&&s.field){if(line.startsWith(' -1')){finishRow(s);const v=numbers(line);s.rowId=v[0]|0;s.rowValues=v.slice(1);}else if(line.startsWith(' -2'))s.rowValues.push(...numbers(line));}
}
function compactMesh(s){
  const nodeIds=Int32Array.from(s.nodes.keys()),positions=new Float32Array(nodeIds.length*3),idToIndex=new Map();
  for(let i=0;i<nodeIds.length;i++){idToIndex.set(nodeIds[i],i);const p=s.nodes.get(nodeIds[i]);positions.set(p,i*3);}
  const valid=s.elements.filter(e=>DEFS[e.type]&&e.nodes.length>=DEFS[e.type].n&&e.nodes.slice(0,DEFS[e.type].n).every(id=>idToIndex.has(id)));
  const elementIds=new Int32Array(valid.length),elementTypes=new Uint8Array(valid.length),elementOffsets=new Uint32Array(valid.length+1);let total=0;
  for(let i=0;i<valid.length;i++){elementIds[i]=valid[i].id;elementTypes[i]=valid[i].type;elementOffsets[i]=total;total+=DEFS[valid[i].type].n;}elementOffsets[valid.length]=total;
  const elementConnectivity=new Uint32Array(total);let o=0;for(const e of valid){const n=DEFS[e.type].n;for(let j=0;j<n;j++)elementConnectivity[o++]=idToIndex.get(e.nodes[j]);}
  return{nodeIds,positions,idToIndex,elementIds,elementTypes,elementOffsets,elementConnectivity};
}
function elemNodes(c,i){return c.elementConnectivity.subarray(c.elementOffsets[i],c.elementOffsets[i+1]);}
function buildGeometry(c){
  const faceMap=new Map(),direct=[];const allPath=new Map();const lineSegments=[],lineSegmentElements=[];
  for(let ei=0;ei<c.elementIds.length;ei++){
    const def=DEFS[c.elementTypes[ei]],en=elemNodes(c,ei);
    for(const edge of def.edges){const seq=edge.map(k=>en[k]);for(let j=0;j<seq.length-1;j++){const a=seq[j],b=seq[j+1],key=a<b?`${a},${b}`:`${b},${a}`;allPath.set(key,[a,b]);}}
    if(def.line){for(const edge of def.edges){const seq=edge.map(k=>en[k]);for(let j=0;j<seq.length-1;j++){lineSegments.push(seq[j],seq[j+1]);lineSegmentElements.push(ei);}}continue;}
    for(const [kind,local] of def.faces){const nodes=local.map(k=>en[k]),corners=nodes.slice(0,CORNERS[kind]);const rec={kind,nodes,element:ei};if(def.shell)direct.push(rec);else{const key=corners.slice().sort((a,b)=>a-b).join(',');if(faceMap.has(key))faceMap.delete(key);else faceMap.set(key,rec);}}
  }
  const faces=[...faceMap.values(),...direct],groups={t3:[],t6:[],q4:[],q8:[]};for(const f of faces)groups[f.kind].push(f);
  const batches={};for(const kind of Object.keys(groups)){const fs=groups[kind],nodes=new Uint32Array(fs.length*8),elements=new Uint32Array(fs.length);nodes.fill(0xffffffff);for(let i=0;i<fs.length;i++){nodes.set(fs[i].nodes,i*8);elements[i]=fs[i].element;}batches[kind]={count:fs.length,nodes,elements};}
  const meshMap=new Map(),featureMap=new Map();
  for(const f of faces){const fe=FACE_EDGES[f.kind],n=faceNormal(c.positions,f.nodes,CORNERS[f.kind]);for(const edge of fe){const seq=edge.map(k=>f.nodes[k]),a=seq[0],b=seq.at(-1),key=a<b?`${a},${b}`:`${b},${a}`;let rec=featureMap.get(key);if(!rec){rec={seq,normals:[]};featureMap.set(key,rec);}rec.normals.push(n);for(let j=0;j<seq.length-1;j++){const x=seq[j],y=seq[j+1],sk=x<y?`${x},${y}`:`${y},${x}`;meshMap.set(sk,[x,y]);}}}
  for(let i=0;i<lineSegments.length;i+=2){const a=lineSegments[i],b=lineSegments[i+1],k=a<b?`${a},${b}`:`${b},${a}`;meshMap.set(k,[a,b]);}
  const boundary=[];const limit=Math.cos(32*Math.PI/180);for(const rec of featureMap.values()){let feature=rec.normals.length!==2;if(!feature){const [a,b]=rec.normals;feature=(a[0]*b[0]+a[1]*b[1]+a[2]*b[2])<limit;}if(feature)for(let j=0;j<rec.seq.length-1;j++)boundary.push(rec.seq[j],rec.seq[j+1]);}
  const allEdges=Uint32Array.from([...allPath.values()].flat());return{batches,meshLines:allEdges,boundaryLines:Uint32Array.from(boundary),pathSegments:Uint32Array.from(allEdges),lineElements:Uint32Array.from(lineSegments),lineElementIds:Uint32Array.from(lineSegmentElements)};
}
function faceNormal(p,nodes,count){const a=nodes[0],b=nodes[1],c=nodes[count-1],ax=p[a*3],ay=p[a*3+1],az=p[a*3+2],ux=p[b*3]-ax,uy=p[b*3+1]-ay,uz=p[b*3+2]-az,vx=p[c*3]-ax,vy=p[c*3+1]-ay,vz=p[c*3+2]-az;let x=uy*vz-uz*vy,y=uz*vx-ux*vz,z=ux*vy-uy*vx,l=Math.hypot(x,y,z)||1;return[x/l,y/l,z/l];}
function packFields(fields,idToIndex,nodeCount){
  return fields.map(f=>{const width=Math.max(1,f.components.length),values=new Float32Array(nodeCount*width);values.fill(NaN);for(const [id,row] of f.rows){const ni=idToIndex.get(id);if(ni==null)continue;for(let j=0;j<width&&j<row.length;j++)values[ni*width+j]=row[j];}return{name:f.name,components:f.components,step:f.step,frame:f.frame,value:f.value,index:f.index,width,values};});
}
