'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert');
const {pathToFileURL}=require('url');
const env=JSON.parse(fs.readFileSync('/tmp/vln-oracle-ui-browser-direct-20261104/browser_env.json'));
Object.assign(process.env,{LD_LIBRARY_PATH:env.LD_LIBRARY_PATH,FONTCONFIG_FILE:env.FONTCONFIG_FILE});
const {chromium}=require(env.PLAYWRIGHT_MODULE);
(async()=>{
 const file=path.resolve(process.argv[2]),out=path.dirname(file),browser=await chromium.launch({executablePath:env.CHROMIUM_EXECUTABLE,headless:true,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']});
 try{
  const page=await browser.newPage({viewport:{width:1480,height:1100},acceptDownloads:true}),errors=[],remote=[];
  page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url())});
  await page.goto(pathToFileURL(file).href,{waitUntil:'load',timeout:120000});await page.waitForFunction(()=>window.CROSSING_LITE);
  await page.evaluate(()=>document.fonts.ready);await page.locator('#rgb').evaluate(i=>i.decode());
  const counts=await page.evaluate(()=>{
   const a=window.CROSSING_LITE;let frames=0,positions=0,valid=0;
   for(const [i,c] of a.bundle.cases.entries()){
    a.select(i);
    for(const r of c.frames){frames++;const p=r.prediction;if(p){if(p.image_frames.join(',')!==Array.from({length:Math.min(3,r.frame+1)},(_,n)=>Math.max(0,r.frame-2)+n).join(','))throw Error('Noncausal input');if(p.valid){valid++;if(!Number.isInteger(p.score)||p.score<1||p.score>5)throw Error('Invalid score')}}if(!a.bundle.images[r.image]?.startsWith('data:image/'))throw Error('Missing image')}
    for(const f of new Set([0,Math.floor(c.frames.length/2),c.frames.length-1,...c.marks.map(e=>e.frame)])){
     a.seek(f);positions++;if(a.state().frame!==f||Number(document.getElementById('frame').value)!==f||Number(document.getElementById('imageFrame').value)!==f)throw Error('Slider mismatch');if(document.getElementById('rgb').src!==a.bundle.images[c.frames[f].image])throw Error('RGB mismatch');
     const p=c.frames[f].prediction;if(p?.valid&&document.getElementById('answer').textContent!==JSON.stringify(p.answer,null,2))throw Error('Answer mismatch');
    }
   }
   a.select(0);return {cases:a.bundle.cases.length,frames,positions,valid,groups:a.bundle.summary.groups};
  });
  for(const group of ['failure','success']){await page.selectOption('#filters',group);assert.equal(await page.locator('#cases button').count(),counts.groups[group])}await page.selectOption('#filters','all');
  for(const id of ['frame','imageFrame']){await page.locator('#'+id).evaluate(e=>{e.value=2;e.dispatchEvent(new Event('input'))});assert.equal((await page.evaluate(()=>window.CROSSING_LITE.state())).frame,2)}
  await page.selectOption('#threshold','5');await page.selectOption('#threshold','4');
  await page.locator('#note').fill('自动浏览器检查：同步与复核导出');await page.selectOption('#category','correct');
  const downloadEvent=page.waitForEvent('download');await page.locator('#export').click();const dl=await downloadEvent;await dl.saveAs(path.join(out,'browser_notes_test.json'));
  assert.equal(JSON.parse(fs.readFileSync(path.join(out,'browser_notes_test.json'))).notes.length,1);await page.evaluate(()=>localStorage.clear());
  await page.locator('#rgb').evaluate(i=>i.decode());await page.screenshot({path:path.join(out,'browser_desktop.png')});
  await page.locator('#rgb').click();assert(await page.locator('#imageDialog').isVisible());await page.locator('#closeImage').click();
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(150);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
  await page.locator('h1').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,'browser_mobile.png')});
  assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
  const result={passed:true,...counts,dual_sliders:true,causal_history:true,raw_answers:true,review_export:true,mobile:true,external_requests:0,page_errors:0};
  fs.writeFileSync(path.join(out,'browser_verification.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
