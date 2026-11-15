"""Run an original-protocol crossing-lite prompt panel on selected frames."""
import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import now, read, write
from core.crossing_lite import digest, request, request_seed, sha, validate, windows

DATASET = ROOT / 'outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001'
SERVICE = ROOT / 'outputs/model_services/qwen4b_gpu0_20261108_01/service.json'


def build_panel(baseline):
    selected = read(baseline / 'evaluation_selection.json')
    episode_ids = [row['episode_id'] for row in selected]
    predictions = read(baseline / 'baseline_predictions.json')
    selected_set = set(episode_ids)
    events = [
        row for row in map(json.loads, (DATASET / 'evaluation/events.jsonl').read_text().splitlines())
        if row['episode_id'] in selected_set
    ]
    by_episode = {}
    for event in events:
        by_episode.setdefault(event['episode_id'], set()).add(event['frame'])

    cases = []
    seen = set()
    for event in events:
        key = (event['episode_id'], event['frame'])
        if key not in seen:
            cases.append(dict(episode_id=key[0], frame=key[1], role='annotation'))
            seen.add(key)
    for episode_id in episode_ids:
        event_frames = by_episode.get(episode_id, set())
        candidates = []
        for frame_text, row in predictions[episode_id].items():
            frame = int(frame_text)
            if row['score'] != 1:
                continue
            v002 = read(baseline / 'cases' / episode_id / ('F%04d.response.json' % frame))
            if v002['answer']['score'] != 1:
                continue
            if event_frames and min(abs(frame - event) for event in event_frames) < 15:
                continue
            candidates.append(frame)
        if candidates:
            frame = candidates[len(candidates) // 2]
            key = (episode_id, frame)
            if key not in seen:
                cases.append(dict(episode_id=episode_id, frame=frame, role='stability_control'))
                seen.add(key)
    for frame in (58, 96):
        key = ('kujiale_0207_14_4', frame)
        if key not in seen:
            cases.append(dict(episode_id=key[0], frame=frame, role='user_target'))
            seen.add(key)
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--prompt', required=True, type=Path)
    parser.add_argument('--prompt-addendum', required=True, type=Path)
    parser.add_argument('--baseline-run', required=True, type=Path)
    parser.add_argument('--candidate-label', required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise ValueError('Use a new output directory')
    baseline = args.baseline_run.resolve()
    prompt_path = args.prompt.resolve()
    addendum_path = args.prompt_addendum.resolve()
    prompt = prompt_path.read_text().rstrip() + '\n\n' + addendum_path.read_text().strip() + '\n'
    service = read(SERVICE)
    if service.get('phase') != 'ready':
        raise RuntimeError('Retained Qwen4B service is not ready')
    episodes = {
        row['episode_id']: row
        for row in map(json.loads, (DATASET / 'inputs/episodes.jsonl').read_text().splitlines())
    }
    cases = build_panel(baseline)
    baseline_predictions = read(baseline / 'baseline_predictions.json')
    out.mkdir(parents=True)
    for rel in ('scripts/run_crossing_lite_prompt_panel.py', 'core/crossing_lite.py'):
        destination = out / 'source' / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, destination)
    shutil.copy2(prompt_path, out / 'source/prompt_en.txt')
    shutil.copy2(addendum_path, out / 'source/prompt_addendum_en.txt')
    (out / 'prompt_effective_en.txt').write_text(prompt)
    (out / 'workspace_status.txt').write_text(
        subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True)
    )
    (out / 'tracked_worktree.diff').write_bytes(
        subprocess.check_output(['git', 'diff', '--binary'], cwd=ROOT)
    )
    write(out / 'panel.json', dict(cases=cases, counts=dict(Counter(row['role'] for row in cases))))
    write(out / 'manifest.json', dict(
        created_at=now(),
        git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        prompt=str(prompt_path),
        prompt_addendum=str(addendum_path),
        prompt_sha256=sha(prompt_path),
        prompt_addendum_sha256=sha(addendum_path),
        effective_prompt_sha256=sha(out / 'prompt_effective_en.txt'),
        baseline_run=str(baseline),
        service=service['base_url'],
        model=service['model'],
        protocol='Original three-frame Crossing-lite request; no instruction, action, map, label, or history answer in model input.',
        seed_base=20261107,
    ))
    write(out / 'status.json', dict(phase='running', started_at=now(), completed=0, total=len(cases)))

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(service['base_url'] + '/models', timeout=10) as response:
        models = json.load(response)
    assert any(row['id'] == service['model'] for row in models['data'])

    rows = []
    for index, case in enumerate(cases, 1):
        episode_id, frame = case['episode_id'], case['frame']
        episode = episodes[episode_id]
        observations = read(DATASET / episode['observations'])
        images = None
        for current, current_images in windows(observations):
            if current == frame:
                images = current_images
                break
        if images is None:
            raise ValueError('Ineligible frame: %s F%d' % (episode_id, frame))
        seed = request_seed(episode_id, frame, 20261107)
        wire = request(prompt, images, DATASET, service['model'], seed)
        preview = request(prompt, images, DATASET, service['model'], seed, embed=False)
        prefix = out / 'cases' / episode_id / ('F%04d' % frame)
        prefix.parent.mkdir(parents=True, exist_ok=True)
        write(prefix.with_suffix('.request.json'), dict(
            frame=frame,
            image_frames=[row['frame'] for row in images],
            images=images,
            request_sha256=digest(wire),
            preview=preview,
        ))
        started = time.monotonic()
        req = urllib.request.Request(
            service['base_url'] + '/chat/completions',
            data=json.dumps(wire).encode(),
            headers={'Content-Type': 'application/json'},
        )
        with opener.open(req, timeout=180) as response:
            raw = json.load(response)
        choice = raw['choices'][0]
        if choice['finish_reason'] != 'stop':
            raise ValueError('Non-stop finish reason: ' + str(choice['finish_reason']))
        answer = validate(json.loads(choice['message']['content']))
        baseline_answer = baseline_predictions[episode_id][str(frame)]['answer']
        v002_answer = read(baseline / 'cases' / episode_id / ('F%04d.response.json' % frame))['answer']
        record = dict(
            **case,
            image_frames=[row['frame'] for row in images],
            seed=seed,
            baseline_best=baseline_answer,
            lite_v002=v002_answer,
            candidate=answer,
            latency_seconds=time.monotonic() - started,
        )
        write(prefix.with_suffix('.response.json'), dict(raw=raw, answer=answer, record=record))
        rows.append(record)
        write(out / 'status.json', dict(phase='running', updated_at=now(), completed=index, total=len(cases)))

    summary = dict(
        total=len(rows),
        by_role={},
        candidate_histogram=dict(Counter(row['candidate']['score'] for row in rows)),
        baseline_histogram=dict(Counter(row['baseline_best']['score'] for row in rows)),
        v002_histogram=dict(Counter(row['lite_v002']['score'] for row in rows)),
        candidate_above_baseline=sum(row['candidate']['score'] > row['baseline_best']['score'] for row in rows),
        candidate_below_baseline=sum(row['candidate']['score'] < row['baseline_best']['score'] for row in rows),
    )
    for role in sorted({row['role'] for row in rows}):
        subset = [row for row in rows if row['role'] == role]
        summary['by_role'][role] = dict(
            total=len(subset),
            candidate_histogram=dict(Counter(row['candidate']['score'] for row in subset)),
            baseline_histogram=dict(Counter(row['baseline_best']['score'] for row in subset)),
            above=sum(row['candidate']['score'] > row['baseline_best']['score'] for row in subset),
            below=sum(row['candidate']['score'] < row['baseline_best']['score'] for row in subset),
        )
    write(out / 'summary.json', summary)
    write(out / 'status.json', dict(phase='complete', finished_at=now(), completed=len(rows), total=len(cases)))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
