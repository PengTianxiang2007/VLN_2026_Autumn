"""Retry failed observations from the ten-case v004 batch and merge results."""
import argparse
import concurrent.futures
import json
import multiprocessing
import os
import shutil
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from core.agent_route_choice import now,read,write
from run_jev_noul_five_concurrent import run_task


def main():
    p=argparse.ArgumentParser();p.add_argument('--source-run',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--concurrency',type=int,default=3);p.add_argument('--attempts',type=int,default=5);a=p.parse_args()
    source=a.source_run.resolve();out=a.output.resolve()
    if out.exists():raise ValueError('Use a new output directory')
    if not os.environ.get('JEV_API_KEY'):raise RuntimeError('Set JEV_API_KEY')
    rows=read(source/'rows_v004.json');tasks={ (r['episode_id'],r['frame']):r for r in read(source/'tasks.json') }
    successful={(r['episode_id'],r['frame']):r for r in rows if r.get('phase')=='complete'}
    failed=[(x['episode_id'],x['frame']) for x in rows if x.get('phase')!='complete']
    out.mkdir(parents=True)
    for name in ('selection.json','qwen_predictions.json','rows_v002.json','prompt_en.json','prompt_zh.json','prompt_v004_en.txt','prompt_v004_zh.txt','manifest.json'):
        shutil.copy2(source/name,out/name)
    write(out/'tasks.json',list(tasks.values()))
    for relative in ('scripts/retry_jev_noul_v004_ten.py','scripts/run_jev_noul_v004_ten.py','scripts/run_jev_noul_five_concurrent.py','core/jev_node.py'):
        target=out/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/relative,target)
    retry_tasks=[]
    for episode_id,frame in failed:
        task=dict(tasks[(episode_id,frame)],output=str(out),endpoint='https://api.site/v1/systemone',model='jev-1.14.0',timeout=120,attempts=a.attempts,question_version='v004')
        retry_tasks.append(task)
    write(out/'retry_audit.json',{'source_run':str(source),'reused':len(successful),'retry_tasks':failed,'concurrency':a.concurrency})
    retry=[]
    context=multiprocessing.get_context('spawn')
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(a.concurrency,len(retry_tasks)),mp_context=context) as executor:
        futures=[executor.submit(run_task,t) for t in retry_tasks]
        for future in concurrent.futures.as_completed(futures):
            try:row=future.result()
            except BaseException as error:row={'phase':'failed','error':type(error).__name__+': '+str(error)}
            retry.append(row)
            if row.get('phase')=='complete':successful[(row['episode_id'],row['frame'])]=row
    final=sorted(successful.values(),key=lambda r:(r['episode_id'],r['frame']))
    write(out/'rows_v004.json',final)
    previous={(r['episode_id'],r['frame']):r for r in read(out/'rows_v002.json')}
    selection=read(out/'selection.json')['cases']
    summary={'cases':len(selection),'expected_calls':len(tasks),'valid_calls':len(final),'failed_calls':len(tasks)-len(final),'max_workers':read(source/'summary.json')['max_workers'],'retry_concurrency':a.concurrency,'by_case':{}}
    for case in selection:
        eid=case['episode_id'];current=[r for r in final if r['episode_id']==eid];old={r['frame']:r for (case_id,_),r in previous.items() if case_id==eid};paired=[(r,old[r['frame']]) for r in current if r['frame'] in old]
        summary['by_case'][eid]={'valid':len(current),'expected':case['eligible'],'previous_mean':sum(o['answer']['probability_yes'] for _,o in paired)/len(paired),'current_mean':sum(r['answer']['probability_yes'] for r,_ in paired)/len(paired),'increased':sum(r['answer']['probability_yes']>o['answer']['probability_yes'] for r,o in paired),'decreased':sum(r['answer']['probability_yes']<o['answer']['probability_yes'] for r,o in paired),'equal':sum(r['answer']['probability_yes']==o['answer']['probability_yes'] for r,o in paired)}
    paired=[(r,previous[(r['episode_id'],r['frame'])]) for r in final if (r['episode_id'],r['frame']) in previous]
    summary['overall']={'valid':len(final),'total':len(tasks),'previous_mean':sum(o['answer']['probability_yes'] for _,o in paired)/len(paired),'current_mean':sum(r['answer']['probability_yes'] for r,_ in paired)/len(paired),'increased':sum(r['answer']['probability_yes']>o['answer']['probability_yes'] for r,o in paired),'decreased':sum(r['answer']['probability_yes']<o['answer']['probability_yes'] for r,o in paired),'equal':sum(r['answer']['probability_yes']==o['answer']['probability_yes'] for r,o in paired)}
    summary.update(phase='complete' if len(final)==len(tasks) else 'complete_with_failures',finished_at=now(),retry_results=retry,credential_on_disk=False)
    write(out/'summary.json',summary);write(out/'status.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
