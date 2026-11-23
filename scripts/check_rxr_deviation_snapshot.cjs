'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert'),{pathToFileURL}=require('url');
const runtime='/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium}=require(path.join(runtime,'playwright-core')),portable=require(path.join(runtime,'@sparticuz/chromium'));
(async()=>{
 const folder=path.resolve(process.argv[2]),dest=path.join(folder,'validation');fs.mkdirSync(dest,{recursive:true});
 const data=JSON.parse(fs.readFileSync(path.join(folder,'snapshot_public.json'),'utf8'));
 assert.equal(data.completed_ids.length,30);
 assert.equal(data.cases.reduce((n,c)=>n+c.dedup.nodes.filter(n=>!n.terminal_node).length,0),517);
 const completed=data.cases.filter(c=>c.deviation),alarms=completed.filter(c=>c.deviation.intervals.length);
 let rounds=0;
 for(const c of completed){
  const d=c.deviation;rounds+=d.result.reviews.length;
  for(const r of d.result.reviews){
   assert.equal(r.raw_content,r.response.response.choices[0].message.content);
   assert.deepEqual(r.images.map(im=>im.frame),r.request.images.map(im=>im.frame));
  }
  assert.deepEqual(d.intervals,d.result.reviews.filter(r=>r.status==='ok'&&r.answer.verdict==='deviated').map(r=>({previous_id:r.previous_id,current_id:r.node_id,from_frame:r.from_frame,to_frame:r.to_frame})));
  for(const s of d.intervals){
   assert.equal(c.dedup.nodes.find(n=>n.id===s.previous_id).index,s.from_frame);
   assert.equal(c.dedup.nodes.find(n=>n.id===s.current_id).index,s.to_frame);
  }
 }
 assert.equal(rounds,data.deviation_summary.calls);
 const browser=await chromium.launch({executablePath:await portable.executablePath(),headless:true,args:['--no-sandbox','--no-zygote','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
 try{
  const page=await browser.newPage({viewport:{width:1500,height:1080}}),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(pathToFileURL(path.join(folder,'index.html')).href,{waitUntil:'load',timeout:45000});
  await page.waitForFunction(()=>window.RxRSnapshot&&loadedRGB&&floor.complete);await page.evaluate(()=>document.fonts.ready);
  assert.equal(await page.locator('#zh').getAttribute('aria-pressed'),'true');assert.equal(await page.isChecked('#deviationLayer'),false);
  const pixelCount=()=>page.evaluate(()=>{const ctx=document.getElementById('map').getContext('2d'),p=ctx.getImageData(0,0,800,600).data;let n=0;for(let i=0;i<p.length;i+=4)if(Math.abs(p[i]-224)<8&&Math.abs(p[i+1]-32)<8&&Math.abs(p[i+2]-50)<8)n++;return n});
  const redChecks=[];
  for(const c of completed){
   await page.selectOption('#task',c.id);await page.waitForFunction(()=>loadedRGB&&floor.complete);
   assert.equal(await page.locator('#devPicker option').count(),c.deviation.result.reviews.length);
   assert.equal(await page.locator('#nodeButtons button').count(),c.dedup.nodes.length);
   for(const [i,r] of c.deviation.result.reviews.entries()){
    await page.selectOption('#devPicker',String(i));
    for(const language of ['en','zh']){
     await page.click('#'+language);
     assert.equal((await page.evaluate(()=>RXR_REPLAY.state())).step,r.to_frame);
     const body=await page.locator('#devAnswer').textContent();assert(body.includes(r.display_answer.reason[language]));
     assert.equal(await page.locator('#devRawAnswer').textContent(),r.raw_content);
     assert.equal(await page.locator('#deviationPrompt').textContent(),data.prompts['deviation_'+language]);
    }
    if(r.status!=='ok')assert(await page.locator('#devError').isVisible());
   }
   await page.uncheck('#deviationLayer');const before=await pixelCount();
   await page.check('#deviationLayer');const after=await pixelCount();
   if(c.deviation.intervals.length){
    assert(after>before+40,`Expected red trajectory for ${c.id}: ${before}/${after}`);
    // Record path drawing calls: every actual A→B pose edge must be drawn, even for skipped review IDs.
    await page.uncheck('#effectiveLayer');
    const drawn=await page.evaluate(()=>{const edges=[];let start=null;const ctx={save(){},restore(){},setLineDash(){},beginPath(){start=null},moveTo(x,z){start=[x,z]},lineTo(x,z){edges.push([start,[x,z]])},stroke(){},arc(){},strokeText(){},fillText(){}};RxRSnapshot.drawNodes({ctx,px:x=>x,pz:z=>z});return edges});
    const expected=[];for(const s of c.deviation.intervals)for(let f=s.from_frame+1;f<=s.to_frame;f++)expected.push([[c.pose[f-1][0],c.pose[f-1][2]],[c.pose[f][0],c.pose[f][2]]]);
    assert.deepEqual(drawn,expected);await page.check('#effectiveLayer');
    const index=c.deviation.result.reviews.findIndex(r=>r.status==='ok'&&r.answer.verdict==='deviated');await page.selectOption('#devPicker',String(index));
    await page.click('#devJumpA');assert.equal((await page.evaluate(()=>RXR_REPLAY.state())).step,c.deviation.intervals[0].from_frame);
    await page.click('#devJumpB');assert.equal((await page.evaluate(()=>RXR_REPLAY.state())).step,c.deviation.intervals[0].to_frame);
    await page.locator('#map').screenshot({path:path.join(dest,'red_'+c.id+'.png')});
   }else assert.equal(after,before);
   await page.uncheck('#deviationLayer');assert.equal(await pixelCount(),before);redChecks.push({episode:c.id,before,after});
  }
  const pending=data.cases.find(c=>!c.deviation);await page.selectOption('#task',pending.id);
  assert(await page.locator('#deviationBody').isHidden());assert((await page.locator('#deviationStatus').textContent()).includes('待完成'));
  assert.equal(await page.locator('#nodeButtons button').count(),pending.dedup.nodes.length);
  await page.locator('#nodeButtons button').first().click();assert.equal((await page.evaluate(()=>RXR_REPLAY.state())).step,pending.dedup.nodes[0].index);
  await page.selectOption('#task',alarms[0].id);await page.check('#deviationLayer');
  await page.locator('#deviationSection').screenshot({path:path.join(dest,'deviation_zh.png')});
  await page.click('#en');await page.locator('#deviationSection').screenshot({path:path.join(dest,'deviation_en.png')});
  await page.click('#zh');await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(dest,'overview_zh.png')});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(dest,'mobile.png')});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  assert.deepEqual(errors,[]);
  const report={passed:true,completed_cases:completed.length,review_rounds:rounds,alarm_cases:alarms.length,final_nodes:517,terminal_nodes:30,redChecks,actual_pose_edges:true,accepted_alarms_only:true,bilingual_alignment:true,raw_answers_preserved:true,pending_distinguished:true,mobile:true,page_errors:errors};
  fs.writeFileSync(path.join(dest,'validation.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
