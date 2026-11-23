"""Audit recorded StreamVLN task IDs and draft a scene-balanced new cohort; CPU only."""
import argparse
import csv
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.paths import resource_root


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def record_ids(value, official):
    found = set()
    if isinstance(value, dict):
        eid = value.get('episode_id')
        if isinstance(eid, str) and eid in official:
            found.add(eid)
        for item in value.values():
            if isinstance(item, (dict, list)):
                found.update(record_ids(item, official))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                found.update(record_ids(item, official))
    return found


def audit_history(official_ids):
    roots = [*sorted((ROOT/'outputs/reproduction').glob('streamvln*')),
             ROOT/'outputs/vlnverse/streamvln/results', ROOT/'outputs/oracle_crossing',
             ROOT/'outputs/serial_recovery', ROOT/'outputs/agent_recovery']
    names = {'episodes.csv', 'episodes.jsonl', 'agent_trace.jsonl', 'result.json', 'case.json', 'failure.json'}
    skip = {'frames', 'assets', 'exports', 'source', 'sources', 'backbone', 'benchmarks',
            'checkpoints', 'policy_checkpoints', 'models', '.venv', '.runtime', 'node_modules',
            'samples', 'videos', 'images', 'media', 'implementation_source'}
    seen = set(); evidence = []; parse_issues = []
    for root in roots:
        if not root.exists():
            continue
        for folder, directories, files in os.walk(root, followlinks=False):
            directories[:] = [d for d in directories if d not in skip and not d.startswith(('code', 'snapshot', 'prepared'))]
            for name in sorted(set(files) & names):
                path = Path(folder)/name
                ids = set()
                if name.endswith('.csv'):
                    with path.open() as stream:
                        ids = {r['episode_id'] for r in csv.DictReader(stream) if r.get('episode_id') in official_ids}
                elif name.endswith('.jsonl'):
                    with path.open() as stream:
                        for line_number, line in enumerate(stream, 1):
                            if not line.strip():
                                continue
                            try:
                                ids.update(record_ids(json.loads(line), official_ids))
                            except ValueError:
                                parse_issues.append(dict(path=str(path.relative_to(ROOT)), line=line_number))
                    # Initial one-task validation used an older trace schema.
                    if name == 'agent_trace.jsonl' and not ids and path.stat().st_size:
                        for parent in path.parents:
                            metadata = parent/'run.json'
                            if metadata.is_file():
                                requested = json.loads(metadata.read_text()).get('episode_ids', [])
                                if len(requested) == 1 and requested[0] in official_ids:
                                    ids.add(requested[0])
                                break
                            if parent == root:
                                break
                else:
                    try:
                        ids = record_ids(json.loads(path.read_text()), official_ids)
                    except ValueError:
                        parse_issues.append(dict(path=str(path.relative_to(ROOT))))
                if ids:
                    seen.update(ids)
                    evidence.append(dict(path=str(path.relative_to(ROOT)), sha256=sha(path), episode_ids=sorted(ids)))
    return seen, dict(roots=[str(p.relative_to(ROOT)) for p in roots], files=evidence,
                      parse_issues=parse_issues, interpretation='Recorded scores, actual task attempts and action traces; '
                      'planned episode-ID lists alone are not treated as executed. Other backbones are excluded.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=400)
    parser.add_argument('--selection-seed', type=int, default=20261116)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.count <= 0 or args.output.exists():
        raise ValueError('Use a positive task count and a new output directory')
    official = resource_root()/'assets/VLNVerse/data/raw_data/final_splits/fine_val_unseen.json.gz'
    with gzip.open(official, 'rt') as stream:
        episodes = json.load(stream)['episodes']
    lookup = {e['episode_id']: e for e in episodes}
    seen, audit = audit_history(set(lookup))
    candidates = defaultdict(list)
    for episode in episodes:
        if episode['episode_id'] not in seen:
            candidates[episode['scan']].append(episode['episode_id'])
    if sum(map(len, candidates.values())) < args.count:
        raise ValueError('Not enough tasks under the recorded StreamVLN-exclusion scope')
    rank = lambda kind, value: hashlib.sha256(f'{args.selection_seed}:{kind}:{value}'.encode()).hexdigest()
    order = sorted(candidates, key=lambda scene: rank('scene', scene))
    allocation = Counter()
    remaining = args.count
    while remaining:
        for scene in order:
            if allocation[scene] < len(candidates[scene]):
                allocation[scene] += 1; remaining -= 1
                if not remaining:
                    break
    selected = {eid for scene, ids in candidates.items()
                for eid in sorted(ids, key=lambda eid: rank('episode', eid))[:allocation[scene]]}
    ordered = [e['episode_id'] for e in episodes if e['episode_id'] in selected]
    assert len(ordered) == args.count and not (selected & seen)
    rows = [dict(scene=scene, candidates=len(ids), selected=allocation[scene]) for scene, ids in sorted(candidates.items())]
    assert sum(r['selected'] for r in rows) == args.count
    args.output.mkdir(parents=True)
    (args.output/'history_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n')
    (args.output/'excluded_episode_ids.json').write_text(json.dumps(sorted(seen), indent=2)+'\n')
    (args.output/'draft_episode_ids.json').write_text(json.dumps(ordered, indent=2)+'\n')
    with (args.output/'scene_counts.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=['scene', 'candidates', 'selected']); writer.writeheader(); writer.writerows(rows)
    with (args.output/'draft_tasks.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=['episode_id', 'scene']); writer.writeheader()
        writer.writerows(dict(episode_id=eid, scene=lookup[eid]['scan']) for eid in ordered)
    summary = dict(status='draft_no_execution', official_tasks=len(episodes),
                   recorded_streamvln_tasks=len(seen), excluded_scenes=len({lookup[e]['scan'] for e in seen}),
                   candidate_tasks=sum(map(len, candidates.values())), candidate_scenes=len(candidates),
                   selected_tasks=len(selected), selected_scenes=len({lookup[e]['scan'] for e in selected}),
                   selection_seed=args.selection_seed, allocation_histogram=dict(Counter(allocation.values())),
                   official_split_sha256=sha(official), draft_ids_sha256=sha(args.output/'draft_episode_ids.json'),
                   audit_files=len(audit['files']), parse_issues=len(audit['parse_issues']),
                   exclusion_scope='All recorded StreamVLN runs/attempts in audited project roots, any seed; not other models.',
                   selection='Round-robin scene balance, SHA256 seed ranking within scenes; no result-based selection.',
                   simulation_started=False, scene_counts=rows)
    (args.output/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
