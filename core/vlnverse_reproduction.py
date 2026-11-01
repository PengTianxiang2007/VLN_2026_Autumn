"""Pure-data checks for the approved 250-episode, complete-scene reproduction."""
from collections import Counter
import hashlib
import json
import math
import random
import statistics

from core.seeding import episode_seed

SCENE_COUNTS = {
    'kujiale_0036': 25, 'kujiale_0113': 25, 'kujiale_0123_fix': 25,
    'kujiale_0207': 23, 'kujiale_0208': 25, 'kujiale_0232': 25,
    'kujiale_0234': 32, 'kujiale_0240': 23, 'kujiale_0257': 23, 'kujiale_0259': 24,
}
SEEDS = [0, 1, 2, 3, 4]
METRICS = ('SR', 'SPL', 'NE', 'OS', 'TL', 'FR', 'StR')


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def select_complete_scenes(episodes, scenes):
    if len(scenes) != len(set(scenes)) or not scenes:
        raise ValueError('Scene IDs must be nonempty and unique.')
    available = {e['scan'] for e in episodes}
    if not set(scenes) <= available:
        raise ValueError('Unknown scenes: ' + str(set(scenes) - available))
    selected = [e for e in episodes if e['scan'] in scenes]
    ids = [e['episode_id'] for e in selected]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate episode IDs in the annotation.')
    return selected


def make_manifest(episodes):
    counts = Counter(e['scan'] for e in episodes)
    order = sorted(counts)
    random.Random(20261101).shuffle(order)
    combinations = {(0, 0): ()}
    for rank, scene in enumerate(order):
        for (number, total), indices in list(combinations.items()):
            if number >= 10 or total + counts[scene] > 250:
                continue
            key = number + 1, total + counts[scene]
            candidate = indices + (rank,)
            if key not in combinations or candidate < combinations[key]:
                combinations[key] = candidate
    chosen = [order[i] for i in combinations[(10, 250)]]
    selected = select_complete_scenes(episodes, chosen)
    if dict(Counter(e['scan'] for e in selected)) != SCENE_COUNTS:
        raise ValueError('Annotation no longer matches the scene plan approved by the user.')
    return dict(selection_seed=20261101, selection_rule='first feasible rank tuple after seeded shuffle; 10 complete scenes totaling 250',
                selection_order=chosen, scene_counts=SCENE_COUNTS, seeds=SEEDS,
                episode_ids=[e['episode_id'] for e in selected],
                scene_episode_ids={scene: [e['episode_id'] for e in selected if e['scan'] == scene] for scene in sorted(chosen)},
                annotation_sha256=digest_json(episodes), selected_annotations_sha256=digest_json(selected),
                episodes_per_seed=250, total_episode_runs=1250, scene_seed_units=50,
                mode='physical', model='StreamVLN_R2R_v1_3')


def verify_resume(meta, selected, seed=None, scenes=None):
    if seed is not None and seed != meta.get('seed'):
        raise ValueError('Resume seed differs from the original run.')
    if scenes is not None and sorted(scenes) != sorted(meta.get('scenes', [])):
        raise ValueError('Resume scene selection differs from the original run.')
    if [e['episode_id'] for e in selected] != meta['episode_ids']:
        raise ValueError('Resume episode order or membership changed.')
    if meta.get('dataset_sha256') and digest_json(selected) != meta['dataset_sha256']:
        raise ValueError('Resume annotation content changed.')


def verify_rows(rows, expected_ids, seed):
    ids = [r['episode_id'] for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(expected_ids):
        raise ValueError('Missing, duplicate, or unexpected scored episodes.')
    for row in rows:
        if row['run_seed'] != seed or row['episode_seed'] != episode_seed(seed, row['episode_id']):
            raise ValueError('Scored episode has the wrong run or episode seed.')
        for metric in METRICS:
            value = float(row[metric])
            if not math.isfinite(value) or value < 0 or (metric in ('SR','SPL','OS','FR','StR') and value > 1):
                raise ValueError('Invalid metric: ' + metric)
    return {metric: statistics.mean(float(r[metric]) for r in rows) for metric in METRICS}


def summarize_complete_seeds(rows, manifest):
    means = {}
    for seed in manifest['seeds']:
        group = [r for r in rows if r['run_seed'] == seed]
        if len(group) == manifest['episodes_per_seed']:
            means[str(seed)] = verify_rows(group, manifest['episode_ids'], seed)
    result = dict(completed_episode_runs=len(rows), expected_episode_runs=manifest['total_episode_runs'],
                  complete_seed_metrics=means, complete=len(means)==len(manifest['seeds']))
    if result['complete']:
        result['mean_std_across_seeds'] = {
            metric: dict(mean=statistics.mean(m[metric] for m in means.values()),
                         std=statistics.stdev(m[metric] for m in means.values()), n=len(means))
            for metric in METRICS}
    return result
