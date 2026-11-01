"""Read a completed run's LMDB and verify episode identity, seeds and scoring."""
import argparse
import gzip
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from core.seeding import episode_seed
from core.vlnverse_reproduction import verify_resume, verify_rows


def export_run(run):
    import lmdb
    import msgpack_numpy

    meta = json.loads((run / 'run.json').read_text())
    with gzip.open(Path(meta['dataset']) / 'val_unseen/val_unseen.json.gz', 'rt') as f:
        episodes = json.load(f)['episodes']
    verify_resume(meta, episodes, meta['seed'])
    expected = {f"{e['trajectory_id']}_{e['episode_id']}": e for e in episodes}
    database = lmdb.open(str(run / 'storage/samples/sample_data.lmdb'), readonly=True, lock=False)
    rows = []
    try:
        with database.begin() as txn:
            # split_data stores its rank assignment in the same LMDB as scores.
            metadata_keys = {b'timestamp_', b'eval_rank_0'}
            keys = {key.decode() for key, _ in txn.cursor() if key not in metadata_keys}
            if keys != set(expected):
                raise ValueError('Completed LMDB keys differ from the frozen task list.')
            for key, episode in expected.items():
                value = msgpack_numpy.unpackb(txn.get(key.encode()))
                info = value['info']
                if info['episode_id'] != episode['episode_id']:
                    raise ValueError('Metric episode ID differs from its LMDB key.')
                reason = value['fail_reason']
                rows.append(dict(episode_id=episode['episode_id'], scene=episode['scan'], run_id=meta['run_id'],
                                 run_seed=info['reproduction_run_seed'], episode_seed=info['reproduction_episode_seed'],
                                 SR=float(info['success']), SPL=float(info['spl']), NE=float(info['NE']),
                                 OS=float(info['osr']), TL=float(info['TL']), FR=float(reason == 'fall'),
                                 StR=float(reason == 'stuck'), steps=int(info['steps']), fail_reason=reason,
                                 pred_path=info['pred_path']))
    finally:
        database.close()
    summary = verify_rows(rows, meta['episode_ids'], meta['seed'])
    traces_checked = 0
    for path in sorted((run / 'storage/chunks').glob('*/agent_trace.jsonl')):
        with path.open() as lines:
            for line in lines:
                record = json.loads(line)
                if record['episode_id'] not in meta['episode_ids']:
                    raise ValueError('Agent trace contains an unexpected episode.')
                if record['run_seed'] != meta['seed'] or record['episode_seed'] != episode_seed(meta['seed'], record['episode_id']):
                    raise ValueError('Model-service seed differs from the simulator seed.')
                if record['forced_smoke_stop']:
                    raise ValueError('A reproduction episode was truncated by a smoke action cap.')
                traces_checked += 1
    official_file = PROJECT / 'benchmarks/vlnverse/upstream/logs' / meta['run_id'] / 'kujiale_result.json'
    official = json.loads(official_file.read_text())['val_unseen']
    if official['Count'] != len(rows):
        raise ValueError('Official count differs from the unique episode count.')
    for metric, value in summary.items():
        if abs(value - float(official[metric])) > 0.0001:
            raise ValueError('Export disagrees with official scoring: ' + metric)
    temporary = run / 'episodes.jsonl.tmp'
    temporary.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
    temporary.replace(run / 'episodes.jsonl')
    proof = dict(passed=True, episodes=len(rows), seed=meta['seed'], scenes=meta['scenes'],
                 metrics=summary, model_trace_records_verified=traces_checked)
    (run / 'validation.json').write_text(json.dumps(proof, indent=2) + '\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    print(json.dumps(export_run(parser.parse_args().run.resolve()), indent=2))
