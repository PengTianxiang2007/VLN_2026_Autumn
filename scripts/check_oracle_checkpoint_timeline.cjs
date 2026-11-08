/* Artifact regression check: actual error frame must be immediately followed by saved-pose restore. */
const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto');
const {pathToFileURL}=require('url');
const cfg=JSON.parse(fs.readFileSync('/tmp/vln-oracle-ui-browser-direct-20261104/browser_env.json'));
const {chromium}=require(cfg.PLAYWRIGHT_MODULE);
const root=process.cwd(), file=path.resolve(process.argv[2]), destination=path.dirname(file);
const campaign=path.resolve(destination,'../..');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
(async()=>{
 const browser=await chromium.launch({executablePath:cfg.CHROMIUM_EXECUTABLE,headless:true,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']});
 const result={cases:0,valid_restore_timelines:0,checked_images:0,page_errors:[],network_requests:[],boundaries:[]};
 try {
  const page=await browser.newPage({viewport:{width:1650,height:1100}});
  page.on('pageerror',e=>result.page_errors.push(String(e)));
  page.on('request',r=>{if(/^https?:/.test(r.url()))result.network_requests.push(r.url());});
  await page.goto(pathToFileURL(file).href);await page.evaluate(()=>document.fonts.ready);
  const cases=await page.evaluate(()=>B.cases.map(c=>({id:c.episode_id,paired:c.paired})));
  assert.equal(cases.length,10);
  for(const [ci,c] of cases.entries()){
   result.cases++;
   const arms=c.paired?['trunk','streamvln','oracle_actions']:['trunk'];
   for(const arm of arms){
    await page.evaluate(([i,a])=>ORACLE_REVIEW.choose(i,a),[ci,arm]);
    const t=await page.evaluate(()=>({t:B.cases[ORACLE_REVIEW.state().ci].timelines[ORACLE_REVIEW.state().arm],state:ORACLE_REVIEW.state()}));
    if(arm!=='trunk'){
     const d=path.join(campaign,'oracle_records',c.id),proof=JSON.parse(fs.readFileSync(path.join(d,arm,'restore_proof.json')));
     const original=fs.readFileSync(path.join(d,'trunk','observations.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
     const branch=fs.readFileSync(path.join(d,arm,'observations.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
     const ri=t.t.restore_index, error=t.t.events.find(e=>e.kind==='error');
     assert.equal(error.index+1,ri);assert.equal(ri,original.length);
     // The entire first-error trajectory is present, not just the checkpoint prefix.
     for(let i=0;i<original.length;i++){
      assert.deepEqual(t.t.frames[i].position,original[i].position);
      assert.equal(t.t.frames[i].image_id,hash(original[i].frame));
     }
     const restored=t.t.frames[ri];assert.deepEqual(restored.position,proof.actual_position);
     assert.equal(restored.physics_ticks,proof.physics_ticks_after);
     assert.equal(restored.image_id,hash(branch[restored.source_index].frame));
     assert.equal(t.t.frames.length,original.length+branch.length-restored.source_index);
     assert(t.t.frames[ri-1].action_index>restored.action_index);
     await page.evaluate(()=>ORACLE_REVIEW.jumpEvent('error'));
     assert.match(await page.locator('#phaseBanner').textContent(),/首次确认走错/);
     const before=await page.locator('#rgb').getAttribute('src');
     await page.locator('#next').click();
     assert.match(await page.locator('#phaseBanner').textContent(),/复位发生/);
     assert.equal((await page.evaluate(()=>ORACLE_REVIEW.state())).idx,ri);
     assert.notEqual(await page.locator('#rgb').getAttribute('src'),before);
     assert.equal(await page.locator('#frame').inputValue(),await page.locator('#imageFrame').inputValue());
     await page.waitForFunction(()=>document.getElementById('rgb').naturalWidth>0);
     result.checked_images++;
     result.boundaries.push({episode:c.id,arm,first_error_action:t.t.frames[ri-1].action_index,restored_action:restored.action_index,restore_replay_index:ri});
     result.valid_restore_timelines++;
    }else if(!c.paired){
     assert.equal(t.t.restore_index,null);
     assert.equal(await page.locator('[data-arm="streamvln"]').isDisabled(),true);
     assert.equal(await page.locator('#restoreEvidence').isVisible(),false);
    }
    for(const slider of ['frame','imageFrame']){
     await page.locator('#'+slider).evaluate(el=>{el.value=el.max;el.dispatchEvent(new Event('input',{bubbles:true}));});
     assert.equal(await page.locator('#frame').inputValue(),await page.locator('#imageFrame').inputValue());
    }
    await page.waitForFunction(()=>document.getElementById('rgb').complete&&document.getElementById('rgb').naturalWidth>0);
    result.checked_images++;
   }
  }
  assert.equal(result.valid_restore_timelines,14);
  await page.evaluate(()=>{ORACLE_REVIEW.choose(0,'streamvln');ORACLE_REVIEW.jumpEvent('error');});
  await page.screenshot({path:path.join(destination,'01_first_error.png'),fullPage:true});
  await page.locator('#speed').selectOption('200');await page.locator('#play').click();
  await page.waitForFunction(()=>ORACLE_REVIEW.state().frame.phase==='restore',{},{timeout:5000});
  await page.evaluate(()=>ORACLE_REVIEW.stop());
  await page.screenshot({path:path.join(destination,'02_restore.png'),fullPage:true});
  // Switching arms at the duplicate checkpoint action must stay on the restore event.
  await page.locator('[data-arm="oracle_actions"]').click();
  assert.equal((await page.evaluate(()=>ORACLE_REVIEW.state())).frame.phase,'restore');
  await page.evaluate(()=>ORACLE_REVIEW.jumpEvent('choice'));
  assert.match(await page.locator('#phaseBanner').textContent(),/交回 StreamVLN/);
  await page.screenshot({path:path.join(destination,'04_oracle_handoff.png'),fullPage:true});
  await page.evaluate(()=>{ORACLE_REVIEW.choose(0,'streamvln');ORACLE_REVIEW.jumpEvent('choice');});
  assert.match(await page.locator('#phaseBanner').textContent(),/再次选错/);
  await page.screenshot({path:path.join(destination,'03_stream_wrong_again.png'),fullPage:true});
  // Review notes must distinguish checkpoint-before-error from restored checkpoint.
  await page.evaluate(()=>ORACLE_REVIEW.jumpEvent('checkpoint'));await page.locator('#note').fill('test-before');
  await page.evaluate(()=>ORACLE_REVIEW.jumpEvent('restore'));await page.locator('#note').fill('test-after');
  await page.evaluate(()=>ORACLE_REVIEW.jumpEvent('checkpoint'));assert.equal(await page.locator('#note').inputValue(),'test-before');
  await page.evaluate(()=>ORACLE_REVIEW.jumpEvent('restore'));assert.equal(await page.locator('#note').inputValue(),'test-after');
  assert.deepEqual(result.page_errors,[]);assert.deepEqual(result.network_requests,[]);
  result.passed=true;fs.writeFileSync(path.join(destination,'validation.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify(result));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
