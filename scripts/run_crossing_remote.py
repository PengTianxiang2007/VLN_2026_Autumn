"""Bounded remote replay; API credential is accepted only via stdin, never serialized."""
import json,sys,os,time,signal,subprocess,multiprocessing,urllib.request,urllib.error,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=Path(sys.argv[1]).resolve();R=json.loads((P/'registration.json').read_text());TAG=R['tag']
sys.path.insert(0,str(Path(R['source'])/'scripts'))
import replay_crossing_checkpoint as replay
KEY=None

def read_stream(response):
    content=[];reasoning=[];finish=None;usage=None;identity={}
    for raw in response:
        line=raw.decode('utf-8').strip()
        if not line.startswith('data:'):continue
        data=line[5:].strip()
        if data=='[DONE]':break
        chunk=json.loads(data)
        if 'error' in chunk:raise RuntimeError('Provider stream error')
        for key in ['id','model','created']:
            if key in chunk:identity[key]=chunk[key]
        if chunk.get('usage'):usage=chunk['usage']
        for choice in chunk.get('choices',[]):
            delta=choice.get('delta',{})
            if delta.get('content'):content.append(delta['content'])
            if delta.get('reasoning_content'):reasoning.append(delta['reasoning_content'])
            if choice.get('finish_reason'):finish=choice['finish_reason']
    if finish is None:raise ConnectionError('Stream ended before finish_reason')
    return dict(**identity,choices=[dict(index=0,finish_reason=finish,message=dict(role='assistant',content=''.join(content),reasoning_content=''.join(reasoning)))],usage=usage)

def remote(base,payload,timeout=600):
    wire={k:v for k,v in payload.items() if k not in ['seed','chat_template_kwargs','response_format']}
    wire.update(thinking={'type':'enabled'},reasoning_effort=R.get('reasoning_effort','max'),response_format={'type':'json_object'},stream=True,max_tokens=32768)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    transport=P/'transport';transport.mkdir(exist_ok=True)
    for attempt in range(8):
        started=time.monotonic();result=None;error=None;fatal=False
        req=urllib.request.Request(R['endpoint'],data=json.dumps(wire,ensure_ascii=False).encode(),headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'})
        try:
            with opener.open(req,timeout=min(timeout,R.get("request_timeout_seconds",600))) as response:result=read_stream(response)
            if result['choices'][0]['finish_reason']=='length':
                error='Output length exhausted at '+str(wire['max_tokens'])
            elif result['choices'][0]['finish_reason']!='stop':error='Unexpected finish reason'
        except urllib.error.HTTPError as e:
            error='Official API HTTP '+str(e.code);fatal=e.code not in [408,429,500,502,503,504]
        except (urllib.error.URLError,ConnectionError,TimeoutError,OSError,json.JSONDecodeError,RuntimeError) as e:
            error=type(e).__name__+': '+str(e)
        with (transport/(str(os.getpid())+'.jsonl')).open('a') as f:
            f.write(json.dumps(dict(time=replay.now(),attempt=attempt,internal_request_sha256=replay.canonical_hash(payload),provider_request_sha256=replay.canonical_hash(wire),max_tokens=wire['max_tokens'],ok=error is None,error=error,usage=result.get('usage') if result else None,elapsed_seconds=time.monotonic()-started))+'\n')
        if error is None:
            result['_provider_request_sha256']=replay.canonical_hash(wire)
            result['_transport_adapter']='remote-json-stream-v2; actual output budget '+str(wire['max_tokens'])
            return result
        if fatal:raise RuntimeError(error)
        if result and result['choices'][0]['finish_reason']=='length':wire['max_tokens']=min(131072,wire['max_tokens']*2)
        if attempt==7:raise RuntimeError('Bounded remote retries exhausted: '+str(error))
        time.sleep(min(60,2**(attempt+1))+os.getpid()%5)

def worker(job):
    global KEY
    def terminate_worker(*args): raise SystemExit(143)
    signal.signal(signal.SIGTERM,terminate_worker)
    replay.call_model=remote
    try:replay.replay_one(job)
    except Exception as e:
        print(json.dumps({'episode':job[2],'failed':type(e).__name__+': '+str(e)}),flush=True)
        raise SystemExit(1)
    finally:KEY=None

def main():
    global KEY
    KEY=sys.stdin.readline().strip().rstrip('"')
    if not KEY:raise ValueError('Missing credential on stdin')
    run=P/'runs'/TAG;run.mkdir(parents=True,exist_ok=True)
    source=replay.read_json(P/'inputs.json');protocol=replay.read_json(P/'protocol.json')
    inf=dict(base_url=R['endpoint'].rsplit('/',1)[0],served_model=R['model'],max_tokens=8192,thinking=True,chat_template_kwargs={'enable_thinking':True})
    hashes={name:replay.file_hash(Path(R['source'])/name) for name in ['core/crossing_checkpoint.py','scripts/replay_crossing_checkpoint.py']}
    manifest=dict(schema=1,tag=TAG,split='development',protocol_sha256=replay.file_hash(P/'protocol.json'),source_sha256=replay.file_hash(P/'inputs.json'),prompt_sha256=replay.canonical_hash(replay.SYSTEM_PROMPT),model_path=R['model'],inference_backend='official_zhipu_api',inference={k:v for k,v in inf.items() if k!='base_url'},episodes=R['development'],code_hashes=hashes,provider_adapter='remote-json-stream-v2',key_stored=False)
    replay.write_json(run/'manifest.json',manifest)
    for name in hashes:
        dst=run/'source'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(Path(R['source'])/name,dst)
    shutil.copy2(__file__,run/'source/remote_driver.py')
    processes=[];outcome='failed';error=None
    def stop(*args):raise RuntimeError('Termination requested')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        for eid in R['development']:
            child=multiprocessing.get_context('fork').Process(target=worker,args=((str(P),TAG,eid,source[eid],inf),));child.start();processes.append(child)
        KEY=None
        replay.write_json(P/'status.json',dict(phase='running',workers=[c.pid for c in processes],expected_calls=R['expected_model_calls'],started_at=replay.now()))
        deadline=time.monotonic()+28800
        while any(c.is_alive() for c in processes):
            if time.monotonic()>deadline:raise TimeoutError('Eight-hour limit')
            time.sleep(2)
        if any(c.exitcode!=0 for c in processes):raise RuntimeError('Worker failure')
        replay.score(P,TAG)
        subprocess.run([sys.executable,'-B',str(ROOT/'scripts/audit_crossing_remote.py'),'--output',str(P),'--tag',TAG],check=True,timeout=600)
        subprocess.run([sys.executable,'-B',str(ROOT/'scripts/analyze_crossing_checkpoint.py'),'--output',str(P),'--tag',TAG],check=True,timeout=600)
        subprocess.run([str(ROOT/'backbone/streamvln/.venv/bin/python'),'-B',str(ROOT/'scripts/export_crossing_iteration.py'),'--output',str(P),'--tag',TAG,'--destination',str(P/'exports/final')],check=True,timeout=600)
        outcome='complete'
    except BaseException as e:error=type(e).__name__+': '+str(e)
    finally:
        for c in processes:
            if c.is_alive():c.terminate()
        for c in processes:
            c.join(timeout=10)
            if c.is_alive():c.kill();c.join()
        KEY=None
        summary=dict(tag=TAG,output=str(P),phase=outcome,error=error,finished_at=replay.now(),credential_on_disk=False,workers_exited=all(not c.is_alive() for c in processes))
        replay.write_json(P/'status.json',summary)
        documentation=[P/'README.md',ROOT/R.get('experiment_readme','experiments/crossing_checkpoint/v004/README.md'),ROOT/'docs/STATUS.md',ROOT/'experiments/README.md',ROOT/'experiments/crossing_checkpoint/README.md']
        if R.get('run_readme'):documentation.append(ROOT/R['run_readme'])
        for f in documentation:
            with f.open('a') as h:h.write('\n最终状态：'+json.dumps(summary,ensure_ascii=False)+'\n')
        print(json.dumps(summary),flush=True)
    return 0 if outcome=='complete' else 1
if __name__=='__main__':sys.exit(main())
