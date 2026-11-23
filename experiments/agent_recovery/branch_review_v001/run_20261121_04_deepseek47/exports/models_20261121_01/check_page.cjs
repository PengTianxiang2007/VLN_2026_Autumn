const assert=require('node:assert/strict'),fs=require('fs'),path=require('path'),{pathToFileURL}=require('url');
const modules='/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium}=require(path.join(modules,'playwright-core')),portable=require(path.join(modules,'@sparticuz/chromium'));
(async()=>{
 const out=path.resolve(process.argv[2]), url=pathToFileURL(path.join(out,'index.html'));
 const ds=JSON.parse(fs.readFileSync('outputs/agent_recovery/branch_review_v001/run_20261121_04_deepseek47/results.json'));
 const q=JSON.parse(fs.readFileSync('outputs/agent_recovery/branch_review_v001/run_20261121_02_all47/results.json'));
 const alt=JSON.parse(fs.readFileSync('outputs/agent_recovery/branch_review_v001.1/run_20261121_01/results.json'));
 const b=await chromium.launch({executablePath:await portable.executablePath(),args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
 try{
  const page=await b.newPage({viewport:{width:1600,height:1000}}),err=[];
  page.on('pageerror',e=>err.push(e.message));
  await page.goto(url.href);await page.waitForFunction(()=>window.BranchReview && document.querySelector('#rgb')?.naturalWidth);
  assert.equal(await page.locator('#language').inputValue(),'zh');
  assert.equal(await page.locator('#cases button').count(),47);
  const corpus=await page.evaluate(()=>Object.values(BranchReview.data.cases).map(r=>({
   c:r.input.case_id,inputs:r.input.images.length,q:r.result.answer,d:r.deepseek.result.answer,qraw:r.result.raw_answer,draw:r.deepseek.result.raw_answer,comparison:r.comparison?.result.answer
  })));
  for(const x of corpus){
   const qr=q.find(r=>r.case_id===x.c);assert.deepEqual(x.q,qr.answer);assert.equal(x.qraw,qr.raw_answer);
   assert.deepEqual(x.d,ds[x.c].answer);assert.equal(x.inputs,7);
   const raw=JSON.parse(fs.readFileSync('outputs/agent_recovery/branch_review_v001/run_20261121_04_deepseek47/'+x.c+'/response.json')).choices[0].message.content;
   assert.equal(x.draw,raw);assert.deepEqual(x.comparison,alt.find(r=>r.case_id===x.c)?.answer);
  }
  for(const cid of ['C50','C07','C01']){
   const idx=corpus.findIndex(v=>v.c===cid);await page.locator('#cases button').nth(idx).click();
   const ck=id=>page.locator('input[data-model="'+id+'"]'),pan=id=>page.locator('[data-model-panel="'+id+'"]');
   await ck('qwen').check();await ck('deepseek').check();const compare=await ck('comparison').isEnabled();assert.equal(compare,cid!=='C01');
   if(compare)await ck('comparison').check();
   const c=corpus[idx];assert.equal(await pan('deepseek').locator('article').count(),c.d.branches.length);
   assert.equal(await pan('qwen').locator('article').count(),c.q.branches.length);
   if(compare)assert(await pan('comparison').locator('.branchCandidateAudit').isVisible());
   const frame=await page.locator('#frame').inputValue();
   await ck('qwen').uncheck();assert.equal(await pan('qwen').count(),0);assert(await pan('deepseek').isVisible());
   await page.selectOption('#language','en');assert.equal(await page.locator('#imageFrame').inputValue(),frame);
   assert.equal(await page.locator('#branchReview').getAttribute('data-case'),cid);
   assert.equal(await pan('deepseek').locator('[data-taken=true]').getAttribute('data-branch'),c.d.previous_attempt.branch_id);
   const en=await page.evaluate(()=>BranchReview.data.cases[JEV_LAB.bundle.cases[JEV_LAB.state().caseIndex].episode_id].deepseek.translation);
   assert((await pan('deepseek').textContent()).includes(en.previous_attempt.reason));
   await ck('deepseek').uncheck();if(compare)await ck('comparison').uncheck();
   assert.equal(await page.locator('[data-model-panel]').count(),0);
   await ck('qwen').check();assert.equal(await page.locator('#frame').inputValue(),frame);
   await page.selectOption('#language','zh');await ck('deepseek').check();
   await page.locator('[data-branch-image="C_plus10"]').click();assert.equal(await page.locator('#imageFrame').inputValue(),String(+frame+10));
   await page.locator('#branchImageDialog button').click();
  }
  assert.deepEqual(err,[]);const res={cases:corpus.length,v1_original_pairs:corpus.length,shared_image_slots:corpus.reduce((n,x)=>n+x.inputs,0),v11_cases:alt.map(x=>x.case_id),checked_interaction_cases:['C50','C07','C01'],independent_model_checkboxes:true,bilingual_same_case_frame:true,synchronized_map_rgb:true,errors:err};
  fs.writeFileSync(path.join(out,'browser_check.json'),JSON.stringify(res,null,2)+'\n');console.log(JSON.stringify(res));
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
