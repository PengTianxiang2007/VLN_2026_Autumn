'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const modules='/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium}=require(path.join(modules,'playwright-core'));
const portable=require(path.join(modules,'@sparticuz/chromium'));
async function main(){
  const [html,record]=process.argv.slice(2),errors=[];
  const browser=await chromium.launch({executablePath:await portable.executablePath(),args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
  try{
    const page=await browser.newPage({viewport:{width:1550,height:1100}});
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(pathToFileURL(path.resolve(html)).href);
    await page.waitForFunction(()=>window.MultiDeviation && document.querySelector('#rgb')?.naturalWidth);
    assert.equal(await page.locator('#language').inputValue(),'zh');
    assert.equal(await page.locator('#cases button').count(),53);
    assert.equal(await page.locator('[data-layer]').count(),4);
    assert.equal(await page.locator('[data-layer]:checked').count(),3);
    assert.equal(await page.locator('[data-layer="deepseek_v003"]').isDisabled(),true);
    await page.evaluate(()=>{const e=document.querySelector('[data-layer="deepseek_v003"]');e.checked=true;e.dispatchEvent(new Event('change'));});
    assert.equal(await page.locator('[data-layer]:checked').count(),3);
    await page.locator('[data-layer="qwen_v003"]').uncheck();
    await page.locator('[data-layer="deepseek_v003"]').check();
    assert.equal(await page.locator('[data-layer]:checked').count(),3);
    for(const key of ['qwen_v003','deepseek_v003','qwen_v005','deepseek_v005']){const e=page.locator(`[data-layer="${key}"]`);if(await e.isChecked())await e.uncheck();}
    assert.equal(await page.locator('[data-track]').count(),0);
    await page.locator('#comparisonEmpty').waitFor();
    for(const k of ['qwen_v003','qwen_v005','deepseek_v005'])await page.locator(`[data-layer="${k}"]`).check();
    const totals=await page.evaluate(()=>Object.fromEntries(Object.entries(JEV_LAB.bundle.reviewVersions).map(([k,v])=>[k,v.totals])));
    for(const [key,n,calls,alarms,invalid] of [['qwen_v003',53,288,36,5],['deepseek_v003',29,99,28,5],['qwen_v005',53,272,40,0],['deepseek_v005',53,219,47,11]]){
      assert.equal(totals[key].cases,n);assert.equal(totals[key].calls,calls);assert.equal(totals[key].flagged,alarms);assert.equal(totals[key].invalid,invalid);
      await page.selectOption('#reviewVersion',key);
      const round=await page.evaluate(k=>JEV_LAB.bundle.reviewVersions[k].cases[JEV_LAB.bundle.cases[0].episode_id].rounds[0],key);
      await page.locator('[data-round="'+round.current_id+'"]').click();
      assert.equal(await page.locator('#v4Raw pre').textContent(),round.raw_answer);
      assert.equal(await page.locator('[data-input-frame]').count(),round.images.length);
      for(const locale of ['en','zh']){
        await page.selectOption('#language',locale);
        assert((await page.locator('#v4Review').textContent()).includes(round.answer.reason[locale]));
        assert.equal(await page.locator('#v4Raw pre').textContent(),round.raw_answer);
      }
    }
    // Missing coverage remains distinct from a negative verdict.
    await page.evaluate(()=>selectCase(52));await page.selectOption('#reviewVersion','deepseek_v003');
    assert((await page.locator('#v4Review').textContent()).includes('仅覆盖 C01–C29'));
    assert.equal(await page.locator('#v4Raw').count(),0);
    await page.selectOption('#language','en');assert((await page.locator('#v4Review').textContent()).includes('Not reviewed'));
    // The malformed JSON response remains visible without being repaired or accepted.
    await page.evaluate(()=>selectCase(21));await page.selectOption('#reviewVersion','deepseek_v005');
    await page.locator('[data-round="S01"]').click();
    const bad=await page.evaluate(()=>JEV_LAB.bundle.reviewVersions.deepseek_v005.cases[JEV_LAB.bundle.cases[21].episode_id].rounds[0]);
    assert.equal(bad.outcome,'format_error');assert.equal(bad.answer,null);assert.equal(await page.locator('#v4Raw pre').textContent(),bad.raw_answer);
    assert((await page.locator('#v4Review').textContent()).includes('could not be parsed'));
    await page.selectOption('#language','zh');assert((await page.locator('#v4Review').textContent()).includes('无法解析'));
    await page.locator('[data-input-frame]').first().click();assert.equal(await page.locator('#frame').inputValue(),await page.locator('#imageFrame').inputValue());
    // Capture a real case where all three selected versions have an alarm.
    const ci=await page.evaluate(()=>JEV_LAB.bundle.cases.findIndex(c=>['qwen_v003','qwen_v005','deepseek_v005'].every(k=>JEV_LAB.bundle.reviewVersions[k].intervals[c.episode_id]?.length)));
    assert(ci>=0);await page.evaluate(i=>selectCase(i),ci);await page.selectOption('#reviewVersion','deepseek_v005');
    assert.equal(await page.locator('.comparisonRail .band').count(),3);
    await page.waitForFunction(()=>mapCache.get(c().scene)?.naturalWidth>0);
    await page.evaluate(()=>window.scrollTo(0,0));
    await page.screenshot({path:path.join(record,'preview.png'),fullPage:false});
    assert.deepEqual(errors,[]);
    const result={cases:53,versions:totals,selection_limit:3,zero_selection:true,missing_coverage:true,invalid_raw_preserved:true,bilingual:true,input_frame_sync:true,errors};
    fs.writeFileSync(path.join(record,'browser_check.json'),JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify(result));
  }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
