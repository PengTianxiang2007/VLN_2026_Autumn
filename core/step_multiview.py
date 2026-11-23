"""Measured-pose, render-only capture at every native navigation action boundary."""
import hashlib
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import time

import numpy as np

OFFSETS = (0, 45, 90, 135, 180, 225, 270, 315)
FRONT = (1, 0, 7)  # left-front, front, right-front; positive yaw is left


def write(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def plain(value):
    if hasattr(value, 'tolist'):
        return value.tolist()
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def quat_product(a, b):
    w, x, y, z = a
    v, i, j, k = b
    return np.array([w*v-x*i-y*j-z*k, w*i+x*v+y*k-z*j,
                     w*j-x*k+y*v+z*i, w*k+x*j-y*i+z*v])


def turn_world_z(q, degrees):
    half = math.radians(degrees) / 2
    return quat_product([math.cos(half), 0, 0, math.sin(half)], q)


def rotate(q, v):
    q = np.asarray(q, dtype=float)
    q = q / np.linalg.norm(q)
    return quat_product(quat_product(q, [0, *v]), q * [1, -1, -1, -1])[1:]


def angle_delta(a, b):
    return (a-b+180) % 360-180


def pose_record(position, q, camera=False):
    q = np.asarray(q, dtype=float)
    q = q / np.linalg.norm(q)
    w, x, y, z = q
    roll = math.atan2(2*(w*x+y*z), 1-2*(x*x+y*y))
    pitch = math.asin(float(np.clip(2*(w*y-z*x), -1, 1)))
    yaw = math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))
    forward = rotate(q, [0, 0, -1] if camera else [1, 0, 0])
    heading = math.degrees(math.atan2(forward[1], forward[0]))
    return dict(position_world_m=plain(position), quaternion_wxyz=q.tolist(),
                roll_deg=math.degrees(roll), pitch_deg=math.degrees(pitch),
                yaw_deg=math.degrees(yaw), heading_deg=heading,
                forward_world=forward.tolist(),
                axes='USD camera: -Z forward, +Y up' if camera else 'robot: +X forward, +Z up')


def state_snapshot(task, world):
    art = task.robot.articulation
    pos, q = art.get_world_pose()
    cp, cq = task.robot.sensors['pano_camera_0'].get_world_pose()
    return dict(physics_ticks=int(task.step_count), world_time=float(world.current_time),
                world_step=int(world.current_time_step_index), position=plain(pos), rotation=plain(q),
                joints=plain(art.get_joint_positions()), joint_velocities=plain(art.get_joint_velocities()),
                camera_position=plain(cp), camera_rotation=plain(cq))


def assert_unchanged(before, after):
    for key in ('physics_ticks', 'world_time', 'world_step'):
        if before[key] != after[key]:
            raise RuntimeError('Capture advanced simulation: ' + key)
    for key in ('position', 'rotation', 'joints', 'joint_velocities', 'camera_position', 'camera_rotation'):
        if not np.allclose(before[key], after[key], atol=1e-7, rtol=0):
            raise RuntimeError('Capture changed physical state: ' + key)


def fresh_render(camera, render, previous_frame):
    """Wait for a new rendered frame without advancing simulation time."""
    for _ in range(3):
        render()
        frame = camera.get_current_frame()
        number = int(frame['rendering_frame'])
        if number > 0 and (previous_frame is None or number > previous_frame):
            return np.array(camera.get_rgba()[..., :3], copy=True), dict(frame)
    raise RuntimeError('Stale capture rendering frame after three render-only attempts')


@contextmanager
def temporary_visibility(attribute):
    """Hide robot appearance for auxiliary rendering; restore even on failure."""
    authored = attribute.HasAuthoredValueOpinion()
    previous = attribute.Get()
    proof = dict(previous=str(previous), authored=authored, restored=False,
                 scope='robot visual geometry hidden only during auxiliary capture; physics unchanged')
    attribute.Set('invisible')
    try:
        yield proof
    finally:
        if authored:
            attribute.Set(previous)
        else:
            attribute.Clear()
        if attribute.Get() != previous or attribute.HasAuthoredValueOpinion() != authored:
            raise RuntimeError('Failed to restore native robot visibility')
        proof['restored'] = True


class NativeViewCamera:
    def __init__(self):
        self.camera = None
        self.last_render = None

    def camera_setup(self, task):
        import omni.usd
        from pxr import UsdGeom
        from isaacsim.sensors.camera import Camera
        source_path = task.robot.config.prim_path + '/' + task.robot.sensors['pano_camera_0'].config.prim_path
        source = UsdGeom.Camera(omni.usd.get_context().get_stage().GetPrimAtPath(source_path))
        if not source:
            raise RuntimeError('Native camera prim missing: ' + source_path)
        if self.camera is None:
            # The default camera rate is gated by simulation time. Capture keeps
            # that time frozen, so explicitly acquire EVERY rendered frame.
            self.camera = Camera(prim_path='/World/StepMultiviewCapture', name='step_multiview',
                                 resolution=(640, 480), frequency=-1)
            self.camera.initialize()
        # Copy real native USD intrinsics; do not move or reconfigure the policy camera.
        names = ('focalLength', 'horizontalAperture', 'verticalAperture', 'clippingRange',
                 'horizontalApertureOffset', 'verticalApertureOffset', 'projection', 'fStop', 'focusDistance')
        for name in names:
            value = source.GetPrim().GetAttribute(name).Get()
            if value is not None:
                self.camera.prim.GetAttribute(name).Set(value)
        focal = float(source.GetFocalLengthAttr().Get())
        horizontal = float(source.GetHorizontalApertureAttr().Get())
        hfov = math.degrees(2*math.atan(horizontal/(2*focal)))
        if abs(hfov-90) > .001:
            raise RuntimeError('Expected native 90-degree horizontal FOV')
        return dict(resolution=[640, 480], horizontal_fov_deg=hfov, acquisition_frequency=-1,
                    intrinsic_matrix=self.camera.get_intrinsics_matrix().tolist(),
                    focal_length_usd=focal, horizontal_aperture_usd=horizontal,
                    vertical_aperture_usd=float(source.GetVerticalApertureAttr().Get()),
                    native_prim=source_path)


class StepCapture(NativeViewCamera):
    def __init__(self, evaluator, root):
        self.e = evaluator
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.active = None
        super().__init__()
        self.native_reset = evaluator.reset_seeded_agent
        self.native_action = evaluator.get_action
        self.native_terminate = evaluator.terminate_ops
        evaluator.reset_seeded_agent = self.after_reset
        evaluator.get_action = self.before_action
        evaluator.terminate_ops = self.before_terminate

    def task(self):
        tasks = list(self.e.env.env.runner.current_tasks.values())
        if len(tasks) != 1:
            raise RuntimeError('Step capture requires one native environment')
        return tasks[0]

    def begin(self, info):
        eid = info.data['episode_id']
        if self.active is not None:
            if self.active['episode_id'] != eid:
                raise RuntimeError('Episode changed without terminal capture')
            return
        directory = self.root/'episodes'/eid/('attempt_' + str(time.time_ns()))
        directory.mkdir(parents=True)
        self.active = dict(episode_id=eid, scene=info.data['scan'], directory=str(directory),
                           step=0, seed=self.e.run_seed, started_at=time.time(), pid=os.getpid())
        write(directory/'case.json', dict(self.active, status='running'))

    def after_reset(self, infos, indices):
        result = self.native_reset(infos, indices)
        if indices != [0] or len(infos) != 1:
            raise RuntimeError('Unexpected native reset shape')
        self.begin(infos[0])
        # Read-only audit of the retained model after the original native reset.
        import urllib.request
        from core.oracle_distance_native import check_reset
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(self.e.agent.base_url + '/oracle/state?deep=1', timeout=120) as response:
            proof = json.load(response)
        check_reset(proof, self.active['episode_id'], self.e.run_seed)
        write(Path(self.active['directory'])/'native_reset_proof.json', proof)
        return result

    def capture(self, ob, terminal=False):
        from PIL import Image
        import omni.replicator.core as rep
        task = self.task()
        world = self.e.env.env.runner._world
        before = state_snapshot(task, world)
        calibration = self.camera_setup(task)
        # Camera creation/initialization must also preserve simulation state.
        assert_unchanged(before, state_snapshot(task, world))
        robot = pose_record(before['position'], before['rotation'])
        native = pose_record(before['camera_position'], before['camera_rotation'], camera=True)
        align = angle_delta(robot['heading_deg'], native['heading_deg'])
        base_q = turn_world_z(before['camera_rotation'], align)
        folder = Path(self.active['directory'])/'steps'/f'{self.active["step"]:06d}'
        folder.mkdir(parents=True, exist_ok=False)
        (folder/'360').mkdir()
        (folder/'180').mkdir()
        policy_rgb = np.array(ob['rgb'], copy=True) if ob.get('rgb') is not None else None
        if policy_rgb is not None and not terminal:
            Image.fromarray(policy_rgb.astype(np.uint8)).save(folder/'policy_front.png')
        views = []
        import omni.usd
        from pxr import UsdGeom
        robot_prim = omni.usd.get_context().get_stage().GetPrimAtPath(task.robot.config.prim_path)
        visibility_attr = UsdGeom.Imageable(robot_prim).GetVisibilityAttr()
        with temporary_visibility(visibility_attr) as visibility_proof:
            for index, degrees in enumerate(OFFSETS):
                q = turn_world_z(base_q, degrees)
                self.camera.set_world_pose(np.asarray(before['camera_position']), q, camera_axes='usd')
                # Same render-only primitive used by the original observation path.
                rgb, frame = fresh_render(self.camera,
                    lambda: rep.orchestrator.step(rt_subframes=4, delta_time=0.0, pause_timeline=False),
                    self.last_render)
                frame_id = int(frame['rendering_frame'])
                self.last_render = frame_id
                if rgb.shape != (480, 640, 3) or rgb.dtype != np.uint8:
                    raise RuntimeError('Invalid multiview RGB')
                p, actual_q = self.camera.get_world_pose(camera_axes='usd')
                actual = pose_record(p, actual_q, camera=True)
                if not np.allclose(p, before['camera_position'], atol=1e-5, rtol=0):
                    raise RuntimeError('Capture optical center moved')
                if abs(angle_delta(actual['heading_deg'], robot['heading_deg']+degrees)) > .01:
                    raise RuntimeError('View does not match current robot heading')
                image_path = folder/'360'/f'view_{index:02d}.png'
                Image.fromarray(rgb).save(image_path)
                views.append(dict(view_id=index, relative_yaw_deg=angle_delta(degrees, 0),
                                  camera_pose=actual, image=str(image_path.relative_to(folder)),
                                  sha256=hashlib.sha256(image_path.read_bytes()).hexdigest(),
                                  rendering_frame=frame_id, rendering_time=float(frame['rendering_time']),
                                  rgb_std=float(rgb.std()), black_fraction=float((rgb.max(axis=2)<5).mean())))
        # Refresh sensors with the original robot appearance restored.
        rep.orchestrator.step(rt_subframes=4, delta_time=0.0, pause_timeline=False)
        # Fresh terminal front image; never reuse a previous navigation observation.
        if terminal:
            front = np.array(task.robot.sensors['pano_camera_0']._camera.get_rgba()[..., :3], copy=True)
            if front.shape != (480, 640, 3):
                raise RuntimeError('Missing terminal front image')
            Image.fromarray(front.astype(np.uint8)).save(folder/'terminal_front.png')
        front_paths = []
        for order, index in enumerate(FRONT):
            target = folder/'180'/f'view_{order:02d}.png'
            os.link(folder/views[index]['image'], target)
            front_paths.append(dict(view_id=index, image=str(target.relative_to(folder))))
        after = state_snapshot(task, world)
        assert_unchanged(before, after)
        if policy_rgb is not None and not np.array_equal(ob['rgb'], policy_rgb):
            raise RuntimeError('Capture changed saved policy RGB')
        # Leave the extra camera at zero direction. Native camera is never moved.
        self.camera.set_world_pose(np.asarray(before['camera_position']), base_q, camera_axes='usd')
        return dict(schema=1, episode_id=self.active['episode_id'], scene=self.active['scene'],
                    step=self.active['step'], terminal=terminal, seed=self.e.run_seed,
                    phase='terminal' if terminal else 'before_action', physics_ticks=before['physics_ticks'],
                    simulation_time_s=before['world_time'], simulation_step=before['world_step'],
                    robot_pose=robot, native_camera_pose=native, alignment_to_robot_deg=align,
                    environment_offset=plain(task.env_offset), calibration=calibration, views_360=views,
                    views_180=front_paths, frame_directory=str(folder),
                    front_image='terminal_front.png' if terminal else 'policy_front.png',
                    observation_position=plain(ob.get('globalgps')), observation_rotation=plain(ob.get('globalrotation')),
                    frozen_state_verified=True, physics_ticks_during_capture=0,
                    auxiliary_visibility=visibility_proof,
                    physical_state_before=before, physical_state_after=after, captured_at=time.time())

    def commit(self, record, action):
        record['action'] = plain(action)
        folder = Path(record['frame_directory'])
        write(folder/'metadata.json', record)
        with (Path(self.active['directory'])/'steps.jsonl').open('a') as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + '\n')
        write(self.root/'progress.json', dict(phase='recording', episode_id=self.active['episode_id'],
              step=record['step'], terminal=record['terminal'], pid=os.getpid(), updated_at=time.time(),
              last_metadata=str(folder/'metadata.json')))
        print('MULTIVIEW_CAPTURE ' + json.dumps(dict(episode_id=record['episode_id'], step=record['step'],
              terminal=record['terminal'], views=8, physics_ticks=record['physics_ticks'])), flush=True)

    def fail(self, error):
        write(self.root.parent/'capture_failure.json', dict(error=repr(error), pid=os.getpid(),
              active=self.active, time=time.time()))

    def before_action(self, observations, actions):
        from vlnverse.evaluator.vln_pe_evaluator import runner_status_code
        if self.e.runner_status[0] != runner_status_code.NORMAL:
            return self.native_action(observations, actions)
        try:
            if self.active is None:
                raise RuntimeError('No native reset before action capture')
            # Render products may share buffers. Copy the complete original policy observation first.
            copied = dict(observations[0])
            for key in ('rgb', 'depth'):
                if copied.get(key) is not None:
                    copied[key] = np.array(copied[key], copy=True)
            record = self.capture(copied)
            result, next_actions = self.native_action([copied], actions)
            self.commit(record, next_actions[0][self.e.robot_name])
            self.active['step'] += 1
            return result, next_actions
        except BaseException as error:
            self.fail(error)
            raise

    def before_terminate(self, observations, infos, terminated):
        from vlnverse.evaluator.vln_pe_evaluator import runner_status_code
        if bool(terminated[0]) and infos[0] is not None and self.e.runner_status[0] != runner_status_code.TERMINATED:
            try:
                self.begin(infos[0])  # includes warmup failures with zero navigation actions
                record = self.capture(observations[0], terminal=True)
                self.commit(record, None)
                metrics = plain(next(iter(observations[0]['metrics'].values()))[0])
                write(Path(self.active['directory'])/'complete.json', dict(self.active, metrics=metrics,
                      actions=self.active['step'], observations=self.active['step']+1,
                      status='capture_complete', completed_at=time.time()))
                self.active = None
            except BaseException as error:
                self.fail(error)
                raise
        return self.native_terminate(observations, infos, terminated)


def install(evaluator):
    root = os.environ.get('VLN_STEP_CAPTURE_ROOT')
    if root and not hasattr(evaluator, '_step_capture'):
        if any(os.environ.get(k) for k in ('VLN_DISTANCE_ARM', 'VLN_ORACLE_MANIFEST', 'VLN_SERIAL_MANIFEST')):
            raise RuntimeError('Multiview baseline must not install correction hooks')
        evaluator._step_capture = StepCapture(evaluator, root)
