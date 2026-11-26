"""Build the single-case bilingual replay from the published template and native H1 receipts."""
import base64
import hashlib
import json
import math
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TEMPLATE = ROOT / 'outputs/visualization_publishing/codex_deviation_v002_astra_terra_web_20261126_01'
RUN = ROOT / 'outputs/inverse_rollback/codex_tools_v001/run_20261126_04_c11_f57_f45'
HOLD = ROOT / 'outputs/inverse_rollback/pose_hold/run_20261126_03_f57'
OUT = ROOT / 'outputs/inverse_rollback/exports' / HERE.name / 'release01'
REVIEW_JS = ROOT / 'experiments/deviation_progress/codex_memory_v002/run_20261125_01_terminal4/exports/map_layers_01/extension.js'
sys.path.insert(0, str(ROOT/'scripts'))
from export_oracle_distance_replay import add_font

def read(path):
    return json.loads(path.read_bytes())

def uri(path):
    kind = {'.webp': 'image/webp', '.png': 'image/png'}[path.suffix]
    return 'data:'+kind+';base64,'+base64.b64encode(path.read_bytes()).decode()

def yaw(q):
    w,x,y,z = q
    return math.degrees(math.atan2(2*(w*z+x*y),1-2*(y*y+z*z)))

EN = [
    'I will first look at the current front view, then use the positions of the wooden chair, white wall and cabinetry at F45 to decide which way to return.',
    'I have not yet returned to S05 (F45). I called `observe()`, but the tool repeatedly reported errors when I tried to turn left. I am at F58 with the status `action_incomplete`, and the view is still mostly a white wall.\n\nI cannot confirm arrival, so I did not call `finish_return`. Movement access needs to be restored before continuing the return.',
    'I will first look at the current view and then continue returning to S05 (F45).',
    'Turning is working normally again, and I can now see the sofa and television. Next I will continue turning toward the open space away from the wall, move back near F45 and check the positions of the wooden chair and cabinetry relative to each other.',
    'I am still close to the white wall. Moving forward just now did not create enough distance. I will look for open space on the cabinet side and continue adjusting my position.'
]
def build():
    src = (TEMPLATE/'index.html').read_text()
    bundle = json.loads(re.search(r'<script id="payload" type="application/json">(.*?)</script>', src,re.S)[1])
    c, = [v for v in bundle['cases'] if v['case_id']=='C11']
    result = read(RUN/'result.json')
    assert c['episode_id']==result['episode_id'] and c['end']==57 and c['rounds'][-1]['a']==45
    images = {}
    grid = bundle['maps'][c['scene']]
    for key in {f['image'] for f in c['frames']} | {grid['image']}:
        images[key]=uri(TEMPLATE/bundle['images'][key])
    steps = (ROOT/result['target_source']).parents[1]
    for f in c['frames']:
        m=read(steps/f"{f['frame']:06d}"/'metadata.json')
        assert m['step']==f['frame'] and m['robot_pose']['position_world_m']==f['position']
        f['heading']=m['robot_pose']['heading_deg']
    calls=[]; notes=[]; moved=0
    for stage,(folder,events) in enumerate([(HOLD/'live',RUN/'codex-events.jsonl'),(RUN/'continued',RUN/'continued-events.jsonl')]):
        receipts=[json.loads(l) for l in (folder/'calls.jsonl').read_text().splitlines()]
        consumed=0
        for line in events.open():
            if not line.endswith('\n'):continue
            event=json.loads(line); item=event.get('item',{})
            if event['type']!='item.completed':continue
            if item['type']=='agent_message':
                notes.append(dict(call=len(calls),text=[item['text'].strip(),EN[len(notes)]]))
                continue
            if item['type']!='mcp_tool_call':continue
            assert item['server']=='vlnverse'
            op=item.get('arguments',{}).get('action') or item['tool']
            failed=item['status']=='failed'
            receipt=receipts[consumed] if consumed<len(receipts) else None
            if failed and not (receipt and receipt.get('error') and receipt['action']==op):
                assert calls and stage==0 and op=='turn_left'
                calls.append(dict(calls[-1],op=op,failed=True,executed=False,feedback=False,
                                  stage=stage,taskTicks=0,worldTicks=0,utc=None,seq=None))
                continue
            consumed+=1
            assert receipt and (receipt['action'] or receipt['method'])==op
            if not failed:
                result_block=next(b for b in item['result']['content'] if b['type']=='text')
                assert json.loads(result_block['text'])==receipt['result']
            before,after=receipt['before'],receipt['after']
            delta=after['task_ticks']-before['task_ticks']
            acted=op!='observe' and delta>0
            moved+=int(acted)
            png=folder/'frames'/f"{receipt['sequence']:05d}.png"
            key=hashlib.sha256(png.read_bytes()).hexdigest()
            if receipt.get('rgb'):assert key==receipt['rgb']['sha256']
            if key not in images:images[key]=uri(png)
            calls.append(dict(op=op,failed=failed,executed=acted,feedback=not failed,stage=stage,
                              seq=receipt['sequence'],image=key,position=after['position'],
                              heading=yaw(after['quaternion_wxyz']),motion=moved,live=57+moved,
                              taskTicks=delta,worldTicks=after['world_ticks']-before['world_ticks'],
                              utc=receipt['finished_utc'],distance=math.dist(after['position'][:2], result['target_position'][:2])))
        assert consumed==len(receipts)
    assert moved==result['movements']==55 and len(calls)==60 and len(notes)==5
    prompt=(ROOT/'experiments/inverse_rollback/codex_tools_v001'/RUN.name/'prompt.txt').read_text().strip()
    data=dict(cases=[c],images=images,grid=grid,calls=calls,notes=notes,result=result,
              prompt=[prompt,'Control the robot and return to S05 (F45). Use observe() to see the current front view. Move using step("forward"), step("turn_left") or step("turn_right"). Use the earlier observations at the checkpoint and the live views returned by your actions to decide how to move. Once you confirm arrival, call step("finish_return") to end the return.'],
              resume=[read(RUN/'continuation.json')['cmd'][-1],'Movement access has been restored. Continue the same return task from your current position.'])
    render(data, src, OUT)

def render(data, src, output):
    c, = data['cases']
    calls = data['calls']
    html=(HERE/'page.html').read_text()
    if 'summary' in data:
        from html import escape
        for tag, css_class, key in [('div', 'notice', 'notice'), ('footer', 'foot muted', 'footer')]:
            zh, en = map(escape, data['summary'][key])
            html = re.sub(fr'<{tag} class="{css_class}" data-en="[^"]*">[^<]*</{tag}>',
                          f'<{tag} class="{css_class}" data-en="{en}">{zh}</{tag}>', html, count=1)
    css='\n'.join(x[1] for x in re.findall(r'<style([^>]*)>(.*?)</style>',src,re.S) if 'embedded-font' not in x[0])
    source=REVIEW_JS.read_text()
    panel=source[source.index('function make('):source.index('function setupTerminalReplay(')]
    js=(HERE/'page.js').read_text().replace('/* ORIGINAL REVIEW PANEL */',panel)
    html=html.replace('/* TEMPLATE CSS */',css).replace('/* REPLAY JS */',js).replace('/* PAYLOAD */',json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False).replace('<','\\u003c'))
    output.mkdir(parents=True,exist_ok=False)
    path=output/'index.html';path.write_text(html)
    add_font(path)
    metadata=dict(historical_frames=len(c['frames']),calls=len(calls),movements=data['result']['movements'],
                  receipt_rows=sum(x['seq'] is not None for x in calls),rounds=len(c['rounds']),
                  template_sha256=hashlib.sha256((TEMPLATE/'index.html').read_bytes()).hexdigest(),
                  html_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (output/'export.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(metadata)
if __name__=='__main__':build()
