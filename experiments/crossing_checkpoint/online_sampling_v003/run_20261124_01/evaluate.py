"""Choose thresholds on design-scene-out predictions, then freeze and replay."""
import hashlib
import json
from functools import lru_cache
from pathlib import Path
import subprocess
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CHECK = ROOT/'outputs/crossing_checkpoint'
OLD = CHECK/'online_sampling_v002/run_20261124_01'
OUT = CHECK/'online_sampling_v003'/HERE.name
SPLIT = ROOT/'experiments/crossing_checkpoint/online_sampling_v002/run_20261124_01/split.json'
MODEL = ROOT/'core/jev_online_sampler_v003.js'
LOCK = HERE/'selection.json'
read = lambda p: json.loads(p.read_text())


def save(file, obj):
    with file.open('x') as f:
        json.dump(obj, f, indent=2, allow_nan=False)
        f.write('\n')


def hashes():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [SPLIT, MODEL, ROOT/'core/jev_online_sampler_v001.js', HERE/'stream.cjs', Path(__file__).resolve()]}


def stream(cases, profiles=None):
    return json.loads(subprocess.check_output(['node', HERE/'stream.cjs'], cwd=ROOT,
        input=json.dumps(dict(episodes=[c['episode'] for c in cases], profiles=profiles)).encode()))


def match(pred, truth):
    @lru_cache(None)
    def visit(i,j):
        if i == len(pred) or j == len(truth):
            return (), 0
        opts = [visit(i+1,j),visit(i,j+1)]
        delta = abs(pred[i]-truth[j])
        if delta <= 3:
            pairs, dist = visit(i+1,j+1)
            opts.append((((pred[i],truth[j]),)+pairs, dist+delta))
        return max(opts,key=lambda x:(len(x[0]),-x[1]))
    return list(visit(0,0)[0])


def fit(examples):
    x=np.asarray([row[0] for row in examples])
    y=np.asarray([row[1] for row in examples])
    mean=x.mean(axis=0)
    scale=x.std(axis=0).clip(.06,None)
    z=np.column_stack([np.ones(len(x)),(x-mean)/scale])
    beta=np.zeros(z.shape[1])
    # Fixed ridge penalty (no hyperparameter search); intercept unpenalized.
    penalty=np.diag([0.]+[5.]*(z.shape[1]-1))
    for _ in range(15):
        prob=1/(1+np.exp(-z@beta))
        grad=z.T@(prob-y)+penalty@beta
        step=np.linalg.solve((z.T*(prob*(1-prob)))@z+penalty, grad)
        beta-=step
        if np.max(abs(step))<1e-8: break
    weights=beta[1:]/scale
    return dict(weights=weights.tolist(), intercept=float(beta[0]-mean@weights))


def scores(rows, model):
    return [(i,float(1/(1+np.exp(-(model['intercept']+np.dot(x,model['weights'])))))) for i,x in rows]


def apply(rows, threshold, spacing):
    frames=[]
    for frame,score in rows:
        if score>=threshold and (not frames or frame-frames[-1]>=spacing):
            frames.append(frame)
    return frames


def metric(rows):
    h=sum(len(r['pairs']) for r in rows)
    n=sum(len(r['frames']) for r in rows)
    refs=sum(len(r['reference']) for r in rows)
    return dict(hits=h,candidates=n,references=refs,precision=h/n if n else 0,
                coverage=h/refs if refs else None,positive_episodes=sum(bool(r['pairs']) for r in rows))


def design(cases):
    raw=stream(cases)
    samples={c['episode']:[(x,any(abs(i-r)<=3 for r in c['reference'])) for i,x in raw[c['episode']]] for c in cases}
    scene=lambda ep:ep.rsplit('_',2)[0]
    flatten=lambda exclude:[v for ep,rows in samples.items() if scene(ep)!=exclude for v in rows]
    folds={sc:fit(flatten(sc)) for sc in {scene(ep) for ep in samples}}
    oof={ep:scores(raw[ep],folds[scene(ep)]) for ep in samples}
    grid=[]
    for spacing in (7,10):
        for t in range(20,91,5):
            rows=[]
            for c in cases:
                frames=apply(oof[c['episode']],t/100,spacing)
                rows.append(dict(frames=frames,reference=c['reference'],pairs=match(frames,c['reference'])))
            grid.append(dict(threshold=t/100,spacing=spacing,**metric(rows)))
    eligible=[g for g in grid if g['hits']>=12 and g['positive_episodes']>=6]
    chosen={}
    for key,target in [('balanced',0),('p60',.60),('p70',.70)]:
        if key=='balanced':
            best=max(eligible,key=lambda g:(2*g['hits']/(g['candidates']+g['references']),g['coverage']))
        else:
            # Seek a small margin while maximizing supported coverage. Preserve
            # a strongest supported option when a target is out of reach.
            available=[g for g in eligible if g['precision']>=target+.03]
            if not available: available=[g for g in eligible if g['precision']>=target]
            best=max(available,key=lambda g:(g['hits'],g['precision'])) if available else max(eligible,key=lambda g:(g['precision'],g['hits']))
        chosen[key]=best
    fitted=fit(flatten(None))
    profiles={key:dict(**fitted,threshold=g['threshold'],spacing=g['spacing']) for key,g in chosen.items()}
    return dict(profiles=profiles,scene_out=chosen,design_scenes=len(folds),sha256=hashes()),grid


def main():
    phase=sys.argv[1]
    if phase not in ('design','validation'): raise ValueError(phase)
    cases=read(OLD/(phase+'.json'))['cases']
    assert [c['number'] for c in cases]==read(SPLIT)[phase]
    if phase=='design':
        lock,grid=design(cases)
        save(OUT/'design_grid.json',grid)
        save(LOCK,lock)
        print('Scene-out',lock['scene_out'])
    else:
        lock=read(LOCK)
        assert lock['sha256']==hashes()
    results=stream(cases,lock['profiles'])
    for c in cases:
        for mode,frames in results[c['episode']].items():
            c['rows'][mode]=dict(frames=frames,pairs=match(frames,c['reference']))
    summary={mode:metric([dict(**c['rows'][mode],reference=c['reference']) for c in cases])
             for mode in ['baseline','near',*lock['profiles']]}
    save(OUT/(phase+'.json'),dict(summary=summary,cases=cases))
    print(phase,summary)

if __name__=='__main__': main()
