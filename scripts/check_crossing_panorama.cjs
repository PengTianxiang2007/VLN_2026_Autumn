/* Verify every task/view and full-size image in the standalone data review. */
const fs=require('fs'),path=require('path'),assert=require('assert');
const {pathToFileURL}=require('url');
const file=path.resolve(process.argv[2]);
const cfg=JSON.parse(fs.readFileSync(process.argv[3]||'/tmp/vln-oracle-ui-browser-direct-20261104/browser_env.json'));
const {chromium}=require(cfg.PLAYWRIGHT_MODULE);
(async()=>{
 const browser=await chromium.launch({executablePath:cfg.CHROMIUM_EXECUTABLE,headless:true,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']});
 const result={cases:0,panorama_image_checks:0,original_frame_checks:0,zoom_checks:0,errors:[],network:[],passed:false};
 try{
  const page=await browser.newPage({viewport:{width:1500,height:1200}});
  page.on('pageerror',e=>result.errors.push(String(e)));
  page.on('request',r=>{if(/^https?:/.test(r.url()))result.network.push(r.url())});
  await page.goto(pathToFileURL(file).href);
  await page.evaluate(()=>document.fonts.ready);
  assert(await page.evaluate(()=>document.fonts.check('16px PanoramaSans','周围画面支路')));
  assert.equal(await page.locator('#case option').count(),10);
  for(let i=1;i<=10;i++){
   await page.locator('#case').selectOption(`sample_${String(i).padStart(2,'0')}`);
   await page.waitForFunction(()=>Array.from(document.querySelectorAll('#original,#views img')).every(im=>im.complete&&im.naturalWidth===640&&im.naturalHeight===480));
   assert.equal(await page.locator('#views img').count(),8);
   const values=await page.evaluate(()=>{
    const c=data.cases.find(x=>x.sample_id===select.value),p=data.panoramas[c.panorama_id];
    return {original:document.getElementById('original').src===data.images[c.checkpoint_image],
      views:Array.from(document.querySelectorAll('#views img')).map((im,i)=>im.src===data.images[p.views[i].path]),
      yaw:p.views.map(v=>v.yaw_deg),frame:document.getElementById('frame').textContent,expected:c.checkpoint_frame};
   });
   assert(values.original);assert(values.views.every(Boolean));assert.deepEqual(values.yaw,[0,45,90,135,180,225,270,315]);
   assert(values.frame.includes('F'+String(values.expected).padStart(4,'0')));
   for(let j=0;j<8;j++){
    await page.locator('#views button').nth(j).click();
    await page.waitForFunction(()=>document.getElementById('large').complete&&document.getElementById('large').naturalWidth===640);
    assert.equal(await page.locator('#large').getAttribute('src'),await page.locator('#views img').nth(j).getAttribute('src'));
    await page.locator('#close').click();result.zoom_checks++;
   }
   result.cases++;result.original_frame_checks++;result.panorama_image_checks+=8;
  }
  await page.locator('#case').selectOption('sample_01');
  await page.screenshot({path:file.replace('.html','.preview.png'),fullPage:true});
  await page.setViewportSize({width:420,height:900});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  assert.deepEqual(result.errors,[]);assert.deepEqual(result.network,[]);result.passed=true;
 }finally{
  fs.writeFileSync(file.replace('.html','.browser_check.json'),JSON.stringify(result,null,2)+'\n');
  await browser.close();
 }
 console.log(JSON.stringify(result));
})().catch(e=>{console.error(e);process.exitCode=1});
