'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const Sampler=require('../core/jev_online_sampler_v001.js'),Filter=require('../core/jev_online_filter_v001.js');
const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/jev_online_sampling_v001.json'),'utf8'));
const config=JSON.parse(fs.readFileSync(path.join(__dirname,'../core/jev_online_sampling_v001.json'),'utf8'));
const source=fs.readFileSync(path.join(__dirname,'../core/jev_online_sampler_v001.js'),'utf8').replaceAll('\r\n','\n');
assert.equal(crypto.createHash('sha256').update(source).digest('hex'),fixture.reference_source_sha256_lf,'v001 is frozen; implement changes as a new version');
assert.deepEqual({...Sampler.defaults},config);
let runs=0,arrivals=0;
function equivalent(actual,expected){
  if(typeof actual==='number'&&typeof expected==='number'){
    assert(Number.isFinite(actual)&&Math.abs(actual-expected)<=fixture.float_tolerance,`${actual} != ${expected}`);return;
  }
  if(actual&&expected&&typeof actual==='object'&&typeof expected==='object'){
    assert.deepEqual(Object.keys(actual),Object.keys(expected));
    for(const key of Object.keys(expected))equivalent(actual[key],expected[key]);return;
  }
  assert.equal(actual,expected);
}
function replay(raw,options={}){
  runs++;const sampler=new Sampler(options),filter=new Filter(options),filtered=[],nodes=[];
  raw.forEach((p,t)=>{
    const before=JSON.stringify([filtered,nodes]),f=filtered.length,n=nodes.length;
    const result=sampler.push(p,t),curve=filter.push(p,t);arrivals++;
    assert.equal(JSON.stringify([filtered,nodes]),before,'arrival mutated previously published objects');
    assert.deepEqual(result.filtered,curve,'standalone filter differs from sampler pipeline');
    if(result.filtered){assert(Object.isFrozen(result.filtered));filtered.push(result.filtered);assert.equal(result.filtered.emittedAt-result.filtered.index,sampler.lookahead);}
    if(result.node){
      const point=result.node;assert(Object.isFrozen(point));assert.equal(point.emittedAt,t);assert.equal(point.delay,sampler.config.delay);
      assert.equal(point.id,'S'+String(n+1).padStart(2,'0'));assert.notEqual(raw[point.index],null);
      if(n)assert(point.index-nodes[n-1].index>=sampler.config.minGap);nodes.push(point);
    }
    assert.equal(JSON.stringify([filtered.slice(0,f),nodes.slice(0,n)]),before);
    assert(sampler.raw.size<=sampler.radius+sampler.lookahead+1);assert(sampler.filtered.size<=2*sampler.confirmation+2);
    assert(filter.raw.size<=filter.radius+filter.lookahead+1);
  });
  return {filtered,nodes,state:sampler.state()};
}
for(const c of fixture.cases)equivalent(replay(c.raw,c.options),c.expected);
for(const c of fixture.cases.filter(c=>c.kind==='recorded'))for(const window of [3,7,31])for(const delay of [0,1,2,3,5]){
  const options={window,delay},full=replay(c.raw,options);
  for(const end of new Set([0,1,4,5,Math.floor(c.raw.length/2),c.raw.length-2,c.raw.length-1])){
    if(end<0)continue;const prefix=replay(c.raw.slice(0,end+1),options);
    assert.deepEqual(prefix.filtered,full.filtered.filter(p=>p.emittedAt<=end));
    assert.deepEqual(prefix.nodes,full.nodes.filter(p=>p.emittedAt<=end));
  }
}
let seed=20261112;const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
for(let i=0;i<40;i++){
  const prefix=Array.from({length:40},random),a=replay([...prefix,...Array.from({length:80},random)]),b=replay([...prefix,...Array.from({length:80},random)]);
  assert.deepEqual(a.filtered.filter(p=>p.emittedAt<40),b.filtered.filter(p=>p.emittedAt<40));
  assert.deepEqual(a.nodes.filter(p=>p.emittedAt<40),b.nodes.filter(p=>p.emittedAt<40));
}
assert.deepEqual(replay(Array(60).fill(.8)).nodes.map(n=>n.index),Array.from({length:11},(_,i)=>i*5));
assert.equal(replay(Array.from({length:80},(_,i)=>.2+.001*Math.sin(i/3))).nodes.length,0);
assert.equal(replay(Array(5).fill(.9)).nodes.length,0);assert.equal(replay(Array(6).fill(.9)).nodes[0].emittedAt,5);
const invalid=new Sampler();for(const value of [undefined,NaN,Infinity,-.1,1.1,'0.5'])assert.throws(()=>invalid.push(value));
assert.throws(()=>invalid.push(.5,1));assert.equal(invalid.time,-1);
const longRun=new Sampler();for(let i=0;i<100000;i++)longRun.push(.5+.3*Math.sin(i/11));
assert(longRun.raw.size<=longRun.radius+longRun.lookahead+1);assert(longRun.filtered.size<=2*longRun.confirmation+2);
console.log(JSON.stringify({passed:true,goldenCases:fixture.cases.length,recordedTrajectories:fixture.recorded_trajectories,
  runs,arrivals,longStreamFrames:100000,recordedCandidates:fixture.cases.filter(c=>c.kind==='recorded').reduce((n,c)=>n+c.expected.nodes.length,0)},null,2));
