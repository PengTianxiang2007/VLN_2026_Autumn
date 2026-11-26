"""Score and replay the 48 original recordings, using content-matched v004 windows."""
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT), str(ROOT/'scripts')]
from core.crossing_lite import windows
from core.jev_node import build_compact_fallback_noul_request, request_digest
from run_rxr_offline_jev import credentials
from run_jev_noul_five_concurrent import run_task
RUN=ROOT/'outputs/crossing_checkpoint/online_sampling_v003'/HERE.name
ATTR=ROOT/'outputs/checkpoint_review/seed2_crossing_attribution_20261103'
ANN=ROOT/'outputs/crossing_annotation/seed2_69'
HIST=ROOT/'outputs/crossing_checkpoint/jev_noul_v004'
read=lambda p:json.loads(Path(p).read_text())
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def save(path,data):
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False, separators=(',',':')))
    tmp.replace(path)


def prepare():
    import cv2
    cv2.setNumThreads(1)
    scratch=Path(tempfile.mkdtemp(prefix='jev-early48-',dir='/tmp'))
    save(RUN/'scratch.json',str(scratch))
    ev=read(ATTR/'evidence.json')
    evidence={c['episode_id']:c for c in ev['cases']}
    annot={c['episode_id']:c for c in read(ANN/'run_20261106_02/data.json')['cases']}
    extra=read(HERE/'extra_zh.json')
    cases=[]; maps={}
    images=scratch/'images';images.mkdir()
    cohort=[r for r in read(ATTR/'attribution_reviews.json') if r['status']=='crossing']
    assert len({r['episode_id'] for r in cohort})==len(cohort)==48
    for i,r in enumerate(cohort,1):
        eid=r['episode_id'];c=evidence[eid];scene=c['scene']; steps=c['steps']
        assert c['seed']==2 and steps[-1]['terminal'] and not any(s['terminal'] or s['rgb_reused'] for s in steps[:-1])
        if scene not in maps:
            m=ev['scenes'][scene]
            (images/(scene+'.png')).write_bytes(base64.b64decode(m['floorplan'].split(',',1)[1]))
            maps[scene]={k:m[k] for k in ['width','height','low','high','resolution']}
        if eid in annot:
            a=annot[eid]
            assert a['source_sha256']['steps']==c['source_steps_sha256'] and a['run_id']==c['run_id']
            rawframes=[base64.b64decode(x.split(',',1)[1]) for x in read(ANN/'run_20261106_01/media'/(eid+'.json'))]
            zh=a['instruction_zh'];assert a['instruction']==c['instruction']
        else:
            cap=cv2.VideoCapture(str(ATTR/'videos'/(eid+'.mp4')))
            rawframes=[]
            for step in steps:
                ok,img=cap.read()
                if not ok:raise ValueError('Short video '+eid)
                ok,enc=cv2.imencode('.webp',img[:480,:640],[cv2.IMWRITE_WEBP_QUALITY,90])
                assert ok;rawframes.append(enc.tobytes())
            cap.release();zh=extra[eid]
        assert len(rawframes)==len(steps)
        frames=[]
        for step,raw in zip(steps[:-1],rawframes[:-1]):
            key=sha(raw);file=images/(key+'.webp')
            if not file.exists():file.write_bytes(raw)
            frames.append(dict(frame=step['frame'],image=key,position=step['position']))
        assert 0<=r['frame']<len(frames)
        cases.append(dict(number=i,review_number=r['review_number'],episode_id=eid,scene=scene,frames=frames,
                          instruction_zh=zh,instruction_en=c['instruction'],reference_path=c['reference_path'],
                          wrong_frame=r['frame'],steps_sha256=c['source_steps_sha256']))
    save(RUN/'dataset.json',dict(cases=cases,maps=maps))
    with zipfile.ZipFile(RUN/'images.zip','x') as archive:
        for f in sorted(images.iterdir()):archive.write(f,'images/'+f.name)
    print('Prepared',len(cases),sum(len(c['frames']) for c in cases),flush=True)


def score(cache_only=False):
    tmp=Path(read(RUN/'scratch.json'));data=read(RUN/'dataset.json')
    images=tmp/'images'
    if not images.exists():
        tmp.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(RUN/'images.zip') as z:z.extractall(tmp)
    # The bulk full-wave record stores the exact frame/source hashes alongside its responses.
    full=HIST/'run_20261109_04_fullwave_prevapi'
    observed={(t['episode_id'],t['frame']):[x['rgb_sha256'] for x in t['images']] for t in read(full/'tasks.json')}
    cache={}
    digest_cache={}
    for folder in [HIST/'run_20261108_01_two_cases',HIST/'run_20261108_03_ten_final',full]:
        for row in read(folder/('rows.json' if folder==full else 'rows_v004.json')):
            if row['phase']!='complete' or row.get('question_version')!='v004':continue
            key=(row['episode_id'],row['frame'])
            if folder==full:cache[key]=row
            digest_cache[key]=row
    scorefile=RUN/'scores.json'
    results=read(scorefile) if scorefile.exists() else {}
    tasks=[]
    for c in data['cases']:
        eid=c['episode_id']; rows=results.setdefault(eid,{})
        obs=[dict(frame=f['frame'],rgb=f['image']+'.webp',rgb_sha256=f['image'],eligible_for_inference=True,
                  terminal=False,rgb_reused=False) for f in c['frames']]
        for k,win in windows(obs):
            if str(k) in rows:continue
            key=(eid,k)
            row=cache.get(key)
            if row and observed.get(key)==[f['rgb_sha256'] for f in win]:
                rows[str(k)]={'prob':row['answer']['probability_yes'],'request':row['request_sha256'],'source':full.name};continue
            row=digest_cache.get(key)
            if row and request_digest(build_compact_fallback_noul_request(win,images,model='jev-1.14.0')[0])==row['request_sha256']:
                rows[str(k)]={'prob':row['answer']['probability_yes'],'request':row['request_sha256'],'source':'archived_request_hash'};continue
            tasks.append(dict(episode_id=eid,scene=c['scene'],group='failure',frame=k,images=win,
                              question_version='v004',dataset=str(images),model='jev-1.14.0',attempts=2,timeout=85))
    save(scorefile,results)
    print('Confirmed cached',sum(map(len,results.values())),'remaining',len(tasks),flush=True)
    if cache_only or not tasks:return
    endpoint,key=credentials();os.environ['JEV_API_KEY']=key
    def process(t):
        with tempfile.TemporaryDirectory(dir=tmp) as work:
            r=run_task(dict(t,endpoint=endpoint,output=work))
            if r['phase']!='complete':return (t,r['error'])
            record={'prob':r['answer']['probability_yes'],'request':r['request_sha256'],'source':'easyjev',
                    'response':read(Path(work)/'cases'/t['episode_id']/('F%04d'%t['frame'])/'response.json')}
            return t,record
    def keep(t,result):
        if isinstance(result,str):return False
        results[t['episode_id']][str(t['frame'])]=result
        return True
    t,r=process(tasks[0])
    if not keep(t,r):raise RuntimeError(r)
    save(scorefile,results)
    print('First missing score complete',t['episode_id'],t['frame'],flush=True)
    for wave in range(2):
        missing=[]
        pending=[t for t in tasks if str(t['frame']) not in results[t['episode_id']]]
        with ThreadPoolExecutor(max_workers=48) as pool:
            for i,f in enumerate(as_completed([pool.submit(process,t) for t in pending]),1):
                t,r=f.result()
                if not keep(t,r):missing.append((t['episode_id'],t['frame'],r))
                if i%64==0:
                    save(scorefile,results)
                    print('Scored',sum(map(len,results.values())),flush=True)
        save(scorefile,results)
        if not missing:break
        save(RUN/'score_failures.json',missing)
    if missing:raise RuntimeError(str(len(missing))+' missing JEV scores')


if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1] in ('cache','score'):score(cache_only=sys.argv[1]=='cache')
    else:raise ValueError(sys.argv[1])
