'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const modules='/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium}=require(path.join(modules,'playwright-core'));
const portable=require(path.join(modules,'@sparticuz/chromium'));
async function main(){
  const [html,output]=process.argv.slice(2);
  const browser=await chromium.launch({executablePath:await portable.executablePath(),args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
  const errors=[];
  try{
    const page=await browser.newPage({viewport:{width:1600,height:1000}});
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(pathToFileURL(path.resolve(html)).href);
    await page.waitForFunction(()=>window.syncV4Review && document.querySelector('#rgb')?.naturalWidth);
    const b=await page.evaluate(()=>JEV_LAB.bundle);
    assert.equal(await page.locator('#language').inputValue(),'zh');
    assert.equal(await page.locator('#cases button').count(),53);
    assert.equal(b.v4.version,'v006');
    assert.equal(b.tag,b.dedup.source_tag);
    assert.deepEqual([b.v4.totals.calls,b.v4.totals.flagged,b.v4.totals.invalid,b.v4.totals.frames,b.v4.totals.nodes],[253,47,9,4890,429]);
    await page.locator('#nodeDeduplication').check();
    const checks=[];
    for(const [i,c] of b.cases.entries()){
      const g=b.v4.cases[c.episode_id];
      const selected=g.rounds.filter(r=>r.validation_error || ((i===0 || i===52)&&r===g.rounds[0]));
      if(!selected.length)continue;
      await page.locator('#cases button').nth(i).click();
      assert.equal(await page.locator('#v4RoundList button').count(),g.nodes.length);
      for(const r of selected){
        await page.locator('[data-round="'+r.current_id+'"]').click();
        assert.equal(await page.locator('#v4Raw pre').textContent(),r.raw_answer);
        assert.equal(await page.locator('[data-input-frame]').count(),r.images.length);
        const a=r.answer || r.display_partial;
        for(const lang of ['en','zh']){
          await page.selectOption('#language',lang);
          const text=await page.locator('#v4Review').textContent();
          assert(text.includes(a.reason[lang]));
          assert(text.includes(r.committed_progress[lang]));
          if(r.validation_error)assert(text.includes(r.validation_error_text[lang]));
          if(a.comments)assert(text.includes(a.comments[lang]));
          assert.equal(await page.locator('#v4Raw pre').textContent(),r.raw_answer);
        }
        await page.locator('[data-input-frame]').first().click();
        assert.equal(await page.locator('#frame').inputValue(),await page.locator('#imageFrame').inputValue());
        await page.waitForFunction(()=>[...document.querySelectorAll('[data-input-frame] img')].every(i=>i.complete && i.naturalWidth===640));
        checks.push(g.case_id+'/'+r.current_id);
      }
    }
    assert.deepEqual(errors,[]);
    const result={cases:53,rounds:253,flagged:47,invalid:9,locales:['zh','en'],checked_rounds:checks,raw_answers_preserved:true,sliders_synced:true,dedup_source_matches:true,errors};
    fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
  }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
