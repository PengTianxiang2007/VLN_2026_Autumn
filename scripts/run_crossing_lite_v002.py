"""Prepare or supervise a fixed three-RGB, 1..5 scoring batch on a local vLLM service."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from core.agent_route_choice import now, read, write
from core.crossing_lite import digest, sha, select_cases, windows, request, request_seed, validate
from run_crossing_local_batch import cleanup
from test_crossing_single_gpu import gpu_snapshot, process

DATASET = ROOT / 'outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001'
MODEL = Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/Qwen3.5-4B')
SOURCES = ['scripts/export_crossing_lite_v002.py', 'core/crossing_lite_v002_review.js', 'scripts/check_crossing_lite_v002.cjs', 'scripts/check_crossing_robot_marker.cjs', 'scripts/export_crossing_lite_full.py', 'core/crossing_lite_full_review.js', 'scripts/crossing_lite_v002_finish.py', 'scripts/check_crossing_lite_full.cjs', 'core/crossing_lite.py', 'scripts/run_crossing_lite_v002.py',
           'scripts/export_crossing_lite.py', 'core/crossing_lite_review.js',
           'scripts/check_crossing_lite.cjs', 'scripts/export_crossing_iteration.py',
           'core/crossing_campaign_template.html', 'core/crossing_campaign_panel.html',
           'core/crossing_visualization_template.json', 'core/agent_route_choice.py',
           'scripts/run_crossing_local_batch.py', 'scripts/test_crossing_single_gpu.py']


def prepare(out, reg):
    if (out / 'manifest.json').exists():
        raise ValueError('Use a new run directory')
    out.mkdir(parents=True, exist_ok=True)
    seed = 20261107
    selected = select_cases([json.loads(x) for x in (DATASET / 'evaluation/episodes.jsonl').read_text().splitlines()],
                            {'failure': 10, 'success': 10}, seed)
    target='kujiale_0113_66_1'
    if target not in {e['episode_id'] for e in selected}:
        target_row=next(e for e in map(json.loads,(DATASET/'evaluation/episodes.jsonl').read_text().splitlines()) if e['episode_id']==target)
        replace_index=max(i for i,e in enumerate(selected) if e['group']==target_row['group'])
        selected[replace_index]=target_row
    index = {e['episode_id']: e for e in map(json.loads, (DATASET / 'inputs/episodes.jsonl').read_text().splitlines())}
    tasks = []
    inputs = []
    for case in selected:
        eid = case['episode_id']
        obs_path = DATASET / index[eid]['observations']
        obs = read(obs_path)
        frames = []
        for t, images in windows(obs):
            for im in images:
                assert sha(DATASET / im['rgb']) == im['rgb_sha256']
            frames.append(dict(frame=t, images=images))
        tasks.append(dict(episode_id=eid, frames=frames))
        inputs.append(dict(episode_id=eid, observations_sha256=sha(obs_path), calls=len(frames)))
    baseline=ROOT/'outputs/crossing_checkpoint/lite_full_v001/run_20261108_01'
    baseline_predictions={}; baseline_hashes={}
    for task in tasks:
        predictions={}
        for f in task['frames']:
            prefix=baseline/'cases'/task['episode_id']/('F%04d'%f['frame'])
            rp=prefix.with_suffix('.response.json'); qp=prefix.with_suffix('.request.json')
            result=read(rp); req=read(qp)
            assert result['valid'] and req['images']==f['images'], 'Baseline inputs differ'
            predictions[str(f['frame'])]=dict(score=result['answer']['score'],answer=result['answer'],raw=result['response'],error=None,image_frames=result['image_frames'],request_sha256=req['request_sha256'],latency_seconds=result['latency_seconds'],valid=True)
            baseline_hashes[str(rp.relative_to(ROOT))]=sha(rp)
        baseline_predictions[task['episode_id']]=predictions
    write(out/'baseline_predictions.json',baseline_predictions)
    write(out/'baseline_audit.json',dict(source=str(baseline),label='最优版本1',same_images_verified=True,response_sha256=baseline_hashes))
    shutil.copy2(baseline/'translations.json',out/'baseline_translations.json')
    shutil.copy2(baseline/'prompt_en.txt',out/'baseline_prompt_en.txt')
    write(out / 'evaluation_selection.json', selected)
    write(reg / 'selection.json', selected)
    write(out / 'input_audit.json', dict(passed=True, cases=inputs, exact_three_frame_windows=True))
    for i in range(4):
        write(out / ('tasks_%d.json' % i), tasks[i::4])
    shutil.copy2(reg / 'prompt_en.txt', out / 'prompt_en.txt')
    config = dict(kind='crossing_lite', version='lite_v002', tag='qwen35_4b_rgb3_score5_v002_20',
                  dataset=str(DATASET), dataset_id=read(DATASET / 'dataset.json')['dataset_id'],
                  model_path=str(MODEL), model='qwen35-4b-standby', gpu=0,
                  concurrency=4, gpu_memory_utilization=0.50, max_model_len=8192,
                  max_images=3, max_tokens=256, temperature=0, thinking=False, seed=seed,
                  selection_rule='Seeded scene round-robin 10 failures + 10 successes; force inclusion of user-selected kujiale_0113_66_1 by replacing last same-group case; development comparison, not held-out evaluation',
                  groups={'failure': 10, 'success': 10}, expected_calls=sum(len(t['frames']) for t in tasks),
                  request_timeout_seconds=180, network_attempts=2, batch_timeout_seconds=28800,
                  structured_output='json_schema', score_range=[1, 5], uturn_counts=True,
                  input_policy='Exact t-2,t-1,t RGB only; no instruction/actions/history answers/labels/maps/future',
                  evaluation_policy='Point annotations are references; unlabeled frames are not negative. No PR/F1 or old 1m matching. Display threshold >=4 is not a checkpoint rule.',
                  register=str(reg), documentation=[str(reg / 'README.md'), str(reg.parent / 'README.md'),
                  str(ROOT / 'experiments/README.md'), str(ROOT / 'docs/STATUS.md')])
    write(out / 'protocol.json', config)
    write(reg / 'protocol.json', config)
    model_config = read(MODEL / 'config.json')
    idx = MODEL / 'model.safetensors.index.json'
    shards = sorted(set(read(idx)['weight_map'].values()))
    assert all((MODEL / s).is_file() and (MODEL / s).stat().st_size > 0 for s in shards)
    write(out / 'model_audit.json', dict(config=model_config, config_sha256=sha(MODEL / 'config.json'),
          index_sha256=sha(idx), shards=[dict(name=s, bytes=(MODEL / s).stat().st_size) for s in shards], offline=True))
    hashes = {}
    for rel in SOURCES:
        dest = out / 'source' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dest)
        hashes[rel] = sha(dest)
    manifest = dict(baseline_hashes={name:sha(out/name) for name in ['baseline_predictions.json','baseline_audit.json','baseline_translations.json','baseline_prompt_en.txt']}, created_at=now(), git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    source_hashes=hashes, prompt_sha256=sha(out / 'prompt_en.txt'), protocol_sha256=sha(out / 'protocol.json'),
                    task_hashes={('tasks_%d.json' % i): sha(out / ('tasks_%d.json' % i)) for i in range(4)},
                    selection_sha256=sha(out / 'evaluation_selection.json'), expected_calls=config['expected_calls'])
    write(out / 'manifest.json', manifest)
    write(reg / 'registration.json', manifest)
    (out / 'workspace_status.txt').write_bytes(subprocess.check_output(['git', 'status', '--short'], cwd=ROOT))
    (out / 'tracked_worktree.diff').write_bytes(subprocess.check_output(['git', 'diff', '--binary'], cwd=ROOT))
    write(out / 'status.json', dict(phase='prepared', created_at=now(), **config))
    print(json.dumps(dict(prepared=True, expected_calls=config['expected_calls'], scenes=len({c['scene'] for c in selected}), groups=config['groups'])))


def verify(out):
    m = read(out / 'manifest.json')
    assert sha(out / 'prompt_en.txt') == m['prompt_sha256']
    assert sha(out / 'protocol.json') == m['protocol_sha256']
    for name, expected in m.get('baseline_hashes',{}).items():
        assert sha(out/name)==expected
    for name, expected in m['task_hashes'].items():
        assert sha(out / name) == expected
    for rel, expected in m['source_hashes'].items():
        assert sha(ROOT / rel) == expected, 'Registered source changed: ' + rel


def worker(out, wid):
    verify(out)
    c = read(out / 'protocol.json')
    prompt = (out / 'prompt_en.txt').read_text()
    base = read(out / 'service/service.json')['base_url']
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    progress = dict(worker=wid, pid=os.getpid(), phase='running', completed_calls=0, valid_calls=0, completed_episodes=0)
    status_path = out / 'workers' / ('worker_%d.json' % wid)
    write(status_path, progress)
    for task in read(out / ('tasks_%d.json' % wid)):
        eid = task['episode_id']
        folder = out / 'cases' / eid
        folder.mkdir(parents=True, exist_ok=False)
        case = dict(phase='running', worker=wid, expected=len(task['frames']), processed=0, valid=0)
        write(folder / 'status.json', case)
        network_streak = 0
        for frame in task['frames']:
            t, images = frame['frame'], frame['images']
            prefix = folder / ('F%04d' % t)
            seed = request_seed(eid, t, c['seed'])
            wire = request(prompt, images, c['dataset'], c['model'], seed)
            write(prefix.with_suffix('.request.json'), dict(frame=t, image_frames=[im['frame'] for im in images],
                  images=images, request_sha256=digest(wire), preview=request(prompt, images, c['dataset'], c['model'], seed, False)))
            started = time.monotonic()
            record = dict(frame=t, image_frames=[im['frame'] for im in images], started_at=now(), attempts=[], valid=False)
            raw = None
            for attempt in range(c['network_attempts']):
                try:
                    req = urllib.request.Request(base + '/chat/completions', data=json.dumps(wire).encode(), headers={'Content-Type': 'application/json'})
                    with opener.open(req, timeout=c['request_timeout_seconds']) as response:
                        raw = json.load(response)
                    record['attempts'].append(dict(attempt=attempt + 1, status='response', at=now()))
                    break
                except (OSError, ValueError) as exc:
                    record['attempts'].append(dict(attempt=attempt + 1, error=str(exc), at=now()))
                    if attempt + 1 < c['network_attempts']:
                        time.sleep(2)
            record.update(response=raw, finished_at=now(), latency_seconds=time.monotonic() - started)
            if raw is not None:
                network_streak = 0
                try:
                    choice = raw['choices'][0]
                    if choice['finish_reason'] != 'stop':
                        raise ValueError('Non-stop finish reason')
                    record['answer'] = validate(json.loads(choice['message']['content']))
                    record['valid'] = True
                except (KeyError, ValueError, TypeError) as exc:
                    record['validation_error'] = str(exc)
            else:
                network_streak += 1
                record['validation_error'] = 'No model response'
            write(prefix.with_suffix('.response.json'), record)
            case['processed'] += 1
            case['valid'] += int(record['valid'])
            progress['completed_calls'] += 1
            progress['valid_calls'] += int(record['valid'])
            progress.update(episode_id=eid, frame=t, updated_at=now())
            write(folder / 'status.json', case)
            write(status_path, progress)
            if network_streak >= 3:
                raise RuntimeError('Three consecutive transport failures; stopping worker')
        case.update(phase='complete' if case['valid'] == case['expected'] else 'complete_with_invalid', finished_at=now())
        write(folder / 'status.json', case)
        progress['completed_episodes'] += 1
        write(status_path, progress)
    progress.update(phase='complete', finished_at=now())
    write(status_path, progress)


def supervise(out):
    verify(out)
    c = read(out / 'protocol.json')
    state = dict(phase='waiting_for_service', pid=os.getpid(), started_at=now(), expected_calls=c['expected_calls'])
    workers = []
    def update(phase, **kw):
        state.update(phase=phase, updated_at=now(), **kw)
        write(out/'status.json', state)
        print(json.dumps(state, ensure_ascii=False), flush=True)
    def stop(*_):
        raise InterruptedError('Pipeline cancelled')
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    update('waiting_for_service')
    try:
        service_path = ROOT/'outputs/model_services/qwen4b_gpu0_20261108_01/service.json'
        deadline = time.monotonic()+3600
        while True:
            svc=read(service_path)
            if svc['phase']=='ready':
                break
            if svc['phase'] in ('failed','stopped'):
                raise RuntimeError('Retained model service unavailable: '+str(svc.get('error',svc['phase'])))
            if time.monotonic()>deadline:
                raise TimeoutError('Service readiness deadline exceeded')
            time.sleep(10)
        (out/'service').mkdir(exist_ok=True)
        write(out/'service/service.json', svc)
        update('inference', service=svc['base_url'], service_reused=True, server_max_num_seqs=1)
        for i in range(c['concurrency']):
            with (out/('worker_%d.log'%i)).open('x') as log:
                workers.append(subprocess.Popen([sys.executable,'-B',__file__,'--output',str(out),'--worker',str(i)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True))
        write(out/'workers.json',[process(w.pid) for w in workers])
        deadline=time.monotonic()+c['batch_timeout_seconds']
        while any(w.poll() is None for w in workers):
            if any(w.poll() not in (None,0) for w in workers):
                raise RuntimeError('Scoring worker failed; see worker logs')
            if time.monotonic()>deadline:
                raise TimeoutError('Scoring batch deadline exceeded')
            time.sleep(15)
        if any(w.returncode for w in workers):
            raise RuntimeError('Scoring worker failed')
        update('export_translate_validate_publish')
        with (out/'finish.log').open('x') as log:
            subprocess.run([str(ROOT/'backbone/streamvln/.venv/bin/python'),'-B',str(ROOT/'scripts/crossing_lite_v002_finish.py'),str(out)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=43200)
        result=read(out/'delivery.json')
        update('complete',finished_at=now(),**result)
    except BaseException as exc:
        update('failed', error=type(exc).__name__+': '+str(exc), finished_at=now())
    finally:
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        write(out/'worker_cleanup.json',[cleanup(w) for w in workers])
        # The user's explicitly retained standby service is not owned by this batch.
        note='\n'+now()+' v002_20后台流程状态：'+json.dumps(state,ensure_ascii=False)+'\n'
        for name in c['documentation']:
            with Path(name).open('a') as f: f.write(note)
    return 0 if state['phase']=='complete' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--prepare', type=Path, help='Registration directory; prepare only')
    parser.add_argument('--worker', type=int)
    args = parser.parse_args()
    out = args.output.resolve()
    if args.prepare:
        prepare(out, args.prepare.resolve())
    elif args.worker is not None:
        worker(out, args.worker)
    else:
        sys.exit(supervise(out))
