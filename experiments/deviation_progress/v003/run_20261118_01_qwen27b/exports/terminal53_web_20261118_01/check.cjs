const fs=require('node:fs'), path=require('node:path'), assert=require('node:assert/strict'), {pathToFileURL}=require('node:url');
const deps=process.env.ORACLE_BROWSER_ROOT || '/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium}=require(deps+'/playwright-core'), portable=require(deps+'/@sparticuz/chromium');
const json=p=>JSON.parse(fs.readFileSync(p,'utf8'));
(async()=>{
  const [html,run]=process.argv.slice(2);
  const truth=json(path.join(run,'retained_nodes_and_terminals.json'));
  const browser=await chromium.launch({executablePath:await portable.executablePath(),args:['--no-sandbox','--disable-gpu','--no-zygote','--allow-file-access-from-files']});
  try {
    const page=await browser.newPage(),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.addInitScript(()=>{
      window.terminalPaint={};
      const original=CanvasRenderingContext2D.prototype.fillText;
      CanvasRenderingContext2D.prototype.fillText=function(text,...args){
        if(text==='终点'||text==='END')window.terminalPaint[this.canvas.id]=text;
        return original.call(this,text,...args);
      };
    });
    await page.goto(pathToFileURL(path.resolve(html)).href);
    await page.waitForFunction(()=>window.JEV_LAB && document.getElementById('rgb').naturalWidth>0);
    const data=await page.evaluate(async (truth)=>{
      const stats={cases:0,frames:0,scored:0,raw:0,retained:0,terminal:0,marked:0};
      if($('guardOverlay').checked)throw Error('Deviation overlay initial state');
      for(let i=0;i<B.cases.length;i++){
        JEV_LAB.select(i);
        const eid=c().episode_id, effective=truth[eid], last=effective.at(-1);
        const check=(ok,msg)=>{if(!ok)throw Error(eid+' '+msg)};
        await new Promise(ok=>mapImage(c().scene,ok));
        const terminalFrame=c().frames[last.index];
        check(c().frames.length===last.index+1 && terminalFrame.jev===null,'terminal observation');
        check(c().frames.slice(0,-1).every(f=>jev(f)!==null),'action scores');
        const retained=JEV_LAB.displayState().versions[0].nodes;
        check(JSON.stringify(retained.map(n=>n.id))===JSON.stringify(effective.slice(0,-1).map(n=>n.source_id)),'retained node IDs');
        window.terminalPaint={};
        $('terminalStep').click();
        await $('rgb').decode();
        check(['frame','imageFrame'].every(k=>Number($(k).value)===last.index && Number($(k).max)===last.index),'both sliders at last step');
        check($('rgb').getAttribute('src')===B.images[terminalFrame.image] && $('rgb').naturalWidth>0,'terminal image');
        check(window.terminalPaint.jevMap==='终点' && window.terminalPaint.scorePlot==='终点','terminal on both canvases');
        check(!$('currentNodeStatus').hidden && $('currentNodeStatus').textContent.includes(last.id),'terminal ID');
        check($('jevValue').textContent.includes('无 JEV'),'terminal score');
        check(JEV_LAB.filterSession().cursor===last.index-1,'terminal excluded from filter');
        const baseline=['jevMap','scorePlot'].map(k=>$(k).toDataURL());
        $('guardOverlay').click();
        const hit=Boolean(B.deviationReviews[eid]?.length);
        check(['jevMap','scorePlot'].every((k,j)=>($(k).toDataURL()!==baseline[j])===hit),'deviation range');
        $('guardOverlay').click();
        check(['jevMap','scorePlot'].every((k,j)=>$(k).toDataURL()===baseline[j]),'restored overlay');
        $('nodeDeduplicationTop').click();
        const raw=JEV_LAB.displayState().versions[0].nodes;
        check(raw.length===D.cases[i].nodes.length,'raw node count');
        check(JEV_LAB.displayState().terminalNode.index===last.index && !$('currentNodeStatus').hidden,'terminal with raw nodes');
        $('nodeDeduplicationTop').click();
        stats.cases++;stats.frames+=c().frames.length;stats.scored+=last.index;stats.terminal++;
        stats.retained+=retained.length;stats.raw+=raw.length;stats.marked+=Number(hit);
      }
      $('language').value='en';$('language').dispatchEvent(new Event('change'));
      if(!window.terminalPaint.jevMap.includes('END')||!$('currentNodeStatus').textContent.includes('Terminal node'))throw Error('English terminal');
      return stats;
    },truth);
    assert.deepEqual(data,{cases:53,frames:4890,scored:4837,raw:494,retained:376,terminal:53,marked:19});
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(__dirname,'browser_marks.json'),JSON.stringify({...data,restores_both:true,errors},null,2)+'\n');
    console.log(data);
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1})
