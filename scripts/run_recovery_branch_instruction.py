"""Generate local recovery instructions with the model that supplied the branch inventory."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import httpx

from run_recovery_branch_review import CASES, ROOT, SERVICE, V006, now, read, sha, write

SPEC = ROOT / 'experiments/agent_recovery/branch_instruction_v001'
FIRST = ROOT / 'outputs/agent_recovery/branch_review_v001/run_20261121_04_deepseek47'
QWEN_FIRST = FIRST.parent / 'run_20261121_02_all47'
ENDPOINT = 'https://api.deepseek.com/chat/completions'
SETTINGS = dict(model='deepseek-flash', temperature=0, top_p=1, max_tokens=512,
                thinking={'type': 'disabled'}, response_format={'type': 'json_object'})


def progress_fields(progress, lang):
    labels = ('已完成', '当前') if lang == 'zh' else ('Completed', 'Current')
    parts = re.split(r'(?m)^(?:已完成|当前|待执行|未决|Completed|Current|Pending|Unresolved)\s*[:：]\s*', progress)
    headings = re.findall(r'(?m)^(已完成|当前|待执行|未决|Completed|Current|Pending|Unresolved)\s*[:：]', progress)
    sections = dict(zip(headings, parts[1:]))
    return {key: sections[label].strip() for key, label in zip(('Completed', 'Current'), labels)}


def instruction_context(instruction, progress, review):
    return dict(instruction_en=instruction, **progress_fields(progress['zh'], 'zh'),
                branches=[{k: b[k] for k in ('id', 'direction', 'entrance_description')}
                          for b in review['branches']],
                previous_attempt={k: review['previous_attempt'][k] for k in ('status', 'branch_id')})


def prepare_case(cid, upstream, model='deepseek'):
    if model == 'qwen':
        source = QWEN_FIRST / 'cases' / cid
        source_answer = read(source / 'result.json')
        assert source_answer['status'] == 'ok'
    else:
        source = FIRST / cid
        source_answer = read(source / 'status.json')
        assert source_answer['phase'] == 'complete'
    first = read(source / 'input.json')
    answer = source_answer['answer']
    row = upstream[first['episode_id']]
    alarm = row['first_deviation']
    assert (alarm['previous_id'], alarm['from_frame']) == (first['node_id'], first['checkpoint_step'])
    folder = Path(row['source_run']) / 'run/cases' / cid
    request = read(folder / (alarm['current_id'] + '.request.json'))
    saved = read(folder / (first['node_id'] + '.response.json'))['answer']
    assert (request['previous_id'], request['previous_frame']) == (first['node_id'], first['checkpoint_step'])
    assert saved['verdict'] == 'consistent' and saved['current_id'] == first['node_id']
    progress = saved['semantic_progress']
    assert request['prior_semantic_progress'] == progress['zh']
    context = instruction_context(request['instruction_en'], progress, answer)
    images = first['images'][:3]
    assert [im['image_id'] for im in images] == ['C_left70', 'C_front', 'C_right70']
    for im in images:
        assert im['actual_step'] == first['checkpoint_step'] and sha(ROOT / im['path']) == im['sha256']
    return dict(case_id=cid, episode_id=first['episode_id'], node_id=first['node_id'],
                checkpoint_step=first['checkpoint_step'], images=images, context=context,
                progress_en=progress_fields(progress['en'], 'en'), progress_source=str(folder.relative_to(ROOT)),
                first_response_sha256=sha(source / 'response.json'))


def validate(answer, context):
    if not isinstance(answer, dict) or set(answer) != {'selected_branch_id', 'recovery_instruction_en'}:
        return ['Unexpected output fields']
    bid, line = answer['selected_branch_id'], answer['recovery_instruction_en']
    if bid is None and line is None:
        return []
    prior = context['previous_attempt']
    allowed = {b['id'] for b in context['branches']} - {prior['branch_id']}
    if prior['status'] != 'identified' or not isinstance(bid, str) or bid not in allowed:
        return ['Selected ID is not an eligible alternative']
    if not isinstance(line, str) or not re.search('[A-Za-z]', line) or '\n' in line or re.search(r'[\u4e00-\u9fff]', line):
        return ['Expected one English instruction']
    return []


def infer(case, out, prompt, key, endpoint, settings):
    folder = out / 'cases' / case['case_id']
    context = case['context']
    content = [dict(type='text', text=json.dumps(context, ensure_ascii=False, indent=2))]
    for im in case['images']:
        data = base64.b64encode((ROOT / im['path']).read_bytes()).decode('ascii')
        content.extend([dict(type='text', text=im['image_id'] + ' | ' + im['view_label']),
                        dict(type='image_url', image_url=dict(url='data:image/png;base64,' + data))])
    body = dict(**settings, messages=[dict(role='system', content=prompt), dict(role='user', content=content)])
    write(folder / 'input.json', case)
    write(folder / 'request.json', body)
    result = dict(case_id=case['case_id'], started_at=now())
    try:
        with httpx.Client(timeout=httpx.Timeout(300, connect=30), trust_env=bool(key), follow_redirects=False) as client:
            response = client.post(endpoint, headers={'Authorization': 'Bearer ' + key} if key else {}, json=body)
        result['http_status'] = response.status_code
        (folder / 'response.json').write_text(response.text.replace(key, '[redacted]') if key else response.text)
        response.raise_for_status()
        choice = response.json()['choices'][0]
        result['raw_answer'] = choice['message']['content']
        result['answer'] = json.loads(result['raw_answer'])
        errors = validate(result['answer'], context)
        if choice['finish_reason'] != 'stop':
            errors.append('Incomplete response')
        result.update(status='invalid' if errors else 'ok', validation_errors=errors)
    except Exception as exc:
        result.update(status='error', error=str(exc).replace(key, '[redacted]') if key else str(exc))
    result['finished_at'] = now()
    write(folder / 'result.json', result)
    print(case['case_id'], result['status'], flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', choices=['qwen','deepseek'], default='deepseek')
    parser.add_argument('--all', action='store_true', help='Use every v006 rollback target.')
    parser.add_argument('--reuse', type=Path, help='Import matching, completed same-model cases.')
    args = parser.parse_args()
    out = args.output
    upstream = {row['episode_id']: row for row in read(V006)}
    ids = sorted('C%02d' % row['case_number'] for row in upstream.values() if row['first_deviation']) if args.all else CASES
    cases = [prepare_case(cid, upstream, args.model) for cid in ids]
    prompt = (SPEC / 'prompt_zh.txt').read_text()
    key = None
    if args.model == 'qwen':
        service = read(SERVICE)
        pid = Path('/proc') / str(service['server_pid'])
        assert service['gpu'] == 3 and pid.joinpath('cwd').resolve() == ROOT
        assert 'vllm.entrypoints.openai.api_server' in pid.joinpath('cmdline').read_bytes().decode()
        base = service['base_url']
        with httpx.Client(trust_env=False, timeout=15) as client:
            models = client.get(base + '/models').raise_for_status().json()
        assert service['model'] in [m['id'] for m in models['data']]
        first_run = QWEN_FIRST
        settings = dict(read(first_run / 'manifest.json')['generation'], model=service['model'], max_tokens=512)
        endpoint = base + '/chat/completions'
    else:
        first_run, endpoint, settings = FIRST, ENDPOINT, SETTINGS
        key = os.environ.get('DEEPSEEK_API_KEY') or (getpass.getpass('DeepSeek credential (hidden): ') if sys.stdin.isatty() else sys.stdin.readline().strip())
        if not key:
            raise SystemExit('Missing DeepSeek credential')
    reused = {}
    if args.reuse:
        old = read(args.reuse / 'manifest.json')
        assert (old['settings'],old['prompt'],old['source_run'],old['endpoint']) == (settings,prompt,str(first_run.relative_to(ROOT)),endpoint)
        available = {r['case_id']:r for r in read(args.reuse / 'results.json') if r['status']=='ok'}
        for case in cases:
            cid = case['case_id']
            if cid in available:
                source = args.reuse / 'cases' / cid
                assert read(source / 'input.json') == case and read(source / 'result.json') == available[cid]
                reused[cid] = available[cid]
    todo = [case for case in cases if case['case_id'] not in reused]
    concurrency = min(1 if args.model == 'qwen' else len(todo), len(todo))
    out.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__).resolve(), ROOT / 'scripts/run_recovery_branch_review.py',
               SPEC / 'prompt_zh.txt', SPEC / 'prompt_en.txt']
    for src in sources:
        target = out / 'source' / src.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    for cid in reused:
        shutil.copytree(args.reuse / 'cases' / cid, out / 'cases' / cid)
    write(out / 'manifest.json', dict(version='branch_instruction_v001', created_at=now(), cases=cases,
          endpoint=endpoint, settings=settings, concurrency=concurrency, source_run=str(first_run.relative_to(ROOT)),
          reused_case_ids=list(reused), reused_from=str(args.reuse) if args.reuse else None,
          new_case_ids=[case['case_id'] for case in todo],
          git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
          source_sha256={str(src.relative_to(ROOT)):sha(src) for src in sources}, prompt=prompt))
    write(out / 'status.json', dict(phase='running', total=len(cases), started_at=now()))
    by_id = dict(reused)
    if todo:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            jobs = [pool.submit(infer, case, out, prompt, key, endpoint, settings) for case in todo]
            for job in jobs:
                result = job.result()
                by_id[result['case_id']] = result
    results = [by_id[cid] for cid in ids]
    write(out / 'results.json', results)
    valid = sum(row['status'] == 'ok' for row in results)
    write(out / 'status.json', dict(phase='complete' if valid == len(results) else 'complete_with_errors',
          valid=valid, total=len(results), finished_at=now()))


if __name__ == '__main__':
    main()
