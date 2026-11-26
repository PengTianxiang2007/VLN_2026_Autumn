"""Export the completed four-case batch alongside C11 at the established return-replay URL."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

import publish_return_cases as replay


HERE = Path(__file__).resolve().parent
STAGE = replay.PUBLISHED / "codex_region60_five_cases_web_20261126_01"
PREVIOUS = replay.STAGE
BATCH = replay.RUN.parent

TRANSLATIONS = {
    'C43': {
        0: '我会先找导航控制工具，然后回到 F30 的门口附近，在声明到达前确认可选支路。',
        11: '现在能看到离开卧室的通道了。我会往交汇处走，并对照 F30 核对侧门。',
        24: '我已接近先前的门口。我会转回卧室方向，确认从这里既可以进入卧室，也可以走旁边的侧面开口。',
        33: '又能看到 F30 的支路布局了：左侧的门通往一处小衣帽区，旁边的路线则通往带大窗户的卧室。从附近的这个位置可以进入两处，我会声明回退完成。',
        34: '已回到 S04（F30）附近，确认了侧门和通往卧室的路线，并调用了 `finish_return`。60 步移动预算共用了 32 步。'},
    'C23': {
        0: '我会先查看当前画面，再回到电视柜旁能看到 S02 各支路入口的区域。',
        21: '又能看到 S02 的两个开口了：电视墙旁的门口，以及朝向梳妆台的开口。我会再往客厅里退一点，回到先前接近路口时的位置。',
        48: '机器人已回到接近 S02 时所在的区域附近。电视柜旁的门口与右侧开口均可见、可达，且无需进入任何一条支路。',
        49: '已回到回退点 S02（F7）附近，原有的两条支路都可见、可达。在执行 47 步移动后调用了 `finish_return`。'},
    'C20': {
        0: '我会先查看当前画面，再往 S03 回退，直到能重新看到客厅区域和电视墙旁的通道。',
        6: '当前画面显示了 S03 的两条路线：客厅座椅区，以及电视墙旁的通道。与历史画面吻合的地标和附近的开阔地面让我确认已经回到回退点所在区域。',
        7: '已回到 S03 回退点附近并调用了 `finish_return`。座椅区路线与电视墙旁的通道都清晰可见。60 步移动预算共用了 5 步。'},
}
EVENTS = {
    'C43': [(11,'模型辨认出卧室出口','Model identified the bedroom exit'),(33,'模型核对侧门与卧室路线','Model compared the side door and the bedroom route')],
    'C23': [(21,'模型辨认出两个开口','Model identified both openings'),(48,'模型确认电视柜旁的选路位置','Model confirmed the choice point beside the TV console')],
    'C20': [(6,'模型辨认出座椅区与电视墙旁的通道','Model identified the seating area and the passage beside the TV wall')],
}


def duration(seconds, english=False):
    m,s = divmod(round(seconds),60)
    return f"{m}m {s:02}s" if english else f"{m} 分 {s:02} 秒"


def build():
    (STAGE/'assets').mkdir(parents=True)
    for asset in (PREVIOUS/'assets').iterdir():
        os.link(asset, STAGE/'assets'/asset.name)
    html = (PREVIOUS/'index.html').read_text()
    packs = json.loads(replay.MARK.search(html)[2])['replays']
    reviews = json.loads(replay.MARK.search((replay.REVIEW/'index.html').read_text())[2])
    template = packs['C11']['summary']
    c11_run=BATCH.parent/'run_20261126_05_c11_region60'
    stamp=datetime.fromisoformat
    c11_elapsed=(stamp(replay.read(c11_run/'result.json')['completed_utc'])-stamp(replay.read(c11_run/'launch.json')['utc'])).total_seconds()
    template['notice'][0] += f' 从控制分支启动登记到结果写入为 {duration(c11_elapsed)}。'
    template['notice'][1] += f' Elapsed time from branch launch registration to result recording was {duration(c11_elapsed,True)}.'
    for task in replay.read(HERE/'cases.json'):
        case_id=task['case']
        if case_id in packs:
            continue
        run=BATCH/case_id
        result=replay.read(run/'result.json')
        timing=replay.read(run/'timing.json')
        node=result['target_node']
        frame=result['target_frame']
        moved=result['movements']
        dist=result['final_m']
        durations=[timing[k] for k in ('placement_elapsed_s','controller_elapsed_s','case_elapsed_s')]
        pl,rt,total=map(duration,durations)
        pen,ren,ten=[duration(v,True) for v in durations]
        notice=[f'模型在第 {moved} 步声明到达 {node}，停点距 F{frame} 水平位置 {dist:.2f} 米。摆位 {pl}，Codex 回退 {rt}，总计 {total}。',
                f'The model declared arrival at {node} after {moved} moves. The final horizontal distance to F{frame} was {dist:.2f} m. Placement took {pen}, the Codex return {ren}, and the full attempt {ten}.']
        if case_id=='C23':
            notice[0]+=' 偏航评审在 F17 报警，实走回退从 F17 开始；原版轨迹的终止帧为 F32。'
            notice[1]+=' The deviation alarm and physical return both start at F17. The original navigation ended at F32.'
        events=[*EVENTS[case_id],(timing['first_person_rgb_frames'],f'R{moved} · 声明到达',f'R{moved} · Declared arrival')]
        summary=dict(verdict=template['verdict'],footer=template['footer'],notice=notice,events=events)
        zh=replay.OLD['PROMPT_ZH'].replace('S09（F68）',f'{node}（F{frame}）')
        packs[case_id]=replay.build_case(reviews,case_id,run,STAGE,TRANSLATIONS[case_id],zh,summary)
    replay.write_replay(packs,html,STAGE,PREVIOUS)


ACTIVATE = """
import hashlib,json,os,pathlib,sys
p=json.load(sys.stdin)
root=pathlib.Path(p['root']); live=root/p['correct']; staged=root/p['release']
if hashlib.sha256((live/'index.html').read_bytes()).hexdigest()!=p['previous_sha']:
    raise RuntimeError('Current stable release changed before activation')
prior=staged/'prior';prior.mkdir(mode=0o700)
for name in ('index.html','replay.zip'):
    os.link(live/name,prior/name)
for asset in (staged/'assets').iterdir():
    dest=live/'assets'/asset.name
    if not dest.exists():os.link(asset,dest)
for name in ('replay.zip','index.html'):
    tmp=live/('.'+name+'.region60five');os.link(staged/name,tmp);os.replace(tmp,live/name)
print('Activated the five-case replay at '+str(live/'index.html'),flush=True)
"""


def publish():
    replay.publish_assets(STAGE,ACTIVATE,dict(correct=replay.LIVE,previous_sha=hashlib.sha256((PREVIOUS/'index.html').read_bytes()).hexdigest()))
    url='http://134.175.18.101/vln/'+replay.LIVE+'/'
    record=dict(published_utc=datetime.now(timezone.utc).isoformat(), url=url+'index.html', download=url+'replay.zip',
                html_sha256=hashlib.sha256((STAGE/'index.html').read_bytes()).hexdigest(),
                zip_sha256=hashlib.sha256((STAGE/'replay.zip').read_bytes()).hexdigest(),
                cases=['C11','C17','C43','C23','C20'])
    (STAGE/'activation.json').write_text(json.dumps(record,indent=2)+'\n')
    with (HERE/'README.md').open('a') as doc:
        doc.write(f"\n{record['published_utc']}，四例全部加入既有 C11 回退网页：[五例回放]({record['url']}) · [离线 ZIP]({record['download']})。本批共 147 张逐调用第一人称 RGB、4 张摆位图。C23 的回退在首次报警 F17 接续，原版 F32 终点仍可在地图上对照。双语任务指令、模型发言、偏航评审、回退步数与耗时随案例切换。源码为 [export_completed.py](export_completed.py)。[发布与哈希记录](../../../../outputs/visualization_publishing/{STAGE.name}/activation.json)。\n")
    print(record['url'])


if __name__=='__main__':
    build()
    publish()
