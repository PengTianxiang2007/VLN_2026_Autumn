/* Check the actual standalone early-group page, without model/simulator use. */
const fs=require('fs'),path=require('path'),assert=require('assert'),{pathToFileURL}=require('url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright-core');
const file=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]||path.join(path.dirname(file),'early_visualization_validation'));
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_EXECUTABLE,headless:true,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-zygote']});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1100},deviceScaleFactor:1}),errors=[],remote=[];
  page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url())});
  await page.goto(pathToFileURL(file).href,{waitUntil:'load',timeout:120000});
  await page.waitForFunction(()=>window.oracleEarly&&!document.getElementById('loading'));
  await page.evaluate(()=>document.fonts.ready);await page.locator('#current-rgb').evaluate(i=>i.decode());
  assert.equal(await page.locator('#cases .case').count(),10);
  await page.screenshot({path:path.join(out,'01_overview.png'),fullPage:true});
  let events=0;
  for(let ci=0;ci<10;ci++){
   await page.evaluate(i=>window.oracleEarly.selectCase(i),ci);
   const info=await page.evaluate(()=>{const app=window.oracleEarly,s=app.state(),c=app.data.cases[s.caseIndex];return {count:s.run.events.length,success:s.run.metrics.success,instruction:document.getElementById('instruction').textContent,expected:c.instruction}});
   assert.equal(info.success,1);assert.equal(info.instruction,info.expected);
   for(let ei=0;ei<info.count;ei++){
    await page.locator(`#event-strip [data-event="${ei}"]`).click();
    await page.locator('#jump-before').click();
    const before=await page.evaluate(()=>{const app=window.oracleEarly,s=app.state();return {phase:s.node.phase,index:s.nodeIndex,event:s.event,segment:s.node.segment,a:s.node.a,image:document.getElementById('current-rgb').src,expected:app.data.images[s.node.image],beforeImage:document.getElementById('before-rgb').src,expectedBefore:app.data.images[s.event.before_image]}});
    assert.equal(before.phase,'before');assert.equal(before.index,before.event.before);assert.equal(before.a,before.event.step);assert.equal(before.image,before.expected);assert.equal(before.beforeImage,before.expectedBefore);
    await page.locator('#next').click();
    const after=await page.evaluate(()=>{const app=window.oracleEarly,s=app.state();return {phase:s.node.phase,index:s.nodeIndex,segment:s.node.segment,a:s.node.a,afterImage:document.getElementById('after-rgb').src,expectedAfter:app.data.images[s.event.after_image],badMap:/NaN|undefined/.test(document.getElementById('map').innerHTML),jumps:document.querySelectorAll('#map [data-jump]').length}});
    assert.equal(after.phase,'after');assert.equal(after.index,before.event.after);assert.equal(after.a,before.a);assert.equal(after.segment,before.segment+1);assert.equal(after.afterImage,after.expectedAfter);assert.equal(after.jumps,ei+1);assert(!after.badMap);
    await page.locator('#jump-after').click();assert.equal(await page.evaluate(()=>window.oracleEarly.state().node.phase),'after');events++;
   }
   await page.locator('#jump-end').click();assert.equal(await page.evaluate(()=>window.oracleEarly.state().node.phase),'end');assert((await page.locator('#rgb-note').textContent()).includes('复用'));
  }
  assert.equal(events,18);
  await page.evaluate(()=>{window.oracleEarly.selectCase(0);window.oracleEarly.setNode(0)});
  await page.locator('#play').click();await page.waitForTimeout(600);assert((await page.evaluate(()=>window.oracleEarly.state().nodeIndex))>0);
  await page.locator('#play').click();const paused=await page.evaluate(()=>window.oracleEarly.state().nodeIndex);await page.waitForTimeout(300);assert.equal(await page.evaluate(()=>window.oracleEarly.state().nodeIndex),paused);
  await page.locator('#timeline').evaluate(e=>{e.value=8;e.dispatchEvent(new Event('input',{bubbles:true}))});assert.equal(await page.evaluate(()=>window.oracleEarly.state().nodeIndex),8);
  await page.locator('h1').click();await page.keyboard.press('ArrowRight');assert.equal(await page.evaluate(()=>window.oracleEarly.state().nodeIndex),9);
  const view=await page.locator('#map').getAttribute('viewBox');await page.locator('#zoom-in').click();assert.notEqual(await page.locator('#map').getAttribute('viewBox'),view);await page.locator('#fit-route').click();await page.locator('#fit-scene').click();
  await page.locator('#current-rgb').click();assert(await page.locator('#image-dialog').isVisible());await page.locator('#close-dialog').click();
  await page.locator('#case-filter').selectOption('multi');assert.equal(await page.locator('#cases .case').count(),5);
  await page.locator('#case-filter').selectOption('near');assert.equal(await page.locator('#cases .case').count(),4);
  await page.locator('#case-filter').selectOption('contact');assert.equal(await page.locator('#cases .case').count(),1);
  await page.locator('#case-filter').selectOption('all');await page.locator('#tab-table').click();assert.equal(await page.locator('#result-table tbody tr').count(),10);
  await page.screenshot({path:path.join(out,'02_results.png'),fullPage:true});
  const downloadPromise=page.waitForEvent('download');await page.locator('#export-table-csv').click();const download=await downloadPromise;await download.saveAs(path.join(out,download.suggestedFilename()));
  assert.equal(fs.readFileSync(path.join(out,download.suggestedFilename()),'utf8').trim().split('\r\n').length,11);
  await page.locator('#tab-replay').click();await page.evaluate(()=>{window.oracleEarly.selectCase(5);window.oracleEarly.selectEvent(4,'after')});
  await page.screenshot({path:path.join(out,'03_five_corrections.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(200);assert(await page.locator('#current-rgb').isVisible());assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
  await page.screenshot({path:path.join(out,'04_mobile.png'),fullPage:true});
  assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
  const result={cases:10,successful:10,correction_boundaries:events,playback_pause_seek:true,exact_before_after:true,zoom:true,filters:true,csv_rows:10,image_dialog:true,mobile_no_overflow:true,external_requests:0,page_errors:0};
  fs.writeFileSync(path.join(out,'browser_verification.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
