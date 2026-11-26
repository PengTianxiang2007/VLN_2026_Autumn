'use strict';
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const root = process.env.ORACLE_BROWSER_ROOT || '/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium} = require(path.join(root,'playwright-core'));
const portable = require(path.join(root,'@sparticuz/chromium'));

(async()=>{
  const browser=await chromium.launch({executablePath:await portable.executablePath(),headless:true,
    args:['--no-sandbox','--no-zygote','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
  try {
    const page=await browser.newPage(), errors=[];
    page.on('pageerror', e=>errors.push(String(e)));
    await page.goto(pathToFileURL(path.resolve(process.argv[2])).href);
    const expected=process.argv[4]?.split(',');
    const results=await page.evaluate(async(expected)=>{
      if(lang!=='zh')throw Error('Default language');
      if(expected){
        const buttons=()=>Array.from($('cases').querySelectorAll('button'));
        const ids=()=>buttons().map(b=>b.textContent.split(' · ')[0]);
        if(JSON.stringify(ids())!==JSON.stringify(expected))throw Error('Sidebar order: '+ids());
        for(const group of ['alarmed','quiet','initOnly','all']){
          $('filters').value=group;$('filters').dispatchEvent(new Event('change'));
          const filtered=B.cases.filter(v=>group==='all'||v.group===group).map(v=>v.case_id);
          if(JSON.stringify(ids())!==JSON.stringify(filtered))throw Error('Sidebar filter '+group);
        }
      }
      const checks=[];
      for(let n=0;n<B.cases.length;n++){
        $('cases').querySelectorAll('button')[n].click();
        const v=c(), final=v.rounds.at(-1);
        if(expected && v.case_id!==expected[n])throw Error('Case selection: '+v.case_id);
        if(index!==final.b||document.querySelectorAll('#routeReviews [data-round]').length!==v.rounds.length)throw Error('Initial reviewed interval: '+v.case_id);
        if($('showAlarm').checked!==true||!$('mapLayers').contains($('showAlarm')))throw Error('Alarm overlay');
        const ref=v.frames[v.end], img=new Image();img.src=B.images[ref.image];await img.decode();
        if(ref.jev!==null||v.terminalReviewed!==final.terminal)throw Error('Terminal metadata');
        $('sample_active').checked=true;
        const layers=displayState().versions;
        if(layers.find(l=>l.version.id==='active').nodes.length!==v.samples.length||layers.find(l=>l.version.id==='Astra').nodes.length!==v.effective.length)throw Error('Map node sets');
        $('sample_active').checked=false;
        const proof=$('routeReviews').querySelector('[data-review-frame]');proof.click();
        if(+proof.dataset.reviewFrame!==index||+$('frame').value!==index||+$('imageFrame').value!==index)throw Error('Evidence seek');
        for(const l of ['en','zh']){
          $('language').value=l;$('language').onchange();
          if(!$('routeReviews').textContent.includes(final.answer.reason[l])||!$('instruction').textContent.includes(v['instruction_'+l]))throw Error('Bilingual round mapping');
        }
        seek(v.end);await $('rgb').decode();
        if($('rgb').getAttribute('src')!==B.images[ref.image]||row().frame!==v.end)throw Error('Terminal frame replay');
        $('showAlarm').click();$('showAlarm').click();
        checks.push({case:v.case_id,frames:v.frames.length,rounds:v.rounds.length,terminal_reviewed:v.terminalReviewed,alarm_interval:v.alarm?[final.a,final.b]:null});
      }
      return checks;
    },expected);
    assert.deepEqual(errors,[]);
    fs.writeFileSync(process.argv[3],JSON.stringify({results,errors},null,2)+'\n');
    console.log(results);
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
