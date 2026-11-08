"""Nominate repeated seed2 wrong-branch trajectories using existing five-seed records.

This is an offline annotation aid, not a semantic classifier or navigation run.
Local discrete Frechet matching proposes candidates; map review remains separate.
"""
import argparse
import base64
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / 'outputs/reproduction/streamvln_scene250_5seeds_20261101_v2'
ATTRIBUTION = ROOT / 'outputs/checkpoint_review/seed2_crossing_attribution_20261103'


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def simplify(points, minimum=.06):
    kept = [0]
    for i in range(1, len(points)):
        if np.linalg.norm(points[i, :2] - points[kept[-1], :2]) >= minimum:
            kept.append(i)
    if kept[-1] != len(points) - 1:
        kept.append(len(points) - 1)
    return points[kept, :2], kept


def resample(points, spacing=.12):
    values, mapping = [points[0]], [0]
    for i in range(1, len(points)):
        count = max(1, math.ceil(np.linalg.norm(points[i] - points[i-1]) / spacing))
        for k in range(1, count + 1):
            values.append(points[i-1] + (points[i] - points[i-1]) * k / count)
            mapping.append(i)
    return np.array(values), mapping


def source_segment(points, frame):
    """Include incoming context and 1.8 m of the annotated outgoing trace."""
    xy, kept = simplify(points)
    center = min(range(len(kept)), key=lambda i: abs(kept[i] - frame))
    start = center
    length = 0.
    while start > 0 and length < .8:
        length += np.linalg.norm(xy[start] - xy[start-1])
        start -= 1
    end = center
    length = 0.
    while end + 1 < len(xy) and length < 1.8:
        length += np.linalg.norm(xy[end+1] - xy[end])
        end += 1
    return xy[start:end+1], kept[start], kept[end]


def local_frechet(source, target):
    """Minimum discrete Frechet distance to a chronological target subsequence."""
    a, _ = resample(source)
    b0, indices = simplify(target)
    b, mapping = resample(b0)
    distance = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    cost = distance.copy()
    starts = np.zeros(cost.shape, dtype=int)
    starts[0] = np.arange(len(b))
    for i in range(1, len(a)):
        starts[i, 0] = 0
        cost[i, 0] = max(cost[i-1, 0], distance[i, 0])
        for j in range(1, len(b)):
            previous = [(cost[i-1, j], starts[i-1, j]),
                        (cost[i, j-1], starts[i, j-1]),
                        (cost[i-1, j-1], starts[i-1, j-1])]
            best = min(previous, key=lambda v: v[0])
            cost[i, j] = max(best[0], distance[i, j])
            starts[i, j] = best[1]
    end = int(np.argmin(cost[-1]))
    start = int(starts[-1, end])
    start_frame, end_frame = indices[mapping[start]], indices[mapping[end]]
    return dict(distance_m=float(cost[-1, end]), start_frame=start_frame, end_frame=end_frame,
                minimum_height=float(target[start_frame:end_frame+1, 2].min()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--render-only', action='store_true', help='Render the already saved nominations with the plotting environment')
    parser.add_argument('--rgb-shortlist-only', action='store_true', help='Extract existing seed2/3 RGB for five-seed nominated tasks')
    args = parser.parse_args()
    out = args.output.resolve()
    if args.rgb_shortlist_only:
        extract_rgb(out)
        return
    if args.render_only:
        shutil.copy2(__file__, out/'source/render_fix.py')
        render(out)
        return
    import lmdb
    import msgpack_numpy
    out.mkdir(parents=True, exist_ok=False)
    write(out/'status.json', dict(phase='reading_existing_records', gpu_used=False))
    (out/'source').mkdir()
    shutil.copy2(__file__, out/'source'/Path(__file__).name)
    git = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    (out/'source/worktree.patch').write_bytes(subprocess.check_output(['git', 'diff', '--binary'], cwd=ROOT))
    (out/'source/git_status.txt').write_text(subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True))
    reviews = [r for r in read(ATTRIBUTION/'attribution_reviews.json') if r['status'] == 'crossing']
    assert len(reviews) == len({r['episode_id'] for r in reviews}) == 48
    ids = {r['episode_id'] for r in reviews}
    evidence = read(ATTRIBUTION/'evidence.json')
    cases = {c['episode_id']: c for c in evidence['cases'] if c['episode_id'] in ids}
    campaign = read(CAMPAIGN/'manifest.json')
    scores = {(int(r['run_seed']), r['episode_id']): r for r in csv.DictReader((CAMPAIGN/'episodes.csv').open())}
    videos = {(r['seed'], r['episode_id']): r for r in map(json.loads, (CAMPAIGN/'visualization/index.jsonl').read_text().splitlines())}
    records = {identity: {} for identity in ids}
    for unit in campaign['units']:
        run = CAMPAIGN/'runs/vlnverse/streamvln/results'/unit['run_id']
        assert read(run/'result.json')['status'] == 'complete'
        assert read(run/'validation.json')['passed']
        dbpath = run/'storage/samples/sample_data.lmdb'
        with lmdb.open(str(dbpath), readonly=True, lock=False) as database:
            with database.begin() as transaction:
                for key, value in transaction.cursor():
                    if key in (b'timestamp_', b'eval_rank_0'):
                        continue
                    record = msgpack_numpy.unpackb(value)
                    info = record['info']
                    identity, seed = info['episode_id'], unit['seed']
                    if identity not in ids:
                        continue
                    assert info['reproduction_run_seed'] == seed and seed not in records[identity]
                    assert math.isclose(info['success'], float(scores[seed, identity]['SR']))
                    assert math.isclose(info['NE'], float(scores[seed, identity]['NE']), abs_tol=1e-6)
                    assert record['fail_reason'] == scores[seed, identity]['fail_reason']
                    reference = np.asarray(info['reference_path'])[:, :2]
                    assert np.allclose(reference, np.asarray(cases[identity]['reference_path'])[:, :2], atol=1e-6)
                    # pred_path includes the pre-warmup root before action observations.
                    points = np.asarray(info['pred_path'])[1:]
                    video = videos.get((seed, identity))
                    if video:
                        stepsfile = CAMPAIGN/'visualization'/video['steps']
                        steps = [json.loads(x) for x in stepsfile.read_text().splitlines()]
                        assert len(steps) == len(points)
                        assert np.allclose(points, np.asarray([s['position'] for s in steps]), atol=1e-6)
                    records[identity][seed] = dict(seed=seed, success=info['success'], NE=info['NE'],
                        fail_reason=record['fail_reason'], points=points.tolist(), episode_seed=info['reproduction_episode_seed'],
                        video=str(CAMPAIGN/'visualization'/video['video']) if video else None,
                        source=dict(lmdb=str(dbpath), record_key=key.decode(), record_sha256=hashlib.sha256(value).hexdigest()))
    assert sum(len(v) for v in records.values()) == 240
    write(out/'trajectories.json', records)
    results = []
    for review in reviews:
        identity = review['episode_id']
        points = np.asarray(records[identity][2]['points'])
        segment, start, end = source_segment(points, review['frame'])
        row = dict(episode_id=identity, scene=cases[identity]['scene'], review=review,
            instruction=cases[identity]['instruction'], reference_path=cases[identity]['reference_path'],
            source_segment=segment.tolist(), source_start_frame=start, source_end_frame=end, seeds={})
        for seed, data in records[identity].items():
            match = local_frechet(segment, np.asarray(data['points']))
            match['nominated'] = match['distance_m'] <= .6 and match['minimum_height'] >= .55
            match.update(success=data['success'], fail_reason=data['fail_reason'], NE=data['NE'])
            row['seeds'][str(seed)] = match
        row['nominated_seeds'] = [int(s) for s, m in row['seeds'].items() if m['nominated']]
        row['failure_seeds'] = [int(s) for s, m in row['seeds'].items() if not m['success']]
        results.append(row)
    results.sort(key=lambda r: (-len(r['nominated_seeds']), -len(r['failure_seeds']), r['episode_id']))
    write(out/'nominations.json', results)
    with (out/'nominations.csv').open('w', newline='', encoding='utf-8-sig') as f:
        fields = ['episode_id','crossing_id','expected','actual','nominated_seed_count','nominated_seeds','failure_seeds']
        fields += [f'seed{s}_{k}' for s in range(5) for k in ['distance_m','success','fail_reason','start_frame','end_frame']]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in results:
            flat = dict(episode_id=r['episode_id'], crossing_id=r['review']['crossing_id'],
                expected=r['review']['expected'], actual=r['review']['actual'],
                nominated_seed_count=len(r['nominated_seeds']), nominated_seeds=','.join(map(str,r['nominated_seeds'])),
                failure_seeds=','.join(map(str,r['failure_seeds'])))
            for s, m in r['seeds'].items():
                for k in ['distance_m','success','fail_reason','start_frame','end_frame']:
                    flat[f'seed{s}_{k}'] = m[k]
            w.writerow(flat)
    manifest = dict(created_at=datetime.now(timezone.utc).isoformat(), git_commit=git,
        code_sha256=sha(__file__), original_campaign_commit=campaign['code_commit'],
        source_hashes={str(p):sha(p) for p in [ATTRIBUTION/'attribution_reviews.json', ATTRIBUTION/'evidence.json',
            CAMPAIGN/'manifest.json', CAMPAIGN/'episodes.csv', CAMPAIGN/'visualization/index.jsonl']},
        samples=48, seeds=list(range(5)), compared_records=240, gpu_used=False,
        protocol=dict(incoming_context_m=.8, outgoing_context_m=1.8, movement_simplification_m=.06,
            resampling_m=.12, nomination_frechet_threshold_m=.6, minimum_height_m=.55,
            status='geometric nomination, subject to map review; not human semantic labels'))
    write(out/'manifest.json', manifest)
    render(out)


def render(out):
    evidence = read(ATTRIBUTION/'evidence.json')
    records = {identity:{int(s):d for s,d in values.items()} for identity,values in read(out/'trajectories.json').items()}
    results = read(out/'nominations.json')
    os.environ.setdefault('MPLCONFIGDIR', str(out/'.matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image
    (out/'maps').mkdir()
    for group in range(0, len(results), 4):
        subset = results[group:group+4]
        fig, axes = plt.subplots(len(subset), 5, figsize=(20, 4.5*len(subset)), squeeze=False)
        for rowindex, r in enumerate(subset):
            scene = evidence['scenes'][r['scene']]
            floor = np.array(Image.open(io.BytesIO(base64.b64decode(scene['floorplan'].split(',',1)[-1]))))
            low, high = scene['low'], scene['high']
            center = next(c['position'] for c in scene['crossings'] if c['id'] == r['review']['crossing_id'])
            ref = np.array(r['reference_path'])[:, :2]
            segment = np.array(r['source_segment'])
            for seed in range(5):
                ax = axes[rowindex, seed]
                data = records[r['episode_id']][seed]
                pts = np.array(data['points'])
                m = r['seeds'][str(seed)]
                ax.imshow(floor, extent=[low[0],high[0],low[1],high[1]], origin='upper', alpha=.65)
                ax.plot(ref[:,0],ref[:,1],color='#12a15f',linewidth=2,alpha=.85)
                ax.plot(pts[:,0],pts[:,1],color='#145aad',linewidth=1.3,alpha=.85)
                ax.plot(segment[:,0],segment[:,1],color='#fa861c',linewidth=5,alpha=.5)
                local=pts[m['start_frame']:m['end_frame']+1]
                ax.plot(local[:,0],local[:,1],color='#c11a32',linewidth=2.5)
                ax.scatter([pts[0,0]],[pts[0,1]],marker='o',s=26,color='#145aad')
                ax.scatter([pts[-1,0]],[pts[-1,1]],marker='x',s=40,color='#145aad')
                ax.scatter([center[0]],[center[1]],marker='*',s=90,color='#9b13ce')
                ax.annotate(r['review']['crossing_id'],center,fontsize=8)
                ax.set_xlim(max(low[0],center[0]-5),min(high[0],center[0]+5))
                ax.set_ylim(max(low[1],center[1]-5),min(high[1],center[1]+5))
                ax.set_aspect('equal'); ax.tick_params(labelsize=7)
                ax.set_title(f"{r['episode_id']} | s{seed} {'SUCCESS' if data['success'] else 'FAIL'}\n"
                    f"d={m['distance_m']:.2f} m | f{m['start_frame']}:{m['end_frame']} | {data['fail_reason']}", fontsize=9)
        fig.suptitle('Green: reference | Blue: full trace | Orange: seed2 annotated segment | Red: best local match | Purple: Crossing',fontsize=13)
        fig.tight_layout(rect=[0,0,1,.975]); fig.savefig(out/'maps'/f'contact_{group//4+1:02d}.png',dpi=110);plt.close(fig)
    summary=dict(records=240,nominated_seed_count_histogram=dict(Counter(len(r['nominated_seeds']) for r in results)),
                 failure_seed_count_histogram=dict(Counter(len(r['failure_seeds']) for r in results)),
                 semantic_labels='not established; map review pending')
    write(out/'nomination_summary.json',summary)
    write(out/'status.json',dict(phase='nomination_complete_map_review_pending',gpu_used=False))
    print(json.dumps(summary,ensure_ascii=False),flush=True)
    for r in results:
        print(r['episode_id'],r['nominated_seeds'],r['failure_seeds'],
              ' '.join(f"{s}:{m['distance_m']:.2f}" for s,m in r['seeds'].items()),flush=True)


def extract_rgb(out):
    import cv2
    from PIL import Image, ImageDraw, ImageFont
    cv2.setNumThreads(1)
    records = read(out/'trajectories.json')
    results = [r for r in read(out/'nominations.json') if len(r['nominated_seeds']) == 5]
    target = out/'rgb_shortlist_v2'
    target.mkdir(exist_ok=False)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
    inventory = []
    for r in results:
        canvas = Image.new('RGB', (1280, 560), 'white')
        draw = ImageDraw.Draw(canvas)
        source_point = np.asarray(records[r['episode_id']]['2']['points'][r['review']['frame']])[:2]
        entry = dict(episode_id=r['episode_id'], image=f"rgb_shortlist_v2/{r['episode_id']}.jpg", seeds={})
        for j, seed in enumerate([2, 3]):
            data = records[r['episode_id']][str(seed)]
            match = r['seeds'][str(seed)]
            points = np.asarray(data['points'])
            start, end = match['start_frame'], match['end_frame']
            decision = start + int(np.argmin(np.linalg.norm(points[start:end+1,:2]-source_point,axis=1)))
            if seed == 2:
                decision = r['review']['frame']
            steps = [json.loads(line) for line in (Path(data['video']).parent/'steps.jsonl').read_text().splitlines()]
            valid = [s['frame'] for s in steps if not s['terminal'] and not s.get('rgb_reused')]
            last = min(end+16, max(valid))
            choices = [f for f in valid if decision <= f <= last]
            assert len(choices) >= 4
            frames = [choices[i] for i in np.linspace(0,len(choices)-1,4).round().astype(int)]
            assert frames == sorted(set(frames)) and set(frames) <= set(valid)
            capture = cv2.VideoCapture(data['video'])
            assert capture.isOpened(), data['video']
            assert int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) == len(points)
            for k, frame in enumerate(frames):
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = capture.read()
                assert ok, (r['episode_id'],seed,frame)
                rgb = cv2.cvtColor(image[:480,:640], cv2.COLOR_BGR2RGB)
                canvas.paste(Image.fromarray(rgb).resize((320,240)), (k*320,j*280+40))
                draw.text((k*320+5,j*280+20), f'seed{seed} frame{frame}', fill='#173149', font=font)
            capture.release()
            entry['seeds'][str(seed)] = dict(frames=frames, source_video=data['video'], source_sha256=sha(data['video']))
        draw.text((5,0),r['episode_id'],fill='black',font=font)
        canvas.save(out/entry['image'],quality=90)
        inventory.append(entry)
    write(target/'manifest.json',inventory)
    shutil.copy2(__file__,out/'source/rgb_export_v2.py')
    print(json.dumps(dict(tasks=len(inventory),videos=2*len(inventory),extracted_frames=8*len(inventory))))


if __name__ == '__main__':
    main()
