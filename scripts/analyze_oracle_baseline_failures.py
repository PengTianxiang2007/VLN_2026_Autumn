"""Offline evidence for baseline failures. Classification is separately reviewed.

Reads completed native scores, reference routes, policy trace and static floor maps.
Never starts a model/simulator. Geometry features do not assign semantic causes.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.seeding import episode_seed


def read(p):
    return json.loads(Path(p).read_text())


def write(p, data):
    Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def project(points, reference):
    """Exact XY distance to segments, with nearest reference arclength."""
    ref = np.asarray(reference, dtype=float)[:, :2]
    ref = ref[np.r_[True, np.linalg.norm(np.diff(ref, axis=0), axis=1) > 1e-8]]
    pts = np.asarray(points, dtype=float)[:, :2]
    if len(ref) == 1:
        return np.linalg.norm(pts-ref[0], axis=1), np.zeros(len(pts)), 0.
    delta = np.diff(ref, axis=0); lengths = np.linalg.norm(delta, axis=1)
    t = np.clip(np.einsum('nsi,si->ns', pts[:, None, :]-ref[:-1], delta) / lengths**2, 0, 1)
    foot = ref[:-1] + t[:, :, None] * delta
    ds = np.linalg.norm(pts[:, None, :] - foot, axis=2)
    ix = ds.argmin(axis=1); rows = np.arange(len(pts))
    arc = np.r_[0, np.cumsum(lengths)]
    return ds[rows, ix], arc[ix] + t[rows, ix]*lengths[ix], float(arc[-1])


def spans(mask, xy):
    result = []; start = None
    for i, flag in enumerate(list(mask) + [False]):
        if flag and start is None:
            start = i
        if not flag and start is not None:
            end = i-1
            result.append(dict(start=start, end=end, observations=end-start+1,
                walked_m=float(np.linalg.norm(np.diff(xy[start:end+1], axis=0), axis=1).sum())))
            start = None
    return result


def draw_card(case, output, geometry_root):
    """Diagnostic plot, not a simulation reconstruction or new HTML template."""
    scene = geometry_root / case['scene']; g = read(scene/'geometry.json')
    floor = Image.open(scene/'floorplan.png').convert('RGB')
    pred = np.asarray(case['pred_path']); ref = np.asarray(case['reference_path'])
    points = np.concatenate((pred[:, :2], ref[:, :2]))
    low = points.min(axis=0)-1.1; high = points.max(axis=0)+1.1
    span = np.maximum(high-low, 1); size = max(span)
    mid = (low+high)/2; low = mid-size/2; high=mid+size/2
    x0=(low[0]-g['low'][0])/g['resolution'];x1=(high[0]-g['low'][0])/g['resolution']
    y0=(g['high'][1]-high[1])/g['resolution'];y1=(g['high'][1]-low[1])/g['resolution']
    card=Image.new('RGB',(760,850),'white');draw=ImageDraw.Draw(card)
    font=ImageFont.truetype(read(ROOT/'core/crossing_visualization_template.json')['font'],17)
    small=ImageFont.truetype(read(ROOT/'core/crossing_visualization_template.json')['font'],14)
    draw.text((14,8),f"{case['number']:03d}  {case['episode_id']}",font=font,fill='#172b40')
    f=case['features'];score=case['score']
    draw.text((14,34),f"{score['fail_reason']}  NE={score['NE']:.2f}m  OS={int(score['OS'])}  actions={f['actions']}  zEnd={pred[-1,2]:.2f}",font=small,fill='#172b40')
    draw.text((14,56),f"route max/end={f['max_route_distance_m']:.2f}/{f['end_route_distance_m']:.2f}m  minGoal={f['min_goal_distance_m']:.2f}m  ref={f['reference_length_m']:.1f}m",font=small,fill='#172b40')
    origin=(35,85); side=660
    crop=floor.transform((side,side),Image.Transform.EXTENT,(x0,y0,x1,y1),Image.Resampling.BILINEAR,fillcolor='#e8e8e8')
    card.paste(crop,origin);draw=ImageDraw.Draw(card)
    def xy(p):return (origin[0]+(p[0]-low[0])/size*side, origin[1]+(high[1]-p[1])/size*side)
    draw.line([xy(p) for p in ref],fill='#008c38',width=5)
    for i,(a,b) in enumerate(zip(pred,pred[1:])):
        t=i/max(1,len(pred)-2);color=(int(35+200*t),int(110-55*t),int(220-160*t))
        draw.line((xy(a),xy(b)),fill=color,width=3)
    marks={'S':0,'E':len(pred)-1,'D':f['first_over_075_index'],'M':f['closest_goal_index']}
    for label,i in marks.items():
        if i is None:continue
        q=xy(pred[i]);draw.ellipse((q[0]-4,q[1]-4,q[0]+4,q[1]+4),fill='#bd3b20')
        draw.text((q[0]+5,q[1]-15),label+str(i),font=small,fill='#8a1c1c',stroke_width=2,stroke_fill='white')
    goal=xy(ref[-1]);draw.ellipse((goal[0]-6,goal[1]-6,goal[0]+6,goal[1]+6),fill='#008c38')
    draw.text((goal[0]+7,goal[1]+4),'G',font=font,fill='#007b23',stroke_width=2,stroke_fill='white')
    draw.line((45,730,45+side/size,730),fill='#111111',width=3);draw.text((45,708),'1 m',font=small,fill='#111111',stroke_width=2,stroke_fill='white')
    # Temporal distance curves, sampled at recorded positions (not physics ticks).
    ys=case['route_distances_m'];gs=case['goal_distances_m'];ymax=max(max(ys),max(gs),3.1)
    top,bottom,left,right=760,815,35,695
    for values,color in [(gs,'#888888'),(ys,'#2357d5')]:
        draw.line([(left+i/max(1,len(values)-1)*(right-left),bottom-v/ymax*(bottom-top)) for i,v in enumerate(values)],fill=color,width=2)
    y=bottom-.75/ymax*(bottom-top);draw.line((left,y,right,y),fill='#d89133',width=1)
    draw.text((14,825),'Green=reference; blue>red=recorded path. D=first 0.75m; M=closest goal; G=goal.',font=small,fill='#26364a')
    card.save(output)


def prepare(campaign, output):
    output.mkdir(parents=True,exist_ok=True)
    status=read(campaign/'baseline/status.json');run=Path(status['validation']).parent
    proof=read(status['validation']);assert proof['passed'] and proof['episodes']==200
    meta=read(run/'run.json');dataset=Path(meta['dataset'])/'val_unseen/val_unseen.json.gz'
    with gzip.open(dataset,'rt') as f:official={e['episode_id']:e for e in json.load(f)['episodes']}
    scores=[json.loads(l) for l in (run/'episodes.jsonl').read_text().splitlines()]
    tracefile=run/'chunk_model_evidence/agent_trace.jsonl';traces=defaultdict(list)
    for line in tracefile.read_text().splitlines():
        t=json.loads(line);traces[t['episode_id']].append(t)
    failures=[r for r in scores if r['SR']==0];assert len(failures)==102
    geometry_root=ROOT/'outputs/oracle_crossing/scene_annotations_v001/run_20261116_01/scenes'
    image_root=Path(meta['borrowed_model']['command'].split('--output ',1)[1].split(' --',1)[0])
    cases=[];source_files=[run/'episodes.jsonl',Path(status['validation']),run/'run.json',dataset,tracefile]
    for number,score in enumerate(failures,1):
        eid=score['episode_id'];e=official[eid];trace=traces[eid]
        assert score['episode_seed']==episode_seed(2,eid)
        if trace:
            assert len({t['episode_reset'] for t in trace})==1
            assert [t['step'] for t in trace]==list(range(len(trace)))
            assert all(t['episode_seed']==score['episode_seed'] and not t['forced_smoke_stop'] for t in trace)
        pred=np.array(score['pred_path']);ref=np.array(e['reference_path'])
        d,arc,length=project(pred,ref);gd=np.linalg.norm(pred[:,:2]-ref[-1,:2],axis=1)
        over=np.flatnonzero(d>=.75);goal=np.flatnonzero(gd<3)
        feet=np.flatnonzero(pred[:,2]<.65)
        features=dict(actions=len(trace),action_counts=dict(Counter(str(t['action']) for t in trace)),last_action=trace[-1]['action'] if trace else None,
            recorded_positions=len(pred),reference_length_m=length,max_route_distance_m=float(d.max()),end_route_distance_m=float(d[-1]),
            min_goal_distance_m=float(gd.min()),closest_goal_index=int(gd.argmin()),first_goal_radius_index=int(goal[0]) if len(goal) else None,
            first_over_075_index=int(over[0]) if len(over) else None,nearest_arc_end_m=float(arc[-1]),nearest_arc_max_m=float(arc.max()),
            first_low_height_index=int(feet[0]) if len(feet) else None,
            offroute_spans_075=spans(d>=.75,pred[:,:2]),offroute_spans_150=spans(d>=1.5,pred[:,:2]),
            end_height_m=float(pred[-1,2]),max_adjacent_xy_move_m=float(np.linalg.norm(np.diff(pred[:,:2],axis=0),axis=1).max()))
        images=[]
        if trace:
            images=sorted((image_root/f"episode_reset_{trace[0]['episode_reset']:04d}").glob('rgb_*.png'))
        case=dict(number=number,episode_id=eid,scene=score['scene'],instruction=e['instruction']['instruction_text'],
                  score={k:v for k,v in score.items() if k!='pred_path'},features=features,
                  pred_path=pred.tolist(),reference_path=ref.tolist(),route_distances_m=d.tolist(),goal_distances_m=gd.tolist(),nearest_reference_arc_m=arc.tolist(),
                  actions=[t['action'] for t in trace],episode_reset=trace[0]['episode_reset'] if trace else None,
                  initial_rgb=[str(x) for x in images],trace_source=str(tracefile),map=f'maps/{number:03d}_{eid}.png')
        cases.append(case)
    (output/'maps').mkdir(exist_ok=True);(output/'sheets').mkdir(exist_ok=True)
    for c in cases:draw_card(c,output/c['map'],geometry_root)
    for start in range(0,len(cases),6):
        sheet=Image.new('RGB',(1520,2550),'#eeeeee')
        for i,c in enumerate(cases[start:start+6]):sheet.paste(Image.open(output/c['map']),(i%2*760,i//2*850))
        sheet.save(output/'sheets'/f'{start+1:03d}_{min(start+6,len(cases)):03d}.jpg',quality=91)
    for scene in sorted({c['scene'] for c in cases}):source_files.extend([geometry_root/scene/'geometry.json',geometry_root/scene/'floorplan.png'])
    write(output/'cases.json',cases)
    write(output/'source_audit.json',dict(created_at=datetime.now(timezone.utc).isoformat(),episodes=200,failures=len(cases),
        native_termination=dict(Counter(c['score']['fail_reason'] for c in cases)),policy_trace_cases=sum(bool(c['actions']) for c in cases),
        first_two_rgb_cases=sum(len(c['initial_rgb'])==2 for c in cases),full_rgb_available=False,
        files_sha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in source_files}))
    for c in cases:
        f=c['features'];s=c['score']
        print(f"{c['number']:03d} {c['episode_id']:25s} {s['fail_reason']:15s} OS{int(s['OS'])} N{f['actions']:3d} NE{s['NE']:5.2f} Dmax{f['max_route_distance_m']:5.2f} Dend{f['end_route_distance_m']:5.2f} Gmin{f['min_goal_distance_m']:5.2f} prog{f['nearest_arc_max_m']/max(f['reference_length_m'],1e-6):.2f} z{f['end_height_m']:.2f}")


LABELS = {
    'route_choice':'选错方向、分支或错过转弯',
    'route_backtrack':'掉头沿来路反向回返',
    'stop_incomplete':'沿正确路线未走完即停止／局部徘徊',
    'fall_onroute':'正确路线附近跌倒，无明确选路偏航',
    'warmup_fall':'预热阶段跌倒，尚无策略动作',
    'stuck_onroute':'正确路线附近卡住',
    'goal_overshoot':'目标区域附近未停，继续走过头',
    'uncertain':'证据不足，局部偏移原因不确定',
}


def finalize(campaign, output, review_file):
    review=read(review_file);cases=read(output/'cases.json');audit=read(output/'source_audit.json')
    assert review['classification_frozen_before_paired_outcome_join']
    assert hashlib.sha256((output/'cases.json').read_bytes()).hexdigest()==review['source_cases_sha256']
    assert hashlib.sha256(review_file.with_name('review_notes.tsv').read_bytes()).hexdigest()==review['notes_sha256']
    for name,digest in audit['files_sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest, name
    by_id={c['episode_id']:c for c in cases};annotations={r['episode_id']:r for r in review['cases']}
    assert len(annotations)==len(by_id)==102 and set(annotations)==set(by_id)
    auto_status=read(campaign/'auto_branch/status.json');auto_path=Path(auto_status['validation']).parent/'episodes.jsonl'
    auto={r['episode_id']:r for r in map(json.loads,auto_path.read_text().splitlines())}
    assert len(auto)==200
    rows=[]
    for c in cases:
        eid=c['episode_id'];r=annotations[eid];f=c['features'];s=c['score'];cat=r['category']
        assert cat in LABELS and r['confidence'] in ('high','moderate','uncertain')
        assert int(r['number'])==c['number'] and s['SR']==0
        assert auto[eid]['episode_seed']==s['episode_seed']==episode_seed(2,eid)
        assert auto[eid]['run_seed']==s['run_seed']==2 and auto[eid]['scene']==c['scene']
        assert len(c['pred_path'])==len(c['actions'])+2
        assert abs(c['goal_distances_m'][-1]-s['NE'])<1e-6
        assert int(min(c['goal_distances_m'][1:])<3)==int(s['OS'])
        rows.append(dict(number=c['number'],episode_id=eid,scene=c['scene'],category=cat,category_zh=LABELS[cat],
            deviation_failure=cat in ('route_choice','route_backtrack'),confidence=r['confidence'],reason_zh=r['reason_zh'],
            termination=s['fail_reason'],baseline_SR=s['SR'],auto_branch_SR=auto[eid]['SR'],baseline_NE_m=s['NE'],baseline_OS=s['OS'],
            actions=f['actions'],physics_ticks=s['steps'],max_route_distance_m=f['max_route_distance_m'],
            end_route_distance_m=f['end_route_distance_m'],min_scored_goal_distance_m=min(c['goal_distances_m'][1:]),
            first_over_075_position_index=f['first_over_075_index'],episode_seed=s['episode_seed'],
            instruction_en=c['instruction'],evidence_map=str(output/c['map']),evidence_trace=c['trace_source'],
            model_episode_reset=c['episode_reset'],full_navigation_rgb=False))
    with (output/'classification.csv').open('x',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    write(output/'classification.json',rows)
    classes=[]
    for cat,label in LABELS.items():
        selected=[r for r in rows if r['category']==cat]
        classes.append(dict(category=cat,label_zh=label,count=len(selected),percent_failures=100*len(selected)/102,
            percent_all_tasks=100*len(selected)/200,auto_successes=sum(int(r['auto_branch_SR']) for r in selected),
            baseline_termination=dict(Counter(r['termination'] for r in selected))))
    deviated=[r for r in rows if r['deviation_failure']]
    scene_summary=[]
    for scene in sorted({r['scene'] for r in rows}):
        rr=[r for r in rows if r['scene']==scene]
        scene_summary.append(dict(scene=scene,baseline_failures=len(rr),deviation_failures=sum(r['deviation_failure'] for r in rr),
            route_choice=sum(r['category']=='route_choice' for r in rr),backtrack=sum(r['category']=='route_backtrack' for r in rr),
            uncertain=sum(r['category']=='uncertain' for r in rr)))
    summary=dict(status='complete',completed_at=datetime.now(timezone.utc).isoformat(),total_baseline=200,baseline_successes=98,
        baseline_failures=102,reviewed=102,scenes=len(scene_summary),categories=classes,
        deviation_failures=len(deviated),deviation_percent_failures=100*len(deviated)/102,deviation_percent_all=100*len(deviated)/200,
        deviation_confidence=dict(Counter(r['confidence'] for r in deviated)),
        deviation_termination=dict(Counter(r['termination'] for r in deviated)),
        deviation_auto_successes=sum(int(r['auto_branch_SR']) for r in deviated),
        deviation_auto_failures=sum(not r['auto_branch_SR'] for r in deviated),
        paired_baseline_failures_saved=sum(int(r['auto_branch_SR']) for r in rows),
        naive_075_distance_count=sum(r['max_route_distance_m']>=.75 for r in rows),
        scene_summary=scene_summary,full_navigation_rgb_available=False,
        interpretation='Retrospective trajectory/instruction/floorplan attribution, not full visual review or counterfactual causal proof. Route choice includes wrong movement direction in open space, not only topological junctions. Missing RGB limits semantic certainty; unknown cases are not counted as confirmed deviation.',
        classification_frozen_before_paired_outcome_join=True,new_navigation=False,new_model_calls=0)
    assert sum(x['count'] for x in classes)==102 and summary['paired_baseline_failures_saved']==69
    write(output/'summary.json',summary)
    write(output/'validation.json',dict(passed=True,reviewed=102,unique_ids=102,all_native_failures_covered=True,
        native_NE_OS_recomputed=True,all_action_position_lengths_verified=True,scenes_and_episode_seeds_verified=True,
        input_sha256_unchanged=True,review_sha256=hashlib.sha256(review_file.read_bytes()).hexdigest(),
        classification_sha256=hashlib.sha256((output/'classification.csv').read_bytes()).hexdigest(),
        auto_result_sha256=hashlib.sha256(auto_path.read_bytes()).hexdigest()))
    with zipfile.ZipFile(output/'review_evidence_102.zip','x',zipfile.ZIP_DEFLATED) as z:
        for p in [output/'classification.csv',output/'classification.json',output/'summary.json',output/'source_audit.json',
                  output/'review.json',output/'validation.json',*sorted((output/'maps').glob('*.png')),*sorted((output/'sheets').glob('*.jpg'))]:
            z.write(p,p.relative_to(output))
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--finalize',action='store_true');p.add_argument('--review',type=Path)
    p.add_argument('--campaign',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.finalize:
        if not args.review:p.error('--finalize requires --review')
        finalize(args.campaign.resolve(),args.output.resolve(),args.review.resolve())
    else:
        prepare(args.campaign.resolve(),args.output.resolve())
