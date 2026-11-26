const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const root='/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium}=require(path.join(root,'playwright-core')), portable=require(path.join(root,'@sparticuz/chromium'));
(async()=>{
  const browser=await chromium.launch({executablePath:await portable.executablePath(),headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--no-zygote']});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:900}});
    const errors=[];page.on('pageerror',e=>errors.push(String(e)));
    await page.goto(pathToFileURL(path.resolve(process.argv[2])).href,{waitUntil:'domcontentloaded',timeout:15000});
    const facts=await page.evaluate(async()=>{
      if(lang!=='zh'||current().frame!==57||$('routeReviews').querySelectorAll('[data-round]').length!==5)throw Error('Initial alarm state');
      await raster.decode();
      const views=[0,25,45,57,N,N+1,stepIndex(50),stepIndex(54),last];
      for(const i of views){
        seek(i);await $('rgb').decode();
        if(+$('frame').value!==i||+$('imageFrame').value!==i||$('rgb').getAttribute('src')!==B.images[current().image])throw Error('Frame sync '+i);
      }
      const checkpoints=c().effective.map(n=>n.index);
      $('jevDetails').open=true;drawJev();
      $('jumpList').children[4].click();
      if(current().motion!==50||Math.abs(current().distance-.64563)>.00001)throw Error('50-move boundary');
      const selected=index;
      $('language').value='en';$('language').onchange();
      if(index!==selected||!$('routeReviews').textContent.includes(c().rounds.at(-1).answer.reason.en)||!$('instruction').textContent.includes(c().instruction_en)||!$('messages').textContent.includes(B.notes.at(-1).text[1]))throw Error('English mismatch');
      $('showAlarm').click();$('returnPath').click();$('returnPath').click();$('showAlarm').click();
      $('language').value='zh';$('language').onchange();
      if(index!==selected||!$('routeReviews').textContent.includes(c().rounds.at(-1).answer.reason.zh))throw Error('Chinese mismatch');
      $('routeReviews').querySelector('[data-review-frame="45"]').click();if(current().frame!==45)throw Error('Historical evidence jump');
      $('callList').children[1].click();if(!current().failed||!current().executed)throw Error('Executed error');
      $('callList').children[3].click();if(!current().failed||current().executed)throw Error('Rejected retry');
      $('jumpList').lastChild.click();if(current().motion!==55||Math.abs(current().distance-.53703)>.00001)throw Error('Cutoff');
      return {framesChecked:views.length,timelinePositions:last+1,calls:calls.length,movements:moves.length-1,historicalFrames:N,retained:checkpoints,languages:['zh','en'],cutoff:current().distance};
    });
    assert.deepEqual(errors,[]);fs.writeFileSync(process.argv[3],JSON.stringify({...facts,errors},null,2));console.log(facts);
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
