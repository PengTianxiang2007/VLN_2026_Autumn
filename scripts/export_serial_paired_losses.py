"""Freeze the latest seed-matched original successes that became failures and export their replay."""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean

from export_online_recovery_answers import export
from export_serial_paired_media import build
from export_serial_paired_snapshot import load, make_site


def freeze(output, translations):
    campaign = output.parent.parent
    config = load(campaign / 'config.json')
    with (translations.parent.parent / 'baseline203.csv').open() as f:
        baseline = {row['episode_id']: row for row in csv.DictReader(f)}
    cutoff = datetime.now(timezone.utc)
    attempts = []
    scored = {}
    for result in sorted(campaign.glob('episodes/*/attempt_*/result.json')):
        if result.stat().st_mtime > cutoff.timestamp():
            continue
        row = load(result)
        eid, metrics = row['episode_id'], row['metrics']
        original = baseline[eid]
        if (eid in scored or result.parent.parent.name != eid or
                metrics['reproduction_run_seed'] != config['seed'] or
                metrics['reproduction_episode_seed'] != int(original['episode_seed'])):
            raise ValueError(f'Conflicting paired score for {eid}')
        current = int(metrics['success']), metrics['spl']
        previous = int(float(original['SR'])), float(original['SPL'])
        scored[eid] = {'current': current, 'original': previous}
        if previous[0] == 1 and current[0] == 0:
            attempts.append(str(result.parent.relative_to(campaign)))
    if not attempts:
        raise ValueError('No original success / current failure pairs at this cutoff')
    skips = sorted(p.stem for p in (campaign / 'failures').glob('*.json')
                   if p.stat().st_mtime <= cutoff.timestamp())
    if scored.keys() & set(skips):
        raise ValueError('Episode has both a formal score and a technical skip')
    population = {v: dict(success=sum(r[v][0] for r in scored.values()),
                          spl=mean(r[v][1] for r in scored.values())) for v in ('current', 'original')}
    snapshot = dict(as_of=cutoff.isoformat(), campaign_size=len(config['episode_ids']), attempts=attempts,
                    skip_ids=[], selection='original_success_current_failure', scored=len(scored),
                    scored_ids=sorted(scored), campaign_skip_ids=skips, population=population)
    output.mkdir(parents=True, exist_ok=False)
    path = output / 'snapshot.json'
    path.write_text(json.dumps(snapshot, indent=2) + '\n')
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='New directory under the campaign exports directory')
    parser.add_argument('translations', type=Path, help='Campaign export record containing both translation files')
    args = parser.parse_args()
    out, record = args.output.resolve(), args.translations.resolve()
    snapshot = freeze(out, record)
    build(snapshot)
    make_site(snapshot, record)
    export(out, record, record)
