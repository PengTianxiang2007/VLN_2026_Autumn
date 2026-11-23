"""Run sealed point capture after the authorized queue releases its simulator."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_oracle_existing_model import identity,assert_model,stop_simulator
from scripts.run_oracle_distance import write


def validate(out,manifest):
    total=0
    for point in manifest['points']:
        record=json.loads((out/'points'/point['point_id']/'complete.json').read_text())
        assert record['point_id']==point['point_id'] and len(record['views'])==8
        assert [v['relative_yaw_deg'] for v in record['views']]==manifest['view_offsets_deg']
        for name,indices in manifest['view_sets'].items():
            meta=json.loads((out/record['view_sets'][name]).read_text())
            assert meta['point']==point and [v['id'] for v in meta['views']]==indices
            for v in meta['views']:
                path=(out/v['path']).resolve();assert path.is_relative_to(out)
                raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==v['sha256']==record['views'][v['id']]['sha256']
                assert raw[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',raw[16:24])==(640,480)
        total+=8
    assert total==manifest['expected_unique_rgb']
    return dict(passed=True,points=manifest['unique_points'],case_references=manifest['retained_node_references'],
                unique_rgb=total,view_180_references=manifest['unique_points']*3,view_360_references=total,
                estimated_headings=True,model_calls=0,navigation_actions=0,validated_at=time.time())


def main(a):
    out=a.output.resolve();m=json.loads((out/'manifest.json').read_text());seal=json.loads((out/'seal.json').read_text())
    assert hashlib.sha256((out/'manifest.json').read_bytes()).hexdigest()==seal['manifest_sha256']
    for rel,h in m['source_hashes'].items():assert hashlib.sha256((out/'source'/rel).read_bytes()).hexdigest()==h
    for s in m['scenes']:assert hashlib.sha256(Path(s['path']).read_bytes()).hexdigest()==s['sha256']
    if a.validate_only:print(json.dumps(validate(out,m)));return
    lock=(out/'run.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    saved=json.loads((out/'queue_plan.json').read_text())['model_identity'];assert_model(saved)
    prior=json.loads((Path(m['after'])/'status.json').read_text())
    if prior['phase']!='complete_services_retained':raise RuntimeError('Previous group is incomplete')
    old_pid=prior['simulator_pid'];old=Path('/proc')/str(old_pid)
    if old.exists() and old.joinpath('stat').read_text().split()[2]!='Z':raise RuntimeError('Previous simulator still live')
    state=dict(phase='waiting_for_resources',pid=os.getpid(),gpu=a.gpu,completed_points=0,expected_points=m['unique_points'],model_pid=saved['pid'],model_retained=True)
    child=None;retained=False
    def stop(*_):raise KeyboardInterrupt('Capture stopped; model retained')
    for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,stop)
    try:
        consecutive=0
        while consecutive<2:
            assert_model(saved)
            raw=subprocess.check_output(['nvidia-smi','-i',str(a.gpu),'--query-gpu=memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True)
            free,util=map(int,raw.strip().split(','))
            mem=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))
            consecutive=consecutive+1 if free>=12000 and util<=10 and mem>=64*1024**2 else 0
            state.update(gpu_free_mib=free,gpu_utilization=util,host_available_kib=mem,updated_at=time.time());write(out/'status.json',state)
            if (out/'cancel_followup').exists():raise KeyboardInterrupt('User cancelled queue')
            if consecutive<2:time.sleep(5)
        project=Path(m['project_root'])
        env={k:v for k,v in os.environ.items() if not k.lower().endswith('_proxy') and not k.startswith(('VLN_','PENG_','STREAMVLN_'))}
        env.update(CUDA_VISIBLE_DEVICES=str(a.gpu),VLN_SIM_CACHE_ROOT=str(out/'runtime_cache'),
            VLNVERSE_VENV=str(project/'benchmarks/vlnverse/.venv'),PENG_ISAAC_ROOT=str(project/'.runtime/isaac45'),
            HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
        for attempt in range(3):
            assert_model(saved)
            cmd=['bash',str(out/'source/scripts/run_crossing_panorama_isaac.sh'),str(out/'source/scripts/render_jev_point_capture.py'),'--output',str(out),'--gpu',str(a.gpu)]
            log_path=out/'logs'/('capture_'+str(time.time_ns())+'.log')
            with log_path.open('x') as log:child=subprocess.Popen(cmd,cwd=project,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            state.update(phase='rendering',simulator_pid=child.pid,simulator_identity=identity(child.pid),log=str(log_path),attempt=attempt+1,simulation_started=True)
            write(out/'status.json',state)
            while child.poll() is None:
                assert_model(saved)
                completed=len(list((out/'points').glob('*/complete.json')))
                state.update(completed_points=completed,updated_at=time.time());write(out/'status.json',state)
                if (out/'simulator_retained.json').exists():
                    marker=json.loads((out/'simulator_retained.json').read_text())
                    assert marker['pid']==child.pid and marker['start_ticks']==identity(child.pid)['start_ticks']
                    proof=validate(out,m);write(out/'validation.json',proof)
                    state.update(phase='complete_services_retained',completed_points=m['unique_points'],simulator_retained=True,finished_at=time.time())
                    write(out/'status.json',state);retained=True;return
                if (out/'cancel_followup').exists():raise KeyboardInterrupt('User cancelled capture')
                progress=out/'capture_progress.json';newest=max(log_path.stat().st_mtime,progress.stat().st_mtime if progress.exists() else 0)
                if time.time()-newest>900:stop_simulator(child);break
                time.sleep(5)
            write(out/'logs'/('exit_'+str(attempt)+'.json'),dict(exit_code=child.returncode,completed_points=state['completed_points'],log=str(log_path)))
        raise RuntimeError('Capture failed after three attempts; partial images preserved')
    except BaseException as e:
        state.update(phase='stopped' if isinstance(e,KeyboardInterrupt) else 'failed',error=repr(e));write(out/'status.json',state);raise
    finally:
        if not retained:stop_simulator(child)
        lock.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--gpu',type=int,default=3);p.add_argument('--validate-only',action='store_true');main(p.parse_args())
