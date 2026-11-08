"""Cross-check replay interventions against actual review actions and native model proposals."""
import argparse
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from core.fall_replay import xy_distance


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def validate(campaign):
    manifest = json.loads((campaign / 'manifest.json').read_text())
    config = manifest['replay']
    cases = {c['episode_id']: c for c in manifest['cases']}
    index = campaign / 'visualization_replay/index.jsonl'
    reviews = read_lines(index) if index.exists() else []
    passed = []
    for unit in config['units']:
        root = Path(config['runtime_env']['VLN_OUTPUT_ROOT']) / 'vlnverse/streamvln/results' / unit['run_id']
        if not (root / 'validation.json').exists():
            continue
        scored = read_lines(root / 'episodes.jsonl')
        traces = {}
        for trace in sorted((root / 'storage/chunks').glob('*/agent_trace.jsonl')):
            for row in read_lines(trace):
                # A failed infrastructure attempt can repeat a partial prefix.
                # Retain the newest attempt's contiguous sequence per episode.
                eid = row['episode_id']
                if row['step'] == 0:
                    traces[eid] = []
                traces[eid].append(row)
        for score in scored:
            eid = score['episode_id']
            case = cases[eid]
            attempts = sorted((campaign / 'replay_records' / eid).glob('*/result.json'))
            result = json.loads(attempts[-1].read_text())
            actions = read_lines(attempts[-1].parent / 'actions.jsonl') if result['actions_executed'] else []
            matches = [r for r in reviews if r['episode_id'] == eid and r['run_id'] == unit['run_id']]
            assert matches and matches[-1]['status'] == 'complete', eid
            observed = [r for r in read_lines(campaign / 'visualization_replay' / matches[-1]['steps']) if not r['terminal']]
            predicted = traces.get(eid, [])
            assert len(actions) == len(observed) == len(predicted) == result['actions_executed'], eid
            target = case['rollback_action_index']
            mismatches = 0
            for i, (record, obs, proposal) in enumerate(zip(actions, observed, predicted)):
                assert record['action_index'] == obs['action_index'] == proposal['step'] == i
                assert record['executed'] == obs['action']
                proposed = {'stop': []} if proposal['action'] == 0 else {'move_by_discrete': [proposal['action']]}
                assert record['proposed'] == proposed
                if i < target:
                    assert record['executed'] == {'move_by_discrete': [case['original_actions'][i]]}
                    assert record['overridden']
                    mismatches += int(proposed != record['executed'])
                else:
                    assert record['executed'] == proposed and not record['overridden']
            assert mismatches == result['proposed_action_mismatches_in_prefix']
            if result['checkpoint_reached']:
                checkpoint = result['checkpoint']
                actual_error = xy_distance(observed[target]['position'], case['target_position'])
                assert abs(actual_error - checkpoint['xy_error_m']) < 1e-6
                assert result['actions_after_checkpoint'] == len(actions) - target
            assert result['fail_reason'] == score['fail_reason'] == matches[-1]['fail_reason']
            assert result['episode_seed'] == score['episode_seed']
            passed.append(dict(episode_id=eid, actions=len(actions), checkpoint_reached=result['checkpoint_reached'],
                               outcome=result['outcome'], prefix_proposal_mismatches=mismatches))
    report = dict(passed=True, episodes_checked=len(passed), expected_eligible=40, inapplicable=1, cases=passed,
                  checks=['original prefix equals physically executed review actions',
                          'native model proposals equal diagnostic proposals',
                          'after release, executed actions equal native model proposals',
                          'checkpoint distance independently recomputed from review position',
                          'fall reason and per-episode seed agree with official score'])
    (campaign / 'replay_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    result = validate(parser.parse_args().campaign.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
