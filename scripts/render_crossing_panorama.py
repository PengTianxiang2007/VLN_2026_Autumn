"""Render one registered scene's Crossing panoramas without a navigation agent."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import signal


def write(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--scene', required=True)
    ap.add_argument('--gpu', type=int, required=True)
    a = ap.parse_args()
    out = a.output.resolve()
    manifest = json.loads((out / 'manifest.json').read_text())
    asset = next(s for s in manifest['scenes'] if s['scene'] == a.scene)
    jobs = [p for p in manifest['panoramas'] if p['scene'] == a.scene]
    if not jobs or (out / 'scenes' / (a.scene + '.json')).exists():
        raise ValueError('Missing scene jobs or already completed scene')
    def stop(*_):
        raise KeyboardInterrupt('Capture termination requested')
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    from isaacsim import SimulationApp
    app = SimulationApp(dict(headless=True, multi_gpu=False, active_gpu=a.gpu, physics_gpu=0,
                             width=640, height=480, renderer='RayTracedLighting'))
    try:
        import numpy as np
        from PIL import Image
        from isaacsim.core.api import World
        from isaacsim.core.utils.stage import add_reference_to_stage
        from isaacsim.core.utils.numpy.rotations import euler_angles_to_quats
        from isaacsim.sensors.camera import Camera
        from pxr import Gf, Usd, UsdGeom, UsdLux
        import omni.replicator.core as rep
        import omni.usd
        random.seed(manifest['render_seed'])
        np.random.seed(manifest['render_seed'])
        world = World(stage_units_in_meters=1.0)
        add_reference_to_stage(asset['path'], '/World/Scene')
        stage = omni.usd.get_context().get_stage()
        assert UsdGeom.GetStageUpAxis(stage) == 'Z'
        # Same light types and intensities as VLNEvalTask.create_light().
        distant = UsdLux.DistantLight.Define(stage, '/World/CaptureLights/distant')
        distant.CreateIntensityAttr(1000)
        distant.CreateColorAttr(Gf.Vec3f(1, 1, 1))
        up = UsdLux.DiskLight.Define(stage, '/World/CaptureLights/up')
        down = UsdLux.DiskLight.Define(stage, '/World/CaptureLights/down')
        for light in [up, down]:
            light.CreateIntensityAttr(5000)
            light.CreateRadiusAttr(50)
            light.CreateColorAttr(Gf.Vec3f(1, 1, 1))
        up_xform = UsdGeom.Xformable(up)
        up_xform.AddRotateXYZOp().Set(Gf.Vec3f(180, 0, 0))
        up_position = up_xform.AddTranslateOp()
        down_position = UsdGeom.Xformable(down).AddTranslateOp()
        camera = Camera(prim_path='/World/CaptureCamera', name='crossing_camera',
                        position=np.array(jobs[0]['position']), resolution=(640, 480))
        world.scene.add(camera)
        world.reset()
        camera.initialize()
        config = manifest['camera']
        # SDK length setters use 1/10 USD camera-attribute units.
        camera.set_focal_length(config['focal_length_usd'] / 10)
        camera.set_horizontal_aperture(config['horizontal_aperture_usd'] / 10)
        camera.set_clipping_range(*config['clipping_range_m'])
        camera.set_lens_aperture(0)
        actual_calibration = dict(focal_length_usd=float(camera.prim.GetAttribute('focalLength').Get()),
                                  horizontal_aperture_usd=float(camera.prim.GetAttribute('horizontalAperture').Get()),
                                  vertical_aperture_usd=float(camera.prim.GetAttribute('verticalAperture').Get()),
                                  intrinsic_matrix=camera.get_intrinsics_matrix().tolist())
        for key in ['focal_length_usd', 'horizontal_aperture_usd', 'vertical_aperture_usd']:
            assert abs(actual_calibration[key] - config[key]) < 1e-4
        results = []
        for job in jobs:
            dest = out / 'panoramas' / job['panorama_id']
            dest.mkdir(exist_ok=False)
            position = np.array(job['position'], dtype=float)
            root_z = position[2] - config['local_translation'][2]
            x, y = position[:2]
            up_position.Set(Gf.Vec3d(x, -y, -root_z - 1))
            down_position.Set(Gf.Vec3d(x, y, root_z + 1))
            views = []
            hashes = set()
            for index, yaw in enumerate(job['yaw_degrees']):
                q = euler_angles_to_quats(np.array([0, math.radians(config['pitch_down_deg']), math.radians(yaw)]))
                camera.set_world_pose(position=position, orientation=q, camera_axes='world')
                # Render without physics ticks: no scene motion, no navigation actions.
                for _ in range(60 if index == 0 else 12):
                    world.render()
                rep.orchestrator.step(rt_subframes=8, delta_time=0.0, pause_timeline=False)
                rgb = np.ascontiguousarray(camera.get_rgba()[..., :3])
                if rgb.shape != (480, 640, 3) or rgb.dtype != np.uint8 or float(rgb.std()) < 2:
                    raise RuntimeError(f'Invalid/blank render {job["panorama_id"]} {yaw}: {rgb.shape}')
                pose, quat = camera.get_world_pose(camera_axes='world')
                matrix = UsdGeom.Xformable(camera.prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
                direction = matrix.TransformDir(Gf.Vec3d(0, 0, -1))
                actual_yaw = math.degrees(math.atan2(direction[1], direction[0])) % 360
                actual_pitch = math.degrees(math.asin(-direction[2]))
                assert np.allclose(pose, position, atol=1e-5)
                assert abs((actual_yaw - yaw + 180) % 360 - 180) < 1e-3
                assert abs(actual_pitch - config['pitch_down_deg']) < 1e-3
                path = dest / f'view_{index:02d}_yaw_{yaw:03d}.png'
                Image.fromarray(rgb).save(path)
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if digest in hashes:
                    raise RuntimeError('Repeated RGB at distinct yaw: stale camera frame')
                hashes.add(digest)
                frame = camera.get_current_frame()
                view = dict(view_id=f'V{index}', yaw_deg=yaw, actual_yaw_deg=actual_yaw, pitch_down_deg=actual_pitch,
                            position=pose.tolist(), quaternion_wxyz=quat.tolist(), forward_world=list(direction),
                            path=str(path.relative_to(out)), sha256=digest, width=640, height=480,
                            rgb_mean=float(rgb.mean()), rgb_std=float(rgb.std()),
                            dark_fraction=float((rgb.max(axis=2) < 5).mean()),
                            white_fraction=float((rgb.min(axis=2) > 250).mean()),
                            rendering_frame=int(frame['rendering_frame']), rendering_time=float(frame['rendering_time']))
                views.append(view)
                print(json.dumps(dict(event='image_saved', panorama=job['panorama_id'], yaw=yaw, sha256=digest)), flush=True)
            metadata = dict(schema=1, panorama_id=job['panorama_id'], scene=a.scene, crossing_id=job['crossing_id'],
                            captured_at=datetime.now(timezone.utc).isoformat(), gpu=a.gpu, position=job['position'],
                            camera=actual_calibration, views=views, model_calls=0, navigation_actions=0,
                            physics_steps_during_capture=0, historical_camera_pose_recovered=False)
            write(dest / 'metadata.json', metadata)
            results.append(dict(panorama_id=job['panorama_id'], images=len(views), metadata=str((dest / 'metadata.json').relative_to(out))))
        write(out / 'scenes' / (a.scene + '.json'), dict(scene=a.scene, results=results, status='complete', model_calls=0))
        print('SCENE_CAPTURE_COMPLETE ' + a.scene, flush=True)
    finally:
        app.close()


if __name__ == '__main__':
    main()
