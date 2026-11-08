/* Functional UI verification with a DOM shim, not a rendered-browser test. */
'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path'),crypto=require('crypto');
const file=process.argv[2],html=fs.readFileSync(file,'utf8');
// Optional expected case/observation counts support later frozen campaigns.
const expectedCases=Number(process.argv[3]??8),expectedObservations=Number(process.argv[4]??573),legacyFixture=process.argv.length===3;
assert(Number.isInteger(expectedCases)&&expectedCases>0);assert(Number.isInteger(expectedObservations)&&expectedObservations>0);
const payload=html.match(/<script id="payload" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
assert(!/<script[^>]+src=|<video\b|<link[^>]+href=/i.test(html),'External dependency in standalone HTML');
const elements=new Map(),storage=new Map(),downloads=[],blobs=new Map(),timers=new Map(),listeners=new Map();let serial=0;
const drawnLabels=[];
const context2d=new Proxy({}, {get:(t,k)=>t[k]??((...args)=>{
 if(['arc','lineTo','moveTo','fillText'].includes(k))for(const x of args.slice(k==='fillText'?1:0))if(typeof x==='number')assert(Number.isFinite(x));
 if(k==='fillText')drawnLabels.push(args[0]);
})});
class Element{
 constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.style={};this.value='';this.checked=false;this.textContent='';this.classList={toggle:()=>{}};}
 append(...e){this.children.push(...e)}replaceChildren(...e){this.children=e}removeAttribute(k){delete this[k]}
 getContext(){return context2d}getBoundingClientRect(){return {left:0,top:0,width:800,height:470}}
 set width(value){this._width=value;if(this.tagName==='CANVAS')drawnLabels.length=0}get width(){return this._width}
 click(){if(this.tagName==='A')downloads.push({name:this.download,url:this.href});if(this.onclick)this.onclick()}
}
for(const m of html.matchAll(/<(\w+)[^>]*\bid="([^"]+)"[^>]*>/g))elements.set(m[2],new Element(m[1]));
const $=id=>{assert(elements.has(id),id);return elements.get(id)};
$('payload').textContent=payload;$('filters').value='all';$('eventFilter').value='all';$('speed').value='500';$('full').checked=true;$('labels').checked=true;
$('showPrior').checked=true;$('showCurrent').checked=true;
const document={getElementById:$,createElement:t=>new Element(t),activeElement:null,addEventListener:(event,fn)=>listeners.set(event,fn)};
class Image{constructor(){this.complete=true;this.naturalWidth=640}set src(v){this._src=v;if(this.onload)this.onload()}get src(){return this._src}}
const context={document,window:{},Image,console,Blob,URL:{createObjectURL:b=>{const id='blob:'+blobs.size;blobs.set(id,b);return id},revokeObjectURL:()=>{}},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},setInterval:f=>{const id=++serial;timers.set(id,f);return id},clearInterval:id=>timers.delete(id)};
vm.createContext(context);vm.runInContext(script,context,{filename:file});
const api=context.window.CROSSING_REVIEW,D=api.data;let observations=0,eventLinks=0,priorPoints=0,currentPoints=0;
assert(D.summary.complete);assert.equal(D.summary.expected_cases,expectedCases);assert.equal(Object.keys(D.cases).length,expectedCases);assert.equal($('cases').children.length,expectedCases);assert.equal($('stats').children.length,5);assert.equal($('radii').children.length,3);
for(const [id,c]of Object.entries(D.cases)){
 api.select(id);assert.equal(api.state().episode_id,id);assert.equal($('frame').max,c.snapshots.length-1);
 assert.equal($('priorList').children.length,c.prior_annotations.length);assert.equal($('currentList').children.length,c.current_annotations.length);
 assert.equal(drawnLabels.filter(x=>x.startsWith('原 ')).length,c.prior_annotations.length);
 assert.equal(drawnLabels.filter(x=>x.startsWith('现 ')).length,c.current_annotations.length,'Full comparison must display all P points even at frame 0');
 priorPoints+=c.prior_annotations.length;currentPoints+=c.current_annotations.length;
 for(const point of c.current_annotations){assert.deepEqual(point.position,c.steps.find(s=>s.frame===point.confirmation_frame).position.slice(0,2));api.chooseCurrent(point);assert.equal(api.state().frame,point.confirmation_frame)}
 for(const point of c.prior_annotations){assert.equal(point.visited,c.encounters.some(e=>e.crossing_id===point.id));api.choosePrior(point);assert.equal(api.state().frame,point.closest_frame);if(!point.visited)assert($('selectedEvent').textContent.includes('不计为漏检'))}
 $('visitedOnly').checked=true;$('visitedOnly').onchange();assert.equal(drawnLabels.filter(x=>x.startsWith('原 ')).length,c.prior_annotations.filter(p=>p.visited).length);$('visitedOnly').checked=false;
 $('showPrior').checked=false;$('showPrior').onchange();assert.equal(drawnLabels.filter(x=>x.startsWith('原 ')).length,0);$('showPrior').checked=true;
 $('showCurrent').checked=false;$('showCurrent').onchange();assert.equal(drawnLabels.filter(x=>x.startsWith('现 ')).length,0);$('showCurrent').checked=true;
 $('full').checked=false;api.seek(0);assert.equal(drawnLabels.filter(x=>x.startsWith('现 ')).length,c.current_annotations.filter(p=>p.confirmation_frame<=c.snapshots[0].frame).length);$('full').checked=true;$('full').onchange();
 api.seek(-5);assert.equal(api.state().index,0);api.seek(99999);assert.equal(api.state().index,c.snapshots.length-1);
 for(let i=0;i<c.snapshots.length;i++){
  api.seek(i);const snap=c.snapshots[i];assert.equal(api.state().frame,snap.frame);assert.equal($('rgb').src,snap.image);assert(snap.image.startsWith('data:image/jpeg;base64,'));
  assert.equal($('history').children.length,snap.image_frames.length);assert.equal($('memory').children.length,snap.events.length);assert.equal($('answer').textContent,JSON.stringify(snap.prediction,null,2));
  assert(snap.image_frames.every(f=>f<=snap.frame));assert(snap.executed_actions.every(a=>a.index<snap.frame));
  for(const e of snap.events){assert(e.last_seen_frame<=snap.frame);assert(e.confirmation_frame===null||e.confirmation_frame<=snap.frame);assert(e.closed_frame===undefined||e.closed_frame<=snap.frame)}observations++;
 }
 const all=api.events();assert.equal(all.length,c.metrics['1.0'].confirmed_predictions+c.metrics['1.0'].fn);
 for(const row of all){api.chooseEvent(row);assert.equal(api.state().frame,row.frame);assert.equal(api.state().selected,row.key);eventLinks++}
 $('eventFilter').value='missed';$('eventFilter').onchange();assert.equal($('eventList').children.length,c.metrics['1.0'].fn);
 $('eventFilter').value='all';$('eventFilter').onchange();assert.equal($('eventList').children.length,all.length);
 api.seek(0);$('next').click();assert.equal(api.state().index,1);$('prev').click();assert.equal(api.state().index,0);
 $('play').click();assert.equal(timers.size,1);const advance=[...timers.values()][0];for(let i=0;i<c.snapshots.length+2;i++)advance();assert.equal(api.state().index,c.snapshots.length-1);assert.equal(timers.size,0);
 $('history').children[0].click();assert.equal(api.state().frame,c.snapshots.at(-1).image_frames[0]);
 if(all.some(e=>e.crossing_id)){
  const row=all.find(e=>e.crossing_id),s=D.maps[c.scene],cross=s.crossings.find(x=>x.id===row.crossing_id),scale=Math.min(800/s.width,470/s.height);
  const x=(cross.position[0]-s.low[0])/s.resolution,y=(s.high[1]-cross.position[1])/s.resolution;
  $('map').onclick({clientX:x*scale+(800-s.width*scale)/2,clientY:y*scale+(470-s.height*scale)/2});assert(api.state().selected);
 }
 $('full').checked=false;$('full').onchange();$('full').checked=true;$('labels').checked=false;$('labels').onchange();$('labels').checked=true;
}
assert.equal(observations,expectedObservations);assert.equal(observations,D.summary.verified_causal_requests);
assert.equal(eventLinks,D.summary.metrics['1.0'].confirmed_predictions+D.summary.metrics['1.0'].fn);assert.equal(currentPoints,D.summary.metrics['1.0'].confirmed_predictions);
assert.equal(priorPoints,Object.values(D.cases).reduce((sum,c)=>sum+D.maps[c.scene].crossings.length,0));
if(legacyFixture){assert.equal(eventLinks,23);assert.equal(currentPoints,7);assert.equal(priorPoints,38)}
const successes=Object.values(D.cases).filter(c=>c.source_success).length;
for(const [filter,expected]of [['success',successes],['failure',expectedCases-successes],['all',expectedCases]]){$('filters').value=filter;$('filters').onchange();assert.equal($('cases').children.length,expected)}
const first=Object.keys(D.cases)[0];api.select(first);api.seek(0);$('category').value='map_question';$('category').onchange();$('note').value='Functional test only';$('note').oninput();api.seek(1);assert.equal($('note').value,'');api.seek(0);assert.equal($('note').value,'Functional test only');assert.equal($('category').value,'map_question');
listeners.get('keydown')({key:'ArrowRight',preventDefault:()=>{}});assert.equal(api.state().index,1);
document.activeElement={tagName:'TEXTAREA'};listeners.get('keydown')({key:'ArrowRight',preventDefault:()=>{}});assert.equal(api.state().index,1);document.activeElement=null;
$('export').click();assert.equal(downloads.at(-1).name,'crossing_dev8_review_notes.json');
(async()=>{const notes=JSON.parse(await blobs.get(downloads.at(-1).url).text());assert.equal(notes.notes.length,1);assert.equal(notes.notes[0].frame,0);assert.equal(notes.notes[0].episode_id,first);assert.equal(notes.notes[0].category,'map_question');const result={passed:true,environment:'Node VM DOM shim; not rendered-browser validation',observations,event_links:eventLinks,cases:expectedCases,prior_points_across_case_views:priorPoints,current_points:currentPoints,all_current_points_visible_on_open:true,unvisited_prior_points_separate:true,current_points_on_recorded_trajectory:true,annotation_layer_toggles:true,causal_states:true,history_thumbnails:true,playback_bounds:true,map_clicks:true,filters:true,keyboard:true,note_export:true,standalone:true,html_sha256:crypto.createHash('sha256').update(html).digest('hex')};fs.writeFileSync(path.join(path.dirname(file),'ui_verification.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));})().catch(e=>{console.error(e);process.exitCode=1});
