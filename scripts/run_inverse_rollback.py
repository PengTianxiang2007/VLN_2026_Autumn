"""Compare open-loop inverse H1 actions with the deployed physical pose reset."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import resource
import runpy
import shutil
import signal
import statistics
import subprocess
import sys
import time
from types import SimpleNamespace


ROOT = Path(os.environ.get('VLN_INVERSE_PROJECT', Path(__file__).resolve().parents[1]))
CAPTURE = ROOT / 'outputs/multiview_capture/v001/run_20261117_03'
DATA = ROOT / 'outputs/offline_route_dataset/v001/run_20261118_01/dataset'
PAIRS = ROOT / 'outputs/agent_recovery/branch_review_v001/run_20261121_02_all47/manifest.json'
ARMS = ('inverse', 'reset')
BACKWARD = 4  # Recorded action ID; the native H1 gait receives a negative body-forward speed.


def read(path):
    return json.loads(path.read_bytes())


def save(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def inverse_actions(history):
    movements = [a for a in history if a != 0]
    reverse = [{1: 1, 2: 3, 3: 2}[a] for a in reversed(movements)]
    if 1 in movements:
        return [2] * 12 + reverse + [3] * 12
    return reverse


def prepare(out, count, min_ab_xy_m=None, capture_rgb=False):
    rows = read(PAIRS)['cases']
    by_id = {row['case_id']: row for row in rows}
    if min_ab_xy_m is not None:
        selected = sorted(by_id)
    else:
        selected = ['C13'] + sorted(random.Random(2).sample(sorted(set(by_id) - {'C13'}), count - 1))
    cases = []
    for cid in selected:
        row = by_id[cid]
        eid, a, b = row['episode_id'], row['checkpoint_step'], row['alarm_step']
        path = DATA / 'provenance/capture_records' / (eid + '.jsonl')
        with path.open() as stream:
            records = [json.loads(line) for i, line in enumerate(stream) if a <= i <= b]
        if [r['step'] for r in records] != list(range(a, b + 1)) or a >= b:
            raise ValueError(f'Invalid A/B interval for {cid}')
        start = records[-1]
        target = records[0]
        distance = math.dist(target['robot_pose']['position_world_m'][:2],start['robot_pose']['position_world_m'][:2])
        if min_ab_xy_m is not None and distance < min_ab_xy_m:
            continue
        history = []
        for r in records[:-1]:
            action = r['action']
            if action == {'stop': []}:
                history.append(0)
            elif action in ({'move_by_discrete': [k]} for k in (1, 2, 3)):
                history.append(action['move_by_discrete'][0])
            else:
                raise ValueError(f'Unknown movement at {cid}/{r["step"]}: {action}')
        cases.append(dict(case_id=cid, episode_id=eid, scene=start['scene'], node=row['node_id'],
                          checkpoint_step=a, alarm_step=b, ab_xy_m=distance,
                          history=history, inverse=inverse_actions(history),
                          historical_start=start['physical_state_before'], historical_offset=start['environment_offset'],
                          target=target['robot_pose'], source=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    selected = [c['case_id'] for c in cases]
    if len(cases)!=count or len({c['episode_id'] for c in cases})!=count:
        raise ValueError(f'Expected {count} unique original alarm cases, got {len(cases)}')
    manifest = dict(seed=2, selection=selected, cases=cases, pairs=str(PAIRS), capture_rgb=capture_rgb,
                    min_ab_xy_m=min_ab_xy_m, eligible=len(rows), simulator_source=str(CAPTURE/'code'),
                    placement='recorded root and joints, joint velocities, zero root velocity; native warmed controller',
                    reset='CheckpointPair.restore_pose; 50 standing ticks', inverse_end='50 standing ticks',
                    xy_m=0.35, yaw_deg=15)
    config = sorted(CAPTURE.glob('runs/**/chunk_*/eval_config.py'))[0]
    freeze_run(out, manifest, config)


def prepare_backward(out, previous):
    manifest = read(previous/'manifest.json')
    for case in manifest['cases']:
        case['inverse'] = [{1: BACKWARD, 2: 3, 3: 2}[a] for a in reversed(case['history']) if a != 0]
    manifest.update(inverse_method='backward', after_run=str(previous),
                    action_labels={'0':'stop', '1':'forward', '2':'left', '3':'right', '4':'backward'})
    freeze_run(out, manifest, previous/'source/eval_config.py')


def freeze_run(out, manifest, config):
    out.mkdir(parents=True, exist_ok=False)
    for name in ('source', 'cases', 'logs'):
        (out / name).mkdir()
    shutil.copyfile(__file__, out / 'source/run_inverse_rollback.py')
    shutil.copyfile(config, out / 'source/eval_config.py')
    for case in manifest['cases']:
        (out / 'cases' / case['case_id']).mkdir()
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
    manifest.update(capture_config=str(config), git_head=git('rev-parse', 'HEAD'),
         workspace=git('status', '--short', '--untracked-files=no'),
         source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'source').iterdir()},
         created_at=time.time())
    save(out / 'manifest.json', manifest)
    print('Prepared', len(manifest['cases']), 'distinct cases, first:', manifest['selection'][0], flush=True)


def yaw(q):
    w, x, y, z = q
    return math.degrees(math.atan2(2 * (w*z + x*y), 1 - 2 * (y*y + z*z)))


def errors(position, orientation, target):
    return dict(xy_m=math.dist(position[:2], target['position_world_m'][:2]),
                yaw_deg=abs((yaw(orientation) - target['heading_deg'] + 180) % 360 - 180))


def save_summary(out, cases):
    paired = []
    for c in cases:
        paths = [out/'cases'/c['case_id']/(arm + '.json') for arm in ARMS]
        if all(p.is_file() for p in paths):
            inv, reset = (read(p) for p in paths)
            paired.append(dict(case_id=c['case_id'], inverse=inv, reset=reset,
                               delta_xy_m=inv['xy_m']-reset['xy_m'], delta_yaw_deg=inv['yaw_deg']-reset['yaw_deg']))
    stats = {arm: dict(passed=sum(p[arm]['passed'] for p in paired),
                       mean_xy_m=statistics.mean(p[arm]['xy_m'] for p in paired) if paired else None,
                       mean_yaw_deg=statistics.mean(p[arm]['yaw_deg'] for p in paired) if paired else None)
             for arm in ARMS}
    save(out/'summary.json', dict(completed_pairs=len(paired), total=len(cases), arms=stats, pairs=paired))


def tick_action(env, action, ticks):
    for i in range(1, ticks + 1):
        obs, _, ended, _, _ = env.step([{'h1': action}])
        ob = obs[0]['h1']
        if ended[0] or ob['finish_action']:
            return ob, bool(ended[0]), i
    raise RuntimeError(f'Action did not complete within {ticks} physics ticks: {action}')


def tick_inverse_action(env, controller, action):
    if action != BACKWARD:
        return tick_action(env, {'move_by_discrete': [action]}, controller.steps_per_action)
    # Keep native action timing and gait feedback. Only the longitudinal
    # command changes sign, for the duration of this translation.
    speed = controller.forward_speed
    if speed <= 0:
        raise ValueError(f'Expected positive H1 forward speed, got {speed}')
    controller.forward_speed = -speed
    try:
        return tick_action(env, {'move_by_discrete': [1]}, controller.steps_per_action)
    finally:
        controller.forward_speed = speed


def save_native_rgb(path, task, world, ob):
    import numpy as np
    from PIL import Image
    from core.step_multiview import pose_record
    tick = world.current_time_step_index
    if ob is None or ob.get('rgb') is None:
        ob = task.get_rgb_depth()
    rgb = np.asarray(ob['rgb'])
    if rgb.shape != (480,640,3) or rgb.dtype != np.uint8:
        raise RuntimeError(f'Invalid native RGB {rgb.shape} {rgb.dtype}')
    camera = task.robot.sensors['pano_camera_0']
    position, quat = camera.get_world_pose()
    if world.current_time_step_index != tick:
        raise RuntimeError('RGB observation advanced physics')
    tmp = path.with_suffix('.part')
    Image.fromarray(rgb).save(tmp, format='PNG', compress_level=2)
    tmp.replace(path)
    return dict(file=path.relative_to(path.parents[2]).as_posix(), width=640, height=480,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(), sensor='pano_camera_0',
                simulation_step=int(tick), simulation_time_s=float(world.current_time),
                camera_pose=pose_record(position,quat,camera=True))


def evaluate_arm(out, case, arm, env, helper_cls, capture_rgb=False, sync_start_camera=False):
    import numpy as np
    directory = out/'cases'/case['case_id']
    task, = env.env.runner.current_tasks.values()
    if task.data['episode_id'] != case['episode_id']:
        raise RuntimeError('Simulator reset to an unexpected episode')
    art = task.robot.articulation._articulation
    ob, ended, _ = tick_action(env, {'stand_still': []}, 500)
    if ended:
        raise RuntimeError('Historical episode warm-up terminated before B initialization')
    standing = art.get_joint_positions().copy()
    start = case['historical_start']
    offset = np.asarray(task.env_offset) - np.asarray(case['historical_offset'])
    art.set_world_pose(position=np.asarray(start['position']) + offset, orientation=np.asarray(start['rotation']))
    art.set_world_velocity(np.zeros(6))
    art.set_joint_positions(np.asarray(start['joints']))
    art.set_joint_velocities(np.asarray(start['joint_velocities']))
    def pose():
        pos, quat = art.get_world_pose()
        return dict(position=(pos - offset).tolist(), orientation=quat.tolist())
    initial = pose()
    if (not np.allclose(initial['position'], start['position'], rtol=0, atol=1e-4) or
        abs(float(np.dot(initial['orientation'], start['rotation']))) < 0.99999):
        raise RuntimeError('B pose readback differs from the frozen pose')
    target = case['target']
    world = env.env.runner._world
    rgb_dir = directory/'rgb'/arm
    if capture_rgb:
        rgb_dir.mkdir(parents=True, exist_ok=True)
        if sync_start_camera:
            # Publish the placed torso/link transforms to the USD-mounted
            # camera before rendering, without moving the gait forward.
            from omni.physx import get_physx_interface
            start_tick = world.current_time_step_index
            if world.physics_sim_view is not None:
                world.physics_sim_view.update_articulations_kinematic()
            get_physx_interface().update_transformations(False, True, False, False)
            world.render()
            if world.current_time_step_index != start_tick:
                raise RuntimeError('B camera synchronization advanced physics')
        # The last warm-up image precedes the placement. Take a native camera
        # observation at the live B pose without advancing a physics tick.
        initial['rgb'] = save_native_rgb(rgb_dir/'start.png', task, world, None)
        if sync_start_camera:
            camera_xy = initial['rgb']['camera_pose']['position_world_m'][:2]
            initial['camera_root_xy_m'] = math.dist(camera_xy, np.asarray(initial['position'][:2])+offset[:2])
    save(directory/(arm + '_start.json'), initial)
    tick_start = world.current_time_step_index
    reason = ''
    executed = 0
    if arm == 'reset':
        helper = object.__new__(helper_cls)
        target_world = np.asarray(target['position_world_m']) + offset
        target_local = target_world - task.env_offset
        helper.active = dict(episode_id=case['episode_id'], initial_height=target_local[2], standing_joints=standing)
        helper.saved_root_pose = target_world, np.asarray(target['quaternion_wxyz'])
        try:
            ob, ended = helper.restore_pose(SimpleNamespace(env=env, robot_name='h1'), ob,
                dict(target_xy=target_local[:2].tolist(), target_yaw_rad=math.radians(target['heading_deg'])), directory)
        except RuntimeError as exc:
            if not str(exc).startswith(('Pose correction drift exceeded', 'Pose correction yaw drift exceeded')):
                raise
            reason = str(exc)
            ob = {}  # Pose check raised after settling; read this endpoint directly.
    else:
        controller = task.robot.controllers['move_by_discrete']
        if not math.isclose(math.degrees(controller.rotation_speed * controller.steps_per_action / controller.physics_frequency), 15):
            raise RuntimeError('Unexpected H1 turn calibration')
        with (directory/'inverse_trace.jsonl').open('w', buffering=1) as trace:
            previous = initial
            for i, action in enumerate(case['inverse'], 1):
                ob, ended, ticks = tick_inverse_action(env, controller, action)
                point = dict(index=i, action=action, ticks=ticks, ended=ended, **pose())
                if action == BACKWARD:
                    heading = math.radians(yaw(previous['orientation']))
                    dx, dy = (point['position'][j] - previous['position'][j] for j in (0, 1))
                    point.update(command_forward_mps=-float(controller.forward_speed),
                                 body_forward_displacement_m=dx*math.cos(heading) + dy*math.sin(heading))
                previous = point
                if capture_rgb:
                    point['rgb'] = save_native_rgb(rgb_dir/f'action_{i:04}.png', task, world, ob)
                trace.write(json.dumps(point) + '\n')
                executed = i
                if i == 1 and not ended and not (out/'startup.json').exists():
                    save(out/'startup.json', dict(pid=os.getpid(), gpu=os.environ['VLN_SIM_RENDER_GPU'],
                         case_id=case['case_id'], checkpoint=case['checkpoint_step'], alarm=case['alarm_step'],
                         initialized_B=initial, first_completed_inverse_action=point, time=time.time()))
                if ended:
                    break
        if not ended:
            task.warm_up_step = 50
            ob, ended, _ = tick_action(env, {'stand_still': []}, 50)
    final = pose()
    if capture_rgb:
        final['rgb'] = save_native_rgb(rgb_dir/'final.png', task, world, ob)
    err = errors(final['position'], final['orientation'], target)
    reason = reason or (ob.get('fail_reason', 'physical_termination') if ended else '')
    passed = not ended and not reason and err['xy_m'] <= 0.35 and err['yaw_deg'] <= 15
    save(directory/(arm + '.json'), dict(case_id=case['case_id'], arm=arm, **final, **err,
         passed=passed, ended=ended, reason=reason, inverse_actions_executed=executed,
         physical_ticks=int(world.current_time_step_index - tick_start)))


def worker(out, gpu):
    capcode = CAPTURE/'code'
    upstream = capcode/'benchmarks/vlnverse/upstream'
    sys.path[:0] = [str(capcode), str(upstream)]
    sys.argv[1:] = [f'--/renderer/activeGpu={gpu}', '--/renderer/multiGpu/enabled=False']
    from vlnverse.configs.evaluator.default_config import get_config
    from vlnverse.env import Env
    from vlnverse.evaluator.utils.eval import generate_episode
    from vlnverse.projects.dataloader.base import BasePathKeyDataloader
    from vlnverse.evaluator.utils.common import set_seed_model
    from core.oracle_checkpoint_pair import CheckpointPair
    set_seed_model(2)
    cfg = get_config(runpy.run_path(str(out/'source/eval_config.py'))['eval_cfg'])
    settings = cfg.dataset.dataset_settings
    loader = BasePathKeyDataloader(dataset_type=cfg.dataset.dataset_type,
        base_data_dir=settings['base_data_dir'], split_data_types=settings['split_data_types'],
        robot_offset=settings['robot_offset'], filter_same_trajectory=settings['filter_same_trajectory'],
        filter_stairs=settings['filter_stairs'])
    loader.task_name = 'inverse_rollback'
    keys = {data['episode_id']: k for k, data in loader.path_key_data.items()}
    manifest = read(out/'manifest.json')
    cases = manifest['cases']
    pending = [(case, arm) for case in cases for arm in ARMS
               if not (out/'cases'/case['case_id']/(arm + '.json')).exists()]
    loader.resumed_path_key_list = [keys[case['episode_id']] for case, arm in pending]
    cfg.task.task_settings['episodes'] = generate_episode(loader, cfg)
    env = Env.init(cfg.env, cfg.task)
    try:
        for i, (case, arm) in enumerate(pending):
            save(out/'progress.json', dict(case_id=case['case_id'], arm=arm, pid=os.getpid(), time=time.time()))
            env.reset([0] if i else None)
            evaluate_arm(out, case, arm, env, CheckpointPair, manifest.get('capture_rgb',False),
                         sync_start_camera=manifest.get('inverse_method') == 'backward')
            save_summary(out, cases)
            if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > 24000 * 1024:
                break
    finally:
        env.close()


def supervise(out, gpu):
    sys.path.insert(0, str(ROOT))
    import fcntl
    from scripts.evaluate import check_gpu
    manifest = read(out/'manifest.json')
    cases = manifest['cases']
    child = None
    def stop(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    st = dict(pid=os.getpid(), gpu=gpu, total=len(cases))
    def status(phase, **fields):
        st.update(phase=phase, updated_at=time.time(), **fields)
        save(out/'status.json', st)
    env = dict(os.environ, VLN_INVERSE_PROJECT=str(ROOT), VLN_EVAL_SEED='2',
               CUDA_VISIBLE_DEVICES=str(gpu), VLN_SIM_RENDER_GPU=str(gpu), PYTHONHASHSEED='2',
               VLN_SIM_CACHE_ROOT=str(CAPTURE/'code/benchmarks/vlnverse/runner'), HF_HUB_OFFLINE='1',
               TRANSFORMERS_OFFLINE='1', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4')
    script = out/'source/run_inverse_rollback.py'
    command = ['bash', str(ROOT/'scripts/run_crossing_panorama_isaac.sh'), str(script),
               'worker', '--output', str(out), '--gpu', str(gpu)]
    def remaining():
        return sum(not (out/'cases'/c['case_id']/(arm+'.json')).exists() for c in cases for arm in ARMS)
    try:
        with (out/'supervisor.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            save_summary(out, cases)
            if 'after_run' in manifest:
                previous = Path(manifest['after_run'])
                status('waiting_for_previous', after_run=str(previous), worker_pid=None)
                while True:
                    prior = read(previous/'status.json')
                    if prior['phase'] == 'complete' and prior['completed_pairs'] == len(cases):
                        break
                    if prior['phase'] not in ('admission', 'running'):
                        raise RuntimeError(f"Preceding run ended with status {prior['phase']}")
                    time.sleep(15)
            while remaining():
                status('admission', worker_pid=None)
                while True:
                    try:
                        admission = check_gpu(gpu, 12000, allow_shared=True)
                        util = int(subprocess.check_output(['nvidia-smi', '-i', str(gpu),
                            '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'], text=True).strip())
                        if util <= 10:
                            break
                    except RuntimeError:
                        pass
                    time.sleep(15)
                before = remaining()
                log = out/'logs'/f'isaac_{time.time_ns()}.log'
                with log.open('x') as stream:
                    child = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, env=env,
                                             cwd=ROOT, start_new_session=True)
                    status('running', worker_pid=child.pid, log=str(log), admission=admission)
                    rc = child.wait()
                    child = None
                if rc or remaining() >= before:
                    raise RuntimeError(f'Isaac exited {rc}, see {log}')
        status('complete', worker_pid=None, completed_pairs=len(cases))
    except BaseException as exc:
        status('failed', error=repr(exc))
        raise
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(30)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'prepare-backward', 'run', 'worker'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--count', type=int, default=30)
    parser.add_argument('--min-ab-xy-m', type=float, help='Keep all original alarm pairs at or above this XY separation')
    parser.add_argument('--capture-rgb', action='store_true', help='Record native camera at B, each inverse step and both endpoints')
    parser.add_argument('--gpu', type=int, default=3)
    parser.add_argument('--after-run', type=Path, help='Freeze the same cases and wait for this run to complete')
    a = parser.parse_args()
    directory = a.output.resolve()
    if a.stage == 'prepare':
        prepare(directory, a.count, a.min_ab_xy_m, a.capture_rgb)
    elif a.stage == 'prepare-backward':
        if a.after_run is None:
            parser.error('prepare-backward requires --after-run')
        prepare_backward(directory, a.after_run.resolve())
    elif a.stage == 'run':
        supervise(directory, a.gpu)
    else:
        worker(directory, a.gpu)
