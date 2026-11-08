"""Freeze the ten-case Oracle pilot before any intervention outcomes exist."""
import collections
import hashlib
import json
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.analyze_crossing_failures import dense_path

SOURCE = ROOT / 'outputs/reproduction/streamvln_scene250_5seeds_20261101_v2'
OUTPUT = ROOT / 'outputs/oracle_crossing/seed2_10_20261103'
ATTR = ROOT / 'outputs/checkpoint_review/seed2_crossing_attribution_20261103'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(p, x):
    Path(p).write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')


def main():
    if (OUTPUT / 'manifest.json').exists():
        raise RuntimeError('Cohort already frozen; do not reselect after outcomes.')
    ranking = json.loads((OUTPUT / 'candidate_ranking.json').read_text())
    evidence = json.loads((ATTR / 'evidence.json').read_text())
    source_cases = {c['episode_id']: c for c in evidence['cases']}
    counts = collections.Counter()
    chosen = []
    for r in ranking:
        if counts[r['scene']] >= 2:
            continue
        counts[r['scene']] += 1
        c = source_cases[r['episode_id']]
        scene = evidence['scenes'][r['scene']]
        cross = next(x for x in scene['crossings'] if x['id'] == r['crossing_id'])
        ref, arc = dense_path(c['reference_path'], spacing=.025)
        closest = int(np.linalg.norm(ref - cross['position'], axis=1).argmin())
        target_arc = float(arc[closest] + .75)
        target = int(np.argmin(abs(arc - target_arc)))
        assert target + 10 < len(ref), 'Do not teleport next to the goal'
        d = ref[min(len(ref)-1, target+12)] - ref[target]
        yaw = float(np.arctan2(d[1], d[0]))
        chosen.append(dict(r, instruction=c['instruction'], reference_path=c['reference_path'],
                           crossing=cross, target_xy=ref[target].tolist(), target_yaw_rad=yaw,
                           target_arc_m=float(arc[target]), crossing_ref_arc_m=float(arc[closest]),
                           crossing_ref_distance_m=float(np.linalg.norm(ref[closest]-cross['position'])),
                           target_crossing_distance_m=float(np.linalg.norm(ref[target]-cross['position'])),
                           source_steps=c['source_steps'], source_steps_sha256=c['source_steps_sha256'],
                           source_video=c['source_video'], original_metrics=c['metrics'],
                           same_branch_confirmed_seeds=[2,3],
                           review_basis='Assistant inspected paired seed2/3 top-down trajectories and original instruction/branch attribution. Other failed seeds are outcome evidence only.'))
        if len(chosen) == 10:
            break
    assert len(chosen) == 10
    original = json.loads((SOURCE / 'manifest.json').read_text())
    code = OUTPUT / 'code_control'
    for name, expected in original['code_sha256'].items():
        src = Path(original['code_root']) / name
        if sha(src) != expected:
            raise RuntimeError('Original source changed: ' + name)
        dst = code / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    env = dict(original['runtime_env'], VLN_OUTPUT_ROOT=str(OUTPUT / 'runs_control'),
               VLN_SIM_CACHE_ROOT=str(OUTPUT / 'sim_cache_control'))
    (OUTPUT / 'runs_control').mkdir(exist_ok=True)
    write(OUTPUT / 'runs_control/visualization.json',
          dict(schema=1, seeds=[2], output_dir=str(OUTPUT / 'visualization_control')))
    write(OUTPUT / 'cohort.json', chosen)
    manifest = dict(schema=1, created_at=datetime.now(timezone.utc).isoformat(), cases=chosen,
                    source_campaign=str(SOURCE), run_seed=2, count=10,
                    selection_rule='48 seed2 crossing-attributed failures; normal-stop failure in seed3; matching outgoing segment nominated and map-reviewed; rank by number of normally failed seeds then seed2/3 segment agreement; maximum two cases per scene; take first ten.',
                    attribution_sha256=sha(ATTR/'attribution.csv'), ranking_sha256=sha(OUTPUT/'candidate_ranking.json'),
                    source_scores_sha256=sha(SOURCE/'episodes.csv'),
                    protocol=dict(arms=['control','oracle'], max_interventions=1, policy_memory='preserve',
                                  intervention='position and yaw; next natural model generation boundary',
                                  target_distance_along_reference_after_crossing_m=.75,
                                  oracle='live assistant; explicit per-event decision, no automatic GT teleport',
                                  wait_timeout_seconds=None, mode='physical',
                                  metrics='SR/NE and paired outcomes; assisted SPL not a baseline reproduction result'),
                    control=dict(code_root=str(code), code_sha256=original['code_sha256'], runtime_env=env,
                                 run_id='peng_fine_oracle10_control_20261103', episode_ids=[c['episode_id'] for c in chosen]))
    write(OUTPUT / 'manifest.json', manifest)
    shutil.copy2(SOURCE/'model_fingerprints.json', OUTPUT/'model_fingerprints.json')
    for c in chosen:
        print(c['episode_id'],c['crossing_id'],'target',c['target_xy'],'yaw',round(c['target_yaw_rad'],3),'distance',round(c['target_crossing_distance_m'],3))


if __name__ == '__main__':
    main()
