"""Run the human dataset with the unchanged no-panorama v001 calls; never export HTML."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from core.agent_route_choice import build_messages, digest, file_hash, now, payload, read, write
from prepare_human_route_choice import verify
from run_agent_route_choice import run_case, wait_local
from run_crossing_local_batch import cleanup
from serve_crossing_vlm import gpu_rows, idle
from test_crossing_single_gpu import gpu_snapshot, process


def admitted(row, total_mib, config, allow_shared):
    if idle(row): return True
    return bool(allow_shared and row['utilization'] <= 10 and
                row['free_mib'] >= int(total_mib * config['gpu_memory_utilization']) + 4096)


def start_local(config, gpu, out, locks, allow_shared=False):
    for prefix in ('peng_vlnverse_gpu_', 'vln_2026_gpu_'):
        handle = (Path('/tmp') / (prefix + str(gpu) + '.lock')).open('a')
        locks.append(handle); fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    admissions = []
    for index in range(3):
        snapshot = gpu_snapshot(); rows = gpu_rows()
        row = next(r for r in rows if r['index'] == gpu)
        total = next(r['total_mib'] for r in snapshot['gpus'] if r['index'] == gpu)
        available = int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))
        admissions.append(dict(snapshot=snapshot, rows=rows, available_host_kib=available))
        write(out / 'gpu_admission.json', dict(allow_shared_gpu=allow_shared, checks=admissions))
        if not admitted(row, total, config, allow_shared): raise RuntimeError('GPU admission failed; other processes are preserved')
        if available < config['minimum_host_memory_gib'] * 1024 ** 2: raise RuntimeError('Insufficient host memory')
        if index < 2: time.sleep(5)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    command = [str(ROOT/config['python']), '-B', '-m', 'vllm.entrypoints.openai.api_server',
        '--model', config['model_path'], '--served-model-name', config['model'],
        '--host', '127.0.0.1', '--port', str(port), '--dtype', 'bfloat16',
        '--tensor-parallel-size', '1', '--cpu-offload-gb', '0',
        '--gpu-memory-utilization', str(config['gpu_memory_utilization']),
        '--max-model-len', str(config['max_model_len']), '--max-num-seqs', '1',
        '--max-num-batched-tokens', '4096', '--limit-mm-per-prompt', '{"image":8,"video":0}',
        '--mm-processor-kwargs', '{"max_pixels":307200}', '--enforce-eager',
        '--no-enable-log-requests', '--seed', str(config['seed']), '--reasoning-parser', config['reasoning_parser']]
    env = {k:v for k,v in os.environ.items() if 'proxy' not in k.lower() and not any(t in k.upper() for t in ('API_KEY','TOKEN','SECRET'))}
    cache = ROOT / '.runtime/crossing_vlm'
    env.update(CUDA_VISIBLE_DEVICES=str(gpu), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1',
        HF_HUB_DISABLE_TELEMETRY='1', VLLM_NO_USAGE_STATS='1', TOKENIZERS_PARALLELISM='false', PYTHONDONTWRITEBYTECODE='1',
        OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4', HF_HOME=str(cache/'huggingface'),
        XDG_CACHE_HOME=str(cache/'cache'), VLLM_CACHE_ROOT=str(cache/'vllm'),
        TORCHINDUCTOR_CACHE_DIR=str(cache/'torchinductor'), TRITON_CACHE_DIR=str(cache/'triton'))
    write(out / 'launch.json', dict(command=command, gpu=gpu, allow_shared_gpu=allow_shared, created_at=now()))
    with (out/'server.log').open('x') as log:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    return child, 'http://127.0.0.1:%d/v1' % port


def request_audit(cases, prepared, out, config):
    checks = []
    for case in cases:
        folder = out/'cases'/case['sample_id']
        for stage, prompt in [(1,'01_inventory_en.txt'),(2,'02_choose_en.txt')]:
            path = folder/('call%d_request.json' % stage)
            if not path.exists(): continue
            inventory = read(folder/'call1_answer.json') if stage == 2 else None
            wire = payload(build_messages(case, prepared, stage, (prepared/'prompts'/prompt).read_text(), inventory),
                           config, case['sample_id'], stage)
            saved = read(path)
            if saved['request_sha256'] != digest(wire): raise ValueError('Request audit mismatch')
            if saved['inventory_sha256'] != (digest(inventory) if inventory is not None else None):
                raise ValueError('First answer was not passed unchanged')
            checks.append(dict(sample_id=case['sample_id'], call=stage, passed=True, request_sha256=digest(wire)))
    write(out/'request_audit.json', dict(passed=True, audited_requests=len(checks), checks=checks, model_calls_added=0))
    return len(checks)


def summarize(cases, out):
    rows = []
    for case in cases:
        folder = out/'cases'/case['sample_id']
        state = read(folder/'status.json') if (folder/'status.json').exists() else dict(phase='not_attempted')
        row = dict(sample_id=case['sample_id'], phase=state['phase'],
                   responses=sum((folder/('call%d_response.json'%i)).exists() for i in (1,2)),
                   valid_calls=sum((folder/('call%d_answer.json'%i)).exists() for i in (1,2)))
        if (folder/'call2_response.json').exists():
            raw = read(folder/'call2_response.json')
            try:
                answer = json.loads(raw['content'])
                row.update(raw_decision=answer.get('status'), raw_selected_branch_id=answer.get('selected_branch_id'))
            except (ValueError, AttributeError): row['raw_decision'] = 'unparseable'
        if state.get('error'): row['error'] = state['error']
        rows.append(row)
    logs = [json.loads(line) for p in out.glob('cases/*/call*_transport.jsonl') for line in p.read_text().splitlines() if line]
    return dict(expected_samples=len(cases), expected_max_calls=2*len(cases),
                processed_samples=sum(r['phase']!='not_attempted' for r in rows),
                protocol_valid_samples=sum(r['valid_calls']==2 for r in rows),
                saved_responses=sum(r['responses'] for r in rows),
                samples_with_two_responses=sum(r['responses']==2 for r in rows),
                raw_selected=sum(r.get('raw_decision')=='selected' for r in rows),
                raw_insufficient=sum(r.get('raw_decision')=='insufficient_evidence' for r in rows),
                network_attempts=len(logs), network_errors=sum(bool(l['error']) for l in logs),
                semantic_accuracy='pending_review', html_generated=False, cases=rows)


def record_completion(registration, out, state):
    paths = registration['documentation']
    write(ROOT/registration['experiment_dir']/'completion.json', dict(state, output=str(out.relative_to(ROOT))))
    notice = ('\n\n%s 人工标注无全景选路自动收尾：状态 `%s`，处理 %s/34 个点，保存 %s/68 次回答，'
              '协议有效 %s/34；语义正确率待复核。本轮按用户要求不生成HTML，GPU释放 %s。结果 `%s`。\n') % (
        now(), state['phase'], state.get('processed_samples',0), state.get('saved_responses',0),
        state.get('protocol_valid_samples',0), state.get('gpu_released',False), out.relative_to(ROOT))
    for name in paths:
        fd = os.open(ROOT/name, os.O_WRONLY|os.O_APPEND)
        try: os.write(fd, notice.encode())
        finally: os.close(fd)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--gpu',type=int,required=True);p.add_argument('--allow-shared-gpu',action='store_true')
    p.add_argument('--registration',type=Path,required=True)
    a=p.parse_args();prepared=a.prepared.resolve();out=a.output.resolve()
    cases=verify(prepared);config=read(prepared/'model.json');registration=read(a.registration)
    out.mkdir(parents=True,exist_ok=False)
    write(out/'manifest.json',dict(prepared=str(prepared),prepared_manifest_sha256=file_hash(prepared/'manifest.json'),
        registration=registration,model_config=config,sample_order=[c['sample_id'] for c in cases],started_at=now()))
    state=dict(phase='starting',supervisor_pid=os.getpid(),started_at=now(),gpu=a.gpu,
               expected_samples=len(cases),expected_max_calls=2*len(cases),html_generated=False,semantic_accuracy='pending_review')
    def update(**kw):
        state.update(kw,updated_at=now());write(out/'status.json',state);print(json.dumps(state),flush=True)
    def stop(*_): raise KeyboardInterrupt('Supervisor termination requested')
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    child=None;locks=[];error=None;completed=False
    update()
    try:
        update(phase='admission')
        child,base=start_local(config,a.gpu,out,locks,a.allow_shared_gpu)
        write(out/'service.json',dict(process=process(child.pid),base_url=base,gpu=a.gpu))
        update(phase='loading',server_pid=child.pid,base_url=base)
        wait_local(child,base,config['model']);update(phase='running')
        deadline=time.monotonic()+config['batch_deadline_seconds']
        for case in cases:
            if child.poll() is not None: raise RuntimeError('Model service exited during inference')
            if time.monotonic()>deadline: raise TimeoutError('Batch deadline exceeded')
            update(current_sample=case['sample_id'])
            try:
                run_case(case,prepared,out,config,base+'/chat/completions',None)
            except Exception as exc:
                write(out/'cases'/case['sample_id']/'status.json',dict(phase='failed',error_type=type(exc).__name__,
                      error=str(exc)[:900],finished_at=now()))
            summary=summarize(cases,out)
            update(**{k:v for k,v in summary.items() if k!='cases'})
            if summary['protocol_valid_samples'] and not (out/'startup_verified.json').exists():
                audited=request_audit(cases,prepared,out,config)
                write(out/'startup_verified.json',dict(at=now(),sample_id=case['sample_id'],
                    model_ready=True,valid_two_call_sample=True,audited_requests=audited,
                    remaining_samples=len(cases)-summary['processed_samples'],html_disabled=True))
        completed=True
    except BaseException as exc:
        error=type(exc).__name__+': '+str(exc)
        update(phase='interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed',error=error)
    finally:
        signal.signal(signal.SIGINT,signal.SIG_IGN);signal.signal(signal.SIGTERM,signal.SIG_IGN)
        try:
            clean=cleanup(child) if child is not None else dict(remaining=[],signals=[])
            write(out/'cleanup.json',dict(server=clean,gpu_after=gpu_snapshot()))
            update(gpu_released=not clean['remaining'])
        finally:
            for handle in locks: handle.close()
    summary=summarize(cases,out)
    try: summary['audited_requests']=request_audit(cases,prepared,out,config)
    except Exception as exc: error=(error+'; ' if error else '')+'audit: '+str(exc)
    phase=('complete_pending_semantic_review' if summary['protocol_valid_samples']==len(cases)
           else 'complete_with_invalid_samples') if completed and error is None else 'failed_or_interrupted'
    if not state.get('gpu_released',False): phase='cleanup_failed'
    summary.update(phase=phase,error=error,finished_at=now(),gpu_released=state.get('gpu_released',False))
    write(out/'summary.json',summary);update(**{k:v for k,v in summary.items() if k!='cases'})
    write(out/'review_template.json',dict(status='pending_semantic_review',cases=[dict(sample_id=c['sample_id'],reviewed=False,
         inventory_sha256=file_hash(out/'cases'/c['sample_id']/'call1_response.json') if (out/'cases'/c['sample_id']/'call1_response.json').exists() else None,
         choice_sha256=file_hash(out/'cases'/c['sample_id']/'call2_response.json') if (out/'cases'/c['sample_id']/'call2_response.json').exists() else None,
         correct_branch=None,wrong_branch=None,notes='') for c in cases]))
    record_completion(registration,out,state)
    return 0 if completed and error is None and state.get('gpu_released') else 1


if __name__=='__main__': sys.exit(main())
