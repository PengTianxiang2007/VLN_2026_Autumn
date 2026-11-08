"""Export per-case reset/replay comparison without counting unfinished trials as nonfalls."""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from core.fall_replay import xy_distance


def summarize(campaign):
    manifest = json.loads((campaign / 'manifest.json').read_text())
    completed = {}
    for arm in ('reset', 'replay'):
        completed[arm] = {}
        config = manifest[arm]
        for unit in config.get('units', []):
            root = Path(config['runtime_env']['VLN_OUTPUT_ROOT']) / 'vlnverse/streamvln/results' / unit['run_id']
            if not (root / 'result.json').exists() or not (root / 'validation.json').exists():
                continue
            assert json.loads((root / 'validation.json').read_text())['passed']
            for line in (root / 'episodes.jsonl').read_text().splitlines():
                row = json.loads(line)
                assert row['episode_id'] not in completed[arm]
                completed[arm][row['episode_id']] = row
    rows = []
    for case in manifest['cases']:
        eid = case['episode_id']
        original = [json.loads(l) for l in Path(case['source_steps']).read_text().splitlines()]
        row = dict(episode_id=eid, scene=case['scene'], episode_seed=case['original']['episode_seed'],
                   original_action_count=case['original_action_count'],
                   rollback_action_index=case['rollback_action_index'])
        for arm in ('reset', 'replay'):
            score = completed[arm].get(eid)
            row[f'{arm}_status'] = 'complete' if score else 'not_applicable' if arm == 'replay' and not case['rollback_eligible'] else 'pending'
            row[f'{arm}_fall'] = score['fail_reason'] == 'fall' if score else None
            row[f'{arm}_termination'] = score['fail_reason'] if score else None
            row[f'{arm}_SR'] = score['SR'] if score else None
            row[f'{arm}_NE'] = score['NE'] if score else None
            row[f'{arm}_terminal_distance_from_original_fall_m'] = xy_distance(score['pred_path'][-1], original[-1]['position']) if score else None
        replay = completed['replay'].get(eid)
        detail = None
        if replay:
            results = sorted((campaign / 'replay_records' / eid).glob('*/result.json'))
            detail = json.loads(results[-1].read_text())
            assert detail['fail_reason'] == replay['fail_reason']
        row['replay_checkpoint_reached'] = detail['checkpoint_reached'] if detail else None
        row['replay_outcome'] = detail['outcome'] if detail else None
        row['replay_checkpoint_xy_error_m'] = detail['checkpoint']['xy_error_m'] if detail and detail['checkpoint'] else None
        row['replay_checkpoint_within_0_5m'] = detail['checkpoint']['within_0_5m'] if detail and detail['checkpoint'] else None
        row['replay_fall_within_10_actions_after_checkpoint'] = detail['fall_within_10_actions_after_checkpoint'] if detail else None
        row['replay_actions_after_checkpoint'] = detail['actions_after_checkpoint'] if detail else None
        row['replay_prefix_proposal_mismatches'] = detail['proposed_action_mismatches_in_prefix'] if detail else None
        rows.append(row)
    result = dict(updated_at=datetime.now(timezone.utc).isoformat(), cohort=41,
                  reset_expected=41, replay_expected=40, replay_inapplicable=1,
                  complete=len(completed['reset']) == 41 and len(completed['replay']) == 40,
                  protocol='One retry per condition, seed 2; replay uses new observations and original action prefix, not historical physics-state restoration.')
    correction_path = campaign / 'protocol_correction.json'
    if correction_path.exists():
        correction = json.loads(correction_path.read_text())
        result.update(requested_direct_rollback_test_completed=False,
                      requested_experiment_complete=False,
                      replay_interpretation='Historical-action prefix replay only; does not answer the requested direct-rollback experiment.',
                      protocol_correction=str(correction_path),
                      correction_recorded_at=correction['recorded_at'])
    for arm in ('reset', 'replay'):
        values = list(completed[arm].values())
        falls = sum(v['fail_reason'] == 'fall' for v in values)
        result[arm] = dict(validated_completed=len(values), falls=falls,
                           fall_percent_of_completed=100 * falls / len(values) if values else None,
                           successes=sum(v['SR'] > 0 for v in values))
    reached = [r for r in rows if r['replay_checkpoint_reached']]
    close = [r for r in reached if r['replay_checkpoint_within_0_5m']]
    for name, values in [('replay_reached_checkpoint', reached), ('replay_checkpoint_within_0_5m', close)]:
        result[name] = dict(episodes=len(values), falls=sum(r['replay_fall'] for r in values),
                            falls_within_next_10_actions=sum(r['replay_fall_within_10_actions_after_checkpoint'] for r in values),
                            no_proposal_mismatch_in_prefix=sum(r['replay_prefix_proposal_mismatches'] == 0 for r in values))
    result['replay_falls_before_checkpoint'] = sum(r['replay_outcome'] == 'fall_before_checkpoint' for r in rows)
    with (campaign / 'comparison.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (campaign / 'comparison.json').write_text(json.dumps(dict(summary=result, cases=rows), ensure_ascii=False, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    print(json.dumps(summarize(parser.parse_args().campaign.resolve()), indent=2))
