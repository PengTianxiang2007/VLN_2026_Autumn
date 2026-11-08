/* Exercise the exported file in an existing CPU-only Chromium runtime. */
'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto');
const {pathToFileURL}=require('url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright-core');
const file=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_EXECUTABLE,headless:true,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-zygote']});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1100},deviceScaleFactor:1});const errors=[],remote=[];
  page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url())});
  await page.goto(pathToFileURL(file).href,{waitUntil:'load',timeout:120000});
  await page.waitForFunction(()=>window.CROSSING_REVIEW?.state().tag==='selected_validation');
  await page.evaluate(()=>document.fonts.ready);await page.locator('#rgb').evaluate(i=>i.decode());
  const embeddedFont=await page.evaluate(()=>[...document.fonts].some(f=>f.family==='CrossingSans'&&f.status==='loaded')&&document.fonts.check('16px CrossingSans','开发验证离线复核侧门漏检'));
  assert(embeddedFont,'Embedded Chinese font must be loaded');
  assert.equal(await page.locator('.runChoice').count(),4);assert.equal(await page.locator('#cases button').count(),15);assert.equal(await page.locator('#stats .metric').count(),6);
  await page.screenshot({path:path.join(out,'01_overview.png')});
  const dataCheck=await page.evaluate(()=>{
   const app=window.CROSSING_REVIEW;let observations=0;const counts={};
   for(const [tag,data] of Object.entries(app.bundle.runs)){
    counts[tag]=Object.keys(data.cases).length;
    for(const c of Object.values(data.cases))for(const s of c.snapshots){
     if(!s.image.startsWith('data:image/jpeg;base64,')||s.image_frames.some(f=>f>s.frame)||s.executed_actions.some(a=>a.index>=s.frame)||s.events.some(e=>e.last_seen_frame>s.frame||e.confirmation_frame>s.frame||e.closed_frame>s.frame))throw Error('Noncausal or missing image');
     observations++;
    }
   }return {observations,counts};
  });assert.equal(dataCheck.observations,1791);assert.deepEqual(dataCheck.counts,{baseline:5,r01_connectivity:5,r02_inventory_first:5,selected_validation:15});
  let views=0,events=0,annotationLinks=0;
  for(const tag of Object.keys(dataCheck.counts)){
   await page.locator(`[data-run="${tag}"]`).click();
   const ids=await page.evaluate(()=>Object.keys(window.CROSSING_REVIEW.data.cases));
   for(const id of ids){
    await page.evaluate(id=>window.CROSSING_REVIEW.select(id),id);
    const checked=await page.evaluate(()=>{
     const app=window.CROSSING_REVIEW,c=app.data.cases[app.state().episode_id];let events=0,annotations=0;
     function check(frame){const s=app.state(),row=c.snapshots[s.index];if(s.frame!==frame||document.getElementById('rgb').src!==row.image||document.getElementById('answer').textContent!==JSON.stringify(row.prediction,null,2))throw Error('Displayed frame mismatch');}
     for(const n of [0,Math.floor(c.snapshots.length/2),c.snapshots.length-1]){app.seek(n);check(c.snapshots[n].frame)}
     for(const e of app.events()){app.chooseEvent(e);check(e.frame);events++}
     for(const p of c.current_annotations){app.chooseCurrent(p);check(p.confirmation_frame);annotations++}
     for(const p of c.prior_annotations){app.choosePrior(p);check(p.closest_frame);annotations++}
     document.getElementById('eventFilter').value='missed';document.getElementById('eventFilter').dispatchEvent(new Event('change'));
     if(document.getElementById('eventList').children.length!==c.metrics['1.0'].fn)throw Error('Missed filter mismatch');
     document.getElementById('eventFilter').value='all';document.getElementById('eventFilter').dispatchEvent(new Event('change'));
     app.seek(0);return {events,annotations};
    });views++;events+=checked.events;annotationLinks+=checked.annotations;
    await page.locator('#rgb').evaluate(i=>i.decode());
   }
   const successCount=await page.evaluate(()=>Object.values(window.CROSSING_REVIEW.data.cases).filter(c=>c.source_success).length);
   await page.locator('#filters').selectOption('success');assert.equal(await page.locator('#cases button').count(),successCount);
   await page.locator('#filters').selectOption('failure');assert.equal(await page.locator('#cases button').count(),ids.length-successCount);
   await page.locator('#filters').selectOption('all');
  }
  assert.equal(views,30);assert.equal(events,76);
  // Version switching must retain the same causal position, with isolated review notes.
  await page.evaluate(()=>{const a=window.CROSSING_REVIEW;a.selectRun('baseline');a.select('kujiale_0113_1_4');a.jump(18)});
  await page.locator('#note').fill('Browser test baseline');await page.locator('#category').selectOption('visual_miss');
  await page.locator('[data-run="r01_connectivity"]').click();assert.equal((await page.evaluate(()=>window.CROSSING_REVIEW.state())).frame,18);
  assert.equal(await page.locator('#note').inputValue(),'');await page.locator('#note').fill('Browser test r01');
  await page.locator('[data-run="baseline"]').click();assert.equal(await page.locator('#note').inputValue(),'Browser test baseline');
  const pending=page.waitForEvent('download');await page.locator('#export').click();const download=await pending;await download.saveAs(path.join(out,download.suggestedFilename()));
  const notes=JSON.parse(fs.readFileSync(path.join(out,download.suggestedFilename()),'utf8'));assert.equal(notes.tag,'baseline');assert.equal(notes.notes.length,1);assert.equal(notes.notes[0].frame,18);assert.equal(notes.notes[0].note,'Browser test baseline');
  await page.evaluate(()=>localStorage.clear());
  await page.evaluate(()=>{window.CROSSING_REVIEW.selectRun('selected_validation');window.CROSSING_REVIEW.select('kujiale_0232_2_4');window.CROSSING_REVIEW.jump(21)});
  await page.locator('#rgb').evaluate(i=>i.decode());await page.screenshot({path:path.join(out,'02_checkpoint_comparison.png'),fullPage:true});
  await page.locator('#rgb').click();assert(await page.locator('#imageDialog').isVisible());await page.locator('#largeImage').evaluate(i=>i.decode());await page.locator('#closeImage').click();
  await page.locator('#showCurrent').uncheck();assert.equal(await page.evaluate(()=>window.CROSSING_REVIEW.annotationLayers().current.length),0);await page.locator('#showCurrent').check();
  await page.locator('#showPrior').uncheck();assert.equal(await page.evaluate(()=>window.CROSSING_REVIEW.annotationLayers().prior.length),0);await page.locator('#showPrior').check();
  await page.locator('#full').uncheck();await page.evaluate(()=>window.CROSSING_REVIEW.seek(0));assert.equal(await page.evaluate(()=>window.CROSSING_REVIEW.annotationLayers().current.length),0);await page.locator('#full').check();
  await page.locator('#play').click();await page.waitForTimeout(1100);assert((await page.evaluate(()=>window.CROSSING_REVIEW.state().index))>0);await page.locator('#play').click();
  const paused=await page.evaluate(()=>window.CROSSING_REVIEW.state().index);await page.waitForTimeout(600);assert.equal(await page.evaluate(()=>window.CROSSING_REVIEW.state().index),paused);
  await page.locator('#frame').evaluate(e=>{e.value=10;e.dispatchEvent(new Event('input',{bubbles:true}))});assert.equal((await page.evaluate(()=>window.CROSSING_REVIEW.state())).index,10);
  await page.locator('h1').click();await page.keyboard.press('ArrowRight');assert.equal((await page.evaluate(()=>window.CROSSING_REVIEW.state())).index,11);
  await page.locator('summary').filter({hasText:'直接查看典型问题'}).click();
  const bookmarks=await page.evaluate(()=>window.CROSSING_REVIEW.bundle.bookmarks);
  for(let i=0;i<bookmarks.length;i++){
   await page.locator('#bookmarks button').nth(i).click();const s=await page.evaluate(()=>window.CROSSING_REVIEW.state());assert.equal(s.tag,bookmarks[i].tag);assert.equal(s.episode_id,bookmarks[i].episode);assert.equal(s.frame,bookmarks[i].frame);
  }
  await page.locator('[data-run="r02_inventory_first"]').click();await page.locator('#rgb').evaluate(i=>i.decode());await page.screenshot({path:path.join(out,'03_development_duplicate.png')});
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(150);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
  await page.locator('h1').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,'04_mobile.png')});
  assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
  const result={passed:true,browser:await browser.version(),runs:4,case_version_views:views,unique_episodes:20,causal_observations:dataCheck.observations,event_jumps:events,annotation_jumps:annotationLinks,bookmarks:bookmarks.length,same_frame_version_switch:true,isolated_notes_and_export:true,play_pause_seek_keyboard:true,layer_toggles:true,image_enlargement:true,mobile_no_overflow:true,embedded_chinese_font_loaded:embeddedFont,external_requests:0,page_errors:0,html_sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')};
  fs.writeFileSync(path.join(out,'browser_verification.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
