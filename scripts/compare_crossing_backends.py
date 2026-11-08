"""Reconstruct exact saved causal inputs for a separately recorded backend transition check."""
import argparse
import base64
from collections import deque
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from preview_crossing_checkpoint import frozen_core
from replay_crossing_checkpoint import read_json,write_json,file_hash,call_model,parse_answer,now


def main():
    import cv2
    cv2.setNumThreads(1)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source-tag',required=True)
    parser.add_argument('--service',type=Path,required=True)
    parser.add_argument('--count',type=int,default=5)
    parser.add_argument('--check-only',action='store_true',help='Verify source input hashes without any inference or result files')
    args=parser.parse_args()
    source_run=args.output/'runs'/args.source_tag
    manifest=read_json(source_run/'manifest.json')
    for filename,digest in manifest['code_hashes'].items():
        if file_hash(source_run/'source'/filename)!=digest:
            raise ValueError('Frozen source implementation differs from manifest')
    core=frozen_core(source_run,manifest)
    CheckpointTracker=core.CheckpointTracker;action_name=core.action_name
    build_messages=core.build_messages;canonical_hash=core.canonical_hash
    service=read_json(args.service/'service.json')
    if service['phase']!='ready':raise ValueError('Target service is not ready')
    if file_hash(Path(service['model_path'])/'download_manifest.json')!=manifest['model_download_manifest_sha256']:
        raise ValueError('Backend check must use identical checkpoint files')
    if args.count<1:raise ValueError('count must be positive')
    inputs=read_json(args.output/'inputs.json')
    episode=manifest['episodes'][0]
    records=[json.loads(l) for l in (source_run/'cases'/episode/'predictions.jsonl').read_text().splitlines()]
    if not records:raise ValueError('No successful source responses')
    # Evenly sample only observations that have already completed in the source run.
    selected={records[round(i*(len(records)-1)/max(1,min(args.count,len(records))-1))]['frame']
              for i in range(min(args.count,len(records)))}
    source=inputs[episode]
    if file_hash(Path(source['video']))!=source['source_video_sha256']:raise ValueError('Source video changed')
    dest=args.output/'backend_comparison'/f'{args.source_tag}_to_{service["served_model"]}'
    identity=dict(source_tag=args.source_tag,episode_id=episode,frames=sorted(selected),
                  source_manifest_sha256=file_hash(source_run/'manifest.json'),target_service=service,
                  purpose='Same causal inputs; BF16-dequantized and native-FP8 computations remain separate.')
    if not args.check_only:
        dest.mkdir(parents=True,exist_ok=True)
        previous=dest/'manifest.json'
        if previous.exists() and read_json(previous)['frames']!=identity['frames']:
            raise ValueError('Comparison frame selection is frozen; do not change the source prefix')
        write_json(previous,identity)
    cached={r['frame']:r for r in read_json(dest/'results.json').get('observations',[])} if (dest/'results.json').exists() else {}
    by_frame={r['frame']:r for r in records};tracker=CheckpointTracker();images=deque(maxlen=8);executed=[];results=[]
    capture=cv2.VideoCapture(source['video'])
    try:
        for obs in source['observations']:
            ok,composite=capture.read()
            if not ok:raise ValueError('Missing video frame')
            frame=obs['frame']
            if frame>max(selected):break
            if obs['terminal']:continue
            if obs['rgb_reused']:
                executed.append(dict(index=frame,name=action_name(obs['action'])));continue
            if frame not in by_frame:raise ValueError('Source observations are not a contiguous causal prefix')
            ok,png=cv2.imencode('.png',composite[:480,:640].copy())
            if not ok:raise ValueError('Cannot encode RGB')
            raw=png.tobytes();images.append(dict(frame=frame,sha256=hashlib.sha256(raw).hexdigest(),
                data_url='data:image/png;base64,'+base64.b64encode(raw).decode()))
            if frame in selected:
                conf=manifest['inference'];seed=int(hashlib.sha256(f'{episode}:{frame}:20261103'.encode()).hexdigest()[:8],16)&0x7fffffff
                payload=dict(model=conf['served_model'],messages=build_messages(list(images),executed[-32:],tracker.prompt_memory()),
                    temperature=0.0,seed=seed,max_tokens=conf['max_tokens'],response_format={'type':'json_schema',
                    'json_schema':{'name':'crossing_observation','strict':True,
                        'schema':core.response_schema([x['frame'] for x in images]) if hasattr(core,'response_schema') else core.RESPONSE_SCHEMA}})
                if 'chat_template_kwargs' in conf:payload['chat_template_kwargs']=conf['chat_template_kwargs']
                elif conf.get('thinking'):payload['chat_template_kwargs']={'enable_thinking':True}
                if canonical_hash(payload)!=by_frame[frame]['request_sha256']:
                    raise ValueError('Reconstructed request differs from the saved actual source request')
                if args.check_only:
                    print(json.dumps(dict(frame=frame,exact_source_request_verified=True)),flush=True)
                    tracker.update(frame,by_frame[frame]['prediction'])
                    executed.append(dict(index=frame,name=action_name(obs['action'])))
                    continue
                payload['model']=service['served_model'];digest=canonical_hash(payload)
                if frame in cached and cached[frame]['target_request_sha256']==digest:
                    row=cached[frame]
                else:
                    started=time.monotonic();reply=call_model(service['base_url'],payload)
                    prediction=parse_answer(reply,[x['frame'] for x in images])
                    row=dict(frame=frame,source_prediction=by_frame[frame]['prediction'],target_prediction=prediction,
                        source_request_sha256=by_frame[frame]['request_sha256'],target_request_sha256=digest,
                        elapsed_seconds=time.monotonic()-started,target_reply=reply)
                row['agreement']={k:row['source_prediction'][k]==row['target_prediction'][k]
                                  for k in ['status','location','confidence','same_place']}
                results.append(row)
                write_json(dest/'results.json',dict(complete=len(results)==len(selected),observations=results,
                    updated_at=now(),note='A small backend transition check, not proof of full benchmark equivalence.'))
                print(json.dumps(dict(frame=frame,agreement=row['agreement'])),flush=True)
            tracker.update(frame,by_frame[frame]['prediction'])
            executed.append(dict(index=frame,name=action_name(obs['action'])))
    finally:
        capture.release()


if __name__=='__main__':main()
