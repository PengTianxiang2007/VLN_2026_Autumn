'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert'),{pathToFileURL}=require('url');
const toolsRoot=process.env.ORACLE_BROWSER_ROOT||'/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium}=require(path.join(toolsRoot,'playwright-core'));
const portable=require(path.join(toolsRoot,'@sparticuz/chromium'));
(async()=>{
 const file=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);fs.mkdirSync(out,{recursive:true});
 const expected=JSON.parse(fs.readFileSync(process.argv[4]||file.replace(/\.html$/,'.build.json'),'utf8')).summary;
 const browser=await chromium.launch({executablePath:await portable.executablePath(),headless:true,args:['--no-sandbox','--no-zygote','--disable-gpu','--disable-software-rasterizer','--disable-dev-shm-usage','--allow-file-access-from-files']});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1200},acceptDownloads:true});
  async function checkRgb(){const missing=await page.evaluate(()=>window.ORACLE_DISTANCE.state().node.image==null);if(missing){assert(!(await page.locator('#rgb').isVisible()));assert(await page.locator('#missing-rgb').isVisible());assert.equal(await page.locator('#rgb').getAttribute('src'),null);}else{assert(await page.locator('#rgb').isVisible());await page.locator('#rgb').evaluate(i=>i.decode());}}
  const errors=[],remote=[];page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url())});
  await page.goto(pathToFileURL(file).href,{waitUntil:'load',timeout:120000});
  await page.waitForFunction(()=>window.ORACLE_DISTANCE&&!document.getElementById('loading'));
  await checkRgb();
  const summary=await page.evaluate(()=>window.ORACLE_DISTANCE.data.summary);
  assert.deepEqual(summary,expected);
  const taskCount=expected.tasks,hasOriginal=await page.evaluate(()=>window.ORACLE_DISTANCE.data.has_original!==false);
  assert.equal(await page.locator('#cases .case').count(),taskCount);
  if(!hasOriginal)assert.equal(await page.locator('#source option').count(),1);
  await page.screenshot({path:path.join(out,'overview.png'),fullPage:true});
  let eventCount=0,emptyCount=0;
  for(let ci=0;ci<taskCount;ci++){
   await page.evaluate(i=>window.ORACLE_DISTANCE.selectCase(i),ci);
   const info=await page.evaluate(()=>{const a=window.ORACLE_DISTANCE,s=a.state(),c=a.data.cases[s.caseIndex];return{events:c.events.length,zh:c.instruction_zh,en:c.instruction,id:c.id}});
   assert.equal(await page.locator('#instruction').textContent(),info.zh);if(expected.outcomes)assert((await page.locator('#review-note').textContent()).includes(await page.evaluate(()=>{const a=window.ORACLE_DISTANCE;return a.data.cases[a.state().caseIndex].review.reason_zh})));
   await checkRgb();
   const pos=await page.evaluate(()=>window.ORACLE_DISTANCE.state().nodeIndex);
   await page.selectOption('#language','en');assert.equal(await page.locator('#instruction').textContent(),info.en);assert.equal(await page.evaluate(()=>window.ORACLE_DISTANCE.state().nodeIndex),pos);
   if(expected.outcomes)assert((await page.locator('#review-note').textContent()).includes(await page.evaluate(()=>{const a=window.ORACLE_DISTANCE;return a.data.cases[a.state().caseIndex].review.reason_en})));await page.selectOption('#language','zh');
   if(!info.events){emptyCount++;assert(await page.locator('#no-event').isVisible());assert(!(await page.locator('#event-detail').isVisible()));}
   for(let ei=0;ei<info.events;ei++){
    await page.evaluate(i=>window.ORACLE_DISTANCE.selectEvent(i),ei);
    const before=await page.evaluate(()=>{const a=window.ORACLE_DISTANCE,s=a.state();return{index:s.nodeIndex,phase:s.node.phase,a:s.node.a,segment:s.node.segment,image:document.getElementById('rgb').getAttribute('src'),expected:a.data.images[s.event.before_image],event:s.event}});
    assert.equal(before.phase,'before');assert.equal(before.index,before.event.before);assert.equal(before.image,before.expected);
    await page.locator('#before-rgb').evaluate(i=>i.decode());await page.locator('#after-rgb').evaluate(i=>i.decode());
    await page.locator('#next').click();
    const after=await page.evaluate(()=>{const a=window.ORACLE_DISTANCE,s=a.state();return{index:s.nodeIndex,phase:s.node.phase,a:s.node.a,segment:s.node.segment,image:document.getElementById('rgb').getAttribute('src'),expected:a.data.images[s.event.after_image],bad:[...document.querySelectorAll('#map path,#map circle,#map text')].some(el=>[...el.attributes].some(v=>/NaN|undefined/.test(v.value))),map:document.getElementById('map-timeline').value,rgb:document.getElementById('rgb-timeline').value}});
    assert.equal(after.phase,'after');assert.equal(after.index,before.event.after);assert.equal(after.a,before.event.after_action??before.a);assert.equal(after.segment,before.segment+1);assert.equal(after.image,after.expected);assert.equal(after.map,after.rgb);assert(!after.bad);eventCount++;
   }
   await page.locator('#end').click();assert.equal(await page.evaluate(()=>window.ORACLE_DISTANCE.state().node.phase),'end');
   const reused=await page.evaluate(()=>window.ORACLE_DISTANCE.state().node.reused);if(reused)assert((await page.locator('#rgb-note').textContent()).includes('复用'));
   if(hasOriginal){await page.selectOption('#source','original');assert.equal(await page.evaluate(()=>window.ORACLE_DISTANCE.state().source),'original');
    if(expected.outcomes){await checkRgb();for(const i of [1,2]){await page.evaluate(i=>window.ORACLE_DISTANCE.setNode(i),i);await checkRgb();assert.equal(await page.evaluate(()=>window.ORACLE_DISTANCE.state().node.image==null),false);}await page.evaluate(()=>window.ORACLE_DISTANCE.setNode(3));await checkRgb();assert.equal(await page.evaluate(()=>window.ORACLE_DISTANCE.state().node.image),null);assert((await page.locator('#pair-note').textContent()).includes('原版对照'));}
   }
   else {await page.locator('#start').click();assert.equal(await page.evaluate(()=>window.ORACLE_DISTANCE.state().source),'oracle');}
   await checkRgb();
   await page.locator('#map-timeline').evaluate(e=>{e.value=3;e.dispatchEvent(new Event('input',{bubbles:true}))});assert.equal(await page.locator('#rgb-timeline').inputValue(),'3');
   await page.locator('#rgb-timeline').evaluate(e=>{e.value=5;e.dispatchEvent(new Event('input',{bubbles:true}))});assert.equal(await page.locator('#map-timeline').inputValue(),'5');
   await page.locator('#end').click();await checkRgb();
  }
  assert.equal(eventCount,expected.events);assert.equal(emptyCount,expected.tasks-expected.triggered);
  await page.evaluate(()=>window.ORACLE_DISTANCE.selectCase(0));await page.locator('#start').click();await page.locator('#play').click();await page.waitForTimeout(600);assert((await page.evaluate(()=>window.ORACLE_DISTANCE.state().nodeIndex))>0);await page.locator('#play').click();
  await page.locator('#rgb').click();assert(await page.locator('#dialog').isVisible());await page.locator('#close').click();
  for(const [f,count] of [['success',expected.success],['failure',expected.tasks-expected.success],['triggered',expected.triggered],['none',expected.tasks-expected.triggered],['special',expected.success-expected.normal_success],['all',expected.tasks]]){await page.selectOption('#filter',f);assert.equal(await page.locator('#cases .case').count(),count);}
  if(expected.outcomes){for(const [f,count] of Object.entries(expected.outcomes)){await page.selectOption('#filter',f);assert.equal(await page.locator('#cases .case').count(),count);}await page.selectOption('#filter','all');}
  const initial=await page.locator('#map').getAttribute('viewBox');await page.locator('#zoom-in').click();assert.notEqual(await page.locator('#map').getAttribute('viewBox'),initial);await page.locator('#fit').click();
  if(hasOriginal){await page.locator('input[data-layer="original"]').uncheck();assert.equal(await page.locator('#map .original-route').count(),0);await page.locator('input[data-layer="original"]').check();}
  else {assert.equal(await page.locator('input[data-layer="original"]').count(),0);assert.equal(await page.locator('#map .original-route').count(),0);}
  await page.locator('#tab-results').click();assert.equal(await page.locator('#results-table tbody tr').count(),taskCount);await page.screenshot({path:path.join(out,'results.png'),fullPage:true});
  const download=page.waitForEvent('download');await page.locator('#export').click();const dl=await download;await dl.saveAs(path.join(out,'results.csv'));
  assert.equal(fs.readFileSync(path.join(out,'results.csv'),'utf8').trim().split(/\r?\n/).length,taskCount+1);
  await page.locator('#tab-replay').click();await page.selectOption('#language','en');await page.screenshot({path:path.join(out,'english.png'),fullPage:true});await page.selectOption('#language','zh');
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1));
  assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
  fs.writeFileSync(path.join(out,'validation.json'),JSON.stringify({passed:true,summary,paired_missing_rgb_verified:!!expected.outcomes,paired_reason_translations_verified:!!expected.outcomes,events_checked:eventCount,zero_event_tasks:emptyCount,bilingual_tasks:taskCount,source_switch_tasks:hasOriginal?taskCount:0,absent_baseline_not_fabricated:!hasOriginal,double_sliders_verified:true,mobile_verified:true,csv_rows:taskCount,page_errors:errors,remote_requests:remote},null,2));
  console.log(JSON.stringify({passed:true,...summary,events_checked:eventCount}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
