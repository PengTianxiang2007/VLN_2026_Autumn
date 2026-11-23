"""Verify a frozen same-400 comparison without executing navigation or loading a model."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.oracle_landing_geometry import SceneLandingGeometry
from scripts.run_oracle_distance import load_campaign, job_plan, job_environment, sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--campaign',type=Path,required=True)
    p.add_argument('--episode-ids-file',type=Path,required=True)
    p.add_argument('--official-split',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():raise FileExistsError('Preserving previous verification')
    root=args.campaign.resolve();m=load_campaign(root)
    assert m['protocol']=='auto_branch_oracle_v001'
    ids=json.loads(args.episode_ids_file.read_text())
    assert len(ids)==len(set(ids))==400
    assert m['episode_ids']==ids==json.loads((root/'episode_ids.json').read_text())
    with gzip.open(args.official_split,'rt') as f:
        official=json.load(f)['episodes']
    chosen=[e for e in official if e['episode_id'] in set(ids)]
    assert [e['episode_id'] for e in chosen]==ids
    assert sha(args.official_split)==m['official_split_sha256']
    for case,source in zip(m['cases'],chosen):
        assert case==dict(episode_id=source['episode_id'],scene=source['scan'],
                         instruction=source['instruction']['instruction_text'],seed=2,
                         reference_path=source['reference_path'])
    assert m['events']==0 and not m['annotation_required']
    assert m['seed']==2 and m['arms']['auto_branch']['threshold_m']==.75
    assert m['arms']['auto_branch']['landing_offset_m']==1.25
    jobs=job_plan(root,m,['baseline','auto_branch'],ids,2,3)
    assert len(jobs)==2 and all(j['episode_ids']==ids for j in jobs)
    env={'VLN_ORACLE_MANIFEST':'previous','VLN_DISTANCE_ARM':'previous','VLN_BRANCH_ROOT':'previous'}
    baseline=job_environment(root,m,jobs[0],env)
    oracle=job_environment(root,m,jobs[1],env)
    assert all(not k.startswith(('VLN_ORACLE_','VLN_DISTANCE_','VLN_BRANCH_')) for k in baseline)
    assert oracle['VLN_DISTANCE_ARM']=='auto_branch'
    native='benchmarks/vlnverse/runner/run_full.py'
    assert m['source_sha256'][native]==m['code_sha256'][native]==sha(ROOT/native)
    geometry=m['landing_geometry_audit']
    scenes=sorted({c['scene'] for c in m['cases']})
    assert scenes==sorted(geometry['scenes']) and len(scenes)==22
    assert geometry['mode']=='audit_only' and not geometry['static_crossing_annotations_used']
    assert len(geometry['files_sha256'])==44
    for scene in scenes:SceneLandingGeometry.from_manifest(geometry,scene)
    for name,expected in m['source_sha256'].items():
        assert sha(ROOT/name)==expected, 'Working source changed since freeze: '+name
    assert not (root/'runs').exists(), 'This checker is for an unstarted preparation'
    result=dict(passed=True,protocol=m['protocol'],tasks_per_arm=400,planned_navigation_episodes=800,
                scenes=22,scene_counts=dict(sorted(Counter(c['scene'] for c in m['cases']).items())),
                same_order_and_seed=True,official_task_fields_unchanged=True,
                baseline_has_no_oracle_environment=True,native_launcher_byte_identical=True,
                code_files_verified=len(m['code_sha256']),geometry_files_verified=44,
                geometry_mode='audit_only',fixed_task_landings=0,static_crossing_annotations_used=False,
                episode_ids_sha256=sha(args.episode_ids_file),manifest_sha256=sha(root/'manifest.json'),
                seal_sha256=sha(root/'seal.json'),simulation_started=False,
                note='GPU indices in the printed plan are placeholders, not a resource reservation or launch approval.')
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    main()
