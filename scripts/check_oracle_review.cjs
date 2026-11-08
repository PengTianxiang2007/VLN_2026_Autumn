/* UI logic check with a DOM shim; this is not rendered-browser validation. */
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const file=process.argv[2],html=fs.readFileSync(file,'utf8');
const payload=html.match(/<script id="payload" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1],D=JSON.parse(payload);
class Element{constructor(){this.style={};this.value='0';this.textContent='';this.innerHTML='';}setAttribute(k,v){this[k]=v}removeAttribute(k){delete this[k]}load(){}}
const elements=new Map([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
elements.get('payload').textContent=payload;
const context={document:{getElementById:id=>{assert(elements.has(id),id);return elements.get(id)}},window:{scrollTo:()=>{}}};
vm.createContext(context);vm.runInContext(script,context);
assert.equal(D.cases.length,10);
assert.equal((elements.get('rows').innerHTML.match(/<tr>/g)||[]).length,10);
for(let i=0;i<D.cases.length;i++){
 elements.get('case').value=String(i);elements.get('case').onchange();
 const c=D.cases[i];assert.equal(elements.get('instruction').textContent,c.instruction);
 assert(!/NaN|undefined/.test(elements.get('map').innerHTML));
 if(c.intervention){assert(elements.get('map').innerHTML.includes('stroke-dasharray'));assert(elements.get('images').innerHTML.includes(c.intervention.after_image));assert(c.intervention.memory_unchanged)}
 for(const iv of c.interventions){assert(elements.get('images').innerHTML.includes(iv.after_image));assert(iv.memory_unchanged)}
 assert((elements.get('map').innerHTML.match(/stroke-dasharray/g)||[]).length===c.interventions.length);
 for(const arm of ['control','oracle'])if(c[arm]){assert.equal(elements.get(arm+'Video').src,c[arm].video);assert(fs.existsSync(path.join(path.dirname(file),c[arm].video)))}
}
const result={passed:true,cases:10,environment:'Node DOM shim; not a rendered browser',jump_edges_dashed:true,all_video_files_present:true};
fs.writeFileSync(path.join(path.dirname(file),'ui_verification.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
