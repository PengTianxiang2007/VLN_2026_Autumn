"""Independent delivery check: all metadata hashes, sampled PNGs, isolated reader.

Does not modify the dataset. Full auxiliary-image hashes were checked at capture;
this check deliberately reports its PNG sampling scope instead of claiming that
it has freshly read every image byte again.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile


def read(path):
    return json.loads(path.read_text())


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def validate(root):
    manifest = read(root / 'manifest.json')
    summary = manifest['summary']
    checksums = {}
    for line in (root / 'SHA256SUMS').read_text().splitlines():
        checksum, name = line.split('  ', 1)
        path = PurePosixPath(name)
        assert not path.is_absolute() and '..' not in path.parts
        assert name not in checksums and len(checksum) == 64
        checksums[name] = checksum
    metadata = [name for name in checksums if not name.startswith('observations/')]
    for name in metadata:
        assert digest(root / name) == checksums[name], name
    labels = read(root / 'evaluation/all69_classifications.json')
    selected = {x['episode_id']: x for x in labels if x['selected']}
    assert len(labels) == summary['reviewed_failures']
    assert Counter(x['decision'] for x in labels) == dict(
        include=summary['selected'], exclude=summary['excluded'], uncertain=summary['uncertain'])
    ids = (root / 'subsets/all_selected.txt').read_text().splitlines()
    assert len(ids) == len(set(ids)) == len(selected) and set(ids) == set(selected)
    assert {p.name for p in (root / 'inputs').iterdir()} == set(ids)
    for subset in ('branch_core', 'direction_extension'):
        subset_ids = (root / f'subsets/{subset}.txt').read_text().splitlines()
        assert set(subset_ids) == {eid for eid, x in selected.items() if x['subset'] == subset}
        assert len(subset_ids) == summary[subset]
    observations = events = hardlink_alias_pairs = 0
    indexed_images = set()
    sampled_pngs = set()
    for eid in ids:
        records = [json.loads(s) for s in (root / f'inputs/{eid}/observations.jsonl').read_text().splitlines()]
        actions = [json.loads(s) for s in (root / f'evaluation/actions/{eid}.jsonl').read_text().splitlines()]
        label = selected[eid]
        assert len(records) == len(actions)
        assert [x['step'] for x in records] == list(range(len(records)))
        assert [x['terminal'] for x in actions] == [False] * (len(records) - 1) + [True]
        for t, record in enumerate(records):
            assert record['episode_id'] == eid
            assert record['previous_action'] == (actions[t - 1]['action'] if t else None)
            assert not {'action', 'terminal', 'reference_path', 'events'} & record.keys()
            assert [v['relative_yaw_deg'] for v in record['views_180']] == [45, 0, -45]
            assert len(record['views_360']) == 8
            for view in [record['native_front'], *record['views_180'], *record['views_360']]:
                name = view['image']
                assert name.startswith(f'observations/{eid}/{t:06d}/')
                assert view['sha256'] == checksums[name]
                indexed_images.add(name)
            for view in record['views_360']:
                angle = view['camera_pose']['heading_deg'] - record['robot_pose']['heading_deg'] - view['relative_yaw_deg']
                assert math.isfinite(angle) and abs((angle + 180) % 360 - 180) < .001
        samples = {0, len(records) - 1}
        for event in label['events']:
            step = event['decision_step_estimate']
            confirm = event['confirmed_wrong_step']
            assert 0 <= event['decision_interval_steps'][0] <= step < confirm < len(records)
            assert event['decision_robot_pose'] == records[step]['robot_pose']
            assert event['confirmation_robot_pose'] == records[confirm]['robot_pose']
            samples.update((step, confirm))
        for t in samples:
            sampled_pngs.add(records[t]['views_360'][t % 8]['image'])
        sampled_pngs.add(records[0]['native_front']['image'])
        # Three aliases are checked for every episode, independent of the builder.
        for alias in records[0]['views_180']:
            original = records[0]['views_360'][alias['view_id']]
            a, b = (root / alias['image']).stat(), (root / original['image']).stat()
            if (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino):
                hardlink_alias_pairs += 1
            else:
                # A plain copy is also a valid portable dataset, at larger size.
                assert digest(root / alias['image']) == original['sha256']
        observations += len(records)
        events += len(label['events'])
    assert observations == summary['observations'] and events == summary['selected_events']
    assert indexed_images == {name for name in checksums if name.startswith('observations/')}
    assert len(indexed_images) == summary['logical_png_paths']
    for name in sampled_pngs:
        assert digest(root / name) == checksums[name], name
    # Real data are copied to an isolated directory, with no evaluation/provenance.
    eid = ids[0]
    first = [json.loads(s) for s in (root / f'inputs/{eid}/observations.jsonl').read_text().splitlines()[:2]]
    with tempfile.TemporaryDirectory(prefix='route_dataset_delivery_') as temporary:
        moved = Path(temporary)
        folder = moved / 'inputs' / eid
        folder.mkdir(parents=True)
        shutil.copy2(root / f'inputs/{eid}/task.json', folder / 'task.json')
        (folder / 'observations.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in first))
        shutil.copy2(root / 'offline_route_dataset.py', moved / 'offline_route_dataset.py')
        for record in first:
            for view in [record['native_front'], *record['views_180'], *record['views_360']]:
                destination = moved / view['image']
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(root / view['image'], destination)
        program = '''import os, sys
from pathlib import Path
sys.path.insert(0, os.getcwd())
from offline_route_dataset import OfflineRouteDataset
root = Path.cwd()
assert not (root/'evaluation').exists() and not (root/'provenance').exists()
ds = OfflineRouteDataset(root)
eid = ds.episode_ids()[0]
for mode, count in [('front',1),('180',3),('360',8)]:
    context = ds.context(eid, 1, mode)
    assert len(context['observations']) == 2
    for step, obs in enumerate(context['observations']):
        assert obs['step'] == step and len(obs['views']) == count
        for view in obs['views']:
            path = Path(view['image'])
            assert path.is_relative_to(root) and path.is_file()
'''
        subprocess.run([sys.executable, '-I', '-B', '-c', program], cwd=moved, check=True)
    return dict(passed=True, completed_at=datetime.now(timezone.utc).isoformat(),
        dataset=str(root), dataset_manifest_sha256=digest(root/'manifest.json'),
        checksum_manifest_sha256=digest(root/'SHA256SUMS'), summary=summary,
        metadata_and_review_files_freshly_rehashed=len(metadata),
        png_paths_indexed=len(indexed_images), png_files_sampled_and_freshly_rehashed=len(sampled_pngs),
        full_png_rehash_this_check=False, alias_pairs_checked=3*len(ids),
        hardlink_alias_pairs=hardlink_alias_pairs,
        every_input_action_pose_view_and_event_index_checked=True,
        isolated_relocation_reader_passed=True, reader_modes_checked=['front','180','360'],
        metadata_and_review_bytes=sum((root/name).stat().st_size for name in metadata),
        checksum_manifest_bytes=(root/'SHA256SUMS').stat().st_size,
        external_files_needed_for_reader=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    root, report = args.dataset.resolve(), args.report.resolve()
    if report.is_relative_to(root):
        parser.error('Write the verification report outside the frozen dataset')
    result = validate(root)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
