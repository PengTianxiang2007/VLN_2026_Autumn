"""Bounded continue-only wait at an already reviewed non-checkpoint location."""
import argparse,json,time,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.oracle_checkpoint_pair import validate
p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);p.add_argument('--request-id',required=True);p.add_argument('--reason',required=True);p.add_argument('--max-reviews',type=int,default=8);a=p.parse_args()
if not 1<=a.max_reviews<=8:raise ValueError('Bounded eight requests maximum')
pending=a.campaign/'oracle_records/pending.json';q=json.loads(pending.read_text());path=Path(q['request']);r=json.loads(path.read_text());origin=r['position'][:2];eid=r['episode_id']
if q['status']!='waiting' or r['request_id']!=a.request_id:raise ValueError('Stale request')
for index in range(a.max_reviews):
 if r['mode']!='trunk' or r['episode_id']!=eid or r['checkpoint'] is not None:break
 if math.dist(r['position'][:2],origin)>.25 or math.dist(r['position'][:2],r['crossing']['position'])<=1.5:break
 response=dict(request_id=r['request_id'],decision='continue',reason=a.reason,
               continue_only_guard={'source_request':a.request_id,'origin_xy':origin,'max_displacement_m':.25,'minimum_crossing_distance_m':1.5,'index':index})
 validate(response,r)
 with (path.parent/'response.json').open('x') as f:json.dump(response,f,ensure_ascii=False)
 for _ in range(55):
  time.sleep(1);q=json.loads(pending.read_text())
  if q['status']=='episode_complete':print(json.dumps(q));sys.exit(0)
  if q['status']=='waiting' and q['request']!=str(path):path=Path(q['request']);r=json.loads(path.read_text());break
 else:print('No new request; guard stopped.');sys.exit(0)
print(json.dumps({k:r[k] for k in ['request_id','mode','action_index','position','rotation','image']},ensure_ascii=False))
