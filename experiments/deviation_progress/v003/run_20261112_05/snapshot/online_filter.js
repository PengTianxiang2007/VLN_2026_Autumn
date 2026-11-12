/* Fixed-lag JEV filtering, extracted from the v001 pipeline without sampling.
 * Output records are immutable. No normalization or end-of-stream padding.
 */
(function(root){
  'use strict';
  class JevOnlineFilter {
    constructor(options={}) {
      this.config=Object.freeze({window:7,delay:5,...options});
      const {window:N,delay:D}=this.config;
      if(!Number.isInteger(N)||N<3||N>101||N%2===0||!Number.isInteger(D)||D<0||D>30)
        throw new Error('Invalid filter configuration');
      this.confirmation=Math.min(2,D);this.lookahead=D-this.confirmation;
      this.sigma=Math.max(.5,N/6);this.radius=Math.max(1,Math.ceil(3*this.sigma));
      this.raw=new Map();this.time=-1;
    }
    push(value,frame=this.time+1) {
      if(!Number.isInteger(frame)||frame!==this.time+1)throw new Error('Expected consecutive frames');
      if(value!==null&&(!Number.isFinite(value)||value<0||value>1))throw new Error('Expected a score in [0,1] or null');
      this.time=frame;this.raw.set(frame,value);
      let output=null;
      const i=frame-this.lookahead;
      if(i>=0){
        let smooth=null;
        if(this.raw.get(i)!==null){
          let sum=0,weight=0;
          for(let j=Math.max(0,i-this.radius);j<=frame;j++){
            const p=this.raw.get(j);
            if(p===null)continue;
            if(p===undefined)throw new Error('Required raw frame was discarded');
            const w=Math.exp(-((j-i)**2)/(2*this.sigma**2));sum+=p*w;weight+=w;
          }
          if(weight)smooth=sum/weight;
        }
        output=Object.freeze({index:i,value:smooth,raw:this.raw.get(i),emittedAt:frame});
      }
      const minimum=Math.max(0,frame+1-this.lookahead-this.radius);
      for(const key of this.raw.keys())if(key<minimum)this.raw.delete(key);
      return output;
    }
    state(){return Object.freeze({receivedThrough:this.time,filteredThrough:Math.max(-1,this.time-this.lookahead),
      lookahead:this.lookahead,confirmation:this.confirmation,rawBufferSize:this.raw.size});}
  }
  if(typeof module==='object'&&module.exports)module.exports=JevOnlineFilter;
  root.JevOnlineFilter=JevOnlineFilter;
})(typeof globalThis==='object'?globalThis:this);
