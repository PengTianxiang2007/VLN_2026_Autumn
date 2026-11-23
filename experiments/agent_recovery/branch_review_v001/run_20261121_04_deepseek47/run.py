"""Replay archived first-call messages with concurrent DeepSeek workers."""
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import sys
import subprocess
import shutil
import httpx
sys.path.insert(0, str(Path('scripts').resolve()))
from run_recovery_branch_review import read, write, validate, now

prior = Path('outputs/agent_recovery/branch_review_v001/run_20261121_02_all47')
out = prior.parent / 'run_20261121_04_deepseek47'
previous = prior.parent / 'run_20261121_03_deepseek2'
record = Path(__file__).resolve().parent
endpoint = 'https://api.deepseek.com/chat/completions'

def worker(case, key):
    folder = out / case
    source = prior / 'cases' / case
    request = read(source / 'request.json')
    body = {k: request[k] for k in ('messages','temperature','top_p','max_tokens','response_format')}
    body.update(model='deepseek-flash', thinking={'type':'disabled'})
    write(folder / 'request.json', body)
    shutil.copy2(source / 'input.json', folder / 'input.json')
    info = dict(case=case, pid=os.getpid(), started_at=now(), phase='requesting')
    write(folder / 'status.json', info)
    try:
        with httpx.Client(timeout=httpx.Timeout(300,connect=30),follow_redirects=False) as client:
            response=client.post(endpoint,headers={'Authorization':'Bearer '+key},json=body)
        info['http_status']=response.status_code
        (folder/'response.json').write_text(response.text.replace(key,'[redacted]'))
        response.raise_for_status()
        choice=response.json()['choices'][0]
        answer=json.loads(choice['message']['content'])
        errors=validate(answer,read(prior/'manifest.json')['schema'])
        if choice['finish_reason']!='stop': errors.append('Incomplete response')
        info.update(phase='invalid' if errors else 'complete',answer=answer,validation_errors=errors)
    except Exception as exc:
        info.update(phase='error',error=str(exc).replace(key,'[redacted]'))
    info['finished_at']=now()
    write(folder/'status.json',info)

if __name__=='__main__':
    key=sys.stdin.readline().strip()
    if not key: raise SystemExit('Missing credential')
    out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(__file__,out/'run.py')
    manifest = read(prior/'manifest.json')
    cases = [c['case_id'] for c in manifest['cases']]
    reused = ['C50','C07']
    for cid in reused:
        assert read(previous/cid/'status.json')['phase'] == 'complete'
        assert read(previous/cid/'input.json') == read(prior/'cases'/cid/'input.json')
        assert read(previous/cid/'request.json')['messages'] == read(prior/'cases'/cid/'request.json')['messages']
        shutil.copytree(previous/cid,out/cid)
    todo = [c for c in cases if c not in reused]
    write(out/'manifest.json',dict(cases=cases,reused=reused,new_cases=todo,prior=str(prior),model='deepseek-flash',endpoint=endpoint,version=manifest['version'],upstream='v006',git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    jobs=[mp.Process(target=worker,args=(case,key)) for case in todo]
    for job in jobs: job.start()
    write(out/'launch.json',dict(supervisor=os.getpid(),workers={c:p.pid for c,p in zip(todo,jobs)},started_at=now()))
    for job in jobs: job.join()
    transient=[case for case in todo if (r:=read(out/case/'status.json'))['phase']=='error' and (r.get('http_status') in (408,429,500,502,503,504,524,525) or 'http_status' not in r)]
    if transient:
        import time
        time.sleep(8)
        for case in transient:
            (out/case).rename(out/(case+'.attempt1'))
        with mp.Pool(5) as pool: pool.starmap(worker,[(case,key) for case in transient])
    results={c:read(out/c/'status.json') for c in cases}
    write(out/'results.json',results)
    from collections import Counter
    write(record/'summary.json',dict(total=len(cases),reused=reused,initial_concurrency=len(jobs),transport_retries=transient,statuses=dict(Counter(r['phase'] for r in results.values())),cases={k:v['phase'] for k,v in results.items()},completed_at=now()))
