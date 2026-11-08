'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert');
const {pathToFileURL}=require('url');
const env=JSON.parse(fs.readFileSync('/tmp/vln-oracle-ui-browser-direct-20261104/browser_env.json'));
Object.assign(process.env,{LD_LIBRARY_PATH:env.LD_LIBRARY_PATH,FONTCONFIG_FILE:env.FONTCONFIG_FILE});
const {chromium}=require(env.PLAYWRIGHT_MODULE);
(async()=>{
 const file=path.resolve(process.argv[2]),browser=await chromium.launch({executablePath:env.CHROMIUM_EXECUTABLE,headless:true,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
 try{
  const page=await browser.newPage({viewport:{width:1480,height:1100}}),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(pathToFileURL(file).href,{waitUntil:'load',timeout:120000});
  await page.waitForFunction(()=>window.CROSSING_LITE);
  await page.evaluate(()=>{const ctx=document.getElementById('map').getContext('2d'),original=ctx.arc;window.robotArc=null;ctx.arc=function(...args){window.robotArc=args;return original.apply(this,args)}});
  const groups=await page.evaluate(()=>['failure','success'].map(g=>window.CROSSING_LITE.bundle.cases.findIndex(c=>c.group===g)));
  let checks=0;
  for(const ci of groups){
   await page.evaluate(ci=>{window.robotArc=null;window.CROSSING_LITE.select(ci)},ci);
   await page.waitForFunction(()=>{window.CROSSING_LITE.draw();return !!window.robotArc});
   for(const full of [true,false])for(const ref of [false,true])for(const id of ['frame','imageFrame'])for(const where of [0,.5,1]){
    await page.evaluate(({ci,full,ref,id,where})=>{
     const a=window.CROSSING_LITE,c=a.bundle.cases[ci],frame=Math.round((c.frames.length-1)*where);
     document.getElementById('full').checked=full;document.getElementById('showReference').checked=ref;
     const slider=document.getElementById(id);slider.value=frame;slider.dispatchEvent(new Event('input'));
     const el=document.getElementById('map'),box=el.getBoundingClientRect(),g=a.bundle.maps[c.scene].geometry,scale=Math.min(box.width/g.width,box.height/g.height),pos=c.frames[frame].position;
     const x=(box.width-g.width*scale)/2+(pos[0]-g.low[0])/g.resolution*scale,y=(box.height-g.height*scale)/2+(g.high[1]-pos[1])/g.resolution*scale;
     if(Math.abs(window.robotArc[0]-x)>.01||Math.abs(window.robotArc[1]-y)>.01||window.robotArc[2]!==6)throw Error('Robot marker position mismatch');
     const pixel=el.getContext('2d').getImageData(Math.round(x*el.width/box.width),Math.round(y*el.height/box.height),1,1).data;
     if(Math.abs(pixel[0]-225)>3||Math.abs(pixel[1]-29)>3||Math.abs(pixel[2]-72)>3)throw Error('Robot dot not visible');
     for(const name of ['frame','imageFrame'])if(Number(document.getElementById(name).value)!==frame)throw Error('Slider mismatch');
    },{ci,full,ref,id,where});checks++;
   }
  }
  await page.screenshot({path:path.join(path.dirname(file),'robot_marker_browser.png')});assert.deepEqual(errors,[]);
  const result={passed:true,checks,groups:['failure','success'],both_sliders:true,reference_on_off:true,full_partial_route:true,projected_position_and_visible_pixel:true};
  fs.writeFileSync(path.join(path.dirname(file),'robot_marker_check.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
