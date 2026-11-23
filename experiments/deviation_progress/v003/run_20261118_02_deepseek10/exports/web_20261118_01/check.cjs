'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const modules = process.env.ORACLE_BROWSER_ROOT || '/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium} = require(path.join(modules,'playwright-core'));
const portable = require(path.join(modules,'@sparticuz/chromium'));
const read = p => JSON.parse(fs.readFileSync(p,'utf8'));

async function check(){
  const [root,file,report,snapshot] = process.argv.slice(2);
  const index = read(snapshot || path.join(root,'dedup_resume_01/summary.json'));
  const trajectories = Object.keys(index.case_results).length;
  const browser = await chromium.launch({executablePath:await portable.executablePath(),
    args:['--no-sandbox','--no-zygote','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
  try {
    const page = await browser.newPage();
    const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('requestfailed',req=>{if(req.failure()?.errorText!=='net::ERR_ABORTED')errors.push(req.url());});
    await page.goto(pathToFileURL(path.resolve(file)).href);
    await page.waitForFunction(()=>window.JEV_LAB && document.querySelector('#rgb').naturalWidth>0);
    assert.equal(await page.locator('html').getAttribute('lang'),'zh-CN');
    assert.equal(await page.locator('#cases button').count(),trajectories);
    assert(await page.locator('#nodeDeduplication').isChecked());
    assert(await page.locator('#nodeDeduplicationTop').isVisible());
    await page.locator('#dedupAudit>summary').click();
    let raw=0, retained=0, compared=0, scored=0, invalid=0;
    for(const [i,[eid,item]] of Object.entries(index.case_results).entries()){
      const c = read(path.join(root,item.result));
      const actual = await page.evaluate(({i,eid})=>{
        JEV_LAB.select(i);
        const row=JEV_LAB.bundle.cases[i];
        const state=()=>JEV_LAB.displayState().versions[0].nodes.map(n=>n.id);
        const kept=state();
        JEV_LAB.seek(row.frames.length-1);
        if(JSON.stringify(kept)!==JSON.stringify(state()))throw Error('Slider changed retained nodes');
        if(+document.querySelector('#frame').value!==+document.querySelector('#imageFrame').value)throw Error('Sliders differ');
        document.querySelector('#nodeDeduplicationTop').click();
        const before=state();
        document.querySelector('#nodeDeduplicationTop').click();
        if(row.episode_id!==eid)throw Error('Episode ID mismatch');
        return {kept,before,eid,scored:row.frames.length};
      },{i,eid});
      assert.deepEqual(actual.kept,c.final_active_ids);
      assert.deepEqual(actual.before,c.nodes.map(n=>n.id));
      await page.locator('#rgb').evaluate(img=>img.decode());
      raw+=actual.before.length; retained+=actual.kept.length; scored+=actual.scored;
      for(const lang of ['zh','en']){
        await page.selectOption('#language',lang);
        const rows=await page.evaluate(({i,lang})=>{
          const $=id=>document.getElementById(id), d=JEV_LAB.dedupData.cases[i], row=JEV_LAB.bundle.cases[i];
          if(!$('instruction').textContent.includes(row['instruction_'+lang]))throw Error('Wrong instruction');
          if($('dedupPrompt').textContent!==JEV_LAB.dedupData['prompt_'+lang])throw Error('Wrong prompt');
          const select=$('dedupDecision');
          return d.decisions.map((decision,j)=>{
            select.selectedIndex=j; select.dispatchEvent(new Event('change'));
            const reason=$('dedupReason').textContent;
            const branches=Array.from($('dedupBranches').children,n=>n.textContent);
            if(lang==='en' && /[\u3400-\u9fff]/u.test([reason,...branches].join(' ')))throw Error('Missing English translation');
            if(!reason || reason==='undefined')throw Error('Missing reason');
            const urls=Array.from($('dedupEvidence').querySelectorAll('img'),n=>n.getAttribute('src'));
            const expected=[decision.previous_id,decision.current_id].filter(Boolean)
              .flatMap(id=>d.nodes.find(n=>n.id===id).images.filter(f=>!f.missing).map(f=>JEV_LAB.bundle.images[f.image_id]));
            if(decision.needs_model && (urls.length!==expected.length||urls.some((url,k)=>!url.endsWith(expected[k]))))throw Error('Evidence mismatch');
            if(!decision.needs_model && urls.length)throw Error('Unexpected comparison images');
            return {reason,branchCount:branches.length,option:select.value, label:select.selectedOptions[0].textContent};
          });
        },{i,lang});
        assert.equal(rows.length,c.decisions.length);
        for(const [j,res] of rows.entries()){
          const d=c.decisions[j];
          assert.equal(res.option,i+':'+d.current_id);
          let answer=d.answer;
          if(d.status==='error'){
            const saved=read(path.join(path.dirname(path.join(root,item.result)),'requests',d.current_id+'.response.json'));
            answer=JSON.parse(saved.response.choices[0].message.content);
            assert(res.label.includes(lang==='zh'?'校验失败':'Validation failed'));
            assert(res.reason.includes('['+answer.relation+']'));
            if(lang==='zh'){assert(res.reason.includes(answer.reason));invalid++;}
          }else if(lang==='zh')assert.equal(res.reason,d.reason);
          assert.equal(res.branchCount,answer?answer.matched_branches.length+answer.a_only.length+answer.b_only.length:0);
        }
      }
      compared+=c.summary.model_calls;
      await page.selectOption('#language','zh');
    }
    assert.deepEqual([raw,retained,compared],[index.dedup.candidates,index.dedup.retained,index.dedup.model_calls]);
    assert.deepEqual(errors,[]);
    assert.equal(invalid,index.dedup.errors||0);
    const result={trajectories,scored_frames:scored,raw,retained,compared,invalid,c48:index.case_results.kujiale_0259_55_0?.retained_ids,
      reasons_and_evidence_checked_both_languages:true,sliders_and_dedup_toggle:true,errors};
    fs.writeFileSync(report,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
    console.log(JSON.stringify(result));
  }finally{await browser.close();}
}
check().catch(err=>{console.error(err);process.exitCode=1;});
