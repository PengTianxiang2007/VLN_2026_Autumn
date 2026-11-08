"""Execute an explicitly supplied short Oracle action plan; never infer next actions."""
import argparse,json,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.oracle_checkpoint_pair import validate

def main():
 p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);p.add_argument('--request-id',required=True)
 p.add_argument('--actions',type=int,nargs='+',required=True);p.add_argument('--reason',required=True);a=p.parse_args()
 if not 1<=len(a.actions)<=4 or any(x not in (1,2,3) for x in a.actions):p.error('1–4 explicit forward/left/right actions only')
 pending=a.campaign/'oracle_records/pending.json';q=json.loads(pending.read_text());path=Path(q['request']);r=json.loads(path.read_text())
 if q['status']!='waiting' or r['request_id']!=a.request_id or r['mode']!='oracle_actions':raise ValueError('Stale/non-Oracle request')
 eid=r['episode_id']
 for index,action in enumerate(a.actions):
  if r['mode']!='oracle_actions' or r['episode_id']!=eid:raise ValueError('Do not cross arm/case')
  response=dict(request_id=r['request_id'],decision='action',action=action,reason=a.reason,
                explicit_plan={'source_request':a.request_id,'actions':a.actions,'index':index})
  validate(response,r)
  with (path.parent/'response.json').open('x') as f:json.dump(response,f,ensure_ascii=False)
  for _ in range(55):
   time.sleep(1);q=json.loads(pending.read_text())
   if q['status']=='episode_complete':print(json.dumps(q));return
   if q['status']=='waiting' and q['request']!=str(path):
    path=Path(q['request']);r=json.loads(path.read_text());break
  else:print('Plan paused: no next request; no remaining actions sent.');return
 print(json.dumps({k:r[k] for k in ['request_id','mode','action_index','position','rotation','image']},ensure_ascii=False))
if __name__=='__main__':main()
