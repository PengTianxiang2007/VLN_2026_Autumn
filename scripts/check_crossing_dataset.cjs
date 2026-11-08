/* Verify the actual immutable offline viewer at every user-annotated point. */
const fs=require('fs'),path=require('path'),assert=require('assert');
const env=JSON.parse(fs.readFileSync('/tmp/vln-oracle-ui-browser-direct-20261104/browser_env.json','utf8'));
Object.assign(process.env,{LD_LIBRARY_PATH:env.LD_LIBRARY_PATH,FONTCONFIG_FILE:env.FONTCONFIG_FILE});
const {chromium}=require(env.PLAYWRIGHT_MODULE);
(async()=>{
 const file=path.resolve(process.argv[2]),out=path.dirname(path.dirname(file)),errors=[],network=[];
 const browser=await chromium.launch({executablePath:env.CHROMIUM_EXECUTABLE,headless:true,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1180}});page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url())});
  await page.goto('file://'+file,{waitUntil:'load',timeout:180000});await page.evaluate(()=>document.fonts.ready);
  const data=await page.evaluate(()=>{const d=JSON.parse(document.getElementById('data').textContent);return{summary:d.summary,cases:d.cases.map(c=>({id:c.episode_id,frames:c.frames.length,group:c.group,events:c.events.map(e=>({id:e.id,frame:e.frame,type:e.type}))}))}});
  assert.equal(data.cases.length,61);assert.equal(data.summary.crossing_events,128);let framesChecked=0,eventsChecked=0;
  async function settle(i,frame){await page.waitForFunction(({i,frame})=>{const $=id=>document.getElementById(id),d=JSON.parse($('data').textContent),c=d.cases[i];return $('loading').hidden&&$('rgb').complete&&$('rgb').naturalWidth===640&&$('rgb').dataset.episodeId===c.episode_id&&Number($('rgb').dataset.frame)===frame&&$('map').dataset.episodeId===c.episode_id&&Number($('map').dataset.frame)===frame},{i,frame})}
  async function check(i,n){const result=await page.evaluate(({i,n})=>{const $=id=>document.getElementById(id),d=JSON.parse($('data').textContent),c=d.cases[i],f=c.frames[n],images=JSON.parse($('media-'+c.episode_id).textContent),cv=$('map'),[x,y]=JSON.parse(cv.dataset.currentPixel);return{image:images[n]===$('rgb').src,sliders:[$('rgb-slider').value,$('map-slider').value],position:JSON.parse(cv.dataset.position),expected:f.position,pixel:[...cv.getContext('2d').getImageData(Math.round(x),Math.round(y),1,1).data],markers:Number(cv.dataset.markerCount),expectedMarkers:c.events.length,instruction:$('instruction').textContent===c.instruction_zh}}, {i,n});assert(result.image&&result.instruction);assert.deepEqual(result.sliders,[String(n),String(n)]);assert.deepEqual(result.position,result.expected);assert.deepEqual(result.pixel,[116,65,198,255]);assert.equal(result.markers,result.expectedMarkers);framesChecked++}
  for(let i=0;i<data.cases.length;i++){
   const c=data.cases[i];assert(c.events.length>0);await page.selectOption('#case-select',String(i));await settle(i,c.events[0].frame);assert.equal(await page.locator('.event').count(),c.events.length);
   for(const e of c.events){await page.locator('.event[data-id="'+e.id+'"]').click();await settle(i,e.frame);await check(i,e.frame);assert((await page.locator('.event[data-id="'+e.id+'"]').getAttribute('class')).includes('active'));eventsChecked++}
   for(const [j,n] of [...new Set([0,Math.floor(c.frames/2),c.frames-1])].entries()){await page.locator(j%2?'#map-slider':'#rgb-slider').evaluate((el,n)=>{el.value=String(n);el.dispatchEvent(new Event('input',{bubbles:true}))},n);await settle(i,n);await check(i,n)}
   if((i+1)%10===0)console.log(JSON.stringify({episodes_checked:i+1,total:61}));
  }
  await page.selectOption('#filter','failure');assert.equal(await page.locator('#case-select option').count(),34);await page.selectOption('#filter','success');assert.equal(await page.locator('#case-select option').count(),27);await page.selectOption('#filter','wrong');assert.equal(await page.locator('#case-select option').count(),data.summary.episodes_with_wrong_choice);
  await page.selectOption('#filter','all');await page.selectOption('#case-select','1');await settle(1,data.cases[1].events[0].frame);await page.screenshot({path:path.join(out,'preview_dataset.png'),fullPage:true});
  await page.click('#play');await page.waitForTimeout(650);await page.click('#play');const paused=await page.locator('#rgb-slider').inputValue();assert(Number(paused)>data.cases[1].events[0].frame);await page.waitForTimeout(350);assert.equal(await page.locator('#rgb-slider').inputValue(),paused);
  await page.click('#zoom-in');await page.click('#zoom-reset');assert.equal(await page.locator('#mark-crossing,#mark-error,#delete-selected,#save-html').count(),0);
  await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  assert.deepEqual(errors,[]);assert.deepEqual(network,[]);const result={passed:true,checked_at:new Date().toISOString(),episodes:61,human_events_checked:eventsChecked,frame_checks:framesChecked,both_sliders:true,positions_and_map_pixels_verified:true,chinese_instructions_verified:true,read_only:true,external_requests:network,browser_errors:errors};
  fs.writeFileSync(path.join(out,'browser_check.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
