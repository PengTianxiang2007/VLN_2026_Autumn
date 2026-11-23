"""Freeze the exact older 48 + newer 56 task union for a native baseline recapture."""
import argparse
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.paths import isaac_root, model_python, resource_root, simulation_python
from core.seeding import episode_seed
from scripts.prepare_oracle_distance import source_files, sha, save, replace_once


def select_tasks(old, new, official):
    old_ids = [r['episode_id'] for r in old if r['status']=='crossing']
    new_ids = new['selected_ids']
    if (len(old_ids), len(new_ids)) != (48, 56) or len(set(old_ids+new_ids)) != 104:
        raise ValueError('Expected disjoint 48 and 56 task sets')
    ids = set(old_ids+new_ids)
    selected = [e for e in official if e['episode_id'] in ids]
    if len(selected) != 104 or {e['episode_id'] for e in selected} != ids:
        raise ValueError('Official task selection mismatch')
    return selected, old_ids, new_ids


def prepare(out):
    old = ROOT/'outputs/checkpoint_review/seed2_crossing_attribution_20261103/attribution_reviews.json'
    new = ROOT/'experiments/oracle_recovery/auto_branch_v001/run_20261117_04_pair200/exports/route_choice56_20261117_01/selection.json'
    official = resource_root()/'assets/VLNVerse/data/raw_data/final_splits/fine_val_unseen.json.gz'
    with gzip.open(official, 'rt') as f:
        selected, old_ids, new_ids = select_tasks(json.loads(old.read_text()), json.loads(new.read_text()), json.load(f)['episodes'])
    out.mkdir(parents=True, exist_ok=False)
    cases = [dict(episode_id=e['episode_id'], scene=e['scan'], seed=2,
                  episode_seed=episode_seed(2,e['episode_id']),
                  source_batch='older48' if e['episode_id'] in old_ids else 'newer56') for e in selected]
    cohort = dict(schema=1, episodes=104, events=0, seed=2, cases=cases,
                  source_sha256={str(p):sha(p) for p in (old,new,official)})
    names = sorted(set(source_files()) | {'core/step_multiview.py','scripts/prepare_step_multiview.py',
                    'scripts/verify_step_multiview.py','scripts/run_oracle_existing_model.py',
                    'scripts/run_step_multiview.py','tests/test_step_multiview.py'})
    originals = {n:sha(ROOT/n) for n in names}
    code = out/'code'
    for name in names:
        dest = code/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/name, dest)
        if sha(dest)!=originals[name]:
            raise RuntimeError('Source changed while freezing: '+name)
    evaluator = code/'benchmarks/vlnverse/upstream/vlnverse/evaluator/vln_pe_evaluator.py'
    evaluator.write_text(replace_once(evaluator.read_text(), '    def eval(self):\n',
        '    def eval(self):\n'
        '        from core.oracle_distance_native import install as install_retention\n'
        '        from core.step_multiview import install as install_capture\n'
        '        install_retention(self)\n'
        '        install_capture(self)\n'))
    head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dirty = subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)
    (out/'git_status.txt').write_text(dirty)
    (out/'git_diff.patch').write_bytes(subprocess.check_output(['git','diff','HEAD'],cwd=ROOT))
    env = dict(STREAMVLN_VENV=str(model_python('streamvln').parent.parent),
               VLNVERSE_VENV=str(simulation_python().parent.parent), PENG_ISAAC_ROOT=str(isaac_root()),
               VLN_RESOURCE_ROOT=str(resource_root()), VLN_OUTPUT_ROOT=str(out/'runs'),
               VLN_STEP_CAPTURE_ROOT=str(out/'capture'), VLN_CODE_COMMIT=head,
               HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1')
    manifest = dict(schema=1, protocol='step_multiview_v001', prepared_at=datetime.now(timezone.utc).isoformat(),
         git_head=head,worktree_dirty=bool(dirty),execution_backend='native_reproduction',
         episodes=104,events=0,cases=cases,episode_ids=[e['episode_id'] for e in selected],seed=2,
         arms={'baseline':{'mode':'baseline','threshold_m':None}},code_root=str(code),runtime_env=env,
         source_sha256=originals,code_sha256={n:sha(code/n) for n in names},
         official_split_sha256=sha(official),dataset_source_sha256=cohort['source_sha256'],
         capture=dict(view_offsets_deg=[0,45,90,135,180,225,270,315],front_view_indices=[1,0,7],
                      resolution=[640,480],format='lossless_png_perspective_sets',
                      heading='measured current robot +X projected into world XY; positive yaw is left',
                      optical_center='measured native front camera position',
                      robot_visibility='hidden for auxiliary multiview render only; restored before native continuation',
                      physics_during_capture=0,terminal_capture=True,policy_input='unchanged original front RGB'),
         interpretation='New independent baseline navigation of historical failure-selected tasks; no correction. New outcomes are retained regardless of success.')
    save(out/'cohort.json',cohort)
    save(out/'manifest.json',manifest)
    save(out/'seal.json',dict(manifest_sha256=sha(out/'manifest.json'),cohort_sha256=sha(out/'cohort.json')))
    dataset = out/'prepared/dataset/fine/val_unseen/val_unseen.json.gz'
    dataset.parent.mkdir(parents=True)
    with gzip.open(dataset,'wt') as f:json.dump({'episodes':selected},f)
    save(out/'episode_ids.json',manifest['episode_ids'])
    save(out/'status.json',dict(phase='prepared',episodes=104,simulation_started=False))
    save(out/'preparation_validation.json',dict(passed=True,older=48,newer=56,unique_episodes=104,
         scenes=len({e['scan'] for e in selected}),source_files=len(names),
         native_run_full_unchanged=sha(code/'benchmarks/vlnverse/runner/run_full.py')==sha(ROOT/'benchmarks/vlnverse/runner/run_full.py')))
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); m=prepare(a.output.resolve())
    print(json.dumps(dict(output=str(a.output.resolve()),episodes=m['episodes'],scenes=len({c['scene'] for c in m['cases']}))))
