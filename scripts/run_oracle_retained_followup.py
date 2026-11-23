"""Start one explicitly authorized follow-up after its prerequisite completes."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_oracle_existing_model import identity
from scripts.run_oracle_distance import write


def main(plan_path):
    plan=json.loads(plan_path.read_text());after=Path(plan['after']);campaign=Path(plan['campaign'])
    state=dict(phase=plan.get('waiting_phase','waiting_for_checkpoint_group'),pid=os.getpid(),after=str(after),campaign=str(campaign),started_at=time.time())
    status=campaign/'queue_status.json';write(status,state)
    while True:
        if (campaign/'cancel_followup').exists():
            state.update(phase='cancelled');write(status,state);return
        previous=json.loads((after/'status.json').read_text())
        if previous['phase']=='complete_services_retained':break
        if previous['phase'] in ('failed','stopped','cancelled'):
            state.update(phase='prerequisite_not_complete',previous=previous);write(status,state);return
        time.sleep(10)
    if identity(plan['model_identity']['pid'])!=plan['model_identity']:
        raise RuntimeError('Retained model identity changed')
    chunk=Path(previous['chunk']);marker=chunk/'simulator_retained.json';held=json.loads(marker.read_text())
    pid=held['pid'];sim=identity(pid)
    if str(after) not in sim['command']:raise RuntimeError('Unexpected retained simulator')
    state.update(phase='releasing_completed_simulator',old_simulator=sim);write(status,state)
    marker.with_suffix('.release').write_text('Next user-authorized group; keep model loaded.\n')
    for _ in range(60):
        p=Path('/proc')/str(pid)
        if not p.exists() or p.joinpath('stat').read_text().split()[2]=='Z':break
        time.sleep(1)
    else:
        if identity(pid)==sim:
            os.kill(pid,signal.SIGTERM)
            for _ in range(20):
                p=Path('/proc')/str(pid)
                if not p.exists() or p.joinpath('stat').read_text().split()[2]=='Z':break
                time.sleep(1)
            else:raise RuntimeError('Completed simulator did not release; model retained')
    with (campaign/'supervisor.log').open('x') as log:
        child=subprocess.Popen(plan['command'],cwd=plan['cwd'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    state.update(phase='running',worker_pid=child.pid,command=plan['command']);write(status,state)
    rc=child.wait();state.update(phase='complete' if rc==0 else 'failed',exit_code=rc,finished_at=time.time());write(status,state)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True)
    main(p.parse_args().plan)
