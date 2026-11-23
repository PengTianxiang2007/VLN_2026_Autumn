const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const modules='/tmp/oracle-distance-browser-20261115/node_modules';
const {chromium}=require(path.join(modules,'playwright-core'));
const portable=require(path.join(modules,'@sparticuz/chromium'));
(async()=>{
  const browser=await chromium.launch({executablePath:await portable.executablePath(),args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--allow-file-access-from-files']});
  try{
    const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(pathToFileURL(path.resolve(process.argv[2])).href);
    const check=await page.evaluate(()=>{
      selectCase(1);
      const snapshot=()=>{
        const state=displayState(),v=state.versions[0];
        return {enabled:$('nodeDeduplication').checked,matched:!!v.dedupRecord,
          frames:v.nodes.map(n=>n.index),labels:v.nodes.map(n=>nodeLabel(n,v.version,1)),
          terminal:state.terminalNode.index};
      };
      const expected=B.reviewNodes[c().episode_id].filter(n=>!n.terminal_node).map(n=>n.index);
      const on=snapshot();
      $('nodeDeduplicationTop').click();const off=snapshot();
      $('nodeDeduplicationTop').click();const restored=snapshot();
      return {case:'C02',on,off,restored,expected,tag:B.tag,source_tag:D.source_tag};
    });
    assert.equal(check.tag,check.source_tag);assert(check.on.enabled&&check.on.matched);
    assert.deepEqual(check.on.frames,check.expected);assert.equal(check.on.frames.length,14);
    assert(!check.on.frames.includes(50));assert(check.on.labels.every(s=>!s.includes('候选')));
    assert(!check.off.enabled);assert.equal(check.off.frames.length,15);assert(check.off.frames.includes(50));
    assert.deepEqual(check.restored,check.on);assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(__dirname,'dedup_check.json'),JSON.stringify({...check,errors},null,2)+'\n');
    console.log(JSON.stringify({passed:true,case:check.case,dedup_nodes:14,original_candidates:15,removed_frame:50}));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
