"""Run one seven-image branch review per selected v006 rollback target."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'experiments/agent_recovery/branch_review_v001'
DATA = ROOT / 'outputs/offline_route_dataset/v001/run_20261118_01/dataset'
CAPTURE = ROOT / 'outputs/multiview_capture/v006_pose70/run_20261121_01/points'
TARGETS = ROOT / 'outputs/visualization_publishing/v006_node_multiview_web_20261121_01/multiview_data.json'
V006 = ROOT / 'outputs/deviation_progress/v006_pair_route53_20261121_01/v006_all53.json'
CASES = ['C42', 'C46', 'C49', 'C50', 'C07', 'C05', 'C09', 'C10', 'C20', 'C21']
SERVICE = ROOT / 'outputs/model_services/qwen27b_gpu3_20261121_01/service.json'


def read(path):
    return json.loads(path.read_text())


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def image_record(path, image_id, step, label, expected):
    digest = sha(path)
    if digest != expected:
        raise ValueError('Input image hash mismatch: ' + str(path))
    return dict(image_id=image_id, actual_step=step, view_label=label,
                path=str(path.relative_to(ROOT)), sha256=digest)


def prepare(out, previous=None, spec=SPEC, selected=None):
    groups = read(TARGETS)['cases']
    upstream = {r['episode_id']: r for r in read(V006)}
    case_ids = selected or CASES
    if previous is not None:
        for eid, group in groups.items():
            assert bool(group['rollback']) == bool(upstream[eid]['first_deviation'])
        case_ids = sorted(g['case_id'] for g in groups.values() if g['rollback'])
    cases = []
    for case_id in case_ids:
        eid, group = next((eid, g) for eid, g in groups.items() if g['case_id'] == case_id)
        target = group['rollback']
        frame, node = target['frame'], target['node_id']
        first = upstream[eid]['first_deviation']
        assert (first['previous_id'], first['from_frame']) == (node, frame)
        point = CAPTURE / f'{case_id}_{node}_F{frame:04d}'
        metadata = read(point / 'metadata.json')
        assert (metadata['episode_id'], metadata['node_id'], metadata['frame']) == (eid, node, frame)
        assert [v['offset_deg'] for v in metadata['views']] == [70, 0, -70]
        images = [image_record(point / v['file'], name, frame, label, v['sha256'])
                  for v, name, label in zip(metadata['views'],
                      ['C_left70', 'C_front', 'C_right70'], ['左侧 +70°', '正前 0°', '右侧 −70°'])]
        observations = {r['step']: r for r in map(json.loads, (DATA / 'inputs' / eid / 'observations.jsonl').read_text().splitlines())}
        for offset in [2, 5, 8, 10]:
            image = observations[frame + offset]['native_front']
            images.append(image_record(DATA / image['image'], f'C_plus{offset}', frame + offset,
                                       f'C+{offset} step 实际前视', image['sha256']))
        cases.append(dict(case_id=case_id, episode_id=eid, node_id=node, checkpoint_step=frame,
                          alarm_step=target['alarm_frame'], images=images))
    out.mkdir(parents=True, exist_ok=False)
    sources = {}
    for path in [Path(__file__), spec / 'prompt_zh.txt', spec / 'prompt_en.txt', spec / 'protocol.json', spec / 'output_schema.json']:
        dest = out / 'source' / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        sources[str(path.relative_to(ROOT))] = sha(path)
    service = read(SERVICE)
    assert service['gpu'] == 3 and service['model'] == 'route53-qwen27b'
    manifest = dict(version=read(spec / 'protocol.json')['version'], created_at=now(), upstream_version='v006',
        cases=cases, seed=2, model=service['model'], base_url=service['base_url'], service=service,
        generation=dict(temperature=0, top_p=1, top_k=-1, max_tokens=4096, seed=2,
                        chat_template_kwargs=dict(enable_thinking=False), response_format=dict(type='json_object')),
        prompt=(spec / 'prompt_zh.txt').read_text(), schema=read(spec / 'output_schema.json'),
        git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        sources=sources, input_source_sha256={str(p.relative_to(ROOT)): sha(p) for p in [TARGETS, V006]},
        task_instruction_in_request=False, recovery_instruction_calls=0, navigation_runs=0)
    if previous is not None:
        prior = read(previous / 'manifest.json')
        for key in ('version', 'upstream_version', 'input_source_sha256', 'model', 'generation', 'prompt', 'schema'):
            if prior[key] != manifest[key]:
                raise ValueError('Previous run differs in ' + key)
        if prior['service']['model_config']['model_path'] != service['model_config']['model_path']:
            raise ValueError('Previous run used different weights')
        current_inputs = {c['case_id']: c for c in cases}
        reused = []
        for result in read(previous / 'results.json'):
            cid = result['case_id']
            if result['status'] != 'ok':
                continue
            folder = previous / 'cases' / cid
            if read(folder / 'input.json') != current_inputs[cid] or read(folder / 'result.json') != result:
                raise ValueError('Previous case or result differs: ' + cid)
            shutil.copytree(folder, out / 'cases' / cid)
            reused.append(result)
        manifest['previous_run'] = str(previous)
        manifest['reused_case_ids'] = [r['case_id'] for r in reused]
        manifest['without_v006_rollback'] = sorted(g['case_id'] for g in groups.values() if not g['rollback'])
        write(out / 'results.json', reused)
    write(out / 'manifest.json', manifest)
    (out / 'workspace.diff').write_bytes(subprocess.check_output(['git', 'diff', '--binary'], cwd=ROOT))
    (out / 'workspace_status.txt').write_text(subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True))
    write(out / 'status.json', dict(phase='prepared', total=len(cases), completed=len(manifest.get('reused_case_ids', [])), updated_at=now()))
    return manifest


def validate(answer, schema):
    errors = [e.message for e in Draft202012Validator(schema).iter_errors(answer)]
    if errors:
        return errors
    ids = [b['id'] for b in answer['branches']]
    if ids != [f'B{i+1}' for i in range(len(ids))]:
        errors.append('Branch IDs must be unique and consecutive in output order.')
    if answer['previous_attempt']['status'] == 'identified' and answer['previous_attempt']['branch_id'] not in ids:
        errors.append('previous_attempt.branch_id is absent from branches.')
    if 'candidate_groups' in schema['properties']:
        candidates = [c['id'] for view in answer['view_candidates'].values() for c in view]
        grouped = [cid for group in answer['candidate_groups'] for cid in group['candidate_ids']]
        if len(set(candidates)) != len(candidates) or sorted(grouped) != sorted(candidates):
            errors.append('Every candidate must be unique and belong to exactly one group.')
        kept = [group['branch_id'] for group in answer['candidate_groups'] if group['branch_id'] is not None]
        if sorted(kept) != sorted(ids):
            errors.append('Each retained group must map to a distinct final branch and vice versa.')
    return errors


def run(out, manifest):
    # Reuse the explicitly retained GPU3 service; never launch or shut down a model here.
    service = read(SERVICE)
    assert (service['gpu'], service['server_pid'], service['base_url']) == (3, manifest['service']['server_pid'], manifest['base_url'])
    proc = Path('/proc') / str(service['server_pid'])
    assert 'vllm.entrypoints.openai.api_server' in (proc / 'cmdline').read_bytes().decode().replace('\0', ' ')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(manifest['base_url'] + '/models', timeout=15) as response:
        models = json.load(response)
    assert manifest['model'] in [m['id'] for m in models['data']]
    reused = set(manifest.get('reused_case_ids', []))
    results = read(out / 'results.json') if reused else []
    for case in manifest['cases']:
        if case['case_id'] in reused:
            continue
        folder = out / 'cases' / case['case_id']
        started = now()
        write(out / 'status.json', dict(phase='running', total=len(manifest['cases']), completed=len(results),
              reused=len(reused), newly_completed=len(results)-len(reused), current=case['case_id'], updated_at=started))
        content = [dict(type='text', text=f"节点 C 的观测 step：{case['checkpoint_step']}。以下按固定顺序提供七张图像。\n输出 JSON Schema：\n" + json.dumps(manifest['schema'], ensure_ascii=False))]
        for image in case['images']:
            content.append(dict(type='text', text=f"{image['image_id']} | actual_step={image['actual_step']} | {image['view_label']}"))
            content.append(dict(type='image_url', image_url=dict(url='data:image/png;base64,' + base64.b64encode((ROOT / image['path']).read_bytes()).decode())))
        request = dict(model=manifest['model'], messages=[dict(role='system', content=manifest['prompt']), dict(role='user', content=content)], **manifest['generation'])
        write(folder / 'request.json', request)
        write(folder / 'input.json', case)
        result = dict(case_id=case['case_id'], episode_id=case['episode_id'], started_at=started,
                      checkpoint_step=case['checkpoint_step'], node_id=case['node_id'])
        tick = time.monotonic()
        try:
            req = urllib.request.Request(manifest['base_url'] + '/chat/completions',
                json.dumps(request, ensure_ascii=False).encode(), headers={'Content-Type': 'application/json'})
            with opener.open(req, timeout=900) as response:
                raw = response.read()
            (folder / 'response.json').write_bytes(raw)
            response = json.loads(raw)
            answer_text = response['choices'][0]['message']['content']
            (folder / 'answer.txt').write_text(answer_text)
            result.update(raw_answer=answer_text, finish_reason=response['choices'][0]['finish_reason'], usage=response.get('usage'))
            answer = json.loads(answer_text)
            errors = validate(answer, manifest['schema'])
            if result['finish_reason'] != 'stop':
                errors.append('Unexpected finish reason: ' + str(result['finish_reason']))
            result.update(answer=answer, validation_errors=errors, status='invalid' if errors else 'ok')
        except Exception as exc:
            result.update(status='error', error=f'{type(exc).__name__}: {exc}')
            if hasattr(exc, 'read'):
                (folder / 'error_response.txt').write_bytes(exc.read())
        result.update(completed_at=now(), seconds=round(time.monotonic() - tick, 3))
        write(folder / 'result.json', result)
        results.append(result)
        write(out / 'results.json', results)
        print(json.dumps(dict(case=case['case_id'], status=result['status'], seconds=result['seconds'],
                              branch_count=len(result.get('answer', {}).get('branches', []))), ensure_ascii=False), flush=True)
    if reused:
        write(out / 'results.json', sorted(results, key=lambda r: r['case_id']))
    write(out / 'status.json', dict(phase='complete' if all(r['status'] == 'ok' for r in results) else 'complete_with_errors',
          total=len(manifest['cases']), completed=len(results), valid=sum(r['status'] == 'ok' for r in results),
          reused=len(reused), newly_completed=len(results)-len(reused), updated_at=now(), service_retained=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--version', choices=('v001', 'v001.1'), default='v001')
    parser.add_argument('--cases', nargs='+', help='Ordered v006 case IDs.')
    parser.add_argument('--continue-from', type=Path,
                        help='Review all v006 rollback targets, reusing matching valid results from this run.')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    if args.cases and (args.continue_from or len(set(args.cases)) != len(args.cases)):
        parser.error('--cases requires distinct IDs and cannot be combined with --continue-from')
    spec = SPEC.parent / ('branch_review_' + args.version)
    manifest = prepare(out, args.continue_from.resolve() if args.continue_from else None, spec, args.cases)
    if args.execute:
        try:
            run(out, manifest)
        except BaseException as exc:
            state = read(out / 'status.json')
            state.update(phase='failed', error=f'{type(exc).__name__}: {exc}', updated_at=now(), service_retained=True)
            write(out / 'status.json', state)
            raise


if __name__ == '__main__':
    main()
