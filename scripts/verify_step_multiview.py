"""Validate measured poses and all image sets against native scored task IDs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.step_multiview import OFFSETS, FRONT, angle_delta, assert_unchanged, write


def verify_attempt(directory, hashes=True):
    from PIL import Image
    records=[json.loads(s) for s in (directory/'steps.jsonl').read_text().splitlines()]
    for i,r in enumerate(records):
        if r['step']!=i or not r['frozen_state_verified'] or r['physics_ticks_during_capture']!=0:
            raise ValueError('Step continuity/frozen-state failure')
        assert_unchanged(r['physical_state_before'],r['physical_state_after'])
        if not r.get('auxiliary_visibility',{}).get('restored'):
            raise ValueError('Native robot appearance restoration not verified')
        folder=Path(r['frame_directory'])
        if len(r['views_360'])!=8 or [v['view_id'] for v in r['views_180']]!=list(FRONT):
            raise ValueError('Incomplete multiview set')
        if not (folder/r['front_image']).is_file():raise ValueError('Missing native front RGB')
        heading=r['robot_pose']['heading_deg']
        for offset,v in zip(OFFSETS,r['views_360']):
            if abs(angle_delta(v['camera_pose']['heading_deg'],heading+offset))>.01:
                raise ValueError('Relative heading mismatch')
            path=folder/v['image']
            if hashes and hashlib.sha256(path.read_bytes()).hexdigest()!=v['sha256']:
                raise ValueError('RGB hash mismatch')
            with Image.open(path) as im:
                if im.size!=(640,480):raise ValueError('RGB dimensions mismatch')
                im.verify()
        for v in r['views_180']:
            if hashlib.sha256((folder/v['image']).read_bytes()).hexdigest()!=r['views_360'][v['view_id']]['sha256']:
                raise ValueError('180/360 observation mismatch')
    complete=directory/'complete.json'
    if complete.exists():
        c=json.loads(complete.read_text())
        if c['observations']!=len(records) or c['actions']!=len(records)-1 or not records[-1]['terminal']:
            raise ValueError('Terminal/action count mismatch')
    return dict(steps=len(records),images=len(records)*8,complete=complete.exists())


def verify_campaign(campaign, run):
    manifest=json.loads((campaign/'manifest.json').read_text())
    scored={r['episode_id']:r for r in map(json.loads,(run/'episodes.jsonl').read_text().splitlines())}
    if set(scored)!=set(manifest['episode_ids']):raise ValueError('Native scored IDs differ from capture cohort')
    results={}; images=0;steps=0
    for eid in manifest['episode_ids']:
        complete=list((campaign/'capture/episodes'/eid).glob('attempt_*/complete.json'))
        if len(complete)!=1:raise ValueError('Expected one completed capture for '+eid)
        result=verify_attempt(complete[0].parent)
        captured=json.loads(complete[0].read_text())
        if abs(captured['metrics']['success']-scored[eid]['SR'])>1e-8:
            raise ValueError('Capture/native score mismatch: '+eid)
        if scored[eid]['run_seed']!=manifest['seed']:raise ValueError('Capture/native seed mismatch')
        results[eid]=result;images+=result['images'];steps+=result['steps']
    native=json.loads((run/'validation.json').read_text())
    if not native['passed'] or native['episodes']!=len(results):raise ValueError('Native validation incomplete')
    report=dict(passed=True,episodes=len(results),observations=steps,unique_multiview_images=images,
                terminal_observations=len(results),results=results,native_validation=str(run/'validation.json'))
    write(campaign/'capture_validation.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--campaign',type=Path,required=True);p.add_argument('--run',type=Path,required=True)
    a=p.parse_args();r=verify_campaign(a.campaign,a.run)
    print(json.dumps({k:v for k,v in r.items() if k!='results'}))
