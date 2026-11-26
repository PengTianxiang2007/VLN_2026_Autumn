"""Publish the C17 addition to the existing deviation replay, including its offline download."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = ROOT / 'outputs/inverse_rollback/codex_tools_v001' / HERE.name / 'C17'
RELEASE = 'c17_region60_inline_web_20261126_01'
FOLDER = 'recovery-c17-20261126-01'
STABLE = 'codex_deviation_v002_terminal4_map_layers_web_20261125_01'
STAGE = ROOT / 'outputs/visualization_publishing' / RELEASE
URL = 'http://134.175.18.101/vln/' + STABLE + '/index.html'
ZH = {
    0: '我会查看当前视野，然后回到 S09 的走廊交汇处，确认能看到那里的其他支路。',
    11: '视野恢复清晰了，我辨认出了经过 S09 后进入的卧室。我正转向出口，准备返回走廊交汇处。',
    28: '我又看到走廊了。我会离开卧室门口，以便核对 S09 的侧面入口。',
    43: '对应 S09 右侧支路的入口重新出现在视野中。我会再看一下对面的房间入口，然后声明到达。',
    56: '我已回到 S09 的走廊尽头交汇处附近。现在的观测显示了原先的卧室入口和两侧的开口，又可以在这些路线之间做选择了。我会标记回退完成。',
    57: '已回到 S09（F68）附近，核对了各支路开口并调用了 `finish_return`。60 步移动预算共用了 55 步。'}
PROMPT_ZH = """请控制机器人回到回退点 S09（F68）。

结合历史观测，确认当前位置符合回退点定义，并且能看清当时从该回退点看到的其他支路。不强求精确复现原来的位置和朝向，在原来位置附近区域即可。

使用 observe() 查看前视画面，使用 step("forward")、step("turn_left") 或 step("turn_right") 移动或转向。满足上述条件后，调用 step("finish_return") 结束回退。

最多可执行 60 步移动。每次前进或转向计一步。观察和声明到达不计步。如果用完 60 步仍无法确认到达，结束本次尝试。"""


def read(path):
    return json.loads(path.read_bytes())


def heading(q):
    w,x,y,z = q
    return math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))


def build():
    dest = STAGE / FOLDER
    dest.mkdir(parents=True)
    state = read(RUN/'placement.json')['state']
    rows = [dict(action='start',move=0,p=state['position'][:2],heading=heading(state['rotation']),
                 image='front.png',utc=read(RUN/'placement_time.json')['finished_utc'])]
    shutil.copyfile(RUN/'front.png',dest/'front.png')
    moved=0
    for line in (RUN/'live/calls.jsonl').open():
        r=json.loads(line)
        action = r['action'] or r['method']
        moved += action in {'forward','turn_left','turn_right'}
        p=RUN/r['rgb']['file']
        shutil.copyfile(p,dest/p.name)
        rows.append(dict(action=action,move=moved,p=r['after']['position'][:2],heading=heading(r['after']['quaternion_wxyz']),
                         image=p.name,utc=r['finished_utc']))
    notes=[]
    calls=0
    for line in (RUN/'codex-events.jsonl').open():
        e=json.loads(line); item=e.get('item',{})
        if e['type']=='item.completed':
            if item['type']=='agent_message':
                notes.append([calls,ZH[calls],item['text'].strip()])
            elif item['type']=='mcp_tool_call':
                calls+=1
    data=dict(folder=FOLDER,rows=rows,notes=notes,prompt=[PROMPT_ZH,(RUN/'prompt.txt').read_text().strip()])
    code=(HERE/'c17_return.js').read_text().replace('RECOVERY_C17_DATA',json.dumps(data,ensure_ascii=False))
    (dest/'replay.js').write_text(code)
    (STAGE/'index.html').write_text(f'<meta charset="utf-8"><meta http-equiv="refresh" content="0;url={URL}#C17-return"><a href="{URL}#C17-return">C17</a>')


ACTIVATE = """
import json,os,pathlib,shutil,sys,zipfile
p=json.load(sys.stdin)
base=pathlib.Path(p['root'])
live=base/p['stable']
stage=base/p['release']
assets=p['folder']
tag=b'<script src="'+assets.encode()+b'/replay.js"></script>'
def insert(html):
    return html.replace(b'</body>',tag+b'</body>',1)
(live/assets).mkdir()
for file in (stage/assets).iterdir():
    os.link(file,live/assets/file.name)
backup=stage/'prior'
backup.mkdir(mode=0o700)
for name in ('index.html','replay.zip'):
    os.link(live/name,backup/name)
index=live/'index.html'
temp=live/('.index-'+assets)
temp.write_bytes(insert(index.read_bytes()))
temp.chmod(0o644)
os.replace(temp,index)
out=live/('.zip-'+assets)
with zipfile.ZipFile(backup/'replay.zip') as original, zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as updated:
    for info in original.infolist():
        body=original.read(info)
        updated.writestr(info.filename,insert(body) if info.filename=='index.html' else body)
    for file in (live/assets).iterdir():
        updated.write(file,assets+'/'+file.name,compress_type=zipfile.ZIP_STORED)
out.chmod(0o644)
os.replace(out,live/'replay.zip')
print('Activated '+str(index),flush=True)
"""


def publish():
    cfg=read(ROOT/'core/visualization_publish.json')
    host=cfg['ssh_user']+'@'+cfg['ssh_host']
    with tempfile.TemporaryDirectory(prefix='vln-c17-') as directory:
        sock=str(Path(directory)/'ctl')
        args=[sys.executable,'-Bu','scripts/publish_visualization.py','--html',str(STAGE/'index.html'),
              '--name',RELEASE,'--ssh-control-path',sock]
        for path in sorted((STAGE/FOLDER).iterdir()):
            args.extend(['--asset',str(path.relative_to(STAGE))])
        try:
            subprocess.run(args,cwd=ROOT,check=True)
            subprocess.run(['ssh','-S',sock,'-o','BatchMode=yes',host,'python3 -c '+shlex.quote(ACTIVATE)],
                           input=json.dumps(dict(root=cfg['remote_root'],stable=STABLE,release=RELEASE,folder=FOLDER)),text=True,check=True)
        finally:
            subprocess.run(['ssh','-S',sock,'-O','exit',host],stderr=subprocess.DEVNULL)
    result=dict(published_utc=datetime.now(timezone.utc).isoformat(),url=URL+'#C17-return',moves=55,tool_frames=57)
    (STAGE/'activation.json').write_text(json.dumps(result,indent=2)+'\n')
    with (HERE/'README.md').open('a') as doc:
        doc.write('\n'+result['published_utc']+'，C17 的 55 步回退、逐调用第一人称 RGB、轨迹、模型发言与计时已加入[原版偏航回放]('+result['url']+')和同页离线包。\n')
    print(result['url'])


if __name__=='__main__':
    build()
    publish()
