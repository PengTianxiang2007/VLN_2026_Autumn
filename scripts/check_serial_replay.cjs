'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert'),{pathToFileURL}=require('url');
const browserRoot=process.env.ORACLE_BROWSER_ROOT||'/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium}=require(path.join(browserRoot,'playwright-core')),portable=require(path.join(browserRoot,'@sparticuz/chromium'));
(async()=>{
 const file=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);fs.mkdirSync(out,{recursive:true});
 const build=JSON.parse(fs.readFileSync(path.join(path.dirname(file),'build.json'),'utf8'));
 const browser=await chromium.launch({executablePath:await portable.executablePath(),headless:true,args:['--no-sandbox','--no-zygote','--disable-gpu','--disable-software-rasterizer','--disable-dev-shm-usage','--allow-file-access-from-files']});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1150},acceptDownloads:true});const errors=[],remote=[];
  page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url())});
  await page.goto(pathToFileURL(file).href,{waitUntil:'load',timeout:60000});
  await page.waitForFunction(()=>window.SERIAL_REPLAY);await page.evaluate(()=>document.fonts.ready);
  const data=await page.evaluate(()=>{const d=window.SERIAL_REPLAY.data;return {...d,images:d.images.map(x=>x.slice(0,32))}});
  assert.deepEqual(data.summary,build.summary);assert.equal(await page.locator('#language').inputValue(),'zh');
  assert.notEqual(await page.locator('#language').evaluate(e=>getComputedStyle(e).color),'rgb(255, 255, 255)');
  assert.equal(await page.locator('#instruction').textContent(),data.instruction.zh);
  assert.equal(data.summary.full_chain_observed,false);assert.equal(data.requests.length,53);
  assert((await page.locator('#outcome').textContent()).includes('未验证'));
  for(let i=0;i<data.frames.length;i++){
   await page.evaluate(i=>window.SERIAL_REPLAY.setFrame(i),i);await page.locator('#rgb').evaluate(im=>im.decode());
   const check=await page.evaluate(()=>{const a=window.SERIAL_REPLAY,s=a.state(),f=a.data.frames[s.frame];return{frame:s.frame,rgb:document.getElementById('rgb').src===a.data.images[f.image],map:document.getElementById('map-timeline').value,slider:document.getElementById('rgb-timeline').value,bad:[...document.querySelectorAll('#map *')].some(el=>[...el.attributes].some(v=>/NaN|undefined/.test(v.value)))}});
   assert.equal(check.frame,i);assert(check.rgb);assert.equal(check.map,String(i));assert.equal(check.map,check.slider);assert(!check.bad);
  }
  for(const node of data.nodes){await page.evaluate(id=>window.SERIAL_REPLAY.chooseNode(id),node.id);const s=await page.evaluate(()=>window.SERIAL_REPLAY.state());assert.equal(s.frame,node.emittedAt);assert.deepEqual(s.nodes.ids,node.retained_after);assert.equal(s.requestIndex,node.deviation_request)}
  let translations=0;
  for(let i=0;i<data.requests.length;i++){
   const c=data.requests[i];await page.evaluate(i=>{const a=window.SERIAL_REPLAY,c=a.data.requests[i];a.setFrame(c.frame);document.querySelector(`[data-stage="${c.stage}"]`).click()},i);
   await page.selectOption('#request-picker',String(i));
   for(const language of ['zh','en']){
    await page.selectOption('#language',language);assert.equal(await page.evaluate(()=>window.SERIAL_REPLAY.state().frame),c.frame);assert.equal(await page.locator('#request-picker').inputValue(),String(i));
    assert.equal(await page.locator('#instruction').textContent(),data.instruction[language]);
    const body=await page.locator('#answer').textContent();const tr=v=>v&&typeof v==='object'?v[language]:v;
    if(c.stage==='dedup'){assert(body.includes(tr(c.answer.reason)));for(const b of c.answer.matched_branches)assert(body.includes(tr(b.description)));for(const value of [...c.answer.a_only,...c.answer.b_only])assert(body.includes(tr(value)))}
    if(c.stage==='deviation'){for(const key of ['segment_summary','reason','semantic_progress'])if(c.answer[key])assert(body.includes(tr(c.answer[key])));assert(body.includes(tr(c.prior_progress)));for(const q of c.answer.uncertainties)assert(body.includes(tr(q)));for(const q of c.answer.visual_evidence)assert(body.includes(tr(q.description)));for(const q of c.answer.instruction_evidence)assert(body.includes(q[language==='zh'?'quote_zh':'quote_en']))}
    const prompt=await page.locator('#prompt').textContent();if(c.stage==='jev'){for(const v of [data.prompts.jev[language].context,data.prompts.jev[language].instructions,...Object.values(data.prompts.jev[language].criteria)])assert(prompt.includes(v))}else assert.equal(prompt,data.prompts[c.stage][language]);
    assert.deepEqual(JSON.parse(await page.locator('#raw-request').textContent()),c.raw_request);assert.deepEqual(JSON.parse(await page.locator('#raw-answer').textContent()),c.raw_answer);
    assert.equal(await page.locator('#input-images img').count(),c.images.length);await page.locator('#input-images img').evaluateAll(imgs=>Promise.all(imgs.map(im=>im.decode())));translations++;
   }
  }
  await page.selectOption('#language','zh');await page.locator('#start').click();await page.locator('[data-stage="deviation"]').click();assert(await page.locator('#request-empty').isVisible());
  await page.locator('#map-timeline').evaluate(e=>{e.value=12;e.dispatchEvent(new Event('input',{bubbles:true}))});assert.equal(await page.locator('#rgb-timeline').inputValue(),'12');
  await page.locator('#rgb-timeline').evaluate(e=>{e.value=20;e.dispatchEvent(new Event('input',{bubbles:true}))});assert.equal(await page.locator('#map-timeline').inputValue(),'20');
  await page.locator('#rgb').click();assert(await page.locator('#dialog').isVisible());await page.locator('#close').click();
  const oldView=await page.locator('#map').getAttribute('viewBox');await page.locator('#zoom-in').click();assert.notEqual(await page.locator('#map').getAttribute('viewBox'),oldView);await page.locator('#fit').click();
  await page.locator('input[data-layer="historical"]').uncheck();assert.equal(await page.locator('.historical-route').count(),0);await page.locator('input[data-layer="historical"]').check();
  await page.locator('#start').click();await page.locator('#show-all').uncheck();assert.equal(await page.locator('#node-table tbody tr').count(),0);await page.locator('#show-all').check();assert.equal(await page.locator('#node-table tbody tr').count(),7);
  await page.selectOption('#speed','400');await page.locator('#play').click();await page.waitForTimeout(550);assert((await page.evaluate(()=>window.SERIAL_REPLAY.state().frame))>0);await page.locator('#play').click();
  await page.locator('#note').fill('浏览器导出验证');let pending=page.waitForEvent('download');await page.locator('#export-notes').click();let dl=await pending;await dl.saveAs(path.join(out,'notes.json'));assert(JSON.parse(fs.readFileSync(path.join(out,'notes.json'),'utf8')).notes.some(n=>n.note==='浏览器导出验证'));
  await page.locator('#note').fill('');pending=page.waitForEvent('download');await page.locator('#export-csv').click();dl=await pending;await dl.saveAs(path.join(out,'frames.csv'));assert.equal(fs.readFileSync(path.join(out,'frames.csv'),'utf8').trim().split('\n').length,41);
  await page.evaluate(()=>window.SERIAL_REPLAY.chooseNode('S07'));await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(out,'overview_zh.png')});await page.locator('#answer').screenshot({path:path.join(out,'review_zh.png')});
  await page.selectOption('#language','en');await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(out,'overview_en.png')});await page.locator('#answer').screenshot({path:path.join(out,'review_en.png')});
  await page.selectOption('#language','zh');await page.locator('#end').click();assert((await page.locator('#rgb-note').textContent()).includes('未采集'));
  await page.setViewportSize({width:390,height:844});await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(out,'mobile.png')});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
  const result={passed:true,frames_checked:data.frames.length,requests_checked:data.requests.length,bilingual_views:translations,nodes_checked:data.nodes.length,dual_sliders:true,causal_visibility:true,raw_records_preserved:true,complete_prompt_translations:true,notes_export:true,csv_rows:40,mobile_verified:true,page_errors:errors,remote_requests:remote};
  fs.writeFileSync(path.join(out,'validation.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
