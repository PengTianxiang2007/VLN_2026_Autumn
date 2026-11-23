'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert'),{pathToFileURL}=require('url');
const root=process.env.ORACLE_BROWSER_ROOT||'/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium}=require(path.join(root,'playwright-core')),portable=require(path.join(root,'@sparticuz/chromium'));
(async()=>{
 const file=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({executablePath:await portable.executablePath(),headless:true,args:['--no-sandbox','--no-zygote','--disable-gpu','--disable-software-rasterizer','--disable-dev-shm-usage','--allow-file-access-from-files']});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1100},acceptDownloads:true});const errors=[],remote=[];
  page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url())});
  await page.addInitScript(()=>{
   window.__canvasText={};window.__strokes={};const p=CanvasRenderingContext2D.prototype;
   for(const name of ['clearRect','fillText','beginPath','moveTo','lineTo','stroke']){const original=p[name];p[name]=function(...args){const id=this.canvas.id;if(name==='clearRect'){window.__canvasText[id]=[];window.__strokes[id]=[]}if(name==='fillText')(window.__canvasText[id]??=[]).push(args[0]);if(name==='beginPath')this.__trace=[];if(name==='moveTo'||name==='lineTo')(this.__trace??=[]).push([name,...args]);if(name==='stroke')(window.__strokes[id]??=[]).push({color:this.strokeStyle,points:(this.__trace||[]).slice()});return original.apply(this,args)}}
  });
  await page.goto(pathToFileURL(file).href,{waitUntil:'load',timeout:60000});await page.waitForFunction(()=>window.SERIAL_JEV);await page.evaluate(()=>document.fonts.ready);await page.locator('#rgb').evaluate(im=>im.decode());
  const actual=await page.evaluate(()=>({summary:SERIAL_JEV.data.summary,nodes:SERIAL_JEV.data.nodes,frames:SERIAL_JEV.data.frames,requests:SERIAL_JEV.data.requests,prompts:SERIAL_JEV.data.prompts}));
  assert.equal(await page.locator('#showRawJev').isChecked(),true);assert.equal(await page.locator('#showFiltered').isChecked(),true);assert.equal(await page.locator('#sample_v001').isChecked(),false);assert.equal(await page.locator('#nodeDeduplication').isChecked(),false);assert(await page.locator('#nodeEliminationTop').isHidden());
  const snapshot=()=>page.evaluate(()=>({map:(window.__canvasText.jevMap||[]).filter(t=>/^S\d+$/.test(t)),wave:(window.__canvasText.scorePlot||[]).filter(t=>/^S\d+$/.test(t)),raw:(window.__strokes.scorePlot||[]).filter(s=>s.color==='#b33a3a').at(-1)?.points,filtered:(window.__strokes.scorePlot||[]).filter(s=>s.color==='#2563eb').at(-1)?.points}));
  assert.equal((await snapshot()).wave.length,0);
  await page.locator('#showCheckpoints').check();await page.waitForFunction(()=>window.__canvasText.jevMap?.filter(t=>/^S\d+$/.test(t)).length===7);
  assert(await page.locator('#sample_v001').isChecked());let s=await snapshot();assert.deepEqual(s.map,['S01','S02','S03','S04','S05','S06','S07']);assert.deepEqual(s.wave,s.map);assert.equal(s.raw.length,40);const raw0=s.raw,filtered0=s.filtered;
  const sampled=await page.evaluate(()=>JEV_LAB.displayState().versions[0].allNodes);assert.equal(sampled.length,actual.nodes.length);
  for(let i=0;i<sampled.length;i++){for(const k of ['id','index','emittedAt','kind','delay'])assert.equal(sampled[i][k],actual.nodes[i][k]);assert(Math.abs(sampled[i].value-actual.nodes[i].value)<1e-12)}
  await page.evaluate(()=>JEV_LAB.seek(39));await page.locator('#rgb').evaluate(im=>im.decode());s=await snapshot();assert.deepEqual(s.raw,raw0);assert.deepEqual(s.filtered,filtered0);assert.equal(s.wave.length,7);
  await page.evaluate(()=>JEV_LAB.seek(0));await page.locator('#jevMap').screenshot({path:path.join(out,'map_all7.png')});await page.locator('#scorePlot').screenshot({path:path.join(out,'wave_all7.png')});
  await page.locator('#nodeDeduplicationTop').click();await page.waitForFunction(()=>window.__canvasText.jevMap?.filter(t=>/^S\d+$/.test(t)).length===2);s=await snapshot();assert.deepEqual(s.map,['S05','S07']);assert.deepEqual(s.wave,s.map);assert(await page.locator('#nodeDeduplication').isChecked());
  await page.locator('#jevMap').screenshot({path:path.join(out,'map_dedup2.png')});await page.locator('#scorePlot').screenshot({path:path.join(out,'wave_dedup2.png')});
  await page.locator('#sample_v001').uncheck();s=await snapshot();assert.deepEqual(s.wave,[]);assert.deepEqual(s.map,[]);assert(!(await page.locator('#showCheckpoints').isChecked()));await page.locator('#showCheckpoints').check();assert.equal((await snapshot()).wave.length,2);
  await page.locator('#nodeDeduplication').uncheck();assert.equal((await snapshot()).wave.length,7);assert.equal(await page.locator('#nodeDeduplicationTop').getAttribute('aria-pressed'),'false');
  await page.locator('#showRawJev').uncheck();assert.equal((await snapshot()).raw,undefined);assert.equal((await snapshot()).wave.length,7);await page.locator('#showRawJev').check();await page.locator('#showFiltered').uncheck();assert.equal((await snapshot()).filtered,undefined);assert.equal((await snapshot()).wave.length,7);await page.locator('#showFiltered').check();
  await page.locator('#dedupAudit').evaluate(e=>e.open=true);
  const decisions=await page.evaluate(()=>JEV_LAB.dedupData.cases[0].decisions);
  for(let i=0;i<decisions.length;i++){
   await page.selectOption('#dedupDecision','0:'+decisions[i].current_id);
   for(const language of ['zh','en']){await page.selectOption('#language',language);const a=decisions[i].display_answer;assert.equal(await page.locator('#dedupReason').textContent(),a.reason[language]);const body=await page.locator('#dedupBranches').textContent();for(const b of a.matched_branches||[])assert(body.includes(b.description[language]));for(const q of [...a.a_only||[],...a.b_only||[]])assert(body.includes(q[language]));assert.equal(await page.locator('#dedupPrompt').textContent(),actual.prompts.dedup[language]);await page.locator('#dedupEvidence img').evaluateAll(imgs=>Promise.all(imgs.map(im=>im.decode())))}
  }
  const reviews=actual.requests.filter(r=>r.stage==='deviation');
  for(let i=0;i<reviews.length;i++){
   await page.selectOption('#serialReviewPick',String(i));
   for(const language of ['zh','en']){await page.selectOption('#language',language);const body=await page.locator('#serialReviewAnswer').textContent(),a=reviews[i].answer;for(const k of ['segment_summary','reason','semantic_progress'])if(a[k])assert(body.includes(a[k][language]));for(const q of a.uncertainties)assert(body.includes(q[language]));for(const q of a.visual_evidence)assert(body.includes(q.description[language]));assert.equal(await page.locator('#serialReviewPrompt').textContent(),actual.prompts.deviation[language]);await page.locator('#serialReviewImages img').evaluateAll(imgs=>Promise.all(imgs.map(im=>im.decode())))}
  }
  await page.selectOption('#language','zh');
  for(let i=0;i<40;i++){await page.evaluate(i=>JEV_LAB.seek(i),i);await page.locator('#rgb').evaluate(im=>im.decode());assert.equal(await page.locator('#frame').inputValue(),String(i));assert.equal(await page.locator('#imageFrame').inputValue(),String(i));assert.equal(await page.locator('#jevValue').textContent(),(actual.frames[i].probability*100).toFixed(1)+'%')}
  await page.locator('#frame').evaluate(e=>{e.value=7;e.dispatchEvent(new Event('input'))});assert.equal(await page.locator('#imageFrame').inputValue(),'7');await page.locator('#imageFrame').evaluate(e=>{e.value=14;e.dispatchEvent(new Event('input'))});assert.equal(await page.locator('#frame').inputValue(),'14');
  await page.selectOption('#serialReviewPick','6');await page.locator('#serialReviewJump').click();assert.equal(await page.locator('#frame').inputValue(),'35');
  await page.locator('#nodeDeduplication').check();await page.locator('#dedupAudit').evaluate(e=>e.open=false);await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(out,'overview_zh.png')});
  await page.selectOption('#language','en');await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(out,'overview_en.png')});await page.selectOption('#language','zh');
  await page.locator('#note').fill('模板回放验证');let pending=page.waitForEvent('download');await page.locator('#export').click();let dl=await pending;await dl.saveAs(path.join(out,'notes.json'));assert(JSON.parse(fs.readFileSync(path.join(out,'notes.json'),'utf8')).notes.some(n=>n.note==='模板回放验证'));await page.locator('#note').fill('');
  pending=page.waitForEvent('download');await page.locator('#serialExport').click();dl=await pending;await dl.saveAs(path.join(out,'evidence.json'));assert.equal(JSON.parse(fs.readFileSync(path.join(out,'evidence.json'),'utf8')).requests.length,53);
  await page.setViewportSize({width:390,height:844});await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(out,'mobile.png')});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);const result={passed:true,reused_original_template:true,sampler_matches_live_nodes:7,full_waveform_invariant_under_playback:true,map_and_waveform_switch_counts:[0,7,2,0,2,7],raw_and_filtered_independent:true,dedup_records_bilingual:7,deviation_reviews_bilingual:7,frames_checked:40,dual_sliders:true,exported_requests:53,mobile_verified:true,page_errors:errors,remote_requests:remote};fs.writeFileSync(path.join(out,'validation.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
