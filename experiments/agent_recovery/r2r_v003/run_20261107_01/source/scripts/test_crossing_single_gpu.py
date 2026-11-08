"""Bounded, offline single-GPU deployment smoke; always clean up owned service PIDs."""
import argparse
import base64
from collections import deque
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.crossing_checkpoint import (CheckpointTracker, action_name, build_messages,
                                      canonical_hash, response_schema, validate_response)


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def gpu_snapshot():
    raw = subprocess.check_output(['nvidia-smi', '--query-gpu=index,memory.total,memory.used,memory.free,utilization.gpu',
                                   '--format=csv,noheader,nounits'], text=True)
    rows = [dict(zip(('index','total_mib','used_mib','free_mib','utilization'),
                    map(int, row.split(',')))) for row in raw.splitlines()]
    apps = subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory,process_name',
                                    '--format=csv,noheader,nounits'],text=True)
    return dict(time=now(), gpus=rows, compute_apps=apps)


def process(pid):
    try:
        p=Path('/proc')/str(pid)
        fields=(p/'stat').read_text().rsplit(')',1)[1].split()
        return dict(pid=pid, ppid=int(fields[1]), session=int(fields[3]), start=fields[19],
                    state=fields[0], cmdline=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace'),
                    cwd=os.readlink(p/'cwd'))
    except (OSError,ValueError):
        return None


def owned_processes(server):
    found={}
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            row=process(int(p.name))
            if row and row['session']==server.pid:
                found[row['pid']]=row
    return found


def prepare_requests(out):
    import cv2
    cv2.setNumThreads(1)
    original=ROOT/'outputs/crossing_checkpoint/seed2_v1_20261103'
    eid='kujiale_0036_10_0'
    source=json.loads((original/'inputs.json').read_text())[eid]
    records=[json.loads(line) for line in (original/'runs/qwen27_fp8_dev_v1_nothinking/cases'/eid/'predictions.jsonl').read_text().splitlines()]
    eligible=[r['frame'] for r in records if len(r['image_frames'])==8]
    selected=[eligible[0],eligible[len(eligible)//2],eligible[-1]]
    cached={r['frame']:r for r in records}
    cap=cv2.VideoCapture(source['video'])
    if not cap.isOpened() or (int(cap.get(3)),int(cap.get(4)))!=(960,640):
        raise RuntimeError('Unexpected original video layout')
    tracker=CheckpointTracker();images=deque(maxlen=8);executed=[];jobs=[]
    try:
        for obs in source['observations']:
            ok,composite=cap.read()
            if not ok:raise RuntimeError('Video truncated')
            frame=obs['frame']
            if obs['terminal']:continue
            if not obs['rgb_reused']:
                ok,encoded=cv2.imencode('.png',composite[:480,:640].copy())
                if not ok:raise RuntimeError('RGB encoding failed')
                raw=encoded.tobytes()
                images.append(dict(frame=frame,sha256=hashlib.sha256(raw).hexdigest(),
                                   data_url='data:image/png;base64,'+base64.b64encode(raw).decode()))
                if frame in selected:
                    ids=[im['frame'] for im in images]
                    seed=int(hashlib.sha256(f'{eid}:{frame}:20261103'.encode()).hexdigest()[:8],16)&0x7fffffff
                    payload=dict(model='crossing-qwen27b',messages=build_messages(list(images),executed[-32:],tracker.prompt_memory()),
                                 temperature=0.0,seed=seed,max_tokens=8192,
                                 response_format={'type':'json_schema','json_schema':{'name':'crossing_observation',
                                     'strict':True,'schema':response_schema(ids)}},chat_template_kwargs={'enable_thinking':False})
                    request_hash=canonical_hash(payload)
                    if request_hash!=cached[frame]['request_sha256']:
                        raise RuntimeError(f'Reconstructed request differs from v001 at {frame}')
                    name=f'request_{frame:04d}.json';write(out/name,payload)
                    jobs.append(dict(episode_id=eid,frame=frame,image_frames=ids,seed=seed,request=name,
                                     request_sha256=request_hash,matches_original_request=True))
                tracker.update(frame,cached[frame]['prediction'])
            executed.append(dict(index=frame,name=action_name(obs['action'])))
    finally:
        cap.release()
    if len(jobs)!=3:raise RuntimeError('Expected three distinct eight-image requests')
    return jobs


def finish_fixed_batch(campaign, service_summary):
    """Record final scores/report and release evidence after this service has exited."""
    registration=json.loads((campaign/'registration.json').read_text())
    tag=registration['tag'];run=campaign/'runs'/tag
    scores=json.loads((run/'scores.json').read_text()) if (run/'scores.json').exists() else None
    visualization=json.loads((run/'visualization.json').read_text()) if (run/'visualization.json').exists() else None
    complete=(service_summary['outcome']=='passed' and scores and scores['summary']['complete']
              and visualization and not service_summary['remaining_owned_processes'])
    final=dict(status='complete' if complete else 'failed',tag=tag,finished_at=now(),
               expected_model_calls=registration['expected_model_calls'],
               scores=scores['summary'] if scores else None,visualization=visualization,
               service_summary=str(campaign/'service_01/summary.json'),
               gpu_cleanup_complete=not service_summary['remaining_owned_processes'],
               gpu_after_cleanup=service_summary['gpu_after_cleanup'])
    write(campaign/'final_summary.json',final)
    label='已完成' if complete else '失败/未完成'
    count=len(registration.get('development',[]))+len(registration.get('validation',[]));stride=registration.get('inference_stride',1)
    detail=f"{label}；{count}条固定离线样本，每{stride}个动作步调用一次。"
    if scores:
        m=scores['summary']['metrics']['1.0']
        detail+=f" TP {m['tp']} / FP {m['fp']} / FN {m['fn']}。"
    detail+=' GPU已释放。' if final['gpu_cleanup_complete'] else ' GPU清理未完成，需核查。'
    for relative in registration.get('documentation',[]):
        path=(ROOT/relative).resolve()
        if not path.is_relative_to(ROOT):raise ValueError('Documentation outside repository')
        marker=registration.get('documentation_marker','CROSSING_V003_BATCH_STATUS')
        text=path.read_text();begin=f'<!-- {marker}_START -->';end=f'<!-- {marker}_END -->'
        if text.count(begin)!=1 or text.count(end)!=1:continue
        a=text.index(begin)+len(begin);b=text.index(end,a)
        text=text[:a]+'\n'+detail+'\n'+text[b:]
        tmp=path.with_suffix(path.suffix+'.batch.tmp');tmp.write_text(text);tmp.replace(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--gpu',type=int,default=0)
    parser.add_argument('--campaign',type=Path,help='After smoke, serve evidence-reviewed sequential jobs for at most eight hours')
    parser.add_argument('--finish-when-queue-empty',action='store_true',help='Finish this fixed batch and release the service without waiting for new jobs')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();server=None;server_identity=None;monitor=None;stop_monitor=threading.Event()
    known={};samples=[];results=[];locks=[];cleanup=[]
    status=dict(phase='preparing',started_at=now(),supervisor_pid=os.getpid(),gpu=args.gpu)
    write(out/'status.json',status)
    def phase(name,**values):
        status.update(phase=name,updated_at=now(),**values);write(out/'status.json',status)
        print(json.dumps(status,ensure_ascii=False),flush=True)
    def terminate(signum,frame):
        raise KeyboardInterrupt(f'Signal {signum}')
    signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)
    try:
        jobs=prepare_requests(out)
        (out/'source').mkdir()
        hashes={}
        for relative in ('scripts/test_crossing_single_gpu.py','core/crossing_checkpoint.py','scripts/replay_crossing_checkpoint.py'):
            content=(ROOT/relative).read_bytes();(out/'source'/Path(relative).name).write_bytes(content)
            hashes[relative]=hashlib.sha256(content).hexdigest()
        diff=subprocess.check_output(['git','diff','--binary'],cwd=ROOT)
        (out/'source/worktree.patch').write_bytes(diff)
        (out/'source/git_status.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True))
        for name in (f'peng_vlnverse_gpu_{args.gpu}.lock',f'vln_2026_gpu_{args.gpu}.lock'):
            f=open(Path('/tmp')/name,'a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
        admissions=[]
        for i in range(2):
            snap=gpu_snapshot();admissions.append(snap)
            row=next(r for r in snap['gpus'] if r['index']==args.gpu)
            if row['free_mib']<row['total_mib']*.80+3072 or row['utilization']>10:
                raise RuntimeError('GPU resources changed; shared admission rejected: '+str(row))
            available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))
            if available<64*1024**2:raise RuntimeError('Less than 64 GiB host memory available')
            if i==0:time.sleep(5)
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        base=f'http://127.0.0.1:{port}/v1'
        model=Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/Qwen3.8-27B-FP8')
        python=ROOT/'.runtime/crossing_vllm27/bin/python'
        command=[str(python),'-B','-m','vllm.entrypoints.openai.api_server','--model',str(model),
                 '--served-model-name','crossing-qwen27b','--host','127.0.0.1','--port',str(port),
                 '--dtype','bfloat16','--tensor-parallel-size','1','--cpu-offload-gb','0',
                 '--gpu-memory-utilization','0.80','--max-model-len','32768','--max-num-seqs','1',
                 '--max-num-batched-tokens','4096','--limit-mm-per-prompt','{"image":8,"video":0}',
                 '--mm-processor-kwargs','{"max_pixels":307200}','--enforce-eager',
                 '--no-enable-log-requests','--seed','20261103','--reasoning-parser','qwen3']
        cache=ROOT/'.runtime/crossing_vlm'
        env={k:v for k,v in os.environ.items() if 'proxy' not in k.lower()}
        env.update(CUDA_VISIBLE_DEVICES=str(args.gpu),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
                   HF_DATASETS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',VLLM_NO_USAGE_STATS='1',DO_NOT_TRACK='1',
                   TOKENIZERS_PARALLELISM='false',PYTHONDONTWRITEBYTECODE='1',
                   OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',
                   HF_HOME=str(cache/'huggingface'),XDG_CACHE_HOME=str(cache/'cache'),
                   VLLM_CACHE_ROOT=str(cache/'vllm'),TORCHINDUCTOR_CACHE_DIR=str(cache/'torchinductor'),
                   TRITON_CACHE_DIR=str(cache/'triton'))
        manifest=dict(created_at=now(),purpose='Single GPU, single concurrent request deployment validation; no method score',
                      git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                      source_sha256=hashes,command=command,base_url=base,admission=admissions,jobs=jobs,
                      shared_gpu_authorization='User authorized this run; current resource checks apply and other processes are not modified',
                      protocol=dict(tensor_parallel=1,max_num_seqs=1,memory_utilization=.8,max_model_len=32768,
                                    input_images=8,rgb_size=[640,480],max_output_tokens=8192,thinking=False))
        write(out/'manifest.json',manifest)
        with (out/'server.log').open('w') as log:
            server=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        server_identity=process(server.pid);known[server.pid]=server_identity
        write(out/'server_process.json',server_identity)
        phase('loading',server_pid=server.pid,base_url=base,requests=jobs)
        def sample():
            with (out/'resources.jsonl').open('a') as f:
                while not stop_monitor.is_set():
                    try:
                        snap=gpu_snapshot();samples.append(snap);f.write(json.dumps(snap)+'\n');f.flush()
                        known.update(owned_processes(server))
                    except Exception as error:
                        f.write(json.dumps({'sampling_error':str(error),'time':now()})+'\n');f.flush()
                    stop_monitor.wait(2)
        monitor=threading.Thread(target=sample,daemon=True);monitor.start()
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        loading_start=time.monotonic()
        while True:
            if server.poll() is not None:raise RuntimeError(f'Model server exited: {server.returncode}')
            try:
                with opener.open(base+'/models',timeout=2) as response:models=json.load(response)
                if any(m['id']=='crossing-qwen27b' for m in models['data']):break
            except (OSError,ValueError,KeyError):pass
            if time.monotonic()-loading_start>2700:raise TimeoutError('Model readiness exceeded 2700 seconds')
            time.sleep(2)
        phase('ready',startup_seconds=time.monotonic()-loading_start)
        for job in jobs:
            phase('request',current_frame=job['frame'],completed_requests=len(results))
            payload=(out/job['request']).read_bytes()
            request=urllib.request.Request(base+'/chat/completions',data=payload,headers={'Content-Type':'application/json'})
            begin=time.monotonic()
            with opener.open(request,timeout=600) as response:reply=json.load(response)
            elapsed=time.monotonic()-begin
            write(out/f"response_{job['frame']:04d}.json",reply)
            choice=reply['choices'][0]
            if choice['finish_reason']!='stop':raise RuntimeError('Incomplete model generation')
            content=choice['message']['content'].strip()
            if content.startswith('```'):content=content.split('\n',1)[1].rsplit('```',1)[0].strip()
            prediction=validate_response(json.loads(content),job['image_frames'])
            results.append(dict(**job,elapsed_seconds=elapsed,usage=reply.get('usage'),prediction=prediction,schema_valid=True))
            write(out/'responses_summary.json',results)
        phase('passed',completed_requests=len(results))
        if args.campaign:
            campaign=args.campaign.resolve()
            write(out/'smoke_result.json',dict(passed=True,results=results,finished_at=now()))
            write(out/'service.json',dict(phase='ready',base_url=base,served_model='crossing-qwen27b',
                  model_path=str(model),dtype='bfloat16',cpu_offload_gb=0,command=command,
                  backend='vllm',quantization_override=None))
            phase('campaign',campaign=str(campaign))
            queue=campaign/'queue';queue.mkdir(exist_ok=True)
            deadline=time.monotonic()+28800
            write(campaign/'session.json',dict(service=str(out),started_at=now(),deadline_epoch=time.time()+28800))
            while not (campaign/'session_complete.json').exists():
                if server.poll() is not None:raise RuntimeError('Campaign model service exited')
                if time.monotonic()>=deadline:raise TimeoutError('Eight-hour campaign limit reached')
                pending=[p for p in sorted(queue.glob('*.json')) if not p.with_suffix('.done').exists()]
                if not pending:
                    time.sleep(2);continue
                job_path=pending[0];job=json.loads(job_path.read_text())
                if job['split']=='development' and job['tag']!='baseline' and not job.get('evidence_review'):
                    raise ValueError('Every changed version needs an evidence review')
                frozen=Path(job['source']).resolve()
                if not frozen.is_relative_to(campaign):raise ValueError('Source must belong to this campaign')
                cmd=[sys.executable,'-B',str(frozen/'scripts/replay_crossing_checkpoint.py'),'run',
                     '--output',str(campaign),'--tag',job['tag'],'--split',job['split'],
                     '--service',str(out),'--workers','1','--max-tokens','8192']
                if job.get('inference_stride',1)!=1:
                    cmd.extend(['--inference-stride',str(job['inference_stride'])])
                phase('campaign_job',tag=job['tag'],split=job['split'])
                with (campaign/(job['tag']+'.log')).open('a') as job_log:
                    child=subprocess.Popen(cmd,cwd=ROOT,stdout=job_log,stderr=subprocess.STDOUT,start_new_session=True)
                    try:
                        while child.poll() is None:
                            if time.monotonic()>=deadline:raise TimeoutError('Eight-hour campaign limit reached')
                            if server.poll() is not None:raise RuntimeError('Model service exited during replay')
                            for state_path in (campaign/'runs'/job['tag']/'cases').glob('*/status.json'):
                                case_state=json.loads(state_path.read_text())
                                if case_state.get('phase')=='failed':
                                    raise RuntimeError('Replay case failed: '+str(case_state))
                            time.sleep(2)
                    finally:
                        if child.poll() is None:
                            # This process group was created above for this single replay job.
                            os.killpg(child.pid,signal.SIGTERM)
                            try:child.wait(timeout=15)
                            except subprocess.TimeoutExpired:
                                os.killpg(child.pid,signal.SIGKILL);child.wait()
                if child.returncode:raise RuntimeError('Replay job failed: '+job['tag'])
                subprocess.run([sys.executable,'-B',str(ROOT/'scripts/analyze_crossing_checkpoint.py'),
                                '--output',str(campaign),'--tag',job['tag']],check=True)
                export_cmd=[str(ROOT/'backbone/streamvln/.venv/bin/python'),'-B',
                            str(ROOT/'scripts/export_crossing_iteration.py'),
                            '--output',str(campaign),'--tag',job['tag']]
                if job.get('export_destination'):
                    destination=(campaign/job['export_destination']).resolve()
                    if not destination.is_relative_to(campaign):
                        raise ValueError('Export destination must belong to this campaign')
                    export_cmd.extend(['--destination',str(destination)])
                subprocess.run(export_cmd,check=True,
                               timeout=max(1,min(600,deadline-time.monotonic())))
                write(job_path.with_suffix('.done'),dict(returncode=child.returncode,finished_at=now(),
                      visualization=str(campaign/'runs'/job['tag']/'visualization.json')))
                phase('awaiting_evidence_review',tag=job['tag'])
                if args.finish_when_queue_empty and all(p.with_suffix('.done').exists() for p in queue.glob('*.json')):
                    write(campaign/'session_complete.json',dict(reason='authorized_fixed_batch_finished',finished_at=now()))
                    break
            phase('passed',campaign_complete=True)
    except BaseException as error:
        (out/'error.txt').write_text(traceback.format_exc())
        phase('failed',error=f'{type(error).__name__}: {error}',completed_requests=len(results))
    finally:
        outcome=status['phase'];stop_monitor.set()
        if monitor:monitor.join(timeout=5)
        if server:
            known.update(owned_processes(server))
            write(out/'owned_processes_before_cleanup.json',list(known.values()))
            # Only the exact child we started and its private-session descendants are eligible.
            def send(pid,sig):
                expected=known.get(pid);current=process(pid)
                if expected and current and current['start']==expected['start'] and current['session']==server.pid and current['state']!='Z':
                    os.kill(pid,sig);cleanup.append(dict(pid=pid,signal=sig,time=now(),identity=current))
            if server.poll() is None:
                send(server.pid,signal.SIGTERM)
                try:server.wait(timeout=30)
                except subprocess.TimeoutExpired:pass
            known.update(owned_processes(server))
            for pid in sorted(known,reverse=True):send(pid,signal.SIGTERM)
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                if not any((p:=process(pid)) and p['start']==row['start'] and p['state']!='Z' for pid,row in known.items() if row):break
                time.sleep(1)
            for pid in sorted(known,reverse=True):send(pid,signal.SIGKILL)
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:pass
        final_gpu=gpu_snapshot();write(out/'gpu_after_cleanup.json',final_gpu)
        remaining=[p for pid,row in known.items() if row and (p:=process(pid)) and p['start']==row['start'] and p['state']!='Z']
        summary=dict(outcome=outcome,completed_requests=len(results),requests=results,
                     elapsed_seconds=time.monotonic()-started,finished_at=now(),cleanup_signals=cleanup,
                     remaining_owned_processes=remaining,gpu_after_cleanup=final_gpu,
                     peak_total_gpu_used_mib=max((r['used_mib'] for s in samples for r in s['gpus'] if r['index']==args.gpu),default=None),
                     minimum_gpu_free_mib=min((r['free_mib'] for s in samples for r in s['gpus'] if r['index']==args.gpu),default=None))
        write(out/'summary.json',summary)
        phase(outcome,cleanup_complete=not remaining,finished_at=now())
        if args.campaign and args.finish_when_queue_empty:
            try:finish_fixed_batch(args.campaign.resolve(),summary)
            except Exception as error:
                write(out/'final_record_error.json',dict(error=str(error),time=now()))
        for f in locks:f.close()
    return 0 if status['phase']=='passed' and not remaining else 1


if __name__=='__main__':
    sys.exit(main())
