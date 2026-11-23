const assert=require('node:assert/strict'), fs=require('node:fs'), path=require('node:path'), {pathToFileURL}=require('node:url');
const deps=process.env.ORACLE_BROWSER_ROOT || '/tmp/oracle-distance-browser-20261115/node_modules';
const snapshot=JSON.parse(fs.readFileSync(path.join(__dirname,'snapshot.json'),'utf8'));
(async()=>{
 const browser=await require(deps+'/playwright-core').chromium.launch({executablePath:await require(deps+'/@sparticuz/chromium').executablePath(),args:['--no-sandbox','--no-zygote','--disable-gpu','--allow-file-access-from-files']});
 try {
  const page=await browser.newPage(); const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.resolve(snapshot.files.online.export)).href);
  await page.waitForFunction(()=>window.JEV_LAB && document.querySelector('#rgb').naturalWidth);
  const result=await page.evaluate(async source=>{
   const ds=$('deepseekDeviation'), qwen=$('guardOverlay');
   if(ds.checked||qwen.checked||ds.parentElement.textContent.trim()!=='DeepSeek偏航识别')throw Error('Checkbox defaults or label');
   const charts=[$('jevMap'),$('scorePlot')];
   const image=()=>charts.map(canvas=>canvas.toDataURL());
   let deepseek=0, qwenCount=0, both=0;
   function differs(a,b,expected,description) {
    if(a.some((s,j)=>(s!==b[j])!==expected))throw Error(c().episode_id+' '+description);
   }
   for(let i=0;i<B.cases.length;i++) {
    JEV_LAB.select(i);await new Promise(ok=>mapImage(c().scene,ok));
    const eid=c().episode_id, dsValue=source.deepseek[eid], qwenValue=source.qwen[eid];
    if(JSON.stringify(dsValue)!==JSON.stringify(B.deepseekReviews[eid]))throw Error('DeepSeek data mismatch');
    if(i<29 && !qwenValue)throw Error('Missing Qwen comparison');
    const d=Boolean(dsValue?.interval),q=Boolean(qwenValue?.interval);
    const plain=image();
    ds.click();const dOnly=image();differs(dOnly,plain,d,'DeepSeek only');
    qwen.click();const joint=image();differs(joint,dOnly,q,'Qwen while DeepSeek on');
    ds.click();const qOnly=image();differs(qOnly,plain,q,'Qwen only');differs(joint,qOnly,d,'DeepSeek while Qwen on');
    qwen.click();differs(image(),plain,false,'Restore');
    if(c().terminal_node.index!==c().frames.length-1)throw Error('Missing terminal');
    deepseek+=d;qwenCount+=q;both+=d&&q;
   }
   $('language').value='en';$('language').dispatchEvent(new Event('change'));
   if(!ds.parentElement.textContent.includes('DeepSeek deviation'))throw Error('English UI');
   return {cases:53,reviewed:Object.keys(source.deepseek).length,deepseek,qwen:qwenCount,both,restores_both:true};
  },snapshot.layers);
  assert.equal(result.reviewed,29);assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(__dirname,'browser_marks.json'),JSON.stringify({...result,errors},null,2)+'\n');console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
