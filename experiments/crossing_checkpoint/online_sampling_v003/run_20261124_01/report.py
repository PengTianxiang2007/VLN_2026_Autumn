"""Freeze four supported operating points, then perform a single holdout replay."""
from datetime import datetime, timezone
import hashlib
import sys
from evaluate import HERE, OUT, OLD, LOCK, SPLIT, read, save, hashes, match, stream, metric

SETTINGS=HERE/'profiles.json'
PHASE=sys.argv[1]
first=read(LOCK)
assert hashes()==first['sha256']
this_hash=hashlib.sha256((HERE/'report.py').read_bytes()).hexdigest()
if PHASE=='freeze':
    grid=read(OUT/'design_grid.json')
    supported=[g for g in grid if g['hits']>=12 and g['positive_episodes']>=6]
    high_coverage=max((g for g in supported if g['coverage']>=.75),
                      key=lambda g:(g['precision'],g['hits']))
    strict=max(supported,key=lambda g:(g['precision'],g['hits']))
    choices=dict(coverage=high_coverage,p60=first['scene_out']['p60'],
                 p70=first['scene_out']['p70'],strict=strict)
    model=first['profiles']['p60']
    profiles={mode:{**model,'threshold':g['threshold'],'spacing':g['spacing']} for mode,g in choices.items()}
    save(SETTINGS,dict(profiles=profiles,scene_out=choices,sha256=hashes(),report_sha256=this_hash,
                       frozen_at=datetime.now(timezone.utc).isoformat()))
    print({k:(v['hits'],v['candidates']) for k,v in choices.items()})
elif PHASE in ('design','validation'):
    lock=read(SETTINGS)
    assert lock['report_sha256']==this_hash and lock['sha256']==hashes()
    cases=read(OLD/(PHASE+'.json'))['cases']
    assert [c['number'] for c in cases]==read(SPLIT)[PHASE]
    result=stream(cases,lock['profiles'])
    for c in cases:
        for mode,frames in result[c['episode']].items():
            c['rows'][mode]=dict(frames=frames,pairs=match(frames,c['reference']))
    summary={mode:metric([dict(**c['rows'][mode],reference=c['reference']) for c in cases])
             for mode in ['baseline','near',*lock['profiles']]}
    save(OUT/(PHASE+'_profiles.json'),dict(summary=summary,cases=cases))
    print(summary)
else:
    raise ValueError(PHASE)
