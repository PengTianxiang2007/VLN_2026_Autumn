"""Queue paired RGB round trips on randomly sampled RxR-CE validation navmeshes."""
import argparse
import fcntl
import gzip
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import random
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time


SEED = 2
GOAL_RADIUS = 0.20
FORWARD, BACK, LEFT, RIGHT = 'move_forward', 'move_backward', 'turn_left', 'turn_right'
ARMS = ('turnaround', 'backward')


def read(path):
    return json.loads(path.read_bytes())


def save(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    tmp.replace(path)


def horizontal(a, b):
    return math.hypot(float(a[0]) - float(b[0]), float(a[2]) - float(b[2]))


def agent_config(settings, camera=False):
    import habitat_sim as hs
    agent = hs.agent.AgentConfiguration()
    for key in (FORWARD, BACK, LEFT, RIGHT):
        amount = settings['step_m'] if key in (FORWARD, BACK) else settings['turn_deg']
        agent.action_space[key] = hs.agent.ActionSpec(key, hs.agent.ActuationSpec(amount=amount))
    if camera:
        rgb = hs.CameraSensorSpec()
        rgb.uuid = 'rgb'
        rgb.sensor_type = hs.SensorType.COLOR
        rgb.resolution = [settings['height'], settings['width']]
        rgb.hfov = settings['hfov']
        rgb.position = [0, settings['camera_height_m'], 0]
        agent.sensor_specifications = [rgb]
    return agent


def initial_state(point, yaw):
    import habitat_sim as hs
    import numpy as np
    from habitat_sim.utils.common import quat_from_angle_axis
    return hs.AgentState(position=np.asarray(point, dtype=np.float32),
                         rotation=quat_from_angle_axis(math.radians(yaw), np.array([0., 1., 0.])))


def sample_routes(scene, mesh, settings, rng, index):
    import habitat_sim as hs
    import numpy as np
    from habitat_sim.scene import SceneGraph
    pf = hs.PathFinder()
    if not pf.load_nav_mesh(str(mesh)):
        raise RuntimeError(f'Cannot load {mesh}')
    pf.seed(SEED + index)
    graph = SceneGraph()
    agent = hs.Agent(graph.get_root_node().create_child(), agent_config(settings))
    agent.controls.move_filter_fn = pf.try_step
    follower = hs.GreedyGeodesicFollower(pf, agent, GOAL_RADIUS)
    cases = []
    for _ in range(4000):
        a = pf.get_random_navigable_point()
        b = pf.get_random_navigable_point()
        distance = horizontal(a, b)
        # Reserve the follower's stopping radius so the actual B also satisfies the bounds.
        if not 1.5 + GOAL_RADIUS <= distance <= 8 - GOAL_RADIUS or abs(a[1] - b[1]) > 0.35:
            continue
        path = hs.ShortestPath()
        path.requested_start, path.requested_end = a, b
        if not pf.find_path(path) or np.ptp(np.asarray(path.points)[:, 1]) > 0.35:
            continue
        heading = rng.uniform(-180, 180)
        agent.set_state(initial_state(a, heading))
        try:
            plan = follower.find_path(b)
        except hs.errors.GreedyFollowerError:
            continue
        if not plan or plan[-1] is not None or len(plan) > 500:
            continue
        cases.append(dict(case_id=f'RX{4 * index + len(cases) + 1:02}', scene=scene,
                          a_xyz=a.tolist(), b_goal_xyz=b.tolist(), a_yaw_deg=heading,
                          ab_goal_xz_m=distance, geodesic_m=path.geodesic_distance,
                          outbound_plan=plan[:-1]))
        if len(cases) == 4:
            return cases
    raise RuntimeError(f'Found only {len(cases)} usable routes in {scene}')


def prepare(out, previous):
    import yaml
    root = Path(__file__).resolve().parents[1]
    previous_manifest = read(previous/'manifest.json')
    if previous_manifest.get('inverse_method') != 'backward':
        raise ValueError('Expected preceding H1 backward experiment')
    model = root/'backbone/streamvln'
    config = model/'config/vln_rxr.yaml'
    cfg = yaml.safe_load(config.read_text())['habitat']
    dataset = cfg['dataset']
    annotations = model/dataset['data_path'].format(split=dataset['split'])
    with gzip.open(annotations, 'rt') as f:
        episodes = json.load(f)['episodes']
    scenes = sorted({e['scene_id'] for e in episodes if e['instruction']['language'] in ('en-US','en-IN')})[:5]
    if len(scenes) != 5:
        raise ValueError('Need five distinct RxR Guide validation scenes')
    sim = cfg['simulator']
    rgb = sim['agents']['main_agent']['sim_sensors']['rgb_sensor']
    settings = dict(width=rgb['width'], height=rgb['height'], hfov=rgb['hfov'], camera_height_m=1.25,
                    step_m=sim['forward_step_size'], turn_deg=sim['turn_angle'], allow_sliding=True)
    rng = random.Random(SEED)
    cases = []
    assets = {}
    for i, scene in enumerate(scenes):
        glb = (model/dataset['scenes_dir']/scene).resolve(strict=True)
        assets[scene] = str(glb)
        cases.extend(sample_routes(scene, glb.with_suffix('.navmesh'), settings, rng, i))
    out.mkdir(parents=True, exist_ok=False)
    (out/'cases').mkdir()
    source = out/'source'
    source.mkdir()
    for path in (Path(__file__), config):
        shutil.copyfile(path, source/path.name)
    save(out/'manifest.json', dict(benchmark='RxR-CE', split=dataset['split'], annotations=str(annotations),
         project=str(root), seed=SEED, after_run=str(previous), after_total=len(previous_manifest['cases']),
         ab_horizontal_limits_m=[1.5, 8.0], goal_radius_m=GOAL_RADIUS, settings=settings, assets=assets,
         git_head=subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip(),
         source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()},
         cases=cases))
    print(f'Prepared {len(cases)} routes in {len(scenes)} RxR-CE scenes', flush=True)


def pose(state):
    from habitat_sim.utils.common import quat_rotate_vector, quat_to_coeffs
    front = quat_rotate_vector(state.rotation, [0., 0., -1.])
    return dict(xyz=state.position.tolist(), quaternion_xyzw=quat_to_coeffs(state.rotation).tolist(),
                yaw_deg=math.degrees(math.atan2(-front[0], -front[2])))


def record_leg(sim, attempt, leg, actions, settings):
    import numpy as np
    from PIL import Image
    folder = attempt/leg
    folder.mkdir()
    agent = sim.get_agent(0)
    executed = []
    with (folder/'trace.jsonl').open('x') as trace:
        for i, action in enumerate(itertools.chain([None], actions)):
            if action is None:
                obs = sim.get_sensor_observations()
            else:
                obs = sim.step(action)
                executed.append(action)
            rgb = np.asarray(obs['rgb'])
            if rgb.shape not in ((settings['height'], settings['width'], 4),
                                 (settings['height'], settings['width'], 3)) or rgb.dtype != np.uint8:
                raise ValueError(f'Invalid Habitat RGB {rgb.shape} {rgb.dtype}')
            image = folder/f'{i:04d}.png'
            Image.fromarray(np.ascontiguousarray(rgb[:,:,:3])).save(image, compress_level=2)
            state = agent.get_state()
            frame = dict(step=i, action=action, pose=pose(state), camera=pose(state.sensor_states['rgb']),
                         rgb=image.name, collided=bool(obs.get('collided', False)))
            trace.write(json.dumps(frame, allow_nan=False) + '\n')
    return executed


def rollback(actions, arm, turn_deg):
    inverse = {FORWARD: BACK if arm == 'backward' else FORWARD, LEFT: RIGHT, RIGHT: LEFT}
    sequence = [inverse[a] for a in reversed(actions)]
    if arm == 'turnaround':
        turns = round(180 / turn_deg)
        if not math.isclose(turns * turn_deg, 180):
            raise ValueError('Turn increment must permit an exact half turn')
        sequence = [LEFT] * turns + sequence + [RIGHT] * turns
    return sequence


def run_case(sim, case, out, settings):
    import numpy as np
    from PIL import Image
    case_dir = out/'cases'/case['case_id']
    case_dir.mkdir(exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix='attempt_', dir=case_dir))
    agent = sim.get_agent(0)
    agent.set_state(initial_state(case['a_xyz'], case['a_yaw_deg']))
    a = pose(agent.get_state())
    bounds = sim.pathfinder.get_bounds()
    raster = sim.pathfinder.get_topdown_view(0.04, a['xyz'][1])
    Image.fromarray(np.uint8(raster) * 255).save(attempt/'map.png')
    save(attempt/'map.json', dict(meters_per_pixel=0.04, height_y=a['xyz'][1],
                                  bounds_xyz=[list(map(float,v)) for v in bounds], row_axis='z', col_axis='x'))
    def collect(leg, actions):
        save(out/'progress.json', dict(case_id=case['case_id'], leg=leg, attempt=str(attempt), time=time.time()))
        return record_leg(sim, attempt, leg, actions, settings)
    actions = collect('outbound', case['outbound_plan'])
    b_state = agent.get_state()
    b = pose(b_state)
    separation = horizontal(a['xyz'], b['xyz'])
    miss = math.dist(b['xyz'], case['b_goal_xyz'])
    if not 1.5 <= separation <= 8.0 or miss > GOAL_RADIUS + 0.01:
        raise RuntimeError(f'{case["case_id"]} did not reach its frozen goal: {miss=} {separation=}')
    arms = {}
    for arm in ARMS:
        if arm == 'backward':
            agent.set_state(b_state, infer_sensor_states=False)
        start = pose(agent.get_state())
        if math.dist(start['xyz'], b['xyz']) > 1e-5 or abs((start['yaw_deg']-b['yaw_deg']+180)%360-180) > 1e-3:
            raise RuntimeError('Different measured B for paired return')
        executed = collect(arm, rollback(actions, arm, settings['turn_deg']))
        end = pose(agent.get_state())
        xz = horizontal(a['xyz'], end['xyz'])
        angle = abs((end['yaw_deg'] - a['yaw_deg'] + 180) % 360 - 180)
        arms[arm] = dict(start=start, end=end, xz_m=xz, yaw_deg=angle, passed=xz <= 0.35 and angle <= 15,
                         rgb_frames=len(executed) + 1)
    save(case_dir/'result.json', dict(case_id=case['case_id'], attempt=attempt.name, a=a, achieved_b=b,
         actual_ab_xz_m=separation, goal_miss_m=miss, outbound_rgb_frames=len(actions)+1, arms=arms))


def summarize(out, cases):
    rows = []
    for c in cases:
        path = out/'cases'/c['case_id']/'result.json'
        if path.is_file():
            rows.append(read(path))
    arms = {}
    for arm in ARMS:
        results = [r['arms'][arm] for r in rows]
        arms[arm] = dict(passed=sum(r['passed'] for r in results),
                         mean_xz_m=statistics.mean(r['xz_m'] for r in results) if results else None,
                         mean_yaw_deg=statistics.mean(r['yaw_deg'] for r in results) if results else None)
    save(out/'summary.json', dict(completed_pairs=len(rows), total=len(cases), arms=arms, pairs=rows))
    return len(rows)


def worker(out, manifest, gpu):
    import habitat_sim as hs
    settings = manifest['settings']
    for scene, group in itertools.groupby(manifest['cases'], key=lambda c: c['scene']):
        pending = [c for c in group if not (out/'cases'/c['case_id']/'result.json').is_file()]
        if not pending:
            continue
        config = hs.SimulatorConfiguration()
        config.scene_id = manifest['assets'][scene]
        config.gpu_device_id = gpu
        config.enable_physics = False
        config.allow_sliding = settings['allow_sliding']
        sim = hs.Simulator(hs.Configuration(config, [agent_config(settings, camera=True)]))
        try:
            mesh = Path(config.scene_id).with_suffix('.navmesh')
            if not sim.pathfinder.load_nav_mesh(str(mesh)):
                raise RuntimeError(f'Cannot load the sampled navmesh: {mesh}')
            for case in pending:
                run_case(sim, case, out, settings)
                summarize(out, manifest['cases'])
        finally:
            sim.close()


def supervise(out, gpu, manifest):
    root = Path(manifest['project'])
    sys.path.insert(0, str(root))
    from core.paths import model_environment, model_python
    from scripts.evaluate import check_gpu
    previous = Path(manifest['after_run'])
    def status(phase, **fields):
        save(out/'status.json', dict(phase=phase, pid=os.getpid(), gpu=gpu, after_run=str(previous),
                                     total=len(manifest['cases']), updated_at=time.time(), **fields))
    def stop(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    with (out/'supervisor.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        child = None
        try:
            summarize(out, manifest['cases'])
            status('waiting_for_previous', worker_pid=None)
            while True:
                prior = read(previous/'status.json')
                if prior['phase'] == 'complete' and prior.get('completed_pairs') == manifest['after_total']:
                    break
                if prior['phase'] not in ('waiting_for_previous', 'running', 'admission'):
                    raise RuntimeError(f'Preceding run: {prior}')
                time.sleep(15)
            status('admission', worker_pid=None)
            while True:
                try:
                    admission = check_gpu(gpu, 2500)
                    break
                except RuntimeError:
                    time.sleep(15)
            env = model_environment('streamvln')
            # Keep EGL's physical device ordinal and CUDA's ordinal identical.
            env['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
            env.pop('CUDA_VISIBLE_DEVICES', None)
            command = [str(model_python('streamvln')), '-Bu', str(out/'source'/Path(__file__).name),
                       'worker', '--output', str(out), '--gpu', str(gpu)]
            with (out/'habitat.log').open('a') as log:
                child = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
                status('running', worker_pid=child.pid, admission=admission)
                if child.wait():
                    raise RuntimeError(f'Habitat worker failed; see {log.name}')
            n = summarize(out, manifest['cases'])
            if n != len(manifest['cases']):
                raise RuntimeError(f'Only {n} completed pairs')
            status('complete', completed_pairs=n, worker_pid=None)
        except BaseException as exc:
            status('failed', error=repr(exc), worker_pid=None)
            raise
        finally:
            if child and child.poll() is None:
                child.terminate()
                child.wait()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare','run','worker'])
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--after-run', type=Path)
    parser.add_argument('--gpu', type=int, default=3)
    args = parser.parse_args()
    out = args.output.resolve()
    if args.stage == 'prepare':
        if not args.after_run:
            parser.error('prepare requires --after-run')
        prepare(out, args.after_run.resolve())
    elif args.stage == 'run':
        supervise(out, args.gpu, read(out/'manifest.json'))
    else:
        worker(out, read(out/'manifest.json'), args.gpu)
