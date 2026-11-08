"""Verify a portable human Crossing dataset without third-party packages."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def verify(root, archive=None):
    root = Path(root).resolve()
    checksums = read(root / 'checksums.json')
    for relative, expected in checksums.items():
        path = (root / relative).resolve()
        assert path.is_relative_to(root), relative
        assert path.is_file() and sha(path) == expected, relative
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    assert actual == set(checksums) | {'checksums.json'}, 'Unexpected or missing package files'
    inputs, evaluation, events = rows(root / 'inputs/episodes.jsonl'), rows(root / 'evaluation/episodes.jsonl'), rows(root / 'evaluation/events.jsonl')
    config, summary = read(root / 'dataset.json'), read(root / 'summary.json')
    snapshot, selection = read(root / 'provenance/annotation_snapshot.json'), read(root / 'evaluation/selection.json')
    ids = [e['episode_id'] for e in inputs]
    assert ids == selection['included'] == [e['episode_id'] for e in evaluation]
    assert len(ids) == len(set(ids)) == summary['episodes']
    excluded = {r['episode_id'] for r in selection['excluded']}
    assert not excluded.intersection(ids) and len(excluded) == summary['excluded_episodes']
    assert {p.name for p in (root/'rgb').iterdir()} == set(ids), 'Excluded episode images present'
    assert set(snapshot['cases']) == set(ids)
    spec = importlib.util.spec_from_file_location('offline_dataset_check', root/'offline_dataset.py')
    module = importlib.util.module_from_spec(spec)
    # Keep the frozen package immutable: suppress creation of __pycache__.
    import sys
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = old
    event_ids, observed_count, frame_count = set(), 0, 0
    by_episode = {eid:[] for eid in ids}
    for e in events:
        assert e['episode_id'] in by_episode and e['id'] not in event_ids
        event_ids.add(e['id']);by_episode[e['episode_id']].append(e)
    allowed_input = {'episode_id','seed','instruction','instruction_zh','fps','observations','frame_count','eligible_observation_count'}
    allowed_frame = {'frame','action_index','video_time_s','rgb','rgb_sha256','rgb_reused','terminal','eligible_for_inference','newly_executed_actions'}
    for episode, truth in zip(inputs,evaluation):
        eid = episode['episode_id'];assert set(episode)==allowed_input
        observations = read(root/episode['observations'])
        trajectory = read(root/truth['trajectory']);positions = trajectory['frames']
        assert len(observations)==len(positions)==episode['frame_count']
        assert [f['frame'] for f in observations]==list(range(len(observations)))
        assert truth['event_ids']==[e['id'] for e in by_episode[eid]]
        human = {m['id']:m for m in snapshot['cases'][eid]['marks']}
        assert human and set(human)==set(truth['event_ids'])
        for i,f in enumerate(observations):
            assert set(f)==allowed_frame
            assert f['eligible_for_inference']==(not f['terminal'] and not f['rgb_reused'])
            assert sha(root/f['rgb'])==f['rgb_sha256']
            prior = positions[i-1] if i else None
            expected = [dict(frame=i-1,action_index=observations[i-1]['action_index'],action=prior['action_after_observation'])] if prior and prior['action_after_observation'] and not observations[i-1]['terminal'] else []
            assert f['newly_executed_actions']==expected
        for e in by_episode[eid]:
            assert all(e[k]==value for k,value in human[e['id']].items()), 'Human label changed'
            f=observations[e['frame']]
            assert e['position']==positions[e['frame']]['position']
            assert e['image_sha256']==f['rgb_sha256'] and e['rgb']==f['rgb'] and f['eligible_for_inference']
            assert e['is_crossing'] is True and e['wrong_choice_marked']==(e['type']=='wrong_choice')
            assert e['branch_choice_correctness']==('wrong' if e['type']=='wrong_choice' else 'unspecified')
        emitted = []
        for s in module.iter_observations(root,eid,image_history=8,action_history=32):
            emitted.append(s['frame'])
            assert set(s)=={'episode_id','frame','action_index','instruction','instruction_zh','images','executed_actions'}
            expected_frames=[f for f in observations[:s['frame']+1] if f['eligible_for_inference']][-8:]
            assert [im['frame'] for im in s['images']]==[f['frame'] for f in expected_frames]
            assert all(im['frame']<=s['frame'] and Path(im['path']).is_file() for im in s['images'])
            expected_actions=[a for f in observations[:s['frame']+1] for a in f['newly_executed_actions']][-32:]
            assert s['executed_actions']==expected_actions and all(a['frame']<s['frame'] for a in s['executed_actions'])
        assert emitted==[f['frame'] for f in observations if f['eligible_for_inference']]
        assert len(emitted)==episode['eligible_observation_count']
        observed_count+=len(emitted);frame_count+=len(observations)
    types=Counter(e['type'] for e in events);groups=Counter(e['group'] for e in evaluation)
    assert len(events)==summary['crossing_events'] and types['crossing']==summary['ordinary_crossing_events'] and types['wrong_choice']==summary['wrong_choice_events']
    assert groups['failure']==summary['failure_episodes'] and groups['success']==summary['success_episodes']
    assert frame_count==summary['frames'] and observed_count==summary['eligible_observations']
    assert config['train_dev_test_split'] is None and config['matching_tolerance'] is None
    if archive:
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            prefix=root.name+'/'
            assert set(z.namelist())=={prefix+p for p in actual}
            for relative,expected in checksums.items():
                with z.open(prefix+relative) as f:
                    h=hashlib.sha256()
                    for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
                    assert h.hexdigest()==expected,relative
    return dict(passed=True,dataset_id=config['dataset_id'],episodes=len(inputs),frames=frame_count,causal_observations_checked=observed_count,human_events_checked=len(events),
                all_files_sha256_verified=len(checksums),all_human_labels_preserved=True,excluded_episode_images_absent=True,causal_images_and_actions=True,
                negative_labels_not_fabricated=True,archive_verified=bool(archive))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--dataset',type=Path,required=True);parser.add_argument('--archive',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=verify(args.dataset,args.archive)
    if args.output:
        if args.output.resolve().is_relative_to(args.dataset.resolve()):raise ValueError('Write verification results outside the frozen dataset')
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))
