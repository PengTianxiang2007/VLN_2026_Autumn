/* Offline functional verification; a DOM shim is not a rendered browser test. */
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const file=process.argv[2],html=fs.readFileSync(file,'utf8');
const payload=html.match(/<script id="report-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const scripts=[...html.matchAll(/<script(?: [^>]*)?>([\s\S]*?)<\/script>/g)];
const registry=new Map(),downloads=[],blobs=new Map(),storage=new Map();
class Element{
 constructor(tag='div'){this.tagName=tag;this.children=[];this.attributes={};this.dataset={};this.style={};this.listeners={};this.value='';this.checked=false;this.textContent='';this.classNames=new Set();this.classList={toggle:(k,v)=>{if(v===undefined)v=!this.classNames.has(k);v?this.classNames.add(k):this.classNames.delete(k)},add:k=>this.classNames.add(k),remove:k=>this.classNames.delete(k),contains:k=>this.classNames.has(k)};this.readyState=0;this.currentTime=0;}
 setAttribute(k,v){this.attributes[k]=String(v);if(k==='id')registry.set(String(v),this);if(k.startsWith('data-'))this.dataset[k.slice(5)]=String(v);if(k==='class')for(const n of String(v).split(/\s+/))this.classNames.add(n);}
 getAttribute(k){return this.attributes[k]}removeAttribute(k){delete this.attributes[k]}
 appendChild(e){this.children.push(e);return e}prepend(e){this.children.unshift(e)}replaceChildren(...e){this.children=e}
 set innerHTML(s){this._html=s;this.children=[];parse(s,this)}get innerHTML(){return this._html||''}
 addEventListener(n,f){(this.listeners[n]??=[]).push(f)}
 pause(){}play(){return Promise.resolve()}remove(){}setPointerCapture(){}releasePointerCapture(){}
 createSVGPoint(){return{x:0,y:0,matrixTransform(){return{x:this.x,y:this.y}}}}getScreenCTM(){return{inverse:()=>({})}}
 click(){if(this.tagName==='a')downloads.push({name:this.download,url:this.href});if(this.onclick)this.onclick({target:this})}
 cloneNode(){const e=new Element(this.tagName);e.attributes={...this.attributes};e.children=this.children.map(c=>c.cloneNode());e.textContent=this.textContent;return e}
}
function parse(s,parent){for(const m of s.matchAll(/<(\w[\w-]*)([^>]*)>/g)){const e=new Element(m[1]);for(const a of m[2].matchAll(/([\w-]+)="([^"]*)"/g))e.setAttribute(a[1],a[2]);if(/\bchecked\b/.test(m[2]))e.checked=true;if(parent&&m[1]==='button')parent.appendChild(e)}}
const escape=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const serialize=e=>`<${e.tagName}${Object.entries(e.attributes).map(([k,v])=>' '+k+'="'+escape(v)+'"').join('')}>${escape(e.textContent)}${e.children.map(serialize).join('')}</${e.tagName}>`;
parse(html);registry.get('report-data').textContent=payload;registry.get('filter-status').value='crossing';
const document={getElementById(id){assert(registry.has(id),'missing element '+id);return registry.get(id)},createElement:t=>new Element(t),createElementNS:(ns,t)=>new Element(t),body:new Element('body')};
const ctx={document,window:{},console,Blob,URL:{createObjectURL:b=>{const u='blob:'+blobs.size;blobs.set(u,b);return u},revokeObjectURL:()=>{}},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},setTimeout:()=>1,clearTimeout:()=>{},XMLSerializer:class{serializeToString(e){return serialize(e)}}};
vm.createContext(ctx);vm.runInContext(scripts.at(-1)[1],ctx,{filename:file});
const api=ctx.window.CROSSING_REPORT,D=api.data,$=id=>document.getElementById(id),walk=e=>[e,...e.children.flatMap(walk)];
assert.equal(D.cases.length,250);assert.equal(Object.keys(D.scenes).length,10);assert.equal(Object.values(D.scenes).reduce((n,s)=>n+s.crossings.length,0),55);
assert.equal(api.getState().episode_id,D.example_id);assert.equal(api.filteredCases().length,48);
let red=0,video=0;
for(const c of D.cases){
 api.selectCase(c.episode_id);assert.equal(api.getState().episode_id,c.episode_id);api.setFrame(-9);assert.equal(api.getState().frame,0);api.setFrame(c.frames+9);assert.equal(api.getState().frame,c.frames-1);assert(!$('map').getAttribute('viewBox').includes('NaN'));
 const redPaths=walk($('map')).filter(e=>e.tagName==='polyline'&&e.getAttribute('data-divergence')==='true');
 if(c.review.status==='crossing'){assert.equal(redPaths.length,1);assert(c.review.highlight.length_m<=1.20001);assert.equal(c.review.highlight.start_frame,c.review.frame);red++;}else assert.equal(redPaths.length,0);
 if(c.video){assert(fs.existsSync(path.resolve(path.dirname(file),c.video)));assert(c.snapshots.length>=3);assert($('snapshot').src.startsWith('data:image/jpeg;base64,'));video++;}else assert.equal(c.snapshots.length,0);
}
let crossings=0;for(const[sid,s]of Object.entries(D.scenes)){api.selectCase(D.cases.find(c=>c.scene===sid).episode_id);for(const c of s.crossings){api.selectCross(c.id);assert.equal(api.getState().selectedCross,c.id);crossings++;}}
for(const[status,count]of Object.entries({crossing:48,uncertain:16,other:41,normal:105,failed:151,success:99,excluded:46,'':250})){$('filter-status').value=status;$('filter-status').onchange();assert.equal(api.filteredCases().length,count)}
$('filter-status').value='';$('filter-scene').value='kujiale_0259';$('filter-scene').onchange();assert.equal(api.filteredCases().length,24);
$('search').value='55_0';$('search').oninput();assert.equal(api.filteredCases().length,1);$('search').value='nothing-matches';$('search').oninput();assert.equal(api.filteredCases().length,0);
$('example').onclick();assert.equal(api.getState().episode_id,D.example_id);assert.equal(api.getState().frame,35);assert.equal(api.filteredCases().length,48);
const c=D.cases.find(c=>c.episode_id===D.example_id),s=D.scenes[c.scene],p=c.review.highlight.points[0],event={button:0,clientX:(p[0]-s.low[0])/s.resolution,clientY:(s.high[1]-p[1])/s.resolution,pointerId:1};
api.setFrame(0);$('map').listeners.pointerdown[0](event);$('map').listeners.pointerup[0](event);assert.equal(api.getState().frame,35);
$('show-actual').checked=false;$('show-actual').onchange();assert.equal(walk($('map')).filter(e=>e.tagName==='polyline'&&e.getAttribute('data-divergence')).length,0);$('show-actual').checked=true;$('show-actual').onchange();
$('zoom-in').onclick();$('zoom-out').onclick();$('fit').onclick();$('jump').onclick();assert.equal(api.getState().frame,35);
$('user-label').value='uncertain';$('user-label').onchange();$('user-comment').value='Functional verification only';$('user-comment').oninput();$('export').onclick();assert.equal(downloads.at(-1).name,'seed2_crossing_review_comments.json');
(async()=>{const ex=JSON.parse(await blobs.get(downloads.at(-1).url).text());assert.equal(ex.edits[D.example_id].label,'uncertain');assert.equal(ex.original_summary.crossing,48);$('save-map').onclick();const svg=await blobs.get(downloads.at(-1).url).text();assert(svg.includes('data-divergence="true"'));fs.writeFileSync(path.join(path.dirname(file),'example_map.svg'),svg);const result={passed:true,environment:'Node VM with DOM shim; not a rendered browser or video-playback test',case_navigation:250,all_crossing_clicks:crossings,short_red_segments:red,portable_video_links:video,frame_bounds:true,all_status_filters:true,search_and_scene_filter:true,red_segment_click_jumps_to_frame:true,zoom_controls:true,review_export:true,svg_export:true};fs.writeFileSync(path.join(path.dirname(file),'validation_ui.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));})().catch(e=>{console.error(e);process.exitCode=1});
