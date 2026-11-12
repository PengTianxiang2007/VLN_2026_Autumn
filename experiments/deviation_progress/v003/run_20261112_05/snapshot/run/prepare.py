import copy,hashlib,json,re,shutil
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'outputs/jev_deviation_progress_v003_terminal_12cases_20261112_run04'
SOURCE=Path(r'C:\Users\93232\Documents\Codex\2026-11-11\yuud\outputs\jev_sampling_lab_20261112')
SITE=ROOT/'outputs/jev_deviation_progress_v003_terminal_34cases_20261112_run05'
REPO=Path(r'C:\Users\93232\Desktop\SCIENCE\CVPR2027_VLN_FDU\Version2\VLN_2026_Autumn')
ALL=list(range(1,35))
REUSED=[4,5,6,7,11,13,14,15,16,17,20,28];NEW=[n for n in ALL if n not in REUSED]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def safe(v):return json.dumps(v,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
assert not SITE.exists(),'Do not overwrite prior runs'
source_html=(SOURCE/'index.html').read_text(encoding='utf-8')
original=json.loads(re.search(r'<script id="payload" type="application/json">(.*?)</script>',source_html,re.S).group(1))
cache=load(SOURCE/'node_deduplication/v001_run02_all/results.json')
previous=load(OLD/'run/inputs.json');cases=[];views=[];maps={};image_ids=set();mapping=[]
for i,number in enumerate(ALL):
    v=copy.deepcopy(original['cases'][number-1]);v['original_case_number']=number
    if number in REUSED:
        c=copy.deepcopy(next(x for x in previous if x['case_number']==number));c['case_index']=i
    else:
        cached=next(x for x in cache['cases'] if x['case_number']==number)
        assert cached['episode_id']==v['episode_id']
        nodes=[copy.deepcopy(n) for n in cached['nodes'] if n['id'] in cached['final_active_ids']]
        for j,n in enumerate(nodes,1):
            mapping.append({'case':number,'source_id':n['id'],'id':f'S{j:02d}','frame':n['index']});n['id']=f'S{j:02d}';n['candidate_id']=n['id']
        f=len(v['frames'])-1;end=v['frames'][f];assert end['terminal'] and end['image']
        if not nodes or nodes[-1]['index']!=f:
            nodes.append({'id':f'S{len(nodes)+1:02d}','index':f,'value':None,'rawScore':None,'kind':'terminal','emittedAt':f,'delay':0,'ready_at_frame':f,'images':[{'frame':f,'image_id':end['image'],'missing':False}]})
        nodes[-1]['terminal_node']=True;nodes[-1]['kind']='terminal';nodes[-1]['candidate_id']=nodes[-1]['id']
        c={'case_number':number,'case_index':i,'episode_id':v['episode_id'],'real_episode_id':v['real_episode_id'],
          'scene':v['scene'],'instruction_en':v['instruction_en'],'instruction_zh':v['instruction_zh'],
          'frames':v['frames'],'nodes':nodes,'final_active_ids':[n['id'] for n in nodes],
          'terminal_frame':f,'image_paths':{r['image']:original['images'][r['image']] for r in v['frames']}}
    assert c['instruction_zh'] and '\ufffd' not in c['instruction_zh']
    assert [n['id'] for n in c['nodes']]==[f'S{j+1:02d}' for j in range(len(c['nodes']))]
    v['initial_index']=c['nodes'][0]['index'];cases.append(c);views.append(v)
    maps[v['scene']]=original['maps'][v['scene']]
    image_ids.update(f['image'] for f in v['frames']);image_ids.add(maps[v['scene']]['image'])
bundle=copy.deepcopy(original);bundle.update(tag=SITE.name,cases=views,maps=maps,images={k:original['images'][k] for k in image_ids})
scores=[f['jev']['probability_yes'] for c in views for f in c['frames'] if f.get('jev')]
bundle['summary'].update(cases=len(ALL),valid_calls=len(scores),expected_calls=len(scores),jev_mean_probability=sum(scores)/len(scores),replay_frames=sum(len(c['frames']) for c in views))
SITE.mkdir(parents=True);(SITE/'run').mkdir()
for name in ['app.js','online_filter.js','online_sampler_v001.js','guard_ui.js','guard_ui.css','node_elimination_results.js']:
    shutil.copy2(OLD/name,SITE/name)
html=(OLD/'index.html').read_text(encoding='utf-8');m=re.search(r'<script id="payload" type="application/json">(.*?)</script>',html,re.S)
html=html[:m.start(1)]+safe(bundle)+html[m.end(1):];(SITE/'index.html').write_text(html,encoding='utf-8')
assets=set(bundle['images'].values())|set(re.findall(r'url\((assets/[^)]+)\)',html))
for rel in assets:
    dest=SITE/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE/rel,dest)
for name in ['prompt_zh.txt','prompt_en.txt']:shutil.copy2(OLD/'run'/name,SITE/'run'/name)
reused_hashes={}
for number in REUSED:
    origin=OLD/f'run/cases/C{number:02d}';dest=SITE/f'run/cases/C{number:02d}';shutil.copytree(origin,dest)
    for p in origin.rglob('*'):
        if p.is_file():reused_hashes[str(p.relative_to(OLD)).replace('\\','/')]=hashlib.sha256(p.read_bytes()).hexdigest()
save(SITE/'run/inputs.json',cases);save(SITE/'run/new_retained_mapping.json',mapping)
data={'source_tag':SITE.name,'sampler_config':{'window':7,'delay':5},'cases':[{'case_number':c['case_number'],'case_index':c['case_index'],'episode_id':c['episode_id'],'nodes':c['nodes'],'final_active_ids':c['final_active_ids'],'decisions':[]} for c in cases]}
(SITE/'node_deduplication_results.js').write_text('window.JEV_NODE_DEDUP_DATA='+safe(data)+';\n',encoding='utf-8')
(SITE/'audit_results.js').write_text('window.JEV_GUARD_DATA='+safe({'cases':[],'summary':{},'status':'prepared'})+';\n',encoding='utf-8')
runner=(OLD/'run/run_review.py').read_text(encoding='utf-8')
compile(runner,'run_review.py','exec');(SITE/'run/run_review.py').write_text(runner,encoding='utf-8')
manifest=load(OLD/'run/manifest.json')
for k in ['actual_summary','standalone_html','terminal_nodes']:manifest.pop(k,None)
manifest.update(status='prepared',created_at=datetime.now(timezone.utc).isoformat(),selected_cases=ALL,new_case_numbers=NEW,reused_case_numbers=REUSED,
  reuse_source=str(OLD),reused_file_hashes=reused_hashes,scene_ids=sorted(maps),copied_assets=len(assets),cached_nodes=sum(len(c['nodes']) for c in cases),cached_final_retained=sum(len(c['nodes']) for c in cases),
  selection_rule='All 34 user-authorized cases. Submit only the remaining 22 cases. Reuse the previous 12 cases byte-for-byte, including failures and early-stop records. Cases 32 and 33 refer to the same episode and are not independent trajectories.',
  prompt_sha256=hashlib.sha256((SITE/'run/prompt_zh.txt').read_text(encoding='utf-8').encode()).hexdigest(),runner_sha256=hashlib.sha256((SITE/'run/run_review.py').read_bytes()).hexdigest())
manifest['protocol']['new_model_calls']='Only the 22 cases listed in new_case_numbers. Reuse all 12 prior results without retries or additional calls, including failed answers. Six workers; other settings and prompts unchanged.'
save(SITE/'run/manifest.json',manifest)
ui=(SITE/'guard_ui.js').read_text(encoding='utf-8')
ui=ui.replace('十二条轨迹离线评审','34 个案例离线评审').replace('Twelve-case offline review','34-case offline review')
ui=ui.replace('原列表第 4、5、6、7、11、13、14、15、16、17、20、28 条。本次补跑 5、6、13、15、16、20；其余六条直接复用上一轮结果。','完整 34 个案例，来自 33 条独立轨迹、9 个场景。本次补跑剩余 22 条，已有 12 条结果原样复用。第 32、33 个案例对应同一条轨迹。')
ui=ui.replace('Original cases 4, 5, 6, 7, 11, 13, 14, 15, 16, 17, 20 and 28. Cases 5, 6, 13, 15, 16 and 20 are newly reviewed; the other six reuse prior results.','All 34 cases from 33 distinct trajectories and 9 scenes. Only the remaining 22 cases are new; 12 prior cases are reused unchanged. Cases 32 and 33 share one trajectory.')
(SITE/'guard_ui.js').write_text(ui,encoding='utf-8')
doc=REPO/'experiments/deviation_progress/v003/run_20261112_05/README.md';doc.parent.mkdir(parents=True,exist_ok=True)
doc.write_text('# v003：扩展至全部34个案例\n\n2026-11-12，准备运行。只补跑剩余22条，已完成的12条（4、5、6、7、11、13、14、15、16、17、20、28）直接复用run04，包括40次请求中的7次失败，不重试。34个案例对应33条独立轨迹、9场景；32和33为同一轨迹的两个事件。\n\n沿用v003：有效节点连续编号、追加终止节点、首节点单图初始化、端点＋均匀最多5张中间图。DeepSeek flash、thinking enabled/high、JSON、max_tokens32768、六进程、每条串行，seed未指定。首次偏航后停止评审，没有真实回退或新导航。提示词与配置不变。\n\n本地网页完整中文任务指令、无去重开关，新增与复用来源分别标明。原始结果按case_number关联，旧case_index作为来源保留。\n\n启动：python -u <产物>/run/run_review.py --site <产物> --key-stdin。产物及源码快照：`'+str(SITE)+'`；基线、源码及复用文件哈希见manifest。\n',encoding='utf-8')
for p,link in [(REPO/'docs/STATUS.md','../experiments/deviation_progress/v003/run_20261112_05/README.md'),(REPO/'experiments/README.md','deviation_progress/v003/run_20261112_05/README.md')]:
    s=p.read_text(encoding='utf-8');i=s.index('\n')+1;s=s[:i]+f'\n2026-11-12：[全部34个案例]({link})准备运行：仅补跑22条，12条复用；六进程、本地网页。\n'+s[i:];p.write_text(s,encoding='utf-8')
print(json.dumps({'site':str(SITE),'new':NEW,'reused':REUSED,'scenes':len(maps),'nodes':manifest['cached_nodes'],'new_nodes':sum(len(c['nodes']) for c in cases if c['case_number'] in NEW),'cases':[{'case':c['case_number'],'nodes':len(c['nodes'])} for c in cases]},ensure_ascii=False))
