'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const root = process.env.ORACLE_BROWSER_ROOT || '/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium} = require(path.join(root, 'playwright-core'));
const portable = require(path.join(root, '@sparticuz/chromium'));

async function run() {
  const source = path.resolve(process.argv[2]), reports = path.resolve(process.argv[3]);
  fs.mkdirSync(reports, {recursive:true});
  const browser = await chromium.launch({executablePath:await portable.executablePath(),headless:true,
    args:['--no-sandbox','--no-zygote','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:960}});
    const errors = [];
    page.on('pageerror',err=>errors.push(String(err)));
    page.on('requestfailed',req=>{if(!req.failure()?.errorText.includes('ABORTED')) errors.push(req.url());});
    await page.goto(pathToFileURL(source).href);
    const tasks = await page.evaluate(()=>REPLAY.tasks.map(t=>({id:t.id,events:t.events,steps:t.robot.length})));
    assert.equal(tasks.length,53);
    const ready = async () => page.waitForFunction(()=>loadState==='ready' && $('focus').style.backgroundImage.includes(atlasURL));
    let eventCount=0;
    for(const t of tasks) {
      await page.selectOption('#task',t.id);
      await ready();
      const routePoints = await page.evaluate(()=>({
        actual:$('actualLine').points.numberOfItems,ref:$('refLine').points.numberOfItems,
        expected:task.reference.length,map:$('floor').getAttribute('href'),
        instruction:$('instruction').textContent,reason:$('reason').textContent}));
      assert.equal(routePoints.actual,t.steps); assert.equal(routePoints.ref,routePoints.expected);
      assert.match(routePoints.instruction,/[\u4e00-\u9fff]/); assert.match(routePoints.reason,/[\u4e00-\u9fff]/);
      assert(fs.existsSync(path.join(path.dirname(source),routePoints.map)));
      for(let i=0;i<t.events.length;i++) {
        const e=t.events[i];eventCount++;
        for(const [index,step] of [[0,e.anchor],[1,e.confirm]]) {
          await page.locator('.event').nth(i).locator('button').nth(index).evaluate(b=>b.click());
          await ready();
          assert.equal(await page.locator('#imageStep').inputValue(),String(step));
          assert.equal(await page.locator('#mapStep').inputValue(),String(step));
          assert(await page.evaluate(()=>atlasURL.includes(task.id+'/'+String(step).padStart(4,'0'))));
        }
      }
      const at = await page.locator('#mapStep').inputValue();
      await page.selectOption('#language','1');
      assert.equal(await page.locator('#mapStep').inputValue(),at);
      assert(await page.evaluate(()=>$('reason').textContent===task.reason[1] && $('instruction').textContent===task.instruction[1] && !/[\u4e00-\u9fff]/.test(task.reason[1]+task.instruction[1])));
      await page.selectOption('#language','0');
    }
    assert.equal(eventCount,54);
    await page.selectOption('#task',tasks[0].id);
    await page.locator('#events button').first().click();await ready();
    const anchor = await page.locator('#mapStep').inputValue();
    for(const [actual,ref] of [[false,false],[true,false],[false,true],[true,true]]) {
      await page.locator('#actual').setChecked(actual); await page.locator('#ref').setChecked(ref);
      assert.deepEqual(await page.evaluate(()=>['actualLayer','refLayer','robot','floor'].map(id=>getComputedStyle($(id)).display!=='none')),
        [actual,ref,true,true]);
      assert.equal(await page.locator('#imageStep').inputValue(),anchor);
    }
    for(const [mode,count] of [['front',0],['360',8],['180',3]]) {
      await page.selectOption('#mode',mode); assert.equal(await page.locator('#thumbs button').count(),count);
      if(count) await page.locator('#thumbs button').last().click();
      assert.equal(await page.locator('#mapStep').inputValue(),anchor);
    }
    await page.screenshot({path:path.join(reports,'desktop.png'),fullPage:true});
    await page.locator('#play').click();await page.waitForFunction(a=>step>Number(a),anchor);
    await page.locator('#play').click();
    await page.locator('#imageStep').evaluate(el=>{el.value=el.max;el.dispatchEvent(new Event('input'));});await ready();
    assert.equal(await page.locator('#mapStep').inputValue(),String(tasks[0].steps-1));
    await page.setViewportSize({width:390,height:844});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    assert.deepEqual(errors,[]);
    const result={checked_at:new Date().toISOString(),passed:true,tasks:tasks.length,events:eventCount,
      steps:tasks.reduce((sum,t)=>sum+t.steps,0),layer_combinations:4,both_languages:true,
      mobile_layout:true,playback:true,all_modes:true,browser_errors:errors};
    fs.writeFileSync(path.join(reports,'browser_check.json'),JSON.stringify(result,null,2)+'\n');
    console.log(result);
  } finally {await browser.close();}
}
run().catch(err=>{console.error(err);process.exitCode=1;});
