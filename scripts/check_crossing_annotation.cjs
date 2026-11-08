/* End-to-end checks against the actual file:// artifact, including saved HTML in a clean browser context. */
const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto'),os=require('os');
const env=JSON.parse(fs.readFileSync('/tmp/vln-oracle-ui-browser-direct-20261104/browser_env.json','utf8'));
Object.assign(process.env,{LD_LIBRARY_PATH:env.LD_LIBRARY_PATH,FONTCONFIG_FILE:env.FONTCONFIG_FILE});
const {chromium}=require(env.PLAYWRIGHT_MODULE);
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
(async()=>{
 const file=path.resolve(process.argv[2]),out=path.dirname(file),scratch=fs.mkdtempSync(path.join(os.tmpdir(),'crossing-annotation-check-'));
 const errors=[],requests=[],checks=[];
 const browser=await chromium.launch({executablePath:env.CHROMIUM_EXECUTABLE,headless:true,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']});
 const contexts=[];
 async function open(file){const context=await browser.newContext({viewport:{width:1600,height:1180},acceptDownloads:true});contexts.push(context);const p=await context.newPage();p.on('pageerror',e=>errors.push(String(e)));p.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url())});await p.goto('file://'+file,{waitUntil:'load',timeout:180000});await p.evaluate(()=>document.fonts.ready);await p.waitForFunction(()=>document.getElementById('loading').hidden&&document.getElementById('map').dataset.frame!==undefined);return p}
 async function settle(p,i,frame){await p.waitForFunction(({i,frame})=>{const d=JSON.parse(document.getElementById('data').textContent),im=document.getElementById('rgb'),m=document.getElementById('map');return document.getElementById('loading').hidden&&im.complete&&im.naturalWidth===640&&im.dataset.episodeId===d.cases[i].episode_id&&Number(im.dataset.frame)===frame&&Number(m.dataset.frame)===frame&&m.dataset.episodeId===im.dataset.episodeId},{i,frame},{timeout:15000})}
 async function select(p,i){await p.selectOption('#case-select',String(i));await settle(p,i,0)}
 async function frame(p,i,n,slider='rgb-slider'){await p.locator('#'+slider).evaluate((el,n)=>{el.value=String(n);el.dispatchEvent(new Event('input',{bubbles:true}))},n);await settle(p,i,n)}
 async function download(p,name){const event=p.waitForEvent('download',{timeout:120000});await p.click('#save-html');const d=await event;const f=path.join(scratch,name);await d.saveAs(f);return f}
 function extract(file,id){const html=fs.readFileSync(file,'utf8'),start=`<script id="${id}" type="application/json">`,a=html.indexOf(start);assert(a>=0,id+' missing');const b=html.indexOf('</script>',a);return JSON.parse(html.slice(a+start.length,b))}
 try{
  let page=await open(file);
  const metadata=await page.evaluate(()=>{const d=JSON.parse(document.getElementById('data').textContent);return{summary:d.summary,cases:d.cases.map(c=>({id:c.episode_id,frames:c.frames.length,reused:c.frames.filter(f=>f.rgb_reused).map(f=>f.frame),group:c.group})),dataset_id:d.dataset_id}});
  assert.equal(metadata.cases.length,69);assert.equal(metadata.cases.filter(c=>c.group==='failure').length,39);assert.equal(metadata.cases.filter(c=>c.group==='success').length,30);
  for(let i=0;i<metadata.cases.length;i++){
   await select(page,i);const c=metadata.cases[i],sample=[...new Set([0,Math.floor(c.frames/2),c.frames-1,...c.reused])];
   assert(await page.evaluate(i=>{const c=JSON.parse(document.getElementById('data').textContent).cases[i];return document.getElementById('instruction').textContent===(c.instruction_zh||c.instruction)},i),'Wrong displayed instruction');
   for(const [j,n] of sample.entries()){
    await frame(page,i,n,j%2?'map-slider':'rgb-slider');
    const result=await page.evaluate(({i,n})=>{const d=JSON.parse(document.getElementById('data').textContent),c=d.cases[i],f=c.frames[n],im=document.getElementById('rgb'),cv=document.getElementById('map'),images=JSON.parse(document.getElementById('media-'+c.episode_id).textContent),[x,y]=JSON.parse(cv.dataset.currentPixel);return{imageMatches:im.src===images[n],position:JSON.parse(cv.dataset.position),expectedPosition:f.position,sliders:['rgb-slider','map-slider'].map(id=>document.getElementById(id).value),pixel:[...cv.getContext('2d').getImageData(Math.round(x),Math.round(y),1,1).data],reused:f.rgb_reused,disabled:document.getElementById('mark-crossing').disabled,mediaLength:images.length}}, {i,n});
    assert(result.imageMatches);assert.equal(result.mediaLength,c.frames);assert.deepEqual(result.position,result.expectedPosition);assert.deepEqual(result.sliders,[String(n),String(n)]);assert.deepEqual(result.pixel,[116,65,198,255]);assert.equal(result.disabled,result.reused);
   }
   checks.push({episode_id:c.id,frames_checked:sample,media_frames:c.frames});
   if((i+1)%10===0)console.log(JSON.stringify({browser_cases_checked:i+1,total:69}));
  }
  await select(page,0);await frame(page,0,5);await page.click('#mark-crossing');assert.equal(await page.locator('#marks tr').count(),1);
  await page.click('#mark-crossing');assert.equal(await page.locator('#marks tr').count(),1);
  await page.click('#mark-error');assert.equal(await page.locator('#marks tr').count(),1);assert((await page.locator('#marks').innerText()).includes('错误选择'));
  await frame(page,0,7);await page.click('#mark-error');assert.equal(await page.locator('#marks tr').count(),2);
  // Use the map marker itself, then selected-point deletion, followed by undo.
  await frame(page,0,5);const point=await page.locator('#map').evaluate(cv=>JSON.parse(cv.dataset.currentPixel)),box=await page.locator('#map').boundingBox();
  await page.mouse.click(box.x+point[0]*box.width/960,box.y+point[1]*box.height/720);await page.waitForFunction(()=>document.getElementById('delete-selected').disabled===false);
  await page.click('#delete-selected');assert.equal(await page.locator('#marks tr').count(),1);assert.equal(await page.locator('#map').getAttribute('data-marker-count'),'1');
  await page.click('#undo-delete');await page.waitForFunction(()=>document.querySelectorAll('#marks tr').length===2);assert.equal(await page.locator('#map').getAttribute('data-marker-count'),'2');
  await page.locator('#marks tr').filter({hasText:'帧 7 ·'}).locator('[data-delete]').click();assert.equal(await page.locator('#marks tr').count(),1);
  await frame(page,0,5);await page.click('#change-type');assert(!(await page.locator('#marks').innerText()).includes('错误选择'));await page.check('#completed');
  await select(page,1);await page.check('#completed'); // Explicitly reviewed task with zero marks.
  await select(page,40);await frame(page,40,10);await page.click('#mark-crossing');await page.check('#completed');
  // Local auto-save survives a page reload, but exported data must not depend on it.
  page.once('dialog',d=>d.accept());await page.reload({waitUntil:'load',timeout:180000});await settle(page,40,10);assert.equal(await page.locator('#marks tr').count(),1);assert(await page.isChecked('#completed'));
  const first=await download(page,'saved-first.html'),a=extract(first,'annotations');assert.equal(Object.values(a.cases).reduce((n,c)=>n+c.marks.length,0),2);assert.equal(Object.values(a.cases).filter(c=>c.completed).length,3);
  assert.equal(a.cases[metadata.cases[0].id].marks[0].frame,5);assert.equal(a.cases[metadata.cases[0].id].marks[0].type,'crossing');assert(!a.cases[metadata.cases[0].id].marks.some(m=>m.frame===7));assert(a.cases[metadata.cases[1].id].completed);assert.equal(a.cases[metadata.cases[1].id].marks.length,0);
  await page.context().close();page=await open(first);await settle(page,40,10);assert.equal(await page.locator('#marks tr').count(),1);assert(await page.isChecked('#completed'));
  assert(await page.evaluate(()=>{const c=JSON.parse(document.getElementById('data').textContent).cases[40];return document.getElementById('instruction').textContent===(c.instruction_zh||c.instruction)}),'Saved HTML instruction language changed');
  assert.equal(await page.evaluate(()=>localStorage.length),0,'Fresh browser must not rely on draft storage');
  await select(page,0);await page.locator('#marks [data-jump]').click();await settle(page,0,5);await page.click('#delete-selected');assert.equal(await page.locator('#map').getAttribute('data-marker-count'),'0');
  const second=await download(page,'saved-after-deletion.html'),b=extract(second,'annotations');assert.equal(b.cases[metadata.cases[0].id].marks.length,0);assert.equal(b.cases[metadata.cases[40].id].marks.length,1);assert.notEqual(a.document_id,b.document_id);
  assert.deepEqual(extract(file,'data'),extract(second,'data'),'Saving must preserve source metadata');
  // Every frame payload is byte-for-byte preserved across both export generations.
  const original=fs.readFileSync(file,'utf8'),saved=fs.readFileSync(second,'utf8');
  function mediaHashes(html){const re=/<script id="media-([^"]+)" type="application\/json">([\s\S]*?)<\/script>/g,rows=[];let match;while((match=re.exec(html)))rows.push([match[1],hash(match[2])]);return rows}
  assert.deepEqual(mediaHashes(original),mediaHashes(saved));assert.equal(mediaHashes(saved).length,69);
  await page.context().close();page=await open(second);await settle(page,0,5);assert.equal(await page.locator('#marks tr').count(),0);assert.equal(await page.locator('#map').getAttribute('data-marker-count'),'0');
  await select(page,40);await frame(page,40,10);assert.equal(await page.locator('#marks tr').count(),1);
  await page.click('#delete-selected');await select(page,0);await page.click('#undo-delete');await settle(page,40,10);assert.equal(await page.locator('#marks tr').count(),1); // Undo across tasks.
  await page.click('#play');await page.waitForTimeout(650);await page.click('#play');const paused=await page.locator('#rgb-slider').inputValue();assert(Number(paused)>10);await page.waitForTimeout(350);assert.equal(await page.locator('#rgb-slider').inputValue(),paused);
  await page.selectOption('#filter','success');assert.equal(await page.locator('#case-select option').count(),30);await page.selectOption('#filter','failure');assert.equal(await page.locator('#case-select option').count(),39);
  await page.selectOption('#filter','all');await select(page,0);await frame(page,0,25);await page.click('#mark-crossing');await frame(page,0,35);await page.click('#mark-error');await page.screenshot({path:path.join(out,'preview_annotation.png'),fullPage:true});
  await page.click('#zoom-in');await page.click('#zoom-reset');
  await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile overflow');await page.screenshot({path:path.join(out,'preview_mobile.png'),fullPage:true});
  assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
  const result={passed:true,checked_at:new Date().toISOString(),cases:69,source_frames:metadata.summary.frames,browser_frames_checked:checks.reduce((n,c)=>n+c.frames_checked.length,0),case_checks:checks,duplicate_prevention:true,type_change:true,map_selection:true,row_delete:true,selected_delete:true,undo_delete:true,cross_case_undo:true,auto_save_reload:true,empty_case_completion:true,saved_html_clean_context:true,deletion_survives_second_export:true,all_media_preserved:true,external_requests:requests,browser_errors:errors,test_exports_directory:scratch};
  fs.writeFileSync(path.join(out,'browser_check.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({...result,case_checks:undefined}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
