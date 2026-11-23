const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const modules = '/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium} = require(path.join(modules, 'playwright-core'));
const portable = require(path.join(modules, '@sparticuz/chromium'));

(async () => {
  const dir = path.resolve(process.argv[2]);
  const summary = JSON.parse(fs.readFileSync(path.join(__dirname, 'summary.json')));
  const browser = await chromium.launch({executablePath:await portable.executablePath(),
    args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
  try {
    const page = await browser.newPage({viewport:{width:1600,height:960}});
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(pathToFileURL(path.join(dir, 'index.html')).href);
    const section = page.locator('#recoveryInstruction');
    await section.waitFor();
    assert.equal(await page.locator('#cases button').count(),47);
    for (const cid of ['C50','C07']) {
      await page.locator('#cases button').filter({hasText:cid+' ·'}).click();
      assert.equal(await section.getAttribute('data-case'),cid);
      const imgFrame=page.locator('#imageFrame');
      const frame=await imgFrame.inputValue();
      for (const id of ['qwen','deepseek']) {
        const toggle = section.locator('[data-model="'+id+'"]');
        const output = section.locator('[data-instruction-model="'+id+'"]');
        assert(await toggle.isChecked());
        await toggle.uncheck();
        assert.equal(await output.count(),0);
        assert.equal(await page.locator('[data-model-panel="'+id+'"]').count(),0);
        assert.equal(await section.locator('[data-instruction-model]').count(),1);
        await toggle.check();
        assert(await output.isVisible());
        assert.equal(await imgFrame.inputValue(), frame);
      }
      await page.selectOption('#language','en');
      for (const id of ['qwen','deepseek']) {
        const row = summary[id].cases[cid];
        const out = section.locator('[data-instruction-model="'+id+'"]');
        assert.equal(await out.locator('[data-role="command"] strong').innerText(),row.instruction_en ?? 'No executable instruction');
        assert((await out.locator('[data-role="previous"] h3').innerText()).startsWith(row.previous+' ·'));
        if (row.selected) assert((await out.locator('[data-role="selected"] h3').innerText()).startsWith(row.selected+' ·'));
        assert.equal(JSON.parse(await out.locator('details pre').textContent()).selected_branch_id,row.selected);
      }
      await page.evaluate(f=>JEV_LAB.seek(f+3),Number(frame));
      await page.locator('#observationRollback').click();
      assert.equal(await imgFrame.inputValue(),frame);
      assert.equal(await page.locator('#observationPanel #frame').inputValue(),frame);
      await page.selectOption('#language','zh');
      assert.equal(await section.getAttribute('data-case'),cid);
    }
    assert.deepEqual(errors,[]);
    const result={cases:47,checked_cases:['C50','C07'],both_models_both_stages:true,language_frame_and_rollback_sync:true,page_errors:errors};
    fs.writeFileSync(path.join(dir,'paired_playback_check.json'),JSON.stringify(result,null,2));
    console.log(result);
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
