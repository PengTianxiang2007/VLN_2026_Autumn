'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const fs = require('node:fs');
const modules = process.env.ORACLE_BROWSER_ROOT || '/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium} = require(path.join(modules,'playwright-core'));
const portable = require(path.join(modules,'@sparticuz/chromium'));
async function main() {
  const [html, expectedPath] = process.argv.slice(2);
  const expected = JSON.parse(fs.readFileSync(expectedPath,'utf8'));
  const browser = await chromium.launch({executablePath:await portable.executablePath(),args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
  try {
    const page=await browser.newPage({viewport:{width:1600,height:1000}}), errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(pathToFileURL(path.resolve(html)).href);
    await page.waitForFunction(()=>window.syncV4Review && document.querySelector('#rgb')?.naturalWidth);
    assert.equal(await page.locator('#language').inputValue(),'zh');
    assert.equal(await page.locator('#cases button').count(),expected.length);
    const bundle=await page.evaluate(()=>JEV_LAB.bundle);
    assert.equal(bundle.v4.version,'v005'); assert.equal(bundle.v4.partial,false);
    assert.equal(Object.keys(bundle.v4.cases).length,expected.length);
    assert.equal(bundle.v4.totals.calls,expected.reduce((sum,row)=>sum+row.calls,0));
    assert.equal(bundle.v4.totals.flagged,expected.reduce((sum,row)=>sum+(row.first_deviation?1:0),0));
    await page.locator('#cases button').last().click();
    const first=expected.find(row=>row.episode_id===bundle.cases[bundle.cases.length-1].episode_id);
    assert.equal(await page.locator('#v4RoundList button').count(),bundle.v4.cases[first.episode_id].nodes.length);
    const round=bundle.v4.cases[first.episode_id].rounds[0];
    await page.locator('[data-round="'+round.current_id+'"]').click();
    assert.equal(await page.locator('#v4Raw pre').textContent(),round.raw_answer);
    assert.equal(await page.locator('[data-input-frame]').count(),round.images.length);
    for(const lang of ['en','zh']) { await page.selectOption('#language',lang); assert((await page.locator('#v4Review').textContent()).includes(round.answer.reason[lang])); assert.equal(await page.locator('#v4Raw pre').textContent(),round.raw_answer); }
    await page.locator('[data-input-frame]').first().click();
    assert.equal(await page.locator('#frame').inputValue(),await page.locator('#imageFrame').inputValue());
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({cases:expected.length,calls:bundle.v4.totals.calls,locales:['zh','en'],raw_answer:true,errors}));
  } finally { await browser.close(); }
}
main().catch(error=>{console.error(error);process.exitCode=1;});
