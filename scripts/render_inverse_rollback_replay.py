"""Render frozen H1 rollback poses in the original USD scenes, without navigation."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import traceback


def read(path):
    return json.loads(path.read_bytes())


def camera_at(root, calibration):
    import numpy as np
    from core.step_multiview import quat_product, rotate
    position, q = np.array(root['position']), np.array(root['orientation'])
    q /= np.linalg.norm(q)
    return position + rotate(q, calibration[0]), quat_product(q, calibration[1])


def render(run, export):
    import numpy as np
    import omni.replicator.core as rep
    import omni.usd
    from isaacsim.core.api import World
    from isaacsim.core.utils.stage import add_reference_to_stage
    from isaacsim.sensors.camera import Camera
    from PIL import Image
    from pxr import Gf, UsdGeom, UsdLux
    from core.step_multiview import fresh_render, quat_product, rotate, write

    source = Path('outputs/multiview_capture/v006_pose70/run_20261121_01/manifest.json')
    source = read(source)
    nodes = {n['case_id']: n for n in source['nodes']}
    jobs = read(run/'manifest.json')['cases']
    scenes = list(dict.fromkeys(c['scene'] for c in jobs))
    media = export/'rendered'
    media.mkdir(exist_ok=True)
    world = World(stage_units_in_meters=1.)
    stage = omni.usd.get_context().get_stage()
    distant = UsdLux.DistantLight.Define(stage, '/World/distant_light')
    distant.CreateIntensityAttr(1000)
    lights = []
    for label in ('up', 'down'):
        light = UsdLux.DiskLight.Define(stage, '/World/' + label)
        light.CreateIntensityAttr(5000)
        light.CreateRadiusAttr(50)
        xform = UsdGeom.Xformable(light)
        if label == 'up':
            xform.AddRotateXYZOp().Set(Gf.Vec3f(180, 0, 0))
        lights.append(xform.AddTranslateOp())
    cam = Camera('/World/RollbackCamera', name='rollback_camera', resolution=(640,480), frequency=-1)
    world.scene.add(cam)
    world.reset()
    cam.initialize()
    cal = nodes[jobs[0]['case_id']]['calibration']
    for attr, key in [('focalLength','focal_length_usd'), ('horizontalAperture','horizontal_aperture_usd'),
                      ('verticalAperture','vertical_aperture_usd')]:
        cam.prim.GetAttribute(attr).Set(cal[key])
    cam.set_clipping_range(0.01, 1e7)
    cam.set_lens_aperture(0)
    assert np.allclose(cam.get_intrinsics_matrix(), cal['intrinsic_matrix'])
    last = None
    for scene in scenes:
        cases = [c for c in jobs if c['scene'] == scene]
        if all((media/c['case_id']/'frames.json').is_file() for c in cases):
            continue
        print('Loading', scene, flush=True)
        if stage.GetPrimAtPath('/World/Apartment'):
            stage.RemovePrim('/World/Apartment')
            world.render()
        add_reference_to_stage(source['scenes'][scene], '/World/Apartment')
        for case in cases:
            cid = case['case_id']
            directory = media/cid
            if (directory/'frames.json').is_file():
                continue
            directory.mkdir(exist_ok=True)
            x,y,z = nodes[cid]['start_position']
            lights[0].Set(Gf.Vec3d(x, -y, -z-1))
            lights[1].Set(Gf.Vec3d(x, y, z+1))
            start = case['historical_start']
            inv_q = np.array(start['rotation']) * [1,-1,-1,-1]
            inv_q /= np.linalg.norm(inv_q)
            extrinsic = (rotate(inv_q, np.array(start['camera_position']) - start['position']),
                         quat_product(inv_q, start['camera_rotation']))
            src = run/'cases'/cid
            trace = [json.loads(l) for l in (src/'inverse_trace.jsonl').read_text().splitlines()]
            poses = [(f'i{p["index"]:03}', p) for p in trace]
            poses.extend((a, read(src/(a+'.json'))) for a in ('inverse', 'reset'))
            records = []
            for i, (name, root) in enumerate(poses):
                position, q = camera_at(root, extrinsic)
                q /= np.linalg.norm(q)
                cam.set_world_pose(position, q, camera_axes='usd')
                if i == 0:
                    for _ in range(12):
                        world.render()
                tick = world.current_time_step_index
                rgb, frame = fresh_render(cam, lambda: rep.orchestrator.step(rt_subframes=4, delta_time=0.,
                                          pause_timeline=False), last)
                last = int(frame['rendering_frame'])
                actual, rot = cam.get_world_pose(camera_axes='usd')
                assert np.allclose(actual, position, rtol=0, atol=1e-4) and abs(np.dot(q, rot)) > .99999
                assert world.current_time_step_index == tick and rgb.shape == (480,640,3)
                if i == 0 and rgb.max() == 0:
                    raise RuntimeError(f'Empty first render in {cid}')
                Image.fromarray(rgb).save(directory/(name+'.webp'), quality=80, method=2)
                records.append(dict(file=name+'.webp', position=position.tolist(), quaternion_wxyz=q.tolist(),
                                    render_frame=last))
            write(directory/'frames.json', dict(scene=scene, case_id=cid, source='B_root_to_camera_extrinsic',
                  local_position=extrinsic[0].tolist(), local_quaternion_wxyz=extrinsic[1].tolist(),
                  physics_ticks_during_capture=0, frames=records))
            print('Rendered',cid,len(records),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    parser.add_argument('export',type=Path)
    parser.add_argument('--gpu',required=True,type=int)
    args = parser.parse_args()
    # Leave the application only its own Kit flags.
    sys.argv[1:] = [f'--/renderer/activeGpu={args.gpu}', '--/renderer/multiGpu/enabled=False']
    from isaacsim import SimulationApp
    app = SimulationApp(dict(headless=True,multi_gpu=False,active_gpu=args.gpu,physics_gpu=0,
                             width=640,height=480,renderer='RayTracedLighting'))
    result = 0
    try:
        render(args.run, args.export)
    except BaseException:
        traceback.print_exc()
        result = 1
    finally:
        app.close()
    sys.exit(result)
