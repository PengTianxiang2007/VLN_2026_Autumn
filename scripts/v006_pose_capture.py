"""Prepare and supervise fresh GPU-3 renders at the retained v006 camera poses."""
import argparse
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys

from run_crossing_panorama import ROOT, cleanup, gpu_snapshot, now, process, wait_for_idle, write


DATA = ROOT/'outputs/offline_route_dataset/v001/run_20261118_01/dataset'
NODES = ROOT/'outputs/deviation_progress/v006/all53_20261121_01/retained_nodes_and_terminals.json'
CAMPAIGN = ROOT/'outputs/multiview_capture/v001/run_20261117_03'
ASSETS = Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/VLNVerse/scenes')
RECORD = ROOT/'experiments/multiview_capture/v006_pose70/run_20261121_01'


def prepare(out):
    nodes = json.loads(NODES.read_bytes())
    episodes_file, = (CAMPAIGN/'runs').glob('**/dataset/fine/val_unseen/val_unseen.json.gz')
    with gzip.open(episodes_file) as stream:
        episodes = {ep['episode_id']:ep for ep in json.load(stream)['episodes']}
    rows = json.loads((NODES.parent/'v006_results.json').read_bytes())
    jobs, scenes = [], {}
    for row in rows:
        eid = row['episode_id']
        scene = episodes[eid]['scan']
        assets = ASSETS/scene
        paths = [assets/'start_result_navigation.usd', assets/(scene.removesuffix('_fix')+'.usda')]
        scenes[scene] = str(next(path for path in paths if path.is_file()))
        selected = {n['index']:n for n in nodes[eid] if not n['terminal_node']}
        with (DATA/'inputs'/eid/'observations.jsonl').open() as stream:
            for line in stream:
                obs = json.loads(line)
                n = selected.pop(obs['step'], None)
                if n is None:
                    continue
                assert obs['episode_id'] == eid and obs['native_front']['camera_pose'] == obs['native_camera_pose']
                jobs.append(dict(case_id=f"C{row['case_number']:02}", episode_id=eid, scene=scene,
                    frame=n['index'], node_id=n['id'], source_id=n['source_id'], emitted_at=n['emittedAt'],
                    camera=obs['native_camera_pose'], robot=obs['robot_pose'], calibration=obs['calibration'],
                    reference_front=obs['native_front'], original_time=obs['simulation_time_s'],
                    start_position=episodes[eid]['start_position']))
        assert not selected
    assert len(jobs)==376 and len(scenes)==19 and len(rows)==53
    out.mkdir(parents=True, exist_ok=False)
    for name in ('points','logs','scenes','source'):
        (out/name).mkdir()
    files = ['scripts/v006_pose_capture.py','scripts/render_v006_pose_capture.py','scripts/run_crossing_panorama_isaac.sh',
             'core/step_multiview.py','scripts/run_crossing_panorama.py','scripts/run_crossing_local_batch.py','scripts/test_crossing_single_gpu.py']
    hashes = {}
    for name in files:
        dst = out/'source'/name
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/name,dst)
        hashes[name] = hashlib.sha256(dst.read_bytes()).hexdigest()
    write(out/'manifest.json',dict(seed=2, version='v006', nodes=jobs, scenes=scenes, offsets_deg=[70,0,-70],
        cases=len(rows),expected_images=3*len(jobs),dataset=str(DATA),source_nodes=str(NODES),
        nodes_sha256=hashlib.sha256(NODES.read_bytes()).hexdigest(),source_sha256=hashes,
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        worktree=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),created_at=now()))
    write(out/'status.json',dict(phase='prepared',completed_nodes=0,expected_nodes=len(jobs)))


def run(out):
    m = json.loads((out/'manifest.json').read_bytes())
    gpu = 3
    uuid = subprocess.check_output(['nvidia-smi','-i','3','--query-gpu=uuid','--format=csv,noheader'],text=True).strip()
    state = dict(supervisor_pid=os.getpid(),gpu=gpu,uuid=uuid,expected_nodes=len(m['nodes']),expected_images=m['expected_images'])
    def phase(name, **fields):
        state.update(phase=name,updated_at=now(),**fields)
        write(out/'status.json',state)
    def stop(*_):
        raise KeyboardInterrupt('Capture stopped')
    signal.signal(signal.SIGTERM,stop)
    locks, admissions = [], []
    child = None
    error = None
    try:
        for prefix in ['peng_vlnverse_gpu_', 'vln_2026_gpu_']:
            lock = Path(f'/tmp/{prefix}{gpu}.lock').open('a')
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            locks.append(lock)
        completed = 0
        phase('admission',completed_nodes=0)
        env = {k:v for k,v in os.environ.items() if 'proxy' not in k.lower()}
        env.update(CUDA_VISIBLE_DEVICES=uuid,VLN_SIM_CACHE_ROOT=str(CAMPAIGN/'code/benchmarks/vlnverse/runner'),
                   PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',
                   HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
        for scene in m['scenes']:
            wait_for_idle(gpu,uuid,admissions,out,phase)
            cmd = ['bash',str(ROOT/'scripts/run_crossing_panorama_isaac.sh'),str(out/'source/scripts/render_v006_pose_capture.py'),
                   '--output',str(out),'--scene',scene]
            with (out/'logs'/f'{scene}.log').open('x') as log:
                child = subprocess.Popen(cmd,env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            phase('rendering',scene=scene,child_pid=child.pid,completed_nodes=completed)
            rc = child.wait()
            capture = out/'scenes'/f'{scene}.json'
            if rc or not capture.is_file():
                raise RuntimeError(f'{scene} exited {rc} without a successful scene close; see logs/{scene}.log')
            proof = json.loads(capture.read_bytes())
            assert proof['completed']==sum(n['scene']==scene for n in m['nodes'])
            completed += proof['completed']
            if cleanup(child)['remaining']:
                raise RuntimeError('Owned scene processes still present')
            child = None
        assert completed == len(m['nodes'])
    except BaseException as exc:
        error = repr(exc)
        raise
    finally:
        clean = cleanup(child) if child is not None else {}
        for lock in locks:
            lock.close()
        phase('failed' if error else 'complete',error=error,child_pid=None,
              completed_nodes=len(list((out/'points').glob('*/metadata.json'))),gpu_after=gpu_snapshot(),cleanup=clean)
        with (RECORD/'README.md').open('a') as f:
            f.write(f"\n{now()} 后台收尾：{state['phase']}，已完成 {state['completed_nodes']}/{len(m['nodes'])} 个节点。详见 status.json 和 progress.json。\n")


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['prepare','run'])
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    (prepare if args.stage=='prepare' else run)(args.output.resolve())
