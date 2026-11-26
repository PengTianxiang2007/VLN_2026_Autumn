'use strict';
const fs=require('node:fs');
const Base=require('../../../../core/jev_online_sampler_v001.js');
const Lean=require('../../../../core/jev_online_sampler_v002.js');
const Ranked=require('../../../../core/jev_online_sampler_v003.js');
const cfg=require('../../../../core/jev_online_sampling_v003.json');
const source=JSON.parse(fs.readFileSync(0,'utf8'));
const output={};
for(const [eid,values] of Object.entries(source)){
  if(!values.every(p=>Number.isFinite(p)&&p>=0&&p<=1))throw Error('Missing score for '+eid);
  const samplers={v001:new Base(),coverage:new Ranked({...cfg,...cfg.modes.coverage}),active:new Lean('active')};
  const rows={};
  for(const [name,model] of Object.entries(samplers)){
    const points=[];
    values.forEach((p,t)=>{
      const node=model.push(p,t).node;
      if(node){if(node.emittedAt!==t || node.index+5!==t)throw Error('Invalid emission lag');points.push(node);}
    });rows[name]=points;
  }output[eid]=rows;
}
process.stdout.write(JSON.stringify(output));
