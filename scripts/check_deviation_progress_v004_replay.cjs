'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const crypto = require('node:crypto');
const modules = process.env.ORACLE_BROWSER_ROOT || '/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium} = require(path.join(modules,'playwright-core'));
const portable = require(path.join(modules,'@sparticuz/chromium'));
const read = file => JSON.parse(fs.readFileSync(file,'utf8'));

async function main() {
  const [run, file, output, model] = process.argv.slice(2);
  const version = read(path.join(run,'manifest.json')).version || 'v004';
  const expected = read(path.join(run,version+'_results.json'));
  const browser = await chromium.launch({executablePath:await portable.executablePath(),
    args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
  const errors=[];
  let rounds=0, missing=0, thumbnails=0;
  try {
    const page=await browser.newPage({viewport:{width:1600,height:1000}});
    page.on('pageerror',e=>errors.push(e.message));
    page.on('requestfailed',r=>{if(r.failure()?.errorText!=='net::ERR_ABORTED') errors.push(r.url().slice(0,160));});
    const entry = pathToFileURL(path.resolve(file));
    if(model) entry.searchParams.set('model',model);
    await page.goto(entry.href);
    await page.waitForFunction(()=>window.syncV4Review && document.querySelector('#rgb')?.naturalWidth);
    assert.equal(await page.locator('#language').inputValue(),'zh');
    assert(await page.locator('#guardOverlay').isChecked());
    assert.equal(await page.locator('#cases button').count(),6);
    if(model) {
      assert.equal(await page.locator('#v4Model').inputValue(),model);
      assert.equal(await page.evaluate(()=>JEV_LAB.bundle.v4.modelId),model);
    }
    for(const [i,c] of expected.entries()){
      await page.locator('#cases button').nth(i).click();
      const nodes=read(path.join(run,'retained_nodes_and_terminals.json'))[c.episode_id];
      assert.equal(await page.locator('#v4RoundList button').count(),nodes.length);
      const got=await page.evaluate(id=>JEV_LAB.bundle.deviationReviews[id],c.episode_id);
      assert.deepEqual(got,c.first_deviation?[{from_frame:c.first_deviation.from_frame,to_frame:c.first_deviation.to_frame}]:[]);
      for(const node of nodes){
        await page.locator(`[data-round="${node.id}"]`).click();
        assert.equal(await page.locator('#frame').inputValue(),String(node.index));
        const round=c.rounds.find(r=>r.node===node.id);
        if(!round){
          assert.equal(await page.locator('#v4Raw').count(),0);
          assert((await page.locator('#v4Review').textContent()).includes('没有发出模型请求'));
          missing++;
          continue;
        }
        const folder=path.join(run,'run/cases','C'+String(c.case_number).padStart(2,'0'));
        const req=read(path.join(folder,node.id+'.request.json'));
        const response=read(path.join(folder,node.id+'.response.json'));
        const content=response.response.choices[0].message.content, answer=JSON.parse(content);
        const saved=read(path.join(folder,'result.json')).reviews.find(row=>row.node_id===node.id);
        assert.equal(await page.locator('#v4Raw pre').textContent(),content);
        assert.equal(await page.locator('[data-input-frame]').count(),req.images.length);
        for(const [idx,im] of req.images.entries()){
          const button=page.locator('[data-input-frame]').nth(idx);
          assert.equal(await button.getAttribute('data-input-frame'),String(im.frame));
          const src=await button.locator('img').getAttribute('src');
          const digest=src.startsWith('data:')?crypto.createHash('sha256').update(Buffer.from(src.split(',')[1],'base64')).digest('hex'):path.basename(src,'.png');
          assert.equal(digest,im.sha256);
        }
        await page.locator('[data-input-frame]').first().click();
        assert.equal(await page.locator('#imageFrame').inputValue(),String(req.images[0].frame));
        assert.equal(await page.locator('#frame').inputValue(),String(req.images[0].frame));
        assert.equal(await page.locator('[data-round][aria-pressed=true]').getAttribute('data-round'),node.id);
        if(model) {
          const peer=await page.locator('#v4Model option').evaluateAll((options,id)=>options.find(o=>o.value!==id).value,model);
          for(const id of [peer,model]) {
            await page.selectOption('#v4Model',id);
            assert.equal(await page.locator('#title').textContent(),c.episode_id);
            assert.equal(await page.locator('#frame').inputValue(),String(req.images[0].frame));
            assert.equal(await page.locator('#imageFrame').inputValue(),String(req.images[0].frame));
            assert.equal(await page.locator('[data-round][aria-pressed=true]').getAttribute('data-round'),node.id);
            const view=await page.evaluate(({eid,node})=>{
              const review=JEV_LAB.bundle.v4;
              return {name:review.modelName,raw:review.cases[eid].rounds.find(r=>r.current_id===node)?.raw_answer ?? null,
                stats:[review.totals.calls,review.totals.flagged,review.totals.invalid]};
            },{eid:c.episode_id,node:node.id});
            assert((await page.title()).includes(view.name));
            assert.deepEqual((await page.locator('#stats strong').allTextContents()).slice(-3).map(Number),view.stats);
            assert.deepEqual(await page.locator('#v4Raw pre').allTextContents(),view.raw===null?[]:[view.raw]);
          }
        }
        for(const language of ['en','zh']){
          await page.selectOption('#language',language);
          assert.equal(await page.locator('[data-round][aria-pressed=true]').getAttribute('data-round'),node.id);
          assert.equal(await page.locator('#v4Raw pre').textContent(),content);
          const fields=await page.locator('#v4Review .v4block p').allTextContents();
          for(const value of [answer.reason[language],answer.segment_summary[language],saved.prior_progress[language],saved.committed_progress[language],
            ...answer.instruction_evidence.map(q=>q['quote_'+language])]) assert(fields.includes(value),node.id+' '+language+' missing translated field');
          assert((await page.locator('#v4Prompt pre').textContent()).includes('semantic_progress'));
        }
        await page.locator('[data-input-frame] img').evaluateAll(imgs=>Promise.all(imgs.map(img=>img.decode())));
        thumbnails+=req.images.length; rounds++;
      }
    }
    await page.locator('#guardOverlay').uncheck();await page.locator('#guardOverlay').check();
    assert.deepEqual(errors,[]);
    const result={model,model_switch_same_case_round_frame:Boolean(model),cases:expected.length,rounds,unreviewed:missing,thumbnails,raw_answer_verbatim:true,
      bilingual_every_round:true,synchronized_sliders:true,errors};
    fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
  } finally {await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
