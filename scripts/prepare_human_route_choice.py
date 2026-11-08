"""Adapt frozen human wrong-choice events to the unchanged no-panorama v001 calls."""
import argparse
import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import build_messages, file_hash, now, read, validate_case, write
from scripts.prepare_agent_route_choice import action_name, choose_rows
from scripts.analyze_crossing_failures import short_segment

MORNING = ROOT / 'outputs/agent_route_choice/v001/preparation_20261106_04'
DATASET = ROOT / 'outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001'
SOURCES = ['core/agent_route_choice.py', 'scripts/prepare_agent_route_choice.py',
           'scripts/run_agent_route_choice.py', 'scripts/analyze_crossing_failures.py',
           'scripts/run_crossing_local_batch.py', 'scripts/test_crossing_single_gpu.py',
           'scripts/serve_crossing_vlm.py', 'core/crossing_checkpoint.py',
           'scripts/prepare_human_route_choice.py', 'scripts/run_human_route_choice.py',
           'tests/test_human_route_choice.py']


def function_ast(path, name):
    tree = ast.parse(Path(path).read_text())
    return ast.dump(next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name), include_attributes=False)


def build_case(event, episode, observations, trajectory, protocol, sid):
    """Positions only select the same 1.2m source interval used by morning v001."""
    cp = event['frame']
    if [f['frame'] for f in observations] != list(range(len(observations))):
        raise ValueError('Noncontiguous source observations')
    frames = trajectory['frames']
    if [f['frame'] for f in frames] != list(range(len(frames))) or len(frames) != len(observations):
        raise ValueError('Trajectory and image indices disagree')
    if not observations[cp]['eligible_for_inference']:
        raise ValueError('Human checkpoint is not a genuine observation')
    segment = short_segment(frames, cp, length=1.2)
    # The human point replaces the old decision frame. No snapping or reuse of a
    # different historical error's endpoint; only the original endpoint rule remains.
    context, attempt = choose_rows(observations, {'review': {
        'decision_frame': cp, 'highlight_end_frame': segment['end_frame']}}, protocol)
    end = attempt[-1]['frame']
    executed = {}
    for obs in observations:
        if obs['frame'] > end:
            break
        for action in obs['newly_executed_actions']:
            if action['frame'] >= obs['frame']:
                raise ValueError('Unexecuted action in source input')
            if action['frame'] in executed:
                raise ValueError('Duplicate executed action')
            executed[action['frame']] = action_name(action)
    case = dict(sample_id=sid, instruction=episode['instruction'], checkpoint_frame=cp,
                wrong_end_frame=end, images=[],
                approach_actions=[dict(frame=f, action=a) for f, a in sorted(executed.items())
                                  if max(0, cp - protocol['approach_action_limit']) <= f < cp],
                attempt_actions=[dict(frame=f, action=a) for f, a in sorted(executed.items()) if cp <= f < end])
    audit = dict(sample_id=sid, event_id=event['id'], episode_id=event['episode_id'],
                 checkpoint_frame=cp, wrong_end_frame=end, source_segment_end_frame=segment['end_frame'],
                 source_segment_length_m=segment['length_m'],
                 call1_frames=[f['frame'] for f in context], call2_frames=[f['frame'] for f in context + attempt],
                 no_precheckpoint_history=(cp == 0), endpoint_rule='original short_segment(length=1.2)',
                 wrong_choice_source='user annotation; not inferred from final outcome',
                 semantic_visibility='not certified; model may abstain if local evidence is insufficient')
    return case, context + attempt, audit


def verify(prepared):
    prepared = Path(prepared)
    manifest = read(prepared / 'manifest.json')
    for rel, sha in manifest['files_sha256'].items():
        if file_hash(prepared / rel) != sha:
            raise ValueError('Frozen prepared file changed: ' + rel)
    for rel, sha in manifest['code_sha256'].items():
        if file_hash(ROOT / rel) != sha:
            raise ValueError('Prepared source changed: ' + rel)
    cases = read(prepared / 'dataset.json')['cases']
    cohort = read(prepared / 'cohort.json')
    if len(cases) != 34 or [c['sample_id'] for c in cases] != [e['sample_id'] for e in cohort['events']]:
        raise ValueError('Frozen human cohort changed')
    if len({e['event_id'] for e in cohort['events']}) != 34:
        raise ValueError('Missing or repeated human event')
    for case in cases:
        validate_case(case)
        for im in case['images']:
            if file_hash(prepared / im['path']) != im['sha256']:
                raise ValueError('Prepared RGB changed')
    return cases


def prepare(dataset, output):
    from PIL import Image
    dataset = dataset.resolve(); output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    write(output / 'status.json', dict(phase='preparing', model_calls=0, html_requested=False, started_at=now()))
    source_meta = read(dataset / 'dataset.json')
    if source_meta['dataset_id'] != 'crossing_seed2_human_v001-afb4e7868989415c':
        raise ValueError('Unexpected human dataset')
    original_protocol = read(MORNING / 'protocol.json')
    old_manifest = read(MORNING / 'manifest.json')
    if file_hash(ROOT / 'core/agent_route_choice.py') != old_manifest['code_sha256']['core/agent_route_choice.py']:
        raise ValueError('Morning request/schema/validation implementation changed')
    run_source = ROOT / 'scripts/run_agent_route_choice.py'
    unchanged = {}
    for name in ('run_case', 'call_model', 'read_stream'):
        unchanged[name] = function_ast(run_source, name) == function_ast(MORNING / 'source/scripts/run_agent_route_choice.py', name)
    if not unchanged['run_case'] or not unchanged['read_stream']:
        raise ValueError('Morning call execution or stream parsing changed')
    events = [json.loads(line) for line in (dataset / 'evaluation/events.jsonl').read_text().splitlines() if line]
    wrong = [e for e in events if e['wrong_choice_marked']]
    if len(wrong) != 34 or len({e['episode_id'] for e in wrong}) != 33:
        raise ValueError('Unexpected human wrong-choice cohort')
    episodes = {e['episode_id']: e for e in [json.loads(line) for line in (dataset / 'inputs/episodes.jsonl').read_text().splitlines() if line]}
    cases, audits, labels, image_checks = [], [], [], []
    source_files = {'dataset.json', 'inputs/episodes.jsonl', 'evaluation/events.jsonl'}
    for number, event in enumerate(wrong, 1):
        sid = 'sample_%02d' % number
        ep = episodes[event['episode_id']]
        tr_rel = 'evaluation/trajectories/%s.json' % event['episode_id']
        observations = read(dataset / ep['observations']); trajectory = read(dataset / tr_rel)
        source_files.update([ep['observations'], tr_rel])
        case, selected, audit = build_case(event, ep, observations, trajectory, original_protocol, sid)
        for frame in selected:
            src = dataset / frame['rgb']
            if file_hash(src) != frame['rgb_sha256']:
                raise ValueError('Human-visible source RGB changed')
            if frame['frame'] == event['frame'] and frame['rgb_sha256'] != event['image_sha256']:
                raise ValueError('Human point no longer matches its image')
            rel = 'images/%s/F%04d.png' % (sid, frame['frame'])
            dest = output / rel; dest.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(src) as im:
                rgb = im.convert('RGB')
                if rgb.size != (640, 480): raise ValueError('Unexpected human RGB dimensions')
                rgb.save(dest, format='PNG')
                with Image.open(dest) as decoded:
                    if decoded.tobytes() != rgb.tobytes(): raise ValueError('PNG conversion changed decoded pixels')
            case['images'].append(dict(id='F%04d' % frame['frame'], frame=frame['frame'],
                phase='checkpoint_context' if frame['frame'] <= case['checkpoint_frame'] else 'wrong_attempt',
                path=rel, sha256=file_hash(dest)))
            image_checks.append(dict(prepared=rel, source=frame['rgb'], source_sha256=frame['rgb_sha256'], decoded_pixels_equal=True))
            source_files.add(frame['rgb'])
        validate_case(case); cases.append(case); audits.append(audit)
        labels.append(dict(sample_id=sid, event=event, reference_path=trajectory['reference_path'],
                           semantic_review='pending; human event does not label the correct branch'))
        print(json.dumps(audit, ensure_ascii=False), flush=True)
    protocol = dict(original_protocol, protocol_id='agent-route-choice-v001-human34',
                    state='authorized_to_run_20261106_no_html', cohort_size=34,
                    cohort_manifest='cohort.json', checkpoint_selection='Exact human wrong-choice frame; no snapping',
                    error_endpoint='Original short_segment 1.2m arc-length rule, then last genuine RGB at or before its endpoint',
                    evaluation='Semantic branch correctness remains pending review; no automatic correct-route labels',
                    primary_metric='Pending semantic review; raw protocol completion is not accuracy',
                    html_requested=False, panoramas=False)
    model = read(MORNING / 'models.json')['qwen32b']
    model.update(model='route-choice-human34-qwen27b', model_path='/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/Qwen3.8-27B-FP8',
                 tensor_parallel_size=1, minimum_host_memory_gib=64, gpu_memory_utilization=0.75,
                 reasoning_parser='qwen3', batch_deadline_seconds=21600, max_images=8)
    model.pop('gpu', None)
    model_meta = read(Path(model['model_path']) / 'config.json')
    write(output / 'model.json', model)
    write(output / 'dataset.json', dict(schema='human-route-v001', cases=cases))
    write(output / 'cohort.json', dict(dataset_id=source_meta['dataset_id'], events=[
        {k:a[k] for k in ('sample_id','event_id','episode_id','checkpoint_frame','wrong_end_frame')} for a in audits]))
    write(output / 'protocol.json', protocol)
    write(output / 'evaluation_only.json', dict(labels=labels, request_access='forbidden'))
    write(output / 'input_audit.json', dict(cases=audits, images=image_checks, event_count=len(cases),
        episode_count=33, frame_zero_count=sum(a['no_precheckpoint_history'] for a in audits),
        frozen_morning_functions_unchanged=unchanged, model_calls=0, html_generated=False,
        transport_note='Current transport adds sanitized provider errors and HTTP429 Retry-After handling; request payload and sequential call semantics unchanged.',
        note='Short segment selection uses evaluation positions only offline; requests contain RGB/actions, with instruction only in call two.'))
    shutil.copytree(MORNING / 'prompts', output / 'prompts')
    for case in cases:
        write(output / 'request_previews' / (case['sample_id'] + '_call1.json'), build_messages(
            case, output, 1, (output / 'prompts/01_inventory_en.txt').read_text(), embed_images=False))
    write(output / 'provenance.json', dict(dataset=str(dataset), morning_prepared=str(MORNING),
        morning_manifest_sha256=file_hash(MORNING / 'manifest.json'),
        sources_sha256={p:file_hash(dataset / p) for p in sorted(source_files)},
        model_architecture=model_meta.get('architectures'), model_config_sha256=file_hash(Path(model['model_path'])/'config.json'),
        source_note='Human-visible WebP decoded losslessly to PNG for unchanged v001 image/png messages; no panorama or simulation.'))
    hashes = {}
    for rel in SOURCES:
        src = ROOT / rel; hashes[rel] = file_hash(src)
        dest = output / 'source' / rel; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dest)
    (output / 'workspace_status.txt').write_text(subprocess.check_output(['git','status','--short'], cwd=ROOT, text=True))
    (output / 'workspace_diff.patch').write_bytes(subprocess.check_output(['git','diff','HEAD'], cwd=ROOT))
    frozen = [str(p.relative_to(output)) for p in output.glob('*.json') if p.name not in ('status.json','manifest.json')]
    frozen += [str(p.relative_to(output)) for p in (output / 'prompts').iterdir() if p.is_file()]
    write(output / 'manifest.json', dict(created_at=now(), git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        files_sha256={p:file_hash(output/p) for p in frozen}, code_sha256=hashes, actual_uncommitted_sources_frozen=True))
    verify(output)
    write(output / 'status.json', dict(phase='prepared', samples=34, planned_calls=68, model_calls=0, html_generated=False, finished_at=now()))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', type=Path, default=DATASET); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); prepare(a.dataset, a.output)
