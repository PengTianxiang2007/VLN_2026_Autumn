"""Prepare, causally replay and score existing seed2 recordings. Never runs a simulator."""
import argparse
import base64
from collections import defaultdict, deque
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.crossing_checkpoint import (PROMPT_VERSION, SYSTEM_PROMPT, RESPONSE_SCHEMA,
    CheckpointTracker, action_name, build_messages, canonical_hash, evaluate_events,
    map_encounters, response_schema, select_history, validate_response)

DEFAULT = ROOT / 'outputs/crossing_checkpoint/seed2_v1_20261103'
SOURCE = ROOT / 'outputs/reproduction/streamvln_scene250_5seeds_20261101_v2/visualization'
PRIOR = ROOT / 'outputs/checkpoint_review/seed2_25_20261103'
DEV_SCENES = ['kujiale_0036', 'kujiale_0113', 'kujiale_0208', 'kujiale_0259']


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(4*1024*1024), b''):
            h.update(data)
    return h.hexdigest()


def prepare(output):
    if (output / 'protocol.json').exists():
        protocol = read_json(output / 'protocol.json')
        assert file_hash(PRIOR/'review_data.json') == protocol['source_map_report_sha256']
        print(json.dumps({'prepared_already': True, 'output': str(output)}))
        return
    selection = read_json(PRIOR / 'selection.json')
    review = read_json(PRIOR / 'review_data.json')
    rows = [json.loads(s) for s in (SOURCE/'index.jsonl').read_text().splitlines() if s.strip()]
    rows = {r['episode_id']: r for r in rows if r['seed'] == 2}
    accepted = {a['episode_id']: a for a in selection['screening'] if a['accepted']}
    dev = []
    for scene in DEV_SCENES:
        for outcome in [1, 0]:
            dev.append(next(c['episode_id'] for c in selection['cases']
                            if c['scene'] == scene and int(c['metrics']['success']) == outcome))
    groups = defaultdict(list)
    for episode, row in rows.items():
        if episode in accepted and row['scene'] not in DEV_SCENES:
            groups[(int(row['metrics']['success']), row['scene'])].append(episode)
    rng = random.Random(20261103)
    for values in groups.values():
        values.sort()
        rng.shuffle(values)
    validation = []
    for outcome in [1, 0]:
        picked = []
        while len(picked) < 20:
            before = len(picked)
            for key in sorted(groups):
                if key[0] == outcome and groups[key] and len(picked) < 20:
                    picked.append(groups[key].pop())
            if len(picked) == before:
                raise ValueError('Not enough screened held-out trajectories')
        validation.extend(picked)
    assert len(dev) == 8 and len(validation) == 40 and not set(dev) & set(validation)
    output.mkdir(parents=True, exist_ok=True)
    (output/'videos').mkdir(exist_ok=True)
    private, inputs = {}, {}
    for episode in dev + validation:
        row = rows[episode]
        detail = read_json(SOURCE / row['detail'])
        steps = [json.loads(s) for s in (SOURCE / row['steps']).read_text().splitlines() if s.strip()]
        assert [s['frame'] for s in steps] == list(range(len(steps)))
        assert len(steps) == detail['frames']
        source_video = SOURCE / row['video']
        # This input manifest intentionally omits positions, reference paths, maps and outcomes.
        inputs[episode] = dict(episode_id=episode, video=str(source_video),
            source_video_sha256=file_hash(source_video), fps=detail['fps'],
            observations=[{k:s[k] for k in ['frame','action_index','action','terminal','rgb_reused']} for s in steps])
        private[episode] = dict(episode_id=episode, scene=row['scene'], instruction=row['instruction'],
            success=int(row['metrics']['success']), fail_reason=row['fail_reason'], steps=steps,
            reference_path=detail['reference_path'], fps=detail['fps'], frames=detail['frames'],
            screening=accepted[episode], video=f'videos/{episode}.mp4',
            encounters=map_encounters(steps, review['scenes'][row['scene']]['crossings']))
    protocol = dict(schema=1, created_at=now(), seed=2, sample_seed=20261103,
        prompt_version=PROMPT_VERSION, model_selection='Compare local candidates on development trajectories only.',
        development=dev, validation=validation, development_scenes=DEV_SCENES,
        validation_scenes=sorted(set(private[e]['scene'] for e in validation)),
        source_index_sha256=file_hash(SOURCE/'index.jsonl'),
        source_map_report_sha256=file_hash(PRIOR/'review_data.json'),
        fixed_reference_sha256=canonical_hash(review['scenes']),
        source_screening_rule=selection['screening_rule'],
        input_policy='RGB only, native 640x480 crop; last 8 available observations; actions strictly before current observation; visual checkpoint memory. No map, GPS, reference path, outcome or future frames.',
        checkpoint_policy=dict(confirmations=2, window=3, close_after_absent=3,
                               anchor='confirmation_frame', future_backdating=False),
        evaluation=dict(reference='Previously marked 55 scene crossings; geometric prior, not independent human gold.',
                        entry_radius_m=.7, exit_radius_m=1.2, approach_radius_m=1.5,
                        primary_match_radius_m=1.0, sensitivity_radii_m=[.7,1.0,1.5],
                        matching='One prediction per encountered crossing visit; repeated detections penalized.',
                        timing='Actions relative to closest approach, not certified pre-choice timing.',
                        validation_gate=dict(precision=.85, recall=.80, duplicate_fraction=.10)))
    write_json(output/'inputs.json', inputs)
    write_json(output/'evaluation/cases.json', private)
    write_json(output/'evaluation/maps.json', review['scenes'])
    write_json(output/'protocol.json', protocol)
    print(json.dumps(dict(development=len(dev), validation=len(validation),
                          development_frames=sum(private[e]['frames'] for e in dev),
                          validation_frames=sum(private[e]['frames'] for e in validation),
                          development_encounters=sum(len(private[e]['encounters']) for e in dev),
                          validation_encounters=sum(len(private[e]['encounters']) for e in validation)), ensure_ascii=False))


def call_model(base_url, payload, timeout=600):
    # Local inference is never sent through an inherited proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    if not base_url.startswith('http://127.0.0.1:'):
        raise ValueError('Only a local vLLM service is allowed')
    request = urllib.request.Request(base_url+'/chat/completions',
        data=json.dumps(payload, ensure_ascii=False).encode(), headers={'Content-Type':'application/json'})
    try:
        with opener.open(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'vLLM HTTP {error.code}: {error.read(1500).decode(errors="replace")}') from error


def parse_answer(reply, image_ids):
    choice = reply['choices'][0]
    if choice['finish_reason'] != 'stop':
        raise ValueError('Incomplete generation: '+str(choice['finish_reason']))
    text = choice['message']['content']
    if not text:
        raise ValueError('Empty final answer')
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n',1)[1].rsplit('```',1)[0].strip()
    return validate_response(json.loads(text), image_ids)


def replay_one(job):
    import cv2
    cv2.setNumThreads(1)
    output, tag, episode, source, inference = job
    output = Path(output)
    directory = output/'runs'/tag/'cases'/episode
    directory.mkdir(parents=True, exist_ok=True)
    final_path = directory/'result.json'
    if final_path.exists() and read_json(final_path).get('complete'):
        return read_json(final_path)
    log_path = directory/'predictions.jsonl'
    old = [json.loads(line) for line in log_path.read_text().splitlines()] if log_path.exists() else []
    cached = {r['frame']:r for r in old}
    tracker = CheckpointTracker()
    images = deque(maxlen=8)
    executed = []
    capture = cv2.VideoCapture(source['video'])
    if not capture.isOpened():
        raise RuntimeError('Cannot open original video')
    if (int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))) != (960,640):
        raise ValueError('Unexpected composite frame layout; refusing unsafe RGB crop')
    current = -1
    calls = 0
    stride = inference.get('inference_stride', 1)
    if type(stride) is not int or stride < 1:
        raise ValueError('inference_stride must be a positive integer')
    expected = sum(not o['terminal'] and not o['rgb_reused'] and o['frame'] % stride == 0
                   for o in source['observations'])
    write_json(directory/'status.json',dict(phase='running',episode_id=episode,pid=os.getpid(),expected=expected,updated_at=now()))
    try:
        with log_path.open('a') as log, (directory/'attempts.jsonl').open('a') as attempts:
            for observation in source['observations']:
                ok, composite = capture.read()
                if not ok:
                    raise ValueError('Video ended before its step log')
                current = observation['frame']
                if observation['terminal']:
                    continue
                if observation['rgb_reused']:
                    executed.append(dict(index=current,name=action_name(observation['action'])))
                    continue
                rgb_bgr = composite[:480,:640].copy()
                ok, encoded = cv2.imencode('.png',rgb_bgr)
                if not ok:
                    raise ValueError('RGB encoding failed')
                raw = encoded.tobytes()
                images.append(dict(frame=current,sha256=hashlib.sha256(raw).hexdigest(),
                                   data_url='data:image/png;base64,'+base64.b64encode(raw).decode()))
                if current % stride:
                    # Keep every valid RGB and executed action; only skip the model request.
                    executed.append(dict(index=current,name=action_name(observation['action'])))
                    continue
                ids = select_history(current,[im['frame'] for im in images])
                messages = build_messages(list(images),executed[-32:],tracker.prompt_memory())
                assert messages[1]['content'][0]['text'].find('"current_observation": '+str(current)) >= 0
                seed = int(hashlib.sha256(f'{episode}:{current}:20261103'.encode()).hexdigest()[:8],16) & 0x7fffffff
                payload = dict(model=inference['served_model'],messages=messages,temperature=0.0,
                               seed=seed,max_tokens=inference['max_tokens'],
                               response_format={'type':'json_schema','json_schema':{
                                   'name':'crossing_observation','strict':True,'schema':response_schema(ids)}})
                # Omitting this setting enables thinking in the model's default template.
                payload['chat_template_kwargs']=inference['chat_template_kwargs']
                request_hash = canonical_hash(payload)
                if current in cached:
                    record = cached[current]
                    if record['request_sha256'] != request_hash:
                        raise ValueError('Resume request differs from saved causal history')
                    prediction = validate_response(record['prediction'],ids)
                else:
                    started = time.monotonic()
                    for attempt in range(2):
                        reply = None
                        try:
                            reply = call_model(inference['base_url'],payload)
                            prediction = parse_answer(reply,ids)
                            attempts.write(json.dumps(dict(frame=current,attempt=attempt,ok=True,
                                request_sha256=request_hash,reply=reply),ensure_ascii=False)+'\n')
                            attempts.flush()
                            break
                        except Exception as error:
                            attempts.write(json.dumps(dict(frame=current,attempt=attempt,ok=False,
                                request_sha256=request_hash,image_frames=ids,reply=reply,
                                error=type(error).__name__+': '+str(error)),ensure_ascii=False)+'\n')
                            attempts.flush()
                            if attempt==1:
                                raise
                            time.sleep(2)
                    record=dict(frame=current,image_frames=ids,image_sha256=[im['sha256'] for im in images],
                                executed_actions=executed[-32:],request_sha256=request_hash,
                                prediction=prediction,elapsed_seconds=time.monotonic()-started,
                                usage=reply.get('usage'),created_at=now())
                    log.write(json.dumps(record,ensure_ascii=False)+'\n');log.flush()
                emitted = tracker.update(current,prediction)
                if emitted:
                    evidence = directory/'evidence';evidence.mkdir(exist_ok=True)
                    (evidence/f'{emitted["id"]}_f{current:04d}.png').write_bytes(raw)
                    write_json(evidence/f'{emitted["id"]}_at_confirmation.json',emitted)
                calls += 1
                write_json(directory/'status.json',dict(phase='running',episode_id=episode,pid=os.getpid(),
                    frame=current,completed_observations=calls,expected=expected,updated_at=now(),
                    confirmed=sum(e['confirmation_frame'] is not None for e in tracker.events)+
                              int(tracker.active is not None and tracker.active['confirmation_frame'] is not None)))
                executed.append(dict(index=current,name=action_name(observation['action'])))
        if calls != expected:
            raise ValueError('Incomplete observation coverage')
        result=dict(episode_id=episode,complete=True,observations=calls,events=tracker.finish(),finished_at=now())
        write_json(final_path,result)
        write_json(directory/'status.json',dict(phase='complete',episode_id=episode,completed_observations=calls,expected=expected,updated_at=now()))
        return result
    except Exception as error:
        write_json(directory/'status.json',dict(phase='failed',episode_id=episode,frame=current,
                   completed_observations=calls,expected=expected,error=type(error).__name__+': '+str(error),updated_at=now()))
        raise
    finally:
        capture.release()


def run(args):
    protocol=read_json(args.output/'protocol.json')
    if args.split=='validation' and not (args.output/'selection_decision.json').exists():
        raise ValueError('Validation remains sealed until a development decision is saved')
    source=read_json(args.output/'inputs.json')
    service=read_json(args.service/'service.json')
    if service['phase']!='ready':
        raise ValueError('vLLM service is not ready')
    inference=dict(base_url=service['base_url'],served_model=service['served_model'],
                   max_tokens=args.max_tokens,thinking=args.thinking,
                   chat_template_kwargs={'enable_thinking':bool(args.thinking)})
    if args.inference_stride != 1:
        inference['inference_stride'] = args.inference_stride
    directory=args.output/'runs'/args.tag;directory.mkdir(parents=True,exist_ok=True)
    manifest=dict(schema=1,tag=args.tag,split=args.split,protocol_sha256=file_hash(args.output/'protocol.json'),
        source_sha256=file_hash(args.output/'inputs.json'),prompt_sha256=canonical_hash(SYSTEM_PROMPT),
        model_path=service['model_path'],quantization_override=service.get('quantization_override'),
        inference_backend=service.get('backend','vllm'),
        server_source_sha256=file_hash(ROOT/'scripts'/('serve_crossing_transformers.py'
            if service.get('backend')=='transformers' else 'serve_crossing_vlm.py')),
        dtype=service['dtype'],cpu_offload_gb=service['cpu_offload_gb'],
        model_config_sha256=file_hash(Path(service['model_path'])/'config.json'),
        model_download_manifest_sha256=file_hash(Path(service['model_path'])/'download_manifest.json'),
        environment_versions=service.get('environment_versions'),
        server_configuration=[value for i,value in enumerate(service['command'])
                              if value != '--port' and (i == 0 or service['command'][i-1] != '--port')],
        inference={k:v for k,v in inference.items() if k!='base_url'},episodes=protocol[args.split],
        code_hashes={name:file_hash(ROOT/name) for name in ['core/crossing_checkpoint.py','scripts/replay_crossing_checkpoint.py']})
    previous=directory/'manifest.json'
    if previous.exists() and read_json(previous)!=manifest:
        raise ValueError('Run tag is frozen; use a new tag for changed model/prompt/code')
    write_json(previous,manifest)
    for name in manifest['code_hashes']:
        target=directory/'source'/name;target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copy2(ROOT/name,target)
    episodes=protocol[args.split]
    if args.limit_cases:episodes=episodes[:args.limit_cases]
    jobs=[(str(args.output),args.tag,e,source[e],inference) for e in episodes]
    failures={}
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(replay_one,job):job[2] for job in jobs}
        for future in concurrent.futures.as_completed(futures):
            episode=futures[future]
            try:
                result=future.result()
                print(json.dumps(dict(episode_id=episode,complete=True,observations=result['observations'],
                                     events=len(result['events']))),flush=True)
            except Exception as error:
                failures[episode]=str(error)
                print(json.dumps(dict(episode_id=episode,complete=False,error=str(error))),flush=True)
            write_json(directory/'status.json',dict(phase='running',failures=failures,updated_at=now()))
    score(args.output,args.tag)
    if failures:raise SystemExit(1)


def score(output,tag):
    manifest=read_json(output/'runs'/tag/'manifest.json')
    cases=read_json(output/'evaluation/cases.json')
    protocol=read_json(output/'protocol.json')
    if canonical_hash(read_json(output/'evaluation/maps.json'))!=protocol['fixed_reference_sha256']:
        raise ValueError('Fixed map reference was modified')
    result={}
    for episode in manifest['episodes']:
        path=output/'runs'/tag/'cases'/episode/'result.json'
        if not path.exists() or not read_json(path).get('complete'):continue
        value=read_json(path)
        result[episode]=dict(events=value['events'],metrics={str(radius):evaluate_events(
            value['events'],cases[episode]['steps'],cases[episode]['encounters'],radius)
            for radius in protocol['evaluation']['sensitivity_radii_m']})
    totals={}
    for radius in protocol['evaluation']['sensitivity_radii_m']:
        metrics=[r['metrics'][str(radius)] for r in result.values()]
        t={key:sum(m[key] for m in metrics) for key in ['tp','fp','fn','confirmed_predictions','reference_encounters','duplicate_predictions']}
        t['precision']=t['tp']/(t['tp']+t['fp']) if t['tp']+t['fp'] else None
        t['recall']=t['tp']/(t['tp']+t['fn']) if t['tp']+t['fn'] else None
        t['f1']=2*t['tp']/(2*t['tp']+t['fp']+t['fn']) if 2*t['tp']+t['fp']+t['fn'] else None
        totals[str(radius)]=t
    summary=dict(tag=tag,split=manifest['split'],complete=len(result)==len(manifest['episodes']),
                 completed_cases=len(result),expected_cases=len(manifest['episodes']),metrics=totals,
                 interpretation='Map-proximity agreement; visibility and pre-choice timing require review.',updated_at=now())
    write_json(output/'runs'/tag/'scores.json',dict(summary=summary,cases=result))
    write_json(output/'runs'/tag/'status.json',dict(phase='complete' if summary['complete'] else 'incomplete',**summary))
    print(json.dumps(summary),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','run','score'])
    parser.add_argument('--output',type=Path,default=DEFAULT)
    parser.add_argument('--tag',default='qwen32_bf16_dev_v1')
    parser.add_argument('--split',choices=['development','validation'],default='development')
    parser.add_argument('--service',type=Path)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--max-tokens',type=int,default=2048)
    parser.add_argument('--thinking',action='store_true')
    parser.add_argument('--limit-cases',type=int,default=0)
    parser.add_argument('--inference-stride',type=int,default=1,
                        help='Call on navigation frames 0,N,2N,...; retain all RGB/action history')
    args=parser.parse_args()
    if not 1<=args.workers<=8:parser.error('workers must be 1..8')
    if args.inference_stride<1:parser.error('inference-stride must be positive')
    if args.command=='prepare':prepare(args.output)
    elif args.command=='run':
        if not args.service:parser.error('--service is required')
        run(args)
    else:score(args.output,args.tag)


if __name__=='__main__':
    main()
