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
    assert.equal(await page.locator('[data-layer]').count(),5);
    assert.equal(await page.locator('#reviewVersion').inputValue(),'qwen_v006');
    assert.deepEqual(await page.evaluate(()=>MultiDeviation.selected()),['qwen_v005','deepseek_v005','qwen_v006']);
    await page.evaluate(()=>{const e=document.querySelector('[data-layer="qwen_v003"]');e.checked=true;e.dispatchEvent(new Event('change'));});
    assert.equal(await page.locator('[data-layer]:checked').count(),3);
    await page.locator('[data-layer="qwen_v005"]').uncheck();
    await page.locator('[data-layer="qwen_v003"]').check();
    assert.equal(await page.locator('[data-track]').count(),3);
    const bundle=await page.evaluate(()=>JEV_LAB.bundle);
    assert.equal(bundle.tag,bundle.dedup.source_tag);
    assert.equal(bundle.reviewVersions.qwen_v006.totals.calls,253);
    assert.equal(bundle.reviewVersions.qwen_v006.totals.invalid,9);
    assert.equal(Object.values(bundle.reviewVersions).reduce((s,v)=>s+v.totals.calls,0),1131);
    for(const [key,v] of Object.entries(bundle.reviewVersions)){
      await page.selectOption('#reviewVersion',key);
      const r=v.cases[bundle.cases[0].episode_id].rounds[0];
      await page.locator('[data-round="'+r.current_id+'"]').click();
      for(const lang of ['en','zh']){
        await page.selectOption('#language',lang);
        assert((await page.locator('#v4Review').textContent()).includes(r.answer.reason[lang]));
        assert.equal(await page.locator('#v4Raw pre').textContent(),r.raw_answer);
      }
    }
    await page.evaluate(()=>selectCase(49));await page.selectOption('#reviewVersion','qwen_v006');
    await page.locator('[data-round="S03"]').click();
    const truncated=bundle.reviewVersions.qwen_v006.cases[bundle.cases[49].episode_id].rounds.find(r=>r.current_id==='S03');
    assert.equal(truncated.answer,null);
    for(const lang of ['en','zh']){
      await page.selectOption('#language',lang);
      const text=await page.locator('#v4Review').textContent();
      assert(text.includes(truncated.display_partial.reason[lang]));
      assert(text.includes(truncated.display_partial.comments[lang]));
      assert(text.includes(truncated.validation_error_text[lang]));
      assert.equal(await page.locator('#v4Raw pre').textContent(),truncated.raw_answer);
    }
    await page.locator('[data-input-frame]').first().click();
    assert.equal(await page.locator('#frame').inputValue(),await page.locator('#imageFrame').inputValue());
    await page.waitForFunction(()=>[...document.querySelectorAll('[data-input-frame] img')].every(i=>i.complete&&i.naturalWidth>0));
    await page.evaluate(()=>selectCase(52));await page.selectOption('#reviewVersion','deepseek_v003');
    assert((await page.locator('#v4Review').textContent()).includes('仅覆盖 C01–C29'));
    assert.equal(await page.locator('#v4Raw').count(),0);
    assert.deepEqual(errors,[]);
    const result={cases:53,versions:5,rounds:1131,default_review:'qwen_v006',maximum_layers:3,bilingual:true,truncated_raw_preserved:true,input_frame_sync:true,missing_coverage_preserved:true,errors};
    fs.writeFileSync(record,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
  }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
