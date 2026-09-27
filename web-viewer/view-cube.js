const LABELS=new Map([
  ['1,0,0','RIGHT'],['-1,0,0','LEFT'],['0,1,0','BACK'],['0,-1,0','FRONT'],['0,0,1','TOP'],['0,0,-1','BOTTOM']
]);
const key=n=>n.map(v=>Math.abs(v)<1e-9?0:Math.round(v*1e6)/1e6).join(',');
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];

function faces(bevel=.30){
  const q=1-Math.min(Math.max(bevel,.04),.32),out=[];
  const corners=[[-q,-q],[q,-q],[q,q],[-q,q]];
  for(let axis=0;axis<3;axis++)for(const sign of[-1,1]){
    const other=[0,1,2].filter(i=>i!==axis),verts=corners.map(([a,b])=>{const p=[0,0,0];p[axis]=sign;p[other[0]]=a;p[other[1]]=b;return p;});
    const n=[0,0,0];n[axis]=sign;out.push({kind:'main',label:LABELS.get(key(n))||'',normal:n,verts});
  }
  for(let a=0;a<3;a++)for(let b=a+1;b<3;b++){const free=[0,1,2].find(i=>i!==a&&i!==b);for(const sa of[-1,1])for(const sb of[-1,1]){
    const verts=[[-q,1,q],[-q,q,1],[q,q,1],[q,1,q]].map(([f,x,y])=>{const p=[0,0,0];p[free]=f;p[a]=x*sa;p[b]=y*sb;return p;});
    const n=[0,0,0];n[a]=sa/Math.SQRT2;n[b]=sb/Math.SQRT2;out.push({kind:'edge',label:'',normal:n,verts});
  }}
  for(const sx of[-1,1])for(const sy of[-1,1])for(const sz of[-1,1]){
    const signs=[sx,sy,sz],verts=[];for(let full=0;full<3;full++){const p=signs.map(s=>s*q);p[full]=signs[full];verts.push(p);}
    const n=signs.map(s=>s/Math.sqrt(3));out.push({kind:'corner',label:'',normal:n,verts});
  }
  return out;
}
function inside(poly,x,y){let c=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const a=poly[i],b=poly[j];if(((a[1]>y)!==(b[1]>y))&&(x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]))c=!c;}return c;}
function area(p){let s=0;for(let i=0;i<p.length;i++){const a=p[i],b=p[(i+1)%p.length];s+=a[0]*b[1]-b[0]*a[1];}return Math.abs(s*.5);}

export class ViewCube{
  constructor(canvas,renderer){this.canvas=canvas;this.renderer=renderer;this.ctx=canvas.getContext('2d');this.faces=faces();this.hit=[];this.hover=null;this.pressed=null;canvas.addEventListener('pointermove',e=>this._move(e));canvas.addEventListener('pointerleave',()=>{this.hover=null;this.draw();});canvas.addEventListener('pointerdown',e=>{e.stopPropagation();this.pressed=this._normalAt(e);canvas.setPointerCapture(e.pointerId);});canvas.addEventListener('pointerup',e=>{e.stopPropagation();const n=this._normalAt(e);if(n&&this.pressed&&key(n)===key(this.pressed))renderer.setViewNormal(n);this.pressed=null;});canvas.addEventListener('wheel',e=>e.stopPropagation(),{passive:true});}
  _point(e){const r=this.canvas.getBoundingClientRect();return[(e.clientX-r.left)*this.canvas.width/r.width,(e.clientY-r.top)*this.canvas.height/r.height];}
  _normalAt(e){const[x,y]=this._point(e);for(let i=this.hit.length-1;i>=0;i--)if(inside(this.hit[i].poly,x,y))return this.hit[i].normal;return null;}
  _move(e){e.stopPropagation();const n=this._normalAt(e),k=n?key(n):null,h=this.hover?key(this.hover):null;if(k!==h){this.hover=n;this.draw();}}
  draw(){const c=this.canvas,g=this.ctx,d=Math.min(devicePixelRatio||1,2),css=this.canvas.getBoundingClientRect();const w=Math.max(1,Math.round(css.width*d)),h=Math.max(1,Math.round(css.height*d));if(c.width!==w||c.height!==h){c.width=w;c.height=h;}g.clearRect(0,0,w,h);const b=this.renderer.cameraBasis(),cx=w*.5,cy=h*.51,scale=Math.min(w,h)*.315;const rows=[b.right,b.up,b.eye],visible=[];for(const f of this.faces){const tr=v=>[dot(rows[0],v),dot(rows[1],v),dot(rows[2],v)],n=tr(f.normal);if(n[2]<=1e-7)continue;const vv=f.verts.map(tr),poly=vv.map(p=>[cx+p[0]*scale,cy-p[1]*scale]),depth=vv.reduce((s,p)=>s+p[2],0)/vv.length;visible.push({f,n,poly,depth});}visible.sort((a,b)=>a.depth-b.depth);this.hit=[];for(const item of visible){const active=this.hover&&key(this.hover)===key(item.f.normal),light=Math.max(0,-.35*item.n[0]+.55*item.n[1]+.75*item.n[2]);const base=item.f.kind==='main'?54:item.f.kind==='edge'?43:34,v=Math.round(base+light*24);g.beginPath();item.poly.forEach((p,i)=>i?g.lineTo(...p):g.moveTo(...p));g.closePath();g.fillStyle=active?'#546f82':`rgb(${v},${v+3},${v+6})`;g.strokeStyle=active?'#a9c5d7':'#69737c';g.lineWidth=active?2*d:.9*d;g.fill();g.stroke();if(item.f.kind==='main'&&area(item.poly)>250*d*d){g.fillStyle='#dce2e6';g.font=`${Math.round(8*d)}px system-ui`;g.textAlign='center';g.textBaseline='middle';const x=item.poly.reduce((s,p)=>s+p[0],0)/item.poly.length,y=item.poly.reduce((s,p)=>s+p[1],0)/item.poly.length;g.fillText(item.f.label,x,y);}this.hit.push({poly:item.poly,normal:item.f.normal});}}
}
