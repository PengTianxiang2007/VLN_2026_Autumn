// Execute the actual page script against a small DOM test double.
// This checks interaction logic, not browser layout or HTML5 video decoding.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const page=fs.readFileSync(process.argv[2],'utf8');
const payload=page.match(/<script id="case-data-json" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script=page.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const elements=new Map(),downloads=[],alerts=[],store=new Map();
class Element {
  constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.listeners={};this.attributes={};this.dataset={};this.style={};this.value='';this.checked=false;this.hidden=false;this.textContent='';this.className='';this.files=[];this.paused=true;this.readyState=4;this.currentTime=0;this.playbackRate=1;this.classList={toggle:(name,on)=>{const s=new Set(this.className.split(' ').filter(Boolean));on?s.add(name):s.delete(name);this.className=[...s].join(' ')}}}
  setAttribute(key,value){this.attributes[key]=String(value);if(key==='id'){this.id=value;elements.set(value,this)}}
  getAttribute(key){return this.attributes[key]}
  append(...nodes){this.children.push(...nodes)}
  replaceChildren(...nodes){this.children=nodes}
  addEventListener(type,callback){(this.listeners[type]??=[]).push(callback)}
  async emit(type,extra={}){for(const cb of this.listeners[type]||[])await cb({target:this,currentTarget:this,preventDefault(){},...extra})}
  click(){return this.emit('click')}
  pause(){this.paused=true}
  play(){this.paused=false;return Promise.resolve()}
  getBoundingClientRect(){return{left:0,top:0,width:900,height:560}}
}
for(const match of page.matchAll(/<([\w-]+)\b[^>]*\bid="([^"]+)"[^>]*>/g)){const e=new Element(match[1]);e.id=match[2];elements.set(e.id,e)}
const document=new Element('document');
document.getElementById=id=>{assert(elements.has(id),'Missing DOM ID '+id);return elements.get(id)};
document.createElement=tag=>new Element(tag);document.createElementNS=(_,tag)=>new Element(tag);
elements.get('case-data-json').textContent=payload;elements.get('sort').value='number';elements.get('speed').value='1';
const context=vm.createContext({document,console,Blob,Math,JSON,Date,Set,Map,Number,String,Array,decodeURIComponent,
  localStorage:{getItem:key=>store.get(key)||null,setItem:(key,value)=>store.set(key,value)},
  location:{hash:''},history:{replaceState(){}},URL:{createObjectURL:blob=>{downloads.push(blob);return'blob:test'},revokeObjectURL(){}},
  requestAnimationFrame:()=>1,cancelAnimationFrame(){},setTimeout:fn=>fn(),alert:x=>alerts.push(x)});
vm.runInContext(script,context,{filename:process.argv[2]});
const run=code=>vm.runInContext(code,context),$=id=>elements.get(id),checks=[];
(async()=>{
  assert.equal(run('rows.length'),25);assert.equal(run('filtered.length'),25);assert.equal($('case-list').children.length,25);checks.push('25 cases load and initial case renders');
  for(let i=0;i<25;i++){run(`show(rows[${i}]);setFrame(current.frames-1,true)`);assert.equal(run('currentFrame'),run('current.frames-1'));assert(Number.isFinite(Number($('current-point').getAttribute('cx'))));assert($('instruction').textContent.length>10);assert($('model-output').textContent.length>0)}checks.push('all 25 cases render, reach final frame and show task/model text');
  $('tag-filter').value='left_goal';await $('tag-filter').emit('input');assert.equal(run('filtered.length'),8);
  $('tag-filter').value='near_goal';await $('tag-filter').emit('input');assert.equal(run('filtered.length'),9);
  $('tag-filter').value='';$('scene-filter').value='kujiale_0234';await $('scene-filter').emit('input');assert.equal(run('filtered.length'),3);
  $('scene-filter').value='';$('search').value='__no_such_case__';await $('search').emit('input');assert($('viewer').hidden);assert(!$('empty').hidden);
  $('search').value='';await $('search').emit('input');assert.equal(run('filtered.length'),25);checks.push('scene, phenomenon and empty-result filters');
  $('sort').value='ne-desc';await $('sort').emit('input');const order=run('filtered.map(r=>r.metrics.NE)');for(let i=1;i<order.length;i++)assert(order[i]<=order[i-1]);
  $('sort').value='number';await $('sort').emit('input');run('show(rows[0])');await $('next').click();assert.equal(run('current.number'),2);await $('previous').click();assert.equal(run('current.number'),1);checks.push('metric sorting and previous/next navigation');
  await $('closest-frame').click();assert.equal(run('currentFrame'),run('current.closest_frame'));assert.equal($('video').currentTime,run('current.closest_frame/current.fps'));
  $('video').currentTime=1.5;await $('video').emit('timeupdate');assert.equal(run('currentFrame'),9);assert.equal(Number($('frame-slider').value),9);
  $('frame-slider').value=12;await $('frame-slider').emit('input');assert.equal(run('currentFrame'),12);
  await $('distance-chart').emit('click',{clientX:873});assert.equal(run('currentFrame'),run('current.frames-1'));checks.push('video time, slider, chart and closest-frame synchronization');
  await $('show-en').click();assert.equal($('instruction').textContent,run('current.instruction'));await $('show-both').click();assert(!$('original-instruction').hidden);checks.push('Chinese, English and bilingual instructions');
  $('note').value='在第 12 帧检查右转；尚未确认原因。';await $('note').emit('input');$('diagnosis').value='路口转向错误';await $('diagnosis').emit('change');$('reviewed').checked=true;await $('reviewed').emit('change');assert.equal(run('reviewedCount()'),1);assert(store.size===1);
  await $('export-notes').click();const exported=JSON.parse(await downloads[0].text());assert.equal(exported.notes[run('current.episode_id')].text,$('note').value);
  $('unreviewed').checked=true;await $('unreviewed').emit('input');assert.equal(run('filtered.length'),24);$('unreviewed').checked=false;await $('unreviewed').emit('input');
  exported.notes[run('current.episode_id')]={text:'导入检查',diagnosis:'其他',reviewed:true};$('notes-file').files=[{text:async()=>JSON.stringify(exported)}];await $('notes-file').emit('change');assert(alerts.includes('笔记已导入。'));checks.push('notes persist, export, import and reviewed filtering');
  run('show(rows[0]);setFrame(3,true)');await document.emit('keydown',{target:new Element('body'),key:'ArrowRight'});assert.equal(run('currentFrame'),4);await document.emit('keydown',{target:new Element('body'),key:'j'});assert.equal(run('current.number'),2);checks.push('keyboard frame and case controls');
  console.log(JSON.stringify({passed:true,verification:'Actual page JavaScript with DOM test double; no browser layout assertion',checks},null,2));
})().catch(error=>{console.error(error);process.exitCode=1});
