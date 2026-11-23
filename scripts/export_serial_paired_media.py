"""Build seekable RGB contact sheets for a frozen serial recovery snapshot."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import cv2
from PIL import Image

BASE = Path('outputs/reproduction/streamvln_scene250_5seeds_20261101_v2/visualization')
WIDTH, HEIGHT, SIDE = 480, 360, 4


def baseline_index():
    rows = (json.loads(line) for line in (BASE / 'index.jsonl').read_text().splitlines())
    return {r['episode_id']: r for r in rows if r['seed'] == 2}


def write_sheets(frames, directory, prefix):
    pages, count = [], 0
    for i, frame in enumerate(frames):
        slot = i % (SIDE * SIDE)
        if slot == 0:
            sheet = Image.new('RGB', (WIDTH * SIDE, HEIGHT * SIDE))
        sheet.paste(frame.resize((WIDTH, HEIGHT), Image.Resampling.BILINEAR),
                    (slot % SIDE * WIDTH, slot // SIDE * HEIGHT))
        count = i + 1
        if slot == SIDE * SIDE - 1:
            path = directory / f'{prefix}_{len(pages):03}.jpg'
            sheet.save(path, quality=81)
            pages.append(path.name)
    if count % (SIDE * SIDE):
        path = directory / f'{prefix}_{len(pages):03}.jpg'
        sheet.crop((0, 0, WIDTH * SIDE, HEIGHT * ((slot // SIDE) + 1))).save(path, quality=81)
        pages.append(path.name)
    return {'sheets': pages, 'count': count}


def current_frames(attempt):
    for line in (attempt / 'observations.jsonl').read_text().splitlines():
        obs = json.loads(line)
        with Image.open(attempt / 'frames' / Path(obs['path']).name) as image:
            yield image.convert('RGB')


def baseline_frames(path):
    capture = cv2.VideoCapture(str(path))
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame.shape[:2] != (640, 960):
                raise ValueError(f'Unexpected baseline layout at {path}')
            # core/vlnverse_review.py writes the native camera into this rectangle.
            yield Image.fromarray(cv2.cvtColor(frame[:480, :640], cv2.COLOR_BGR2RGB))
    finally:
        capture.release()


def build(snapshot):
    output = snapshot.parent
    campaign = output.parent.parent
    frozen = json.loads(snapshot.read_text())
    original = baseline_index()
    (output / 'media').mkdir(exist_ok=True)
    cv2.setNumThreads(1)

    def encode(relative):
        attempt = campaign / relative
        eid = attempt.parent.name
        directory = output / 'media' / eid
        directory.mkdir(exist_ok=True)
        baseline = original[eid]
        curr = write_sheets(current_frames(attempt), directory, 'current')
        orig = write_sheets(baseline_frames(BASE / baseline['video']), directory, 'original')
        if not curr['count'] or orig['count'] != baseline['frames']:
            raise ValueError(f'Incomplete RGB media for {eid}: {curr["count"]}, {orig["count"]}')
        return eid, {'current': curr, 'original': orig}

    with ThreadPoolExecutor(max_workers=3) as workers:
        entries = dict(workers.map(encode, frozen['attempts']))
    (output / 'media_index.json').write_text(json.dumps(entries))
    print('Exported RGB for', len(entries), 'paired cases', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    build(parser.parse_args().snapshot.resolve())
