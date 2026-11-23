'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const modules = '/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium} = require(path.join(modules,'playwright-core'));
const portable = require(path.join(modules,'@sparticuz/chromium'));
const root = path.resolve(__dirname,'../../../../..');
const out = path.join(root,'outputs/visualization_publishing/v006_node_multiview_web_20261121_01');

async function main() {
  const errors = [];
  const browser = await chromium.launch({executablePath:await portable.executablePath(),
    args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
  try {
    const page = await browser.newPage({viewport:{width:1600,height:1100}});
    page.on('pageerror',e=>errors.push(e.message));
    page.on('requestfailed',r=>{if(r.failure()?.errorText !== 'net::ERR_ABORTED')errors.push(r.url());});
    await page.goto(pathToFileURL(path.join(out,'index.html')).href);
    await page.waitForFunction(()=>window.NodeMultiview && document.querySelector('#rgb')?.naturalWidth);
    assert.equal(await page.locator('#cases button').count(),53);
    assert.equal(await page.locator('#reviewVersion').inputValue(),'qwen_v006');
    assert.equal(await page.locator('[data-layer]').count(),5);
    assert.deepEqual(await page.evaluate(()=>MultiDeviation.selected()),['qwen_v005','deepseek_v005','qwen_v006']);
    assert.deepEqual(await page.evaluate(()=>NodeMultiview.data.totals),
      {cases:53,retained:376,terminal:53,rollback_targets:47,images:3432});
    async function checkViews(ids) {
      assert.deepEqual(await page.locator('[data-mv-view]').evaluateAll(xs=>xs.map(x=>Number(x.dataset.mvView))),ids);
      await page.locator('#mvGrid img').evaluateAll(images=>Promise.all(images.map(im=>im.decode())));
      const result = await page.evaluate(() => {
        const state = JEV_LAB.state(), g = NodeMultiview.data.cases[JEV_LAB.bundle.cases[state.caseIndex].episode_id];
        const n = g.nodes.find(n=>n.index===state.frame);
        return [...document.querySelectorAll('[data-mv-view]')].every(button => {
          const im=button.querySelector('img');
          return im.naturalWidth===640 && im.naturalHeight===480 && im.getAttribute('src')===n.views[Number(button.dataset.mvView)].image;
        });
      });
      assert(result);
      assert.equal(await page.locator('#frame').inputValue(),await page.locator('#imageFrame').inputValue());
      assert.equal(await page.locator('#nodeMultiview').getAttribute('data-node-frame'),await page.locator('#frame').inputValue());
    }
    await checkViews([1,0,7]);
    await page.selectOption('#mvMode','360'); await checkViews([0,1,2,3,4,5,6,7]);
    await page.locator('[data-mv-view="4"]').click();
    assert(await page.locator('#mvDialog').evaluate(d=>d.open));
    assert((await page.locator('#mvDialogCaption').textContent()).includes('正后 · 180°'));
    await page.locator('#mvEnlarged').evaluate(im=>im.decode());
    await page.locator('#mvClose').click();
    await page.evaluate(()=>NodeMultiview.jump(1));
    assert.equal(await page.locator('#mvGrid').count(),0);
    assert.equal(await page.locator('#nodeMultiview').getAttribute('data-node-frame'),null);
    assert((await page.locator('#mvStatus').textContent()).includes('不是保留'));
    await page.locator('#mvNext').click(); assert.equal(await page.locator('#frame').inputValue(),'5');
    await page.locator('#mvPrevious').click(); assert.equal(await page.locator('#frame').inputValue(),'0');

    await page.evaluate(()=>JEV_LAB.select(3));
    assert(await page.locator('#mvRollback').isDisabled());
    await page.evaluate(()=>JEV_LAB.select(49));
    await page.locator('[data-round="S05"]').click();
    assert.equal(await page.locator('#frame').inputValue(),'33');
    await page.locator('[data-mv-rollback-link]').click();
    assert.equal(await page.locator('#frame').inputValue(),'15');
    assert((await page.locator('#mvStatus').textContent()).includes('报警于 F33'));
    await page.selectOption('#mvMode','180'); await checkViews([1,0,7]);
    await page.locator('#nodeMultiview').screenshot({path:path.join(out,'multiview_desktop.png')});
    for (const language of ['en','zh']) {
      await page.selectOption('#language',language);
      await checkViews([1,0,7]);
      const content=await page.locator('#nodeMultiview').textContent();
      assert(content.includes(language==='en'?'Front-left':'左前'));
      assert(content.includes(language==='en'?'no physical rollback was performed':'未执行实际回退'));
      const raw=await page.evaluate(()=>{
        const state=JEV_LAB.state(),eid=JEV_LAB.bundle.cases[state.caseIndex].episode_id;
        return JEV_LAB.bundle.reviewVersions.qwen_v006.cases[eid].rounds.find(r=>r.current_id==='S04').raw_answer;
      });
      assert.equal(await page.locator('#v4Raw pre').textContent(),raw);
    }
    await page.selectOption('#reviewVersion','qwen_v005');
    assert.equal(await page.locator('#frame').inputValue(),'15'); await checkViews([1,0,7]);
    await page.selectOption('#reviewVersion','qwen_v006');
    await page.locator('[data-round="S03"]').click();
    assert((await page.locator('#v4Review').textContent()).includes('回答达到长度上限'));
    await page.locator('#mvRollback').click(); assert.equal(await page.locator('#frame').inputValue(),'15');
    await page.setViewportSize({width:390,height:844});
    await page.selectOption('#mvMode','360'); await checkViews([0,1,2,3,4,5,6,7]);
    const box=await page.locator('#nodeMultiview').boundingBox();
    assert(box.width<=390, 'Multiview panel overflows mobile viewport');
    await page.locator('#nodeMultiview').screenshot({path:path.join(out,'multiview_mobile.png')});
    await page.evaluate(()=>JEV_LAB.select(52));
    await page.locator('#terminalStep').click(); await checkViews([0,1,2,3,4,5,6,7]);
    assert((await page.locator('#mvStatus').textContent()).includes('终止节点'));
    assert(await page.locator('#mvNext').isDisabled());
    assert.deepEqual(errors,[]);
    const result={cases:53,retained:376,terminal:53,rollback_targets:47,
      checked_cases:['C01','C04','C50','C53'],views_180_and_360:true,full_resolution: [640,480],
      node_frame_not_alarm_frame:true,ordinary_frames_clear:true,node_navigation:true,
      terminal_views:true,modal:true,bilingual:true,sliders_synchronized:true,
      historical_versions_and_format_error_preserved:true,mobile:true,errors};
    fs.writeFileSync(path.join(out,'browser_check.json'),JSON.stringify(result,null,2)+'\n');
    fs.writeFileSync(path.join(__dirname,'browser_check.json'),JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
}
main().catch(e=>{console.error(e);process.exitCode=1;});
