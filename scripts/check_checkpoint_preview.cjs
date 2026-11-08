/* Functional DOM-shim check; this is not a rendered-browser test. */
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const file=process.argv[2],html=fs.readFileSync(file,'utf8');
const payload=html.match(/<script id="payload" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
const elements=new Map(),storage=new Map(),downloads=[],blobs=new Map(),timers=new Map();
const canvas=new Proxy({}, {get:(target,key)=>target[key]??((...args)=>{
 if(['arc','lineTo','moveTo','fillText'].includes(key)) for(const x of args.slice(key==='fillText'?1:0)) if(typeof x==='number')assert(Number.isFinite(x),'nonfinite canvas coordinate');
})});
class Element {
 constructor(tag='div'){this.tagName=tag;this.children=[];this.dataset={};this.value='';this.textContent='';this.style={};this.classList={toggle:()=>{}};}
 append(e){this.children.push(e)}replaceChildren(...e){this.children=e}removeAttribute(k){delete this[k]}
 getContext(){return canvas}click(){if(this.tagName==='a')downloads.push({name:this.download,url:this.href});if(this.onclick)this.onclick()}
}
for(const m of html.matchAll(/<(\w+)[^>]*\bid="([^"]+)"[^>]*>/g))elements.set(m[2],new Element(m[1]));
elements.get('payload').textContent=payload;
const document={getElementById:id=>{assert(elements.has(id));return elements.get(id)},createElement:t=>new Element(t),querySelectorAll:selector=>{assert.equal(selector,'#cases button');return elements.get('cases').children}};
class Image {constructor(){this.complete=true;this.naturalWidth=640;}set src(v){this._src=v;if(this.onload)this.onload()}get src(){return this._src}}
const context={document,window:{},Image,console,Blob,URL:{createObjectURL:b=>{const id='blob:'+blobs.size;blobs.set(id,b);return id},revokeObjectURL:()=>{}},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},setInterval:f=>{const id=timers.size;timers.set(id,f);return id},clearInterval:id=>timers.delete(id)};
vm.createContext(context);vm.runInContext(script,context,{filename:file});
const api=context.window.CROSSING_PREVIEW,D=api.data,$=id=>elements.get(id);let frames=0,queued=0;
assert.equal($('cases').children.length,D.summary.expected_cases);
for(const [id,c]of Object.entries(D.cases)){
 api.select(id);assert.equal(api.state().episode_id,id);api.seek(-100);assert.equal(api.state().index,0);api.seek(100000);assert.equal(api.state().index,Math.max(0,c.snapshots.length-1));
 if(!c.snapshots.length){assert.equal(api.state().frame,null);assert(!$('rgb').src);queued++;continue}
 for(let i=0;i<c.snapshots.length;i++){
  api.seek(i);const snap=c.snapshots[i];assert.equal(api.state().frame,snap.frame);assert.equal($('rgb').src,snap.image);assert(snap.image.startsWith('data:image/jpeg;base64,'));assert.equal($('events').children.length,snap.events.length);assert(snap.image_frames.every(f=>f<=snap.frame));assert(snap.executed_actions.every(a=>a.index<snap.frame));
  for(const e of snap.events){assert(e.first_seen_frame<=snap.frame);assert(e.last_seen_frame<=snap.frame);assert(e.confirmation_frame===null||e.confirmation_frame<=snap.frame);assert(e.closed_frame===undefined||e.closed_frame<=snap.frame)}frames++;
 }
 assert.equal(c.last_frame,c.snapshots.at(-1).frame);assert(c.steps.every(s=>s.frame<=c.last_frame));
 api.seek(0);$('next').onclick();assert.equal(api.state().index,Math.min(1,c.snapshots.length-1));$('prev').onclick();assert.equal(api.state().index,0);
 $('play').onclick();assert.equal(timers.size,1);const advance=[...timers.values()][0];for(let i=0;i<=c.snapshots.length;i++)advance();assert.equal(api.state().index,c.snapshots.length-1);assert.equal(timers.size,0);
}
const selected=Object.keys(D.cases).find(id=>D.cases[id].processed);api.select(selected);api.seek(0);$('note').value='Functional verification only';$('note').oninput();api.seek(1);api.seek(0);assert.equal($('note').value,'Functional verification only');$('export').onclick();assert.equal(downloads.at(-1).name,'crossing_prefix_review.json');
(async()=>{const notes=JSON.parse(await blobs.get(downloads.at(-1).url).text());assert.equal(notes.notes.length,1);assert.equal(notes.notes[0].episode_id,selected);assert.equal(notes.notes[0].frame,D.cases[selected].snapshots[0].frame);const result={passed:true,environment:'Node VM DOM shim; not rendered browser validation',cases:Object.keys(D.cases).length,cases_without_completed_observations:queued,processed_snapshots:frames,frame_bounds:true,chronological_states:true,embedded_RGB:true,playback_bounds:true,note_export:true};fs.writeFileSync(path.join(path.dirname(file),'validation_ui.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));})().catch(e=>{console.error(e);process.exitCode=1});
