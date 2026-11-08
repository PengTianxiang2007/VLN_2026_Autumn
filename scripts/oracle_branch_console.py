"""Inspect and explicitly label live semantic Oracle requests; never auto-detect."""
import argparse
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.oracle_crossing import write
from core.oracle_branching import STAGES
from scripts import oracle_crossing_console as view

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['show','respond']);p.add_argument('--campaign',type=Path,required=True)
    p.add_argument('--stage',choices=STAGES);p.add_argument('--target');p.add_argument('--reason');a=p.parse_args()
    pending_path=a.campaign/'oracle_records/pending.json'
    pending=json.loads(pending_path.read_text()) if pending_path.exists() else {'status':'initializing'}
    if pending['status']!='waiting':print(json.dumps(pending));return
    path=Path(pending['request']);r=json.loads(path.read_text())
    if a.command=='show':
        view.CAMPAIGN=a.campaign.resolve();view.render(path)
        print(json.dumps({k:r[k] for k in ['mode','calibration','event','saved_arms','physics_ticks']},ensure_ascii=False));return
    if not a.stage or len(a.reason or '')<12:raise ValueError('Stage and evidence reason required')
    if a.stage=='onset' and a.target not in {t['id'] for t in r['targets']}:raise ValueError('Frozen target required')
    response=dict(request_id=r['request_id'],stage=a.stage,reason=a.reason,reviewer='assistant_oracle',time=time.time())
    if a.target:response['target_id']=a.target
    if (path.parent/'response.json').exists():raise FileExistsError('Already responded')
    write(path.parent/'response.json',response);print(json.dumps(response,ensure_ascii=False))

if __name__=='__main__':main()
