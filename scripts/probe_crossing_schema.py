"""Probe a failed development observation with frame-constrained structured output.

Uses the saved causal prefix of the old run. This diagnostic is not a fresh method
evaluation and must not be merged into full-trajectory results.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from core.crossing_checkpoint import build_messages,response_schema,canonical_hash,SYSTEM_PROMPT
from preview_crossing_checkpoint import frozen_core,load_records
from replay_crossing_checkpoint import call_model,parse_answer,read_json,write_json,now


def main(args):
    import cv2
    cv2.setNumThreads(1)
    source=read_json(args.output/'inputs.json')[args.episode]
    manifest=read_json(args.output/'runs'/args.source_tag/'manifest.json')
    if manifest['split']!='development' or args.episode not in manifest['episodes']:
        raise ValueError('Probe is restricted to the fixed development set')
    core=frozen_core(args.output/'runs'/args.source_tag,manifest)
    if core.SYSTEM_PROMPT!=SYSTEM_PROMPT:raise ValueError('Probe requires unchanged detector instructions')
    records=load_records(args.output/'runs'/args.source_tag/'cases'/args.episode/'predictions.jsonl')
    records={r['frame']:r for r in records if r['frame']<args.frame}
    required=[o['frame'] for o in source['observations'] if o['frame']<args.frame and not o['terminal'] and not o['rgb_reused']]
    if sorted(records)!=required:raise ValueError('Missing preceding causal predictions')
    tracker=core.CheckpointTracker();images=[];executed=[]
    capture=cv2.VideoCapture(source['video'])
    if (int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))!=(960,640):
        raise ValueError('Unexpected video layout')
    reached=False
    try:
        for obs in source['observations']:
            frame=obs['frame']
            ok,composite=capture.read()
            if not ok:raise ValueError('Video truncated')
            if obs['terminal']:continue
            if not obs['rgb_reused']:
                ok,png=cv2.imencode('.png',composite[:480,:640].copy())
                if not ok:raise ValueError('RGB encoding failed')
                raw=png.tobytes();images.append(dict(frame=frame,sha256=hashlib.sha256(raw).hexdigest(),data_url='data:image/png;base64,'+base64.b64encode(raw).decode()));images=images[-8:]
                ids=[im['frame'] for im in images]
                seed=int(hashlib.sha256(f'{args.episode}:{frame}:20261103'.encode()).hexdigest()[:8],16)&0x7fffffff
                old_payload=dict(model=manifest['inference']['served_model'],messages=core.build_messages(images,executed[-32:],tracker.prompt_memory()),temperature=0.0,seed=seed,max_tokens=manifest['inference']['max_tokens'],response_format={'type':'json_schema','json_schema':{'name':'crossing_observation','strict':True,'schema':core.RESPONSE_SCHEMA}})
                if manifest['inference'].get('thinking'):old_payload['chat_template_kwargs']={'enable_thinking':True}
                if frame==args.frame:
                    reached=True;break
                if records[frame]['request_sha256']!=core.canonical_hash(old_payload):raise ValueError('Prefix request mismatch')
                tracker.update(frame,core.validate_response(records[frame]['prediction'],ids))
            executed.append(dict(index=frame,name=core.action_name(obs['action'])))
    finally:capture.release()
    if not reached:raise ValueError('Probe frame is not a valid observation')
    service=read_json(args.service/'service.json')
    if service['phase']!='ready':raise ValueError('Service not ready')
    if service['served_model']!=manifest['inference']['served_model']:raise ValueError('Model service changed')
    payload={**old_payload,'messages':build_messages(images,executed[-32:],tracker.prompt_memory()),
             'response_format':{'type':'json_schema','json_schema':{'name':'crossing_observation','strict':True,'schema':response_schema(ids)}}}
    dest=args.output/'schema_regression'/f'{args.source_tag}_{args.episode}_f{args.frame:04d}'
    if (dest/'result.json').exists():raise ValueError('Preserve existing probe; do not overwrite')
    metadata=dict(phase='running',started_at=now(),source_tag=args.source_tag,episode_id=args.episode,frame=args.frame,image_frames=ids,old_request_sha256=core.canonical_hash(old_payload),request_sha256=canonical_hash(payload),scope='Diagnostic with saved old-run memory; not full method evaluation')
    write_json(dest/'status.json',metadata);write_json(dest/'request.json',payload)
    start=time.monotonic();reply=None
    try:
        reply=call_model(service['base_url'],payload,timeout=900)
        write_json(dest/'reply.json',reply)
        prediction=parse_answer(reply,ids)
        result=dict(**metadata,passed=True,prediction=prediction,elapsed_seconds=time.monotonic()-start,finished_at=now())
        result['phase']='complete';write_json(dest/'result.json',result);write_json(dest/'status.json',result)
        print(json.dumps(result,ensure_ascii=False))
    except Exception as error:
        if reply is not None:write_json(dest/'reply.json',reply)
        metadata.update(phase='failed',error=type(error).__name__+': '+str(error),finished_at=now())
        write_json(dest/'status.json',metadata);raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--source-tag',required=True)
    parser.add_argument('--episode',required=True);parser.add_argument('--frame',type=int,required=True)
    parser.add_argument('--service',type=Path,required=True);main(parser.parse_args())
