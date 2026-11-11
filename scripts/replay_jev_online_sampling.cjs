#!/usr/bin/env node
'use strict';
// Replay is a test/integration oracle. Live callers use Sampler.push per arrival.
const fs=require('node:fs'),path=require('node:path');
const Sampler=require('../core/jev_online_sampler_v001.js');
function main(){
  const args=process.argv.slice(2),parsed={};
  if(args.includes('--help')){console.log('node scripts/replay_jev_online_sampling.cjs --input scores.json [--config config.json] [--output result.json]');return;}
  for(let i=0;i<args.length;i+=2){if(!['--input','--config','--output'].includes(args[i])||!args[i+1])throw new Error('Expected --input, --config or --output followed by a path');parsed[args[i].slice(2)]=args[i+1];}
  if(!parsed.input)throw new Error('--input is required');
  const source=JSON.parse(fs.readFileSync(parsed.input,'utf8')),scores=Array.isArray(source)?source:source.scores;
  if(!Array.isArray(scores))throw new Error('Input must be an array, or an object with a scores array');
  const config=JSON.parse(fs.readFileSync(parsed.config||path.join(__dirname,'../core/jev_online_sampling_v001.json'),'utf8'));
  const model=new Sampler(config),filtered=[],nodes=[];
  scores.forEach((score,t)=>{const result=model.push(score,t);if(result.filtered)filtered.push(result.filtered);if(result.node)nodes.push(result.node);});
  const result=JSON.stringify({config:model.config,received:scores.length,filtered,nodes,state:model.state()},null,2)+'\n';
  if(parsed.output){fs.mkdirSync(path.dirname(parsed.output),{recursive:true});fs.writeFileSync(parsed.output,result,{flag:'wx'});console.log('Saved '+parsed.output);}
  else process.stdout.write(result);
}
try{main();}catch(error){console.error(error.message);process.exitCode=1;}
