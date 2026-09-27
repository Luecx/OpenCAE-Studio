const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const nice=v=>Number.isFinite(v)?(Math.abs(v)>=1e4||(Math.abs(v)>0&&Math.abs(v)<1e-4)?v.toExponential(5):String(+v.toPrecision(9))):'—';

export class TimeManager{
  constructor(opts){this.o=opts;this.$=s=>document.querySelector(s);this.$$=s=>[...document.querySelectorAll(s)];this.mode='across';this.playing=false;this.loop=false;this.raf=0;this.last=0;this.time=0;this.phase=0;this.restoreFrame=null;this.restoreRange=null;this._wire();}
  _wire(){
    this.$$('#tmMode button').forEach(b=>b.onclick=()=>this.setMode(b.dataset.value));
    this.$('#tmMin').onchange=()=>this._rangeChanged('min');this.$('#tmMax').onchange=()=>this._rangeChanged('max');
    this.$('#tmTime').oninput=()=>{const [a,b]=this.range();this.time=a+(b-a)*(+this.$('#tmTime').value/1000);this.o.displayTime(this.time);this._updateLabels();};
    this.$('#tmFirst').onclick=()=>this.move('first');this.$('#tmPrev').onclick=()=>this.move('prev');this.$('#tmNext').onclick=()=>this.move('next');this.$('#tmLast').onclick=()=>this.move('last');
    this.$('#tmPlay').onclick=()=>this.toggle();this.$('#tmStop').onclick=()=>this.stop(true);this.$('#tmLoop').onclick=()=>{this.loop=!this.loop;this._media();};
    this.$('#tmSpeed').oninput=()=>{this.$('#tmSpeedValue').value=this.$('#tmSpeed').value+'%';};
    this.$('#tmWaveform').onchange=()=>{if(this.mode==='current')this.o.renderer.setAnimationFactor(this.waveform(this.phase));this._updateLabels();};
  }
  frames(){return this.o.getFrames().slice().sort((a,b)=>a.value-b.value||a.id-b.id);}
  fullRange(){const fs=this.frames();if(!fs.length)return[0,0];const a=Number(fs[0].value),b=Number(fs.at(-1).value);return[Number.isFinite(a)?a:0,Number.isFinite(b)?b:(Number.isFinite(a)?a:0)];}
  range(){const full=this.fullRange();let a=Number(this.$('#tmMin').value),b=Number(this.$('#tmMax').value);if(!Number.isFinite(a))a=full[0];if(!Number.isFinite(b))b=full[1];a=clamp(a,full[0],full[1]);b=clamp(b,full[0],full[1]);if(a>b)[a,b]=[b,a];return[a,b];}
  sync(reset=false){
    const fs=this.frames();if(!fs.length)return;const full=this.fullRange(),current=fs.find(f=>f.id===this.o.getCurrentFrame())||fs[0];
    for(const id of['tmMin','tmMax']){const e=this.$('#'+id);e.min=String(full[0]);e.max=String(full[1]);e.step='any';}
    if(reset||!Number.isFinite(+this.$('#tmMin').value)||!Number.isFinite(+this.$('#tmMax').value)){this.$('#tmMin').value=String(full[0]);this.$('#tmMax').value=String(full[1]);}
    this._clampInputs();
    if(!this.playing&&this.mode==='across'){this.time=clamp(Number(current.value),...this.range());this.o.clearInterpolation?.();}
    this.$('#tmAcrossOptions').hidden=this.mode!=='across';this.$('#tmCurrentOptions').hidden=this.mode!=='current';
    this._updateSlider();this._updateLabels();this._media();
  }
  setMode(mode){this.stop(false);this.mode=mode==='current'?'current':'across';this.$$('#tmMode button').forEach(b=>b.classList.toggle('active',b.dataset.value===this.mode));this.o.renderer.clearFrameInterpolation();this.o.renderer.setAnimationFactor(1);this.phase=0;this.sync(false);this.o.onRangeChanged?.();}
  _clampInputs(){const full=this.fullRange();let a=clamp(Number(this.$('#tmMin').value),full[0],full[1]),b=clamp(Number(this.$('#tmMax').value),full[0],full[1]);if(!Number.isFinite(a))a=full[0];if(!Number.isFinite(b))b=full[1];if(a>b){if(document.activeElement===this.$('#tmMin'))b=a;else a=b;}this.$('#tmMin').value=String(a);this.$('#tmMax').value=String(b);}
  _rangeChanged(){this._clampInputs();const [a,b]=this.range();this.time=clamp(this.time,a,b);if(this.mode==='across')this.o.displayTime(this.time);this._updateSlider();this._updateLabels();this.o.onRangeChanged?.();}
  _updateSlider(){const [a,b]=this.range(),span=Math.max(Math.abs(b-a),1e-30),t=clamp((this.time-a)/span,0,1);this.$('#tmTime').value=String(Math.round(t*1000));}
  _updateLabels(){const [a,b]=this.range();this.$('#tmTimeValue').value=this.mode==='across'?nice(this.time):nice(this.phase);this.$('#tmSpeedValue').value=this.$('#tmSpeed').value+'%';this.$('#timeSummary').textContent=this.mode==='across'?('Range '+nice(a)+' → '+nice(b)+(this.o.isInterpolated?.()?' · interpolated':'')):('Current frame · '+this.$('#tmWaveform').value);}
  waveform(x){x=clamp(x,0,1);const n=this.$('#tmWaveform').value;if(n==='Half sine')return Math.sin(Math.PI*x);if(n==='Triangle')return x<=.25?4*x:x<=.75?2-4*x:4*x-4;if(n==='Ramp')return x;return Math.sin(2*Math.PI*x);}
  toggle(){this.playing?this.pause():this.play();}
  play(){
    const fs=this.frames();if(!fs.length)return;const [a,b]=this.range();if(this.mode==='across'&&b<=a)return;
    if(this.restoreFrame==null){this.restoreFrame=this.o.getCurrentFrame();this.restoreRange=this.o.captureContour?.();this.o.onPlaybackStart?.(this.envelopeBounds());}
    if(this.mode==='across'){this.time=clamp(this.time,a,b);this.o.renderer.setAnimationFactor(1);this.o.displayTime(this.time);}else{this.phase=0;this.o.renderer.clearFrameInterpolation();this.o.renderer.setAnimationFactor(this.waveform(0));}
    this.last=performance.now();this.playing=true;this._media();this.raf=requestAnimationFrame(t=>this._tick(t));
  }
  pause(){if(!this.playing)return;this.playing=false;if(this.raf)cancelAnimationFrame(this.raf);this.raf=0;this._media();}
  stop(restore=false){
    this.playing=false;if(this.raf)cancelAnimationFrame(this.raf);this.raf=0;this.o.renderer.setAnimationFactor(1);this.o.renderer.clearFrameInterpolation();
    if(restore&&this.restoreFrame!=null)this.o.selectFrame(this.restoreFrame);if(restore&&this.restoreRange)this.o.restoreContour?.(this.restoreRange);
    this.restoreFrame=null;this.restoreRange=null;this.phase=0;this.sync(false);
  }
  _tick(now){
    if(!this.playing)return;const dt=Math.min(.12,Math.max(0,(now-this.last)/1000)),speed=(+this.$('#tmSpeed').value||100)/100;this.last=now;
    if(this.mode==='current'){this.phase+=dt*speed;if(this.phase>1){if(this.loop)this.phase%=1;else{this.phase=1;this.o.renderer.setAnimationFactor(this.waveform(this.phase));this.pause();return;}}this.o.renderer.setAnimationFactor(this.waveform(this.phase));}
    else{const [a,b]=this.range(),duration=4/speed;this.time+=(b-a)*dt/duration;if(this.time>b){if(this.loop)this.time=a+(this.time-b)%Math.max(b-a,1e-30);else{this.time=b;this.o.displayTime(this.time);this.pause();return;}}this.o.displayTime(this.time);this._updateSlider();}
    this._updateLabels();if(this.playing)this.raf=requestAnimationFrame(t=>this._tick(t));
  }
  move(kind){
    const fs=this.frames();if(!fs.length)return;const [a,b]=this.range(),valid=fs.filter(f=>f.value>=a-1e-12&&f.value<=b+1e-12);if(!valid.length)return;
    let i=this.mode==='across'?valid.reduce((best,f,k)=>Math.abs(f.value-this.time)<Math.abs(valid[best].value-this.time)?k:best,0):valid.findIndex(f=>f.id===this.o.getCurrentFrame());if(i<0)i=0;
    if(kind==='first')i=0;else if(kind==='last')i=valid.length-1;else if(kind==='prev')i=Math.max(0,i-1);else if(kind==='next')i=Math.min(valid.length-1,i+1);
    const f=valid[i];this.o.selectFrame(f.id);this.time=f.value;this.o.renderer.clearFrameInterpolation();this._updateSlider();this._updateLabels();
  }
  bracket(time=this.time){
    const fs=this.frames();if(!fs.length)return null;if(fs.length===1)return{left:fs[0],right:fs[0],alpha:0,time:fs[0].value};
    if(time<=fs[0].value)return{left:fs[0],right:fs[0],alpha:0,time:fs[0].value};if(time>=fs.at(-1).value)return{left:fs.at(-1),right:fs.at(-1),alpha:0,time:fs.at(-1).value};
    for(let i=1;i<fs.length;i++)if(time<=fs[i].value){const l=fs[i-1],rr=fs[i],span=rr.value-l.value,alpha=span>1e-14?(time-l.value)/span:0;return{left:l,right:rr,alpha:clamp(alpha,0,1),time};}
    return{left:fs.at(-1),right:fs.at(-1),alpha:0,time:fs.at(-1).value};
  }
  envelopeBounds(){const field=this.o.getCurrentField();if(!field)return null;let mn=Infinity,mx=-Infinity;if(this.mode==='current'){const base=this.o.boundsForField(field,this.o.getCurrentComponent());for(let i=0;i<=256;i++){const f=this.waveform(i/256);for(const v of[base[0]*f,base[1]*f]){mn=Math.min(mn,v);mx=Math.max(mx,v);}}}else{const [a,b]=this.range(),merge=q=>{if(!q)return;mn=Math.min(mn,q[0]);mx=Math.max(mx,q[1]);};merge(this.o.boundsAtTime?.(a));merge(this.o.boundsAtTime?.(b));for(const f of this.o.getData().fields){if(f.step!==this.o.getCurrentStep()||f.name!==field.name||f.value<a-1e-12||f.value>b+1e-12)continue;merge(this.o.boundsForField(f,this.o.getCurrentComponent()));}}return mn===Infinity?null:[mn,mx];}
  _media(){const row=this.$('.tmMedia');if(row)row.classList.toggle('playing',this.playing);this.$('#tmLoop').classList.toggle('active',this.loop);}
  draw(){}
}
