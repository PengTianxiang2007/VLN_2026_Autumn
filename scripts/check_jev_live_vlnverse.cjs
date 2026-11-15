'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert');
const {pathToFileURL}=require('url');
const env=JSON.parse(fs.readFileSync('/tmp/vln-oracle-ui-browser-direct-20261104/browser_env.json'));
Object.assign(process.env,{LD_LIBRARY_PATH:env.LD_LIBRARY_PATH,FONTCONFIG_FILE:env.FONTCONFIG_FILE});
const {chromium}=require(env.PLAYWRIGHT_MODULE);

(async()=>{
  const file=path.resolve(process.argv[2]),out=path.dirname(file);
  const browser=await chromium.launch({executablePath:env.CHROMIUM_EXECUTABLE,headless:true,
    args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
  try{
    const page=await browser.newPage({viewport:{width:1500,height:1100},acceptDownloads:true});
    const errors=[],remote=[];
    page.on('pageerror',e=>errors.push(String(e)));
    page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url())});
    await page.goto(pathToFileURL(file).href,{waitUntil:'load',timeout:180000});
    await page.waitForFunction(()=>window.JEV_LIVE,{timeout:180000});
    await page.locator('#rgb').evaluate(image=>image.decode());
    const counts=await page.evaluate(()=>{
      const b=window.JEV_LIVE.bundle;let frames=0,calls=0,history=0,nodes=0;
      for(let ci=0;ci<b.cases.length;ci++){
        const item=b.cases[ci];
        if(item.streaming.raw.length!==item.frames.length)throw Error('Raw length mismatch');
        if(item.streaming.filtered.length!==item.frames.length)throw Error('Filtered length mismatch');
        for(const row of item.frames){
          frames++;
          if(!b.images[row.image]?.startsWith('data:image/'))throw Error('Missing RGB payload');
          if(row.jev){calls++;history++;
            const ids=row.jev.image_frames;
            if(ids.length<1||ids.length>3)throw Error('Invalid history length');
            const expected=Array.from({length:ids.length},(_,n)=>Math.max(0,row.frame-2)+n);
            if(ids.join(',')!==expected.join(','))throw Error('Non-causal image history');
            if(row.jev.unresolved_step_lag<0||row.jev.unresolved_step_lag>5)throw Error('Invalid step lag');
          }
        }
        nodes+=item.streaming.nodes.length;
      }
      return {cases:b.cases.length,frames,calls,history,nodes,
        expectedFrames:b.summary.frames,expectedCalls:b.summary.valid_calls};
    });
    assert.deepEqual(counts,{cases:40,frames:2878,calls:2878,history:2878,nodes:215,
      expectedFrames:2878,expectedCalls:2878});
    const interactions=await page.evaluate(async()=>{
      const api=window.JEV_LIVE;
      if(!api.bundle.map?.image||!api.bundle.images[api.bundle.map.image]?.startsWith('data:image/png;base64,'))throw Error('Missing floorplan image');
      if(api.bundle.map.geometry.width<=0||api.bundle.map.geometry.height<=0)throw Error('Missing floorplan geometry');
      api.select(39);api.seek(api.bundle.cases[39].frames.length-1);
      if(Number(document.getElementById('frame').value)!==api.bundle.cases[39].frames.length-1)throw Error('Map slider mismatch');
      if(Number(document.getElementById('imageFrame').value)!==api.bundle.cases[39].frames.length-1)throw Error('Image slider mismatch');
      const plain=document.getElementById('map').toDataURL();
      await new Promise(r=>setTimeout(r,300));
      const canvas=document.getElementById('map'),pixels=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
      let nonBlank=0;for(let i=0;i<pixels.length;i+=16)if(pixels[i]<245||pixels[i+1]<245||pixels[i+2]<245)nonBlank++;
      if(nonBlank<500)throw Error('Floorplan canvas is blank');
      document.getElementById('showMapNodes').checked=true;api.draw();
      await new Promise(r=>setTimeout(r,150));
      const withNodes=document.getElementById('map').toDataURL();
      if(plain===withNodes)throw Error('Map node toggle had no effect');
      const summary=document.getElementById('sampleSummary').textContent;
      if(!summary.includes('S01'))throw Error('Sample summary missing nodes');
      return {mapNodeToggle:true,floorplanNonBlankPixels:nonBlank,summary};
    });
    await page.selectOption('#language','en');
    assert.equal(await page.locator('h2').first().textContent(),'Trajectories and live scores');
    assert((await page.locator('#instruction').textContent()).includes('English:'));
    assert((await page.locator('#instruction').textContent()).includes('中文：'));
    await page.selectOption('#language','zh');
    assert.equal(await page.locator('h2').first().textContent(),'轨迹与实时评分');
    assert((await page.locator('#instruction').textContent()).includes('English:'));
    const prompt=await page.evaluate(()=>({en:document.getElementById('promptEnglish').textContent,
      zh:document.getElementById('promptChinese').textContent}));
    assert(prompt.en.includes('fallback point'));
    assert(prompt.zh.includes('回退点'));
    await page.locator('#note').fill('自动浏览器检查');
    const downloadEvent=page.waitForEvent('download');
    await page.locator('#export').click();
    const download=await downloadEvent;
    const notePath=path.join(out,'browser_notes_test.json');
    await download.saveAs(notePath);
    assert.equal(JSON.parse(fs.readFileSync(notePath)).notes.length,1);
    await page.evaluate(()=>localStorage.clear());
    await page.screenshot({path:path.join(out,'browser_desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.waitForTimeout(200);
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
    await page.screenshot({path:path.join(out,'browser_mobile.png'),fullPage:true});
    assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
    const result={passed:true,...counts,dualLanguage:true,fullTranslation:true,
      promptBilingual:true,reviewExport:true,mobile:true,externalRequests:0,
      pageErrors:0,...interactions};
    fs.writeFileSync(path.join(out,'browser_verification.json'),JSON.stringify(result,null,2));
    console.log(JSON.stringify(result));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
