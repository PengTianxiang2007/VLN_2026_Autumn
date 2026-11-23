"""Freeze completed RxR deviation reviews and all final nodes; no model calls."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import shutil
import export_rxr_offline_snapshot as base

OLD = base.OUT
NAME = 'deviation_snapshot_20261123_02'
base.OUT = base.RUN/'exports'/NAME
base.RECORD = base.ROOT/'experiments'/base.OUT.relative_to(base.ROOT/'outputs')


def prepare():
    base.OUT.mkdir(parents=True, exist_ok=False)
    data = base.read(OLD/'snapshot_public.json')
    data['created_at'] = datetime.now(timezone.utc).isoformat()
    data['archive'] = 'rxr30_deviation_snapshot_offline.zip'
    summaries = base.read(base.RUN/'deviation/v006_results.json')
    by_id = {r['episode_id']: r for r in summaries}
    totals, outcomes, hashes = Counter(), Counter(), {}
    data['extra_assets'] = []
    data['dedup_detail_ids'] = data['completed_ids'][:]
    def read_source(path):
        hashes[str(path.relative_to(base.ROOT))] = base.sha(path)
        return base.read(path)
    (base.OUT/'results').mkdir()
    for i, c in enumerate(data['cases'], 1):
        result = read_source(base.RUN/f'dedup/cases/C{i:02d}/result.json')
        nodes = read_source(base.RUN/'effective_nodes'/(c['id']+'.json'))
        assert [n['source_id'] for n in nodes if not n['terminal_node']] == result['final_active_ids']
        previous_details = c.get('dedup') or {}
        c['dedup'] = dict(case_number=i, nodes=nodes, summary=result['summary'],
                          decisions=previous_details.get('decisions',[]),
                          started_at=result['started_at'], completed_at=result['completed_at'])
        raw_file = f"results/{c['id']}_dedup.json"
        base.save(base.OUT/raw_file, result)
        c['dedup']['raw_file'] = raw_file
        data['extra_assets'].append(raw_file)
        totals.update(result['summary'])
        c['deviation'] = None
        if c['id'] not in by_id:
            continue
        summary = by_id[c['id']]
        result = read_source(base.RUN/f'deviation/run/cases/C{i:02d}/result.json')
        assert str(result['episode_id']) == c['id']
        intervals = []
        for row in result['reviews']:
            row['request'] = read_source(base.RUN/'deviation'/row['request_file'])
            row['response'] = read_source(base.RUN/'deviation'/row['response_file'])
            row['raw_content'] = row['response'].get('response',{}).get('choices',[{'message':{}}])[0]['message'].get('content','')
            row['display_answer'] = row.get('answer') or row['response'].get('parsed_original')
            verdict = row['answer']['verdict'] if row['status']=='ok' else 'format_error'
            outcomes[verdict] += 1
            if verdict == 'deviated':
                a = next(n for n in nodes if n['id']==row['previous_id'])
                b = next(n for n in nodes if n['id']==row['node_id'])
                assert a['index']==row['from_frame'] and b['index']==row['to_frame']
                intervals.append(dict(previous_id=a['id'],current_id=b['id'],from_frame=a['index'],to_frame=b['index']))
        assert len(result['reviews']) == summary['calls']
        assert (intervals[0] if intervals else None) == summary['first_deviation']
        c['deviation'] = dict(summary=summary, result=result, intervals=intervals)
    data['summary'] = dict(totals)
    data['completed_ids'] = [c['id'] for c in data['cases']]
    data['deviation_complete'] = len(summaries)
    data['deviation_summary'] = dict(outcomes=outcomes, calls=sum(outcomes.values()),
        alarm_cases=sum(bool(c['deviation'] and c['deviation']['intervals']) for c in data['cases']))
    data['deviation_completed_ids'] = list(by_id)
    for language in ['zh','en']:
        p=base.ROOT/f'experiments/deviation_progress/v006/prompt_{language}.txt'
        data['prompts']['deviation_'+language] = p.read_text()
        hashes[str(p.relative_to(base.ROOT))] = base.sha(p)
    base.save(base.OUT/'snapshot.json',data)
    base.save(base.OUT/'source_hashes.json',hashes)
    base.save(base.RECORD/'summary.json',dict(created_at=data['created_at'],dedup=data['summary'],
        deviation_complete=len(summaries),deviation=data['deviation_summary'],cases=summaries))
    print(base.encoded(dict(snapshot=data['created_at'],dedup=totals,deviation_complete=len(summaries),deviation=data['deviation_summary'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['prepare','build'])
    args=parser.parse_args()
    if args.phase=='prepare':
        prepare()
    else:
        base.build()
        source=base.OUT/'source'; source.mkdir(exist_ok=True)
        for p in [Path(__file__),Path(base.__file__),*[base.ROOT/'core'/n for n in ['rxr_offline_snapshot.js','rxr_offline_snapshot.css','rxr_offline_snapshot_panel.html']]]:
            shutil.copy2(p,source/p.name)
