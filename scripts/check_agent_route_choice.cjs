/* CPU browser checks for inputs, translated real answers and invalid raw responses. */
const fs = require('fs'), path = require('path'), assert = require('assert'), crypto = require('crypto');
const {pathToFileURL} = require('url');
const file = path.resolve(process.argv[2]);
const configPath = process.argv[3] || '/tmp/vln-oracle-ui-browser-direct-20261104/browser_env.json';
const cfg = JSON.parse(fs.readFileSync(configPath));
const {chromium} = require(cfg.PLAYWRIGHT_MODULE);
(async () => {
  const browser = await chromium.launch({executablePath: cfg.CHROMIUM_EXECUTABLE, headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']});
  const result = {cases: 0, model_case_checks: 0, image_checks: 0, fixed_checkpoint_checks: 0, branch_cards_checked: 0, selected_branches_checked: 0, translated_answers_checked: 0, invalid_responses_checked: 0, page_errors: [], network_requests: [], passed: false};
  try {
    const page = await browser.newPage({viewport: {width: 1650, height: 1100}});
    page.on('pageerror', e => result.page_errors.push(String(e)));
    page.on('request', r => {if (/^https?:/.test(r.url())) result.network_requests.push(r.url());});
    await page.goto(pathToFileURL(file).href);
    await page.evaluate(() => document.fonts.ready);
    assert(await page.evaluate(() => document.fonts.check('14px RouteChoiceSans', '复位选路')));
    assert.equal(await page.locator('#cases button').count(), 10);
    const modelCount = await page.evaluate(() => DATA.models.length);
    assert.equal(await page.locator('#model').inputValue(), modelCount ? '0' : '-1');
    assert.equal(await page.locator('#advancedDetails').evaluate(el => el.open), false);
    const counts = await page.evaluate(() => DATA.cases.map(c => ({context: c.images.filter(x => x.phase === 'checkpoint_context').length, all: c.images.length, cp: c.checkpoint_frame})));
    for (const modelIndex of modelCount ? Array.from({length:modelCount}, (_,i)=>i) : [-1]) {
    const beforeModel = await page.locator('#frame').inputValue();
    await page.locator('#model').selectOption(String(modelIndex));
    assert.equal(await page.locator('#frame').inputValue(), beforeModel);
    for (let i = 0; i < 10; i++) {
      await page.locator('#cases button').nth(i).click();
      assert.equal(await page.locator('#advancedDetails').evaluate(el => el.open), false);
      await page.waitForFunction(() => $('checkpointImage').complete && $('checkpointImage').naturalWidth === 640 && $('checkpointImage').naturalHeight === 480);
      const hero = await page.evaluate(() => {
        const c = current(), cp = c.images.find(im => im.frame === c.checkpoint_frame);
        const first = slot(1)?.parsed, choice = slot(2)?.parsed;
        return {srcMatches:$('checkpointImage').src === DATA.images[cp.sha256], imageId:$('checkpointImage').dataset.imageId,
          expectedId:cp.id, frame:Number($('checkpointImage').dataset.frame), expectedFrame:c.checkpoint_frame,
          branches:first?.branches || [], choice, heading:$('chosenHeading').textContent,
          cards:Array.from(document.querySelectorAll('#branchCards .branch-card')).map(el=>({...el.dataset})),
          source:model()?.checkpoint_views[c.sample_id]};
      });
      assert(hero.srcMatches); assert.equal(hero.imageId, hero.expectedId); assert.equal(hero.frame, hero.expectedFrame);
      assert.equal(hero.cards.length, hero.branches.length);
      hero.branches.forEach((branch,n) => {
        assert.equal(hero.cards[n].branchId, branch.id); assert.equal(hero.cards[n].direction, branch.direction);
        assert.equal(hero.cards[n].selected, String(hero.choice?.selected_branch_id === branch.id));
        assert.equal(hero.cards[n].excluded, String(!!hero.choice?.excluded_branch_ids?.includes(branch.id)));
        result.branch_cards_checked++;
      });
      if (hero.choice?.selected_branch_id) {assert(hero.heading.includes(hero.choice.selected_branch_id)); result.selected_branches_checked++;}
      if (hero.source?.matches_recorded_request['2']) assert(hero.source.matches_recorded_request['1']);
      result.fixed_checkpoint_checks++; result.image_checks++;
      const fixedSource = await page.locator('#checkpointImage').getAttribute('src');
      await page.locator('#advancedDetails').evaluate(el => {el.open = true;});
      for (const call of [1, 2]) {
        await page.locator('#call' + call).click();
        const status = await page.evaluate(() => ({stage, id: current().sample_id, frame: timeline()[index].frame,
          reset: timeline()[index].reset, a: $('frame').value, b: $('imageFrame').value}));
        assert.equal(status.stage, call); assert.equal(status.frame, counts[i].cp);
        assert.equal(status.reset, call === 2); assert.equal(status.a, status.b);
        assert.equal(await page.locator('#checkpointImage').getAttribute('src'), fixedSource);
        assert.equal(await page.locator('#history img').count(), call === 1 ? counts[i].context : counts[i].all);
        await page.waitForFunction(() => Array.from(document.querySelectorAll('#rgb,#history img')).every(im => im.complete && im.naturalWidth === 640 && im.naturalHeight === 480));
        result.image_checks += 1 + (call === 1 ? counts[i].context : counts[i].all);
        const answer = await page.evaluate(() => slot(stage) || null);
        if (answer?.raw_content) {
          assert.equal(await page.locator('#rawAnswer').textContent(), answer.raw_content);
          if (answer.answer_zh) {
            const expected = call === 1 ? answer.answer_zh.view_summary : answer.answer_zh.error_reason;
            assert((await page.locator('#answer').textContent()).includes(expected));
            result.translated_answers_checked++;
          }
          if (!answer.validated) {
            assert((await page.locator('#answerStatus').textContent()).includes('未通过协议校验'));
            result.invalid_responses_checked++;
          }
          await page.locator('#language').selectOption('en');
          assert.equal(await page.locator('#answer').textContent(), answer.raw_content);
          await page.locator('#language').selectOption('zh');
        }
        if (call === 2) {
          await page.locator('#history button').first().click();
          assert.equal(await page.evaluate(() => stage), 2);
          assert.equal(await page.locator('#frame').inputValue(), await page.locator('#imageFrame').inputValue());
          assert.equal(await page.locator('#checkpointImage').getAttribute('src'), fixedSource);
        }
      }
      for (const control of ['frame', 'imageFrame']) {
        await page.locator('#' + control).evaluate(el => {el.value = '0'; el.dispatchEvent(new Event('input', {bubbles: true}));});
        assert.equal(await page.locator('#frame').inputValue(), await page.locator('#imageFrame').inputValue());
        assert.equal(await page.locator('#checkpointImage').getAttribute('src'), fixedSource);
      }
      result.model_case_checks++;
    }
    }
    result.cases = counts.length;
    if (modelCount) await page.locator('#model').selectOption('0');
    await page.locator('#cases button').first().click();
    const imageBox = await page.locator('#checkpointImage').boundingBox();
    assert(imageBox.y >= 0 && imageBox.y + imageBox.height <= 1100);
    assert(await page.locator('#chosenHeading').isVisible());
    await page.locator('#checkpointImage').click();
    assert(await page.locator('#checkpointDialog').evaluate(el=>el.open));
    assert.equal(await page.locator('#checkpointLarge').getAttribute('src'), await page.locator('#checkpointImage').getAttribute('src'));
    await page.locator('#closeCheckpoint').click(); result.checkpoint_zoom_passed = true;
    await page.screenshot({path: file.replace(/\.html$/, '.preview.png'), fullPage: true});
    if (result.invalid_responses_checked) {
      await page.locator('#cases button').nth(6).click();
      const invalid = await page.evaluate(() => slot(2));
      if (invalid?.parsed?.wrong_branch_id === invalid?.parsed?.selected_branch_id) {
        assert((await page.locator('#decisionSummary').textContent()).includes('矛盾'));
        assert((await page.locator('#choiceWarning').textContent()).includes('同一支路'));
        assert.equal(await page.locator('#branchCards .conflict').count(), 1);
        await page.screenshot({path:file.replace(/\.html$/, '.invalid_case07.png'), fullPage:true});
      }
    }
    await page.locator('#advancedDetails').evaluate(el => {el.open = true;});
    await page.locator('#note').fill('浏览器检查：中文复核意见');
    const downloadPromise = page.waitForEvent('download'); await page.locator('#export').click();
    const download = await downloadPromise, stream = await download.createReadStream(); let noteText = '';
    for await (const chunk of stream) noteText += chunk.toString();
    assert(JSON.parse(noteText).notes.some(n => n.note === '浏览器检查：中文复核意见'));
    result.notes_export_passed = true;
    await page.setViewportSize({width:680,height:1000});
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
    result.mobile_no_overflow = true;
    assert.deepEqual(result.page_errors, []); assert.deepEqual(result.network_requests, []);
    result.passed = true;
  } finally {
    await browser.close();
    result.html_sha256 = crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
    result.checker_sha256 = crypto.createHash('sha256').update(fs.readFileSync(__filename)).digest('hex');
    fs.writeFileSync(file.replace(/\.html$/, '.browser_validation.json'), JSON.stringify(result, null, 2), {flag: 'wx'});
  }
  process.stdout.write(JSON.stringify(result));
})().catch(e => {console.error(e); process.exitCode = 1;});
