"""Portable, standard-library-only reader for the frozen human Crossing dataset.

Only input manifests are read. Evaluation labels, positions and maps stay separate.
"""
import json
from collections import deque
from pathlib import Path


def episodes(dataset):
    """Return episode metadata with English/Chinese instructions and relative paths."""
    root = Path(dataset)
    return [json.loads(line) for line in (root / 'inputs/episodes.jsonl').read_text().splitlines() if line]


def iter_observations(dataset, episode_id, image_history=8, action_history=32):
    """Yield eligible observations in order, with images <= t and actions < t.

    History lengths are caller choices, not benchmark scoring parameters.
    RGB paths are absolute for convenient loading on the current machine.
    """
    if type(image_history) is not int or image_history < 1 or type(action_history) is not int or action_history < 0:
        raise ValueError('Invalid history lengths')
    root = Path(dataset).resolve()
    episode = next((e for e in episodes(root) if e['episode_id'] == episode_id), None)
    if episode is None:
        raise KeyError(episode_id)
    frames = json.loads((root / episode['observations']).read_text())
    images, actions = deque(maxlen=image_history), deque(maxlen=action_history)
    for f in frames:
        for action in f['newly_executed_actions']:
            if action['frame'] >= f['frame']:
                raise ValueError('Action is not strictly before the observation')
            actions.append(action)
        if not f['eligible_for_inference']:
            continue
        image = dict(frame=f['frame'], path=str(root / f['rgb']), sha256=f['rgb_sha256'])
        images.append(image)
        yield dict(episode_id=episode_id, frame=f['frame'], action_index=f['action_index'],
                   instruction=episode['instruction'], instruction_zh=episode['instruction_zh'],
                   images=list(images), executed_actions=list(actions))
