"""Compact read/respond interface; no polling and no automatic Oracle decisions."""
import argparse,json
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True)
 p.add_argument('--decision',choices=['continue','checkpoint','error','verdict','action','handoff','abort'])
 p.add_argument('--wait',action='store_true');p.add_argument('--request-id');p.add_argument('--reason');p.add_argument('--action',type=int);p.add_argument('--choice',choices=['correct','wrong','uncertain'])
 a=p.parse_args();out=a.campaign
 pending=out/'oracle_records/pending.json'
 if not pending.exists():
  s=json.loads((out/'status.json').read_text());print(json.dumps({k:s.get(k) for k in ['phase','episode_id','completed','error']},ensure_ascii=False));return
 q=json.loads(pending.read_text())
 if q['status']!='waiting':print(json.dumps(q));return
 path=Path(q['request']);r=json.loads(path.read_text())
 if a.decision:
  import sys
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
  from core.oracle_checkpoint_pair import validate
  response=dict(request_id=a.request_id,decision=a.decision,reason=a.reason or '')
  if a.action is not None:response['action']=a.action
  if a.choice is not None:response['choice']=a.choice
  validate(response,r)
  with (path.parent/'response.json').open('x') as f:json.dump(response,f,ensure_ascii=False)
  print(json.dumps(response,ensure_ascii=False))
  if a.wait:
   import time
   for _ in range(55):
    time.sleep(1);q=json.loads(pending.read_text())
    if q['status']=='waiting' and q['request']!=str(path):
     nr=json.loads(Path(q['request']).read_text());print(json.dumps({k:nr[k] for k in ['request_id','mode','action_index','position','rotation','image']},ensure_ascii=False));break
   else:print('Awaiting next request; no action inferred.')
  return
 result={k:r[k] for k in ['request_id','mode','episode_id','action_index','position','rotation','instruction','expected','original_error','checkpoint','image','physics_ticks']}
 result['history']=[{k:row[k] for k in ['action_index','position','rotation']} for row in r['history']]
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
