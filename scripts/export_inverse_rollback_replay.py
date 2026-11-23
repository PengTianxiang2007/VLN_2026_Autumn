"""Build a bilingual, self-contained replay of the completed physical return pairs."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ROUTES = ROOT/'outputs/offline_route_dataset/v001/run_20261118_01'
DATA = ROUTES/'dataset'
NODES = ROOT/'outputs/deviation_progress/v006/all53_20261121_01/retained_nodes_and_terminals.json'
PAIR = ROOT/'outputs/inverse_rollback/v001/run_20261122_02'


def read(p):
    return json.loads(p.read_bytes())


def data_uri(kind, data):
    return 'data:' + kind + ';base64,' + base64.b64encode(data).decode('ascii')


def point(position, q):
    w,x,y,z = q
    yaw = math.degrees(math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z)))
    return [*(round(float(x),6) for x in position), round(yaw,4)]


def build(out, run=PAIR, case_ids=None):
    status, summary, manifest = (read(run/name) for name in ('status.json','summary.json','manifest.json'))
    selected = manifest['cases']
    if case_ids:
        completed = {p['case_id'] for p in summary['pairs']}
        if len(set(case_ids)) != len(case_ids) or not set(case_ids) <= completed:
            raise ValueError('Each requested case must be a distinct, completed pair')
        selected = [c for c in selected if c['case_id'] in case_ids]
    elif status['phase'] != 'complete' or summary['completed_pairs'] != len(selected):
        raise ValueError('Physical pairs incomplete')
    original = (ROUTES/'exports/replay_20261118_01/tasks.js').read_text()
    old_tasks = json.loads(original.removeprefix('const REPLAY = ').strip().removesuffix(';'))['tasks']
    instructions = {t['id']:t['instruction'] for t in old_tasks}
    retained = read(NODES)
    cases, maps, media = [], {}, {}
    historical_count = 0
    for case in selected:
        cid, eid, scene = case['case_id'], case['episode_id'], case['scene']
        a,b = case['checkpoint_step'], case['alarm_step']
        if scene not in maps:
            folder = ROUTES/'geometry'/scene
            geom = read(folder/'geometry.json')
            maps[scene] = {k:geom[k] for k in ('width','height','low','high','resolution')}
            maps[scene]['image'] = data_uri('image/png',(folder/'floorplan.png').read_bytes())
        source = run/'cases'/cid
        nodes = retained[eid]
        following = next((n['index'] for n in nodes if n['index']>b), b)
        observations = []
        with (DATA/'inputs'/eid/'observations.jsonl').open() as f:
            for line in f:
                ob = json.loads(line)
                if ob['step']>following:
                    break
                if ob['step']>=a:
                    observations.append(ob)
        history, after = [], []
        for ob in observations:
            pose = ob['robot_pose']
            p = point(pose['position_world_m'],pose['quaternion_wxyz'])
            step = ob['step']
            if step >= b:
                after.append(p)
            if step <= b:
                asset = ob['native_front']
                key = f'{cid}/f{step}'
                with Image.open(DATA/asset['image']) as im:
                    buf = io.BytesIO()
                    im.convert('RGB').save(buf,format='WEBP',quality=82,method=2)
                media[key] = data_uri('image/webp',buf.getvalue())
                history.append(dict(p=p, image=key, index=step, action=None if step==a else case['history'][step-a-1]))
                historical_count += 1
        assert len(history)==b-a+1
        def frame(record, index, action=None):
            f = dict(p=point(record['position'],record['orientation']),index=index,action=action)
            if manifest.get('capture_rgb'):
                rgb = record['rgb']
                key = f"{cid}/{rgb['file']}"
                pixels = (source/rgb['file']).read_bytes()
                if hashlib.sha256(pixels).hexdigest() != rgb['sha256']:
                    raise ValueError(f'RGB hash mismatch: {key}')
                media[key] = data_uri('image/png', pixels)
                f.update(image=key, tick=rgb['simulation_step'])
                if index == 0:
                    # The simulator runs one environment at the origin. Root
                    # samples are in the historical coordinate frame.
                    root_xy = [record['position'][i] - case['historical_offset'][i] for i in range(2)]
                    f['cameraGap'] = math.dist(root_xy, rgb['camera_pose']['position_world_m'][:2])
            return f
        trace = [json.loads(l) for l in (source/'inverse_trace.jsonl').read_text().splitlines()]
        inv, reset = (read(source/(method+'.json')) for method in ('inverse','reset'))
        inverse_frames = [frame(r,r['index'],r['action']) for r in trace]
        inverse_frames.append(frame(inv,len(trace)+1))
        metrics = {arm:{k:r[k] for k in ('xy_m','yaw_deg','ended','reason','passed')}
                   for arm,r in [('inverse',inv),('reset',reset)]}
        points = {r['step']:point(r['robot_pose']['position_world_m'],r['robot_pose']['quaternion_wxyz'])
                  for r in observations}
        starts = {arm: frame(read(source/(arm+'_start.json')),0) for arm in ('inverse','reset')} if manifest.get('capture_rgb') else {}
        cases.append(dict(id=cid,eid=eid,scene=scene,a=a,b=b,next=following,node=case['node'],
             starts=starts,ab_xy_m=case.get('ab_xy_m', math.dist(history[0]['p'][:2],history[-1]['p'][:2])),
             nodes=[dict(id=n['id'],f=n['index'],p=points[n['index']]) for n in nodes if a <= n['index'] <= following],
             instruction=instructions[eid],history=history,after=after,inverse=inverse_frames,
             reset=frame(reset,1),metrics=metrics,planned=len(case['inverse']),executed=len(trace)))
    template = ROOT/'core/inverse_rollback_replay.html'
    player = ROOT/'core/inverse_rollback_replay.js'
    counts = {arm: dict(passed=sum(c['metrics'][arm]['passed'] for c in cases)) for arm in ('inverse','reset')}
    data = dict(cases=cases,maps=maps,media=media,summary=counts,captureRGB=manifest.get('capture_rgb',False))
    page = template.read_text().replace('/*__PLAYER__*/',player.read_text())
    # Bundle the relevant CJK characters for desktop and offline Linux browsers.
    from fontTools import subset
    from fontTools.ttLib import TTFont
    font_config = read(ROOT/'core/crossing_visualization_template.json')
    chars = page + ''.join(''.join(c['instruction']) for c in cases)
    with TTFont(font_config['font'],fontNumber=0) as font:
        sub = subset.Subsetter()
        sub.populate(text=''.join(set(chars)))
        sub.subset(font)
        buf=io.BytesIO()
        font.save(buf)
    page=page.replace('__FONT__',data_uri('font/ttf',buf.getvalue()))
    page=page.replace('<!--__FONT_LICENSE__-->', '<!-- '+Path(font_config['font_license']).read_text().replace('--','—')+' -->')
    encoded=json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False).replace('</','<\\/')
    html = out/'index.html'
    out.mkdir(parents=True,exist_ok=True)
    with html.open('x') as f:
        f.write(page.replace('/*__DATA__*/',encoded))
    sources=[template,player,Path(__file__)]
    report=dict(cases=len(cases),scenes=len(maps),historical_frames=historical_count,
                reconstructed_frames=0,inverse_actions=sum(c['executed'] for c in cases),
                case_ids=[c['id'] for c in cases],rollback_rgb_frames=len(media)-historical_count,
                created_utc=datetime.now(timezone.utc).isoformat(),source_run=str(run.relative_to(ROOT)),
                git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                sources_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                html_sha256=hashlib.sha256(html.read_bytes()).hexdigest())
    (out/'export.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('export',type=Path)
    p.add_argument('--run',type=Path,default=PAIR)
    p.add_argument('--cases',nargs='+',metavar='CASE')
    args=p.parse_args()
    build(args.export.resolve(),args.run.resolve(),args.cases)
