"""CPU-only causal replay of stored poses; never simulates or applies a teleport."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.oracle_auto_branch import AutoBranchTrigger, PROTOCOL
from scripts.prepare_oracle_auto_route import read_episode_ids


def replay(trajectory, config):
    trigger = AutoBranchTrigger({'reference_path': trajectory['reference_path']},
                                config['threshold_m'], config['landing_offset_m'], config['branch'])
    events = {}
    reasons = Counter()
    threshold_frames = resolved_frames = 0
    records = []
    for frame in trajectory['frames']:
        decision = trigger.update(frame['position'], frame['frame'])
        if decision['threshold_reached']:
            threshold_frames += 1
            if decision['target'] is None:
                reasons[decision['branch_unresolved_reason']] += 1
            else:
                resolved_frames += 1
                events.setdefault(decision['event']['target_id'], dict(
                    first_available_frame=frame['frame'], event=decision['event'], target=decision['target']))
        records.append(dict(frame=frame['frame'], **decision))
    return dict(observations=len(records), threshold_frames=threshold_frames,
                resolved_threshold_frames=resolved_frames, unresolved_reasons=dict(reasons),
                candidate_branches=list(events.values()), observations_log=records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--episode-ids-file', type=Path, required=True)
    parser.add_argument('--config', type=Path,
                        default=ROOT/'experiments/oracle_recovery/auto_branch_v001/config.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserving existing audit: ' + str(args.output))
    ids = read_episode_ids(args.episode_ids_file)
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate replay task IDs')
    metadata = {r['episode_id']: r for r in map(json.loads,
        (args.dataset/'evaluation/episodes.jsonl').read_text().splitlines())}
    if not set(ids) <= set(metadata):
        raise ValueError('Unknown replay task IDs')
    config = json.loads(args.config.read_text())
    args.output.mkdir(parents=True)
    tasks = []
    for eid in ids:
        trajectory = json.loads((args.dataset/metadata[eid]['trajectory']).read_text())
        result = replay(trajectory, config)
        (args.output/(eid+'.json')).write_text(json.dumps(result, ensure_ascii=False)+'\n')
        tasks.append(dict(episode_id=eid, **{k: v for k, v in result.items() if k != 'observations_log'}))
    reasons = Counter()
    for task in tasks:
        reasons.update(task['unresolved_reasons'])
    summary = dict(protocol=PROTOCOL, episodes=len(tasks),
                   observations=sum(t['observations'] for t in tasks),
                   threshold_frames=sum(t['threshold_frames'] for t in tasks),
                   resolved_threshold_frames=sum(t['resolved_threshold_frames'] for t in tasks),
                   candidate_branches=sum(len(t['candidate_branches']) for t in tasks),
                   tasks_with_candidates=sum(bool(t['candidate_branches']) for t in tasks),
                   unresolved_reasons=dict(reasons), simulation_started=False,
                   annotations_used=False, corrections_applied=0,
                   interpretation='Existing poses replayed causally, no counterfactual navigation. Candidate counts '
                                  'are not localization accuracy, correction success or navigation gains.', tasks=tasks)
    (args.output/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'tasks'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
