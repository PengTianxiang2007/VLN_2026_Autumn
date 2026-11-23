const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const deps = '/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium} = require(deps+'/playwright-core');
const portable = require(deps+'/@sparticuz/chromium');
const out = path.resolve('outputs/visualization_publishing/v006_node_multiview70_web_20261121_01');
(async () => {
  const browser = await chromium.launch({executablePath:await portable.executablePath(),args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', e=>errors.push(e.message));
    await page.goto(pathToFileURL(out+'/index.html').href);
    await page.waitForFunction(()=>window.NodeMultiview);
    assert.deepEqual(await page.locator('#mvMode option').evaluateAll(xs=>xs.map(o=>o.value)),['180','360','70']);
    for (const mode of ['180','360','70']) {
      await page.selectOption('#mvMode',mode);
      assert.equal(await page.locator('#mvGrid img').count(),mode==='360'?8:3);
      await page.locator('#mvGrid img').evaluateAll(xs=>Promise.all(xs.map(im=>im.decode())));
    }
    for (const language of ['en','zh']) {
      await page.selectOption('#language',language);
      assert((await page.locator('#mvGrid').textContent()).includes('+70°'));
      assert((await page.locator('#mvGrid').textContent()).includes('-70°'));
    }
    const src = await page.locator('#mvGrid img').first().getAttribute('src');
    await page.locator('[data-mv-view="1"]').click();
    assert.equal(await page.locator('#mvEnlarged').getAttribute('src'),src);
    await page.locator('#mvClose').click();
    await page.evaluate(()=>JEV_LAB.select(49));
    await page.locator('#mvRollback').click();
    assert.equal(await page.locator('#frame').inputValue(),'15');
    await page.locator('#mvGrid img').evaluateAll(xs=>Promise.all(xs.map(im=>im.decode())));
    await page.locator('#terminalStep').click();
    assert.equal(await page.locator('#mvGrid').count(),0);
    assert((await page.locator('.mvMissing').textContent()).includes('未采集'));
    await page.selectOption('#mvMode','180');
    assert.equal(await page.locator('#mvGrid img').count(),3);
    assert.deepEqual(errors,[]);
    const result = {passed:true,options:['180','360','70'],bilingual:true,modal:true,C50_target_frame:15,terminal_missing:true,errors};
    fs.writeFileSync(out+'/browser_check.json',JSON.stringify(result,null,2));
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1});
