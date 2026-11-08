"""Freeze the same ten tasks with multiple live Oracle corrections allowed."""
import hashlib
import argparse
import json
import math
from pathlib import Path
import shutil
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'outputs/oracle_crossing/seed2_10_20261103'
OUT=ROOT/'outputs/oracle_crossing/seed2_10_multi_20261103'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--refresh-unlaunched',action='store_true')
    args=ap.parse_args()
    if (OUT/'manifest.json').exists():
        previous=json.loads((OUT/'manifest.json').read_text())
        if not args.refresh_unlaunched or 'oracle' in previous or (OUT/'oracle_records').exists():
            raise RuntimeError('Multi-intervention cohort already frozen')
    m=json.loads((SOURCE/'manifest.json').read_text())
    assert json.loads((SOURCE/'status_control.json').read_text())['phase']=='complete'
    m.pop('oracle',None)
    m['protocol'].update(max_interventions=None,review_after_each_intervention_actions=4,
                         near_goal_caveat='Report each handover distance and separate tasks that receive any correction inside the official 3m goal radius.',
                         terminal_rule='Native STOP, fall, stuck and physics budget remain unchanged; no task reset after terminal.')
    m.update(schema=2,multi_intervention=True,created_at=time.time(),
             single_intervention_pilot=str(SOURCE),
             protocol_revision='User explicitly permits repeated pose corrections; no policy-memory reset; ordinary episode budget and stop conditions remain.',
             reused_control=dict(campaign=str(SOURCE),manifest_sha256=hashlib.sha256((SOURCE/'manifest.json').read_bytes()).hexdigest()))
    rejected=[]
    for c in m['cases']:
        scene=ROOT/'outputs/checkpoint_review/seed2_25_20261103/scenes'/c['scene']
        g=json.loads((scene/'geometry.json').read_text());z=np.load(scene/'map_masks.npz')
        crosses=json.loads((scene/'crossings_reviewed.json').read_text())['crossings']
        ref=np.array(c['reference_path'])[:,:2]
        keep=np.r_[True,np.linalg.norm(np.diff(ref,axis=0),axis=1)>1e-8];ref=ref[keep]
        arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(ref,axis=0),axis=1))]
        def at(s):return np.array([np.interp(s,arc,ref[:,k]) for k in range(2)])
        def safe(p):
            u=int(round((p[0]-g['low'][0])/g['resolution']));v=int(round((g['high'][1]-p[1])/g['resolution']))
            if not (0<=v<g['height'] and 0<=u<g['width']):return False,0
            clearance=float(z['distance'][v,u])
            return bool(z['safe'][v,u]) and clearance>=.20,clearance
        targets=[]
        for cr in crosses:
            k=int(np.argmin(np.linalg.norm(ref-np.array(cr['position']),axis=1)))
            distance=float(np.linalg.norm(ref[k]-cr['position']))
            if distance>1.6:continue
            s0=float(arc[k]);t=None
            for offset in [.75,.5,1.,.25,1.25]:
                s=min(s0+offset,float(arc[-1]));p=at(s)
                if arc[-1]-s<.5:continue
                ok,clearance=safe(p)
                if ok and math.dist(p,cr['position'])<=2.0:
                    delta=at(min(s+.25,arc[-1]))-at(max(s-.25,0))
                    t=dict(id=cr['id'],crossing_position=cr['position'],target_xy=p.tolist(),
                           target_yaw_rad=math.atan2(delta[1],delta[0]),target_crossing_distance_m=math.dist(p,cr['position']),
                           reference_arc_m=s,nearest_reference_arc_m=s0,crossing_reference_distance_m=distance,
                           planned_goal_distance_m=math.dist(p,ref[-1]),clearance_m=clearance,source='reviewed_geometry_crossing_and_reference_route')
                    break
            if cr['id']==c['crossing_id']:
                ok,clearance=safe(c['target_xy']);assert ok
                t=dict(id=cr['id'],crossing_position=cr['position'],target_xy=c['target_xy'],
                       target_yaw_rad=c['target_yaw_rad'],target_crossing_distance_m=c['target_crossing_distance_m'],
                       reference_arc_m=float(arc[int(np.argmin(np.linalg.norm(ref-c['target_xy'],axis=1)))]),
                       nearest_reference_arc_m=s0,crossing_reference_distance_m=distance,
                       planned_goal_distance_m=math.dist(c['target_xy'],ref[-1]),clearance_m=clearance,
                       source='unchanged_first_intervention_target_from_pilot')
            if t:targets.append(t)
            else:rejected.append(dict(episode_id=c['episode_id'],crossing_id=cr['id'],reason='No safe reference landing within two meters with at least 0.5m remaining route'))
        assert c['crossing_id'] in {t['id']for t in targets}
        c['targets']=sorted(targets,key=lambda t:t['reference_arc_m'])
    OUT.mkdir(parents=True,exist_ok=True)
    # Reuse immutable completed controls, with explicit provenance. No new control GPU work.
    for name in ['visualization_control','runs_control']:
        if (OUT/name).exists():assert (OUT/name).resolve()==(SOURCE/name).resolve()
        else:(OUT/name).symlink_to(SOURCE/name,target_is_directory=True)
    for name in ['model_fingerprints.json','status_control.json','environment_check.json']:
        shutil.copy2(SOURCE/name,OUT/name)
    (OUT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    (OUT/'target_exclusions.json').write_text(json.dumps(rejected,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({c['episode_id']:[dict(id=t['id'],arc=round(t['reference_arc_m'],2),clearance=round(t['clearance_m'],2),goal=round(t['planned_goal_distance_m'],2)) for t in c['targets']] for c in m['cases']},indent=2))


if __name__=='__main__':main()
