"""Read-only source audit and visual evidence for current multiview failures.

Distances propose review windows; no semantic labels are assigned here.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.analyze_oracle_baseline_failures import project, spans, draw_card


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def font(size):
    return ImageFont.truetype(read(ROOT/'core/crossing_visualization_template.json')['font'], size)


def candidates(xy, distance, arc):
    result = []
    for span in spans(distance >= .75, xy):
        start, end = span['start'], span['end']
        anchor = start
        while anchor > 0 and distance[anchor] > .35:
            anchor -= 1
        peak = start + int(np.argmax(distance[start:end+1]))
        result.append(dict(anchor_step=anchor, confirmation_step=start, peak_step=peak,
                           end_step=end, max_distance_m=float(distance[peak]),
                           excursion_walk_m=float(np.linalg.norm(np.diff(xy[anchor:end+1], axis=0), axis=1).sum()),
                           recovered_near_reference=end < len(xy)-1))
    return result


def evidence_card(case, out, extra_steps=None, tag='default'):
    records = [json.loads(x) for x in Path(case['steps_source']).read_text().splitlines()]
    proposals = case['candidate_events']
    if extra_steps is None:
        if proposals:
            primary = max(proposals, key=lambda x: x['excursion_walk_m'] * min(x['max_distance_m'], 3))
            steps = [primary['anchor_step'], primary['confirmation_step'], primary['peak_step']]
        else:
            steps = [0, len(records)//2, len(records)-1]
        steps = sorted(set(steps + [len(records)-1]))
    else:
        steps = sorted(set(min(max(0,int(x)),len(records)-1) for x in extra_steps))
    width = 1680
    rows = len(steps)
    height = 210 + rows*248
    panel = Image.new('RGB',(width,height),'white');draw=ImageDraw.Draw(panel)
    title=f"{case['number']:02d} {case['episode_id']} | {case['score']['fail_reason']} | NE={case['score']['NE']:.2f} | {case['features']['actions']} actions"
    draw.text((12,8),title,font=font(22),fill='#162c42')
    for i,line in enumerate(textwrap.wrap(case['instruction'],155)):
        draw.text((12,43+i*24),line,font=font(17),fill='#23354b')
    for row,step in enumerate(steps):
        record=records[step];folder=Path(record['frame_directory']);y=210+row*248
        draw.text((12,y),f"step {step} | heading={record['robot_pose']['heading_deg']:.1f} | off={case['route_distances_m'][step]:.2f}m | arc={case['nearest_reference_arc_m'][step]:.2f}m | action={record['action']}",font=font(17),fill='#102d4d')
        paths=[('native front',folder/record['front_image'])]
        for label,ix in [('left +90',2),('left-front +45',1),('forward 0',0),('right-front -45',7),('right -90',6),('back 180',4)]:
            paths.append((label,folder/record['views_360'][ix]['image']))
        for j,(label,path) in enumerate(paths):
            x=12+j*238;im=Image.open(path).convert('RGB');im.thumbnail((232,174))
            panel.paste(im,(x,y+44));draw.text((x,y+23),label,font=font(15),fill='#24364c')
        draw.text((12,y+220),'Each tile is a separate perspective view. Original PNGs are unchanged.',font=font(14),fill='#626262')
    target=out/'visual'/f"{case['number']:03d}_{case['episode_id']}_{tag}.jpg"
    target.parent.mkdir(exist_ok=True)
    panel.save(target,quality=91)
    return dict(episode_id=case['episode_id'],steps=steps,file=str(target),kind=tag,
                views_per_step=['native_front',90,45,0,-45,-90,180])


def prepare(source, out):
    if (out/'cases.json').exists():
        raise FileExistsError('Preserve existing evidence; select a new output')
    out.mkdir(parents=True,exist_ok=True)
    status=read(source/'status.json');proof=read(source/'capture_validation.json')
    assert proof['passed'] and proof['episodes']==104
    run=Path(status['validation']).parent
    native=read(run/'validation.json');assert native['passed'] and native['episodes']==104
    manifest=read(source/'manifest.json');cohort={c['episode_id']:c for c in read(source/'cohort.json')['cases']}
    meta=read(run/'run.json');dataset=Path(meta['dataset'])/'val_unseen/val_unseen.json.gz'
    with gzip.open(dataset,'rt') as f:official={e['episode_id']:e for e in json.load(f)['episodes']}
    scores=[json.loads(x) for x in (run/'episodes.jsonl').read_text().splitlines()]
    failures=sorted([s for s in scores if s['SR']==0],key=lambda x:x['episode_id'])
    assert len(failures)==69 and len(scores)==104
    files=[source/'manifest.json',source/'cohort.json',source/'capture_validation.json',run/'validation.json',run/'episodes.jsonl',dataset]
    oldmeta=ROOT/'outputs/checkpoint_review/seed2_25_20261103/review_data.json'
    oldmaps=read(oldmeta)['scenes'];files.append(oldmeta)
    for scene in sorted({s['scene'] for s in scores}):
        dest=out/'geometry'/scene;dest.mkdir(parents=True)
        new=ROOT/'outputs/oracle_crossing/scene_annotations_v001/run_20261116_01/scenes'/scene
        if (new/'geometry.json').exists():
            geom=read(new/'geometry.json');floor=new/'floorplan.png';files.append(new/'geometry.json')
        else:
            geom=oldmaps[scene];floor=oldmeta.parent/'scenes'/scene/'floorplan.png'
        write(dest/'geometry.json',geom);shutil.copy2(floor,dest/'floorplan.png');files.append(floor)
    cases=[];audit=[]
    for number,score in enumerate(failures,1):
        eid=score['episode_id'];e=official[eid]
        completed=list((source/'capture/episodes'/eid).glob('attempt_*/complete.json'));assert len(completed)==1
        directory=completed[0].parent;finish=read(completed[0]);steps=directory/'steps.jsonl'
        records=[json.loads(x) for x in steps.read_text().splitlines()]
        assert len(records)==finish['actions']+1 and records[-1]['terminal']
        assert [r['step'] for r in records]==list(range(len(records)))
        assert score['run_seed']==finish['seed']==2 and finish['metrics']['success']==0
        poses=np.asarray([r['robot_pose']['position_world_m'] for r in records]);ref=np.asarray(e['reference_path'])
        distance,arc,length=project(poses,ref);gd=np.linalg.norm(poses[:,:2]-ref[-1,:2],axis=1)
        assert abs(gd[-1]-score['NE'])<1e-5
        assert len(score['pred_path'])==len(records)+1
        assert np.allclose(poses,np.asarray(score['pred_path'])[1:],atol=1e-5,rtol=0)
        assert all(r['frozen_state_verified'] and r['auxiliary_visibility']['restored'] for r in records)
        over=np.flatnonzero(distance>=.75);low=np.flatnonzero(poses[:,2]<.65)
        actions=[(r['action'] or {}).get('move_by_discrete', [0])[0] for r in records[:-1]]
        features=dict(actions=finish['actions'],observations=len(records),action_counts=dict(Counter(actions)),
            reference_length_m=length,max_route_distance_m=float(distance.max()),end_route_distance_m=float(distance[-1]),
            min_goal_distance_m=float(gd.min()),closest_goal_index=int(gd.argmin()),first_over_075_index=int(over[0]) if len(over) else None,
            nearest_arc_end_m=float(arc[-1]),nearest_arc_max_m=float(arc.max()),
            first_low_height_index=int(low[0]) if len(low) else None,end_height_m=float(poses[-1,2]))
        case=dict(number=number,episode_id=eid,scene=score['scene'],source_batch=cohort[eid]['source_batch'],
            instruction=e['instruction']['instruction_text'],score={k:v for k,v in score.items() if k!='pred_path'},features=features,
            pred_path=poses.tolist(),reference_path=ref.tolist(),route_distances_m=distance.tolist(),goal_distances_m=gd.tolist(),
            nearest_reference_arc_m=arc.tolist(),headings_deg=[r['robot_pose']['heading_deg'] for r in records],actions=actions,
            steps_source=str(steps),capture_directory=str(directory),native_source=str(run/'episodes.jsonl'),
            candidate_events=candidates(poses[:,:2],distance,arc),map=f'maps/{number:03d}_{eid}.png')
        cases.append(case);files.extend([steps,completed[0]])
        audit.append(dict(episode_id=eid,actions=finish['actions'],observations=len(records),native_positions_equal=True))
    (out/'maps').mkdir(exist_ok=True);(out/'sheets').mkdir(exist_ok=True)
    for c in cases:
        draw_card(c,out/c['map'],out/'geometry')
        # Add temporal step indices and heading ticks to the same geometry mapping.
        image=Image.open(out/c['map']).convert('RGB');draw=ImageDraw.Draw(image)
        pts=np.r_[np.asarray(c['pred_path'])[:,:2],np.asarray(c['reference_path'])[:,:2]]
        lo=pts.min(axis=0)-1.1;hi=pts.max(axis=0)+1.1;size=max(np.maximum(hi-lo,1));mid=(lo+hi)/2;lo=mid-size/2;hi=mid+size/2
        for i in range(0,len(c['pred_path']),max(5,len(c['pred_path'])//12)):
            p=c['pred_path'][i];x=35+(p[0]-lo[0])/size*660;y=85+(hi[1]-p[1])/size*660
            draw.text((x+3,y),str(i),font=font(13),fill='#17204e',stroke_width=1,stroke_fill='white')
        image.save(out/c['map'])
        print(f"{c['number']:02} {c['episode_id']} {c['score']['fail_reason']} N={c['features']['actions']} Dmax={c['features']['max_route_distance_m']:.2f} end={c['features']['end_route_distance_m']:.2f}",flush=True)
    for start in range(0,len(cases),6):
        sheet=Image.new('RGB',(2280,1700),'#eeeeee')
        for j,c in enumerate(cases[start:start+6]):sheet.paste(Image.open(out/c['map']),(j%3*760,j//3*850))
        sheet.save(out/'sheets'/f'{start+1:03d}_{min(start+6,len(cases)):03d}.jpg',quality=92)
    write(out/'cases.json',cases);write(out/'source_audit.json',dict(created_at=datetime.now(timezone.utc).isoformat(),
        failures=69,native_termination=dict(Counter(c['score']['fail_reason'] for c in cases)),
        source_capture_validation=proof,files_sha256={str(p):sha(p) for p in files},checks=audit,
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        historical_labels_used_for_classification=False,new_navigation=False,new_model_calls=0))
    code=out/'code';code.mkdir(exist_ok=True)
    for p in [Path(__file__),ROOT/'scripts/analyze_oracle_baseline_failures.py']:
        shutil.copy2(p,code/p.name)
    (out/'git_status.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True))
    (out/'git_diff.patch').write_bytes(subprocess.check_output(['git','diff'],cwd=ROOT))
    evidence=[]
    for c in cases:
        evidence.append(evidence_card(c,out))
        print('VISUAL',c['number'],flush=True)
    write(out/'visual_evidence.json',evidence)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'outputs/multiview_capture/v001/run_20261117_03')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--case',type=int);p.add_argument('--steps',type=int,nargs='+');p.add_argument('--tag',default='detail')
    a=p.parse_args()
    if a.case:
        c=next(c for c in read(a.output/'cases.json') if c['number']==a.case)
        print(json.dumps(evidence_card(c,a.output,a.steps,a.tag)))
    else:prepare(a.source.resolve(),a.output.resolve())
