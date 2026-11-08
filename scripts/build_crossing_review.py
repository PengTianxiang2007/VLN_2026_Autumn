"""Export a standalone review of a completed run; no inference or method changes."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from preview_crossing_checkpoint import digest, frozen_core, load_records, prefix_case, read_json

ROOT = Path(__file__).resolve().parents[1]


def build(output, tag, destination=None):
    destination = destination or output / 'reports' / (tag + '_review')
    if destination.exists():
        raise ValueError('Existing reports are immutable; specify a new --destination')
    run = output / 'runs' / tag
    manifest = read_json(run / 'manifest.json')
    protocol = read_json(output / 'protocol.json')
    assert digest(output / 'protocol.json') == manifest['protocol_sha256'], 'Protocol changed'
    assert digest(output / 'inputs.json') == manifest['source_sha256'], 'Input manifest changed'
    core = frozen_core(run, manifest)
    maps = read_json(output / 'evaluation/maps.json')
    assert core.canonical_hash(maps) == protocol['fixed_reference_sha256'], 'Map reference changed'
    inputs = read_json(output / 'inputs.json')
    private = read_json(output / 'evaluation/cases.json')
    scores = read_json(run / 'scores.json')
    diagnostics = read_json(run / 'diagnostics.json')
    assert scores['summary']['complete'], 'Only completed runs can be exported'
    cases = {}
    totals = {str(radius): dict(tp=0, fp=0, fn=0, duplicate_predictions=0,
                              confirmed_predictions=0, reference_encounters=0)
              for radius in protocol['evaluation']['sensitivity_radii_m']}
    for episode in manifest['episodes']:
        final = read_json(run / 'cases' / episode / 'result.json')
        assert final['complete'], episode
        records = load_records(run / 'cases' / episode / 'predictions.jsonl')
        source = private[episode]
        case = prefix_case(episode, inputs[episode], source, records, core,
                           manifest['inference'], maps[source['scene']]['crossings'])
        assert case['processed'] == case['expected'] == final['observations'], episode
        # Reconstruct the final tracker state independently; snapshots remain causal.
        tracker = core.CheckpointTracker()
        for row in records:
            tracker.update(row['frame'], row['prediction'])
        assert tracker.finish() == final['events'], f'{episode}: saved tracker state differs'
        metrics = {}
        for radius in protocol['evaluation']['sensitivity_radii_m']:
            key = str(radius)
            metric = core.evaluate_events(final['events'], source['steps'], source['encounters'], radius)
            assert metric == scores['cases'][episode]['metrics'][key], f'{episode}: score changed'
            metrics[key] = metric
            for name in totals[key]:
                totals[key][name] += metric[name]
        case.update(complete=True, metrics=metrics, final_events=final['events'],
                    encounters=source['encounters'], diagnostics=diagnostics['cases'][episode])
        positions = [s for s in case['steps'] if s['position'] is not None]
        visited = {e['crossing_id'] for e in source['encounters']}
        case['prior_annotations'] = []
        for crossing in maps[source['scene']]['crossings']:
            closest = min(positions, key=lambda s: math.dist(s['position'][:2], crossing['position']))
            case['prior_annotations'].append(dict(
                id=crossing['id'], position=crossing['position'], visited=crossing['id'] in visited,
                closest_frame=closest['frame'],
                closest_distance_m=math.dist(closest['position'][:2], crossing['position']),
                kind=crossing.get('kind'), note=crossing.get('note', '')))
        case['current_annotations'] = []
        for event in final['events']:
            frame = event['confirmation_frame']
            if frame is None:
                continue
            position = next(s['position'][:2] for s in positions if s['frame'] == frame)
            match = next(m for m in metrics['1.0']['predictions'] if m['prediction_id'] == event['id'])
            case['current_annotations'].append(dict(id=event['id'], position=position,
                confirmation_frame=frame, matched_crossing_id=match.get('crossing_id'),
                description=event['confirmation_observation']['description'],
                position_source='Recorded robot position at checkpoint confirmation; not an estimated crossing center.'))
        cases[episode] = case
    for radius, metric in totals.items():
        for key, value in metric.items():
            assert value == scores['summary']['metrics'][radius][key], f'Total differs: {radius}/{key}'
    summary = dict(scores['summary'], created_at=datetime.now(timezone.utc).isoformat(),
                   processed=sum(c['processed'] for c in cases.values()),
                   verified_causal_requests=sum(c['processed'] for c in cases.values()),
                   model=Path(manifest['model_path']).name,
                   thinking=manifest['inference']['thinking'], backend=manifest['inference_backend'],
                   inference_stride=manifest['inference'].get('inference_stride', 1),
                   mean_seconds=sum(s['elapsed_seconds'] for c in cases.values() for s in c['snapshots']) /
                                sum(c['processed'] for c in cases.values()))
    data = dict(tag=tag, summary=summary, cases=cases,
                maps={s: maps[s] for s in {c['scene'] for c in cases.values()}},
                diagnostic_counts=diagnostics['missed_diagnostic_counts'])
    destination.mkdir(parents=True)
    target = destination / 'crossing_dev8_review.html'
    template = (ROOT / 'core/crossing_checkpoint_review.html').read_text()
    encoded = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    temp = target.with_suffix('.tmp')
    temp.write_text(template.replace('__DATA__', encoded))
    temp.replace(target)
    audit = dict(tag=tag, created_at=summary['created_at'], cases=len(cases),
                 verified_causal_requests=summary['verified_causal_requests'],
                 frozen_source_verified=True, fixed_maps_verified=True,
                 final_tracker_states_verified=True, scores_recomputed_and_verified=True,
                 embedded_images=True, external_network_dependencies=False,
                 method_iteration_started=False, presentation='prior_C_vs_current_P',
                 default_map='All prior annotations and all confirmed current checkpoints; unvisited prior annotations identified separately.',
                 current_annotation_count=sum(len(c['current_annotations']) for c in cases.values()),
                 bytes=target.stat().st_size,
                 html_sha256=digest(target), metrics=summary['metrics'])
    (destination / 'verification.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(report=str(target), **audit), ensure_ascii=False))
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--destination', type=Path, help='New directory for the audited source report')
    args = parser.parse_args()
    build(args.output, args.tag, args.destination)
