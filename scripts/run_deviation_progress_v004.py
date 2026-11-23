"""Check or review frozen Route53 trajectories with a versioned deviation prompt."""
from __future__ import annotations

import argparse
from collections import Counter
from functools import partial
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

import run_deviation_progress_review as review
import run_route53_qwen_review as route
from core.agent_route_choice import file_hash, now, read, write

ROOT = route.ROOT
VERSION = ROOT / 'experiments/deviation_progress/v004'
V003 = route.RUN
validate_v004 = review.validate_v004
validate_v005 = review.validate_v005


VALIDATORS = {'v004': validate_v004, 'v005': validate_v005, 'v005.1': validate_v005,
              'v006': validate_v005, 'v006.1': validate_v005}


def load_cases(numbers):
    frozen = read(V003 / 'retained_nodes_and_terminals.json')
    selected = {}
    for case in route.load_cases():
        number = case['case_number']
        if number not in numbers:
            continue
        dedup = read(V003 / f'dedup/cases/C{number:02d}/result.json')
        selected[number] = route.retained_case(case, dedup)
        if selected[number]['nodes'] != frozen[case['episode_id']]:
            raise ValueError(f'Frozen v003 nodes differ for C{number:02d}')
    if len(selected) != len(numbers):
        raise ValueError('Choose unique case numbers from the frozen 53 cases')
    return [selected[number] for number in numbers]


def verify(condition, message):
    if not condition:
        raise ValueError(message)


def audit_case(case, folder, validator, prompt, settings):
    """Reconstruct the sampled inputs and causal state from actual archived replies."""
    result = read(folder / 'result.json')
    verify(result['episode_id'] == case['episode_id'], 'Episode mismatch')
    nodes = case['nodes']
    anchor = nodes[0]
    progress = {'zh': '首次有效节点：尚未确认此前完成了哪些导航要求。',
                'en': 'First retained node: prior completion of navigation requirements is unconfirmed.'}
    alarm = None
    counts = Counter()
    rounds = []
    prompt_hash = review.sha(prompt.encode())
    for i, item in enumerate(result['reviews']):
        node = nodes[i]
        stem = folder / node['id']
        req = read(stem.with_suffix('.request.json'))
        response = read(stem.with_suffix('.response.json'))
        expected = review.image_refs(case, anchor, node)
        verify(not alarm and node['id'] == item['node_id'] == req['current_id'] and
               anchor['id'] == req['previous_id'] == item['previous_id'], 'Unexpected endpoint')
        verify(req['previous_frame'] == item['from_frame'] == anchor['index'] and
               req['current_frame'] == item['to_frame'] == node['index'], 'Unexpected endpoint frame')
        verify(req['mode'] == item['mode'] == ('initialization' if i == 0 else 'segment') and
               item['terminal_node'] == node['terminal_node'] and
               item['available_at_frame'] == node['emittedAt'] ==
               (node['index'] if node['terminal_node'] else node['index'] + 5), 'Timing mismatch')
        verify(req['instruction_en'] == case['instruction_en'] and req['prior_semantic_progress'] == progress['zh']
               and item['prior_progress'] == progress, 'Prior progress or instruction mismatch')
        verify(req['settings'] == settings and req['prompt_sha256'] == prompt_hash, 'Model or prompt mismatch')
        verify(len(expected) == len(req['images']) == len(item['images']), 'Wrong image count')
        for ref, actual, logged in zip(expected, req['images'], item['images']):
            path = Path(case['image_paths'][ref['image_id']])
            verify(all(actual[k] == logged[k] == v for k, v in ref.items()) and
                   path == Path(actual['path']) == Path(logged['path']) and
                   file_hash(path) == actual['sha256'] == ref['image_id'], 'Input frame mismatch')
        verify(item['status'] == response['status'] and response.get('http_status') == 200,
               'Missing model response')
        choice = response['response']['choices'][0]
        try:
            verify(choice['finish_reason'] == 'stop', 'Incomplete model output')
            answer = validator(json.loads(choice['message']['content']), req)
        except ValueError:
            if item['status'] != 'error':
                raise
            verdict = 'format_error'
        else:
            verify(item['status'] == 'ok' and answer == response['answer'] == item['answer'],
                   'Raw and accepted answer differ')
            verdict = answer['verdict']
            if verdict == 'consistent':
                anchor, progress = node, answer['semantic_progress']
            elif verdict == 'deviated':
                alarm = {'previous_id': anchor['id'], 'current_id': node['id'],
                         'from_frame': anchor['index'], 'to_frame': node['index']}
                verify(item['rollback_target'] == {'node_id': anchor['id'], 'frame': anchor['index'],
                                                   'progress': progress}, 'Rollback mismatch')
        verify(item['committed_progress'] == progress and
               item['progress_anchor'] == {'id': anchor['id'], 'frame': anchor['index']}, 'Commit mismatch')
        counts[verdict] += 1
        rounds.append(dict(node=node['id'], previous=req['previous_id'], frames=[x['frame'] for x in expected],
                           verdict=verdict))
    verify(result['stop_node'] == (alarm['current_id'] if alarm else None) and
           (bool(alarm) or len(rounds) == len(nodes)) and
           result['unreviewed_nodes'] == [n['id'] for n in nodes[len(rounds):]], 'Incomplete or extra rounds')
    return dict(case_number=case['case_number'], episode_id=case['episode_id'], nodes=len(nodes),
                calls=len(rounds), outcomes=dict(counts), first_deviation=alarm, rounds=rounds)


def review_qwen_cases(out, cases, prompt, settings, endpoint, gpu, version, *,
                      resume_from=None, transport_retries=0):
    validator = VALIDATORS[version]
    call = partial(review.call_model, api_base=endpoint, validate_answer=validator, request_timeout=900)
    os.environ['NO_PROXY'] = os.environ['no_proxy'] = '127.0.0.1,localhost'

    def local_call(*args):
        request, folder = args[0], args[-1]
        if resume_from is not None:
            old = resume_from / folder.relative_to(out)
            reqfile, respfile = old.with_suffix('.request.json'), old.with_suffix('.response.json')
            if reqfile.is_file() and respfile.is_file():
                meta, response = read(reqfile), read(respfile)
                matches = all(meta.get(k) == v for k, v in request.items() if k != 'images')
                matches = matches and len(meta['images']) == len(request['images']) and all(
                    all(a.get(k) == v for k, v in b.items())
                    for a, b in zip(meta['images'], request['images']))
                if (matches and meta['settings'] == settings and
                        meta['prompt_sha256'] == review.sha(prompt.encode()) and
                        response.get('http_status') == 200):
                    folder.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(reqfile, folder.with_suffix('.request.json'))
                    shutil.copy2(respfile, folder.with_suffix('.response.json'))
                    write(folder.with_suffix('.provenance.json'), dict(reused_from=str(respfile)))
                    return meta, response
        for attempt in range(transport_retries + 1):
            meta, response = call(*args)
            status = response.get('http_status')
            if status == 200:
                return meta, response
            archive = folder.parent / 'transport_attempts' / folder.name / f'{attempt + 1:02d}'
            archive.mkdir(parents=True, exist_ok=False)
            for suffix in ('.request.json', '.response.json'):
                shutil.copy2(folder.with_suffix(suffix), archive / (folder.name + suffix))
            error = response.get('error', 'unknown')
            retryable = status in (408, 429, 500, 502, 503, 504) or (
                status is None and error.startswith((
                    'ReadTimeout:', 'ConnectTimeout:', 'WriteTimeout:', 'PoolTimeout:',
                    'ConnectError:', 'ReadError:', 'WriteError:', 'RemoteProtocolError:')))
            if not retryable or attempt == transport_retries:
                raise RuntimeError('Local Qwen transport failed: ' + error)
            delay = min(60, 15 * 2 ** attempt)
            print(f'{folder.name}: {error}, retry {attempt + 1}/{transport_retries} in {delay}s', flush=True)
            time.sleep(delay)

    audited = []
    for case in cases:
        number = case['case_number']
        write(out / 'status.json', dict(phase='reviewing', gpu=gpu, current_case=number,
                                        completed=[c['case_number'] for c in audited], at=now()))
        review.run_case(case, str(out), route.LOCAL_AUTH, prompt, settings, model_call=local_call)
        audited.append(audit_case(case, out / f'run/cases/C{number:02d}', validator, prompt, settings))
        write(out / f'{version}_results.json', audited)
    return audited


def run_local(out, cases, prompt, settings, config, gpu, allow_shared, *, version='v004'):
    from run_human_route_choice import start_local
    from run_agent_route_choice import wait_local
    from run_crossing_local_batch import cleanup
    from test_crossing_single_gpu import gpu_snapshot

    service = out / 'service'
    service.mkdir()
    child, locks = None, []
    os.environ['NO_PROXY'] = os.environ['no_proxy'] = '127.0.0.1,localhost'

    def stop(signum, frame):
        raise KeyboardInterrupt('Local review terminated')

    signal.signal(signal.SIGTERM, stop)
    try:
        write(out / 'status.json', dict(phase='admission', gpu=gpu, at=now()))
        while child is None:
            try:
                child, endpoint = start_local(config, gpu, service, locks, allow_shared)
            except (BlockingIOError, RuntimeError) as error:
                if not isinstance(error, BlockingIOError) and str(error) not in (
                    'GPU admission failed; other processes are preserved', 'Insufficient host memory'
                ):
                    raise
                for lock in locks:
                    lock.close()
                locks.clear()
                write(out / 'status.json', dict(phase='waiting_for_gpu', reason=str(error), gpu=gpu, at=now()))
                time.sleep(15)
        write(out / 'status.json', dict(phase='loading', gpu=gpu, server_pid=child.pid, at=now()))
        wait_local(child, endpoint, settings['model'])
        return review_qwen_cases(out, cases, prompt, settings, endpoint, gpu, version)
    finally:
        try:
            cleanup_result = cleanup(child)
            write(service / 'cleanup.json', dict(owned=cleanup_result, gpu_snapshot=gpu_snapshot(), at=now()))
            if cleanup_result and cleanup_result['remaining']:
                raise RuntimeError('Owned server processes remain after cleanup')
        finally:
            for lock in locks:
                lock.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=VALIDATORS, default='v004', help='prompt and answer contract')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-only', action='store_true', help='replay v003 request and answer archives on CPU')
    mode.add_argument('--local-qwen', action='store_true', help='start local Qwen27B for the selected cases')
    mode.add_argument('--qwen-service', type=Path, metavar='SERVICE_JSON', help='use a running local Qwen service')
    parser.add_argument('--cases', nargs='+', required=True, type=int, metavar='N')
    parser.add_argument('--output', type=Path, required=True, help='new output directory')
    parser.add_argument('--resume-from', type=Path, help='reuse matching archived HTTP 200 rounds with a running Qwen service')
    parser.add_argument('--transport-retries', type=int, default=0, help='retry temporary transport failures with a running Qwen service')
    parser.add_argument('--gpu', type=int)
    parser.add_argument('--allow-shared-gpu', action='store_true', help='use the repository shared GPU admission checks')
    parser.add_argument('--gpu-memory-utilization', type=float, help='vLLM memory reservation fraction')
    parser.add_argument('--max-model-len', type=int, help='vLLM context capacity, including generated tokens')
    args = parser.parse_args(argv)
    if args.transport_retries < 0:
        parser.error('--transport-retries must be nonnegative')
    if (args.resume_from or args.transport_retries) and not args.qwen_service:
        parser.error('Resume and transport retries require --qwen-service')
    if args.local_qwen and args.gpu is None:
        parser.error('--local-qwen requires --gpu')
    if args.gpu_memory_utilization is not None and not 0 < args.gpu_memory_utilization <= 1:
        parser.error('GPU memory utilization must be in (0, 1]')
    cases = load_cases(args.cases)
    settings = read(V003 / 'request_settings.json')['settings']
    service = read(args.qwen_service) if args.qwen_service else None
    if args.qwen_service:
        if (service['model'] != settings['model'] or
                not re.fullmatch(r'http://127\.0\.0\.1:[0-9]+/v1', service['base_url'])):
            parser.error('Expected the registered local Qwen model and loopback endpoint')
        if args.gpu is not None or args.gpu_memory_utilization is not None or args.max_model_len is not None or args.allow_shared_gpu:
            parser.error('A running service already has its GPU and capacity settings')
        args.gpu = service['gpu']
        config = dict(service['model_config'])
    else:
        config = read(route.RECORD / 'service_config.json')
    if args.resume_from:
        args.resume_from = args.resume_from.resolve()
        old = read(args.resume_from / 'manifest.json')
        expected_prompt = file_hash(VERSION.parent / args.version / 'prompt_zh.txt')
        if (old['version'] != args.version or old['prompt_sha256'] != expected_prompt or
                old['settings'] != settings or old['gpu'] != args.gpu):
            parser.error('Resume source uses a different version, prompt, model settings or GPU')
    config.pop('retention_authorization', None)
    if args.gpu_memory_utilization is not None:
        config['gpu_memory_utilization'] = args.gpu_memory_utilization
    if args.max_model_len is not None:
        if not settings['max_tokens'] < args.max_model_len <= config['max_model_len']:
            parser.error('Context capacity must fit the unchanged generation budget and model limits')
        config['max_model_len'] = args.max_model_len
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    if service:
        write(out / 'retained_service.json', service)
    baseline_prompt = (ROOT / route.PROMPTS['deviation']).read_text(encoding='utf-8')
    version_dir = VERSION.parent / args.version
    sources = [Path(__file__), Path(review.__file__), Path(route.__file__), version_dir / 'prompt_zh.txt',
               version_dir / 'prompt_en.txt', ROOT / 'tests/test_deviation_progress_v004.py',
               ROOT / 'scripts/run_human_route_choice.py', ROOT / 'scripts/run_crossing_local_batch.py',
               ROOT / 'scripts/run_agent_route_choice.py', ROOT / 'scripts/test_crossing_single_gpu.py',
               ROOT / 'scripts/serve_crossing_vlm.py']
    if args.version in ('v005', 'v005.1', 'v006', 'v006.1'):
        sources.extend([ROOT / 'scripts/run_deviation_progress_v004_deepseek.py',
                        ROOT / 'tests/test_deviation_progress_v005.py',
                        ROOT / 'tests/fixtures/deviation_v004_c47_s04.json'])
    for source in sources:
        target = out / 'source' / source.resolve().relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    prompt = (out / 'source' / version_dir.relative_to(ROOT) / 'prompt_zh.txt').read_text(encoding='utf-8')
    write(out / 'retained_nodes_and_terminals.json', {c['episode_id']: c['nodes'] for c in cases})
    write(out / 'manifest.json', dict(version=args.version, created_at=now(), cases=args.cases,
          mode='check_only' if args.check_only else 'retained_qwen' if service else 'local_qwen',
          gpu=args.gpu, allow_shared_gpu=args.allow_shared_gpu,
          git_head=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
          source_sha256={str(p.resolve().relative_to(ROOT)):file_hash(out/'source'/p.resolve().relative_to(ROOT)) for p in sources},
          prompt_sha256=review.sha(prompt.encode()), settings=settings, service_config=config, trajectory_seed=2,
          frozen_nodes_sha256=file_hash(V003 / 'retained_nodes_and_terminals.json'),
          dataset_manifest_sha256=file_hash(route.DATA / 'manifest.json'),
          resume_from=str(args.resume_from) if args.resume_from else None,
          transport_retries=args.transport_retries,
          request_timeout=900 if (service or args.local_qwen) else 300,
          command=sys.argv if argv is None else [str(Path(__file__).resolve().relative_to(ROOT)), *argv]))
    try:
        baseline = []
        if args.check_only:
            baseline = [audit_case(c, V003 / f"deviation/run/cases/C{c['case_number']:02d}", review.validate,
                                   baseline_prompt, settings) for c in cases]
            write(out / 'v003_replay.json', baseline)
        results = []
        if service:
            results = review_qwen_cases(out, cases, prompt, settings, service['base_url'], args.gpu, args.version,
                                       resume_from=args.resume_from, transport_retries=args.transport_retries)
        elif args.local_qwen:
            results = run_local(out, cases, prompt, settings, config, args.gpu, args.allow_shared_gpu, version=args.version)
        summary = dict(phase='complete', version=args.version, cases=args.cases, at=now(),
                       v003_archived_rounds=sum(c['calls'] for c in baseline),
                       verdicts=dict(sum((Counter(c['outcomes']) for c in results), Counter())))
        summary[f'{args.version}_model_calls'] = sum(c['calls'] for c in results)
        write(out / 'status.json', summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)
    except BaseException as error:
        write(out / 'status.json', dict(phase='failed', at=now(), error=str(error)))
        raise


if __name__ == '__main__':
    main()
