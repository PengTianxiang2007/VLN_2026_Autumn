"""Add C17 to the published C11 return replay and withdraw the earlier misplaced addition."""
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import runpy
import shlex
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PUBLISHED = ROOT / "outputs/visualization_publishing"
LIVE = "c11_codex_region60_f57_f45_web_20261126_01"
RELEASE = "c11_c17_codex_region60_web_20261126_01"
STAGE = PUBLISHED / RELEASE
BASE = PUBLISHED / LIVE
REVIEW = PUBLISHED / "codex_deviation_v002_astra_terra_web_20261126_01"
RUN = ROOT / "outputs/inverse_rollback/codex_tools_v001" / HERE.name / "C17"
TEMPLATE = HERE.parents[1] / "exports/c11_branch_return_20261126_01"
PANEL = ROOT / "experiments/deviation_progress/codex_memory_v002/run_20261125_01_terminal4/exports/map_layers_01/extension.js"
OLD = runpy.run_path(str(HERE / "publish_c17.py"))
MARK = re.compile(r'(<script id="payload" type="application/json">)(.*?)(</script>)', re.S)


def read(path):
    return json.loads(path.read_bytes())


def add_image(images, path, stage=STAGE):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    dest = 'assets/' + digest + path.suffix
    if not (stage/dest).exists():
        os.link(path,stage/dest)
    images[digest] = dest
    return digest


def build():
    (STAGE/'assets').mkdir(parents=True)
    base_html = (BASE/'index.html').read_text()
    c11 = json.loads(MARK.search(base_html)[2])
    for p in (BASE/'assets').iterdir():
        os.link(p,STAGE/'assets'/p.name)
    original = json.loads(MARK.search((REVIEW/'index.html').read_text())[2])
    summary=dict(verdict=c11['summary']['verdict'],footer=c11['summary']['footer'],
        notice=["模型在第 55 步声明回到 S09 的走廊交汇处，停点距 F68 为 1.32 米。摆位 7 分 27 秒，Codex 回退 8 分 44 秒，总计 16 分 11 秒。",
                "The model declared arrival at the S09 hallway junction after 55 moves. The final position was 1.32 m from F68. Placement took 7m 27s, the Codex return 8m 44s, and the full attempt 16m 11s."],
        events=[[28,"模型辨认出走廊","Model identified the hallway"],[43,"模型辨认出侧面入口","Model identified a side entrance"],[57,"R55 · 声明到达","R55 · Declared arrival"]])
    c17=build_case(original,'C17',RUN,STAGE,OLD['ZH'],OLD['PROMPT_ZH'],summary)
    c11['startImage']=add_image(c11['images'],RUN.parent.parent/'run_20261126_05_c11_region60/front.png')
    write_replay(dict(C11=c11,C17=c17),base_html,STAGE,BASE)


def build_case(original,case_id,run,stage,translations,prompt_zh,summary,*,include_rejected=False):
    case, = [c for c in original['cases'] if c['case_id']==case_id]
    grid = original['maps'][case['scene']]
    images = {}
    for key in {f['image'] for f in case['frames']} | {grid['image']}:
        rel = original['images'][key]
        if not (stage/rel).exists():
            os.link(REVIEW/rel, stage/rel)
        images[key]=rel
    steps=(ROOT/read(run/'placement.json')['source']).parents[1]
    for frame in case['frames']:
        frame['heading']=read(steps/f"{frame['frame']:06d}/metadata.json")['robot_pose']['heading_deg']
    r=read(run/'result.json')
    target=case['frames'][r['target_frame']]['position']
    result={k:r[k] for k in ('parent_thread','branch_thread','movements','cap','final_m','nearest_m','nearest_move')}
    result['target_position']=target
    rows=[]
    moved=0
    for rec in map(json.loads,(run/'live/calls.jsonl').open()):
        action=rec['action'] or rec['method']
        executed=action in ('forward','turn_right','turn_left')
        moved+=executed
        pose=rec['after']; rt=rec['result']
        rows.append(dict(seq=rec['sequence'], op=action, failed=False, executed=executed, feedback=True,
                         position=pose['position'],heading=math.degrees(OLD['heading'](pose['quaternion_wxyz'])),
                         utc=rec['finished_utc'],status=rt['status'],terminal_reason=rt.get('terminal_reason'),distance=math.dist(pose['position'][:2],target[:2]),
                         motion=moved,live=rt['live_frame'],taskTicks=rt['task_ticks_advanced'],worldTicks=rt['physics_ticks_advanced'],
                         image=add_image(images,run/rec['rgb']['file'],stage)))
    notes=[]
    count=0
    for e in map(json.loads,(run/'codex-events.jsonl').open()):
        if e['type']=='item.completed':
            item=e['item']
            if item['type']=='agent_message':
                notes.append(dict(call=count,text=[translations[count],item['text'].strip()]))
            elif item['type']=='mcp_tool_call':
                if include_rejected and item['status']=='failed':
                    action=item['arguments'].get('action',item['tool'])
                    rows.insert(count,dict(rows[count-1],op=action,failed=True,executed=False,feedback=False,
                                           seq=None,utc=None,taskTicks=0,worldTicks=0,terminal_reason=None))
                count+=1
    if include_rejected and (count!=len(rows) or moved!=result['movements']):
        raise ValueError(f"Tool timeline does not match the recorded attempt for {case_id}")
    return dict(cases=[case],grid=grid,images=images,result=result,calls=rows,notes=notes,
                startImage=add_image(images,run/'front.png',stage),
                prompt=[prompt_zh,(run/'prompt.txt').read_text().strip()],summary=summary)


def write_replay(replays,base_html,stage,base,*,versions=None):
    data=dict(replays=replays)
    if versions is not None:
        data['versions']=versions
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    renderer=(TEMPLATE/'page.js').read_text()
    source=PANEL.read_text()
    renderer=renderer.replace('/* ORIGINAL REVIEW PANEL */',source[source.index('function make('):source.index('function setupTerminalReplay(')])
    html=MARK.sub(lambda m:m[1]+payload+m[3],base_html,count=1)
    last=html.rindex('<script>');end=html.index('</script>',last)
    html=html[:last]+'<script>'+renderer+html[end:]
    (stage/'index.html').write_text(html)
    with zipfile.ZipFile(stage/'replay.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        z.writestr('index.html',re.sub(r'<a href="replay.zip"[^>]*>.*?</a>','',html,count=1))
        for p in sorted((stage/'assets').iterdir()):
            z.write(p,'assets/'+p.name,compress_type=zipfile.ZIP_STORED)
        with zipfile.ZipFile(base/'replay.zip') as baseline:
            z.writestr('FONT_LICENSE.txt',baseline.read('FONT_LICENSE.txt'))


ACTIVATE="""
import json,os,pathlib,sys,zipfile
p=json.load(sys.stdin); root=pathlib.Path(p['root'])
stage=root/p['release']; live=root/p['correct']; wrong=root/p['wrong']; misplaced=root/p['misplaced']; original=misplaced/'prior'
back=stage/'prior';back.mkdir(mode=0o700)
def swap(source,target):
    tmp=target.with_name('.'+target.name+'.c11c17')
    os.link(source,tmp);os.replace(tmp,target)
for name in ('index.html','replay.zip'):
    os.link(live/name,back/name)
for img in (stage/'assets').iterdir():
    target=live/'assets'/img.name
    if not target.exists():os.link(img,target)
for name in ('replay.zip','index.html'):swap(stage/name,live/name)
tag=b'<script src="recovery-c17-20261126-01/replay.js"></script>'
current=(wrong/'index.html').read_bytes()
if tag in current:
    removed=current.replace(tag,b'',1)
    if removed==(original/'index.html').read_bytes():
        swap(original/'index.html',wrong/'index.html')
    else:
        temp=wrong/'.index-c17-withdraw';temp.write_bytes(removed);temp.chmod(0o644);os.replace(temp,wrong/'index.html')
    def original_members(z):
        return {i.filename:(i.CRC,i.file_size) for i in z.infolist() if i.filename!='index.html' and not i.filename.startswith('recovery-c17-20261126-01/')}
    with zipfile.ZipFile(wrong/'replay.zip') as cur, zipfile.ZipFile(original/'replay.zip') as prior:
        simple=(original_members(cur)==original_members(prior) and cur.read('index.html').replace(tag,b'',1)==prior.read('index.html'))
        if not simple:
            temp=wrong/'.zip-c17-withdraw'
            with zipfile.ZipFile(temp,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as out:
                for i in cur.infolist():
                    if not i.filename.startswith('recovery-c17-20261126-01/'):
                        b=cur.read(i);out.writestr(i,b.replace(tag,b'',1) if i.filename=='index.html' else b)
            temp.chmod(0o644);os.replace(temp,wrong/'replay.zip')
    if simple:swap(original/'replay.zip',wrong/'replay.zip')
    artifacts=wrong/'recovery-c17-20261126-01'
    if artifacts.exists():os.rename(artifacts,back/'withdrawn-c17-assets')
redirect=misplaced/'.index-corrected'
redirect.write_text('<meta charset="utf-8"><meta http-equiv="refresh" content="0;url=../'+p['correct']+'/index.html#C17"><a href="../'+p['correct']+'/index.html#C17">C17</a>')
redirect.chmod(0o644);os.replace(redirect,misplaced/'index.html')
print('Activated '+str(live/'index.html')+' and withdrew the C17 addition from '+str(wrong/'index.html'),flush=True)
"""


def publish_assets(stage, activation, parameters):
    cfg=read(ROOT/'core/visualization_publish.json')
    host=cfg['ssh_user']+'@'+cfg['ssh_host']
    with tempfile.TemporaryDirectory(prefix='vln-return-publish-') as tmp:
        sock=str(Path(tmp)/'ctl')
        args=[sys.executable,'-Bu','scripts/publish_visualization.py','--html',str(stage/'index.html'),'--name',stage.name,'--ssh-control-path',sock,'--asset','replay.zip']
        for p in sorted((stage/'assets').iterdir()):
            args.extend(['--asset','assets/'+p.name])
        try:
            subprocess.run(args,cwd=ROOT,check=True)
            cfg_live=dict(root=cfg['remote_root'],release=stage.name,**parameters)
            subprocess.run(['ssh','-S',sock,'-o','BatchMode=yes',host,'python3 -c '+shlex.quote(activation)],input=json.dumps(cfg_live),text=True,check=True)
        finally:
            subprocess.run(['ssh','-S',sock,'-O','exit',host],stderr=subprocess.DEVNULL)


def publish():
    publish_assets(STAGE,ACTIVATE,dict(correct=LIVE,wrong=OLD['STABLE'],misplaced=OLD['RELEASE']))
    url='http://134.175.18.101/vln/'+LIVE+'/index.html#C17'
    stamp=datetime.now(timezone.utc).isoformat()
    (STAGE/'activation.json').write_text(json.dumps(dict(published_utc=stamp,url=url,withdrawn=OLD['STABLE']),indent=2)+'\n')
    with (HERE/'README.md').open('a') as f:
        f.write('\n'+stamp+'，发布位置已更正。[C11 / C17 实走回退回放]('+url+')可在同一页面切换案例；原偏航评审页及其下载包已撤回上次添加的 C17 回退内容。\n')
    print(url)


if __name__=='__main__':
    build()
    publish()
