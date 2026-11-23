'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const modules = process.env.ORACLE_BROWSER_ROOT || '/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium} = require(path.join(modules, 'playwright-core'));
const portable = require(path.join(modules, '@sparticuz/chromium'));
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));

async function main() {
  const [run, file, report] = process.argv.slice(2);
  const expected = read(path.join(run, 'summary.json'));
  const browser = await chromium.launch({executablePath: await portable.executablePath(),
    args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--allow-file-access-from-files']});
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('requestfailed', req => {if (req.failure()?.errorText !== 'net::ERR_ABORTED') errors.push(req.url());});
    await page.goto(pathToFileURL(path.resolve(file)).href);
    await page.waitForFunction(() => window.JEV_LAB && document.getElementById('rgb').naturalWidth > 0);
    assert(await page.locator('#sample_v001').isChecked());
    assert(!(await page.locator('#nodeDeduplication').isChecked()));
    const quick = page.locator('#showCheckpoints');
    const hasQuickToggle = (await quick.count()) === 1;
    if (hasQuickToggle) {
      assert(await quick.isChecked());
      await quick.uncheck();
      assert(!(await page.locator('#sample_v001').isChecked()));
      assert.equal(await page.evaluate(() => JEV_LAB.displayState().versions.length), 0);
      await page.locator('#sample_v001').check();
      assert(await quick.isChecked());
      assert(await page.locator('#reference').isChecked());
    }
    let scored = 0, candidates = 0;
    const ids = await page.evaluate(() => JEV_LAB.bundle.cases.map(c => c.episode_id));
    for (const [i,id] of ids.entries()) {
      const scores = read(path.join(run, 'episodes', id, 'scores.json'));
      const sampling = read(path.join(run, 'episodes', id, 'sampling.json'));
      const actual = await page.evaluate(index => {
        JEV_LAB.select(index);
        const c = JEV_LAB.bundle.cases[index];
        const first = JEV_LAB.displayState().versions[0].nodes;
        JEV_LAB.seek(c.frames.length - 1);
        return {scores:c.frames.map(f => f.jev.probability_yes), nodes:JEV_LAB.displayState().versions[0].nodes,
          stable:JSON.stringify(first)===JSON.stringify(JEV_LAB.displayState().versions[0].nodes),
          instruction:c.instruction_zh, displayed:document.getElementById('instruction').textContent};
      }, i);
      assert.deepEqual(actual.scores, scores);
      assert.deepEqual(actual.nodes, sampling.nodes);
      assert(actual.stable && actual.instruction && actual.displayed.includes(actual.instruction));
      await page.locator('#rgb').evaluate(img => img.decode());
      await page.selectOption('#language','en');
      assert(await page.evaluate(i => document.getElementById('instruction').textContent.includes(JEV_LAB.bundle.cases[i].instruction_en),i));
      await page.selectOption('#language','zh');
      scored += scores.length;
      candidates += actual.nodes.length;
    }
    assert.equal(ids.length, expected.episodes);
    assert.equal(scored, expected.scored);
    assert.equal(candidates, expected.candidates);
    assert.deepEqual(errors, []);
    const result = {episodes:ids.length, scored, candidates, all_nodes_match_saved_results:true,
      stable_under_playback:true, bilingual_instructions:true, deduplication:false,
      map_shortcut_verified:hasQuickToggle, errors};
    fs.writeFileSync(report, JSON.stringify(result,null,2)+'\n', {flag:'wx'});
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
}
main().catch(error => {console.error(error);process.exitCode=1;});
