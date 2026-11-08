"""Seven parallel multimodal correction requests; stdin/pipe-only user credential."""
import argparse
import base64
import getpass
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
BASE='https://api.deepseek.com'

def now():return datetime.now(timezone.utc).isoformat()
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix('.tmp');t.write_text(json.dumps(d,ensure_ascii=False,indent=2));t.replace(p)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None

def call(path,key,payload=None):
    if path not in ['/models','/chat/completions']:raise ValueError('Unregistered endpoint')
    body=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    req=urllib.request.Request(BASE+path,data=body,headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open(req,timeout=180) as r:raw=r.read().decode()
    # Never persist reflected credentials, including in error bodies.
    return raw.replace(key,'[redacted]')

def wire(case,prepared,config):
    image=prepared/case['image_path']
    if sha(image)!=case['image_sha256']:raise ValueError('Image hash mismatch')
    text=(prepared/'prompt_en.txt').read_text().format(selected_direction=case['selected_direction'],selected_entrance_description=case['selected_entrance_description'])
    return dict(model=config['model'],messages=[dict(role='user',content=[dict(type='text',text=text),dict(type='image_url',image_url=dict(url='data:image/png;base64,'+base64.b64encode(image.read_bytes()).decode(),detail='original'))])],temperature=0,max_tokens=512,stream=False,thinking={'type':'disabled'})

def run_case(case,prepared,out,config,key,gate):
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    def stop(*_):raise KeyboardInterrupt('Termination requested')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    folder=out/'cases'/case['sample_id'];folder.mkdir(parents=True)
    state=dict(phase='waiting_start',pid=os.getpid(),sample_id=case['sample_id'])
    write(folder/'status.json',state)
    try:
        request=wire(case,prepared,config);write(folder/'request.json',request)
        write(folder/'input_audit.json',dict(image_sha256=case['image_sha256'],checkpoint_frame=case['checkpoint_frame'],prompt_sha256=sha(prepared/'prompt_en.txt'),request_sha256=sha(folder/'request.json'),selected_branch_id=case['selected_branch_id']))
        gate.wait(60)
        if not gate.is_set():raise TimeoutError('Start gate timeout')
        state.update(phase='running',started_at=now());write(folder/'status.json',state)
        raw=call('/chat/completions',key,request);(folder/'response.json').write_text(raw)
        response=json.loads(raw);choice=response['choices'][0]
        text=choice['message'].get('content')
        if choice['finish_reason']!='stop' or not isinstance(text,str) or not text.strip():raise ValueError('Incomplete or empty response; raw response preserved')
        result=dict(sample_id=case['sample_id'],episode_id=case['episode_id'],checkpoint_frame=case['checkpoint_frame'],selected_direction=case['selected_direction'],instruction=text,response_model=response.get('model'),usage=response.get('usage'))
        write(folder/'instruction.json',result)
        state.update(phase='complete',response_model=response.get('model'))
    except BaseException as e:
        state.update(phase='cancelled' if isinstance(e,KeyboardInterrupt) else 'failed',error_type=type(e).__name__)
        if isinstance(e,urllib.error.HTTPError):
            state['http_status']=e.code
            state['provider_error']=e.read(4096).decode(errors='replace').replace(key,'[redacted]')
        else:state['error']=str(e).replace(key,'[redacted]')[:600]
    finally:
        state['finished_at']=now();write(folder/'status.json',state)
        key=None


def worker(args):
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    key=sys.stdin.readline().strip();sys.stdin.close()
    if not key:raise ValueError('Missing stdin credential')
    prepared=args.prepared.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    config=read(prepared/'model.json');cases=read(prepared/'samples.json');manifest=read(prepared/'manifest.json')
    state=dict(phase='checking_service',supervisor_pid=os.getpid(),started_at=now(),model=config['model'],concurrency=7,expected_calls=7,completed=0,credential_on_disk=False,navigation_executed=False,simulation_started=False)
    children=[]
    def update(**kw):
        state.update(kw,updated_at=now());write(out/'status.json',state)
    def stop(*_):raise KeyboardInterrupt('Termination requested')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);update()
    try:
        assert config['base_url']==BASE and config['model']=='deepseek-flash'
        for name,expected in manifest['prepared_hashes'].items():assert sha(prepared/name)==expected,name
        assert sha(Path(__file__))==manifest['worker_sha256']
        models=json.loads(call('/models',key));write(out/'service_models.json',models)
        if config['model'] not in [x['id'] for x in models['data']]:raise RuntimeError('Configured multimodal model absent from models endpoint')
        context=mp.get_context('fork');gate=context.Event()
        for case in cases:
            p=context.Process(target=run_case,args=(case,prepared,out,config,key,gate));p.start();children.append((case['sample_id'],p))
        write(out/'workers.json',[dict(sample_id=sid,pid=p.pid) for sid,p in children])
        update(phase='running_parallel',worker_pids=[p.pid for _,p in children]);gate.set()
        deadline=time.monotonic()+600
        while any(p.is_alive() for _,p in children):
            if time.monotonic()>deadline:raise TimeoutError('Parallel batch exceeded 600 seconds')
            update(completed=sum((out/'cases'/sid/'instruction.json').exists() for sid,_ in children))
            time.sleep(2)
        for _,p in children:p.join()
        rows=[read(out/'cases'/c['sample_id']/'instruction.json') for c in cases if (out/'cases'/c['sample_id']/'instruction.json').exists()]
        write(out/'instructions.json',rows)
        update(phase='complete' if len(rows)==len(cases) else 'failed_partial',completed=len(rows),semantic_review='pending')
    except BaseException as e:
        update(phase='cancelled' if isinstance(e,KeyboardInterrupt) else 'failed',error_type=type(e).__name__,error=str(e).replace(key,'[redacted]')[:600])
        if isinstance(e,urllib.error.HTTPError):update(http_status=e.code,provider_error=e.read(4096).decode(errors='replace').replace(key,'[redacted]'))
    finally:
        signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
        for _,p in children:
            if p.is_alive():p.terminate()
        for _,p in children:
            p.join(5)
            if p.is_alive():p.kill();p.join(5)
        # Scan this run only, using the in-memory secret; never print the secret.
        leaks=[str(p.relative_to(out)) for p in out.rglob('*') if p.is_file() and key.encode() in p.read_bytes()]
        update(workers_exited=all(not p.is_alive() for _,p in children),credential_on_disk=bool(leaks),finished_at=now())
        key=None;write(prepared/'completion.json',state)
        notice='\n\nDeepSeek v005七例图文并行收尾：'+json.dumps(state,ensure_ascii=False)+'；产物 '+str(out.relative_to(ROOT))+'。无导航或仿真。\n'
        for p in [prepared/'README.md',ROOT/'experiments/README.md',ROOT/'docs/STATUS.md']:
            with p.open('a') as f:f.write(notice)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepared',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--worker',action='store_true');args=ap.parse_args()
    if args.worker:return worker(args)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    key=getpass.getpass('DeepSeek API key (hidden): ')
    if not key:raise ValueError('Empty credential')
    cmd=[sys.executable,'-B',str(Path(__file__).resolve()),'--worker','--prepared',str(args.prepared.resolve()),'--output',str(args.output.resolve())]
    log=args.output.parent/(args.output.name+'.supervisor.log');log.parent.mkdir(parents=True,exist_ok=True)
    env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ['TOKEN','SECRET','API_KEY']) and 'proxy' not in k.lower()}
    with log.open('x') as f:p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=f,stderr=subprocess.STDOUT,cwd=ROOT,env=env,start_new_session=True)
    p.stdin.write((key+'\n').encode());p.stdin.close();key=None
    write(args.prepared/'launcher.json',dict(supervisor_pid=p.pid,command=cmd,credential_transport='hidden terminal input then anonymous stdin pipe'))
    time.sleep(3);print('Supervisor PID:',p.pid,'returncode:',p.poll(),flush=True)
    status=args.output/'status.json'
    if status.exists():print(status.read_text(),flush=True)

if __name__=='__main__':main()
