"""Sequential seven-instruction generation and navigation stack deployment check."""
import json, os, signal, subprocess, sys, time, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from core.agent_route_choice import read,write,now
from run_human_route_choice import start_local
from run_agent_route_choice import wait_local
from run_crossing_local_batch import cleanup
from test_crossing_single_gpu import gpu_snapshot
from core.paths import model_environment,model_python,resource_root
OUT=ROOT/'outputs/agent_recovery/r2r_v001/run_20261107_01'
EXP=ROOT/'experiments/agent_recovery/r2r_v001/run_20261107_01'
state=dict(phase='starting',pid=os.getpid(),started_at=now(),gpu=0)
children=[];locks=[]
def update(**kw):
    state.update(kw,updated_at=now());write(OUT/'status.json',state)
def stop(*_): raise KeyboardInterrupt('Termination requested')
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def post(url,data):
    with opener.open(urllib.request.Request(url,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'}),timeout=180) as r:return json.load(r)
def launch(cmd,env,log):
    with (OUT/log).open('x') as f:p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    children.append(p);return p
try:
    qout=OUT/'qwen';qout.mkdir()
    config=read(EXP/'model.json')
    q,base=start_local(config,0,qout,locks,True);children.append(q)
    update(phase='qwen_loading',qwen_pid=q.pid,base_url=base)
    wait_local(q,base,config['model'])
    rows=[]
    for c in read(EXP/'samples.json'):
        update(phase='generating',sample=c['sample_id'])
        prompt=(EXP/'prompt_en.txt').read_text().format(**c['choice'])
        req=dict(model=config['model'],messages=[dict(role='user',content=prompt)],temperature=0,seed=20261107,max_tokens=512,chat_template_kwargs={'enable_thinking':False})
        write(qout/(c['sample_id']+'_request.json'),req)
        response=post(base+'/chat/completions',req);write(qout/(c['sample_id']+'_response.json'),response)
        answer=response['choices'][0];assert answer['finish_reason']=='stop'
        instruction=answer['message']['content'].strip();assert instruction
        rows.append(dict(sample_id=c['sample_id'],episode_id=c['episode_id'],checkpoint_frame=c['checkpoint_frame'],instruction=instruction))
        write(OUT/'instructions.json',rows)
    clean=cleanup(q);write(qout/'cleanup.json',clean);assert not clean['remaining'];children.remove(q)
    for h in locks:h.close()
    locks=[]
    update(phase='navigation_admission',instructions=7)
    # Recheck twice after Qwen release; no other process is modified.
    for _ in range(2):
        snap=gpu_snapshot();write(OUT/'navigation_gpu.json',snap)
        row=subprocess.check_output(['nvidia-smi','--id=0','--query-gpu=memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True).strip().split(',')
        assert int(row[0])>=40000 and int(row[1])<=10,row
        time.sleep(5)
    import fcntl
    for prefix in ('peng_vlnverse_gpu_','vln_2026_gpu_'):
        h=open('/tmp/'+prefix+'0.lock','a');locks.append(h);fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
    nav=OUT/'streamvln';nav.mkdir()
    env=model_environment('streamvln',0)
    env={k:v for k,v in env.items() if 'proxy' not in k.lower()}
    env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4')
    p=launch([str(model_python('streamvln')),'-B',str(ROOT/'benchmarks/vlnverse/runner/service.py'),'--method','StreamVLN','--checkpoint',str(resource_root()/'models/StreamVLN_R2R_v1_3'),'--output',str(nav),'--smoke-steps','0'],env,'streamvln.log')
    update(phase='streamvln_loading',streamvln_pid=p.pid)
    deadline=time.monotonic()+2700
    while not (nav/'ready.json').exists():
        assert p.poll() is None,'StreamVLN exited'
        assert time.monotonic()<deadline,'StreamVLN startup timeout'
        time.sleep(3)
    port=read(nav/'ready.json')['port']
    reset=post(f'http://127.0.0.1:{port}/agent/StreamVLN/reset',{'reset_index':None});assert reset['status']=='success'
    write(nav/'reset_check.json',reset)
    simenv=dict(env,VLN_SIM_CACHE_ROOT=str(OUT/'sim_cache'))
    s=launch(['bash',str(ROOT/'scripts/run_crossing_panorama_isaac.sh'),str(ROOT/'scripts/check_recovery_isaac.py'),str(OUT/'isaac_check.json')],simenv,'isaac.log')
    update(phase='isaac_loading',isaac_pid=s.pid)
    assert s.wait(timeout=900)==0,'Isaac asset load failed'
    assert (OUT/'isaac_check.json').exists()
    update(phase='deployment_checks_complete',navigation_executed=False,checkpoint_restored=False)
except BaseException as e:
    update(phase='failed',error=type(e).__name__+': '+str(e))
finally:
    results=[cleanup(p) for p in reversed(children)]
    for h in locks:h.close()
    write(OUT/'cleanup.json',dict(results=results,gpu=gpu_snapshot()))
    update(finished_at=now(),gpu_released=all(not r['remaining'] for r in results))
    notice='\n\n后台部署结果：'+json.dumps(state,ensure_ascii=False)+'。仅指令生成和环境加载检查；七例物理恢复尚未执行。\n'
    for path in [EXP/'README.md',ROOT/'docs/STATUS.md',ROOT/'experiments/README.md']:
        with path.open('a') as f:f.write(notice)
