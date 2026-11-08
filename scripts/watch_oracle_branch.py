"""Read-only bounded live Oracle status and review rendering helper."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def main():
    p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);p.add_argument('--wait',type=float,default=30);a=p.parse_args()
    out=a.campaign.resolve();deadline=time.time()+min(a.wait,45)
    while True:
        state=json.loads((out/'status.json').read_text()) if (out/'status.json').exists() else {}
        pending=json.loads((out/'oracle_records/pending.json').read_text()) if (out/'oracle_records/pending.json').exists() else {}
        if pending.get('status')=='waiting' and not Path(pending['request']).with_name('response.json').exists():
            path=Path(pending['request']);r=json.loads(path.read_text())
            if not (path.parent/'review.jpg').exists():
                from scripts import oracle_crossing_console as view
                view.CAMPAIGN=out
                with contextlib.redirect_stdout(io.StringIO()):view.render(path)
            print(json.dumps(dict(image=str(path.parent/'review.jpg'),request=str(path),
                 **{k:r[k] for k in ('episode_id','mode','action_index','position','event','saved_arms','physics_ticks','intervention_count')}),ensure_ascii=False));return
        if state.get('phase') in ('failed','stopped','complete') or time.time()>=deadline:
            print(json.dumps({k:state.get(k) for k in ('phase','episode_id','completed','error')},ensure_ascii=False));return
        time.sleep(1)

if __name__=='__main__':main()
