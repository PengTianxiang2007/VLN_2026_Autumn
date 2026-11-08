"""Review an immutable snapshot of processed prefixes; never score unfinished cases.

Reconstruct each request using the run's frozen source and verify its hash, RGB crop,
past actions and visual memory. Only already processed RGB is included in the HTML.
This evaluator has access to maps; neither the inference logs nor the run are changed.
"""
import argparse
import base64
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_records(path):
    if not path.exists():
        return []
    # A live worker may be appending the final line. Never consume a partial write.
    lines = path.read_bytes().splitlines(keepends=True)
    return [json.loads(line) for line in lines if line.endswith(b'\n')]


def frozen_core(run, manifest):
    path = run / 'source/core/crossing_checkpoint.py'
    if digest(path) != manifest['code_hashes']['core/crossing_checkpoint.py']:
        raise ValueError('Frozen detector source hash differs from manifest')
    spec = importlib.util.spec_from_file_location('crossing_preview_frozen_core', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prefix_case(episode, source, private, records, core, inference, crossings):
    import cv2
    cv2.setNumThreads(1)
    stride = inference.get('inference_stride', 1)
    if type(stride) is not int or stride < 1:
        raise ValueError('Invalid inference stride')
    all_valid = [o['frame'] for o in source['observations'] if not o['terminal'] and not o['rgb_reused']]
    valid = [frame for frame in all_valid if frame % stride == 0]
    frames = [r['frame'] for r in records]
    if frames != valid[:len(frames)]:
        raise ValueError(f'{episode}: predictions are not a complete causal prefix')
    result = dict(episode_id=episode, scene=private['scene'], instruction=private['instruction'],
                  source_success=private['success'], expected=len(valid), processed=len(records),
                  last_frame=frames[-1] if frames else None, snapshots=[], steps=[])
    if not records:
        return result
    if stride > 1:
        result['history_images'] = {}
    # A complete sparse replay still displays the complete observed trajectory.
    last_frame = all_valid[-1] if stride > 1 and len(frames) == len(valid) else frames[-1]
    if digest(Path(source['video'])) != source['source_video_sha256']:
        raise ValueError(f'{episode}: source video hash changed')
    capture = cv2.VideoCapture(source['video'])
    shape = (int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    if not capture.isOpened() or shape != (960, 640):
        raise ValueError('Unexpected RGB source layout')
    tracker = core.CheckpointTracker()
    images, executed = [], []
    by_frame = {r['frame']: r for r in records}
    positions = {s['frame']: s.get('position') for s in private['steps']}
    try:
        for obs in source['observations']:
            frame = obs['frame']
            if frame > last_frame:
                break
            ok, composite = capture.read()
            if not ok:
                raise ValueError('Video ended before its observed prefix')
            result['steps'].append(dict(frame=frame, position=positions[frame]))
            if obs['terminal']:
                continue
            if not obs['rgb_reused']:
                rgb = composite[:480, :640].copy()
                ok, png = cv2.imencode('.png', rgb)
                if not ok:
                    raise ValueError('RGB encoding failed')
                raw = png.tobytes()
                images.append(dict(frame=frame, sha256=hashlib.sha256(raw).hexdigest(),
                                   data_url='data:image/png;base64,' + base64.b64encode(raw).decode()))
                images = images[-8:]
                if stride > 1:
                    ok, jpeg = cv2.imencode('.jpg', rgb, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if not ok:
                        raise ValueError('History image encoding failed')
                    result['history_images'][str(frame)] = 'data:image/jpeg;base64,' + base64.b64encode(jpeg).decode()
                if frame not in by_frame:
                    executed.append(dict(index=frame, name=core.action_name(obs['action'])))
                    continue
                record = by_frame[frame]
                ids = [im['frame'] for im in images]
                if record['image_frames'] != ids or record['image_sha256'] != [im['sha256'] for im in images]:
                    raise ValueError(f'{episode}:{frame}: RGB/history mismatch')
                if record['executed_actions'] != executed[-32:]:
                    raise ValueError(f'{episode}:{frame}: executed actions mismatch')
                payload = dict(model=inference['served_model'],
                    messages=core.build_messages(images, executed[-32:], tracker.prompt_memory()),
                    temperature=0.0,
                    seed=int(hashlib.sha256(f'{episode}:{frame}:20261103'.encode()).hexdigest()[:8], 16) & 0x7fffffff,
                    max_tokens=inference['max_tokens'],
                    response_format={'type': 'json_schema', 'json_schema': {
                        'name': 'crossing_observation', 'strict': True,
                        'schema': core.response_schema(ids) if hasattr(core, 'response_schema') else core.RESPONSE_SCHEMA}})
                if 'chat_template_kwargs' in inference:
                    payload['chat_template_kwargs'] = inference['chat_template_kwargs']
                elif inference.get('thinking'):
                    payload['chat_template_kwargs'] = {'enable_thinking': True}
                if core.canonical_hash(payload) != record['request_sha256']:
                    raise ValueError(f'{episode}:{frame}: reconstructed causal request mismatch')
                prediction = core.validate_response(record['prediction'], ids)
                tracker.update(frame, prediction)
                # Do not finish() a partial trajectory or use a later description at an earlier frame.
                events = copy.deepcopy(tracker.events + ([tracker.active] if tracker.active else []))
                for event in events:
                    anchor = event['confirmation_frame']
                    if anchor is not None and positions.get(anchor) is not None:
                        nearest = min(crossings, key=lambda c: math.dist(positions[anchor][:2], c['position']))
                        event['map_reference_only'] = dict(crossing_id=nearest['id'],
                            distance_m=math.dist(positions[anchor][:2], nearest['position']))
                ok, jpeg = cv2.imencode('.jpg', rgb, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not ok:
                    raise ValueError('Preview image encoding failed')
                result['snapshots'].append(dict(frame=frame, prediction=prediction, events=events,
                    image='data:image/jpeg;base64,' + base64.b64encode(jpeg).decode(),
                    image_frames=ids, executed_actions=record['executed_actions'],
                    request_sha256=record['request_sha256'], elapsed_seconds=record['elapsed_seconds'],
                    created_at=record['created_at']))
            executed.append(dict(index=frame, name=core.action_name(obs['action'])))
    finally:
        capture.release()
    return result


def build(output, tag):
    run = output / 'runs' / tag
    manifest = read_json(run / 'manifest.json')
    protocol = read_json(output / 'protocol.json')
    if digest(output / 'protocol.json') != manifest['protocol_sha256']:
        raise ValueError('Protocol changed')
    if digest(output / 'inputs.json') != manifest['source_sha256']:
        raise ValueError('Input manifest changed')
    core = frozen_core(run, manifest)
    maps = read_json(output / 'evaluation/maps.json')
    if core.canonical_hash(maps) != protocol['fixed_reference_sha256']:
        raise ValueError('Fixed map reference changed')
    inputs = read_json(output / 'inputs.json')
    private = read_json(output / 'evaluation/cases.json')
    cases = {}
    for episode in manifest['episodes']:
        records = load_records(run / 'cases' / episode / 'predictions.jsonl')
        c = prefix_case(episode, inputs[episode], private[episode], records, core,
                        manifest['inference'], maps[private[episode]['scene']]['crossings'])
        final = run / 'cases' / episode / 'result.json'
        c['complete'] = bool(final.exists() and read_json(final).get('complete') and c['processed'] == c['expected'])
        status = run / 'cases' / episode / 'status.json'
        c['phase'] = read_json(status).get('phase', 'unknown') if status.exists() else 'queued'
        cases[episode] = c
    timestamp = datetime.now(timezone.utc).isoformat()
    summary = dict(created_at=timestamp, tag=tag, split=manifest['split'],
        processed=sum(c['processed'] for c in cases.values()), expected=sum(c['expected'] for c in cases.values()),
        completed_cases=sum(c['complete'] for c in cases.values()), expected_cases=len(cases),
        confirmed=sum(sum(e['confirmation_frame'] is not None for e in c['snapshots'][-1]['events'])
                      for c in cases.values() if c['snapshots']),
        verified_causal_requests=sum(c['processed'] for c in cases.values()),
        scoring='Not scored: snapshot of processed prefixes, not a final evaluation.',
        model=Path(manifest['model_path']).name, backend=manifest['inference_backend'],
        run_phase=read_json(run / 'status.json').get('phase') if (run / 'status.json').exists() else 'running')
    data = dict(tag=tag, summary=summary, cases=cases,
                maps={scene: maps[scene] for scene in {c['scene'] for c in cases.values()}})
    dest = output / 'reports' / (tag + '_preview')
    dest.mkdir(parents=True, exist_ok=True)
    template = (ROOT / 'core/crossing_checkpoint_preview.html').read_text()
    encoded = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    temp = dest / 'index.html.tmp'
    temp.write_text(template.replace('__DATA__', encoded))
    temp.replace(dest / 'index.html')
    (dest / 'snapshot.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(report=str(dest / 'index.html'), **summary), ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    build(args.output, args.tag)
