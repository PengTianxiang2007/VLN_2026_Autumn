"""Connect live v006 decisions to the native StreamVLN takeover and handoff."""
import json
import numpy as np
from PIL import Image

from core.serial_runtime import SerialHook
from core.serial_pipeline import save, sha
from core.serial_v006 import NODE_VIEWS, V006API, V006Decisions
from core.step_multiview import (NativeViewCamera, assert_unchanged, fresh_render, pose_record,
                                 state_snapshot, temporary_visibility, turn_world_z)


class V006Hook(SerialHook):
    api_type = V006API
    decisions_type = V006Decisions
    correction_source = 'branch_instruction_v001'
    require_original_motion = True

    def __init__(self, evaluator):
        super().__init__(evaluator)
        self.view_camera = NativeViewCamera()
        # This run owns the simulator. The existing Qwen service belongs to its supervisor.
        evaluator.env.close = self.native_close

    def camera_metadata(self):
        pos, quat = self.task().robot.sensors['pano_camera_0'].get_world_pose()
        return {'native_camera': pose_record(pos, quat, camera=True)}

    def render_views(self, checkpoint):
        directory = self.folder / 'checkpoint_views' / f"{checkpoint['sequence']:06d}"
        metadata = directory / 'views.json'
        if metadata.is_file():
            cached = json.loads(metadata.read_text())
            if cached['leg'] != self.leg or cached['source']['sequence'] != checkpoint['sequence']:
                raise ValueError('Checkpoint view identity changed')
            return cached['views']
        import omni.replicator.core as rep
        import omni.usd
        from pxr import UsdGeom

        task = self.task()
        world = self.e.env.env.runner._world
        before = state_snapshot(task, world)
        source = checkpoint['native_camera']
        position = np.asarray(source['position_world_m'])
        base = np.asarray(source['quaternion_wxyz'])
        directory.mkdir(parents=True)
        calibration = self.view_camera.camera_setup(task)
        camera = self.view_camera.camera
        robot = omni.usd.get_context().get_stage().GetPrimAtPath(task.robot.config.prim_path)
        visibility = UsdGeom.Imageable(robot).GetVisibilityAttr()

        def render():
            rep.orchestrator.step(rt_subframes=4, delta_time=0., pause_timeline=False)

        views = []
        try:
            with temporary_visibility(visibility):
                for image_id, degrees, label in NODE_VIEWS:
                    quat = turn_world_z(base, degrees)
                    camera.set_world_pose(position, quat, camera_axes='usd')
                    rgb, data = fresh_render(camera, render, self.view_camera.last_render)
                    self.view_camera.last_render = int(data['rendering_frame'])
                    p, q = camera.get_world_pose(camera_axes='usd')
                    if (not np.allclose(p, position, atol=1e-5, rtol=0)
                            or min(np.linalg.norm(q-quat), np.linalg.norm(q+quat)) > 1e-5
                            or rgb.shape != (480, 640, 3) or not rgb.any()):
                        raise ValueError('Invalid checkpoint camera pose or image')
                    path = directory / (image_id + '.png')
                    Image.fromarray(rgb).save(path)
                    views.append(dict(index=checkpoint['index'], image_id=image_id, view_label=label,
                                      path=str(path), sha256=sha(path), camera=pose_record(p, q, camera=True)))
        finally:
            render()  # Refresh the original sensors after restoring robot visibility.
            assert_unchanged(before, state_snapshot(task, world))
        save(directory / 'views.json', dict(leg=self.leg, source=checkpoint, views=views,
                                            calibration=calibration, physics_steps_during_capture=0))
        return views

    def select_route(self, pending):
        return self.api.recovery(pending['target'], self.engine.frames, self.instruction,
                                 pending['progress'], self.render_views)

    def observe_main(self, frame):
        self.pending = self.engine.observe(frame)

    def review_main_stop(self):
        frame = self.engine.frames[-1]['index']
        self.event('stop_requested', frame=frame)
        alarm = self.engine.review_endpoint(stop_requested=True)
        self.event('stop_review', frame=frame, accepted=alarm is None,
                   target=alarm['target']['id'] if alarm else None)
        return alarm

    def recover(self, ob):
        pending = self.pending
        target = pending['target']
        if target is None:
            raise RuntimeError('Deviation has no trusted checkpoint')
        source = self.engine.frames[target['index']]
        directory = self.folder / f'recovery_{self.recoveries + 1:03d}'
        directory.mkdir()
        decision = dict(deviation=pending, checkpoint=source)
        restored, ended = self.rollback(ob, target, source, directory, 'interrupt_and_save')
        if ended:
            save(directory/'decision.json', dict(decision, selection={'status': 'terminal_during_restore'}))
            return restored, True

        # Select from observations already available at the alarm. No original
        # action may run between detecting the deviation and restoring the pose.
        selection = self.select_route(pending)
        save(directory/'decision.json', dict(decision, selection=selection))
        if selection['status'] == 'selected':
            self.event('route_selected', selection=selection)
            return self.start_correction(restored, pending, selection, directory), False

        self.event('route_unresolved', selection=selection)
        self.restore_main('resume_at_checkpoint_without_local_instruction')
        self.new_leg(pending['progress'])
        self.after_handoff(restored)
        return restored, False

    def after_handoff(self, ob):
        self.observe_main(self.frame(ob))

    def correction_instruction(self, selection, fresh):
        return selection['recovery_instruction_en']

    def stop_at_scored_cycle(self):
        result = json.loads((self.folder / 'result.json').read_text())
        if result['full_chain_observed']:
            save(self.output / 'scored_cycle.json', dict(episode_id=result['episode_id']))
            return True
        return False

    def finish_before_reset(self, observations, infos, terminated):
        if self.active and terminated[0]:
            if self.pending or self.local or self.terminal is not None:
                self.event('terminal_no_takeover', pending=bool(self.pending), local=self.local)
            else:
                try:
                    import omni.replicator.core as rep
                    rep.orchestrator.step(rt_subframes=4, delta_time=0., pause_timeline=False)
                    rgb = self.task().robot.sensors['pano_camera_0']._camera.get_rgba()[..., :3].copy()
                    frame = self.frame(dict(observations[0], rgb=rgb))
                    if not self.engine.frames or self.engine.frames[-1].get('action_after') != 'STOP':
                        alarm = self.engine.terminal(frame)
                        self.event('terminal_review', frame=frame['index'], alarm=alarm, takeover=False)
                except Exception as exc:
                    # A post-terminal diagnostic cannot invalidate the completed physical task.
                    self.event('terminal_review_error', error=str(exc))
        return super().finish_before_reset(observations, infos, terminated)
