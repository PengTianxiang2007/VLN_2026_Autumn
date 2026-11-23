"""Render one VLNVerse scene at the measured v006 optical centres."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import traceback


def capture(out, scene):
    import numpy as np
    from PIL import Image
    from isaacsim.core.api import World
    from isaacsim.core.utils.stage import add_reference_to_stage
    from isaacsim.sensors.camera import Camera
    import omni.replicator.core as rep
    import omni.usd
    from pxr import Gf, UsdGeom, UsdLux
    from core.step_multiview import angle_delta, fresh_render, pose_record, turn_world_z, write

    manifest = json.loads((out/'manifest.json').read_bytes())
    jobs = [n for n in manifest['nodes'] if n['scene']==scene]
    world = World(stage_units_in_meters=1.)
    add_reference_to_stage(manifest['scenes'][scene], '/World/Scene')
    stage = omni.usd.get_context().get_stage()
    distant = UsdLux.DistantLight.Define(stage,'/World/distant_light')
    distant.CreateIntensityAttr(1000)
    distant.CreateColorAttr(Gf.Vec3f(1,1,1))
    up = UsdLux.DiskLight.Define(stage,'/World/up_disk_light')
    down = UsdLux.DiskLight.Define(stage,'/World/down_disk_light')
    for light in (up,down):
        light.CreateIntensityAttr(5000)
        light.CreateRadiusAttr(50)
        light.CreateColorAttr(Gf.Vec3f(1,1,1))
    up_xform = UsdGeom.Xformable(up)
    up_xform.AddRotateXYZOp().Set(Gf.Vec3f(180,0,0))
    light_up = up_xform.AddTranslateOp()
    light_down = UsdGeom.Xformable(down).AddTranslateOp()
    camera = Camera(prim_path='/World/NodeCamera',name='v006_pose70',resolution=(640,480),frequency=-1)
    world.scene.add(camera)
    world.reset()
    camera.initialize()
    calib = jobs[0]['calibration']
    for attr,key in [('focalLength','focal_length_usd'),('horizontalAperture','horizontal_aperture_usd'),
                     ('verticalAperture','vertical_aperture_usd')]:
        camera.prim.GetAttribute(attr).Set(calib[key])
    camera.set_clipping_range(.01,1.e7)
    camera.set_lens_aperture(0)
    assert np.allclose(camera.get_intrinsics_matrix(),calib['intrinsic_matrix'])
    previous = None
    completed_before = len(list((out/'points').glob('*/metadata.json')))
    assert UsdGeom.GetStageUpAxis(stage)=='Z'
    for ordinal, job in enumerate(jobs,1):
        node = f"{job['case_id']}_{job['node_id']}_F{job['frame']:04d}"
        dest = out/'points'/node
        dest.mkdir()
        x,y,z = job['start_position']
        light_up.Set(Gf.Vec3d(x,-y,-z-1))
        light_down.Set(Gf.Vec3d(x,y,z+1))
        native = job['camera']
        position = np.array(native['position_world_m'])
        base = np.array(native['quaternion_wxyz'])
        views = []
        assert np.allclose(job['calibration']['intrinsic_matrix'],calib['intrinsic_matrix'])
        for degrees,label in [(70,'left_70'), (0,'front_0'), (-70,'right_70')]:
            q = turn_world_z(base,degrees)
            camera.set_world_pose(position,q,camera_axes='usd')
            if previous is None:
                for _ in range(24):
                    world.render()
            tick = world.current_time_step_index
            rgb, frame = fresh_render(camera, lambda:rep.orchestrator.step(rt_subframes=4,delta_time=0.,pause_timeline=False),previous)
            previous = int(frame['rendering_frame'])
            assert world.current_time_step_index == tick
            assert rgb.shape == (480,640,3) and rgb.dtype == np.uint8 and rgb.max()>0
            p, rotation = camera.get_world_pose(camera_axes='usd')
            pose = pose_record(p,rotation,camera=True)
            assert np.allclose(p,position,atol=1e-5,rtol=0)
            assert min(np.linalg.norm(rotation-q),np.linalg.norm(rotation+q)) < 1e-5
            assert abs(angle_delta(pose['heading_deg'],native['heading_deg']+degrees)) < .01
            path = dest/(label+'.png')
            Image.fromarray(rgb).save(path)
            views.append(dict(offset_deg=degrees, file=path.name, camera=pose, render_frame=previous,
                              sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rgb_std=float(rgb.std())))
        assert len({v['sha256'] for v in views})==3
        record = dict(**job,views=views,original_dataset=manifest['dataset'],relative_to='native_camera_heading',
                      robot_geometry='excluded in auxiliary scene render',physics_steps_during_capture=0)
        write(dest/'metadata.json',record)
        progress = dict(completed_nodes=completed_before+ordinal, expected_nodes=len(manifest['nodes']),
                        new_images=(completed_before+ordinal)*3,scene=scene,last_node=node,pid=os.getpid())
        write(out/'progress.json',progress)
        print('CAPTURED',node,progress['completed_nodes'],flush=True)
    write(out/'scenes'/(scene+'.json'),dict(scene=scene,completed=len(jobs),images=3*len(jobs)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--scene',required=True)
    args = parser.parse_args()
    from isaacsim import SimulationApp
    app = SimulationApp(dict(headless=True,multi_gpu=False,active_gpu=3,physics_gpu=0,width=640,height=480,
                             renderer='RayTracedLighting'))
    try:
        capture(args.output,args.scene)
    except BaseException:
        traceback.print_exc()
        raise
    finally:
        app.close()
