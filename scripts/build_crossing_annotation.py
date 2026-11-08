"""Build the fixed seed2 39-failure + 30-success offline human annotation file.

CPU only. Reuses recorded RGB/positions and never prepopulates historical labels.
"""
import argparse
import base64
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / 'outputs/reproduction/streamvln_scene250_5seeds_20261101_v2'
EVIDENCE = ROOT / 'outputs/checkpoint_review/seed2_crossing_attribution_20261103/evidence.json'
COMMON = ROOT / 'outputs/checkpoint_review/seed2_multiseed48/run_20261106_01/common_failures.csv'
EXPERIMENT = ROOT / 'experiments/crossing_analysis/seed2_annotation69'
SALT = 'crossing69-success-v1:'


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def compact(data):
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')


def choose_samples():
    scores = list(csv.DictReader((CAMPAIGN / 'episodes.csv').open()))
    by_id = {}
    for r in scores:
        by_id.setdefault(r['episode_id'], {})[int(r['run_seed'])] = r
    common = list(csv.DictReader(COMMON.open(encoding='utf-8-sig')))
    failures = sorted(r['episode_id'] for r in common if int(r['failed_seed_count']) >= 3)
    prior = read(EVIDENCE.parent / 'attribution_reviews.json')
    assert set(failures) <= {r['episode_id'] for r in prior if r['status'] == 'crossing'}
    successes = []
    for scene in sorted({r['scene'] for r in scores}):
        pool = [eid for eid, seeds in by_id.items() if seeds[2]['scene'] == scene and float(seeds[2]['SR']) == 1]
        assert len(pool) >= 3
        successes.extend(sorted(pool, key=lambda eid: hashlib.sha256((SALT + eid).encode()).hexdigest())[:3])
    result = []
    for group, ids in [('failure', failures), ('success', sorted(successes))]:
        for eid in ids:
            seeds = by_id[eid]
            assert set(seeds) == set(range(5))
            failed = [s for s in range(5) if float(seeds[s]['SR']) == 0]
            assert (2 in failed and len(failed) >= 3) if group == 'failure' else 2 not in failed
            result.append(dict(episode_id=eid, scene=seeds[2]['scene'], seed=2, group=group, failed_seeds=failed))
    assert len(failures) == 39 and len(successes) == 30 and len({r['episode_id'] for r in result}) == 69
    return result


def build(out):
    import cv2
    cv2.setNumThreads(1)
    out.mkdir(parents=True, exist_ok=False)
    (out / 'media').mkdir()
    write(out / 'status.json', dict(phase='preparing', created_at=now(), gpu_used=False))
    try:
        samples = choose_samples()
        write(out / 'samples.json', samples)
        sample_target = EXPERIMENT / 'samples.json'
        if sample_target.exists() and read(sample_target) != samples:
            raise ValueError('Refusing to change previously fixed sample list')
        write(sample_target, samples)
        index = {r['episode_id']: r for r in [json.loads(line) for line in (CAMPAIGN / 'visualization/index.jsonl').read_text().splitlines()] if r['seed'] == 2}
        evidence = read(EVIDENCE)
        evidence_cases = {c['episode_id']: c for c in evidence['cases']}
        maps = {scene: dict(geometry={k: m[k] for k in ('width', 'height', 'low', 'high', 'resolution')}, image=m['floorplan']) for scene, m in evidence['scenes'].items()}
        source_paths = [COMMON, EVIDENCE, EVIDENCE.parent / 'attribution_reviews.json', CAMPAIGN / 'episodes.csv', CAMPAIGN / 'visualization/index.jsonl', CAMPAIGN / 'manifest.json']
        input_hashes = {str(p.relative_to(ROOT)): sha(p) for p in source_paths}
        cases, audits = [], []
        for i, sample in enumerate(samples):
            eid = sample['episode_id']
            entry = index[eid]
            assert entry['scene'] == sample['scene'] and entry['status'] == 'complete'
            paths = {name: CAMPAIGN / 'visualization' / entry[name] for name in ('video', 'steps', 'detail')}
            hashes = {name: sha(path) for name, path in paths.items()}
            detail = read(paths['detail'])
            steps = [json.loads(line) for line in paths['steps'].read_text().splitlines()]
            assert detail['seed'] == 2 and detail['episode_id'] == eid
            assert bool(detail['metrics']['success']) == (sample['group'] == 'success')
            assert steps == evidence_cases[eid]['steps']
            assert [s['frame'] for s in steps] == list(range(len(steps)))
            assert detail['pred_path'][1:] == [s['position'] for s in steps]
            assert detail['reference_path'] == evidence_cases[eid]['reference_path']
            assert len(detail['reference_path']) >= 2 and len(steps) == entry['frames'] == detail['frames']
            capture = cv2.VideoCapture(str(paths['video']))
            urls, frames, encoded_bytes = [], [], 0
            try:
                assert capture.isOpened()
                assert [int(capture.get(3)), int(capture.get(4))] == [960, 640]
                assert int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) == len(steps)
                assert abs(capture.get(cv2.CAP_PROP_FPS) - detail['fps']) < 1e-6
                for step in steps:
                    ok, composite = capture.read()
                    if not ok:
                        raise ValueError('Video shorter than steps: ' + eid)
                    rgb = composite[:480, :640].copy()
                    ok, encoded = cv2.imencode('.webp', rgb, [cv2.IMWRITE_WEBP_QUALITY, 90])
                    if not ok:
                        raise ValueError('Image encoding failed')
                    raw = encoded.tobytes()
                    encoded_bytes += len(raw)
                    urls.append('data:image/webp;base64,' + base64.b64encode(raw).decode())
                    frames.append(dict(step, video_time_s=step['frame'] / detail['fps'], heading=None,
                                       image_sha256=hashlib.sha256(raw).hexdigest()))
                assert not capture.read()[0], 'Unexpected extra video frame'
            finally:
                capture.release()
            media_path = out / 'media' / (eid + '.json')
            media_path.write_text(compact(urls))
            cases.append(dict(sample, instruction=detail['instruction'], reference_path=detail['reference_path'],
                              frames=frames, fps=detail['fps'], episode_seed=detail['episode_seed'],
                              run_id=detail['run_id'], source={k: str(p.relative_to(ROOT)) for k, p in paths.items()}, source_sha256=hashes))
            audits.append(dict(episode_id=eid, frames=len(frames), rgb_reused=sum(s['rgb_reused'] for s in steps),
                               terminal_frames=sum(s['terminal'] for s in steps), media_sha256=sha(media_path),
                               encoded_bytes=encoded_bytes, source_sha256=hashes))
            write(out / 'status.json', dict(phase='encoding', completed=i + 1, total=69, frames=sum(c['frames'] for c in audits), gpu_used=False))
            print(json.dumps(dict(completed=i + 1, episode_id=eid, frames=len(frames)), ensure_ascii=False), flush=True)
        for p in source_paths:
            assert sha(p) == input_hashes[str(p.relative_to(ROOT))], 'Input changed during export'
        dataset_id = hashlib.sha256(compact(dict(samples=samples, source_hashes=input_hashes)).encode()).hexdigest()
        config = read(ROOT / 'core/crossing_visualization_template.json')
        summary = dict(samples=69, failures=39, successes=30, scenes=len(maps), frames=sum(len(c['frames']) for c in cases),
                       reused_frames=sum(a['rgb_reused'] for a in audits), initially_annotated=0, gpu_used=False)
        data = dict(schema='crossing-annotation-data-v1', dataset_id=dataset_id, created_at=now(), summary=summary,
                    maps=maps, cases=cases, font_license=Path(config['font_license']).read_text())
        annotations = dict(schema='crossing-human-annotations-v1', dataset_id=dataset_id, document_id=str(uuid.uuid4()),
                           created_at=now(), updated_at=now(), exported_at=None,
                           cases={c['episode_id']: dict(completed=False, marks=[]) for c in cases},
                           resume=dict(episode_id=cases[0]['episode_id'], frame=0))
        write(out / 'data.json', data)
        write(out / 'initial_annotations.json', annotations)
        # Use the existing fontTools environment; no installation or global environment changes.
        template = (ROOT / 'core/crossing_annotation_page.html').read_text()
        controller = (ROOT / 'core/crossing_annotation.js').read_text()
        text_file = out / 'font_characters.txt'
        text_file.write_text(''.join(sorted(set(template + controller + compact(data)))))
        font_path = out / 'annotation_font.ttf'
        font_code = 'from fontTools import subset; from fontTools.ttLib import TTFont; from pathlib import Path; import sys; f=TTFont(sys.argv[1],fontNumber=0); s=subset.Subsetter(); s.populate(text=Path(sys.argv[2]).read_text()); s.subset(f); f.save(sys.argv[3])'
        subprocess.run([str(ROOT / 'backbone/streamvln/.venv/bin/python'), '-c', font_code, config['font'], str(text_file), str(font_path)], check=True)
        page = template.replace('__FONT__', 'data:font/ttf;base64,' + base64.b64encode(font_path.read_bytes()).decode())
        page = page.replace('__DATA__', compact(data)).replace('__ANNOTATIONS__', compact(annotations)).replace('__SCRIPT__', controller)
        head, tail = page.split('__MEDIA__')
        html = out / 'crossing_annotation_69.html'
        with html.open('w') as stream:
            stream.write(head)
            for c in cases:
                stream.write('<script id="media-' + c['episode_id'] + '" type="application/json">')
                stream.write((out / 'media' / (c['episode_id'] + '.json')).read_text())
                stream.write('</script>\n')
            stream.write(tail)
        source_hashes = {}
        for rel in ['scripts/build_crossing_annotation.py', 'core/crossing_annotation_page.html', 'core/crossing_annotation.js', 'experiments/crossing_analysis/seed2_annotation69/README.md', 'experiments/crossing_analysis/seed2_annotation69/samples.json']:
            dest = out / 'source' / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dest)
            source_hashes[rel] = sha(dest)
        (out / 'workspace_status.txt').write_bytes(subprocess.check_output(['git', 'status', '--short'], cwd=ROOT))
        (out / 'workspace_diff.patch').write_bytes(subprocess.check_output(['git', 'diff', 'HEAD', '--binary'], cwd=ROOT))
        write(out / 'manifest.json', dict(dataset_id=dataset_id, created_at=now(), summary=summary, cases=audits,
                                         input_sha256=input_hashes, source_sha256=source_hashes,
                                         export_git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                                         reproduction_git_commit=read(CAMPAIGN / 'manifest.json').get('code_commit'),
                                         success_selection=dict(per_scene=3, method='SHA256 ascending first 3', salt=SALT),
                                         image_encoding=dict(format='WebP', quality=90, crop_xywh=[0, 0, 640, 480], all_frames=True),
                                         protocol=dict(seed=2, failure_minimum_failed_seeds=3, annotations_initially_empty=True, heading='not_recorded', reused_rgb_marking=False),
                                         html_sha256=sha(html), html_bytes=html.stat().st_size))
        write(out / 'summary.json', summary)
        write(out / 'status.json', dict(phase='exported_pending_browser_check', finished_at=now(), summary=summary))
        print(json.dumps(dict(html=str(html),mib=round(html.stat().st_size/1024**2,2),**summary)),flush=True)
    except BaseException as exc:
        write(out / 'status.json', dict(phase='failed', error=str(exc), updated_at=now(), gpu_used=False))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.output.resolve())
