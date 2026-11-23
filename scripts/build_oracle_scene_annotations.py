"""CPU scene geometry for an explicitly selected, unrun Oracle cohort.

Candidate generation is separate from assistant visual review and task association.
This entry never loads a policy, creates a simulator, or launches evaluation.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gc
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/VLNVerse/data/raw_data/final_splits/fine_val_unseen.json.gz')
IDS = ROOT / 'experiments/oracle_recovery/auto_branch_v001/scene_plan_20261116_01/draft_episode_ids.json'
IDS_SHA = '579c835e83dcf7b9701e32f672ebaaa7de1e67d488de90946d470ced33d860b5'


def read(p):
    return json.loads(Path(p).read_text())


def write(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(2 ** 20), b''):
            h.update(b)
    return h.hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def extract(out):
    import build_checkpoint_review as geometry
    import cv2
    cv2.setNumThreads(1)
    out.mkdir(parents=True, exist_ok=False)
    (out / 'source').mkdir()
    sources = [Path(__file__), ROOT / 'scripts/build_checkpoint_review.py']
    for p in sources:
        shutil.copyfile(p, out / 'source' / p.name)
    ids = read(IDS)
    assert sha(IDS) == IDS_SHA
    if isinstance(ids, dict):
        ids = ids['episode_ids']
    assert len(ids) == len(set(ids)) == 400
    with gzip.open(OFFICIAL, 'rt') as f:
        episodes = json.load(f)['episodes']
    selected = [e for e in episodes if e['episode_id'] in set(ids)]
    counts = Counter(e['scan'] for e in selected)
    assert len(selected) == 400 and len(counts) == 22
    # Natural language is retained in private task metadata; the review portal
    # needs only geometry and IDs, so it need not alter or translate instructions.
    write(out / 'tasks.json', selected)
    shutil.copyfile(IDS, out / 'episode_ids.json')
    manifest = dict(schema='oracle-scene-annotation-v1', created_at=now(),
                    status='extracting_cpu_geometry', gpu_used=False, navigation_episodes=0,
                    git_head=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
                    official_sha256=sha(OFFICIAL), ids_sha256=sha(IDS),
                    scene_counts=dict(sorted(counts.items())),
                    source_sha256={p.name: sha(p) for p in sources},
                    evidence='USD mesh projection; pending assistant visual review; not collision certification')
    write(out / 'manifest.json', manifest)
    for name, command in [('git_status.txt',['git','status','--short']), ('git_diff.patch',['git','diff','--'])]:
        (out / name).write_text(subprocess.check_output(command, cwd=ROOT, text=True))
    write(out / 'commands.json', dict(argv=sys.argv, interpreter=sys.executable,
          LD_LIBRARY_PATH=os.environ.get('LD_LIBRARY_PATH'), threads=1))
    for index, scene in enumerate(sorted(counts), 1):
        geometry.extract(out, scene, resolution=.035)
        geometry.map_scene(out, scene)
        write(out / 'status.json', dict(phase='extracting_cpu_geometry', completed=index,
              total=len(counts), scene=scene, updated_at=now(), gpu_used=False))
        gc.collect()
    manifest.update(status='geometry_ready_pending_visual_review', extraction_finished_at=now())
    write(out / 'manifest.json', manifest)
    write(out / 'status.json', dict(phase=manifest['status'], completed=22, total=22, updated_at=now(), gpu_used=False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    extract(args.output)


if __name__ == '__main__':
    main()
