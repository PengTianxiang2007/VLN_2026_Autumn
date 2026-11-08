"""Persistent explicit-review console; one stdin JSON per human/assistant decision."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.oracle_branching import STAGES
from core.oracle_crossing import write
from scripts import oracle_crossing_console as view

p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);a=p.parse_args()
out=a.campaign.resolve();view.CAMPAIGN=out

def pending():
    f=out/'oracle_records/pending.json'
    if not f.exists():return None
    d=json.loads(f.read_text())
    if d.get('status')!='waiting':return None
    path=Path(d['request'])
    if (path.parent/'response.json').exists():return None
    return path,json.loads(path.read_text())

def show(wait):
    deadline=time.time()+min(wait,40)
    while True:
        item=pending()
        if item:
            path,r=item
            if not (path.parent/'review.jpg').exists():
                with contextlib.redirect_stdout(io.StringIO()):view.render(path)
            data={k:r[k] for k in ('request_id','episode_id','mode','action_index','position','event','saved_arms','physics_ticks','intervention_count')}
            data['image']=str(path.parent/'review.jpg')
            print('REVIEW '+json.dumps(data,ensure_ascii=False),flush=True);return
        status=json.loads((out/'status.json').read_text())
        if status['phase'] in ('failed','stopped','complete') or time.time()>=deadline:
            print('STATUS '+json.dumps({k:status.get(k) for k in ('phase','episode_id','completed','error')},ensure_ascii=False),flush=True);return
        time.sleep(.25)

print('CONSOLE_READY',flush=True)
for line in sys.stdin:
    try:
        d=json.loads(line)
        if d.get('command')=='quit':break
        if 'stage' in d:
            item=pending()
            if item is None:raise ValueError('No unanswered request')
            path,r=item
            if d['request_id']!=r['request_id']:raise ValueError('Stale request')
            if d['stage'] not in STAGES or len(d.get('reason',''))<12:raise ValueError('Explicit semantic label and evidence required')
            if d['stage']=='onset' and d.get('target_id') not in {t['id'] for t in r['targets']}:raise ValueError('Unknown target')
            response=dict(d,reviewer='assistant_oracle',time=time.time())
            write(path.parent/'response.json',response)
            print('RESPONDED '+r['request_id'],flush=True)
        show(d.get('wait',10))
    except Exception as e:
        print('CONSOLE_ERROR '+repr(e),flush=True)
