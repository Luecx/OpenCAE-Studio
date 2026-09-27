
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const fmt=x=>Number.isFinite(x)?(Math.abs(x)>=1e4||Math.abs(x)<1e-3&&x!==0?x.toExponential(3):x.toPrecision(5).replace(/0+$/,'').replace(/\.$/,'')):'—';

export class TimeManager{
  constructor(opts){
    this.o=opts;this.mode='across';this.start=0;this.end=1;this.position=0;this.speed=1;this.loop=false;this.playing=false;this.raf=0;this.last=0;this.restoreFrame=null;
    this.$=s=>document.querySelector(s);this.$$=s=>[...document.querySelectorAll(s)];
    this._wire();this.sync(true);
  }
  _wire(){
    this.$$('#tmMode button').forEach(b=>b.onclick=()=>this.setMode(b.dataset.value));
    this.$('#tmFirst').onclick=()=>this.move('first');this.$('#tmPrev').onclick=()=>this.move('prev');this.$('#tmNext').onclick=()=>this.move('next');this.$('#tmLast').onclick=()=>this.move('last');
    this.$('#tmPlay').onclick=()=>this.toggle();this.$('#tmStop').onclick=()=>this.stop(true);this.$('#tmLoop').onclick=()=>{this.loop=!this.loop;this._media();};
    this.$('#tmSpeed').oninput=()=>{this.speed=(+this.$('#tmSpeed').value||100)/100;this.sync(false);};
    this.$('#tmWaveform').onchange=()=>{if(this.mode==='current')this.o.renderer.setAnimationFactor(this.waveform(this.position));this.sync(false);};
    for(const id of['tmStart','tmEnd'])this.$('#'+id).oninput=()=>this._rangeChanged(id);
    this.$('#openTimeManager').onclick=()=>this.open();this.$('#timeManagerTab').onclick=()=>this.open();this.$('#closeTimeManager').onclick=()=>this.close();
  }
  open(){const e=this.$('#timeManager');e.classList.add('open');e.setAttribute('aria-hidden','false');this.$('#timeManagerTab').hidden=true;this.sync(false);requestAnimationFrame(()=>this.draw());}
  close(){const e=this.$('#timeManager');e.classList.remove('open');e.setAttribute('aria-hidden','true');this.$('#timeManagerTab').hidden=!this.o.getData()?.fields?.length;}
  setMode(mode){this.stop(false);this.mode=mode;this.o.renderer.setAnimationFactor(1);this.$$('#tmMode button').forEach(b=>b.classList.toggle('active',b.dataset.value===mode));this.$('#tmCurrentOptions').hidden=mode!=='current';const fs=this.o.getFrames();if(mode==='across'){const i=Math.max(0,fs.findIndex(x=>x.id===this.o.getCurrentFrame()));this.position=i/Math.max(1,fs.length-1);}else this.position=this.start;this.sync(false);}
  range(){let a=(+this.$('#tmStart').value||0)/1000,b=(+this.$('#tmEnd').value||1000)/1000;if(a>b)[a,b]=[b,a];if(b-a<.005)b=Math.min(1,a+.005);return[a,b];}
  indices(){const fs=this.o.getFrames(),r=this.range(),n=Math.max(1,fs.length-1);return[Math.max(0,Math.min(fs.length-1,Math.floor(r[0]*n+1e-9))),Math.max(0,Math.min(fs.length-1,Math.ceil(r[1]*n-1e-9)))];}
  _rangeChanged(source){let a=+this.$('#tmStart').value,b=+this.$('#tmEnd').value;if(a>b){if(source==='tmStart')this.$('#tmEnd').value=String(a);else this.$('#tmStart').value=String(b);}const r=this.range();this.start=r[0];this.end=r[1];if(this.position<this.start||this.position>this.end)this.position=this.start;this.sync(false);}
  waveform(x,name=this.$('#tmWaveform').value){x=clamp(x);if(name==='Half sine')return Math.sin(Math.PI*x);if(name==='Triangle')return x<=.25?4*x:x<=.75?2-4*x:4*x-4;if(name==='Ramp')return x;return Math.sin(2*Math.PI*x);}
  toggle(){this.playing?this.pause():this.play();}
  play(){
    const data=this.o.getData(),fs=this.o.getFrames();if(!data?.fields?.length)return;if(this.mode==='across'&&fs.length<2)return;
    const r=this.range();this.start=r[0];this.end=r[1];if(this.restoreFrame==null){this.restoreFrame=this.o.getCurrentFrame();this.o.onPlaybackStart?.(this.envelopeBounds());}
    if(this.mode==='across'){const i=Math.max(0,fs.findIndex(x=>x.id===this.o.getCurrentFrame())),p=i/Math.max(1,fs.length-1);this.position=p>=this.start&&p<=this.end?p:this.start;this.o.renderer.setAnimationFactor(1);}else{this.position=clamp(this.position,this.start,this.end);this.o.renderer.setAnimationFactor(this.waveform(this.position));}
    this.last=performance.now();this.playing=true;this._media();this.raf=requestAnimationFrame(t=>this._tick(t));
  }
  pause(){if(!this.playing)return;this.playing=false;if(this.raf)cancelAnimationFrame(this.raf);this.raf=0;this._media();this.draw();}
  stop(restore=false){
    this.playing=false;if(this.raf)cancelAnimationFrame(this.raf);this.raf=0;this.o.renderer.setAnimationFactor(1);
    if(restore&&this.restoreFrame!=null)this.o.selectFrame(this.restoreFrame);
    this.o.onPlaybackStop?.(restore);this.restoreFrame=null;this._media();this.sync(false);
  }
  _tick(now){
    if(!this.playing)return;const dt=Math.min(.12,Math.max(0,(now-this.last)/1000));this.last=now;const r=this.range(),speed=(+this.$('#tmSpeed').value||100)/100;
    if(this.mode==='current'){
      this.position+=dt*speed;if(this.position>r[1]){if(this.loop)this.position=r[0]+(this.position-r[1])%Math.max(r[1]-r[0],.005);else{this.position=r[1];this.o.renderer.setAnimationFactor(this.waveform(this.position));this.pause();return;}}this.o.renderer.setAnimationFactor(this.waveform(this.position));
    }else{
      const fs=this.o.getFrames(),rate=4*speed/Math.max(1,fs.length-1);this.position+=dt*rate;if(this.position>r[1]){if(this.loop)this.position=r[0]+(this.position-r[1])%Math.max(r[1]-r[0],.005);else{this.position=r[1];this.pause();}}
      const i=Math.max(0,Math.min(fs.length-1,Math.round(this.position*Math.max(1,fs.length-1)))),f=fs[i];if(f&&f.id!==this.o.getCurrentFrame())this.o.selectFrame(f.id);
    }
    this.sync(false);if(this.playing)this.raf=requestAnimationFrame(t=>this._tick(t));
  }
  move(kind){const fs=this.o.getFrames();if(!fs.length)return;const lim=this.indices(),i=Math.max(0,fs.findIndex(x=>x.id===this.o.getCurrentFrame()));let j=i;if(kind==='first')j=lim[0];else if(kind==='last')j=lim[1];else if(kind==='prev')j=Math.max(lim[0],i-1);else if(kind==='next')j=Math.min(lim[1],i+1);this.o.selectFrame(fs[j].id);this.position=j/Math.max(1,fs.length-1);this.sync(false);}
  envelopeBounds(){
    const field=this.o.getCurrentField();if(!field)return null;let mn=Infinity,mx=-Infinity;
    if(this.mode==='across'){const fs=this.o.getFrames(),lim=this.indices(),ids=new Set(fs.slice(lim[0],lim[1]+1).map(x=>x.id));for(const f of this.o.getData().fields){if(f.step!==this.o.getCurrentStep()||f.name!==field.name||!ids.has(f.frame))continue;const b=this.o.boundsForField(f,this.o.getCurrentComponent());mn=Math.min(mn,b[0]);mx=Math.max(mx,b[1]);}}
    else{const r=this.range(),base=this.o.boundsForField(field,this.o.getCurrentComponent());let f0=Infinity,f1=-Infinity;for(let i=0;i<=256;i++){const v=this.waveform(r[0]+(r[1]-r[0])*i/256);f0=Math.min(f0,v);f1=Math.max(f1,v);}for(const v of[base[0]*f0,base[0]*f1,base[1]*f0,base[1]*f1]){mn=Math.min(mn,v);mx=Math.max(mx,v);}}
    return mn===Infinity?null:[mn,mx];
  }
  sync(reset=false){
    const data=this.o.getData();if(!data?.fields?.length)return;if(reset){this.$('#tmStart').value='0';this.$('#tmEnd').value='1000';this.start=0;this.end=1;}
    const fs=this.o.getFrames(),r=this.range(),lim=this.indices();this.start=r[0];this.end=r[1];if(this.mode==='across'){const i=Math.max(0,fs.findIndex(x=>x.id===this.o.getCurrentFrame()));if(!this.playing)this.position=i/Math.max(1,fs.length-1);this.$('#tmRangeReadout').textContent=fs.length?'Frame '+(fs[lim[0]]?.id??1)+' → Frame '+(fs[lim[1]]?.id??1):'No frames';this.$('#tmStartLabel').textContent=fs[lim[0]]?'Frame '+fs[lim[0]].id:'Start';this.$('#tmEndLabel').textContent=fs[lim[1]]?'Frame '+fs[lim[1]].id:'End';this.$('#tmCursorLabel').textContent=fs[i]?'Current '+fs[i].id:'Current';this.$('#timeSummary').textContent=fs.length?'Across frames · '+(lim[0]+1)+'–'+(lim[1]+1)+' of '+fs.length:'Across frames';}else{this.$('#tmRangeReadout').textContent=Math.round(r[0]*100)+'% → '+Math.round(r[1]*100)+'% · '+this.$('#tmWaveform').value;this.$('#tmStartLabel').textContent=Math.round(r[0]*100)+'%';this.$('#tmEndLabel').textContent=Math.round(r[1]*100)+'%';this.$('#tmCursorLabel').textContent='Phase '+Math.round(this.position*100)+'%';this.$('#timeSummary').textContent='Current frame · '+this.$('#tmWaveform').value;}
    this.$('#tmSpeedValue').value=this.$('#tmSpeed').value+'%';this._media();this.draw();
  }
  _media(){const m=document.querySelector('.tmMedia');if(m)m.classList.toggle('playing',this.playing);this.$('#tmLoop')?.classList.toggle('active',this.loop);}
  draw(){
    const c=this.$('#timeCanvas');if(!c||!this.$('#timeManager').classList.contains('open'))return;const d=Math.min(devicePixelRatio||1,2),r=c.getBoundingClientRect(),w=Math.max(1,Math.round(r.width*d)),h=Math.max(1,Math.round(r.height*d));if(c.width!==w||c.height!==h){c.width=w;c.height=h;}const g=c.getContext('2d');g.setTransform(d,0,0,d,0,0);const W=r.width,H=r.height,pad=18,rr=this.range();g.clearRect(0,0,W,H);g.fillStyle='#1f2428';g.fillRect(0,0,W,H);g.fillStyle='#2d353b';g.fillRect(pad+rr[0]*(W-2*pad),8,(rr[1]-rr[0])*(W-2*pad),H-16);g.strokeStyle='#4a545c';g.lineWidth=1;g.beginPath();g.moveTo(pad,H/2);g.lineTo(W-pad,H/2);g.stroke();
    if(this.mode==='current'){g.strokeStyle='#bcc7ce';g.lineWidth=1.5;g.beginPath();for(let i=0;i<=220;i++){const x=i/220,y=this.waveform(x),X=pad+x*(W-2*pad),Y=H/2-y*(H*.34);if(i)g.lineTo(X,Y);else g.moveTo(X,Y);}g.stroke();}else{const fs=this.o.getFrames();g.fillStyle='#89949c';for(let i=0;i<fs.length;i++){const x=pad+i/Math.max(1,fs.length-1)*(W-2*pad);g.beginPath();g.arc(x,H/2,2.3,0,Math.PI*2);g.fill();}}
    const x=pad+this.position*(W-2*pad);g.strokeStyle='#e1e5e8';g.beginPath();g.moveTo(x,6);g.lineTo(x,H-6);g.stroke();
  }
}
