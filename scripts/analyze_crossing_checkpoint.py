"""Evaluation-only development diagnostics; never provides labels to inference."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def analyze(output, tag):
    run = output / 'runs' / tag
    manifest = read(run / 'manifest.json')
    scores = read(run / 'scores.json')
    cases = read(output / 'evaluation/cases.json')
    maps = read(output / 'evaluation/maps.json')
    diagnoses = {}
    by_kind = defaultdict(Counter)
    reasons = Counter()
    for episode, result in scores['cases'].items():
        case = cases[episode]
        references = {r['id']: r for r in case['encounters']}
        crossings = {r['id']: r for r in maps[case['scene']]['crossings']}
        predictions = [json.loads(line) for line in
                       (run / 'cases' / episode / 'predictions.jsonl').read_text().splitlines()]
        metric = result['metrics']['1.0']
        missed = []
        for encounter in references.values():
            kind = crossings[encounter['crossing_id']].get('kind', 'unknown')
            by_kind[kind]['references'] += 1
            by_kind[kind]['missed' if encounter['id'] in metric['missed_encounters'] else 'matched'] += 1
            if encounter['id'] not in metric['missed_encounters']:
                continue
            nearby = [r for r in predictions
                      if encounter['approach_frame'] <= r['frame'] <= encounter['exit_frame']]
            eligible = [r for r in nearby if r['prediction']['status'] == 'crossing'
                        and r['prediction']['location'] == 'here'
                        and r['prediction']['confidence'] != 'low']
            visual = [r for r in nearby if r['prediction']['status'] == 'crossing']
            if len(eligible) >= 2:
                reason = 'here_votes_exist_check_tracking_or_matching'
            elif len(eligible) == 1:
                reason = 'only_one_here_vote'
            elif visual:
                reason = 'crossing_seen_but_no_eligible_here_vote'
            else:
                reason = 'no_crossing_prediction_in_reference_window'
            reasons[reason] += 1
            missed.append(dict(encounter_id=encounter['id'], kind=kind,
                               diagnostic=reason, window=[encounter['approach_frame'], encounter['exit_frame']],
                               closest_frame=encounter['closest_frame'],
                               here_vote_frames=[r['frame'] for r in eligible],
                               crossing_vote_frames=[r['frame'] for r in visual]))
        unmatched = []
        positions = {s['frame']: s['position'] for s in case['steps']}
        for prediction in metric['predictions']:
            if prediction['label'] == 'matched':
                continue
            p = positions[prediction['frame']]
            nearest = min(crossings.values(), key=lambda c: math.dist(p[:2], c['position'])) if p else None
            unmatched.append(dict(**prediction,
                nearest_crossing=nearest['id'] if nearest else None,
                nearest_distance_m=math.dist(p[:2], nearest['position']) if nearest else None,
                diagnostic='Needs RGB review: valid unlabelled route, spatial offset, duplicate, or visual false alarm.'))
        counts = Counter(r['prediction']['status'] + '/' + r['prediction']['location'] for r in predictions)
        diagnoses[episode] = dict(missed=missed, unmatched=unmatched, observation_counts=dict(counts))
    for counts in by_kind.values():
        counts['recall'] = counts['matched'] / counts['references'] if counts['references'] else None
    data = dict(tag=tag, split=manifest['split'], summary=scores['summary'],
                reference_recall_by_kind=dict(by_kind), missed_diagnostic_counts=dict(reasons),
                cases=diagnoses,
                caveat='Diagnostic categories are log-derived leads, not manually verified causes. '
                       'Do not use validation diagnostics for further tuning on the same held-out set.')
    target = run / 'diagnostics.json'
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in data.items() if k != 'cases'}, ensure_ascii=False))
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    analyze(args.output, args.tag)
