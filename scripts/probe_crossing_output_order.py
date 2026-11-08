"""One development-only diagnostic request, outside all trajectory scores."""
import argparse
import base64
from collections import deque
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import time
import urllib.request


def read(path):
    return json.loads(path.read_text())


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--parent', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--episode', required=True)
    parser.add_argument('--frame', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.campaign.resolve()
    if args.episode not in read(root/'protocol.json')['development']:
        raise ValueError('Only frozen development inputs may be probed')
    if (root/'selection_decision.json').exists():
        raise ValueError('Development is already frozen')
    if any(not p.with_suffix('.done').exists() for p in (root/'queue').glob('*.json')):
        raise ValueError('Do not interleave with a trajectory replay')
    parent_path = root/'versions'/args.parent/'core/crossing_checkpoint.py'
    candidate_path = root/'versions'/args.candidate/'core/crossing_checkpoint.py'
    parent = module(parent_path, 'probe_parent')
    candidate = module(candidate_path, 'probe_candidate')
    case = root/'runs'/args.parent/'cases'/args.episode
    if not read(case/'result.json')['complete']:
        raise ValueError('Parent case is incomplete')
    records = {r['frame']: r for r in map(json.loads, (case/'predictions.jsonl').read_text().splitlines())}
    source = read(root/'inputs.json')[args.episode]
    service = read(Path(read(root/'session.json')['service'])/'service.json')
    import cv2
    cv2.setNumThreads(1)
    capture = cv2.VideoCapture(source['video'])
    if not capture.isOpened() or (int(capture.get(3)), int(capture.get(4))) != (960, 640):
        raise ValueError('Unexpected original recording')
    tracker = parent.CheckpointTracker()
    images = deque(maxlen=8)
    executed = []
    payload = None
    try:
        for obs in source['observations']:
            ok, composite = capture.read()
            if not ok:
                raise ValueError('Recording ended early')
            frame = obs['frame']
            if obs['terminal']:
                continue
            if not obs['rgb_reused']:
                ok, encoded = cv2.imencode('.png', composite[:480, :640].copy())
                if not ok:
                    raise ValueError('RGB encoding failed')
                raw = encoded.tobytes()
                images.append(dict(frame=frame, sha256=hashlib.sha256(raw).hexdigest(),
                                   data_url='data:image/png;base64,' + base64.b64encode(raw).decode()))
                if frame == args.frame:
                    ids = [im['frame'] for im in images]
                    payload = dict(model=service['served_model'], temperature=0.0, max_tokens=8192,
                        seed=int(hashlib.sha256(f'{args.episode}:{frame}:20261103'.encode()).hexdigest()[:8],16)&0x7fffffff,
                        messages=parent.build_messages(list(images), executed[-32:], tracker.prompt_memory()),
                        response_format={'type':'json_schema','json_schema':{'name':'crossing_observation',
                            'strict':True,'schema':parent.response_schema(ids)}},
                        chat_template_kwargs={'enable_thinking':False})
                    parent_hash = parent.canonical_hash(payload)
                    if parent_hash != records[frame]['request_sha256']:
                        raise ValueError('Reconstructed parent request differs from recorded causal input')
                    payload['messages'] = candidate.build_messages(list(images), executed[-32:], tracker.prompt_memory())
                    payload['response_format']['json_schema']['schema'] = candidate.response_schema(ids)
                    break
                tracker.update(frame, records[frame]['prediction'])
            executed.append(dict(index=frame, name=parent.action_name(obs['action'])))
    finally:
        capture.release()
    if payload is None:
        raise ValueError('Requested observation was not found')
    args.output.mkdir(parents=True, exist_ok=False)
    write(args.output/'request.json', payload)
    write(args.output/'provenance.json', dict(episode=args.episode, frame=args.frame,
        parent=args.parent, candidate=args.candidate, parent_request_sha256=parent_hash,
        candidate_request_sha256=candidate.canonical_hash(payload),
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (parent_path,candidate_path)},
        purpose='Diagnostic order check with the recorded parent memory; excluded from all method scores',
        created_at=datetime.now(timezone.utc).isoformat()))
    base = service['base_url']
    if not base.startswith('http://127.0.0.1:'):
        raise ValueError('Only the local inference service is allowed')
    request = urllib.request.Request(base+'/chat/completions', data=json.dumps(payload).encode(),
                                     headers={'Content-Type':'application/json'})
    begin = time.monotonic()
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=600) as response:
        reply = json.load(response)
    write(args.output/'reply.json', reply)
    choice = reply['choices'][0]
    if choice['finish_reason'] != 'stop':
        raise ValueError('Incomplete diagnostic generation')
    prediction = candidate.validate_response(json.loads(choice['message']['content']), ids)
    order = list(prediction)
    summary = dict(order=order, requested_order=list(candidate.response_schema(ids)['properties']),
                   status_last=order[-1]=='status', prediction=prediction, elapsed_seconds=time.monotonic()-begin)
    write(args.output/'summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False))
    if order != summary['requested_order']:
        raise ValueError('Output order did not follow the proposed schema')


if __name__ == '__main__':
    main()
