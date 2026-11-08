"""Build a self-contained paired semantic-delay review from existing records only."""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_oracle_replay import Media, yaw_wxyz


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--campaign', type=Path, required=True)
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    campaign = args.campaign.resolve()
    output = args.output or campaign / 'oracle_paired_delay10_offline.html'
    summary = json.loads((campaign / 'summary.json').read_text())
    manifest = json.loads((campaign / 'manifest.json').read_text())
    assert summary['complete'] and len(summary['results']) == 30
    media = Media()
    data = dict(version=1, run=campaign.name, seed=manifest['seed'],
                groups=summary['groups'], paired=summary['fully_triggered_pairs'],
                physics_dt=summary['simulation_time']['physics_dt_seconds'],
                git_head=manifest['git_head'], cases=[], scenes={}, images=[])
    validations = []
    for case in manifest['cases']:
        eid = case['episode_id']
        case_dir = campaign / 'oracle_records' / eid
        review_dirs = sorted((case_dir / 'trunk').glob('review_*'))
        reviews = []
        for folder in review_dirs:
            if (folder / 'response.json').exists():
                req = json.loads((folder / 'request.json').read_text())
                rsp = json.loads((folder / 'response.json').read_text())
                reviews.append(dict(a=req['action_index'], ticks=req['physics_ticks'],
                                    stage=rsp['stage'], reason=rsp['reason'],
                                    target=rsp.get('target_id')))
        onset = next((r for r in reviews if r['stage'] == 'onset'), None)
        clear = next((r for r in reviews if r['stage'] == 'clear'), None)
        scene = case['scene']
        if scene not in data['scenes']:
            src = ROOT / 'outputs/checkpoint_review/seed2_25_20261103/scenes' / scene
            geometry = json.loads((src / 'geometry.json').read_text())
            data['scenes'][scene] = dict(geometry={k: geometry[k] for k in ('width', 'height', 'resolution', 'low', 'high')},
                image='data:image/png;base64,' + base64.b64encode((src / 'floorplan.png').read_bytes()).decode())
        item = dict(id=eid, scene=scene, instruction=case['instruction'],
                    reference=case['reference_path'], targets=case['targets'],
                    historical=case['calibration'] if 'calibration' in case else None,
                    onset=onset, clear=clear, reviews=reviews, stages={}, runs={})

        def trace(folder):
            actions = {r['action_index']: r['action'] for r in read_jsonl(folder / 'actions.jsonl')}
            nodes = []
            for obs in read_jsonl(folder / 'observations.jsonl'):
                frame = Path(obs['frame'])
                if not frame.is_absolute():
                    frame = folder / frame
                action = actions.get(obs['action_index'], {})
                code = 0 if 'stop' in action else (action.get('move_by_discrete') or [-1])[0]
                if frame.is_file():
                    image, rgb_reused = media.add(frame), False
                else:
                    assert obs.get('terminal') and nodes, (folder, frame)
                    image, rgb_reused = nodes[-1]['image'], True
                nodes.append(dict(a=obs['action_index'], p=[round(v, 6) for v in obs['position']],
                    yaw=yaw_wxyz(obs.get('rotation')), image=image, rgb_reused=rgb_reused,
                    segment=obs['intervention_count'], ticks=obs['physics_ticks'],
                    terminal=obs.get('terminal', False), phase='walk',
                    action={0: 'STOP', 1: '前进', 2: '左转', 3: '右转', -1: '结束'}.get(code, '未知')))
            assert nodes and all(a['ticks'] <= b['ticks'] for a, b in zip(nodes, nodes[1:]))
            return nodes

        item['trunk'] = dict(nodes=trace(case_dir / 'trunk'), events=[])
        for arm in manifest['arms']:
            result = next(r for r in summary['results'] if r['episode_id'] == eid and r['arm'] == arm)
            if result['triggered']:
                snap = json.loads((case_dir / f'snapshot_{arm}.json').read_text())
                review = next(r for r in reviews if r['a'] == snap['action_index'])
                assert review['stage'] == arm
                item['stages'][arm] = dict(a=snap['action_index'], ticks=snap['physics_ticks'],
                    reason=review['reason'], delta_actions=result['first_delay_actions'],
                    delta_seconds=result['first_delay_sim_seconds'], delta_batches=result['first_delay_model_batches'],
                    distance=result['first_reference_distance_m'], target=snap['target_id'])
                nodes = trace(case_dir / arm)
            else:
                nodes = item['trunk']['nodes']
            events = []
            for iv in result['interventions']:
                before = [i for i, n in enumerate(nodes) if n['a'] == iv['action_index'] and n['segment'] == iv['number'] - 1]
                after = [i for i, n in enumerate(nodes) if n['a'] == iv['action_index'] and n['segment'] == iv['number']]
                if not after:
                    # Later corrections record their exact post-settle pose/RGB in correction_*/,
                    # while observations.jsonl resumes at the next action boundary.
                    assert len(before) == 1
                    post = dict(nodes[before[0]], p=[round(v, 6) for v in iv['after_position']],
                        yaw=yaw_wxyz(iv['after_rotation']), segment=iv['number'],
                        ticks=iv['physics_ticks'], terminal=False, phase='after', rgb_reused=False,
                        image=media.add(case_dir / arm / f'correction_{iv["number"]:02d}' / 'after.jpg'))
                    nodes.insert(before[0] + 1, post)
                    after = [before[0] + 1]
                assert len(before) == len(after) == 1, (eid, arm, iv['number'])
                b, a = before[0], after[0]
                assert a == b + 1
                assert math.dist(nodes[b]['p'], iv['before_position']) < .00001
                assert math.dist(nodes[a]['p'], iv['after_position']) < .00001
                nodes[b]['phase'], nodes[a]['phase'] = 'before', 'after'
                events.append(dict(number=iv['number'], a=iv['action_index'], before=b, after=a,
                    before_ticks=nodes[b]['ticks'], after_ticks=nodes[a]['ticks'],
                    target=iv['target_id'], goal_distance=iv['goal_distance_m'],
                    inside=iv['goal_distance_m'] < 3, memory=iv['memory_unchanged'],
                    reason=iv['response']['reason'], onset=iv['event']['action_index'],
                    onset_reason=iv['event']['reason']))
                assert iv['memory_unchanged']
            metrics = {k: result['metrics'][k] for k in ('success', 'NE', 'TL', 'spl', 'fail_reason')}
            item['runs'][arm] = dict(nodes=nodes, events=events, triggered=result['triggered'],
                metrics=metrics, actions=result['actions'], physics_ticks=result['physics_ticks'],
                untriggered_reason=result.get('untriggered_reason'),
                evidence=result.get('untriggered_evidence'),
                first_goal_distance=result.get('first_correction_goal_distance_m'),
                last_goal_distance=result.get('last_correction_goal_distance_m'),
                post_last_actions=result.get('post_last_correction_actions'))
            # Verify that every visual walking edge remains within a single correction segment.
            for i in range(1, len(nodes)):
                if nodes[i]['segment'] != nodes[i - 1]['segment']:
                    assert any(e['before'] == i - 1 and e['after'] == i for e in events)
            validations.append(dict(episode_id=eid, arm=arm, nodes=len(nodes), corrections=len(events)))
        data['cases'].append(item)
    print(json.dumps(dict(phase='encoding_images', unique_images=len(media.jobs)), ensure_ascii=False), flush=True)
    data['images'] = media.encode()
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    template_path = ROOT / 'core/oracle_paired_replay.html'
    template = template_path.read_text()
    assert template.count('__PAYLOAD__') == 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace('__PAYLOAD__', payload))
    build = dict(html=str(output), bytes=output.stat().st_size,
        sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        source_summary_sha256=hashlib.sha256((campaign / 'summary.json').read_bytes()).hexdigest(),
        builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        template_sha256=hashlib.sha256(template_path.read_bytes()).hexdigest(),
        git_head_at_experiment_prepare=manifest['git_head'],
        cases=len(data['cases']), group_results=30, corrected_branches=22, untriggered_results=8,
        correction_events=sum(v['corrections'] for v in validations), unique_images=len(data['images']),
        self_contained=True, no_model_or_simulator_started=True, traces=validations)
    assert build['correction_events'] == 33
    output.with_suffix('.build.json').write_text(json.dumps(build, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in build.items() if k != 'traces'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
