"""Freeze all retained JEV+dedup nodes and their estimated-heading capture plan."""
import argparse
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.jev_capture import estimate_headings,estimate_visual_motion,camera_position,VIEW_OFFSETS,VIEW_SETS


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')


def prepare(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    dedup=json.loads(args.dedup.read_text())
    dataset=args.dataset.resolve()
    meta={r['episode_id']:r for r in map(json.loads,(dataset/'evaluation/episodes.jsonl').read_text().splitlines())}
    inputs={r['episode_id']:r for r in map(json.loads,(dataset/'inputs/episodes.jsonl').read_text().splitlines())}
    with gzip.open(args.episodes,'rt') as f:episodes={e['episode_id']:e for e in json.load(f)['episodes']}
    camera=json.loads(args.calibration.read_text())['camera']
    camera.update(origin_policy='Recorded root XYZ + H1 camera offset rotated by estimated base yaw; fixed optical center for all views.',
                  height_policy='Recorded root Z + static H1 camera offset Z; body roll/pitch and joint pose unavailable.')
    points={};refs=[];sources={str(args.dedup.resolve()):sha(args.dedup),str(args.episodes.resolve()):sha(args.episodes),str(args.calibration.resolve()):sha(args.calibration)}
    cache={};(out/'heading_estimates').mkdir()
    for c in dedup['cases']:
        eid=c['real_episode_id'];ep=episodes[eid]
        if ep['scan']!=meta[eid]['scene']:raise ValueError('Scene mismatch')
        if eid not in cache:
            path=dataset/meta[eid]['trajectory'];doc=json.loads(path.read_text())
            obs_path=dataset/inputs[eid]['observations'];obs=json.loads(obs_path.read_text())
            if len(doc['frames'])!=c['frames'] or len(obs)!=c['frames']:raise ValueError('Frame count mismatch')
            sources[str(path)]=sha(path);sources[str(obs_path)]=sha(obs_path)
            if args.heading_cache:
                old=args.heading_cache/'heading_estimates'/(eid+'.json');cached=json.loads(old.read_text())
                old_manifest=json.loads((args.heading_cache/'manifest.json').read_text())
                if old_manifest['source_sha256'][str(path)]!=sha(path) or old_manifest['source_sha256'][str(obs_path)]!=sha(obs_path):raise ValueError('Heading cache source mismatch')
                visual=cached['visual_motion'];headings=cached['headings'];sources[str(old.resolve())]=sha(old)
            else:
                visual=estimate_visual_motion([dataset/o['rgb'] for o in obs])
                headings=estimate_headings(doc['frames'],ep['start_rotation'],visual)
            write(out/'heading_estimates'/(eid+'.json'),dict(episode_id=eid,visual_motion=visual,headings=headings))
            cache[eid]=(doc['frames'],headings,obs)
            print('HEADINGS_READY '+eid,flush=True)
        frames,headings,obs=cache[eid]
        active=set(c['final_active_ids']);nodes={n['id']:n for n in c['nodes']}
        if not active<=set(nodes):raise ValueError('Missing retained node')
        for nid in c['final_active_ids']:
            n=nodes[nid];i=n['index'];point_id=eid+'__F'+str(i).zfill(4)
            image=next(x for x in n['images'] if x['frame']==i)
            if image['image_id']!=obs[i]['rgb_sha256']:raise ValueError('Node/trajectory RGB identity mismatch')
            ref=dict(case_number=c['case_number'],episode_id=eid,node_id=nid,candidate_id=n['candidate_id'],frame=i,emitted_at=n['emittedAt'],point_id=point_id)
            refs.append(ref)
            if point_id not in points:
                points[point_id]=dict(point_id=point_id,episode_id=eid,scene=ep['scan'],frame=i,
                    root_position=frames[i]['position'],heading=headings[i],
                    position=camera_position(frames[i]['position'],headings[i]['base_yaw_deg'],camera['local_translation']),
                    source_rgb=str(dataset/obs[i]['rgb']),source_rgb_sha256=obs[i]['rgb_sha256'],
                    instruction=inputs[eid]['instruction'],instruction_zh=inputs[eid]['instruction_zh'],references=[])
            points[point_id]['references'].append(ref)
    assert len(refs)==165 and len(points)==159 and len(cache)==33 and len(dedup['cases'])==34
    scenes=[]
    for scene in sorted({p['scene'] for p in points.values()}):
        path=args.resource/'scenes'/scene/'start_result_navigation.usd'
        if not path.exists():raise FileNotFoundError(path)
        scenes.append(dict(scene=scene,path=str(path),sha256=sha(path)))
    manifest=dict(schema=1,protocol='jev_dedup_point_capture_v001',prepared_at=datetime.now(timezone.utc).isoformat(),
        source_dedup=str(args.dedup.resolve()),source_sha256=sources,cases=34,episodes=33,retained_node_references=len(refs),
        unique_points=len(points),points=list(points.values()),references=refs,scenes=scenes,camera=camera,
        render_seed=20261115,view_offsets_deg=VIEW_OFFSETS,view_sets=VIEW_SETS,
        output_semantics='Separate 180-degree three-view and 360-degree eight-view image sets; overlapping views share freshly rendered bytes. No stitched panorama.',
        heading_semantics='Motion estimate is a prior; refine against fresh 360 renders using source node RGB when unambiguous. All headings estimated, not measured; no goal/reference route used.',model_calls=0,navigation_actions=0,
        static_capture=True,original_physical_state_recovered=False,expected_unique_rgb=len(points)*8,
        gpu=3,project_root=str(ROOT),after=str(args.after.resolve()),keep_model=True,keep_final_simulator=True,
        expected_probe_rgb=len(points)*8,absolute_visual_alignment=True)
    files=['core/__init__.py','core/jev_capture.py','scripts/prepare_jev_point_capture.py','scripts/render_jev_point_capture.py',
           'scripts/run_jev_point_capture.py','scripts/run_crossing_panorama_isaac.sh',
           'scripts/run_oracle_retained_followup.py','scripts/run_oracle_existing_model.py','scripts/run_oracle_distance.py',
           'scripts/evaluate.py','core/paths.py','core/seeding.py','core/vlnverse_reproduction.py']
    hashes={}
    for rel in files:
        dst=out/'source'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dst);hashes[rel]=sha(dst)
    manifest['source_hashes']=hashes
    manifest['git_head']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    (out/'source/workspace_status.txt').write_bytes(subprocess.check_output(['git','status','--short']))
    (out/'source/tracked.diff').write_bytes(subprocess.check_output(['git','diff','HEAD']))
    for sub in ['logs','points','scenes']:(out/sub).mkdir()
    write(out/'manifest.json',manifest);write(out/'seal.json',dict(manifest_sha256=sha(out/'manifest.json')))
    write(out/'status.json',dict(phase='queued_after_early_plus05',completed_points=0,expected_points=len(points),simulation_started=False))
    print(json.dumps(dict(references=len(refs),points=len(points),scenes=len(scenes),unique_rgb=len(points)*8)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['output','dedup','dataset','episodes','calibration','resource','after']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--heading-cache',type=Path)
    prepare(p.parse_args())
