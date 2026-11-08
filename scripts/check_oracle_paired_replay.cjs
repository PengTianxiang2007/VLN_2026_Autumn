/* Validate the actual offline page, all correction boundaries and key controls. */
const fs=require('fs'),path=require('path'),assert=require('assert');
const {pathToFileURL}=require('url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright-core');
const file=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]||path.join(path.dirname(file),'paired_visualization_validation'));
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_EXECUTABLE,headless:true,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-zygote']});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1100},deviceScaleFactor:1});const errors=[],remote=[];
  page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url())});
  await page.goto(pathToFileURL(file).href,{waitUntil:'load',timeout:120000});
  await page.waitForFunction(()=>window.oraclePaired&&!document.getElementById('loading'));
  await page.evaluate(()=>document.fonts.ready);
  await page.locator('#trunk-rgb').evaluate(i=>i.decode());
  assert.equal(await page.locator('#cases .case').count(),10);
  assert.equal(await page.locator('#branches .branch').count(),3);
  await page.screenshot({path:path.join(out,'01_overview.png'),fullPage:true});
  let results=0,events=0,stages=0,untriggered=0;
  for(let ci=0;ci<10;ci++){
   await page.evaluate(i=>window.oraclePaired.selectCase(i),ci);
   const info=await page.evaluate(()=>{
    const app=window.oraclePaired,s=app.state(),cc=app.data.cases[s.caseIndex];return {id:cc.id,instruction:document.getElementById('instruction').textContent,expected:cc.instruction,
     arms:['short','medium','long'].map(a=>({arm:a,triggered:cc.runs[a].triggered,events:cc.runs[a].events,stage:cc.stages[a]}))};
   });assert.equal(info.instruction,info.expected);
   for(const r of info.arms){
    if(!r.triggered)untriggered++;
    if(r.stage){await page.evaluate(a=>window.oraclePaired.jumpStage(a),r.arm);assert.equal(await page.evaluate(()=>window.oraclePaired.state().tick),r.stage.ticks);stages++}
    for(let ei=0;ei<r.events.length;ei++){
     const event=r.events[ei];
     for(const phase of ['before','after']){
      await page.locator(`[data-event="${r.arm}:${ei}:${phase}"]`).click();
      const state=await page.evaluate(a=>{const app=window.oraclePaired,s=app.state(),n=s.arms[a].node;return {phase:n.phase,a:n.a,segment:n.segment,image:document.getElementById('rgb-'+a).src,expected:app.data.images[n.image],map:document.getElementById('map-'+a).innerHTML}},r.arm);
      assert.equal(state.phase,phase);assert.equal(state.a,event.a);assert.equal(state.image,state.expected);assert(!/NaN|undefined/.test(state.map));
      assert.equal(state.segment,phase==='before'?event.number-1:event.number);
      if(phase==='after')assert.equal(await page.locator(`#map-${r.arm} [data-jump]`).count(),event.number);
     }events++;
    }
    results++;
   }
   await page.evaluate(()=>window.oraclePaired.setTime(1e9));
   const final=await page.evaluate(()=>Object.entries(window.oraclePaired.state().arms).filter(([a])=>a!=='trunk').map(([a,v])=>({a,terminal:v.node.terminal,index:v.index,length:v.run.nodes.length})));
   assert(final.every(r=>r.terminal&&r.index===r.length-1));
  }
  assert.equal(results,30);assert.equal(events,33);assert.equal(stages,22);assert.equal(untriggered,8);
  await page.evaluate(()=>{window.oraclePaired.selectCase(0);window.oraclePaired.setTime(1)});
  await page.locator('#play').click();await page.waitForTimeout(550);assert((await page.evaluate(()=>window.oraclePaired.state().tick))>1);
  await page.locator('#play').click();const paused=await page.evaluate(()=>window.oraclePaired.state().tick);await page.waitForTimeout(350);assert.equal(await page.evaluate(()=>window.oraclePaired.state().tick),paused);
  await page.locator('#timeline').evaluate(e=>{e.value=701;e.dispatchEvent(new Event('input',{bubbles:true}))});assert.equal(await page.evaluate(()=>window.oraclePaired.state().tick),701);
  await page.locator('h1').click();await page.keyboard.press('ArrowRight');assert.equal(await page.evaluate(()=>window.oraclePaired.state().tick),751);
  const oldView=await page.locator('#map-short').getAttribute('viewBox');await page.locator('[data-zoom="short:1.3"]').click();assert.notEqual(await page.locator('#map-short').getAttribute('viewBox'),oldView);
  await page.locator('#rgb-short').click();assert(await page.locator('#image-dialog').isVisible());await page.locator('#close-dialog').click();
  await page.locator('#case-filter').selectOption('paired');assert.equal(await page.locator('#cases .case').count(),7);
  await page.locator('#tab-table').click();assert.equal(await page.locator('#result-table tbody tr').count(),7);
  await page.screenshot({path:path.join(out,'02_paired_results.png'),fullPage:true});
  await page.locator('#case-filter').selectOption('all');assert.equal(await page.locator('#result-table tbody tr').count(),10);
  const downloadPromise=page.waitForEvent('download');await page.locator('#export-table-csv').click();const download=await downloadPromise;await download.saveAs(path.join(out,download.suggestedFilename()));
  const csv=fs.readFileSync(path.join(out,download.suggestedFilename()),'utf8');assert.equal(csv.trim().split('\r\n').length,31);
  await page.locator('#tab-replay').click();await page.evaluate(()=>{window.oraclePaired.selectCase(5);window.oraclePaired.setTime(1e9)});
  await page.screenshot({path:path.join(out,'03_multiple_corrections.png'),fullPage:true});
  await page.evaluate(()=>{window.oraclePaired.selectCase(9);window.oraclePaired.setTime(1e9)});
  assert((await page.locator('#branches').textContent()).includes('没有实施纠正'));
  await page.screenshot({path:path.join(out,'04_untriggered.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(150);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
  await page.screenshot({path:path.join(out,'05_mobile.png'),fullPage:true});
  assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
  const check={cases:10,group_results:results,correction_boundaries:events,semantic_stages:stages,untriggered_results:untriggered,playback_pause_seek:true,csv_rows:30,zoom:true,image_dialog:true,paired_filter:true,mobile_no_overflow:true,external_requests:0,page_errors:0};
  fs.writeFileSync(path.join(out,'browser_verification.json'),JSON.stringify(check,null,2)+'\n');console.log(JSON.stringify(check));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
