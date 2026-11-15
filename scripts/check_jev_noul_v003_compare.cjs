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
    const page=await browser.newPage({viewport:{width:1480,height:1050},acceptDownloads:true}),errors=[],remote=[];
    page.on('pageerror',error=>errors.push(String(error)));
    page.on('request',request=>{if(/^https?:/.test(request.url()))remote.push(request.url())});
    await page.goto(pathToFileURL(file).href,{waitUntil:'load',timeout:120000});
    await page.waitForFunction(()=>window.JEV_VERSION_COMPARE);
    await page.evaluate(()=>document.fonts.ready);
    await page.locator('#rgb').evaluate(image=>image.decode());
    const counts=await page.evaluate(()=>{
      const api=window.JEV_VERSION_COMPARE,b=api.bundle;
      let frames=0,previous=0,current=0;
      for(let i=0;i<api.cases.length;i++){
        api.select(i);const item=api.cases[i];frames+=item.frames.length;
        for(const frame of item.frames){
          if(api.previousValue(frame)!==null)previous++;
          if(api.newValue(frame)!==null)current++;
          if(!b.images[frame.image]?.startsWith('data:image/'))throw Error('Missing image');
        }
        for(const frame of [0,Math.floor(item.frames.length/2),item.frames.length-1]){
          api.seek(frame);
          if(api.state().frame!==frame)throw Error('State mismatch');
          for(const id of ['frame','imageFrame'])if(Number(document.getElementById(id).value)!==frame)throw Error('Slider mismatch');
        }
      }
      return {cases:api.cases.length,frames,previous,current,valid:b.summary.valid,total:b.summary.total,framesDeclared:b.summary.replay_frames};
    });
    const expectedCounts=await page.evaluate(()=>({cases:window.JEV_VERSION_COMPARE.cases.length,frames:window.JEV_VERSION_COMPARE.bundle.summary.replay_frames,total:window.JEV_VERSION_COMPARE.bundle.summary.total}));
    assert.deepEqual(counts,{
      cases:expectedCounts.cases,frames:expectedCounts.frames,
      previous:expectedCounts.total,current:expectedCounts.total,
      valid:expectedCounts.total,total:expectedCounts.total,
      framesDeclared:expectedCounts.frames
    });
    const mapDifference=await page.evaluate(()=>{
      const left=document.getElementById('previousMap'),right=document.getElementById('newMap');
      const a=left.getContext('2d').getImageData(0,0,left.width,left.height).data,b=right.getContext('2d').getImageData(0,0,right.width,right.height).data;
      let n=0;for(let i=0;i<a.length;i+=16)if(a[i]!==b[i]||a[i+1]!==b[i+1]||a[i+2]!==b[i+2])n++;
      if(!n)throw Error('Maps identical');return n;
    });
    const routeOnly=await page.evaluate(async()=>{
      const arcs=[],prototype=CanvasRenderingContext2D.prototype,original=prototype.arc;
      prototype.arc=function(...args){arcs.push({id:this.canvas.id,args});return original.apply(this,args)};
      window.JEV_VERSION_COMPARE.draw();await new Promise(resolve=>setTimeout(resolve,200));prototype.arc=original;
      const routeArcs=arcs.filter(row=>['previousMap','newMap'].includes(row.id));
      if(routeArcs.length!==2)throw Error('Expected two robot markers, got '+routeArcs.length);
      return routeArcs.length;
    });
    const prompts=await page.evaluate(()=>({v2:document.getElementById('v002Prompt').textContent,v3:document.getElementById('v003Prompt').textContent,v3zh:document.getElementById('v003PromptZh').textContent}));
    assert(!/\bv1\b|original v1|最初 v1/i.test(prompts.v2+' '+prompts.v3+' '+prompts.v3zh));
    assert(prompts.v3.includes('5 future action steps'));
    assert(prompts.v3.includes('at most 7 steps'));
    assert(prompts.v3zh.includes('回退点是指'));
    await page.selectOption('#language','en');
    assert((await page.locator('#runInfo').textContent()).includes(`${expectedCounts.cases} trajectories`));
    assert((await page.locator('#runInfo').textContent()).includes(`${expectedCounts.total}/${expectedCounts.total} valid observations`));
    await page.selectOption('#language','zh');
    assert((await page.locator('#runInfo').textContent()).includes(`${expectedCounts.cases}条轨迹`));
    assert((await page.locator('#runInfo').textContent()).includes(`${expectedCounts.total}/${expectedCounts.total}个有效观测`));
    await page.locator('#note').fill('自动浏览器检查：v002与v003同帧概率');
    await page.selectOption('#category','both_ok');
    const downloadEvent=page.waitForEvent('download');await page.locator('#export').click();const download=await downloadEvent;
    const notes=path.join(out,'browser_notes_test.json');await download.saveAs(notes);
    assert.equal(JSON.parse(fs.readFileSync(notes)).notes.length,1);await page.evaluate(()=>localStorage.clear());
    await page.screenshot({path:path.join(out,'browser_desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});await page.waitForTimeout(200);
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
    await page.screenshot({path:path.join(out,'browser_mobile.png'),fullPage:true});
    assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
    const result={passed:true,...counts,dual_maps:true,dual_sliders:true,case_switch:true,route_only:true,robotMarkers:routeOnly,mapDifference,bilingual:true,prompt_self_contained:true,review_export:true,mobile:true,external_requests:0,page_errors:0};
    fs.writeFileSync(path.join(out,'browser_verification.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
  }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
