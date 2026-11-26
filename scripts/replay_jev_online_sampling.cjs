#!/usr/bin/env node
'use strict';
// Replay is a test/integration oracle. Live callers use Sampler.push per arrival.
const fs=require('node:fs'),path=require('node:path');
const Sampler=require('../core/jev_online_sampler_v001.js');
function main(){
  const args=process.argv.slice(2),parsed={};
  if(args.includes('--help')){console.log('node scripts/replay_jev_online_sampling.cjs --input scores.json [--version v001|v002|v003] [--mode near|plateau|active (v002), coverage|p60|p70|strict (v003)] [--config config.json (v001)] [--output result.json]');return;}
  for(let i=0;i<args.length;i+=2){if(!['--input','--config','--output','--version','--mode'].includes(args[i])||!args[i+1])throw new Error('Expected an option followed by its value');parsed[args[i].slice(2)]=args[i+1];}
  if(!parsed.input)throw new Error('--input is required');
  const source=JSON.parse(fs.readFileSync(parsed.input,'utf8')),scores=Array.isArray(source)?source:source.scores;
  if(!Array.isArray(scores))throw new Error('Input must be an array, or an object with a scores array');
  const version = parsed.version || 'v001';
  if (!['v001', 'v002', 'v003'].includes(version)) throw new Error('Unknown sampling version: ' + version);
  if (version !== 'v001' && parsed.config) throw new Error('This version uses frozen settings');
  if (parsed.mode && version === 'v001') throw new Error('--mode requires --version v002 or v003');
  const mode = parsed.mode || (version === 'v003' ? 'p60' : 'near');
  const config=JSON.parse(fs.readFileSync(parsed.config||path.join(__dirname,'../core/jev_online_sampling_v001.json'),'utf8'));
  let model;
  if (version === 'v003') {
    const settings = require('../core/jev_online_sampling_v003.json');
    if (!Object.prototype.hasOwnProperty.call(settings.modes, mode)) throw new Error('Unknown v003 mode: ' + mode);
    const RankedSampler = require('../core/jev_online_sampler_v003.js');
    model = new RankedSampler({weights:settings.weights, intercept:settings.intercept, ...settings.modes[mode]});
  } else if (version === 'v002') {
    model = new (require('../core/jev_online_sampler_v002.js'))(mode);
  } else {
    model = new Sampler(config);
  }
  const filtered=[],nodes=[];
  scores.forEach((score,t)=>{const result=model.push(score,t);if(result.filtered)filtered.push(result.filtered);if(result.node)nodes.push(result.node);});
  const result=JSON.stringify({...(version !== 'v001' ? {version, mode} : {}),config:model.config,received:scores.length,filtered,nodes,state:model.state()},null,2)+'\n';
  if(parsed.output){fs.mkdirSync(path.dirname(parsed.output),{recursive:true});fs.writeFileSync(parsed.output,result,{flag:'wx'});console.log('Saved '+parsed.output);}
  else process.stdout.write(result);
}
try{main();}catch(error){console.error(error.message);process.exitCode=1;}
