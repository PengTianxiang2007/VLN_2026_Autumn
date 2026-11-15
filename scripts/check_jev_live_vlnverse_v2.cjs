'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert');
const {pathToFileURL}=require('url');
const env=JSON.parse(fs.readFileSync('/tmp/vln-oracle-ui-browser-direct-20261104/browser_env.json'));
Object.assign(process.env,{LD_LIBRARY_PATH:env.LD_LIBRARY_PATH,FONTCONFIG_FILE:env.FONTCONFIG_FILE});
const {chromium}=require(env.PLAYWRIGHT_MODULE);
(async()=>{
  const file=path.resolve(process.argv[2]),out=path.dirname(file);
  const browser=await chromium.launch({executablePath:env.CHROMIUM_EXECUTABLE,headless:true,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
  try{
    const page=await browser.newPage({viewport:{width:1560,height:1100},acceptDownloads:true});
    const errors=[],remote=[];
    page.on('pageerror',e=>errors.push(String(e)));
    page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url())});
    await page.goto(pathToFileURL(file).href,{waitUntil:'load',timeout:180000});
    await page.waitForFunction(()=>window.JEV_LIVE_V2,{timeout:180000});
    await page.locator('#rgb').evaluate(image=>image.decode());
    const counts=await page.evaluate(()=>{
      const b=window.JEV_LIVE_V2.bundle;let frames=0,calls=0,nodes=0;
      if(!b.map?.image||!b.images[b.map.image]?.startsWith('data:image/png;base64,'))throw Error('Missing floorplan');
      for(const c of b.cases){if(c.streaming.raw.length!==c.frames.length)throw Error('Raw length mismatch');for(const f of c.frames){frames++;if(!b.images[f.image]?.startsWith('data:image/'))throw Error('Missing RGB');if(f.jev){calls++;if(f.jev.image_frames.length<1||f.jev.image_frames.length>3)throw Error('Invalid history');}}nodes+=c.streaming.nodes.length;}
      return {cases:b.cases.length,frames,calls,nodes};
    });
    assert.deepEqual(counts,{cases:40,frames:2878,calls:2878,nodes:215});
    const buttons=page.locator('#cases button');
    assert((await buttons.count())===40);
    const expected=await page.evaluate(()=>window.JEV_LIVE_V2.bundle.cases[9].episode_id);
    await buttons.nth(9).click();
    assert.equal(await page.locator('#episodeTitle').textContent(),expected);
    assert(await buttons.nth(9).evaluate(node=>node.classList.contains('active')));
    await page.waitForTimeout(300);
    const mapCheck=await page.evaluate(()=>{
      const raw=document.getElementById('rawMap'),stream=document.getElementById('streamMap');
      const a=raw.getContext('2d').getImageData(0,0,raw.width,raw.height).data,b=stream.getContext('2d').getImageData(0,0,stream.width,stream.height).data;
      let nonBlank=0,different=0;for(let i=0;i<a.length;i+=16){if(a[i]<245||a[i+1]<245||a[i+2]<245)nonBlank++;if(a[i]!==b[i]||a[i+1]!==b[i+1]||a[i+2]!==b[i+2])different++;}
      if(nonBlank<500)throw Error('Blank floorplan');if(!different)throw Error('Raw/stream maps identical');
      const before=stream.toDataURL();document.getElementById('showSampleMapPoints').checked=true;window.JEV_LIVE_V2.draw();return {nonBlank,different,before};
    });
    await page.waitForTimeout(150);
    assert.notEqual(await page.locator('#streamMap').evaluate(c=>c.toDataURL()),mapCheck.before);
    await page.locator('#frame').evaluate((slider)=>{slider.value=5;slider.dispatchEvent(new Event('input'))});
    assert.equal(await page.locator('#imageFrame').inputValue(),'5');
    await page.selectOption('#language','en');
    assert((await page.locator('#notice').textContent()).includes('floorplan'));
    assert((await page.locator('#instruction').textContent()).includes('English:'));
    await page.selectOption('#language','zh');
    assert((await page.locator('#instruction').textContent()).includes('中文：'));
    const prompt=await page.evaluate(()=>({en:document.getElementById('promptEnglish').textContent,zh:document.getElementById('promptChinese').textContent}));
    assert(prompt.en.includes('fallback point'));assert(prompt.zh.includes('回退点'));
    await page.locator('#note').fill('自动浏览器检查');
    const downloadEvent=page.waitForEvent('download');await page.locator('#export').click();const download=await downloadEvent;
    const notePath=path.join(out,'browser_notes_test.json');await download.saveAs(notePath);
    assert.equal(JSON.parse(fs.readFileSync(notePath)).notes.length,1);
    await page.evaluate(()=>localStorage.clear());
    await page.screenshot({path:path.join(out,'browser_desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});await page.waitForTimeout(200);
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
    await page.screenshot({path:path.join(out,'browser_mobile.png'),fullPage:true});
    assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
    const result={passed:true,...counts,caseClickSwitch:true,dualFloorplanMaps:true,rawStreamMapsDiffer:true,mapNodeToggle:true,floorplanNonBlankPixels:mapCheck.nonBlank,dualSliders:true,bilingual:true,promptBilingual:true,reviewExport:true,mobile:true,externalRequests:0,pageErrors:0};
    fs.writeFileSync(path.join(out,'browser_verification.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
