"""Run one Crossing-lite frame with a candidate prompt; no batch or navigation."""
import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import now, read, write
from core.crossing_lite import digest, request, request_seed, sha, validate, windows

DATASET = ROOT / 'outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001'
SERVICE = ROOT / 'outputs/model_services/qwen4b_gpu0_20261108_01/service.json'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--prompt', required=True, type=Path)
    parser.add_argument('--prompt-addendum', type=Path)
    parser.add_argument('--episode', required=True)
    parser.add_argument('--frame', required=True, type=int)
    parser.add_argument('--baseline-run', required=True, type=Path)
    parser.add_argument('--candidate-label', default='lite_v003')
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise ValueError('Use a new output directory')
    prompt_path = args.prompt.resolve()
    prompt = prompt_path.read_text()
    addendum_path = args.prompt_addendum.resolve() if args.prompt_addendum else None
    if addendum_path:
        prompt = prompt.rstrip() + '\n\n' + addendum_path.read_text().strip() + '\n'
    service = read(SERVICE)
    if service.get('phase') != 'ready':
        raise RuntimeError('Retained Qwen4B service is not ready')

    episodes = {
        row['episode_id']: row
        for row in map(json.loads, (DATASET / 'inputs/episodes.jsonl').read_text().splitlines())
    }
    episode = episodes[args.episode]
    observations = read(DATASET / episode['observations'])
    selected = None
    for frame, images in windows(observations):
        if frame == args.frame:
            selected = images
            break
    if selected is None:
        raise ValueError('Requested frame is not an eligible inference frame')

    baseline_run = args.baseline_run.resolve()
    name = 'F%04d' % args.frame
    v002_request = read(baseline_run / 'cases' / args.episode / (name + '.request.json'))
    v002_response = read(baseline_run / 'cases' / args.episode / (name + '.response.json'))
    assert v002_request['images'] == selected
    assert v002_request['image_frames'] == [row['frame'] for row in selected]

    seed = request_seed(args.episode, args.frame, 20261107)
    assert seed == v002_request['preview']['seed']
    wire = request(prompt, selected, DATASET, service['model'], seed)
    preview = request(prompt, selected, DATASET, service['model'], seed, embed=False)

    out.mkdir(parents=True)
    for rel in ('scripts/probe_crossing_lite_single.py', 'core/crossing_lite.py'):
        destination = out / 'source' / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, destination)
    shutil.copy2(prompt_path, out / 'source/prompt_en.txt')
    if addendum_path:
        shutil.copy2(addendum_path, out / 'source/prompt_addendum_en.txt')
    (out / 'prompt_effective_en.txt').write_text(prompt)
    (out / 'workspace_status.txt').write_text(
        subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True)
    )
    (out / 'tracked_worktree.diff').write_bytes(
        subprocess.check_output(['git', 'diff', '--binary'], cwd=ROOT)
    )
    write(out / 'manifest.json', dict(
        created_at=now(),
        git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        prompt=str(prompt_path),
        prompt_sha256=sha(prompt_path),
        prompt_addendum=str(addendum_path) if addendum_path else None,
        prompt_addendum_sha256=sha(addendum_path) if addendum_path else None,
        effective_prompt_sha256=sha(out / 'prompt_effective_en.txt'),
        dataset=str(DATASET),
        episode=args.episode,
        frame=args.frame,
        image_frames=[row['frame'] for row in selected],
        image_sha256=[row['rgb_sha256'] for row in selected],
        baseline_run=str(baseline_run),
        baseline_request_sha256=v002_request['request_sha256'],
        service=service['base_url'],
        model=service['model'],
        seed=seed,
    ))
    write(out / 'request.json', dict(
        frame=args.frame,
        image_frames=[row['frame'] for row in selected],
        images=selected,
        request_sha256=digest(wire),
        preview=preview,
    ))
    write(out / 'status.json', dict(phase='inference', started_at=now()))

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(service['base_url'] + '/models', timeout=10) as response:
        models = json.load(response)
    assert any(row['id'] == service['model'] for row in models['data'])

    started = time.monotonic()
    req = urllib.request.Request(
        service['base_url'] + '/chat/completions',
        data=json.dumps(wire).encode(),
        headers={'Content-Type': 'application/json'},
    )
    with opener.open(req, timeout=180) as response:
        raw = json.load(response)
    latency = time.monotonic() - started
    choice = raw['choices'][0]
    if choice['finish_reason'] != 'stop':
        raise ValueError('Non-stop finish reason: ' + str(choice['finish_reason']))
    answer = validate(json.loads(choice['message']['content']))

    baseline_answers = read(baseline_run / 'baseline_predictions.json')[args.episode][str(args.frame)]['answer']
    result = dict(
        phase='complete',
        finished_at=now(),
        answer=answer,
        latency_seconds=latency,
        comparison=dict(
            best_v001=baseline_answers,
            lite_v002=v002_response['answer'],
            **{args.candidate_label: answer},
        ),
        scope='Single diagnostic frame only; not a method improvement claim.',
    )
    write(out / 'response.json', dict(raw=raw, answer=answer, latency_seconds=latency, started_at=now()))
    write(out / 'result.json', result)
    write(out / 'status.json', dict(phase='complete', finished_at=result['finished_at']))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
