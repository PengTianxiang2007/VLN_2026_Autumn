"""Export paired formal scores and time-aligned online recovery evidence to a static site."""
import argparse
import csv
import json
from pathlib import Path
import shutil
from statistics import mean
from zipfile import ZipFile, ZIP_DEFLATED

from PIL import Image
from fontTools import subset
from fontTools.ttLib import TTFont

from export_serial_paired_media import BASE, baseline_index

ROOT = Path(__file__).resolve().parents[1]


def read(p):
    return p.open(encoding='utf-8').read()


def load(p):
    return json.loads(read(p))


def lines(p):
    return [json.loads(line) for line in read(p).splitlines() if line.strip()]


def xy(position):
    return [round(float(v), 4) for v in position[:2]]


def timeline(attempt, observations, images, translations):
    events = lines(attempt / 'events.jsonl')
    main = {(o['leg'], o['index']): o['sequence'] for o in observations if not o['local']}
    starts = {leg: seq for (leg, index), seq in main.items() if index == 0}
    reviews, nodes, jev, recovery = [], [], [], []
    rollback_boundaries = {(e['leg'], e['action_count']) for e in events if e['kind']=='rollback'}
    last = 0
    folders = iter(sorted(attempt.glob('recovery_*')))
    for e in events:
        kind, leg = e['kind'], e['leg']
        if kind == 'jev':
            last = main[leg, e['frame']]
            jev.append([last, e['probability'], e.get('filtered')])
        elif kind == 'node':
            n = e['node']
            last = main[leg, n['retained_at']]
            nodes.append([main[leg, n['index']], last, leg, n['id'], n['terminal_node']])
        elif kind in ('deviation', 'deviation_gate'):
            ans = e.get('answer')
            reviews.append(dict(type=kind, seq=last, action=e['action_count'], leg=leg,
                                node=e.get('node'), previous=e.get('previous'),
                                terminal=e.get('terminal', False) or (e['action_count'] == events[-1]['action_count']
                                         and (leg,e['action_count']) not in rollback_boundaries),
                                answer=ans))
        elif kind == 'route_unresolved':
            reviews.append(dict(type=kind, seq=last, action=e['action_count'], leg=leg,
                                status=e['selection']['status']))
        elif kind == 'rollback':
            folder = next(folders)
            decision = load(folder / 'decision.json')
            sel = decision['selection']
            check = decision['checkpoint']['sequence']
            assert check == main[leg, e['frame']]
            after = last if e['ended'] else last + 1
            if not e['ended']:
                landing = observations[after]
                assert landing['index'] == 0
                expected_local = sel['status']=='selected'
                assert landing['local'] == expected_local and landing['leg'] == (leg if expected_local else leg+1)
            key = folder.name
            view_dir = attempt / 'checkpoint_views' / f'{check:06}'
            views = []
            for view in ('C_left70', 'C_front', 'C_right70'):
                if sel['status'] in ('input_incomplete','terminal_during_restore'):
                    break  # No branch images when input is incomplete or rollback ends the task.
                name = f'{key}_{view}.jpg'
                with Image.open(view_dir / (view + '.png')) as image:
                    image.convert('RGB').save(images / name, quality=84)
                views.append(name)
            instruction = sel.get('recovery_instruction_en')
            record = dict(type=kind, seq=last, after=after, target=check, action=e['action_count'],
                          leg=leg, node=e['target'], views=views, number=len(recovery) + 1,
                          chosen=sel.get('selected_branch_id'), tried=sel.get('previous_attempt',{}).get('branch_id'),
                          status=sel['status'], instruction={'en': instruction, 'zh': translations[instruction] if instruction else None})
            recovery.append(record)
            reviews.append(record)
        elif kind == 'handoff':
            reviews.append(dict(type=kind, seq=starts[leg + 1], action=e['action_count'], leg=leg,
                                localSteps=e['local_steps'], reason=e['reason']))
        elif kind == 'pending_alarm_superseded':
            reviews.append(dict(type=kind, seq=last, action=e['action_count'], leg=leg))
    assert next(folders, None) is None
    return events[0]['instruction'], reviews, nodes, jev, recovery


def add_map(directory, scene):
    source = ROOT / 'outputs/offline_route_dataset/v001/run_20261118_01/geometry' / scene
    g = load(source / 'geometry.json')
    (directory / 'maps').mkdir(exist_ok=True)
    shutil.copyfile(source / 'floorplan.png', directory / 'maps' / (scene + '.png'))
    return {key: g[key] for key in ('width', 'height', 'low', 'high', 'resolution')}


def make_site(snapshot, record):
    output = snapshot.parent
    camp = output.parent.parent
    frozen = load(snapshot)
    media = load(output / 'media_index.json')
    originals = baseline_index()
    translations = load(record / 'translations.json')
    tasks = load(ROOT / 'experiments/crossing_analysis/seed2_annotation69/instructions_zh.json')['cases']
    tasks.update(translations['tasks'])
    with (record.parent.parent / 'baseline203.csv').open() as file:
        baseline = {r['episode_id']: r for r in csv.DictReader(file)}
    cases, maps, pairs = [], {}, []
    for relative in frozen['attempts']:
        attempt = camp / relative
        result = load(attempt / 'result.json')
        eid = result['episode_id']
        b, original = baseline[eid], originals[eid]
        m = result['metrics']
        assert m['reproduction_episode_seed'] == int(b['episode_seed'])
        obs = lines(attempt / 'observations.jsonl')
        old = lines(BASE / original['steps'])
        assert [o['sequence'] for o in obs] == list(range(len(obs)))
        assert len(obs) == media[eid]['current']['count'] and len(old) == media[eid]['original']['count']
        instruction, events, nodes, jev, recoveries = timeline(attempt, obs, output / 'media' / eid, translations['recovery'])
        assert instruction == original['instruction'] and len(recoveries) == result['recoveries']
        scene = b['scene']
        if scene not in maps:
            maps[scene] = add_map(output, scene)
        case = dict(id=eid, scene=scene, instruction={'en': instruction, 'zh': tasks[eid]},
                    reference=[xy(p) for p in m['reference_path']], events=events,
                    nodes=nodes, jev=jev, rollbacks=result['recoveries'], handoffs=result['handoffs'])
        case['current'] = dict(media[eid]['current'], sr=int(m['success']), spl=m['spl'], ne=m['NE'], tl=m['TL'],
                               end=m['fail_reason'], points=[xy(o['position']) for o in obs],
                               local=[o['sequence'] for o in obs if o['local']])
        case['original'] = dict(media[eid]['original'], sr=int(float(b['SR'])), spl=float(b['SPL']),
                                ne=float(b['NE']), tl=float(b['TL']), end=b['fail_reason'],
                                points=[xy(o['position']) for o in old])
        pairs.append(dict(episode_id=eid, seed=2, episode_seed=b['episode_seed'],
                          **{version+'_'+k: case[version][k] for version in ('current','original')
                             for k in ('sr','spl','ne','tl','end')}, rollbacks=result['recoveries'], handoffs=result['handoffs']))
        cases.append(case)
    assert len({c['id'] for c in cases}) == len(cases)
    skips = []
    for eid in frozen['skip_ids']:
        failure = load(camp / 'failures' / (eid + '.json'))
        error = failure['error']
        if 'JEV HTTP 520' in error:
            reason = 'http520'
        elif 'yaw drift' in error:
            reason = 'yaw'
        else:
            raise ValueError('Add a bilingual skip reason for ' + eid)
        skips.append(dict(id=eid, reason=reason))
    summary = {v:{'success':sum(c[v]['sr'] for c in cases),'spl':mean(c[v]['spl'] for c in cases)}
               for v in ('current','original')}
    summary.update(gains=sum(c['current']['sr']>c['original']['sr'] for c in cases),
                   losses=sum(c['current']['sr']<c['original']['sr'] for c in cases),
                   rollbacks=sum(c['rollbacks'] for c in cases), handoffs=sum(c['handoffs'] for c in cases),
                   rollbackCases=sum(bool(c['rollbacks']) for c in cases))
    data = dict(at=frozen['as_of'], total=frozen['campaign_size'], cases=cases, skips=skips, maps=maps, summary=summary)
    if 'selection' in frozen:
        data.update(selection=frozen['selection'], scored=frozen['scored'], skipCount=len(frozen['campaign_skip_ids']))
    text = json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    (output / 'data.js').write_text('const DATA = '+text+';\n')
    with (output / 'paired_results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=pairs[0]);writer.writeheader();writer.writerows(pairs)
    for source, dest in [('serial_paired_snapshot.html','index.html'),('serial_paired_snapshot.js','player.js')]:
        shutil.copyfile(ROOT / 'core' / source, output / dest)
    font = load(ROOT / 'core/crossing_visualization_template.json')
    with TTFont(font['font'], fontNumber=0) as f:
        sub = subset.Subsetter()
        sub.populate(text=''.join(sorted(set(text+read(output/'index.html')+read(output/'player.js')))))
        sub.subset(f)
        f.save(output/'replay.ttf')
    (output/'font_license.json').write_text(json.dumps({'license':read(Path(font['font_license']))}, ensure_ascii=False))
    with ZipFile(output/'paired_results.zip','w',ZIP_DEFLATED) as archive:
        archive.write(output/'paired_results.csv','paired_results.csv')
    assets = ['data.js','player.js','paired_results.zip','replay.ttf','font_license.json']
    assets += [str(p.relative_to(output)) for folder in ('media','maps') for p in sorted((output/folder).rglob('*')) if p.is_file()]
    with ZipFile(output/'replay_offline.zip','w',ZIP_DEFLATED,compresslevel=1) as archive:
        for filename in ['index.html','paired_results.csv',*assets]:
            archive.write(output/filename,filename)
    assets.append('replay_offline.zip')
    (output/'online_manifest.json').write_text(json.dumps(dict(html='index.html',assets=assets),indent=2)+'\n')
    print(json.dumps(summary), 'assets', len(assets))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('snapshot',type=Path)
    p.add_argument('record',type=Path)
    a=p.parse_args()
    make_site(a.snapshot.resolve(),a.record.resolve())
