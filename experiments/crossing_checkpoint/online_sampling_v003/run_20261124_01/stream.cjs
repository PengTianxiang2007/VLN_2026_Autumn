'use strict';
const fs = require('node:fs');
const Sampler = require('../../../../core/jev_online_sampler_v003.js');
const episodes = 'outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/episodes/';
const input = JSON.parse(fs.readFileSync(0,'utf8'));
const output = {};
for (const episode of input.episodes) {
  const scores=JSON.parse(fs.readFileSync(episodes+episode+'/scores.json','utf8'));
  const features=[], rows={};
  const profiles = input.profiles || {features:null};
  for (const [name,profile] of Object.entries(profiles)) {
    const sampler=new Sampler(profile,profile ? null : (index,x)=>features.push([index,x]));
    const frames=[];
    scores.forEach((s,t)=>{
      const node=sampler.push(s,t).node;
      if(node) {
        if(node.index+5!==t || node.rawScore!==scores[node.index]) throw new Error('Output frame mismatch');
        frames.push(node.index);
      }
    });
    rows[name]=frames;
  }
  output[episode]=input.profiles ? rows : features;
}
process.stdout.write(JSON.stringify(output));
