"""Single-GPU fine val_unseen evaluator. Full episodes; explicit owned-process cleanup."""
import argparse,fcntl,gzip,json,os,re,signal,subprocess,sys,time,urllib.request
from pathlib import Path
RUNNER=Path(__file__).resolve().parent
ROOT=RUNNER.parent/"upstream"
PROJECT=RUNNER.parents[2]
import sys
sys.path.insert(0,str(PROJECT))
from core.paths import output_root, model_python, resource_root, model_environment, simulation_python, isaac_root
from core.seeding import SEED_SCHEME
from core.vlnverse_runtime import RuntimeFailure, OOMLogMonitor, failure_record, wait_for_model_ready, ExistingModelService
from core.vlnverse_reproduction import digest_json, select_complete_scenes, verify_resume
from core.vlnverse_review import review_settings
from scripts.evaluate import check_gpu
RESOURCE=resource_root()
ASSETS=RESOURCE/'assets/VLNVerse'

def atomic_json(path,data):
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)); temp.replace(path)

def cleanup(process):
    if getattr(process, 'retained', False): return
    if process is None or process.poll() is not None: return
    try:
        os.killpg(process.pid,signal.SIGTERM); process.wait(timeout=20)
    except ProcessLookupError: pass
    except subprocess.TimeoutExpired:
        os.killpg(process.pid,signal.SIGKILL); process.wait(timeout=10)


def check_serial_chunk(settings, returncode, completed, before):
    if settings and ((Path(settings['output_dir'])/'halt.json').exists()
                     or returncode not in (0, None) or completed <= before):
        raise RuntimeError('Codex serial run interrupted; automatic episode/chunk retry is disabled. Inspect halt.json and evaluator.log.')

def write_config(path,method,port,task,dataset,mode,review=None,jev_live=None,codex_serial=None):
    model='streamvln_rgb' if method=='StreamVLN' else 'janusvln'
    ckpt='StreamVLN_R2R_v1_3' if method=='StreamVLN' else 'JanusVLN_Extra'
    # Official defaults: 25k physics ticks; the official fine flash configs use 500 ticks.
    max_step=25000 if mode=='physical' else 500
    path.write_text(f"""from vlnverse.configs.agent import AgentCfg
from vlnverse.configs.evaluator import EnvCfg, EvalCfg, EvalDatasetCfg, SceneCfg, TaskCfg
resource={str(RESOURCE)!r}
eval_cfg=EvalCfg(
 agent=AgentCfg(server_host='127.0.0.1',server_port={port},model_name={model!r},ckpt_path=resource+'/models/{ckpt}',model_settings={{}}),
 env=EnvCfg(env_type='vln_pe',env_settings={{'headless':True,'use_fabric':False}}),
 task=TaskCfg(task_name={task!r},task_settings={{'env_num':1,'proc_num':1,'use_distributed':False,'max_step':{max_step},'warm_up_step':500}},scene=SceneCfg(scene_type='kujiale',scene_data_dir=resource+'/assets/VLNVerse/scenes'),robot_name='h1',robot_flash={mode=='flash'},flash_collision=False,robot_usd_path=resource+'/assets/VLNVerse/Embodiments/vln-pe/h1/h1_vln_pointcloud.usd',camera_resolution=[640,480],camera_prim_path='torso_link/h1_pano_camera_0'),
 dataset=EvalDatasetCfg(dataset_type='kujiale',dataset_settings={{'base_data_dir':{str(dataset)!r},'split_data_types':['val_unseen'],'filter_stairs':False}}),
    eval_settings={{'save_to_json':True,'vis_output':False,'review_output':{review!r},'jev_live_output':{jev_live!r},'codex_serial':{codex_serial!r}}},
)
""")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--method',choices=['StreamVLN','JanusVLN'],required=True)
    ap.add_argument('--gpu',type=int,required=True,help='Model GPU')
    ap.add_argument('--sim-gpu',type=int,help='Simulator GPU; defaults to model GPU')
    ap.add_argument('--mode',choices=['physical','flash'],default='physical')
    ap.add_argument('--limit-episodes',type=int,default=0,help='0 = all 825; >0 is a validation subset')
    ap.add_argument('--episode-ids',nargs='+',help='Explicit validation subset; cannot combine with limit-episodes')
    ap.add_argument('--resume',help='Run ID printed by a previous run')
    ap.add_argument('--run-id',help='Explicit new run ID')
    ap.add_argument('--seed',type=int,help='Run seed; stable per-episode seeds are derived from it')
    ap.add_argument('--scenes',nargs='+',help='Run every episode of these scenes')
    ap.add_argument('--allow-shared-gpu',action='store_true')
    ap.add_argument('--preflight-only',action='store_true')
    ap.add_argument('--jev-live-output',type=Path,help='Causal JEV v004 scoring output directory')
    ap.add_argument('--codex-shadow-output',type=Path,help='Stream native observations to an independent JEV/Codex reviewer')
    ap.add_argument('--codex-serial-output',type=Path,help='Serial live JEV/Codex gate and 180-step GPT takeover to the goal')
    ap.add_argument('--rss-budget-mib',type=int,default=24000)
    ap.add_argument('--model-service-manifest',type=Path,help='Reuse and retain the registered model for this GPU/seed')
    a=ap.parse_args()
    if a.codex_serial_output:
        if a.jev_live_output or a.codex_shadow_output:
            ap.error('Codex serial capture cannot be combined with another observer')
        if a.method != 'StreamVLN' or a.mode != 'physical' or a.seed is None:
            ap.error('Codex serial requires StreamVLN, physical mode, and an explicit seed')
        if not os.environ.get('JEV_API_KEY'):
            ap.error('JEV_API_KEY is required for Codex serial navigation')
    codex_serial = dict(output_dir=str(a.codex_serial_output.resolve())) if a.codex_serial_output else None
    if codex_serial and (Path(codex_serial['output_dir'])/'halt.json').exists():
        ap.error('This serial run was halted; preserve it and choose a new output directory')
    if a.jev_live_output and a.codex_shadow_output: ap.error('Choose one live observer')
    if a.limit_episodes < 0: ap.error('limit-episodes must be nonnegative')
    if a.episode_ids and a.limit_episodes: ap.error('Choose episode-ids or limit-episodes')
    if a.scenes and (a.episode_ids or a.limit_episodes): ap.error('Complete scenes cannot be combined with episode limits/IDs')
    if a.run_id and a.resume: ap.error('Choose a new run-id or resume')
    if a.seed is not None and (not 0 <= a.seed < 2**31 or a.method != 'StreamVLN'):
        ap.error('Seeded reproduction currently supports StreamVLN and seeds in [0, 2**31)')
    if a.sim_gpu is None: a.sim_gpu=a.gpu
    existing_model = (ExistingModelService(a.model_service_manifest,a.gpu,a.method,a.seed,PROJECT)
                      if a.model_service_manifest else None)
    method_dir=output_root()/'vlnverse'/a.method.lower()
    run_id=a.resume or a.run_id or ('peng_fine_'+a.method.lower()+'_'+a.mode+'_'+time.strftime('%Y%m%d_%H%M%S'))
    if not re.fullmatch(r'peng_fine_[a-z0-9_]+',run_id): ap.error('Invalid run ID')
    output=method_dir/'results'/run_id
    if a.resume:
        meta=json.loads((output/'run.json').read_text())
        if meta.get('codex_serial') != codex_serial:
            raise RuntimeError('Resume must retain the original Codex serial configuration')
        if meta['method']!=a.method: raise RuntimeError('Resume method mismatch')
        a.mode=meta['mode']; episodes=meta['episode_ids']; dataset=Path(meta['dataset'])
        with gzip.open(dataset/'val_unseen/val_unseen.json.gz','rt') as f: selected=json.load(f)['episodes']
        verify_resume(meta, selected, a.seed, a.scenes)
        a.seed=meta.get('seed')
        a.scenes=meta.get('scenes') if meta.get('complete_scenes') else None
    else:
        with gzip.open(ASSETS/'data/raw_data/final_splits/fine_val_unseen.json.gz','rt') as f: selected=json.load(f)['episodes']
        if a.scenes:
            selected=select_complete_scenes(selected,a.scenes)
        elif a.episode_ids:
            requested=set(a.episode_ids)
            selected=[e for e in selected if e['episode_id'] in requested]
            if {e['episode_id'] for e in selected}!=requested: raise RuntimeError('Unknown validation episode ID')
        elif a.limit_episodes: selected=selected[:a.limit_episodes]
        if not selected: raise RuntimeError('Empty dataset')
        episodes=[e['episode_id'] for e in selected]
        dataset=output/'dataset/fine'
    if a.resume and (output/'result.json').exists():
        done=json.loads((output/'result.json').read_text())
        if done.get('status')=='complete' and done['official_result']['val_unseen']['Count']==len(episodes):
            print(json.dumps({'status':'already_complete','result':str(output/'result.json'),'episodes':len(episodes)}),flush=True)
            return
    review=review_settings(output_root(),a.seed,a.method)
    if codex_serial:
        review = None  # SerialHook owns the full RGB/trajectory capture, including GPT actions.
    if a.resume and meta.get('review_visualization') != review:
        raise RuntimeError('Resume visualization policy differs from the original run.')
    python=model_python(a.method.lower())
    runtime=isaac_root()
    sim_python=simulation_python()
    for p in [python,sim_python,runtime/'.peng_extraction_complete',ASSETS/'Embodiments/vln-pe/h1/h1_vln_pointcloud.usd',ASSETS/'Embodiments/vln-pe/h1/policy/move_by_speed/h1_loco_jit_policy.pt']:
        if not p.exists(): raise RuntimeError('Required resource missing: '+str(p))
    needed_scenes=sorted({e['scan'] for e in selected})
    if len(selected)==825:
        ready=json.loads((ASSETS/'fine_val_unseen_assets_ready.json').read_text())
        if ready['episodes']!=825 or ready['scenes']!=needed_scenes: raise RuntimeError('Full scene manifest not ready')
        paths=json.loads((ASSETS/'scene_paths_verified.json').read_text())
        if sorted(paths['entry_scenes_checked'])!=needed_scenes or paths['missing_entry_references']:
            raise RuntimeError('Full scene paths are not verified')
        manifest=json.loads((ASSETS/'fine_val_unseen_scene_manifest.json').read_text())
        for entry in manifest:
            for item in entry['files']:
                p=ASSETS/'scenes'/item['path']
                if not p.is_file() or p.stat().st_size!=item['size']:
                    raise RuntimeError('Missing or conflicting scene file: '+str(p))
    for scene in needed_scenes:
        d=ASSETS/'scenes'/scene
        if not any((d/f).is_file() for f in ['start_result_navigation.usd',scene+'.usda',scene.replace('_fix','')+'.usda']):
            raise RuntimeError('Scene entry missing: '+scene)
    # Selected GPU must have enough free memory; never evict other workloads.
    query=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.free','--format=csv,noheader,nounits'],text=True)
    free={int(line.split(',')[0]):int(line.split(',')[1]) for line in query.strip().splitlines()}
    required=(39000 if a.sim_gpu!=a.gpu else 45000) if a.method=='JanusVLN' else (25000 if a.sim_gpu!=a.gpu else 32000)
    if existing_model: required=12000 if a.sim_gpu==a.gpu else 0
    if free.get(a.gpu,0)<required: raise RuntimeError(f'Model GPU {a.gpu} needs {required} MiB free; for JanusVLN use a separate --sim-gpu')
    if a.sim_gpu!=a.gpu and free.get(a.sim_gpu,0)<12000: raise RuntimeError(f'Simulator GPU {a.sim_gpu} needs 12000 MiB free')
    check_gpu(a.gpu, required, a.allow_shared_gpu)
    if a.sim_gpu != a.gpu: check_gpu(a.sim_gpu, 12000, a.allow_shared_gpu)
    print(json.dumps({'status':'preflight_passed','method':a.method,'mode':a.mode,'episodes':len(episodes),'scenes':len(needed_scenes),'gpu':a.gpu,'sim_gpu':a.sim_gpu}),flush=True)
    if a.preflight_only: return
    jev_live = None
    if a.jev_live_output:
        if not os.environ.get('JEV_API_KEY'):
            raise RuntimeError('JEV_API_KEY is required for --jev-live-output')
        jev_live = {
            'output_dir': str(a.jev_live_output.resolve()),
            'seed': 0 if a.seed is None else a.seed,
            'window_n': 11,
            'max_delay_steps': 5,
            'max_in_flight': 5,
            'attempts': 5,
            'timeout': 120,
            'endpoint': 'https://api.site/v1/systemone',
            'model': 'jev-1.14.0',
            'response_type': 'noul',
            'question_version': 'v004',
        }
    if a.codex_shadow_output:
        jev_live = dict(observer='codex_shadow', output_dir=str(a.codex_shadow_output.resolve()), seed=a.seed)
    if not a.resume:
        output.mkdir(parents=True,exist_ok=False)
        target=dataset/'val_unseen/val_unseen.json.gz'; target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            with gzip.open(target,'rt') as f: assert json.load(f)['episodes']==selected
        else:
            with gzip.open(target,'wt') as f: json.dump({'episodes':selected},f)
        meta={'method':a.method,'mode':a.mode,'run_id':run_id,'dataset':str(dataset),'episode_ids':episodes,'gpu':a.gpu,'sim_gpu':a.sim_gpu,'model_action_cap':None,'physics_tick_cap':25000 if a.mode=='physical' else 500,'camera_resolution':[640,480],'warm_up_step':500}
        meta.update(seed=a.seed,seed_scheme=SEED_SCHEME if a.seed is not None else None,
                    scenes=needed_scenes,complete_scenes=bool(a.scenes),dataset_sha256=digest_json(selected),
                    code_commit=os.environ.get('VLN_CODE_COMMIT'),review_visualization=review,
                    jev_live=jev_live,codex_serial=codex_serial)
        if existing_model:
            meta['retained_model_service'] = dict(manifest=str(a.model_service_manifest.resolve()), **existing_model.entry)
        atomic_json(output/'run.json',meta)
    lock_root=output_root()/'locks'
    lock_root.mkdir(parents=True,exist_ok=True)
    locks=[]
    for path in [*[lock_root/f'peng_vlnverse_gpu_{gpu}.lock' for gpu in sorted({a.gpu,a.sim_gpu})],output/'run.lock']:
        lock=path.open('a'); fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB); locks.append(lock)
    if existing_model:
        lock=(existing_model.output/'consumer.lock').open('a')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB); locks.append(lock)
    # Keep run-specific LMDB and caches inside this project's output directory.
    storage=output/'storage'
    storage.mkdir(parents=True,exist_ok=True)
    sample_target=storage/'samples'; sample_target.mkdir(exist_ok=True)
    sample_link=ROOT/'data/sample_episodes'/run_id
    sample_link.parent.mkdir(parents=True,exist_ok=True)
    if sample_link.is_symlink():
        if sample_link.resolve()!=sample_target.resolve(): raise RuntimeError('Conflicting LMDB symlink')
    elif sample_link.exists(): raise RuntimeError('Preserving existing conflicting LMDB directory')
    else: sample_link.symlink_to(sample_target,target_is_directory=True)
    results_file=ROOT/'logs'/run_id/'kujiale_result.json'
    count=lambda: json.loads(results_file.read_text()).get('val_unseen',{}).get('Count',0) if results_file.exists() else 0
    print('RUN_ID='+run_id+'\nOUTPUT='+str(output),flush=True)
    env=model_environment(a.method.lower(),a.gpu)
    env.pop('PENG_SMOKE_BACKEND',None)
    env.pop('VLN_EVAL_SEED',None)
    if a.seed is not None:
        env.update(VLN_EVAL_SEED=str(a.seed),PYTHONHASHSEED=str(a.seed))
    env.update(CUDA_VISIBLE_DEVICES=str(a.gpu),OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',NO_PROXY='127.0.0.1,localhost',no_proxy='127.0.0.1,localhost',VLN_RSS_BUDGET_MIB=str(a.rss_budget_mib))
    model_ready_timeout=float(os.environ.get('VLN_MODEL_READY_TIMEOUT','900'))
    if a.method=='JanusVLN': env['PYTORCH_CUDA_ALLOC_CONF']='expandable_segments:True'
    eval_env=env.copy()
    eval_env.update(CUDA_VISIBLE_DEVICES=str(a.sim_gpu),VLN_SIM_RENDER_GPU=str(a.sim_gpu))
    tmp_dir=output/'tmp'
    tmp_dir.mkdir(parents=True,exist_ok=True)
    eval_env.update(TMPDIR=str(tmp_dir),TEMP=str(tmp_dir),TMP=str(tmp_dir))
    checkpoint=RESOURCE/'models'/('StreamVLN_R2R_v1_3' if a.method=='StreamVLN' else 'JanusVLN_Extra')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    server=evaluator=None; failures=0
    try:
        for chunk in range(1000):
            if count()==len(episodes): break
            if count()>len(episodes): raise RuntimeError('Unexpected completed episode count')
            check_gpu(a.gpu, required, a.allow_shared_gpu)
            if a.sim_gpu != a.gpu: check_gpu(a.sim_gpu, 12000, a.allow_shared_gpu)
            chunk_name=f'chunk_{time.time_ns()}'
            chunk_storage=storage/'chunks'/chunk_name
            chunk_storage.mkdir(parents=True,exist_ok=False)
            chunk_dir=output/chunk_name
            chunk_dir.symlink_to(chunk_storage,target_is_directory=True)
            start_count=count()
            atomic_json(chunk_dir/'execution.json', {'model_gpu':a.gpu,'sim_gpu':a.sim_gpu,'seed':a.seed,'started_at':time.time(),'model_ready_timeout_seconds':model_ready_timeout})
            if existing_model:
                server=existing_model
                (chunk_dir/'agent.log').symlink_to(existing_model.output/'agent.log')
                (chunk_dir/'ready.json').symlink_to(existing_model.output/'ready.json')
                atomic_json(chunk_dir/'retained_model.json',existing_model.entry)
            else:
                with (chunk_dir/'agent.log').open('w') as log:
                    server=subprocess.Popen([str(python),'-u',str(RUNNER/'service.py'),'--method',a.method,'--checkpoint',str(checkpoint),'--output',str(chunk_dir),'--smoke-steps','0','--compact-trace','--save-rgb','2'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            atomic_json(output/'owned_processes.json',{'agent_pid':server.pid,'gpu':a.gpu,'sim_gpu':a.sim_gpu,'launcher_pid':os.getpid(),'launcher_start_ticks':Path('/proc/self/stat').read_text().split()[21],'chunk':str(chunk_dir)})
            ready=wait_for_model_ready(server,chunk_dir,timeout=model_ready_timeout)
            if existing_model and (ready.get('method')!=a.method or ready.get('run_seed')!=a.seed):
                raise RuntimeError('Existing model readiness configuration mismatch')
            port=ready['port']
            # Explicit post-load reset; official evaluator resets again between episodes.
            req=urllib.request.Request(f'http://127.0.0.1:{port}/agent/{a.method}/reset',data=b'{"reset_index":null}',headers={'Content-Type':'application/json'})
            with opener.open(req,timeout=60) as response: assert json.load(response)['status']=='success'
            config=chunk_dir/'eval_config.py'
            write_config(config,a.method,port,run_id,dataset,a.mode,review,jev_live,codex_serial)
            with (chunk_dir/'evaluator.log').open('w') as log:
                evaluator=subprocess.Popen(['bash',str(RUNNER/'run_eval.sh'),str(config)],env=eval_env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            atomic_json(output/'owned_processes.json',{'agent_pid':server.pid,'evaluator_pid':evaluator.pid,'gpu':a.gpu,'sim_gpu':a.sim_gpu,'launcher_pid':os.getpid(),'launcher_start_ticks':Path('/proc/self/stat').read_text().split()[21],'chunk':str(chunk_dir)})
            print(f'CHUNK_START {chunk_dir.name} completed={start_count}/{len(episodes)}',flush=True)
            model_oom=OOMLogMonitor(chunk_dir/'agent.log','model_inference')
            simulator_oom=OOMLogMonitor(chunk_dir/'evaluator.log','simulator')
            while evaluator.poll() is None:
                model_oom.check()
                simulator_oom.check()
                if server.poll() is not None:
                    raise RuntimeFailure('Model service exited during evaluation','model_inference',chunk_dir/'agent.log',server.returncode)
                newest=max((chunk_dir/'agent.log').stat().st_mtime,(chunk_dir/'evaluator.log').stat().st_mtime)
                if time.time()-newest>900:
                    cleanup(evaluator); break
                time.sleep(5)
            # A process may emit its OOM and exit between two poll iterations.
            model_oom.check()
            simulator_oom.check()
            rc=evaluator.returncode
            cleanup(evaluator); evaluator=None
            cleanup(server); server=None
            completed=count()
            atomic_json(output/'progress.json',{'completed':completed,'expected':len(episodes),'last_chunk':str(chunk_dir),'exit_code':rc})
            print(f'CHUNK_END rc={rc} completed={completed}/{len(episodes)}',flush=True)
            check_serial_chunk(codex_serial,rc,completed,start_count)
            if completed==len(episodes): break
            if completed<=start_count:
                failures+=1
                if failures>=3: raise RuntimeError('Three chunks made no progress; inspect logs and resume after fixing')
            else: failures=0
        if count()!=len(episodes): raise RuntimeError('Evaluation incomplete')
        result=json.loads(results_file.read_text())
        if a.seed is not None:
            subprocess.run([str(sim_python),str(PROJECT/'scripts/export_vlnverse_results.py'),
                            '--run',str(output)],cwd=PROJECT,env=dict(eval_env,CUDA_VISIBLE_DEVICES='',PYTHONPATH=str(PROJECT)),check=True)
        atomic_json(output/'result.json',{'status':'complete','method':a.method,'mode':a.mode,'expected_episodes':len(episodes),'official_result':result,'official_result_path':str(results_file),'run_id':run_id,'model_gpu':a.gpu,'sim_gpu':a.sim_gpu})
        atomic_json(method_dir/'latest_eval.json',{'run_id':run_id,'output':str(output),'result':str(output/'result.json')})
        print(json.dumps({'status':'complete','result':str(output/'result.json')}),flush=True)
    except Exception as error:
        atomic_json(output/'failure.json', dict(failure_record(error), time=time.time(), gpu=a.gpu, sim_gpu=a.sim_gpu))
        raise
    finally:
        cleanup(evaluator); cleanup(server)
        atomic_json(output/'owned_processes.json',{'status':'stopped','gpu':a.gpu,'sim_gpu':a.sim_gpu,
                    'retained_model_pid':existing_model.pid if existing_model else None})

if __name__=='__main__':
    def stop(signum,frame): raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop)
    if signal.getsignal(signal.SIGHUP)!=signal.SIG_IGN: signal.signal(signal.SIGHUP,stop)
    main()
