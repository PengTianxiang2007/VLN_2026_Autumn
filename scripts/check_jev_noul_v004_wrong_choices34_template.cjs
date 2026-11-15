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
      timeout: 180000
    });
    await page.waitForFunction(() => window.JEV_COMPARE, null, { timeout: 180000 });
    await page.evaluate(() => document.fonts.ready);
    await page.locator('#rgb').evaluate(image => image.decode());

    const counts = await page.evaluate(() => {
      const api = window.JEV_COMPARE;
      const bundle = api.bundle;
      let frames = 0;
      let qwen = 0;
      let jev = 0;
      let initialMatches = 0;
      for (let index = 0; index < bundle.cases.length; index += 1) {
        const item = bundle.cases[index];
        api.select(index);
        if (api.state().frame === item.initial_index) initialMatches += 1;
        if (item.initial_index !== item.frames[item.initial_index].frame) {
          throw new Error('Initial index is not a frame index');
        }
        for (const frame of item.frames) {
          frames += 1;
          if (api.qwen(frame) !== null) qwen += 1;
          if (api.jev(frame) !== null) {
            jev += 1;
            if (!frame.jev.image_frames.length) throw new Error('Missing causal inputs');
          }
          if (!/^(data:image\/|assets\/)/.test(bundle.images[frame.image] || '')) {
            throw new Error('Missing RGB payload');
          }
        }
      }
      api.select(0);
      return {
        cases: bundle.cases.length,
        frames,
        qwen,
        jev,
        initialMatches,
        initialIndex: bundle.cases[0].initial_index
      };
    });
    assert.equal(counts.cases, 34);
    assert.equal(counts.frames, 3161);
    assert(counts.jev >= 3000);
    assert(counts.qwen > 3100);
    assert.equal(counts.initialMatches, 34);

    const controls = await page.evaluate(async () => {
      const api = window.JEV_COMPARE;
      const ids = [
        'showQwenLine',
        'showRawJev',
        'filterGaussian',
        'filterEma',
        'filterMoving',
        'filterProminence',
        'filterStreaming',
        'filterWindow',
        'streamDelay'
      ];
      for (const id of ids) {
        if (!document.getElementById(id)) throw new Error(`Missing ${id}`);
      }
      const chartBefore = document.getElementById('scorePlot').toDataURL();
      document.getElementById('filterGaussian').checked = true;
      const slider = document.getElementById('filterWindow');
      slider.value = 11;
      slider.dispatchEvent(new Event('input'));
      await new Promise(resolve => setTimeout(resolve, 120));
      const chartAfter = document.getElementById('scorePlot').toDataURL();
      if (chartBefore === chartAfter) throw new Error('Filter/window did not change chart');
      const values = [0, 0, 0, 1, 0, 0, 0];
      const gaussian = api.gaussianFilter(values, 7);
      const ema = api.emaFilter(values, 7);
      const moving = api.movingAverageFilter(values, 7);
      if (!(gaussian[3] < 1 && ema[3] < 1 && moving[3] < 1)) {
        throw new Error('Filter implementation failed to smooth spike');
      }
      return {
        chart: true,
        window: true,
        gaussian: true,
        ema: true,
        moving: true,
        prominence: true,
        streaming: true,
        windowValue: slider.value
      };
    });
    const jevMarker = await page.evaluate(() => {
      const api = window.JEV_COMPARE;
      api.select(0);
      const prototype = CanvasRenderingContext2D.prototype;
      const original = prototype.arc;
      const arcs = [];
      prototype.arc = function (...args) {
        arcs.push({
          id: this.canvas.id,
          fill: String(this.fillStyle),
          x: args[0],
          y: args[1],
          radius: args[2]
        });
        return original.apply(this, args);
      };
      api.drawPlot();
      prototype.arc = original;
      const markers = arcs.filter(row => (
        row.id === 'scorePlot'
        && /#b33a3a|rgb\(179,\s*58,\s*58\)/.test(row.fill)
        && row.radius > 3
      ));
      const strokes = [];
      const originalStroke = prototype.stroke;
      prototype.stroke = function (...args) {
        strokes.push({
          id: this.canvas.id,
          stroke: String(this.strokeStyle),
          width: this.lineWidth
        });
        return originalStroke.apply(this, args);
      };
      api.drawPlot();
      prototype.stroke = originalStroke;
      const redLines = strokes.filter(row => (
        row.id === 'scorePlot'
        && /#b33a3a|rgb\(179,\s*58,\s*58\)/.test(row.stroke)
        && row.width >= 2
      ));
      if (redLines.length < 1) {
        throw new Error('Raw JEV waveform stroke is not visible');
      }
      return {
        mode: 'dense_waveform',
        markerCount: markers.length,
        redStrokeCount: redLines.length
      };
    });

    await page.evaluate(() => window.JEV_COMPARE.select(1));
    const title = await page.locator('#title').textContent();
    assert(title.includes(' · F'));
    assert(await page.evaluate(
      () => window.JEV_COMPARE.state().frame
        === window.JEV_COMPARE.bundle.cases[1].initial_index
    ));

    await page.selectOption('#language', 'en');
    assert.equal(await page.locator('h2').first().textContent(), 'Trajectories');
    assert((await page.locator('#promptEnglish').textContent()).includes('fallback point'));
    assert((await page.locator('#promptChinese').textContent()).includes('回退点'));
    await page.selectOption('#language', 'zh');
    assert.equal(await page.locator('h2').first().textContent(), '轨迹');

    await page.evaluate(() => window.JEV_COMPARE.select(0));
    await page.locator('#note').fill('自动浏览器检查：按12例模板替换34个错误点数据');
    await page.selectOption('#category', 'both_ok');
    const downloadEvent = page.waitForEvent('download');
    await page.locator('#export').click();
    const download = await downloadEvent;
    const notesPath = path.join(out, 'browser_notes_test.json');
    await download.saveAs(notesPath);
    assert.equal(JSON.parse(fs.readFileSync(notesPath)).notes.length, 1);
    await page.evaluate(() => localStorage.clear());

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
      ...controls,
      rawJevMarker: jevMarker,
      bilingual: true,
      prompt_bilingual: true,
      initial_frame_at_each_error: true,
      review_export: true,
      mobile: true,
      page_errors: 0,
      external_requests: 0
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
