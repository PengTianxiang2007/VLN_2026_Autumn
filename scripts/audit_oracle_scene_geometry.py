"""Check reference-route/CPU-projection alignment, without inventing branch points."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.oracle_auto_branch import ReferenceGeometry
from core.oracle_landing_geometry import SceneLandingGeometry, digest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--geometry-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserving previous audit')
    root=args.geometry_root
    task_file=root/'tasks.json'
    tasks=json.loads(task_file.read_text())
    cache={};rows=[];hashes={str(task_file):digest(task_file)}
    for task in tasks:
        scene=task['scan']
        if scene not in cache:
            base=root/'scenes'/scene
            cache[scene]=SceneLandingGeometry.load(base/'geometry.json',base/'map_masks.npz')
            for name in ['geometry.json','map_masks.npz']:
                hashes[str(base/name)]=digest(base/name)
        audit=cache[scene];g=ReferenceGeometry(task['reference_path'])
        n=int(math.ceil(g.length/.05))+1
        samples=[audit.check_xy(g.at(float(arc))[0]) for arc in np.linspace(0,g.length,n)]
        rows.append(dict(episode_id=task['episode_id'],scene=scene,route_length_m=g.length,samples=n,
                    outside=sum(not s['inside_raster'] for s in samples),
                    off_floor=sum(not s['on_projected_floor'] for s in samples),
                    projected_obstacle_overlap=sum(bool(s['overlapping_layers']) for s in samples),
                    below_018m_clearance=sum(not s['in_approximate_safe_mask'] for s in samples),
                    assessments=dict(Counter(s['assessment'] for s in samples))))
    summary=dict(tasks=len(rows),scenes=len(cache),sample_spacing_m=.05,
                 **{k:sum(r[k] for r in rows) for k in ['samples','outside','off_floor','projected_obstacle_overlap','below_018m_clearance']},
                 tasks_with_projected_overlap=sum(r['projected_obstacle_overlap']>0 for r in rows),
                 scope='Reference-route alignment only; no observed divergence, chosen landing or physical collision certification.')
    args.output.write_text(json.dumps(dict(summary=summary,tasks=rows,source_sha256=hashes),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    main()
