"""Prepare ten recorded route-choice samples on CPU; never calls any model."""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import (build_messages, file_hash, now, read, select_evenly,
                                     validate_case, write)

EXPERIMENT = ROOT / 'experiments/agent_route_choice/v001'
SOURCE_FILES = [
    'core/agent_route_choice.py', 'core/agent_route_choice_review.js', 'core/agent_route_choice_page.html',
    'core/crossing_campaign_template.html', 'core/crossing_visualization_template.json',
    'core/crossing_checkpoint.py',
    'scripts/prepare_agent_route_choice.py', 'scripts/run_agent_route_choice.py',
    'scripts/report_agent_route_choice.py', 'scripts/export_agent_route_choice.py',
    'scripts/run_crossing_local_batch.py', 'scripts/test_crossing_single_gpu.py',
    'scripts/serve_crossing_vlm.py', 'tests/test_agent_route_choice.py',
    'scripts/check_agent_route_choice.cjs',
]


def action_name(row):
    action = row['action']
    code = 0 if 'stop' in action else (action.get('move_by_discrete') or action.get('move_by_flash') or [-1])[0]
    if code not in (-1, 0, 1, 2, 3):
        raise ValueError('Unknown recorded action')
    return {-1: 'WAIT', 0: 'STOP', 1: 'FORWARD', 2: 'LEFT', 3: 'RIGHT'}[code]


def choose_rows(rows, case, protocol):
    cp = int(case['review']['decision_frame'])
    end = int(case['review']['highlight_end_frame'])
    frames = [r['frame'] for r in rows]
    if frames != list(range(len(rows))):
        raise ValueError('Video log must have contiguous frame indices')
    valid = [r for r in rows if not r['terminal'] and not r['rgb_reused']]
    before = [r for r in valid if r['frame'] <= cp]
    after = [r for r in valid if cp < r['frame'] <= end]
    if not before or before[-1]['frame'] != cp or not after:
        raise ValueError('Missing genuine checkpoint or later wrong-attempt image')
    context = select_evenly(before[-protocol['context_window_observations']:], protocol['checkpoint_context_images'])
    attempt = select_evenly(after, protocol['wrong_attempt_images'])
    return context, attempt


def prepare(output):
    import cv2
    cv2.setNumThreads(1)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    write(output / 'status.json', {'phase': 'preparing_inputs_only', 'model_calls': 0, 'created_at': now()})
    protocol = read(EXPERIMENT / 'protocol.json')
    cohort = read(EXPERIMENT / 'cohort.json')
    source = ROOT / protocol['cohort_manifest']
    manifest = read(source)
    if [c['episode_id'] for c in manifest['cases']] != cohort['episode_ids']:
        raise ValueError('Historical ten-case cohort changed')
    cases, labels, audit, sources = [], [], [], []
    for number, original in enumerate(manifest['cases'], 1):
        sid = 'sample_%02d' % number
        steps, video = Path(original['source_steps']), Path(original['source_video'])
        if file_hash(steps) != original['source_steps_sha256']:
            raise ValueError('Historical steps changed: ' + original['episode_id'])
        rows = [json.loads(line) for line in steps.read_text().splitlines()]
        context, attempt = choose_rows(rows, original, protocol)
        selected = context + attempt
        cp, end = context[-1]['frame'], attempt[-1]['frame']
        images = []
        cap = cv2.VideoCapture(str(video))
        try:
            if not cap.isOpened() or [int(cap.get(3)), int(cap.get(4))] != protocol['expected_video_size']:
                raise ValueError('Unexpected composite video layout; refusing unsafe crop')
            wanted = {r['frame'] for r in selected}
            for frame in range(end + 1):
                ok, composite = cap.read()
                if not ok:
                    raise ValueError('Video ended before selected observation')
                if frame not in wanted:
                    continue
                crop = composite[:480, :640].copy()
                if crop.shape != (480, 640, 3):
                    raise ValueError('Invalid RGB crop')
                relative = 'images/%s/F%04d.png' % (sid, frame)
                dest = output / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not cv2.imwrite(str(dest), crop):
                    raise ValueError('Failed to write prepared RGB')
                images.append({'id': 'F%04d' % frame, 'frame': frame,
                               'phase': 'checkpoint_context' if frame <= cp else 'wrong_attempt',
                               'path': relative, 'sha256': file_hash(dest)})
        finally:
            cap.release()
        case = {'sample_id': sid, 'instruction': original['instruction'],
                'checkpoint_frame': cp, 'wrong_end_frame': end, 'images': images,
                'approach_actions': [{'frame': r['frame'], 'action': action_name(r)} for r in rows
                                     if max(0, cp - protocol['approach_action_limit']) <= r['frame'] < cp],
                'attempt_actions': [{'frame': r['frame'], 'action': action_name(r)} for r in rows if cp <= r['frame'] < end]}
        validate_case(case)
        cases.append(case)
        # Evaluation-only information never enters dataset.json or message construction.
        labels.append({'sample_id': sid, 'episode_id': original['episode_id'], 'scene': original['scene'],
                       'crossing_id': original['crossing_id'], 'crossing': original['crossing'],
                       'expected_route': original['review']['expected'], 'wrong_route': original['review']['actual'],
                       'historical_rationale': original['review']['rationale'],
                       'label_status': 'prior_assistant_review_with_map_and_RGB_not_independent_human_gold',
                       'reference_path': original['reference_path'],
                       'trajectory': [{'frame': r['frame'], 'position': r['position']} for r in rows if r['frame'] <= end],
                       'checkpoint_position': rows[cp]['position']})
        row = {'sample_id': sid, 'episode_id': original['episode_id'], 'checkpoint_frame': cp,
               'wrong_end_frame': end, 'marked_wrong_end_frame': int(original['review']['highlight_end_frame']),
               'checkpoint_distance_to_marked_crossing_m': math.dist(rows[cp]['position'][:2], original['crossing']['position']),
               'call1_frames': [r['frame'] for r in context], 'call2_frames': [r['frame'] for r in selected],
               'images_verified': len(images), 'model_calls': 0}
        audit.append(row)
        sources.append({'sample_id': sid, 'steps': str(steps), 'steps_sha256': file_hash(steps),
                        'video': str(video), 'video_sha256': file_hash(video)})
        print(json.dumps(row, ensure_ascii=False), flush=True)
    write(output / 'dataset.json', {'schema': 1, 'cases': cases})
    write(output / 'evaluation_only.json', {'labels': labels, 'request_access': 'forbidden; review/export only'})
    write(output / 'input_audit.json', {'cases': audit, 'total_cases': len(cases), 'model_calls': 0,
                                       'physical_restore_performed': False, 'original_run_seed': 2})
    write(output / 'provenance.json', {'cohort_manifest': str(source), 'cohort_manifest_sha256': file_hash(source),
                                      'sources': sources, 'historical_source_version': 'Use source campaign manifests; current HEAD is preparation code only.'})
    for name in ['protocol.json', 'models.json', 'cohort.json']:
        shutil.copy2(EXPERIMENT / name, output / name)
    shutil.copytree(EXPERIMENT / 'prompts', output / 'prompts')
    for case in cases:
        preview = build_messages(case, output, 1, (output / 'prompts/01_inventory_en.txt').read_text(), embed_images=False)
        write(output / 'request_previews' / (case['sample_id'] + '_call1.json'), preview)
    write(output / 'request_previews/call2_contract.json', {
        'status': 'not_built_until_real_same_model_call1_answer_exists',
        'system_prompt': (output / 'prompts/02_choose_en.txt').read_text(),
        'roles': ['system', 'user'], 'instruction': 'from dataset.json',
        'branch_inventory': 'validated actual answer of the same model; no fabricated inventory',
        'images': 'checkpoint context plus recorded wrong attempt; max eight',
        'hidden_conversation_memory': False})
    hashes = {}
    for name in SOURCE_FILES:
        path = ROOT / name
        hashes[name] = file_hash(path)
        frozen = output / 'source' / name
        frozen.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, frozen)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    (output / 'workspace_status.txt').write_text(subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True))
    (output / 'workspace_diff.patch').write_bytes(subprocess.check_output(['git', 'diff', 'HEAD'], cwd=ROOT))
    names = ['dataset.json', 'evaluation_only.json', 'input_audit.json', 'provenance.json', 'protocol.json', 'models.json', 'cohort.json']
    names += ['prompts/' + p.name for p in sorted((output / 'prompts').iterdir())]
    write(output / 'manifest.json', {'schema': 1, 'created_at': now(), 'preparation_git_head': head,
                                    'code_sha256': hashes, 'files_sha256': {n: file_hash(output / n) for n in names},
                                    'source_note': 'Frozen uncommitted source included; HEAD alone is insufficient.'})
    subprocess.run([str(ROOT / 'backbone/streamvln/.venv/bin/python'), '-B',
                    str(ROOT / 'scripts/export_agent_route_choice.py'), '--prepared', str(output),
                    '--destination', str(output / 'input_review.html')], check=True, timeout=600)
    write(output / 'status.json', {'phase': 'prepared_waiting_for_user_start', 'prepared_at': now(),
                                   'ready_samples': len(cases), 'model_calls': 0, 'models_started': [],
                                   'planned_calls_per_model': 20, 'planned_calls_total': 40})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New preparation directory; old data is never overwritten')
    args = parser.parse_args()
    prepare(args.output)


if __name__ == '__main__':
    main()
