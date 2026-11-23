"""Standard-library reader for a portable, causal multiview observation bundle.

This module deliberately never reads evaluation/ or provenance/.
"""
import json
from pathlib import Path


class OfflineRouteDataset:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def _path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError('Path is outside the dataset')
        return path

    def episode_ids(self):
        return sorted(p.name for p in (self.root/'inputs').iterdir() if p.is_dir())

    def _episode(self, episode_id):
        if not episode_id or Path(episode_id).name != episode_id:
            raise ValueError('Invalid episode ID')
        return self._path('inputs/' + episode_id)

    def task(self, episode_id):
        return json.loads((self._episode(episode_id)/'task.json').read_text())

    def iter_observations(self, episode_id, *, through_step, mode='180'):
        """Yield observations 0..t, including a_(t-1), never a_t or later.

        Image paths are absolute local paths after resolving portable bundle paths.
        'front' selects the native image; '180' and '360' select auxiliary images.
        """
        if mode not in ('front', '180', '360'):
            raise ValueError('mode must be front, 180, or 360')
        if not isinstance(through_step, int) or through_step < 0:
            raise ValueError('through_step must be a nonnegative integer')
        found = False
        with (self._episode(episode_id)/'observations.jsonl').open() as stream:
            for line in stream:
                raw = json.loads(line)
                if raw['step'] > through_step:
                    break
                # Explicit allowlist: adding offline audit fields cannot expose them.
                value = {key: raw[key] for key in (
                    'episode_id', 'step', 'simulation_time_s', 'episode_elapsed_s',
                    'robot_pose', 'native_camera_pose', 'calibration', 'previous_action')}
                selected = [raw['native_front']] if mode == 'front' else raw['views_' + mode]
                value['observation_mode'] = mode
                value['views'] = [{**v, 'image': str(self._path(v['image']))} for v in selected]
                yield value
                if raw['step'] == through_step:
                    found = True
                    break
        if not found:
            raise IndexError(f'No observation at step {through_step}')

    def context(self, episode_id, step, mode='180'):
        return dict(task=self.task(episode_id),
                    observations=list(self.iter_observations(episode_id, through_step=step, mode=mode)))
