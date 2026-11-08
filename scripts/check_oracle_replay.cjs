/* Real browser validation of the offline replay. No model/simulator is involved. */
const fs = require('fs'), path = require('path'), assert = require('assert');
const {pathToFileURL} = require('url');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright-core');
const file = path.resolve(process.argv[2]);
const out = path.resolve(process.argv[3] || path.join(path.dirname(file), 'replay_v2_validation'));
fs.mkdirSync(out, {recursive:true});

(async()=>{
  const browser = await chromium.launch({
    executablePath:process.env.CHROMIUM_EXECUTABLE,
    headless:true,
    args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-zygote'],
  });
  try {
    const page=await browser.newPage({viewport:{width:1600,height:1050},deviceScaleFactor:1});
    const errors=[],remote=[];
    page.on('pageerror',e=>errors.push(String(e)));
    page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url());});
    await page.goto(pathToFileURL(file).href,{waitUntil:'load',timeout:120000});
    await page.waitForFunction(()=>window.oracleReplay && !document.getElementById('loading'));
    await page.evaluate(()=>document.fonts.ready);
    await page.locator('#observation').evaluate(i=>i.decode());
    assert.equal(await page.locator('#groups button').count(),5);
    assert.equal(await page.locator('#cases button').count(),10);
    assert.equal(await page.locator('video').count(),0);
    await page.screenshot({path:path.join(out,'01_overview.png'),fullPage:true});

    let checkedRuns=0,checkedEvents=0;
    for(const group of ['early','d3','d5','d8','d12']){
      await page.evaluate(g=>window.oracleReplay.selectGroup(g),group);
      for(let ci=0;ci<10;ci++){
        await page.evaluate(i=>window.oracleReplay.selectCase(i),ci);
        const info=await page.evaluate(()=>{
          const r=window.oracleReplay,s=r.state(),c=r.data.cases[s.caseIndex];
          return {nodes:s.nodes.length,events:s.events.length,summary:document.getElementById('task-meta').textContent,
            image:document.getElementById('observation').src,payloadImage:r.data.images[s.node.image],
            badMap:/NaN|undefined/.test(document.getElementById('map').innerHTML),
            instructions:document.getElementById('instruction').textContent===c.instruction};
        });
        assert(info.nodes>1 && info.instructions && !info.badMap);
        assert.equal(info.image,info.payloadImage);
        for(let ei=0;ei<info.events;ei++){
          await page.evaluate(i=>window.oracleReplay.selectEvent(i,'before',false),ei);
          const before=await page.evaluate(()=>{const s=window.oracleReplay.state();return {node:s.node,event:s.events[s.eventIndex],index:s.nodeIndex}});
          assert.equal(before.node.phase,'before');
          assert.equal(before.index,before.event.before);
          await page.locator('#next').click();
          const after=await page.evaluate(()=>{const s=window.oracleReplay.state();return {node:s.node,index:s.nodeIndex,jumps:document.querySelectorAll('#jumps [data-jump]').length}});
          assert.equal(after.node.phase,'after');
          assert.equal(after.index,before.event.after);
          assert.equal(after.node.a,before.node.a);
          assert.equal(after.node.segment,before.node.segment+1);
          assert.equal(after.jumps,info.events);
          checkedEvents++;
        }
        checkedRuns++;
      }
    }
    assert.equal(checkedRuns,50);assert.equal(checkedEvents,26);

    await page.evaluate(()=>{window.oracleReplay.selectGroup('early');window.oracleReplay.selectCase(0);window.oracleReplay.selectEvent(0,'before');});
    await page.locator('#observation').evaluate(i=>i.decode());
    await page.screenshot({path:path.join(out,'02_before_teleport.png'),fullPage:true});
    await page.locator('[data-stage="after"].stage-button').click();
    await page.locator('#observation').evaluate(i=>i.decode());
    await page.screenshot({path:path.join(out,'03_after_teleport.png'),fullPage:true});
    assert.equal(await page.evaluate(()=>window.oracleReplay.state().node.phase),'after');

    // Actual playback controls, including pause and a manually moved slider.
    await page.locator('#restart').click();
    await page.locator('#play').click();
    await page.waitForTimeout(650);
    assert((await page.evaluate(()=>window.oracleReplay.state().nodeIndex))>0);
    await page.locator('#play').click();
    const paused=await page.evaluate(()=>window.oracleReplay.state().nodeIndex);
    await page.waitForTimeout(500);
    assert.equal(await page.evaluate(()=>window.oracleReplay.state().nodeIndex),paused);
    await page.locator('#timeline').evaluate(e=>{e.value=10;e.dispatchEvent(new Event('input',{bubbles:true}))});
    assert.equal(await page.evaluate(()=>window.oracleReplay.state().nodeIndex),10);
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.evaluate(()=>window.oracleReplay.state().nodeIndex),11);
    await page.locator('#fit-route').click();
    const scale=await page.evaluate(()=>window.oracleReplay.state().view.scale);
    await page.locator('#zoom-in').click();
    assert((await page.evaluate(()=>window.oracleReplay.state().view.scale))>scale);
    const rect=await page.locator('#map').boundingBox();
    const oldX=await page.evaluate(()=>window.oracleReplay.state().view.x);
    await page.mouse.move(rect.x+30,rect.y+150);await page.mouse.down();
    await page.mouse.move(rect.x+110,rect.y+180,{steps:8});await page.mouse.up();
    assert(Math.abs((await page.evaluate(()=>window.oracleReplay.state().view.x))-oldX)>50);

    // Multi-intervention task: each P/T pair remains individually navigable.
    await page.evaluate(()=>{const r=window.oracleReplay;r.selectCase(r.data.cases.findIndex(c=>c.id==='kujiale_0234_27_4'));r.selectEvent(4,'after');});
    assert.equal(await page.locator('#event-strip button').count(),5);
    await page.screenshot({path:path.join(out,'04_multiple_corrections.png'),fullPage:true});
    await page.locator('#observation').click();assert(await page.locator('#image-dialog').evaluate(e=>e.open));
    await page.keyboard.press('Escape');
    await page.locator('#help').click();assert(await page.locator('#help-dialog').evaluate(e=>e.open));
    await page.keyboard.press('Escape');

    await page.locator('[data-group="d8"]').click();
    assert((await page.locator('#event-detail').textContent()).includes('没有发生瞬移'));
    await page.locator('#filter').selectOption('intervened');
    assert.equal(await page.locator('#cases button').count(),0);
    await page.locator('#filter').selectOption('all');
    await page.screenshot({path:path.join(out,'05_no_intervention.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.waitForTimeout(200);
    assert(await page.locator('#mobile-case').isVisible());
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1));
    await page.screenshot({path:path.join(out,'06_mobile.png'),fullPage:true});
    assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
    const result={passed:true,browser:'Chromium',runs:checkedRuns,teleports:checkedEvents,
      actual_playback:true,pause:true,slider:true,pan_zoom:true,dialogs:true,mobile_no_horizontal_overflow:true,
      external_network_requests:remote.length,page_errors:errors.length,screenshots:6};
    fs.writeFileSync(path.join(out,'browser_verification.json'),JSON.stringify(result,null,2));
    console.log(JSON.stringify(result));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
