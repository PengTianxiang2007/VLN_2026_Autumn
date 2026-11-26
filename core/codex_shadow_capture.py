"""Publish action-boundary RGB for a read-only reviewer outside Isaac."""
import gzip
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image

from core.vlnverse_review import now, recording_only, write_json


class ShadowCapture:
    def __init__(self, settings, run_id, dataset):
        self.root = Path(settings['output_dir'])
        self.root.mkdir(parents=True, exist_ok=True)
        self.seed, self.run_id = settings['seed'], run_id
        with gzip.open(Path(dataset) / 'val_unseen/val_unseen.json.gz', 'rt') as stream:
            episodes = json.load(stream)['episodes']
        self.episodes = {f"{e['trajectory_id']}_{e['episode_id']}": e for e in episodes}
        self.active = None

    @recording_only
    def start(self, path_key):
        e = self.episodes[path_key]
        self.folder = self.root / e['episode_id'] / f'attempt_{time.time_ns()}'
        (self.folder / 'frames').mkdir(parents=True)
        self.active = dict(episode_id=e['episode_id'], scene=e['scan'], path_key=path_key,
                           instruction=e['instruction']['instruction_text'], seed=self.seed,
                           started_at=now(), remote_wait_seconds=0)
        self.step = 0
        self.capture_seconds = 0.0
        self.started = time.monotonic()
        write_json(self.folder / 'start.json', self.active)

    @recording_only
    def observe(self, path_key, observation, action, terminal=False):
        tick = time.monotonic()
        assert path_key == self.active['path_key']
        image = self.folder / 'frames' / f'F{self.step:06d}.png'
        rgb = np.asarray(observation['rgb'])
        if rgb.dtype != np.uint8 or rgb.shape != (480, 640, 3):
            raise ValueError(f'Unexpected RGB at F{self.step}: {rgb.shape} {rgb.dtype}')
        Image.fromarray(rgb).save(image, compress_level=1)
        position = observation.get('globalgps', observation.get('current_pose'))
        row = dict(episode_id=self.active['episode_id'], step=self.step, terminal=bool(terminal),
                   observed_at=now(), action=action, position=np.asarray(position).tolist() if position is not None else None,
                   native_front=dict(image=str(image.relative_to(self.folder)), sha256=hashlib.sha256(image.read_bytes()).hexdigest()))
        with (self.folder / 'observations.jsonl').open('a') as stream:
            stream.write(json.dumps(row, default=lambda x: np.asarray(x).tolist())+'\n')
        self.step += 1
        self.capture_seconds += time.monotonic() - tick
        if terminal:
            self.active['terminal_frame'] = row['step']

    @recording_only
    def finish(self, path_key, metrics):
        assert self.active['path_key'] == path_key
        self.active.update(finished_at=now(), simulation_wall_seconds=time.monotonic()-self.started,
                           capture_seconds=self.capture_seconds, frames=self.step,
                           metrics={k:float(metrics[k]) for k in ('success','spl','NE','TL','steps') if k in metrics})
        write_json(self.folder / 'navigation.json', self.active)
        self.active = None

    def close(self):
        pass
