'use strict';
// Thin transport around the frozen sampler; its numerical rules stay unchanged.
const readline=require('node:readline');
const Sampler=require('../core/jev_online_sampler_v001.js');
let sampler=new Sampler();
readline.createInterface({input:process.stdin,crlfDelay:Infinity}).on('line',line=>{
  try {
    const q=JSON.parse(line);
    if(q.reset) { sampler=new Sampler(q.config||{}); process.stdout.write('{"reset":true}\n'); }
    else process.stdout.write(JSON.stringify(sampler.push(q.value,q.frame))+'\n');
  } catch(error) { process.stdout.write(JSON.stringify({error:error.message})+'\n'); }
});
