"""Publish the five 120-move recovery runs and retain the preceding 60-move replay."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'run_20261126_06_four_region60'))
import export_completed as previous
import publish_return_cases as replay

BASE = previous.STAGE
STAGE = replay.PUBLISHED / 'codex_branch120_five_cases_web_20261126_01'
BATCH = replay.ROOT / 'outputs/inverse_rollback/codex_tools_v001' / HERE.name
PROMPT = """请控制机器人回到回退点 {checkpoint}。

结合历史观测，确认当前位置符合回退点定义，并且能看清当时从该回退点看到的其他支路。不强求精确复现原来的位置和朝向，在原来位置附近区域即可。

回到该区域后，结合原始导航指令、已完成的路段和当前观测，判断哪条支路符合指令接下来的要求。可以转身查看各个入口。确定正确支路后，穿过入口，并通过新的第一人称观测确认机器人已进入该支路。此时即可结束本轮，无需继续走到原始导航任务的终点。

如果查看各个方向后仍看不到合适的支路，或现有证据不足以判断该走哪一条，就沿已走过的路线回到历史记录中再上一个有效回退点。在那里重复同样的过程，直到确认已经进入正确支路。如果已经没有更早的有效回退点，且依然无法选路，结束尝试并说明原因。

使用 observe() 查看当前前视画面。使用 step("forward")、step("turn_left") 或 step("turn_right") 移动或转向。到达回退点后继续选路；只有确认机器人已经进入正确支路，才调用 step("finish_return")。

整轮共用 120 步移动预算，包括所有回退、转向和进入支路的移动。每次前进或转向计一步。观察和声明完成不计步。如果用完 120 步仍无法确认已进入正确支路，结束尝试并报告进展。"""

ZH = {
    'C11': {
        0:'我会朝 S05 回退，查看可选路线，再确认已进入指令所支持的支路。',
        16:'转离墙面后看到了客厅的窗户和电视。我会回到 S05 开阔的地面区域，先对照客厅和餐区两条路线再作选择。',
        23:'我已回到 S05 附近开阔的选路区域，也看过了餐区和客厅两侧。客厅侧通道通向窗户，电视在左，符合指令余下部分。我会进入这条通道，然后从里面查看画面。',
        29:'已回到 S05 附近，检查了两条路线，并进入通往窗户的客厅侧通道。新的观测确认已进入，电视在左，窗户在前。\n\n已调用 `finish_return`。120 步预算共用了 26 步。'},
    'C17': {
        0:'我会先查看当前画面，回到 S09 的走廊尽头交汇处，查看右侧入口后再进入。',
        12:'画面恢复可见，确认机器人仍在走错的卧室内。我正转身寻找通往走廊的出口；剩余 109 步移动预算。',
        34:'我已回到走廊尽头交汇处附近。因为现在面朝走廊来路，另一间卧室的入口在我左侧；这对应原行进方向所要求的右转。我会查看它的地标和相邻入口。',
        59:'机器人靠近门框边缘，挡住了邻侧书房的视野。我会再往交汇处移动一点，以便看清后再进入另一间卧室。',
        76:'另一间卧室的左侧有要求的六边形置物架和书桌，前方是床和带窗帘的窗户。这确认了从 S09 出发应走的支路。我会跨过门槛，在里面获取新的观测。',
        84:'已回到 S09 附近并进入正确支路，即从原行进方向看位于右侧的房间。F172 的新观测确认，六边形架和书桌在左，床和带窗帘的窗户在前。\n\n已调用 `finish_return`。120 步预算共用了 81 步。'},
    'C43': {
        0:'我会先找导航控制工具，沿来路退回 F30 区域，检查另一个入口后再进入。',
        21:'我已朝门口区域退回。反方向的视野显示了更远处的另一个房间，我正查看各个入口，以确定 F30 的选路位置。',
        44:'我已回到 F30 附近，能看到通往卧室的路线和左侧开口。左侧现在看起来是一个封闭的小凹间，看不到通往餐区或客厅的路线。我会回到更早保留的回退点 S03，再查看那里的选项。',
        63:'在先前的平台处，我能看到浴室和卧室的入口，以及书房旁先前画面中没有露出的走廊。透过走廊能看到右侧的餐椅，符合指令。我会进入这条走廊，查看左侧是否为客厅。',
        83:'新观测确认我进入了正确支路：右侧是餐区家具，左侧有沙发和电视。我会在这里结束本轮回退。',
        84:'已回到 S04 附近，查看了各条支路，随后因为 S04 的另一个开口看起来是封闭的，又回溯到 S03。\n\n已进入通往开放房间的走廊。新观测确认餐区家具在右，沙发和电视在左。已调用 `finish_return`。\n\n120 步预算共用了 80 步。'},
    'C23': {
        0:'我会先找导航控制工具，回到 S02 区域，查看各条支路后再选择入口。',
        16:'我已回到 S02 附近，可以看到电视墙旁的门口和右手侧的入口。沿客厅回望能看到一个带帘的开口，后面有一把棕色椅子。走那条路线时电视和电视柜都在右侧，所以我会查看并接近它。',
        37:'电视和电视柜现在位于我右后方。我正接近带帘的门口，后面有那把棕色椅子；我会寻找盆栽，并通过新的观测确认是否已经进入。',
        59:'已回到 S02 附近，经过右侧的电视与电视柜，接近了带帘的门口。入口后方可见一把棕色椅子。\n\n在我能确认进入前，仿真于 F73 进入 `physical_terminal` 状态。我没有调用 `finish_return`。120 步预算共用了 56 步，本次尝试未完成。'},
    'C20': {
        0:'我会朝 S03 回退，查看可选入口；如果在那里无法辨认出卧室支路，就使用更早的回退点。',
        20:'我已到 S03 的客厅交汇处附近，看到了座椅区和相连的通道。转身后还看到了通向更早回退点的走廊。我尚未在这里辨认出所需卧室，所以会沿走廊回溯，查看沿途入口。',
        39:'我沿走廊回溯，经过 S02 的浴室，到达 S01 区域。这里仍可选择两侧的房间或走廊。原行进方向左侧的卧室现在位于我右侧。我会先查看里面有没有书桌和六边形架，再进入。',
        54:'新观测确认我已在卧室里，床在右，书桌和六边形架在左。这与指令吻合，我将标记恢复完成。',
        55:'恢复完成。查看 S03 后，我经 S02 回溯至 S01 并进入了卧室。新观测确认床在右，书桌和六边形架在左。\n\n确认后已调用 `finish_return`。'}}
# These boundaries are model statements after a tool call, not inferred geometric crossings.
EVENTS = {
    'C11': [(23,'S05 · 模型选中客厅侧通道','S05 · Model selected the living-side passage'),(28,'通道内的新观测','New view inside the passage')],
    'C17': [(34,'模型报告回到走廊交汇处','Model reported returning to the hallway junction'),(76,'S09 · 模型决定跨过卧室门槛','S09 · Model decided to cross the bedroom threshold'),(83,'卧室内的新观测','New view inside the bedroom')],
    'C43': [(44,'S04 → S03 · 模型决定继续回溯','S04 → S03 · Model decided to retrace farther'),(63,'模型在更早的平台选择书房旁的走廊','Model selected the corridor beside the study at the earlier landing'),(83,'进入后核对餐区、沙发和电视','Dining area, sofas and TV checked after entry')],
    'C23': [(16,'S02 · 模型选择带帘开口','S02 · Model selected the curtained opening'),(37,'接近门口，尚待确认','Approaching the doorway; entry unconfirmed'),(57,'F73 · 前进时跌倒','F73 · Fall during a forward move'),(58,'终止后再次前进被拒绝','Forward request rejected after termination'),(59,'F73 · 最后一次原生观测','F73 · Last native observation')],
    'C20': [(20,'S03 · 模型决定沿走廊继续回溯','S03 · Model decided to retrace the hallway'),(39,'模型报告经 S02 回到 S01，开始查看卧室','Model reported passing S02 and reaching S01 to inspect the bedroom'),(54,'卧室内的新观测','New view inside the bedroom')]}
PHASES = {
    'C11': (['S05'],None,23), 'C17': (['S09'],None,76),
    'C43': (['S04','S03'],44,63), 'C23': (['S02'],None,16), 'C20': (['S03','S02','S01'],20,39)}
OUTCOME = {
    'C11': ['模型报告从 S05 进入了通往窗户的客厅侧通道。','The model reported entering the living-side passage toward the window from S05.'],
    'C17': ['模型报告从 S09 进入了原行进方向右侧的卧室。','The model reported entering the bedroom on the right of the original approach from S09.'],
    'C43': ['模型报告 S04 的另一开口看起来封闭，于是退到 S03，转入通往开放房间的走廊。','The model reported that the alternative opening at S04 appeared enclosed. It retraced to S03 and entered the corridor toward the open room.'],
    'C23': ['第 56 步前进时仿真记录跌倒（现场 F73），入门尚未确认。原始报警在 F17，原版导航终止于 F32。','The simulator recorded a fall on forward move 56 (live F73) before branch entry was confirmed. The original alarm was at F17; original navigation ended at F32.'],
    'C20': ['模型报告从 S03 经 S02 回到 S01，再进入卧室。','The model reported retracing from S03 through S02 to S01 and entering the bedroom.']}


def build():
    (STAGE/'assets').mkdir(parents=True)
    for path in (BASE/'assets').iterdir():
        os.link(path,STAGE/'assets'/path.name)
    html=(BASE/'index.html').read_text()
    legacy=json.loads(replay.MARK.search(html)[2])['replays']
    reviews=json.loads(replay.MARK.search((replay.REVIEW/'index.html').read_text())[2])
    packs={}
    for case in replay.read(HERE/'cases.json'):
        cid=case['case']
        run=BATCH/cid
        r=replay.read(run/'result.json')
        timing=replay.read(run/'timing.json')
        entered=r['endpoint_declared']
        verdict=['模型声明已进入支路','Model declared branch entry'] if entered else ['跌倒终止 · 未确认进入','Fall · entry unconfirmed']
        times=[timing[k] for k in ('placement_elapsed_s','controller_elapsed_s','case_elapsed_s')]
        pl,ctrl,total=map(previous.duration,times)
        ple,ctrle,totale=[previous.duration(s,True) for s in times]
        seconds=round(times[-1])
        notice=[OUTCOME[cid][0]+f' 摆位 {pl}，控制 {ctrl}，总计 {total}。',
                OUTCOME[cid][1]+f' Placement took {ple}, control took {ctrle}, and total elapsed time was {totale}.']
        summary=dict(verdict=verdict,footer=legacy[cid]['summary']['footer'],notice=notice,events=list(EVENTS[cid]))
        zh=PROMPT.format(checkpoint=f"{case['target_node']}（F{case['target_frame']}）")
        pack=replay.build_case(reviews,cid,run,STAGE,ZH[cid],zh,summary,include_rejected=True)
        if entered:
            summary['events'].append([len(pack['calls']),f"R{r['movements']} · 声明已进入支路",f"R{r['movements']} · Branch entry declared"])
        chain,earlier,entry=PHASES[cid]
        pack['recovery']=dict(checkpoints=chain,earlierCall=earlier,entryCall=entry,stop=r['native_terminal'] or r['stop_reason'],
                              elapsed=f'{seconds//60}:{seconds%60:02d}')
        packs[cid]=pack
    replay.write_replay(packs,html,STAGE,BASE,versions={'return60':legacy})


def publish():
    replay.publish_assets(STAGE,previous.ACTIVATE,dict(correct=replay.LIVE,previous_sha=hashlib.sha256((BASE/'index.html').read_bytes()).hexdigest()))
    url='http://134.175.18.101/vln/'+replay.LIVE+'/'
    record=dict(utc=datetime.now(timezone.utc).isoformat(),entry=url+'index.html',download=url+'replay.zip',
                html_sha256=hashlib.sha256((STAGE/'index.html').read_bytes()).hexdigest(),
                zip_sha256=hashlib.sha256((STAGE/'replay.zip').read_bytes()).hexdigest())
    (STAGE/'activation.json').write_text(json.dumps(record,indent=2)+'\n')
    print(record['entry'])


if __name__=='__main__':
    build()
    if '--build-only' not in sys.argv:
        publish()
