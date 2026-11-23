"""Read-only worker observer; write progress and a validated final comparison.

Never starts/stops navigation, sends policy requests, changes inputs or retries cases.
"""
import argparse
import csv
import json
from pathlib import Path
import time


def read(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    path=Path(path);temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');temporary.replace(path)


def final_report(root, states):
    records={};summaries={}
    ids=read(root/'auto_branch/episode_ids.json')
    assert ids==read(root/'baseline/episode_ids.json')
    for arm,state in states.items():
        validation=Path(state['validation']);proof=read(validation)
        assert proof['passed'] and proof['episodes']==len(ids)
        rows=[json.loads(line) for line in (validation.parent/'episodes.jsonl').read_text().splitlines()]
        by_id={r['episode_id']:r for r in rows}
        assert len(rows)==len(by_id)==len(ids) and set(by_id)==set(ids)
        records[arm]=by_id
        summaries[arm]=dict(episodes=len(rows),successes=sum(int(r['SR']) for r in rows),metrics=proof['metrics'],validation=str(validation))
    rows=[];missing_oracle=[]
    for eid in ids:
        base,auto=records['baseline'][eid],records['auto_branch'][eid]
        assert base['scene']==auto['scene'] and base['episode_seed']==auto['episode_seed']
        assert base['run_seed']==auto['run_seed']
        oracle_path=root/'auto_branch/oracle_records/auto_branch'/eid/'result.json'
        interventions=None
        if oracle_path.exists():
            oracle=read(oracle_path)
            assert oracle['status']=='complete' and float(oracle['metrics']['success'])==float(auto['SR'])
            interventions=len(oracle['interventions'])
        else:
            # Native scoring may finish before the Oracle result hook (e.g.
            # warm-up falls). Keep its validated score; missing is not zero.
            missing_oracle.append(eid)
        row=dict(episode_id=eid,scene=auto['scene'],episode_seed=auto['episode_seed'],
                 interventions=interventions,
                 oracle_result_status='missing' if interventions is None else 'verified')
        for metric in ['SR','SPL','NE','steps','fail_reason']:
            row['baseline_'+metric]=base[metric];row['auto_branch_'+metric]=auto[metric]
        rows.append(row)
    with (root/'comparison.csv').open('x',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary=dict(phase='complete_services_retained',completed_at=time.time(),planned_total=2*len(ids),
                 completed_total=2*len(ids),arms=summaries,
                 paired_wins=sum(r['auto_branch_SR']>r['baseline_SR'] for r in rows),
                 paired_losses=sum(r['auto_branch_SR']<r['baseline_SR'] for r in rows),
                 interventions=None if missing_oracle else sum(r['interventions'] for r in rows),
                 recorded_interventions=sum(r['interventions'] for r in rows if r['interventions'] is not None),
                 oracle_results_verified=len(ids)-len(missing_oracle),
                 oracle_results_missing=missing_oracle,
                 intervention_counts_complete=not missing_oracle,
                 interpretation='Same tasks and seeds, independent runs; no shared-prefix causal claim.',
                 services_retained=True)
    write(root/'comparison_summary.json',summary)
    return summary


def update(root):
    states={arm:read(root/arm/'status.json') for arm in ['auto_branch','baseline']}
    finished=all(s['phase']=='complete_services_retained' for s in states.values())
    failed=any(s['phase'] in ['failed','stopped','cancelled'] for s in states.values())
    report=dict(phase='complete_services_retained' if finished else 'incomplete_worker_stopped' if failed else 'running',
                updated_at=time.time(),completed_total=sum(s.get('completed',0) for s in states.values()),
                planned_total=800,model_pid=3194667,model_gpu=3,simulation_gpu=2,
                arms={arm:{k:s.get(k) for k in ['phase','completed','expected','simulator_pid','error','validation']} for arm,s in states.items()})
    if finished:
        report=read(root/'comparison_summary.json') if (root/'comparison_summary.json').exists() else final_report(root,states)
    write(root/'progress.json',report)
    return report,finished or failed


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--campaign',type=Path,required=True)
    p.add_argument('--once',action='store_true');a=p.parse_args()
    while True:
        report,done=update(a.campaign)
        print(json.dumps({k:v for k,v in report.items() if k!='arms'},ensure_ascii=False),flush=True)
        if done or a.once:return
        time.sleep(30)


if __name__=='__main__':main()
