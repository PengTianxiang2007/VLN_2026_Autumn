"""Export synchronized floorplan and multiview previews of the frozen route dataset."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
RUN = Path('offline_route_dataset/v001/run_20261118_01')
ANALYSIS = ROOT / 'outputs' / RUN
DATA = ANALYSIS / 'dataset'
VERSION = Path('exports/replay_20261118_01')
OUT = ANALYSIS / VERSION
RECORD = ROOT / 'experiments' / RUN / VERSION


def read(path):
    return json.loads(path.read_text())


def observations(eid):
    with (DATA / 'inputs' / eid / 'observations.jsonl').open() as stream:
        return [json.loads(line) for line in stream]


def make_atlas(record):
    tiles = [record['native_front'], *record['views_360']]
    assert [v['view_id'] for v in tiles[1:]] == list(range(8))
    assert [v['view_id'] for v in record['views_180']] == [1, 0, 7]
    atlas = Image.new('RGB', (960, 720))
    for i, view in enumerate(tiles):
        with Image.open(DATA / view['image']) as image:
            assert image.size == (640, 480)
            atlas.paste(image.convert('RGB').resize((320, 240), Image.Resampling.BILINEAR),
                        ((i % 3) * 320, (i // 3) * 240))
    atlas.save(OUT/'frames'/record['episode_id']/f"{record['step']:04}.webp",
               format='WEBP', quality=65, method=1)


def build_media(ids):
    (OUT/'frames').mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=6) as workers:
        for eid in ids:
            (OUT/'frames'/eid).mkdir()
            list(workers.map(make_atlas, observations(eid)))
            print(eid, flush=True)


def build_page(ids):
    maps = {}
    tasks = []
    older = read(ROOT/'experiments/crossing_analysis/seed2_annotation69/instructions_zh.json')['cases']
    older = {**older, **read(RECORD/'instructions_zh_additions.json')}
    newer = read(ROOT/'experiments/oracle_recovery/auto_branch_v001/run_20261117_04_pair200/exports/route_choice56_20261117_01/instructions_zh.json')
    english_notes = read(RECORD/'reasons_en.json')
    (OUT/'maps').mkdir(exist_ok=True)
    for eid in ids:
        task = read(DATA/'inputs'/eid/'task.json')
        scene = task['scene']
        if scene not in maps:
            source = ANALYSIS/'geometry'/scene
            geometry = read(source/'geometry.json')
            maps[scene] = {k: geometry[k] for k in ('low','high','resolution','width','height')}
            shutil.copyfile(source/'floorplan.png', OUT/'maps'/f'{scene}.png')
        episode = read(DATA/'evaluation/episodes'/f'{eid}.json')
        annotation = episode['annotation']
        frames = observations(eid)
        assert [r['robot_pose']['position_world_m'] for r in frames] == episode['actual_path']
        assert [r['step'] for r in frames] == list(range(len(frames)))
        def pose(record, name):
            p = record[name]
            return [*p['position_world_m'], p['heading_deg'], *p['quaternion_wxyz']]
        tasks.append(dict(id=eid, scene=scene, number=annotation['number'], batch=annotation['source_batch'],
            group=annotation['subset'], subtype=annotation['subtype'], confidence=annotation['confidence'],
            instruction=[(older if annotation['source_batch']=='older48' else newer)[eid],task['instruction']],
            reason=[annotation['reason_zh'],english_notes[str(annotation['number'])]],
            reference=episode['reference_path'], robot=[pose(r,'robot_pose') for r in frames],
            camera=[pose(r,'native_camera_pose') for r in frames],
            seconds=[r['episode_elapsed_s'] for r in frames],
            events=[dict(anchor=e['decision_step_estimate'],confirm=e['confirmed_wrong_step'],
                         interval=e['decision_interval_steps']) for e in annotation['events']]))
    data = json.dumps(dict(tasks=tasks,maps=maps),ensure_ascii=False,separators=(',',':'))
    (OUT/'tasks.js').write_text('const REPLAY = '+data+';\n')
    shutil.copyfile(ROOT/'core/offline_route_replay.html', OUT/'index.html')
    for name in ('style.css','player.js'):
        shutil.copyfile(ROOT/'core'/('offline_route_replay_'+name), OUT/name)
    # The headless review browser has no system CJK fonts. Cover task-specific
    # instructions and reasons as well as the static interface.
    from fontTools import subset
    from fontTools.ttLib import TTFont
    source = read(ROOT/'core/crossing_visualization_template.json')
    charset = set(''.join((OUT/name).read_text() for name in ('index.html','player.js','tasks.js')))
    with TTFont(source['font'], fontNumber=0) as font:
        sub = subset.Subsetter()
        sub.populate(text=''.join(sorted(charset)))
        sub.subset(font)
        font.save(OUT/'replay.ttf')
    (OUT/'font_license.json').write_text(json.dumps(
        {'font':'WenQuanYi Micro Hei','license':Path(source['font_license']).read_text()},
        ensure_ascii=False,indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['media','page'])
    stage = parser.parse_args().stage
    ids = (DATA/'subsets/all_selected.txt').read_text().splitlines()
    assert len(set(ids)) == len(ids) == 53
    if stage == 'media':
        build_media(ids)
    else:
        build_page(ids)
