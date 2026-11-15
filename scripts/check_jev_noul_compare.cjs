'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert');
const {pathToFileURL}=require('url');
const env=JSON.parse(fs.readFileSync('/tmp/vln-oracle-ui-browser-direct-20261104/browser_env.json'));
Object.assign(process.env,{LD_LIBRARY_PATH:env.LD_LIBRARY_PATH,FONTCONFIG_FILE:env.FONTCONFIG_FILE});
const {chromium}=require(env.PLAYWRIGHT_MODULE);

(async()=>{
  const file=path.resolve(process.argv[2]),out=path.dirname(file);
  const browser=await chromium.launch({
    executablePath:env.CHROMIUM_EXECUTABLE,
    headless:true,
    args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']
  });
  try{
    const page=await browser.newPage({viewport:{width:1560,height:1150},acceptDownloads:true});
    const errors=[],remote=[];
    page.on('pageerror',error=>errors.push(String(error)));
    page.on('request',request=>{if(/^https?:/.test(request.url()))remote.push(request.url())});
    await page.goto(pathToFileURL(file).href,{waitUntil:'load',timeout:120000});
    await page.waitForFunction(()=>window.JEV_COMPARE);
    await page.evaluate(()=>document.fonts.ready);
    await page.locator('#rgb').evaluate(image=>image.decode());

    const counts=await page.evaluate(()=>{
      const api=window.JEV_COMPARE,bundle=api.bundle;
      let frames=0,qwen=0,jev=0,history=0;
      for(let i=0;i<bundle.cases.length;i++){
        api.select(i);
        const current=bundle.cases[i];
        for(const frame of current.frames){
          frames++;
          if(api.qwen(frame)!==null)qwen++;
          if(api.jev(frame)!==null){
            jev++;
            if(frame.jev.image_frames.length<1||frame.jev.image_frames.length>3)throw Error('Invalid history length');
            const expected=Array.from({length:frame.jev.image_frames.length},(_,n)=>Math.max(0,frame.frame-2)+n);
            if(frame.jev.image_frames.join(',')!==expected.join(','))throw Error('Non-causal images');
            history++;
          }
          if(!bundle.images[frame.image]?.startsWith('data:image/'))throw Error('Missing RGB payload');
        }
        for(const frameIndex of [0,Math.floor(current.frames.length/2),current.frames.length-1]){
          api.seek(frameIndex);
          if(Number(document.getElementById('frame').value)!==frameIndex)throw Error('Map slider mismatch');
          if(Number(document.getElementById('imageFrame').value)!==frameIndex)throw Error('Image slider mismatch');
          if(api.state().frame!==frameIndex)throw Error('State frame mismatch');
        }
      }
      api.select(0);
      return {cases:bundle.cases.length,frames,qwen,jev,history};
    });
    const expected=await page.evaluate(()=>({
      cases:window.JEV_COMPARE.bundle.cases.length,
      frames:window.JEV_COMPARE.bundle.summary.replay_frames,
      calls:window.JEV_COMPARE.bundle.summary.expected_calls
    }));
    assert.deepEqual(counts,{
      cases:expected.cases,frames:expected.frames,
      qwen:expected.calls,jev:expected.calls,history:expected.calls
    });
    assert.equal(await page.locator('#eventList').count(),0);
    assert.equal(await page.locator('#jevList').count(),0);

    const colors=await page.evaluate(()=>{
      const api=window.JEV_COMPARE;
      const luminance=color=>{
        if(color.startsWith('#')){
          const values=[1,3,5].map(i=>parseInt(color.slice(i,i+2),16));
          return .2126*values[0]+.7152*values[1]+.0722*values[2];
        }
        const values=color.match(/\d+/g).slice(0,3).map(Number);
        return .2126*values[0]+.7152*values[1]+.0722*values[2];
      };
      const q1=api.qwenColor(1),q5=api.qwenColor(5),p0=api.jevColor(0),p1=api.jevColor(1);
      if(!(luminance(q5)<luminance(q1)))throw Error('Qwen palette is not darker at higher score');
      if(!(luminance(p1)<luminance(p0)))throw Error('JEV palette is not darker at higher probability');
      return {q1,q5,p0,p1,qDelta:luminance(q1)-luminance(q5),pDelta:luminance(p0)-luminance(p1)};
    });

    const mapDifference=await page.evaluate(()=>{
      const left=document.getElementById('qwenMap'),right=document.getElementById('jevMap');
      const a=left.getContext('2d').getImageData(0,0,left.width,left.height).data;
      const b=right.getContext('2d').getImageData(0,0,right.width,right.height).data;
      let differing=0;
      for(let i=0;i<a.length;i+=16)if(a[i]!==b[i]||a[i+1]!==b[i+1]||a[i+2]!==b[i+2])differing++;
      if(!differing)throw Error('Qwen and JEV maps are visually identical');
      return differing;
    });
    const routeOnly=await page.evaluate(async()=>{
      const arcs=[],prototype=CanvasRenderingContext2D.prototype,original=prototype.arc;
      prototype.arc=function(...args){arcs.push({id:this.canvas.id,args});return original.apply(this,args)};
      window.JEV_COMPARE.draw();
      await new Promise(resolve=>setTimeout(resolve,250));
      prototype.arc=original;
      const routeArcs=arcs.filter(row=>['qwenMap','jevMap'].includes(row.id));
      if(routeArcs.length!==2)throw Error('Expected exactly two robot markers, got '+routeArcs.length);
      if(routeArcs.some(row=>Math.abs(row.args[2]-7)>0.001))throw Error('Unexpected marker radius');
      return {robotMarkers:routeArcs.length};
    });
    const filterChecks=await page.evaluate(async()=>{
      const api=window.JEV_COMPARE;
      for(const id of ['showQwenLine','showRawJev'])if(!document.getElementById(id).checked)throw Error('Original line unexpectedly hidden by default');
      for(const id of ['filterGaussian','filterEma','filterMoving','filterProminence','filterStreaming'])if(document.getElementById(id).checked)throw Error('Filter unexpectedly enabled by default');
      if(Number(document.getElementById('filterWindow').value)!==7)throw Error('Unexpected default filter window');
      if(Number(document.getElementById('streamDelay').value)!==5)throw Error('Unexpected default stream delay');
      const values=[0,0,0,1,0,0,0];
      const gaussian=api.filterSeries('gaussian',values,7);
      const ema=api.filterSeries('ema',values,7);
      const moving=api.filterSeries('movingAverage',values,7);
      const prominence=api.relativeProminence(values,7);
      const base=[.1,.2,.1,.8,.2,.1,.5,.2,.1,.3,.2,.1,.2,.4,.1,.3,.2,.1,.6,.2,.1,.2];
      const extended=base.concat([.9,.8,.7,.6,.5,.4]);
      const streamed=api.streamingProminence(base,7,5),streamedExtended=api.streamingProminence(extended,7,5),causal=api.streamingProminence(base,7,0);
      const actualValues=api.bundle.cases[0].frames.map(api.jev);
      const sampledNodes=api.sampleStreamingNodes(api.streamingProminence(actualValues,7,5),7);
      if(!(gaussian[3]<1&&gaussian[3]>0))throw Error('Gaussian did not smooth spike');
      if(!(ema[3]<1&&ema[3]>0))throw Error('EMA did not smooth spike');
      if(Math.abs(moving[3]-1/7)>1e-9)throw Error('Moving average result mismatch');
      if(!(prominence[3]>0&&prominence[3]===Math.max(...prominence)))throw Error('Prominence did not isolate spike');
      for(let i=0;i<base.length-5;i++)if(Math.abs(streamed[i]-streamedExtended[i])>1e-12)throw Error('Streaming output changes after bounded delay');
      if(streamed.every((value,i)=>Math.abs(value-causal[i])<1e-12))throw Error('Streaming delay had no effect');
      if(!sampledNodes.length)throw Error('Streaming sampler returned no nodes');
      for(let i=1;i<sampledNodes.length;i++)if(sampledNodes[i].index-sampledNodes[i-1].index<3)throw Error('Sampling points violate minimum distance');
      const beforeChart=document.getElementById('scorePlot').toDataURL();
      const beforeMap=document.getElementById('jevMap').toDataURL();
      document.getElementById('showQwenLine').checked=false;api.drawPlot();
      const hiddenQwen=document.getElementById('scorePlot').toDataURL();
      if(hiddenQwen===beforeChart)throw Error('Original Qwen line toggle had no effect');
      document.getElementById('showQwenLine').checked=true;
      document.getElementById('showRawJev').checked=false;api.drawPlot();
      const hiddenJev=document.getElementById('scorePlot').toDataURL();
      if(hiddenJev===beforeChart)throw Error('Original JEV line toggle had no effect');
      document.getElementById('showRawJev').checked=true;api.drawPlot();
      document.getElementById('filterGaussian').checked=true;
      document.getElementById('filterEma').checked=true;
      document.getElementById('filterMoving').checked=true;
      document.getElementById('filterProminence').checked=true;
      document.getElementById('filterStreaming').checked=true;
      const slider=document.getElementById('filterWindow');slider.value=11;slider.dispatchEvent(new Event('input'));
      const delay=document.getElementById('streamDelay');delay.value=5;delay.dispatchEvent(new Event('input'));api.drawPlot();
      await new Promise(resolve=>setTimeout(resolve,150));
      if(document.getElementById('filterWindowValue').textContent!=='11')throw Error('Window label not updated');
      if(!document.getElementById('sampleSummary').textContent.includes('F'))throw Error('Sampled x-axis nodes not summarized');
      const afterChart=document.getElementById('scorePlot').toDataURL();
      const afterMap=document.getElementById('jevMap').toDataURL();
      if(beforeChart===afterChart)throw Error('Filtered chart did not change');
      if(beforeMap!==afterMap)throw Error('Filter unexpectedly changed map');
      if(document.getElementById('showSampleMapPoints').checked)throw Error('Map sample points unexpectedly enabled by default');
      const mapWithoutSamples=document.getElementById('jevMap').toDataURL();
      document.getElementById('showSampleMapPoints').checked=true;api.draw();await new Promise(resolve=>setTimeout(resolve,150));
      const mapWithSamples=document.getElementById('jevMap').toDataURL();
      if(mapWithoutSamples===mapWithSamples)throw Error('Map sample-point toggle had no effect');
      document.getElementById('showSampleMapPoints').checked=false;api.draw();
      return {filters_smoothed:true,prominence_peak:true,streaming_prefix_stable:true,streaming_delay:5,xaxis_sampling:true,sampled_nodes:sampledNodes.length,map_sample_toggle:true,original_lines_toggle:true,chart_only:true,gaussianPeak:gaussian[3],emaPeak:ema[3],movingPeak:moving[3],prominencePeak:prominence[3],window:11};
    });
    const targetFirstPeak=await page.evaluate(async()=>{
      const api=window.JEV_COMPARE,b=api.bundle,ci=b.cases.findIndex(c=>c.episode_id==='kujiale_0207_41_0');
      api.select(ci);
      const windowSlider=document.getElementById('filterWindow');windowSlider.value=5;windowSlider.dispatchEvent(new Event('input'));
      document.getElementById('filterStreaming').checked=true;
      const delay=document.getElementById('streamDelay');delay.value=5;delay.dispatchEvent(new Event('input'));
      api.draw();await new Promise(resolve=>setTimeout(resolve,150));
      const nodes=api.samplingState().nodes,caseData=b.cases[ci];
      const frames=nodes.map(node=>caseData.frames[node.index].frame);
      if(!frames.includes(3))throw Error('First peak F3 was not sampled');
      return {episode:caseData.episode_id,nodeFrames:frames};
    });

    const prompt=await page.evaluate(()=>({en:document.getElementById('promptEnglish').textContent,zh:document.getElementById('promptChinese').textContent}));
    assert(!/\bv1\b|original v1|最初 v1/i.test(prompt.en+' '+prompt.zh));
    assert(prompt.en.includes('fallback point'));
    assert(prompt.zh.includes('回退点'));

    await page.selectOption('#language','en');
    assert.equal(await page.locator('h2').first().textContent(),'Trajectories');
    assert((await page.locator('#instruction').textContent()).includes('Original task instruction'));
    assert((await page.locator('#runInfo').textContent()).includes(`${expected.cases} trajectories`));
    await page.selectOption('#language','zh');
    assert.equal(await page.locator('h2').first().textContent(),'轨迹');
    assert((await page.locator('#instruction').textContent()).includes('原任务指令'));
    assert((await page.locator('#runInfo').textContent()).includes(`${expected.cases}条轨迹`));

    await page.locator('#note').fill('自动浏览器检查：JEV与Qwen同帧对照');
    await page.selectOption('#category','both_ok');
    const downloadEvent=page.waitForEvent('download');
    await page.locator('#export').click();
    const download=await downloadEvent;
    const notesPath=path.join(out,'browser_notes_test.json');
    await download.saveAs(notesPath);
    assert.equal(JSON.parse(fs.readFileSync(notesPath)).notes.length,1);
    await page.evaluate(()=>localStorage.clear());

    await page.evaluate(()=>{
      document.getElementById('filterStreaming').checked=true;
      document.getElementById('showSampleMapPoints').checked=true;
      window.JEV_COMPARE.draw();
    });
    await page.waitForTimeout(200);
    await page.screenshot({path:path.join(out,'browser_desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.waitForTimeout(200);
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
    await page.screenshot({path:path.join(out,'browser_mobile.png'),fullPage:true});
    assert.deepEqual(errors,[]);
    assert.deepEqual(remote,[]);
    const result={
      passed:true,...counts,dual_sliders:true,dual_maps:true,path_color_intensity:true,
      route_only:true,...routeOnly,
      ...filterChecks,...targetFirstPeak,bilingual:true,prompt_self_contained:true,review_export:true,mobile:true,
      external_requests:0,page_errors:0,colors,mapDifference
    };
    fs.writeFileSync(path.join(out,'browser_verification.json'),JSON.stringify(result,null,2));
    console.log(JSON.stringify(result));
  }finally{
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exit(1)});
