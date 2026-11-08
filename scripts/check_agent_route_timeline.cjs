/* Check the actual offline artifact, including every recorded video frame. */
const fs=require('fs'),path=require('path'),assert=require('assert');
const env=JSON.parse(fs.readFileSync('/tmp/vln-oracle-ui-browser-direct-20261104/browser_env.json','utf8'));
Object.assign(process.env,{LD_LIBRARY_PATH:env.LD_LIBRARY_PATH,FONTCONFIG_FILE:env.FONTCONFIG_FILE});
const {chromium}=require(env.PLAYWRIGHT_MODULE);
(async()=>{
 const file=path.resolve(process.argv[2]),out=path.dirname(file),browser=await chromium.launch({executablePath:env.CHROMIUM_EXECUTABLE,headless:true,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']});
 const page=await browser.newPage({viewport:{width:1480,height:1100},acceptDownloads:true}),errors=[],network=[],results=[];
 page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url())});
 try{
  await page.goto('file://'+file,{waitUntil:'load',timeout:120000});await page.evaluate(()=>document.fonts.ready);
  const cases=await page.evaluate(()=>JSON.parse(document.getElementById('data').textContent).cases.map(c=>({id:c.sample_id,checkpoint:c.checkpoint_frame,length:c.frames.length,branches:c.calls[1].answer.branches.length,selected:c.calls[2].answer.selected_branch_id})));
  assert.equal(cases.length,10);
  for(let n=0;n<cases.length;n++){
   const c=cases[n];await page.selectOption('#case-select',String(n));
   await page.waitForFunction(c=>document.getElementById('rgb').dataset.sampleId===c.id&&Number(document.getElementById('rgb').dataset.frame)===c.checkpoint,c);
   assert.equal(await page.locator('.branch').count(),c.branches);assert.equal(await page.locator('.branch[data-selected="true"]').getAttribute('data-branch'),c.selected);
   const result=await page.evaluate(async n=>{
    const $=id=>document.getElementById(id),d=JSON.parse($('data').textContent),c=d.cases[n],g=d.maps[c.review.scene].geometry,cv=$('map');
    const pause=()=>new Promise(r=>requestAnimationFrame(r));
    async function settle(frame){const start=performance.now();while(!(Number($('rgb').dataset.frame)===frame&&Number(cv.dataset.frame)===frame&&$('rgb').complete&&$('rgb').naturalWidth===640)){if(performance.now()-start>8000)throw Error('Frame sync timeout '+c.sample_id+':'+frame);await pause()}await pause()}
    function check(frame){
     const row=c.frames[frame],rgb=$('rgb');if(rgb.src!==d.images[row.image_key])throw Error('Wrong RGB '+c.sample_id+':'+frame);
     if($('rgb-slider').value!==String(frame)||$('map-slider').value!==String(frame))throw Error('Slider disagreement');
     if(cv.dataset.prefixFrames!==String(frame+1)||cv.dataset.position!==JSON.stringify(row.position))throw Error('Map trajectory prefix mismatch');
     const s=Math.min(616/g.width,452/g.height),ox=(640-g.width*s)/2,oy=(480-g.height*s)/2,x=Math.round(ox+(row.position[0]-g.low[0])/g.resolution*s),y=Math.round(oy+(g.high[1]-row.position[1])/g.resolution*s);
     const pixel=[...cv.getContext('2d').getImageData(x,y,1,1).data];if(pixel[0]!==116||pixel[1]!==65||pixel[2]!==198)throw Error('Current-position marker wrong at '+c.sample_id+':'+frame+' '+pixel);
    }
    for(let frame=0;frame<c.frames.length;frame++){
     const slider=$(frame%2?'map-slider':'rgb-slider');slider.value=String(frame);slider.dispatchEvent(new Event('input',{bubbles:true}));await settle(frame);check(frame);
    }
    $('jump-crossing').click();await settle(c.checkpoint_frame);check(c.checkpoint_frame);
    const original=c.images.find(im=>im.frame===c.checkpoint_frame);if($('rgb').src!==d.images[original.sha256])throw Error('Crossing jump is not exact original PNG');
    const before=$('rgb').src;document.querySelector('.evidence-jump').click();await settle(Number(document.querySelector('.evidence-jump').dataset.frame));
    $('jump-crossing-detail').click();await settle(c.checkpoint_frame);if($('rgb').src!==before)throw Error('Detail Crossing jump mismatch');
    $('rgb-slider').value='0';$('rgb-slider').dispatchEvent(new Event('input',{bubbles:true}));await settle(0);
    $('language').click();if($('task').textContent!==c.instruction||$('rgb-slider').value!=='0')throw Error('Language switch changed progress');$('language').click();
    $('jump-crossing').click();await settle(c.checkpoint_frame);
    return {sample_id:c.sample_id,replay_frames:c.frames.length,all_frames_verified:true,crossing_frame:c.checkpoint_frame,crossing_png_exact:true,branches:c.calls[1].answer.branches.length,selected_branch:c.calls[2].answer.selected_branch_id};
   },n);results.push(result);
  }
  await page.selectOption('#case-select','0');await page.waitForFunction(()=>document.getElementById('rgb').dataset.sampleId==='sample_01');
  await page.locator('#play').click();await page.waitForTimeout(700);await page.locator('#jump-crossing').click();assert.equal(await page.locator('#play').innerText(),'▶ 播放');
  await page.waitForFunction(()=>document.getElementById('rgb-slider').value==='11');await page.waitForTimeout(350);assert.equal(await page.locator('#rgb-slider').inputValue(),'11');
  await page.screenshot({path:path.join(out,'preview_crossing.png'),fullPage:true});
  await page.locator('#rgb-slider').evaluate(el=>{el.value=25;el.dispatchEvent(new Event('input',{bubbles:true}))});await page.waitForFunction(()=>document.getElementById('map').dataset.frame==='25');await page.screenshot({path:path.join(out,'preview_replay.png'),fullPage:true});
  await page.locator('#rgb').click();assert(await page.locator('#zoom').isVisible());await page.locator('#close-zoom').click();
  await page.selectOption('#case-select','6');await page.waitForFunction(()=>document.getElementById('rgb').dataset.sampleId==='sample_07');
  assert((await page.locator('#decision').innerText()).includes('已经排除 B1，却又选择了它'));assert.equal(await page.locator('.branch.conflict').getAttribute('data-branch'),'B1');await page.screenshot({path:path.join(out,'preview_case07.png'),fullPage:true});
  await page.locator('#review-note').fill('浏览器测试意见，验证后清空');const dl=page.waitForEvent('download');await page.locator('#export-review').click();const saved=await dl;assert.equal(JSON.parse(fs.readFileSync(await saved.path(),'utf8')).cases.length,10);await page.locator('#review-note').fill('');
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'preview_mobile.png'),fullPage:true});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile overflow');
  assert.deepEqual(errors,[]);assert.deepEqual(network,[]);const result={passed:true,checked_at:new Date().toISOString(),cases:results,frames_checked:results.reduce((n,r)=>n+r.replay_frames,0),both_sliders:true,map_pixel_positions_checked:true,return_button_pauses_playback:true,retains_case07_conflict:true,external_requests:network,browser_errors:errors};
  fs.writeFileSync(path.join(out,'browser_check.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
