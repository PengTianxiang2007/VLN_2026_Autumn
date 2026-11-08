/* CPU-only browser checks of the final exported artifact; no inference. */
const fs=require('fs'),path=require('path'),assert=require('assert');
const env=JSON.parse(fs.readFileSync('/tmp/vln-oracle-ui-browser-direct-20261104/browser_env.json','utf8'));
Object.assign(process.env,{LD_LIBRARY_PATH:env.LD_LIBRARY_PATH,FONTCONFIG_FILE:env.FONTCONFIG_FILE});
const {chromium}=require(env.PLAYWRIGHT_MODULE);
(async()=>{
 const file=path.resolve(process.argv[2]),out=path.dirname(file),browser=await chromium.launch({executablePath:env.CHROMIUM_EXECUTABLE,headless:true,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']});
 const page=await browser.newPage({viewport:{width:1480,height:1100},acceptDownloads:true}),errors=[],requests=[],checks=[];
 page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url())});
 try{
  await page.goto('file://'+file,{waitUntil:'load',timeout:120000});await page.evaluate(()=>document.fonts.ready);
  const data=await page.evaluate(()=>JSON.parse(document.getElementById('data').textContent));assert.equal(data.cases.length,10);
  for(let i=0;i<10;i++){
   await page.selectOption('#case-select',String(i));const c=data.cases[i],inv=c.calls['1']?.answer,choice=c.calls['2']?.answer;
   assert.equal(await page.locator('.view').count(),8);assert.equal(await page.locator('.branch').count(),inv?.branches?.length||0);
   const banner=await page.locator('#decision').innerText();assert(banner.includes(choice?.selected_branch_id?'选择：'+choice.selected_branch_id:'选择：未选择'));
   for(const im of c.images.filter(x=>x.phase==='crossing_panorama')){
    await page.locator(`.view[data-view="${im.id}"]`).click();await page.waitForFunction(()=>{const im=document.getElementById('main-image');return im.complete&&im.naturalWidth===640});
    const shown=await page.locator('#main-image').getAttribute('src');assert.equal(shown,data.images[im.image_key]);
   }
   for(const b of inv?.branches||[]){
    await page.locator(`.branch[data-branch="${b.id}"]`).click();assert((await page.locator('#active-branch').innerText()).includes(b.id));
    assert.equal(await page.locator('.view.cited').count(),b.panorama_view_ids.length);
    const id=await page.locator('.view.active').getAttribute('data-view');assert.equal(id,b.panorama_view_ids[0]);
   }
   await page.locator('#main-image').click();assert(await page.locator('#zoom').isVisible());await page.locator('#close-zoom').click();
   await page.evaluate(()=>document.getElementById('history').open=true);
   for(let n=0;n<8;n++){
    await page.locator('#rgb-slider').evaluate((el,n)=>{el.value=n;el.dispatchEvent(new Event('input',{bubbles:true}))},n);
    assert.equal(await page.locator('#map-slider').inputValue(),String(n));
    const im=c.images.filter(x=>x.phase!=='crossing_panorama')[n];assert.equal(await page.locator('#history-image').getAttribute('src'),data.images[im.image_key]);
   }
   await page.locator('#map-slider').evaluate(el=>{el.value=2;el.dispatchEvent(new Event('input',{bubbles:true}))});assert.equal(await page.locator('#rgb-slider').inputValue(),'2');
   await page.evaluate(()=>document.getElementById('history').open=false);
   await page.waitForTimeout(80);const pixels=await page.locator('#map').evaluate(cv=>{const d=cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;let n=0;for(let j=0;j<d.length;j+=4)if(d[j]<190&&d[j+1]<190&&d[j+2]<190)n++;return n});assert(pixels>1000,'Floorplan missing');
   await page.locator('#language').click();assert.equal(await page.locator('#task').innerText(),c.instruction);await page.locator('#language').click();assert.equal(await page.locator('#task').innerText(),c.translation.instruction_zh);
   checks.push({sample_id:c.sample_id,panoramas:8,branches:inv?.branches?.length||0,selected:choice?.selected_branch_id||null,history:8,map_dark_pixels:pixels});
  }
  await page.selectOption('#case-select','0');await page.screenshot({path:path.join(out,'preview_desktop.png'),fullPage:true});
  const abstain=data.cases.findIndex(c=>c.calls['2']?.answer?.status==='insufficient_evidence');
  if(abstain>=0){await page.selectOption('#case-select',String(abstain));await page.screenshot({path:path.join(out,'preview_abstention.png'),fullPage:true})}
  await page.selectOption('#case-select','0');await page.locator('#review-note').fill('浏览器验证：导出后清空此测试意见');
  const dl=page.waitForEvent('download');await page.locator('#export-review').click();const downloaded=await dl;const payload=JSON.parse(fs.readFileSync(await downloaded.path(),'utf8'));assert.equal(payload.cases.length,10);
  await page.locator('#review-note').fill('');await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'preview_mobile.png'),fullPage:true});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),'Horizontal overflow');assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
  const result={passed:true,cases:checks,external_network_requests:requests,browser_errors:errors,review_export_cases:10,checked_at:new Date().toISOString()};fs.writeFileSync(path.join(out,'browser_check.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
