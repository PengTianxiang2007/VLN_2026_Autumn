'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { pathToFileURL } = require('url');

const env = JSON.parse(
  fs.readFileSync('/tmp/vln-oracle-ui-browser-direct-20261104/browser_env.json')
);
Object.assign(process.env, {
  LD_LIBRARY_PATH: env.LD_LIBRARY_PATH,
  FONTCONFIG_FILE: env.FONTCONFIG_FILE
});
const { chromium } = require(env.PLAYWRIGHT_MODULE);

(async () => {
  const file = path.resolve(process.argv[2]);
  const out = path.dirname(file);
  const browser = await chromium.launch({
    executablePath: env.CHROMIUM_EXECUTABLE,
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-gpu',
      '--disable-dev-shm-usage',
      '--allow-file-access-from-files'
    ]
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1560, height: 1150 },
      acceptDownloads: true
    });
    const errors = [];
    const remote = [];
    page.on('pageerror', error => errors.push(String(error)));
    page.on('request', request => {
      if (/^https?:/.test(request.url())) remote.push(request.url());
    });
    await page.goto(pathToFileURL(file).href, {
      waitUntil: 'load',
      timeout: 120000
    });
    await page.waitForFunction(() => window.WRONG_CHOICES_REVIEW);
    await page.evaluate(() => document.fonts.ready);
    await page.locator('#rgb').evaluate(image => image.decode());

    const counts = await page.evaluate(() => {
      const api = window.WRONG_CHOICES_REVIEW;
      const bundle = api.bundle;
      const seen = new Set();
      let images = 0;
      for (const event of bundle.events) {
        assertUnique(event.event_id);
        seen.add(event.event_id);
        if (event.qwen_score !== 1 && event.qwen_score !== 5) {
          throw new Error('Unexpected Qwen score');
        }
        if (!(event.jev_probability >= 0 && event.jev_probability <= 1)) {
          throw new Error('JEV probability outside 0..1');
        }
        const expected = Array.from(
          { length: event.frame - Math.max(0, event.frame - 2) + 1 },
          (_, index) => Math.max(0, event.frame - 2) + index
        );
        if (event.input_frames.map(row => row.frame).join(',') !== expected.join(',')) {
          throw new Error('Non-causal input frames');
        }
        for (const frame of event.input_frames) {
          if (!/^(data:image\/|assets\/)/.test(bundle.images[frame.image] || '')) {
            throw new Error('Missing input image');
          }
          images += 1;
        }
      }
      function assertUnique(value) {
        if (seen.has(value)) throw new Error('Duplicate event ID');
      }
      return {
        events: bundle.events.length,
        episodes: Object.keys(bundle.trajectories).length,
        images: Object.keys(bundle.images).length,
        input_frames: images,
        qwen1: bundle.events.filter(row => row.qwen_score === 1).length,
        qwen5: bundle.events.filter(row => row.qwen_score === 5).length,
        reused: bundle.events.filter(
          row => row.provenance === 'reused_exact_request'
        ).length,
        newCalls: bundle.events.filter(row => row.provenance === 'new_call').length
      };
    });
    assert.deepEqual(counts, {
      events: 34,
      episodes: 33,
      images: 101,
      input_frames: 92,
      qwen1: 14,
      qwen5: 20,
      reused: 5,
      newCalls: 29
    });
    const decodedImages = await page.evaluate(async () => {
      const uris = [...new Set(Object.values(window.WRONG_CHOICES_REVIEW.bundle.images))];
      const results = await Promise.all(uris.map(uri => new Promise(resolve => {
        const image = new Image();
        image.onload = () => resolve(true);
        image.onerror = () => resolve(false);
        image.src = uri;
      })));
      if (results.some(value => !value)) throw new Error('An image asset failed to decode');
      return results.length;
    });

    const colors = await page.evaluate(() => {
      const api = window.WRONG_CHOICES_REVIEW;
      const luminance = color => {
        const values = color.match(/\d+/g).slice(0, 3).map(Number);
        return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2];
      };
      const q1 = api.qwenColor(1);
      const q5 = api.qwenColor(5);
      const j0 = api.jevColor(0);
      const j1 = api.jevColor(1);
      if (!(luminance(q5) < luminance(q1))) {
        throw new Error('Qwen palette does not darken with score');
      }
      if (!(luminance(j1) < luminance(j0))) {
        throw new Error('JEV palette does not darken with probability');
      }
      return { q1, q5, j0, j1 };
    });
    const plotChecks = await page.evaluate(async () => {
      const api = window.WRONG_CHOICES_REVIEW;
      if (!document.getElementById('scorePlot')) throw new Error('Missing line chart');
      if (Number(document.getElementById('filterWindow').value) !== 5) {
        throw new Error('Unexpected default sliding window');
      }
      if (document.getElementById('smoothingMode').value !== 'none') {
        throw new Error('Smoothing unexpectedly enabled by default');
      }
      if (!document.getElementById('showQwenRaw').checked
          || !document.getElementById('showJevRaw').checked) {
        throw new Error('Raw lines hidden by default');
      }
      const values = [1, 1, 1, 5, 1, 1, 1, 1];
      const gaussian = api.smoothSeries(values, 'gaussian', 5);
      const ema = api.smoothSeries(values, 'ema', 5);
      const moving = api.smoothSeries(values, 'moving', 5);
      if (!(gaussian[3] > 1 && gaussian[3] < 5)) {
        throw new Error('Gaussian smoothing did not reduce the spike');
      }
      if (!(ema[3] > 1 && ema[3] < 5)) {
        throw new Error('EMA did not smooth the spike');
      }
      if (!(moving[3] > 1 && moving[3] < 5)) {
        throw new Error('Moving average did not smooth the spike');
      }
      const before = document.getElementById('scorePlot').toDataURL();
      const slider = document.getElementById('filterWindow');
      slider.value = 9;
      slider.dispatchEvent(new Event('input'));
      const mode = document.getElementById('smoothingMode');
      mode.value = 'gaussian';
      mode.dispatchEvent(new Event('change'));
      await new Promise(resolve => setTimeout(resolve, 100));
      const after = document.getElementById('scorePlot').toDataURL();
      if (before === after) throw new Error('Sliding window/filter did not change chart');
      if (!document.getElementById('plotSummary').textContent.includes('9')) {
        throw new Error('Sliding-window summary not updated');
      }
      return {
        chart: true,
        slider: true,
        gaussian: true,
        ema: true,
        moving: true,
        gaussianPeak: gaussian[3],
        emaPeak: ema[3],
        movingPeak: moving[3]
      };
    });

    const initialTitle = await page.locator('#eventTitle').textContent();
    await page.evaluate(() => window.WRONG_CHOICES_REVIEW.select(1));
    const secondTitle = await page.locator('#eventTitle').textContent();
    assert.notEqual(initialTitle, secondTitle);
    assert((await page.locator('#events button.active').textContent()).includes(
      secondTitle.split(' · ')[0]
    ));

    const mapDifference = await page.evaluate(() => {
      const left = document.getElementById('qwenMap');
      const right = document.getElementById('jevMap');
      const a = left.getContext('2d').getImageData(0, 0, left.width, left.height).data;
      const b = right.getContext('2d').getImageData(0, 0, right.width, right.height).data;
      let differing = 0;
      for (let index = 0; index < a.length; index += 16) {
        if (
          a[index] !== b[index]
          || a[index + 1] !== b[index + 1]
          || a[index + 2] !== b[index + 2]
        ) differing += 1;
      }
      if (!differing) throw new Error('Maps are visually identical');
      return differing;
    });

    await page.selectOption('#filters', 'qwen1');
    assert.equal(await page.locator('#events button').count(), 14);
    await page.selectOption('#filters', 'qwen5');
    assert.equal(await page.locator('#events button').count(), 20);
    await page.selectOption('#filters', 'jevHigh');
    assert.equal(await page.locator('#events button').count(), 19);
    await page.selectOption('#filters', 'jevLow');
    assert.equal(await page.locator('#events button').count(), 4);
    await page.selectOption('#filters', 'reused');
    assert.equal(await page.locator('#events button').count(), 5);
    await page.selectOption('#filters', 'all');
    await page.fill('#search', 'kujiale_0257_82_4');
    assert.equal(await page.locator('#events button').count(), 2);
    await page.fill('#search', '');
    assert.equal(await page.locator('#events button').count(), 34);

    await page.selectOption('#language', 'en');
    assert.equal(await page.locator('#title').textContent(), 'Human-labeled wrong choices · JEV v004 × Qwen4B');
    assert((await page.locator('#instruction').textContent()).includes('Original task instruction'));
    assert((await page.locator('#runInfo').textContent()).includes('34 wrong choices'));
    assert((await page.locator('#promptEnglish').textContent()).includes('fallback point'));
    assert((await page.locator('#promptChinese').textContent()).includes('回退点'));
    await page.selectOption('#language', 'zh');
    assert.equal(await page.locator('#title').textContent(), '人工错误选择点 · JEV v004 × Qwen4B');
    assert((await page.locator('#instruction').textContent()).includes('原任务指令'));

    await page.locator('#note').fill('自动浏览器检查：错误选择点双模型对照');
    await page.selectOption('#category', 'likely');
    const downloadEvent = page.waitForEvent('download');
    await page.locator('#export').click();
    const download = await downloadEvent;
    const notesPath = path.join(out, 'browser_notes_test.json');
    await download.saveAs(notesPath);
    assert.equal(JSON.parse(fs.readFileSync(notesPath)).notes.length, 1);
    await page.evaluate(() => localStorage.clear());

    await page.evaluate(() => window.WRONG_CHOICES_REVIEW.select(0));
    await page.screenshot({
      path: path.join(out, 'browser_desktop.png'),
      fullPage: true
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(250);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
    await page.screenshot({
      path: path.join(out, 'browser_mobile.png'),
      fullPage: true
    });
    assert.deepEqual(errors, []);
    assert.deepEqual(remote, []);

    const result = {
      passed: true,
      ...counts,
      decoded_images: decodedImages,
      bilingual: true,
      prompt_bilingual: true,
      event_switching: true,
      filters: true,
      review_export: true,
      mobile: true,
      mapDifference,
      colors,
      ...plotChecks,
      page_errors: errors.length,
      external_requests: remote.length
    };
    fs.writeFileSync(
      path.join(out, 'browser_verification.json'),
      JSON.stringify(result, null, 2)
    );
    console.log(JSON.stringify(result));
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exit(1);
});
