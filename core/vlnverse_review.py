"""Compressed, observation-only review records; no additional simulator sensors."""
from datetime import datetime, timezone
import fcntl
import functools
import gzip
import json
from pathlib import Path
import re
import subprocess
import textwrap
import time
import traceback


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def review_settings(output_root, seed, method):
    policy = Path(output_root) / 'visualization.json'
    if not policy.exists():
        return None
    settings = json.loads(policy.read_text())
    if settings.get('schema') != 1 or not isinstance(settings.get('seeds'), list):
        raise ValueError('Invalid visualization policy')
    if method != 'StreamVLN' or seed not in settings['seeds']:
        return None
    root = Path(settings['output_dir']).resolve()
    if not root.is_relative_to(Path(output_root).resolve().parent):
        raise ValueError('Review output must remain inside this campaign')
    return dict(output_dir=str(root), seed=seed, fps=6, crf=26,
                policy=str(policy), format='rgb_actions_xy_path_h264_v1')


def recording_only(method):
    """A recording failure is reported without changing navigation or its score."""
    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception:
            error = dict(time=now(), run_id=self.run_id, seed=self.seed,
                         operation=method.__name__, error=traceback.format_exc())
            if self.active is not None:
                self.active['recording_error'] = error['error']
            print('VISUALIZATION_ERROR ' + json.dumps(error), flush=True)
            try:
                with (self.root / 'errors.jsonl').open('a') as stream:
                    fcntl.flock(stream, fcntl.LOCK_EX)
                    stream.write(json.dumps(error) + '\n')
            except OSError:
                pass
    return wrapped


class EpisodeReview:
    def __init__(self, settings, run_id, dataset):
        import cv2
        import imageio_ffmpeg
        import numpy as np

        self.cv2, self.np = cv2, np
        self.ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        self.root = Path(settings['output_dir'])
        self.root.mkdir(parents=True, exist_ok=True)
        self.seed, self.fps, self.crf = settings['seed'], settings['fps'], settings['crf']
        self.run_id = run_id
        with gzip.open(Path(dataset) / 'val_unseen/val_unseen.json.gz', 'rt') as stream:
            episodes = json.load(stream)['episodes']
        self.episodes = {f"{e['trajectory_id']}_{e['episode_id']}": e for e in episodes}
        self.active = None
        self.encoder = self.encoder_log = self.steps = None
        self.last_rgb = None

    def _close(self):
        encoder, self.encoder = self.encoder, None
        if encoder is not None:
            try:
                encoder.stdin.close()
                code = encoder.wait(timeout=30)
            except BaseException:
                if encoder.poll() is None:
                    encoder.kill()
                    encoder.wait()
                raise
            finally:
                self._close_logs()
            if code:
                raise RuntimeError(f'Video encoder exited {code}')
        else:
            self._close_logs()

    def _close_logs(self):
        if self.encoder_log is not None:
            self.encoder_log.close()
            self.encoder_log = None
        if self.steps is not None:
            self.steps.close()
            self.steps = None

    @recording_only
    def start(self, path_key):
        self._close()
        episode = self.episodes[path_key]
        if not all(re.fullmatch(r'[a-zA-Z0-9_-]+', episode[k]) for k in ('scan', 'episode_id')):
            raise ValueError('Unsafe episode path')
        directory = self.root / f'seed_{self.seed}' / episode['scan'] / episode['episode_id'] / f'attempt_{time.time_ns()}'
        directory.mkdir(parents=True, exist_ok=False)
        instruction = episode['instruction']['instruction_text']
        self.active = dict(seed=self.seed, run_id=self.run_id, scene=episode['scan'], episode_id=episode['episode_id'],
                           instruction=instruction, reference_path=episode.get('reference_path', []), pred_path=[],
                           directory=str(directory), started_at=now(), status='recording', frames=0, actions=0,
                           fps=self.fps, frame_semantics='one frame per policy action; terminal frame when available',
                           visualization_only=True)
        self.last_rgb = None
        write_json(directory / 'case.json', self.active)
        self.steps = (directory / 'steps.jsonl').open('w', buffering=1)
        self.encoder_log = (directory / 'encoder.log').open('w')
        command = [self.ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
                   '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '960x640', '-r', str(self.fps), '-i', 'pipe:0',
                   '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', str(self.crf), '-threads', '1',
                   '-pix_fmt', 'yuv420p', '-g', '12', '-movflags', '+frag_keyframe+empty_moov+default_base_moof',
                   str(directory / 'navigation.mp4')]
        self.encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                        stderr=self.encoder_log, bufsize=0)
        print(f'REVIEW_RECORDING seed={self.seed} episode={episode["episode_id"]} output={directory}',flush=True)

    def _frame(self, rgb, action, terminal=False):
        np, cv = self.np, self.cv2
        case = self.active
        frame = np.full((640, 960, 3), (20, 24, 31), dtype=np.uint8)
        frame[:480, :640] = cv.resize(rgb, (640, 480))
        def label(text, x, y, color=(225, 230, 238), scale=.48):
            cv.putText(frame, str(text), (x, y), cv.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv.LINE_AA)
        label('XY TRAJECTORY (review only)', 653, 27, scale=.48)
        ref = np.asarray(case['reference_path'], dtype=float).reshape(-1, 3)[:, :2]
        pred = np.asarray(case['pred_path'], dtype=float).reshape(-1, 3)[:, :2]
        points = np.concatenate([ref, pred])
        if len(points):
            low, high = points.min(axis=0), points.max(axis=0)
            span = max(float((high-low).max()), 1.) + 1.
            center = (low+high)/2
            def pixels(path):
                xy = (path-center)/span*260
                return np.column_stack([800+xy[:, 0], 195-xy[:, 1]]).astype(np.int32)
            for path, color in [(ref, (81, 191, 130)), (pred, (93, 166, 255))]:
                if len(path)>1:
                    cv.polylines(frame, [pixels(path)], False, color, 2, cv.LINE_AA)
            if len(ref):
                cv.circle(frame, tuple(pixels(ref)[-1]), 6, (255, 116, 116), -1)
            if len(pred):
                cv.circle(frame, tuple(pixels(pred)[-1]), 5, (245, 245, 255), -1)
        label('Green: reference  Blue: actual', 652, 353, scale=.43)
        label('Red: goal  White: current', 652, 375, scale=.43)
        label(f'Seed {self.seed} | {case["scene"]}', 652, 407, scale=.43)
        action_code = 0 if 'stop' in action else (action.get('move_by_discrete') or action.get('move_by_flash') or [-1])[0]
        name = {0:'STOP', 1:'FORWARD', 2:'LEFT', 3:'RIGHT', -1:'WAIT'}.get(action_code, str(action_code))
        label(f'Action {case["actions"]}: {"TERMINAL" if terminal else name}', 652, 432, scale=.5)
        label('Playback: 6 action frames/sec', 652, 456, scale=.43)
        label(case['episode_id'], 12, 503, scale=.55)
        for i, line in enumerate(textwrap.wrap(str(case['instruction']), width=113)[:5]):
            label(line, 12, 527+i*20, scale=.46)
        return frame

    @recording_only
    def observe(self, path_key, observation, action, terminal=False):
        if self.active is None or self.active.get('recording_error'):
            return
        case = self.active
        if self.episodes[path_key]['episode_id'] != case['episode_id']:
            raise ValueError('Visualization episode association changed')
        rgb = observation.get('rgb')
        if rgb is None:
            rgb = self.last_rgb
        if rgb is None:
            return
        rgb = self.np.asarray(rgb)
        if rgb.dtype != self.np.uint8 or rgb.shape != (480, 640, 3):
            raise ValueError('Unexpected review RGB shape/dtype')
        self.last_rgb = rgb.copy()
        position = observation.get('globalgps')
        if position is not None:
            case['pred_path'].append(self.np.asarray(position).astype(float).tolist())
        frame = self._frame(rgb, action, terminal)
        # FileIO writes may be short; send every byte of a raw RGB frame.
        data = memoryview(frame).cast('B')
        while data:
            count = self.encoder.stdin.write(data)
            if not count:
                raise BrokenPipeError('Video encoder pipe closed')
            data = data[count:]
        record = dict(frame=case['frames'], action_index=case['actions'], action=action,
                      terminal=terminal, position=case['pred_path'][-1] if case['pred_path'] else None,
                      rgb_reused='rgb' not in observation)
        self.steps.write(json.dumps(record) + '\n')
        if not case['frames']:
            self.cv2.imwrite(str(Path(case['directory'])/'poster.jpg'), self.cv2.cvtColor(frame, self.cv2.COLOR_RGB2BGR))
        case['frames'] += 1
        if not terminal:
            case['actions'] += 1

    @recording_only
    def finish(self, path_key, metrics):
        if self.active is None:
            return
        case = self.active
        if (metrics['episode_id'] != case['episode_id'] or self.episodes[path_key]['episode_id'] != case['episode_id']
                or metrics['reproduction_run_seed'] != self.seed):
            raise ValueError('Review score belongs to another episode')
        try:
            self._close()
        except Exception:
            case['recording_error'] = traceback.format_exc()
        case.update(finished_at=now(), status='error' if case.get('recording_error') else 'complete',
                    metrics={k:float(metrics[k]) for k in ('success','spl','NE','osr','TL','steps')},
                    fail_reason=metrics['fail_reason'], episode_seed=int(metrics['reproduction_episode_seed']),
                    pred_path=self.np.asarray(metrics.get('pred_path',case['pred_path'])).tolist())
        directory = Path(case['directory'])
        write_json(directory/'case.json',case)
        if self.last_rgb is not None:
            frame = self._frame(self.last_rgb, {'stop':[]}, terminal=True)
            self.cv2.imwrite(str(directory/'trajectory.png'), self.cv2.cvtColor(frame[:480,640:],self.cv2.COLOR_RGB2BGR))
        row = {k:case[k] for k in ('seed','run_id','scene','episode_id','instruction','status','metrics','fail_reason','frames')}
        row.update(video=str((directory/'navigation.mp4').relative_to(self.root)),
                   detail=str((directory/'case.json').relative_to(self.root)),
                   steps=str((directory/'steps.jsonl').relative_to(self.root)),
                   trajectory=str((directory/'trajectory.png').relative_to(self.root)))
        with (self.root/'index.jsonl').open('a+') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.write(json.dumps(row,ensure_ascii=False)+'\n');stream.flush();stream.seek(0)
            rows = [json.loads(line) for line in stream if line.strip()]
            write_review_index(self.root, rows)
        self.active, self.last_rgb = None, None


def write_review_index(root, rows):
    payload = json.dumps(rows,ensure_ascii=False).replace('<','\\u003c')
    template = Path(__file__).with_name('vlnverse_review.html').read_text()
    temporary = root/'index.html.tmp'
    temporary.write_text(template.replace('__REVIEW_DATA__',payload))
    temporary.replace(root/'index.html')
