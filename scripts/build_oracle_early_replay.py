"""Export only the original 10/10 successful early-correction group, offline.

Reuse recorded media from the existing audited replay. Validate its early group
against the original results and each raw action/intervention record first.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / 'outputs/oracle_crossing/seed2_10_multi_20261103'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output):
    source_path = CAMPAIGN / 'report/results.json'
    replay_path = ROOT / 'outputs/oracle_crossing/oracle_replay_v2_20261104.html'
    source = json.loads(source_path.read_text())
    manifest_path = CAMPAIGN / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    assert source['summary']['oracle_success'] == source['summary']['oracle_complete'] == 10
    assert source['summary']['correction_events'] == 18
    old = json.loads(re.search(r'<script id="replay-data" type="application/json">(.*?)</script>', replay_path.read_text(), re.S).group(1))
    data = dict(version=1, campaign=CAMPAIGN.name, seed=manifest['run_seed'],
                summary=source['summary'], cases=[], scenes={}, images=[])
    ids = {}

    def image_index(old_index):
        if old_index not in ids:
            ids[old_index] = len(data['images'])
            data['images'].append(old['images'][old_index])
        return ids[old_index]

    audits = []
    for raw in source['cases']:
        original = next(c for c in old['cases'] if c['id'] == raw['episode_id'])
        run = original['runs']['early']
        assert run['metrics'] == raw['oracle']['metrics']
        assert original['control_metrics'] == raw['control']['metrics']
        assert original['instruction'] == raw['instruction']
        assert original['reference'] == raw['reference']
        assert original['control'] == raw['control']['path']
        assert len(run['events']) == len(raw['interventions'])
        attempts = [a for a in (CAMPAIGN / 'oracle_records' / raw['episode_id']).glob('attempt_*') if (a / 'result.json').exists()]
        assert len(attempts) == 1
        actions = [json.loads(line) for line in (attempts[0] / 'actions.jsonl').read_text().splitlines()]
        assert len(actions) == run['action_count']
        assert math.dist(run['nodes'][-1]['p'], raw['oracle']['path'][-1]) < .00001
        for event, iv in zip(run['events'], raw['interventions']):
            before, after = run['nodes'][event['before']], run['nodes'][event['after']]
            assert event['step'] == iv['action_index'] == before['a'] == after['a']
            assert event['crossing'] == iv['target_id']
            assert event['reason'] == iv['response']['reason']
            assert math.dist(before['p'], iv['before_position']) < .00001
            assert math.dist(after['p'], iv['after_position']) < .00001
            assert before['segment'] + 1 == after['segment']
            assert event['after'] == event['before'] + 1
            assert event['memory'] and iv['memory_unchanged']
            assert event['after_ne'] == iv['handover_NE']
            # Independent evidence comes from the saved intervention record, not a UI label.
            saved = json.loads((Path(iv['request_directory']) / 'intervention.json').read_text())
            assert saved['memory_unchanged'] and saved['after_position'] == iv['after_position']
            proof = json.loads((Path(iv['request_directory']) / 'memory_proof.json').read_text())
            assert proof['equal'] and proof['before']['sha256'] == proof['after']['sha256']
            event['before_image'] = image_index(event['before_image'])
            event['after_image'] = image_index(event['after_image'])
        boundaries = {(e['before'], e['after']) for e in run['events']}
        for i, node in enumerate(run['nodes']):
            node['image'] = image_index(node['image'])
            if i and node['segment'] != run['nodes'][i - 1]['segment']:
                assert (i - 1, i) in boundaries
        c = {k: original[k] for k in ('id', 'scene', 'instruction', 'reference', 'crossings', 'control', 'control_metrics')}
        c.update(run=run, analysis=raw['analysis'], control_fail_reason=raw['control']['fail_reason'])
        data['cases'].append(c)
        data['scenes'][c['scene']] = old['scenes'][c['scene']]
        audits.append(dict(episode_id=c['id'], actions=len(actions), events=len(run['events']),
                           exact_correction_boundaries=True, raw_intervention_records_verified=True))
    data['summary']['first_inside_count'] = sum(c['run']['events'][0]['inside_goal'] for c in data['cases'])
    template_path = ROOT / 'core/oracle_early_replay.html'
    template = template_path.read_text()
    assert template.count('__PAYLOAD__') == 1
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace('__PAYLOAD__', payload))
    meta = dict(html=str(output), bytes=output.stat().st_size, sha256=sha(output),
                campaign=CAMPAIGN.name, cases=10, successful=10, control_successful=0,
                correction_events=18, policy_memory_verified=18, images=len(data['images']),
                first_correction_inside_goal_radius=data['summary']['first_inside_count'],
                source_report_sha256=sha(source_path), source_replay_sha256=sha(replay_path),
                experiment_manifest_sha256=sha(manifest_path), builder_sha256=sha(Path(__file__)),
                template_sha256=sha(template_path), self_contained=True,
                no_model_or_simulator_started=True, audits=audits)
    output.with_suffix('.build.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in meta.items() if k != 'audits'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=CAMPAIGN / 'oracle_early10_offline.html')
    args = ap.parse_args()
    build(args.output)
