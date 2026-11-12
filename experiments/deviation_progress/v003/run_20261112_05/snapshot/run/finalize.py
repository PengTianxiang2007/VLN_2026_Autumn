import base64,hashlib,json,mimetypes,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SITE=ROOT/'outputs/jev_deviation_progress_v003_terminal_34cases_20261112_run05'
SINGLE=ROOT/'outputs/jev_deviation_progress_v003_terminal_34cases_20261112.html'
REPO=Path(r'C:\Users\93232\Desktop\SCIENCE\CVPR2027_VLN_FDU\Version2\VLN_2026_Autumn')
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def safe(v):return json.dumps(v,ensure_ascii=False,separators=(',',':')).replace('</','<\\/').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
results=load(SITE/'run/results.json');inputs=load(SITE/'run/inputs.json');manifest=load(SITE/'run/manifest.json')
assert [c['case_number'] for c in results['cases']]==list(range(1,35))
assert len(results['cases'])==34 and sum(len(c['nodes']) for c in inputs)==manifest['cached_nodes']
for rel,digest in manifest['reused_file_hashes'].items():
    assert hashlib.sha256((SITE/rel).read_bytes()).hexdigest()==digest,'Reused source changed: '+rel
assert results['summary']['reused_calls']==40 and results['summary']['new_worker_processes']==6
raw={'run/results.json':results};red=[]
for c,source in zip(results['cases'],inputs):
    assert c['case_number']==source['case_number']
    nodes=source['nodes'];assert [n['id'] for n in nodes]==[f'S{i+1:02d}' for i in range(len(nodes))]
    assert nodes[-1]['terminal_node'] and nodes[-1]['index']==len(source['frames'])-1
    assert nodes[-1]['emittedAt']==nodes[-1]['index']
    assert len({n['index'] for n in nodes})==len(nodes)
    anchor=nodes[0];progress=None
    for r,n in zip(c['reviews'],nodes):
        assert r['node_id']==n['id'] and r['to_frame']==n['index']
        assert r['previous_id']==anchor['id'] and r['from_frame']==anchor['index']
        if progress is not None:assert r['prior_progress']==progress
        ims=r['images'];assert len(ims)<=7 and all(anchor['index']<=im['frame']<=n['index'] for im in ims)
        if r['mode']=='initialization':assert len(ims)==1 and r['from_frame']==r['to_frame']
        raw[r['request_file']]=load(SITE/r['request_file']);raw[r['response_file']]=load(SITE/r['response_file'])
        if r.get('answer',{}).get('verdict')=='consistent':anchor=n;progress=r['answer']['semantic_progress']
        else:progress=r['prior_progress']
        if r.get('answer',{}).get('verdict')=='deviated':red.append({'case':c['case_number'],'nodes':r['previous_id']+' → '+r['node_id'],'frames':[r['from_frame'],r['to_frame']]})
    assert len(c['reviews'])+len(c['unreviewed_nodes'])==len(nodes)
html=(SITE/'index.html').read_text(encoding='utf-8');m=re.search(r'<script id="payload" type="application/json">(.*?)</script>',html,re.S);bundle=json.loads(m.group(1))
for c,r,s in zip(bundle['cases'],results['cases'],inputs):
    assert c['instruction_zh'] and '\ufffd' not in c['instruction_zh']
    first=next((x for x in r['reviews'] if x.get('answer',{}).get('verdict')=='deviated'),None)
    c['initial_index']=first['to_frame'] if first else s['nodes'][0]['index']
html=html[:m.start(1)]+safe(bundle)+html[m.end(1):]
(SITE/'index.html').write_text(html,encoding='utf-8')
m=re.search(r'<script id="payload" type="application/json">(.*?)</script>',html,re.S)
for k,rel in list(bundle['images'].items()):bundle['images'][k]='data:'+(mimetypes.guess_type(rel)[0] or 'application/octet-stream')+';base64,'+base64.b64encode((SITE/rel).read_bytes()).decode()
html=html[:m.start(1)]+safe(bundle)+html[m.end(1):]
for rel in set(re.findall(r'url\((assets/[^)]+)\)',html)):
    html=html.replace('url('+rel+')','url(data:font/ttf;base64,'+base64.b64encode((SITE/rel).read_bytes()).decode()+')')
html=html.replace('<link rel="stylesheet" href="guard_ui.css">','<style>\n'+(SITE/'guard_ui.css').read_text(encoding='utf-8')+'\n</style>')
html=html.replace('<script src="guard_ui.js"></script>','<script>window.JEV_GUARD_FILES='+safe(raw)+';</script><script src="guard_ui.js"></script>')
html=re.sub(r'<script src="([^"/]+\.js)"></script>',lambda m:'<script>\n'+(SITE/m.group(1)).read_text(encoding='utf-8').replace('</script','<\\/script')+'\n</script>',html)
assert not re.search(r'<script[^>]+src=',html) and 'id="nodeDeduplication"' not in html
assert not re.search(r'sk-[A-Za-z0-9_-]{20,}',html)
SINGLE.write_text(html,encoding='utf-8')
s=results['summary'];manifest.update(status='complete',actual_summary=s,standalone_html=str(SINGLE));save(SITE/'run/manifest.json',manifest)
verification={'passed':True,'effective_nodes':manifest['cached_nodes'],'terminal_nodes':34,'reused_twelve_cases_unchanged':True,'six_new_worker_processes':True,'consecutive_ids':True,'all_review_endpoints_are_effective_nodes':True,'max_input_images':7,'full_chinese_instructions':34,'no_dedup_controls':True,'no_external_assets':True,'red_intervals':red,'standalone_sha256':hashlib.sha256(SINGLE.read_bytes()).hexdigest()}
save(SITE/'run/verification.json',verification)
report='本地可视化 v003｜全部34个案例｜2026-11-12\n\n打开 '+SINGLE.name+' 或本目录index.html。网页本地离线，不调用API。\n\n34个案例对应33条独立轨迹、9场景。仅补跑22条，已有12条原样复用（40次历史请求，包括7次失败）。编号32、33属于同一条轨迹，不作为两个独立样本统计。\n\n沿用v003，仅有效节点连续编号，增加终止节点，首节点单图初始化；端点两图＋均匀最多五张中间图。首次偏航停止后续评审，未执行真实回退。\n\n结果：'+json.dumps(s,ensure_ascii=False,indent=2)+'\n\n偏航区间：'+json.dumps(red,ensure_ascii=False,indent=2)+'\n\nnew_calls为本次新调用，reused_calls为历史复用，calls为合计。字段或请求错误均保留，未推进可信进度。模型结论不等同于真值或准确率。\n'
(SITE/'README.txt').write_text(report,encoding='utf-8')
doc=REPO/'experiments/deviation_progress/v003/run_20261112_05/README.md'
text=doc.read_text(encoding='utf-8').replace('准备运行。','已完成。')
text+='\n实际结果：'+json.dumps(s,ensure_ascii=False)+'。\n\n红色区间：'+json.dumps(red,ensure_ascii=False)+'。\n\n单文件产物：`'+str(SINGLE)+'`。只做节点链、输入范围、完整中文及页面基本显示检查；未重跑导航，模型判定不是独立准确率。\n'
doc.write_text(text,encoding='utf-8')
for p in [REPO/'docs/STATUS.md',REPO/'experiments/README.md']:
    text=p.read_text(encoding='utf-8');text=text.replace('准备运行：仅补跑22条，12条复用；',f'已完成：补跑22条，新请求{s["new_calls"]}次、有效{s["new_valid"]}次，12条的40次记录原样复用；');p.write_text(text,encoding='utf-8')
category=REPO/'experiments/deviation_progress/README.md';text=category.read_text(encoding='utf-8')
if 'v003/run_20261112_05' not in text:text+='\n- [v003 / run_20261112_05](v003/run_20261112_05/README.md)：全部34个案例；仅补跑22条，12条直接复用。\n'
category.write_text(text,encoding='utf-8')
version_doc=REPO/'experiments/deviation_progress/v003/README.md';text=version_doc.read_text(encoding='utf-8')
if 'run_20261112_05' not in text:text+='\n- [全部34个案例](run_20261112_05/README.md)：补跑22条，复用12条。\n'
version_doc.write_text(text,encoding='utf-8')
for p in Path(__file__).parent.glob('*.py'):shutil.copy2(p,SITE/'run'/p.name)
print(json.dumps({'html':str(SINGLE),'summary':s,'red':red},ensure_ascii=False))
