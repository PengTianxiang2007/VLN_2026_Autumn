"""GLM process pool for frozen no-panorama human inputs; stdin-only credentials."""
import argparse
from collections import deque
import json
import multiprocessing
import os
from pathlib import Path
import random
import resource
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
from core.agent_route_choice import digest, file_hash, now, read, write
from prepare_human_route_choice import verify
from run_agent_route_choice import NoRedirect, read_stream, run_case, cleanup_case_workers
from run_human_route_choice import request_audit, summarize

ENDPOINT = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'


class AccountBlocked(RuntimeError):
    pass


def redact(text, key):
    value = str(text)
    for part in [key] + key.split('.'):
        if part: value = value.replace(part, '[redacted]')
    return value


def terminal_account_error(http_code, provider):
    return http_code in (401, 403) or str(provider.get('code')) == '1113'


def request_model(endpoint, wire, key, config, log_path):
    if endpoint != ENDPOINT or not key:
        raise ValueError('Expected registered GLM endpoint and in-memory credential')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    deadline = time.monotonic() + config['request_deadline_seconds']
    for attempt in range(config['max_network_attempts']):
        started = time.monotonic(); result = None; error = None; provider = {}; retryable = True; fatal = False; retry_after = 0
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0: raise TimeoutError('Request deadline exceeded')
            req = urllib.request.Request(endpoint, data=json.dumps(wire, ensure_ascii=False).encode(),
                headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
            with opener.open(req, timeout=min(config['request_timeout_seconds'],remaining)) as response:
                result = read_stream(response, deadline)
            # Authentication is never a model input. Defend against accidental
            # provider reflection before any returned text can reach disk.
            result = json.loads(redact(json.dumps(result, ensure_ascii=False), key))
        except urllib.error.HTTPError as exc:
            error = 'HTTP_%d' % exc.code
            retryable = exc.code in (408,429,500,502,503,504)
            try:
                body = json.loads(exc.read(8192)).get('error',{})
                provider = {k:redact(body[k],key)[:600] for k in ('code','message') if k in body}
            except (ValueError,TypeError,AttributeError): pass
            fatal = terminal_account_error(exc.code,provider)
            try: retry_after = max(0,float(exc.headers.get('Retry-After',0)))
            except (ValueError,TypeError): pass
        except (OSError,ValueError,RuntimeError) as exc:
            error = type(exc).__name__
        record = dict(at=now(), attempt=attempt+1, request_sha256=digest(wire),
            elapsed_seconds=time.monotonic()-started, error=error, provider_error=provider,
            finish_reason=result['finish_reason'] if result else None)
        with Path(log_path).open('a') as stream: stream.write(json.dumps(record,ensure_ascii=False)+'\n')
        if fatal: raise AccountBlocked('GLM account unavailable: '+json.dumps(provider,ensure_ascii=False))
        if result is not None: return result
        delay = min(config['retry_backoff_cap_seconds'],config['retry_backoff_base_seconds']*2**attempt)
        delay = max(delay,retry_after)+random.SystemRandom().uniform(0,config['retry_jitter_seconds'])
        if not retryable or attempt+1>=config['max_network_attempts'] or time.monotonic()+delay>=deadline:
            raise RuntimeError('Bounded GLM request failed: '+str(error))
        time.sleep(delay)
    raise RuntimeError('No GLM response')


def case_worker(case, prepared, out, config, key):
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    def stop(*_): raise KeyboardInterrupt('Worker termination requested')
    signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
    failed=False
    try:
        run_case(case,prepared,out,config,ENDPOINT,key,request_fn=request_model)
    except BaseException as exc:
        failed=True
        write(out/'cases'/case['sample_id']/'status.json',dict(sample_id=case['sample_id'],phase='failed',
            pid=os.getpid(),error_type=type(exc).__name__,error=redact(str(exc),key)[:900],
            fatal_account_error=isinstance(exc,AccountBlocked),finished_at=now()))
    finally: key=None
    if failed: raise SystemExit(1)


def append_notice(registration, message):
    for name in registration['documentation']:
        fd=os.open(ROOT/name,os.O_WRONLY|os.O_APPEND)
        try: os.write(fd,message.encode())
        finally: os.close(fd)


def worker_main(a):
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    prepared=a.prepared.resolve();out=a.output.resolve();registration=read(a.registration);config=read(a.config)
    if config['model']!='glm-5.3-flash' or config['backend']!='glm' or config['endpoint']!=ENDPOINT:
        raise ValueError('Unexpected model or endpoint')
    cases=verify(prepared)
    out.mkdir(parents=True,exist_ok=False)
    # The launcher sends the secret via an anonymous pipe, not argv or env.
    key=sys.stdin.readline().strip();sys.stdin.close()
    if not key: raise ValueError('Missing stdin credential')
    state=dict(phase='starting',model=config['model'],started_at=now(),supervisor_pid=os.getpid(),
        expected_samples=len(cases),expected_max_calls=2*len(cases),concurrency=config['concurrency'],
        credential_on_disk=False,html_generated=False,semantic_accuracy='pending_review')
    def update(**kw):
        state.update(kw,updated_at=now());write(out/'status.json',state);print(json.dumps(state),flush=True)
    def stop(*_): raise KeyboardInterrupt('Supervisor termination requested')
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    context=multiprocessing.get_context('fork');active={};workers=[];pending=deque(cases)
    completed=False;error=None;account_blocked=False
    write(out/'manifest.json',dict(prepared=str(prepared),prepared_manifest_sha256=file_hash(prepared/'manifest.json'),
        config=config,registration=registration,sample_order=[c['sample_id'] for c in cases],started_at=now(),
        input_protocol='Unchanged morning v001 and same human34 inputs as local Qwen',
        source_sha256={name:file_hash(ROOT/name) for name in [
            'scripts/run_human_route_choice_glm.py','core/agent_route_choice.py',
            'scripts/run_agent_route_choice.py','scripts/run_human_route_choice.py','scripts/prepare_human_route_choice.py']}))
    def launch(case):
        child=context.Process(target=case_worker,args=(case,prepared,out,config,key));child.start()
        active[case['sample_id']]=child;workers.append((case['sample_id'],child))
        write(out/'workers.json',[dict(sample_id=sid,pid=process.pid) for sid,process in workers])
    try:
        # The first actual sample is the availability probe and counts toward 34.
        update(phase='checking_first_sample');launch(pending.popleft())
        deadline=time.monotonic()+config['batch_deadline_seconds'];probe_done=False
        last_update=0
        while active or pending:
            if time.monotonic()>deadline: raise TimeoutError('GLM batch deadline exceeded')
            for sid,child in list(active.items()):
                if child.is_alive(): continue
                child.join();active.pop(sid)
                path=out/'cases'/sid/'status.json'
                result=read(path) if path.exists() else dict(phase='failed',error='Worker exited without status')
                if result.get('phase')=='running':
                    result.update(phase='failed',error='Worker exited before finishing',worker_exitcode=child.exitcode);write(path,result)
                if result.get('fatal_account_error'):
                    account_blocked=True;raise AccountBlocked(result['error'])
                if sid==cases[0]['sample_id']:
                    if not (out/'cases'/sid/'call1_response.json').exists():
                        raise RuntimeError('First real sample received no complete GLM response; batch not expanded')
                    probe_done=True
                    update(phase='running_parallel',first_sample_finished=True)
            if probe_done:
                while pending and len(active)<config['concurrency']: launch(pending.popleft())
            if time.monotonic()-last_update>=5:
                summary=summarize(cases,out)
                update(**{k:v for k,v in summary.items() if k!='cases'},active_workers=[c.pid for c in active.values()],
                       queued_samples=len(pending),finished_samples=sum(
                           (out/'cases'/c['sample_id']/'status.json').exists() and
                           read(out/'cases'/c['sample_id']/'status.json').get('phase') in ('failed','complete_pending_semantic_review')
                           for c in cases))
                last_update=time.monotonic()
            time.sleep(2)
        completed=True
    except BaseException as exc:
        error=redact(type(exc).__name__+': '+str(exc),key)
    finally:
        signal.signal(signal.SIGINT,signal.SIG_IGN);signal.signal(signal.SIGTERM,signal.SIG_IGN)
        cleanup=cleanup_case_workers(workers)
        write(out/'worker_cleanup.json',cleanup)
        # Scan only text artifacts produced by this run, while key is still in
        # memory. Neither the key nor a hash/prefix of it is written to this audit.
        hits=[]
        for path in out.rglob('*'):
            if path.is_file() and path.suffix in ('.json','.jsonl','.log','.txt'):
                if key.encode() in path.read_bytes(): hits.append(str(path.relative_to(out)))
        if hits: error='Credential output audit failed: '+','.join(hits)
        key=None
        write(out/'credential_cleanup.json',dict(at=now(),credential_on_disk=bool(hits),matching_files=hits,
            workers_exited=all(not row['alive'] for row in cleanup),core_dumps_disabled=True,
            scope='No key in argv/environment/files; anonymous stdin pipe and process memory; workers exited.'))
    summary=summarize(cases,out)
    try: summary['audited_requests']=request_audit(cases,prepared,out,config)
    except Exception as exc: error=(error+'; ' if error else '')+'request audit: '+str(exc)
    phase=('complete_pending_semantic_review' if summary['protocol_valid_samples']==len(cases)
        else 'complete_with_invalid_samples') if completed and error is None else ('blocked_account' if account_blocked else 'failed_or_interrupted')
    summary.update(phase=phase,error=error,finished_at=now(),workers_exited=all(not r['alive'] for r in cleanup),credential_on_disk=bool(hits))
    write(out/'summary.json',summary);update(**{k:v for k,v in summary.items() if k!='cases'})
    write(ROOT/registration['experiment_dir']/'completion.json',dict(state,output=str(out.relative_to(ROOT))))
    notice=('\n\n%s GLM-5.3-Flash人工34点无全景批次收尾：`%s`，保存%s/68次回答，协议有效%s/34。'
            'worker全部退出%s，凭据未落盘%s，本轮无HTML；语义正确率待复核。结果 `%s`。\n') % (
        now(),phase,summary['saved_responses'],summary['protocol_valid_samples'],summary['workers_exited'],not hits,out.relative_to(ROOT))
    append_notice(registration,notice)
    return 0 if completed and error is None else 1


def launch_main(a):
    import termios
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    if not sys.stdin.isatty(): raise ValueError('Launcher requires a no-echo terminal for stdin transfer')
    original=termios.tcgetattr(sys.stdin.fileno());hidden=list(original);hidden[3]&=~(termios.ECHO|termios.ECHONL)
    termios.tcsetattr(sys.stdin.fileno(),termios.TCSANOW,hidden)
    try:
        print('READY_FOR_KEY_STDIN_NO_ECHO',flush=True)
        key=sys.stdin.readline().strip()
    finally: termios.tcsetattr(sys.stdin.fileno(),termios.TCSANOW,original)
    if not key: raise ValueError('Missing credential')
    parent=a.output.resolve().parent;parent.mkdir(parents=True,exist_ok=False)
    command=[sys.executable,'-B',str(Path(__file__).resolve()),'--worker','--prepared',str(a.prepared.resolve()),
        '--output',str(a.output.resolve()),'--registration',str(a.registration.resolve()),'--config',str(a.config.resolve())]
    env={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ('API_KEY','TOKEN','SECRET'))}
    env.update(PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1')
    try:
        with (parent/'supervisor.log').open('x') as log:
            child=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        child.stdin.write((key+'\n').encode());child.stdin.close()
    finally: key=None
    record=dict(at=now(),supervisor_pid=child.pid,command=command,credential_delivery='anonymous stdin pipe',credential_on_disk=False)
    write(parent/'launcher.json',record)
    write(ROOT/read(a.registration)['experiment_dir']/'launch.json',record)
    print('LAUNCHED supervisor_pid=%d'%child.pid,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--launch',action='store_true');mode.add_argument('--worker',action='store_true')
    p.add_argument('--prepared',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--registration',type=Path,required=True);p.add_argument('--config',type=Path,required=True)
    a=p.parse_args();sys.exit(launch_main(a) if a.launch else worker_main(a))
