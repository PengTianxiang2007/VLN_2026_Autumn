/* Online candidate sampling v001. No data access beyond push(value, frame).
 * Frame parameters are frozen at construction. Outputs are append-only.
 * Total delay D = smoothing lookahead F + peak confirmation H.
 * Default D=5 => F=3, H=2. No end-of-stream padding or tail flush.
 */
(function (root) {
  'use strict';
  const DEFAULTS = Object.freeze({window:7,delay:5,high:0.60,low:0.45,
    peakDrop:0.03,initialFloor:0.45,debounce:2,minGap:3,plateauGap:5});
  class JevOnlineSampler {
    constructor(options={}) {
      this.config=Object.freeze({...DEFAULTS,...options});
      const c=this.config;
      for(const k of ['window','delay','debounce','minGap','plateauGap'])
        if(!Number.isInteger(c[k]))throw new Error('Integer required: '+k);
      if(c.window<3||c.window>101||c.window%2===0||c.delay<0||c.delay>30||
         c.debounce<1||c.minGap<1||c.plateauGap<c.minGap||
         ![c.high,c.low,c.peakDrop,c.initialFloor].every(Number.isFinite)||
         c.low<0||c.high>1||c.high<=c.low||c.peakDrop<=0||c.peakDrop>1||
         c.initialFloor<0||c.initialFloor>1)throw new Error('Invalid sampler configuration');
      this.confirmation=Math.min(2,c.delay);
      this.lookahead=c.delay-this.confirmation;
      this.sigma=Math.max(.5,c.window/6);
      this.radius=Math.max(1,Math.ceil(3*this.sigma));
      this.raw=new Map();this.filtered=new Map();
      this.time=-1;this.count=0;this.lastAccepted=-Infinity;
      this.active=false;this.highRun=0;this.lowRun=0;
    }
    push(value,frame=this.time+1) {
      if(!Number.isInteger(frame)||frame!==this.time+1)throw new Error('Frames must arrive consecutively; use null for an explicitly missing score');
      if(value!==null&&(!Number.isFinite(value)||value<0||value>1))throw new Error('Expected a score in [0,1] or null');
      this.time=frame;this.raw.set(frame,value);
      let filtered=null,node=null;
      const i=frame-this.lookahead;
      if(i>=0) {
        let smooth=null;
        if(this.raw.get(i)!==null) {
          let sum=0,weight=0;
          for(let j=Math.max(0,i-this.radius);j<=frame;j++) {
            const p=this.raw.get(j);
            if(p===null)continue;
            if(p===undefined)throw new Error('Required raw frame was discarded');
            const w=Math.exp(-((j-i)**2)/(2*this.sigma**2));
            sum+=p*w;weight+=w;
          }
          if(weight)smooth=sum/weight;
        }
        filtered=Object.freeze({index:i,value:smooth,raw:this.raw.get(i),emittedAt:frame});
        this.filtered.set(i,filtered);
        const k=i-this.confirmation;
        if(k>=0)node=this.decide(k,frame);
      }
      // Only the finite windows needed for the next arrival are retained.
      const rawMinimum=Math.max(0,frame+1-this.lookahead-this.radius);
      for(const key of this.raw.keys())if(key<rawMinimum)this.raw.delete(key);
      const decision=frame-this.config.delay;
      const filteredMinimum=Math.max(0,decision+1-Math.max(1,this.confirmation));
      for(const key of this.filtered.keys())if(key<filteredMinimum)this.filtered.delete(key);
      return Object.freeze({filtered,node});
    }
    decide(k,emittedAt) {
      const cfg=this.config,record=this.filtered.get(k),s=record.value;
      if(s===null) {this.active=false;this.highRun=0;this.lowRun=0;return null;}
      let entered=false;
      if(!this.active) {
        this.highRun=s>=cfg.high?this.highRun+1:0;
        if(this.highRun>=cfg.debounce){this.active=true;this.lowRun=0;entered=true;}
      } else {
        this.lowRun=s<cfg.low?this.lowRun+1:0;
        if(this.lowRun>=cfg.debounce){this.active=false;this.highRun=0;}
      }
      let isPeak=false,drop=0;
      const H=this.confirmation;
      if(H>0&&k>0&&s>=cfg.low) {
        const left=[],right=[];
        for(let j=Math.max(0,k-H);j<k;j++)left.push(this.filtered.get(j)?.value??null);
        for(let j=k+1;j<=k+H;j++)right.push(this.filtered.get(j)?.value??null);
        if(left.length&&right.length===H&&!left.includes(null)&&!right.includes(null)){
          drop=Math.min(s-Math.min(...left),s-Math.min(...right));
          // Equal peaks prefer their earliest eligible point; broad tops use the high-region branch.
          isPeak=s>Math.max(...left)+1e-12&&s>=Math.max(...right)-1e-12&&drop>=cfg.peakDrop-1e-12;
        }
      }
      let kind=null;
      if(k===0&&record.raw>=cfg.initialFloor)kind='initial';
      else if(isPeak)kind='peak';
      else if(entered&&s>=cfg.low)kind='entry';
      else if(this.active&&s>=cfg.low&&k-this.lastAccepted>=cfg.plateauGap)kind='plateau';
      if(!kind||k-this.lastAccepted<cfg.minGap)return null;
      this.lastAccepted=k;this.count++;
      return Object.freeze({id:'S'+String(this.count).padStart(2,'0'),index:k,value:s,
        rawScore:record.raw,kind,drop:kind==='peak'?drop:null,emittedAt,delay:emittedAt-k});
    }
    state() {
      return Object.freeze({receivedThrough:this.time,filteredThrough:Math.max(-1,this.time-this.lookahead),
        decidedThrough:Math.max(-1,this.time-this.config.delay),samples:this.count,
        active:this.active,lookahead:this.lookahead,confirmation:this.confirmation,
        rawBufferSize:this.raw.size,filteredBufferSize:this.filtered.size});
    }
  }
  JevOnlineSampler.defaults=DEFAULTS;
  if(typeof module==='object'&&module.exports)module.exports=JevOnlineSampler;
  root.JevOnlineSampler=JevOnlineSampler;
})(typeof globalThis==='object'?globalThis:this);
