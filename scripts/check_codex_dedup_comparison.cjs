'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const modules=process.env.ORACLE_BROWSER_ROOT||'/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium}=require(path.join(modules,'playwright-core')),portable=require(path.join(modules,'@sparticuz/chromium'));

async function main(){
  const [file,report,screenshot]=process.argv.slice(2);
  const browser=await chromium.launch({executablePath:await portable.executablePath(),headless:true,
    args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('requestfailed',r=>{if(r.failure()?.errorText!=='net::ERR_ABORTED')errors.push(r.url());});
    await page.goto(pathToFileURL(path.resolve(file)).href,{waitUntil:'load'});
    await page.waitForFunction(()=>window.JEV_LAB?.comparison&&document.getElementById('rgb').naturalWidth>0);
    assert.equal(await page.locator('#language').inputValue(),'zh');
    const primary=await page.evaluate(()=>JEV_LAB.bundle.primaryModel||'astra');
    const modelKeys=await page.evaluate(()=>Object.keys(JEV_LAB.comparison.models));
    const caseCount=await page.evaluate(()=>JEV_LAB.bundle.cases.length);
    assert(await page.locator('#remove_'+primary).isChecked());
    assert(await page.locator('#remove_deepseek').isDisabled());
    const layout=await page.evaluate(()=>({children:document.querySelector('main.layout').children.length,
      observation:document.getElementById('observationPanel').getBoundingClientRect().top,
      main:document.querySelector('main.layout>section').getBoundingClientRect().top,
      notice:document.querySelector('.notice').textContent}));
    assert.equal(layout.children,3);assert(Math.abs(layout.observation-layout.main)<2,'Map and RGB panels are no longer side by side');
    assert(layout.notice.includes(['terra6','terra61'].includes(primary)?'GPT-6.1 Terra Fast':primary==='astra62'?'GPT-6.2 Astra':'GPT-6 Astra'));
    const details=[];
    for(let i=0;i<caseCount;i++){
      const row=await page.evaluate(i=>{
        JEV_LAB.select(i);const B=JEV_LAB.bundle,c=B.cases[i],models=JEV_LAB.comparison.models;
        const records=Object.fromEntries(Object.entries(models).map(([k,m])=>[k,m.cases.find(r=>r.episode_id===c.episode_id)]));
        const raw=records[B.primaryModel||'astra'].nodes;
        const checks=[];
        for(const flags of [[],...Object.keys(models).map(k=>[k]),Object.keys(models)]){
          for(const k of Object.keys(models))document.getElementById('remove_'+k).checked=flags.includes(k);
          JEV_LAB.draw();
          const expected=raw.filter(n=>!flags.some(k=>records[k]&&!records[k].final_active_ids.includes(n.id))).map(n=>n.id);
          const actual=JEV_LAB.displayState().versions[0].nodes.map(n=>n.id);
          checks.push({flags,expected,actual});
        }
        const middle=Math.floor(c.frames.length/2);JEV_LAB.seek(middle);
        return {case:c.case_number,availableModels:Object.keys(models).filter(k=>!!records[k]),checks,frame:middle,frameSlider:document.getElementById('frame').value,
          imageSlider:document.getElementById('imageFrame').value,deepseekAvailable:!!records.deepseek,
          deepseekDisabled:document.getElementById('remove_deepseek').disabled};
      },i);
      for(const check of row.checks)assert.deepEqual(check.actual,check.expected);
      assert.equal(row.frameSlider,String(row.frame));assert.equal(row.imageSlider,String(row.frame));
      assert.equal(row.deepseekDisabled,!row.deepseekAvailable);
      await page.locator('#rgb').evaluate(img=>img.decode());
      for(const model of row.availableModels){
        await page.selectOption('#reviewModel',model);
        const selection=await page.evaluate(model=>{
          const c=JEV_LAB.bundle.cases[JEV_LAB.state().caseIndex];
          const r=JEV_LAB.comparison.models[model].cases.find(r=>r.episode_id===c.episode_id);
          const d=r.decisions.find(d=>d.needs_model);
          if(!d)return null;
          const reason=d.validation_error?d.unvalidated_answer.reason:d.reason;
          return {value:JEV_LAB.state().caseIndex+':'+d.current_id,reason,validationError:!!d.validation_error,
            english:JEV_LAB.comparison.models[model].translations[reason],raw:d.raw_text};
        },model);
        if(!selection)continue;
        await page.selectOption('#dedupDecision',selection.value);
        for(const [language,reason] of [['zh',selection.reason],['en',selection.english]]){
          await page.selectOption('#language',language);
          const displayed=await page.locator('#dedupReason').textContent();
          if(selection.validationError){
            assert(displayed.endsWith(reason));
            assert(displayed.length>reason.length,'Invalid historical answer must retain its validation warning');
          }else assert.equal(displayed,reason);
        }
        assert.equal(await page.locator('#rawAnswerText').textContent(),selection.raw);
        assert.equal(await page.locator('#frame').inputValue(),String(row.frame));
        assert(await page.locator('#dedupEvidence img').count()>0);
        const count=await page.locator('.dedupEvidenceRow').first().locator('figure').count();
        const expectedCount=await page.evaluate(key=>JEV_LAB.comparison.models[key].observation_offsets.length,model);
        assert.equal(count,expectedCount);
        if(expectedCount===3){
          const prompt=await page.locator('#dedupPrompt').textContent();
          for(const label of ['A-1','A+1','B-1','B+1'])assert(!prompt.includes(label));
        }
        await page.selectOption('#language','zh');
      }
      details.push({case:row.case,filter_combinations:row.checks.length,available_models:row.availableModels});
    }
    // Exercise actual checkbox events and the unavailable-model explanation.
    const deepseekCase=await page.evaluate(()=>JEV_LAB.bundle.cases.findIndex(c=>JEV_LAB.comparison.models.deepseek.cases.some(r=>r.episode_id===c.episode_id)));
    await page.evaluate(i=>JEV_LAB.select(i),Math.max(0,deepseekCase));
    await page.locator('#showRawCandidates').click();
    await page.locator('#remove_'+primary).check();await page.locator('#remove_qwen').check();if(deepseekCase>=0)await page.locator('#remove_deepseek').check();
    assert((await page.locator('#combinationStatus').textContent()).includes('并集'));
    await page.evaluate(()=>JEV_LAB.select(0));await page.selectOption('#reviewModel','deepseek');
    assert((await page.locator('#dedupStatus').textContent()).includes('没有'));
    assert.equal(await page.locator('#dedupDecision option').count(),0);
    if(caseCount>10&&modelKeys.includes('astra')){
      await page.evaluate(()=>JEV_LAB.select(10));await page.selectOption('#reviewModel','astra');
      assert(await page.locator('#remove_astra').isDisabled());
      assert((await page.locator('#dedupStatus').textContent()).includes('没有'));
    }
    await page.selectOption('#reviewModel',primary);await page.locator('#showRawCandidates').click();await page.locator('#remove_'+primary).check();
    await page.evaluate(i=>JEV_LAB.select(i),Math.min(3,caseCount-1));
    await page.locator('#rgb').evaluate(img=>img.decode());
    await page.screenshot({path:screenshot,fullPage:true});
    await page.setViewportSize({width:430,height:932});
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+2);
    assert.equal(overflow,false,'Mobile page has horizontal overflow');
    assert.deepEqual(errors,[]);
    const result={checked_at:new Date().toISOString(),cases:caseCount,model_filters:true,combined_union:true,raw_candidates:true,
      bilingual_model_text:true,original_json_preserved:true,synchronized_sliders:true,native_images_loaded:true,
      unavailable_deepseek_explicit:true,mobile_no_overflow:true,details,errors};
    fs.writeFileSync(report,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
  }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
