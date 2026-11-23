'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert'),{pathToFileURL}=require('url');
const runtime='/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium}=require(path.join(runtime,'playwright-core')),portable=require(path.join(runtime,'@sparticuz/chromium'));
(async()=>{
 const folder=path.resolve(process.argv[2]),dest=path.join(folder,'validation');fs.mkdirSync(dest,{recursive:true});
 const data=JSON.parse(fs.readFileSync(path.join(folder,'snapshot_public.json'),'utf8'));
 assert.equal(data.completed_ids.length,4);let calls=0,nodes=0,terminal=0;
 for(const c of data.cases){
  assert.equal(c.scores.length,c.pose.length-1);if(!c.dedup)continue;
  const ds=c.dedup,kept=ds.decisions.at(-1).active_ids_after;
  assert.deepEqual(ds.nodes.filter(n=>!n.terminal_node).map(n=>n.source_id),kept);
  for(const n of ds.nodes){if(n.terminal_node)terminal++;else nodes++}
  for(const d of ds.decisions){
   const answer=d.answer||{},texts=[d.reason,...(answer.matched_branches||[]).map(m=>m.description),...(answer.a_only||[]),...(answer.b_only||[])];
   for(const text of texts)assert(data.translations[text],text);
   if(d.needs_model){calls++;assert.equal(d.raw_content,d.response.response.choices[0].message.content);assert.equal(d.answer.reason,d.reason)}
  }
 }
 assert.equal(nodes,71);assert.equal(terminal,4);assert.equal(calls,134);
 const browser=await chromium.launch({executablePath:await portable.executablePath(),headless:true,args:['--no-sandbox','--no-zygote','--disable-gpu','--disable-software-rasterizer','--disable-dev-shm-usage','--allow-file-access-from-files']});
 try{
  const page=await browser.newPage({viewport:{width:1500,height:1080},acceptDownloads:true});const errors=[],remote=[];
  page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url())});
  await page.goto(pathToFileURL(path.join(folder,'index.html')).href,{waitUntil:'load',timeout:45000});
  await page.waitForFunction(()=>window.RxRSnapshot&&loadedRGB);
  assert.equal(await page.locator('#task option').count(),30);assert.equal(await page.locator('#zh').getAttribute('aria-pressed'),'true');
  for(const c of data.cases.filter(c=>c.dedup)){
   await page.selectOption('#task',c.id);await page.waitForFunction(()=>loadedRGB);
   assert.equal(await page.locator('#nodeButtons button').count(),c.dedup.nodes.length);
   const samples=[1,c.dedup.decisions.findIndex(d=>d.relation==='same'),c.dedup.decisions.findIndex(d=>d.relation==='uncertain')].filter(i=>i>=0);
   for(const index of [...new Set(samples)]){
    const d=c.dedup.decisions[index];await page.selectOption('#roundPicker',String(index));
    for(const language of ['zh','en']){
     await page.click('#'+language);assert.equal(await page.locator('#reviewReason').textContent(),language==='zh'?d.reason:data.translations[d.reason]);
     const state=await page.evaluate(()=>window.RxRSnapshot.inspect());assert.equal(state.frame,d.current_frame);assert.equal(state.choice,index);
     assert.equal(await page.locator('#instruction').textContent(),c.instruction[language==='zh'?0:1]);
     assert.equal(await page.locator('#dedupPrompt').textContent(),data.prompts['dedup_'+language]);
     if(d.needs_model)assert.equal(await page.locator('#rawAnswer').textContent(),d.raw_content);
    }
   }
  }
  await page.click('#zh');await page.selectOption('#task',data.completed_ids[0]);
  await page.locator('#mapStep').evaluate(e=>{e.value=10;e.dispatchEvent(new Event('input',{bubbles:true}))});assert.equal(await page.locator('#imageStep').inputValue(),'10');
  await page.locator('#imageStep').evaluate(e=>{e.value=15;e.dispatchEvent(new Event('input',{bubbles:true}))});assert.equal(await page.locator('#mapStep').inputValue(),'15');
  await page.locator('#nodeButtons button').first().click();assert.equal(await page.locator('#imageStep').inputValue(),String(data.cases[0].dedup.nodes[0].index));
  await page.click('#roundNext');await page.click('#roundPrev');await page.uncheck('#effectiveLayer');await page.check('#effectiveLayer');
  await page.selectOption('#task',data.cases[4].id);assert.equal(await page.locator('#nodeButtons button').count(),0);assert(await page.locator('#reviewEmpty').isVisible());assert(await page.locator('#reviewBody').isHidden());
  await page.selectOption('#task',data.completed_ids[0]);await page.locator('#reviewNote').fill('快照复核验证');await page.click('#saveNote');
  const pending=page.waitForEvent('download');await page.click('#downloadNotes');const download=await pending;await download.saveAs(path.join(dest,'notes.json'));assert(JSON.parse(fs.readFileSync(path.join(dest,'notes.json'),'utf8')).notes.some(r=>r.note==='快照复核验证'));
  await page.evaluate(()=>window.RXR_REPLAY.jump(0));await page.waitForFunction(()=>loadedRGB);await page.click('#play');await page.waitForTimeout(600);await page.click('#play');assert((await page.evaluate(()=>window.RXR_REPLAY.state().step))>0);
  await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(dest,'overview_zh.png')});
  await page.selectOption('#roundPicker','1');await page.locator('#dedupSection').screenshot({path:path.join(dest,'review_zh.png')});
  await page.click('#en');await page.locator('#dedupSection').screenshot({path:path.join(dest,'review_en.png')});
  await page.setViewportSize({width:390,height:844});await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(dest,'mobile.png')});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
  const report={passed:true,completed_cases:4,retained_nodes:nodes,terminal_nodes:terminal,raw_model_calls:calls,translations:Object.keys(data.translations).length,dual_sliders:true,bilingual_alignment:true,raw_answers_preserved:true,pending_cases_have_no_nodes:true,notes_export:true,playback:true,mobile:true,page_errors:errors};
  fs.writeFileSync(path.join(dest,'validation.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
