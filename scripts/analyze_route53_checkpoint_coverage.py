"""Compare the frozen Qwen route53 rollback checkpoints to the offline event labels."""
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'outputs/offline_route_dataset/v001/run_20261118_01/dataset'
QWEN = ROOT / 'outputs/deviation_progress/v003/run_20261118_01_qwen27b'
CANDIDATES = ROOT / 'outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/candidates.json'
OUTPUT = QWEN / 'analysis/branch_coverage_01'


def read(path):
    return json.loads(path.read_bytes())


def summarize(rows):
    cases = defaultdict(list)
    for row in rows:
        cases[row['case']].append(row['retained_hit'])
    groups = [sum(hits) for hits in cases.values()]
    counts = {key: sum(r[key] for r in rows) for key in (
        'raw_hit', 'retained_hit', 'with_terminal_hit', 'lost_to_dedup',
        'exact_anchor', 'in_window_on_or_before_anchor', 'in_window_emitted_by_confirmation')}
    return dict(events=len(rows), cases=len(cases), cases_all=sum(all(h) for h in cases.values()),
                cases_some=sum(n > 0 for n in groups), cases_none=groups.count(0), **counts,
                spatial={key: {str(radius): sum(r[key] is not None and r[key] <= radius for r in rows)
                               for radius in (0.25, 0.5, 1.0)}
                         for key in ('nearest_any_xy_m', 'nearest_prior_xy_m', 'nearest_in_window_xy_m')})


def main():
    manifest = DATA / 'manifest.json'
    selection = DATA / 'subsets/all_selected.txt'
    kept_path = QWEN / 'retained_nodes_and_terminals.json'
    sources = [Path(__file__).resolve(), manifest, selection, kept_path, CANDIDATES]
    kept_by_ep = read(kept_path)
    raw_by_ep = defaultdict(list)
    for node in read(CANDIDATES):
        raw_by_ep[node['episode_id']].append(node)
    selected = selection.read_text().splitlines()
    assert set(selected) == set(kept_by_ep) == set(raw_by_ep) and len(selected) == len(set(selected)) == 53
    rows = []
    counts = defaultdict(int)
    episode_ids = set()
    for result_path in sorted((QWEN / 'dedup/cases').glob('C*/result.json')):
        result = read(result_path)
        eid = result['episode_id']
        case = result_path.parent.name
        assert eid not in episode_ids and case == f"C{result['case_number']:02d}"
        episode_ids.add(eid)
        label_path = DATA / 'evaluation/episodes' / (eid + '.json')
        sources.extend([result_path, label_path])
        label = read(label_path)
        path = label['actual_path']
        annotation = label['annotation']
        assert annotation['episode_id'] == eid and annotation['selected']
        raw = raw_by_ep[eid]
        raw_lookup = {n['id']: n['index'] for n in raw}
        assert [(n['id'], n['index']) for n in raw] == [(n['id'], n['index']) for n in result['nodes']]
        effective = kept_by_ep[eid]
        retained = [n for n in effective if not n['terminal_node']]
        terminals = [n for n in effective if n['terminal_node']]
        assert len(terminals) == 1 and terminals[0]['index'] == len(path) - 1
        assert [n['source_id'] for n in retained] == result['final_active_ids']
        assert all(n['index'] == raw_lookup[n['source_id']] for n in retained)
        assert all(0 <= n['index'] < len(path)-1 for n in raw)
        counts['raw'] += len(raw)
        counts['retained'] += len(retained)
        counts['terminal'] += len(terminals)
        for event in annotation['events']:
            lower, upper = event['decision_interval_steps']
            anchor = event['decision_step_estimate']
            assert 0 <= lower <= anchor < upper == event['confirmed_wrong_step'] < len(path)
            assert math.dist(event['decision_robot_pose']['position_world_m'],path[anchor]) < 1e-5
            raw_hits = [n for n in raw if lower <= n['index'] <= upper]
            kept_hits = [n for n in retained if lower <= n['index'] <= upper]
            nearest = min(retained, key=lambda n: (abs(n['index']-anchor), n['index']))
            distances = [(math.dist(path[n['index']][:2], path[anchor][:2]), n['index']) for n in retained]
            any_m, any_step = min(distances)
            prior_m, prior_step = min((d for d in distances if d[1] <= anchor), default=(None, None))
            window_m = min((distance for distance, step in distances if lower <= step <= upper), default=None)
            lost = bool(raw_hits) and not kept_hits
            replacements = []
            if lost:
                for node in raw_hits:
                    removal, = [d for d in result['decisions'] if node['id'] in d['active_ids_before']
                                and node['id'] not in d['active_ids_after']]
                    assert removal['relation'] == 'same' and removal['action'] == 'replace_previous'
                    replacements.append(f"{node['index']}->{removal['current_frame']}")
            rows.append(dict(case=case, episode_id=eid, event_id=event['event_id'], subset=annotation['subset'],
                             subtype=event['subtype'], confidence=event['confidence'], lower=lower, anchor=anchor,
                             upper=upper, raw_hit=bool(raw_hits), retained_hit=bool(kept_hits),
                             with_terminal_hit=bool(kept_hits) or lower <= terminals[0]['index'] <= upper,
                             lost_to_dedup=lost, replacement_steps=" ".join(replacements),
                             raw_hit_steps=' '.join(str(n['index']) for n in raw_hits),
                             retained_hit_steps=' '.join(str(n['index']) for n in kept_hits),
                             retained_hit_ids=' '.join(n['id'] for n in kept_hits),
                             exact_anchor=any(n['index']==anchor for n in kept_hits),
                             in_window_on_or_before_anchor=any(n['index'] <= anchor for n in kept_hits),
                             in_window_emitted_by_confirmation=any(n['emittedAt'] <= upper for n in kept_hits),
                             nearest_step=nearest['index'], nearest_step_delta=nearest['index']-anchor,
                             nearest_to_window_steps=min(max(lower-n['index'], n['index']-upper,0) for n in retained),
                             nearest_any_xy_m=any_m, nearest_any_xy_step=any_step, nearest_in_window_xy_m=window_m,
                             nearest_prior_xy_m=prior_m, nearest_prior_xy_step=prior_step))
    assert episode_ids == set(selected)
    assert len(rows) == read(manifest)['summary']['selected_events'] == len({r['event_id'] for r in rows})
    assert dict(counts) == dict(raw=494,retained=376,terminal=53)
    subsets = {s: summarize([r for r in rows if r['subset']==s]) for s in sorted({r['subset'] for r in rows})}
    subtypes = {s: summarize([r for r in rows if r['subtype']==s]) for s in sorted({r['subtype'] for r in rows})}
    summary = dict(node_counts=counts, overall=summarize(rows), by_subset=subsets, by_subtype=subtypes,
                   input_and_script_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                            for p in sources})
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT/'events.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    (OUTPUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')


if __name__ == '__main__':
    main()
