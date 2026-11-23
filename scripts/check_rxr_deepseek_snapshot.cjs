'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert'),{pathToFileURL}=require('url');
const runtime='/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium}=require(path.join(runtime,'playwright-core')),portable=require(path.join(runtime,'@sparticuz/chromium'));
(async()=>{
 const folder=path.resolve(process.argv[2]),dest=path.join(folder,'validation');fs.mkdirSync(dest,{recursive:true});
 const data=JSON.parse(fs.readFileSync(path.join(folder,'snapshot_public.json'),'utf8'));
 assert.equal(data.cases.length,30);assert.equal(data.summary.retained,295);assert.equal(data.summary.model_calls,656);
 assert.equal(data.deviation_summary.calls,137);assert.equal(data.deviation_summary.alarm_cases,23);
 assert(data.model_label.includes('DeepSeek'));
 const rawText=r=>{const content=r.response.choices[0].message.content;return typeof content==='string'?content:content.filter(x=>x.type==='text').map(x=>x.text).join('')};
 let finalNodes=0,terminalNodes=0,calls=0,invalid=0;
 for(const c of data.cases){
  const d=c.dedup;assert.deepEqual(d.nodes.filter(n=>!n.terminal_node).map(n=>n.source_id),d.decisions.at(-1).active_ids_after);
  finalNodes+=d.nodes.filter(n=>!n.terminal_node).length;terminalNodes+=d.nodes.filter(n=>n.terminal_node).length;
  for(const r of d.decisions){
   if(!r.needs_model)continue;calls++;
   assert.equal(r.request.settings.model,data.model_name);
   const raw=JSON.parse(fs.readFileSync(path.join(folder,r.raw_response_file),'utf8'));assert.equal(rawText(raw),r.raw_content);
   const a=r.answer;for(const text of [r.reason,...a.matched_branches.map(x=>x.description),...a.a_only,...a.b_only])assert(data.translations[text]);
  }
  for(const r of c.deviation.result.reviews){
   assert.equal(r.request.settings.model,data.model_name);
   const raw=JSON.parse(fs.readFileSync(path.join(folder,r.raw_response_file),'utf8'));assert.equal(rawText(raw),r.raw_content);
   if(r.status!=='ok')invalid++;
  }
  assert.deepEqual(c.deviation.intervals,c.deviation.result.reviews.filter(r=>r.status==='ok'&&r.answer.verdict==='deviated').map(r=>({previous_id:r.previous_id,current_id:r.node_id,from_frame:r.from_frame,to_frame:r.to_frame})));
 }
 assert.equal(finalNodes,295);assert.equal(terminalNodes,30);assert.equal(calls,656);assert.equal(invalid,7);
 const browser=await chromium.launch({executablePath:await portable.executablePath(),headless:true,args:['--no-sandbox','--no-zygote','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
 try{
  const page=await browser.newPage({viewport:{width:1500,height:1080}}),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(pathToFileURL(path.join(folder,'index.html')).href,{waitUntil:'load',timeout:45000});
  await page.waitForFunction(()=>window.RxRSnapshot&&loadedRGB&&floor.complete);await page.evaluate(()=>document.fonts.ready);
  assert.equal(await page.locator('#zh').getAttribute('aria-pressed'),'true');assert.equal(await page.isChecked('#deviationLayer'),false);
  const countRed=()=>page.evaluate(()=>{const p=document.getElementById('map').getContext('2d').getImageData(0,0,800,600).data;let n=0;for(let i=0;i<p.length;i+=4)if(Math.abs(p[i]-224)<8&&Math.abs(p[i+1]-32)<8&&Math.abs(p[i+2]-50)<8)n++;return n});
  // Check actual pose edges for every case without repeating all language interactions.
  for(const c of data.cases){
   await page.selectOption('#task',c.id);
   assert.equal(await page.locator('#nodeButtons button').count(),c.dedup.nodes.length);
   assert.equal(await page.locator('#roundPicker option').count(),c.dedup.decisions.length);
   assert.equal(await page.locator('#devPicker option').count(),c.deviation.result.reviews.length);
   await page.check('#deviationLayer');await page.uncheck('#effectiveLayer');
   const edges=await page.evaluate(()=>{const result=[];let start;const ctx={save(){},restore(){},setLineDash(){},beginPath(){start=null},moveTo(x,z){start=[x,z]},lineTo(x,z){result.push([start,[x,z]])},stroke(){},arc(){},strokeText(){},fillText(){}};RxRSnapshot.drawNodes({ctx,px:x=>x,pz:z=>z});return result});
   const expected=[];for(const s of c.deviation.intervals)for(let f=s.from_frame+1;f<=s.to_frame;f++)expected.push([[c.pose[f-1][0],c.pose[f-1][2]],[c.pose[f][0],c.pose[f][2]]]);
   assert.deepEqual(edges,expected);await page.check('#effectiveLayer');await page.uncheck('#deviationLayer');
  }
  const samples=[0,5,11,19,23,29].map(i=>data.cases[i]);
  for(const c of samples){
   await page.selectOption('#task',c.id);await page.waitForFunction(()=>loadedRGB&&floor.complete);
   const selected=new Set([0,c.deviation.result.reviews.length-1,...c.deviation.result.reviews.map((r,i)=>r.status!=='ok'?i:-1).filter(i=>i>=0)]);
   for(const i of selected){
    const r=c.deviation.result.reviews[i];await page.selectOption('#devPicker',String(i));
    for(const language of ['en','zh']){
     await page.click('#'+language);assert.equal((await page.evaluate(()=>RXR_REPLAY.state())).step,r.to_frame);
     if(r.display_answer)assert((await page.locator('#devAnswer').textContent()).includes(r.display_answer.reason[language]));
     else assert((await page.locator('#devAnswer').textContent()).includes(language==='zh'?'未形成可解析':'no parseable'));
     if(r.raw_content)assert.equal(await page.locator('#devRawAnswer').textContent(),r.raw_content);
     assert.equal(await page.locator('#devResponseLink').getAttribute('href'),r.raw_response_file);
    }
    if(r.status!=='ok'){assert(await page.locator('#devError').isVisible());assert(!(await page.locator('#devError').textContent()).includes('ValueError'));}
   }
   for(const relation of ['same','different','uncertain']){
    const i=c.dedup.decisions.findIndex(r=>r.relation===relation);if(i<0)continue;
    const r=c.dedup.decisions[i];await page.selectOption('#roundPicker',String(i));
    await page.click('#en');assert.equal(await page.locator('#reviewReason').textContent(),data.translations[r.reason]);
    await page.click('#zh');assert.equal(await page.locator('#reviewReason').textContent(),r.reason);
    assert.equal(await page.locator('#rawAnswer').textContent(),r.raw_content);
   }
  }
  const c=data.cases[0];await page.selectOption('#task',c.id);await page.waitForFunction(()=>loadedRGB&&floor.complete);
  const before=await countRed();await page.check('#deviationLayer');const after=await countRed();assert(after>before+20);
  await page.locator('#map').screenshot({path:path.join(dest,'red_deviation.png')});
  await page.uncheck('#deviationLayer');assert.equal(await countRed(),before);await page.check('#deviationLayer');
  const alarm=c.deviation.intervals[0];await page.click('#devJumpA');assert.equal((await page.evaluate(()=>RXR_REPLAY.state())).step,alarm.from_frame);
  await page.click('#devJumpB');assert.equal((await page.evaluate(()=>RXR_REPLAY.state())).step,alarm.to_frame);
  await page.locator('#deviationSection').screenshot({path:path.join(dest,'deviation_zh.png')});
  await page.click('#en');await page.locator('#deviationSection').screenshot({path:path.join(dest,'deviation_en.png')});
  await page.locator('#dedupSection').screenshot({path:path.join(dest,'dedup_en.png')});await page.click('#zh');
  await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(dest,'overview_zh.png')});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(dest,'mobile.png')});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  assert.deepEqual(errors,[]);
  const report={passed:true,cases:30,effective_nodes:295,terminal_nodes:30,dedup_calls:656,deviation_rounds:137,alarms:23,invalid_answers:7,raw_answers_preserved:true,actual_pose_edges_all_cases:true,bilingual_samples:samples.map(c=>c.id),red_toggle_pixels:{before,after},mobile:true,page_errors:errors};
  fs.writeFileSync(path.join(dest,'validation.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
