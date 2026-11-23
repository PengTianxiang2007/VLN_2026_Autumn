"""Launch a versioned, parallel offline review using the archived DeepSeek configuration."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import getpass
import multiprocessing
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time

import httpx

import run_deviation_progress_v004 as v4
from core.agent_route_choice import file_hash, now, read, write


def worker(case, out, key, prompt, settings, version='v004', api_base=v4.review.API,
           resume_from=None, rate_limit_retries=0):
    validator = v4.VALIDATORS[version]
    source_endpoint = read(resume_from/'manifest.json')['endpoint'] if resume_from else None

    def invoke(*args):
        request, folder = args[0], args[-1]
        if resume_from is not None:
            old = resume_from / folder.relative_to(out)
            reqfile, respfile = old.with_suffix('.request.json'), old.with_suffix('.response.json')
            if reqfile.is_file() and respfile.is_file():
                meta, response = read(reqfile), read(respfile)
                matches = all(meta.get(k) == v for k, v in request.items() if k != 'images')
                matches = matches and len(meta['images']) == len(request['images']) and all(
                    all(a.get(k) == v for k, v in b.items()) for a, b in zip(meta['images'], request['images']))
                if (matches and meta['settings'] == settings and meta['prompt_sha256'] == v4.review.sha(prompt.encode())
                        and response.get('http_status') == 200):
                    folder.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(reqfile, folder.with_suffix('.request.json'))
                    shutil.copy2(respfile, folder.with_suffix('.response.json'))
                    provenance = old.with_suffix('.provenance.json')
                    origin = read(provenance).get('endpoint', source_endpoint) if provenance.is_file() else source_endpoint
                    write(folder.with_suffix('.provenance.json'), dict(endpoint=origin, reused_from=str(respfile)))
                    return meta, response
        for attempt in range(rate_limit_retries + 1):
            meta, response = v4.review.call_model(*args, api_base=api_base, validate_answer=validator)
            write(folder.with_suffix('.provenance.json'), dict(endpoint=api_base, reused_from=None))
            if response.get('http_status') != 429:
                break
            archive = folder.parent / 'rate_limit_attempts'
            archive.mkdir(exist_ok=True)
            for suffix in ('.request.json', '.response.json'):
                shutil.copy2(folder.with_suffix(suffix), archive / (folder.name + f'.attempt{attempt+1:02d}' + suffix))
            if attempt < rate_limit_retries:
                delay = min(60, 15 * 2 ** attempt) + random.uniform(0, 5)
                print(f'HTTP 429: C{case["case_number"]:02d}/{folder.name}, retry in {delay:.1f}s', flush=True)
                time.sleep(delay)
        if response.get('http_status') != 200:
            raise RuntimeError(response.get('error', 'DeepSeek transport failure'))
        return meta, response

    result = v4.review.run_case(case, str(out), key, prompt, settings, model_call=invoke)
    number = case['case_number']
    audit = v4.audit_case(case, out / f'run/cases/C{number:02d}', validator, prompt, settings)
    return dict(audit, worker_pid=result['worker_pid'])


def supervise(out, numbers, workers, version='v004', api_base=v4.review.API,
              resume_from=None, rate_limit_retries=0, allow_endpoint_change=False):
    key = sys.stdin.readline().strip()
    sys.stdin.close()
    if not key:
        raise ValueError('Missing DeepSeek credential')
    version_dir = v4.VERSION.parent / version
    state = dict(phase='preparing', version=version, pid=os.getpid(), started_at=now(), workers=workers, cases=numbers, completed=0)
    def update(**changes):
        state.update(changes, updated_at=now())
        write(out / 'status.json', state)
    try:
        update()
        cases = v4.load_cases(numbers)
        history = v4.ROOT / 'outputs/deviation_progress/v003/run_20261118_03_deepseek29/manifest.json'
        historical = read(history)
        settings = historical['settings']
        if historical['api'] != v4.review.API or v4.review.API != 'https://api.deepseek.com':
            raise ValueError('Historical API differs from the official DeepSeek endpoint')
        sources = [Path(__file__).resolve(), Path(v4.__file__), Path(v4.review.__file__),
                   Path(v4.route.__file__), version_dir/'prompt_zh.txt', version_dir/'prompt_en.txt']
        hashes = {}
        for source in sources:
            relative = source.relative_to(v4.ROOT)
            dest = out / 'source' / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            hashes[str(relative)] = file_hash(dest)
        prompt = (out / 'source' / version_dir.relative_to(v4.ROOT) / 'prompt_zh.txt').read_text(encoding='utf-8')
        write(out/'retained_nodes_and_terminals.json', {c['episode_id']:c['nodes'] for c in cases})
        write(out/'manifest.json', dict(version=version, git_head=subprocess.check_output(
            ['git','rev-parse','HEAD'], cwd=v4.ROOT, text=True).strip(), source_sha256=hashes,
            prompt_sha256=v4.review.sha(prompt.encode()), created_at=now(), endpoint=api_base,
            settings=settings, trajectory_seed=2, workers=workers, cases=numbers,
            max_review_calls=sum(len(c['nodes']) for c in cases), historical_settings_sha256=file_hash(history),
            resume_from=str(resume_from) if resume_from else None, rate_limit_retries=rate_limit_retries,
            allow_endpoint_change=allow_endpoint_change,
            resume_endpoint=read(resume_from/'manifest.json')['endpoint'] if resume_from else None,
            frozen_nodes_sha256=file_hash(v4.V003/'retained_nodes_and_terminals.json'),
            dataset_manifest_sha256=file_hash(v4.route.DATA/'manifest.json')))
        update(phase='checking_model')
        with httpx.Client(trust_env=False, timeout=30, follow_redirects=False) as client:
            catalog = client.get(api_base+'/models', headers={'Authorization':'Bearer '+key})
            catalog.raise_for_status()
            model = next((m for m in catalog.json()['data'] if m['id']==settings['model']), None)
        if not model or 'image' not in model.get('input_modalities', ['image']):
            raise ValueError('Selected DeepSeek image model is unavailable')
        write(out/'model_catalog_entry.json', model)
        results, failures = [], {}
        counts = Counter()
        reused = {}
        if resume_from is not None:
            old_manifest = read(resume_from/'manifest.json')
            if old_manifest['endpoint'] != api_base and not allow_endpoint_change:
                raise ValueError('Resume endpoint differs; explicit --allow-endpoint-change is required')
            for field, value in (('version',version), ('settings',settings),
                                 ('prompt_sha256',v4.review.sha(prompt.encode()))):
                if old_manifest.get(field) != value:
                    raise ValueError('Resume source differs: '+field)
            update(phase='waiting_previous', resume_from=str(resume_from))
            while read(resume_from/'status.json')['phase'] not in ('complete','incomplete','failed'):
                time.sleep(15)
            old_results = resume_from/f'{version}_results.json'
            if old_results.is_file():
                reused = {r['case_number']:r for r in read(old_results)}
        pending = []
        for case in cases:
            number = case['case_number']
            if number in reused:
                shutil.copytree(resume_from/f'run/cases/C{number:02d}', out/f'run/cases/C{number:02d}')
                write(out/f'run/cases/C{number:02d}/reuse_source.json', dict(
                    run=str(resume_from), endpoint=old_manifest['endpoint'], reused_complete_case=True))
                results.append(reused[number]); counts.update(reused[number]['outcomes'])
            else:
                pending.append(case)
        write(out/f'{version}_results.json', sorted(results, key=lambda r:r['case_number']))
        update(phase='reviewing', completed=len(results), reused_cases=sorted(reused),
               pending_cases=[c['case_number'] for c in pending], completed_case_verdicts=dict(counts))
        with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('fork')) as pool:
            futures = {pool.submit(worker, case, out, key, prompt, settings, version, api_base,
                                   resume_from, rate_limit_retries):case['case_number'] for case in pending}
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as error:
                    failures[str(futures[future])] = str(error).replace(key, '[redacted]')[:500]
                else:
                    results.append(result)
                    counts.update(result['outcomes'])
                    write(out/f'{version}_results.json', sorted(results, key=lambda r:r['case_number']))
                update(completed=len(results), failed_cases=failures, completed_case_verdicts=dict(counts))
        update(phase='incomplete' if failures else 'complete', finished_at=now(),
               calls_in_completed_cases=sum(counts.values()), workers_exited=True)
    except Exception as error:
        update(phase='failed', error=str(error).replace(key, '[redacted]')[:800])
    record = version_dir / out.name
    if out.parent == v4.ROOT/'outputs/deviation_progress'/version and (record/'README.md').is_file():
        write(record/'completion.json', state)
    if state['phase'] != 'complete':
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=v4.VALIDATORS, default='v004', help='prompt and answer contract')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--cases', required=True, nargs='+', type=int)
    parser.add_argument('--workers', required=True, type=int)
    parser.add_argument('--api-base', default=v4.review.API, help='OpenAI-compatible API base, including /v1 if required')
    parser.add_argument('--resume-from', type=Path, help='Wait for this run to exit, then reuse its completed cases and matching HTTP 200 replies')
    parser.add_argument('--allow-endpoint-change', action='store_true', help='Explicitly reuse previous answers while sending new calls to a different endpoint')
    parser.add_argument('--rate-limit-retries', type=int, default=0, help='Bounded backoff retries for HTTP 429 only')
    parser.add_argument('--supervise', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.api_base = args.api_base.rstrip('/')
    if args.resume_from is not None:
        args.resume_from = args.resume_from.resolve()
    if args.rate_limit_retries < 0:
        parser.error('--rate-limit-retries must be nonnegative')
    out = args.output.resolve()
    if len(set(args.cases)) != len(args.cases) or any(n < 1 or n > 53 for n in args.cases):
        parser.error('Choose unique frozen case numbers 1–53')
    if not 1 <= args.workers <= len(args.cases):
        parser.error('Select between one and the number of trajectories for --workers')
    if args.supervise:
        supervise(out, args.cases, args.workers, args.version, args.api_base,
                  args.resume_from, args.rate_limit_retries, args.allow_endpoint_change)
        return
    if out.exists():
        parser.error('Select a new output directory')
    key = getpass.getpass('DeepSeek API key (hidden): ').strip()
    if not key:
        parser.error('Missing DeepSeek credential')
    out.mkdir(parents=True, exist_ok=False)
    env = {k:v for k,v in os.environ.items() if 'proxy' not in k.lower()
           and not any(word in k.upper() for word in ('API_KEY','TOKEN','SECRET'))}
    env['CUDA_VISIBLE_DEVICES'] = ''
    command = [sys.executable, '-Bu', str(Path(__file__).resolve()), '--supervise', '--output', str(out),
               '--version', args.version, '--api-base', args.api_base,
               '--workers', str(args.workers), '--rate-limit-retries', str(args.rate_limit_retries),
               '--cases', *map(str, args.cases)]
    if args.resume_from is not None:
        command.extend(['--resume-from', str(args.resume_from)])
    if args.allow_endpoint_change:
        command.append('--allow-endpoint-change')
    with (out/'supervisor.log').open('xb') as log:
        child = subprocess.Popen(command, cwd=v4.ROOT, env=env, stdin=subprocess.PIPE, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
    with child.stdin as pipe:
        pipe.write((key+'\n').encode())
    print(f'DeepSeek supervisor PID {child.pid}, workers {args.workers}, cases {args.cases}', flush=True)


if __name__ == '__main__':
    main()
