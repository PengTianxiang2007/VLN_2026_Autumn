"""Episode failure ledger, kept separate from native navigation scores."""
import json
import os
from pathlib import Path
import time

from core.serial_pipeline import save


def batch_progress(output):
    output=Path(output)
    expected=set(json.loads((output/'config.json').read_text())['episode_ids'])
    results=[json.loads(p.read_text()) for p in (output/'episodes').glob('*/attempt_*/result.json')]
    completed=[r['episode_id'] for r in results]
    failures=[json.loads(p.read_text()) for p in (output/'failures').glob('*.json')]
    skipped=[r['episode_id'] for r in failures]
    if len(completed)!=len(set(completed)) or len(skipped)!=len(set(skipped)):
        raise RuntimeError('Duplicate episode accounting')
    if set(completed)&set(skipped) or not (set(completed)|set(skipped))<=expected:
        raise RuntimeError('Conflicting episode accounting')
    return dict(expected=len(expected),completed=len(completed),skipped=len(skipped),
                processed=len(completed)+len(skipped),pending=len(expected-set(completed)-set(skipped)),
                completed_ids=sorted(completed),skipped_ids=sorted(skipped),failures=failures)


def record_episode_failure(output, episode_id, attempt, error, stage, **details):
    output=Path(output)
    if episode_id not in json.loads((output/'config.json').read_text())['episode_ids']:
        raise ValueError('Cannot defer an unknown episode')
    if list((output/'episodes'/episode_id).glob('attempt_*/result.json')):
        raise RuntimeError('Cannot mark a scored episode as skipped')
    target=output/'failures'/(episode_id+'.json')
    if target.exists(): return json.loads(target.read_text())
    message=str(error)
    for key in ('JEV_API_KEY','DEEPSEEK_API_KEY'):
        if os.environ.get(key): message=message.replace(os.environ[key],'[REDACTED]')
    row=dict(episode_id=episode_id,attempt=str(attempt),error=message,stage=stage,
             time=time.time(),status='deferred_for_rerun',counted_as_navigation_result=False,**details)
    save(Path(attempt)/'failure.json',row)
    save(target,row)
    write_retry_manifest(output)
    return row


def write_retry_manifest(output):
    progress=batch_progress(output)
    save(Path(output)/'retry_manifest.json',dict(episode_ids=progress['skipped_ids'],
         failures=progress['failures'],automatic_rerun=False,
         note='Deferred technical failures; excluded from valid navigation count and scores.'))
    return progress


def exclude_failed_tasks(dataloader):
    """On a native RSS/crash restart, do not revisit deferred tasks."""
    output=os.environ.get('VLN_SERIAL_OUTPUT')
    if not output: return
    failed={p.stem for p in (Path(output)/'failures').glob('*.json')}
    dataloader.resumed_path_key_list=[k for k in dataloader.resumed_path_key_list
        if dataloader.path_key_data[k]['episode_id'] not in failed]
