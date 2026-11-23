"""Export the completed RxR-CE and H1 round trips with paired measured RGB."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import shutil

from PIL import Image
from export_inverse_rollback_replay import DATA, NODES, ROOT, ROUTES, point, read


BASE = ROOT / 'outputs/inverse_rollback'
RXR = BASE / 'rxr_ce_v001/run_20261122_01_rgb20'
H1 = {'turn': BASE / 'v001/run_20261122_03_rgb22', 'back': BASE / 'v002/run_20261122_01_backward_rgb22'}
H1_ACTIONS = {None: 'start', 0: 'stop', 1: 'move_forward', 2: 'turn_left', 3: 'turn_right', 4: 'move_backward'}


def json_text(data):
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('</', '<\\/')


def lines(path):
    with path.open() as source:
        for row in source:
            yield json.loads(row)


class Export:
    def __init__(self, out):
        self.out = out
        out.mkdir(parents=True, exist_ok=False)
        (out/'maps').mkdir()
        (out/'cases').mkdir()
        self.images = {}
        self.index = []

    def frame(self, case, leg, i, source, pose, action, **extra):
        rel = f'frames/{case}/{leg}/{i:04}.webp'
        self.images[rel] = (source, extra.pop('sha', None))
        return dict(p=pose, img=rel, act=action, **extra)

    def write_case(self, c, group):
        for leg in c['legs'].values():
            if not leg:
                raise ValueError(f'Empty leg in {c["id"]}')
        (self.out/'cases'/f'{c["id"]}.js').write_text('loadRoundtrip(' + json_text(c) + ');\n')
        self.index.append(dict(id=c['id'],group=group,scene=c['scene'],
                               passed={k:v['pass'] for k,v in c['metrics'].items()}))

    def convert(self, item):
        relative,(path,sha) = item
        data = path.read_bytes()
        if sha and hashlib.sha256(data).hexdigest() != sha:
            raise ValueError(f'RGB checksum mismatch: {path}')
        dest = self.out/relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(io.BytesIO(data)) as im:
            im.convert('RGB').save(dest,format='WEBP',quality=84,method=2)


def results(run):
    status, summary = read(run/'status.json'), read(run/'summary.json')
    if status['phase'] != 'complete' or summary['completed_pairs'] != summary['total']:
        raise ValueError(f'Incomplete run: {run}')
    return {p['case_id']:p for p in summary['pairs']}


def metric(row, key):
    return {'m':row[key], 'deg':row['yaw_deg'], 'pass':row['passed'], 'fall':row.get('reason')=='fall'}


def rxr(export):
    rows = results(RXR)
    for case in read(RXR/'manifest.json')['cases']:
        cid = case['case_id']
        r = rows[cid]
        src = RXR/'cases'/cid/r['attempt']
        geom = read(src/'map.json')
        low = geom['bounds_xyz'][0]
        res = geom['meters_per_pixel']
        map_image = f'maps/{cid}.png'
        with Image.open(src/'map.png') as im:
            # Preserve every measured navigable cell and give the tracks a light background.
            im.convert('L').point(lambda n: 250 if n else 216).save(export.out/map_image)
            width,height = im.size
        def projected(p):
            x,_,z = p['xyz']
            return [round((x-low[0])/res,3),round((z-low[2])/res,3),round(-90-p['yaw_deg'],4)]
        legs = {}
        for key,leg in [('out','outbound'),('turn','turnaround'),('back','backward')]:
            seq = []
            for f in lines(src/leg/'trace.jsonl'):
                seq.append(export.frame(cid,key,f['step'],src/leg/f['rgb'],projected(f['pose']),
                        f['action'] or 'start', collision=f['collided']))
            expected = r['outbound_rgb_frames'] if key=='out' else r['arms'][leg]['rgb_frames']
            if len(seq) != expected: raise ValueError(f'Incomplete RGB leg: {cid}/{leg}')
            legs[key] = seq
        export.write_case(dict(id=cid,scene=Path(case['scene']).stem,ab=r['actual_ab_xz_m'],
            map=dict(src=map_image,w=width,h=height,res=res), legs=legs,
            metrics={k:metric(r['arms'][v],'xz_m') for k,v in [('turn','turnaround'),('back','backward')]}),'rxr')


def h1(export):
    tasks = (ROUTES/'exports/replay_20261118_01/tasks.js').read_text()
    instructions = {t['id']:t['instruction'] for t in json.loads(tasks.removeprefix('const REPLAY = ').strip().removesuffix(';'))['tasks']}
    retained = read(NODES)
    manifests = {k:{c['case_id']:c for c in read(path/'manifest.json')['cases']} for k,path in H1.items()}
    scores = {k:results(path) for k,path in H1.items()}
    if set(manifests['turn']) != set(manifests['back']): raise ValueError('H1 case sets differ')
    for cid,case in manifests['turn'].items():
        if any(case[k]!=manifests['back'][cid][k] for k in ('episode_id','checkpoint_step','alarm_step','scene','history')):
            raise ValueError(f'Unpaired H1 interval: {cid}')
        eid,scene = case['episode_id'],case['scene']
        a,b = case['checkpoint_step'],case['alarm_step']
        folder = ROUTES/'geometry'/scene
        geom = read(folder/'geometry.json')
        map_image = f'maps/{scene}.png'
        if not (export.out/map_image).exists(): shutil.copyfile(folder/'floorplan.png',export.out/map_image)
        res = geom['resolution']
        def projected(p):
            return [round((p[0]-geom['low'][0])/res,3),round((geom['high'][1]-p[1])/res,3),-p[3]]
        nodes = {n['index']:n['id'] for n in retained[eid]}
        following = min((step for step in nodes if step>b), default=b)
        markers,after,legs,metrics = [],[],{'out':[]},{}
        for obs in lines(DATA/'inputs'/eid/'observations.jsonl'):
            i = obs['step']
            if i<a: continue
            if i>following: break
            q = obs['robot_pose']
            p = projected(point(q['position_world_m'],q['quaternion_wxyz']))
            if i in nodes: markers.append(dict(p=p,label=nodes[i],step=i))
            if i>=b: after.append(p)
            if i<=b:
                action = H1_ACTIONS[case['history'][i-a-1]] if i>a else 'start'
                legs['out'].append(export.frame(cid,'out',i-a,DATA/obs['native_front']['image'],p,action,origin=i))
        if len(legs['out']) != b-a+1: raise ValueError(f'Missing history in {cid}')
        for key,run in H1.items():
            folder = run/'cases'/cid
            for arm,name in [('inverse',key),('reset','reset_'+key)]:
                seq = [read(folder/(arm+'_start.json'))]
                if arm=='inverse': seq.extend(lines(folder/'inverse_trace.jsonl'))
                seq.append(read(folder/(arm+'.json')))
                metrics[name] = metric(scores[key][cid][arm],'xy_m')
                frames = []
                for i,row in enumerate(seq):
                    rgb = row['rgb']
                    pose = projected(point(row['position'],row['orientation']))
                    action = H1_ACTIONS.get(row.get('action')) if i<len(seq)-1 else ('reset' if arm=='reset' else 'endpoint')
                    extra = dict(tick=rgb['simulation_step'],sha=rgb['sha256'])
                    if i==0:
                        root = [v-off for v,off in zip(row['position'][:2],case['historical_offset'][:2])]
                        extra['gap'] = round(math.dist(root,rgb['camera_pose']['position_world_m'][:2]),3)
                    frames.append(export.frame(cid,name,i,folder/rgb['file'],pose,action,**extra))
                legs[name] = frames
        export.write_case(dict(id=cid,eid=eid,scene=scene,ab=case['ab_xy_m'],a=a,b=b,
            map=dict(src=map_image,w=geom['width'],h=geom['height'],res=res),legs=legs,metrics=metrics,
            instruction=instructions[eid],nodes=markers,after=after),'h1')


def export_data(out):
    export=Export(out)
    rxr(export)
    h1(export)
    print(f'{len(export.index)} cases, {len(export.images)} recorded frames',flush=True)
    with ThreadPoolExecutor(max_workers=8) as workers:
        for _ in workers.map(export.convert,export.images.items()): pass
    report=dict(cases=len(export.index),frames=len(export.images),created_utc=datetime.now(timezone.utc).isoformat(),
                runs=[str(p.relative_to(ROOT)) for p in [RXR,*H1.values()]])
    (export.out/'catalog.js').write_text('const catalog = '+json_text(export.index)+';\n')
    assets=['catalog.js','player.js']+sorted(p.relative_to(export.out).as_posix() for sub in ['cases','maps','frames'] for p in (export.out/sub).rglob('*') if p.is_file())
    (export.out/'online_manifest.json').write_text(json_text(dict(html='index.html',assets=assets)))
    (export.out/'export.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report,flush=True)


def export_player(out):
    from fontTools import subset
    from fontTools.ttLib import TTFont
    template=ROOT/'core/roundtrip_comparison.html'
    player=ROOT/'core/roundtrip_comparison.js'
    config=read(ROOT/'core/crossing_visualization_template.json')
    chars=set(template.read_text()+player.read_text())
    for path in (out/'cases').glob('*.js'):
        chars.update(path.read_text())
    with TTFont(config['font'],fontNumber=0) as font:
        sub=subset.Subsetter()
        sub.populate(text=''.join(sorted(chars)))
        sub.subset(font)
        font.save(out/'replay.ttf')
    notice=Path(config['font_license']).read_text().replace('--','—')
    (out/'index.html').write_text(template.read_text().replace('</html>','<!-- '+notice+' --></html>'))
    shutil.copyfile(ROOT/'core/roundtrip_comparison.js',out/'player.js')
    manifest=read(out/'online_manifest.json')
    if 'replay.ttf' not in manifest['assets']:
        manifest['assets'].append('replay.ttf')
        (out/'online_manifest.json').write_text(json_text(manifest))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    export_data(args.output)
    export_player(args.output)
