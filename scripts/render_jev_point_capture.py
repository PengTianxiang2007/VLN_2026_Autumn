"""One Isaac application, scene reloads, fresh 180/360 RGB at frozen JEV points."""
import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import time
from core.jev_capture import align_reference, camera_position


def write(path,data):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temp.replace(path)


def render_scene(out,manifest,asset):
    import numpy as np
    from PIL import Image
    from isaacsim.core.api import World
    from isaacsim.core.utils.stage import add_reference_to_stage
    from isaacsim.core.utils.numpy.rotations import euler_angles_to_quats
    from isaacsim.sensors.camera import Camera
    from pxr import Gf,Usd,UsdGeom,UsdLux
    import omni.usd
    import omni.replicator.core as rep
    jobs=[p for p in manifest['points'] if p['scene']==asset['scene']]
    world=World(stage_units_in_meters=1.)
    add_reference_to_stage(asset['path'],'/World/Scene')
    stage=omni.usd.get_context().get_stage();assert UsdGeom.GetStageUpAxis(stage)=='Z'
    distant=UsdLux.DistantLight.Define(stage,'/World/CaptureLights/distant');distant.CreateIntensityAttr(1000);distant.CreateColorAttr(Gf.Vec3f(1,1,1))
    up=UsdLux.DiskLight.Define(stage,'/World/CaptureLights/up');down=UsdLux.DiskLight.Define(stage,'/World/CaptureLights/down')
    for light in [up,down]:
        light.CreateIntensityAttr(5000);light.CreateRadiusAttr(50);light.CreateColorAttr(Gf.Vec3f(1,1,1))
    ux=UsdGeom.Xformable(up);ux.AddRotateXYZOp().Set(Gf.Vec3f(180,0,0));up_pos=ux.AddTranslateOp();down_pos=UsdGeom.Xformable(down).AddTranslateOp()
    camera=Camera(prim_path='/World/CaptureCamera',name='jev_camera',position=np.array(jobs[0]['position']),resolution=(640,480))
    world.scene.add(camera);world.reset();camera.initialize();config=manifest['camera']
    camera.set_focal_length(config['focal_length_usd']/10);camera.set_horizontal_aperture(config['horizontal_aperture_usd']/10)
    camera.set_clipping_range(*config['clipping_range_m']);camera.set_lens_aperture(0)
    calibration=dict(intrinsic_matrix=camera.get_intrinsics_matrix().tolist())
    for key,attr in [('focal_length_usd','focalLength'),('horizontal_aperture_usd','horizontalAperture'),('vertical_aperture_usd','verticalAperture')]:
        calibration[key]=float(camera.prim.GetAttribute(attr).Get());assert abs(calibration[key]-config[key])<1e-4
    for job in jobs:
        dest=out/'points'/job['point_id']
        if (dest/'complete.json').exists():continue
        dest.mkdir(exist_ok=True)
        attempt=dest/('attempt_'+str(time.time_ns()));attempt.mkdir();views=[];hashes=set();last_render_frame=None
        effective_yaw=job['heading']['base_yaw_deg'];effective_position=job['position'];alignment=None
        for capture_pass in ['probe','final']:
            capture_dir=attempt/capture_pass;capture_dir.mkdir();views=[];hashes=set();last_render_frame=None
            position=np.array(effective_position);x,y,z=job['root_position']
            up_pos.Set(Gf.Vec3d(x,-y,-z-1));down_pos.Set(Gf.Vec3d(x,y,z+1))
            for index,offset in enumerate(manifest['view_offsets_deg']):
                yaw=(effective_yaw+offset)%360
                q=euler_angles_to_quats(np.array([0,math.radians(config['pitch_down_deg']),math.radians(yaw)]))
                camera.set_world_pose(position=position,orientation=q,camera_axes='world')
                for _ in range(60 if index==0 else 12):world.render()
                rep.orchestrator.step(rt_subframes=8,delta_time=0.,pause_timeline=False)
                rgb=np.ascontiguousarray(camera.get_rgba()[...,:3]);frame=camera.get_current_frame()
                if rgb.shape!=(480,640,3) or rgb.dtype!=np.uint8 or float(rgb.std())<2:raise RuntimeError('Invalid render: '+job['point_id'])
                render_frame=int(frame['rendering_frame'])
                if last_render_frame is not None and render_frame<=last_render_frame:raise RuntimeError('Stale render timestamp')
                last_render_frame=render_frame
                pose,quat=camera.get_world_pose(camera_axes='world')
                matrix=UsdGeom.Xformable(camera.prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default());direction=matrix.TransformDir(Gf.Vec3d(0,0,-1))
                actual_yaw=math.degrees(math.atan2(direction[1],direction[0]))%360;pitch=math.degrees(math.asin(-direction[2]))
                assert np.allclose(pose,position,atol=1e-5)
                assert abs((actual_yaw-yaw+180)%360-180)<1e-3 and abs(pitch-config['pitch_down_deg'])<1e-3
                path=capture_dir/f'view_{index:02d}.png';Image.fromarray(rgb).save(path);digest=hashlib.sha256(path.read_bytes()).hexdigest()
                if digest in hashes:raise RuntimeError('Identical RGB at different directions')
                hashes.add(digest)
                views.append(dict(id=index,relative_yaw_deg=offset,world_yaw_deg=yaw,actual_yaw_deg=actual_yaw,
                    position=pose.tolist(),quaternion_wxyz=quat.tolist(),forward_world=list(direction),pitch_down_deg=pitch,
                    path=str(path.relative_to(out)),sha256=digest,width=640,height=480,rendering_frame=render_frame,
                    rgb_std=float(rgb.std()),dark_fraction=float((rgb.max(axis=2)<5).mean())))
            if capture_pass=='probe':
                alignment=align_reference(job['source_rgb'],[dict(v,path=str(out/v['path'])) for v in views])
                write(attempt/'alignment.json',dict(alignment=alignment,probe_views=views,prior_heading=job['heading']))
                if alignment['accepted']:
                    effective_yaw=alignment['base_yaw_deg']
                    effective_position=camera_position(job['root_position'],effective_yaw,config['local_translation'])
        sets={}
        for name,indices in manifest['view_sets'].items():
            folder=attempt/name;folder.mkdir();selected=[]
            for order,index in enumerate(indices):
                v=dict(views[index]);target=folder/f'{order:02d}_relative_{v["relative_yaw_deg"]:03d}.png'
                os.link(out/v['path'],target);v['path']=str(target.relative_to(out));selected.append(v)
            metadata=dict(point=job,view_set=name,views=selected,camera=calibration,
                          effective_base_yaw_deg=effective_yaw,effective_camera_position=effective_position,alignment=alignment,
                          base_heading_is_estimated=True,physical_state_recovered=False,
                          coverage='Forward +/-90 degrees' if name=='180' else 'Full circle',
                          format='overlapping_perspective_views',model_calls=0,physics_steps_during_capture=0)
            write(folder/'metadata.json',metadata);sets[name]=str((folder/'metadata.json').relative_to(out))
        write(dest/'complete.json',dict(point_id=job['point_id'],scene=asset['scene'],view_sets=sets,views=views,alignment=alignment,effective_base_yaw_deg=effective_yaw,captured_at=time.time(),attempt=str(attempt)))
        completed=len(list((out/'points').glob('*/complete.json')))
        write(out/'capture_progress.json',dict(phase='rendering',pid=os.getpid(),completed_points=completed,expected_points=manifest['unique_points'],current_point=job['point_id'],scene=asset['scene'],updated_at=time.time()))
        print('POINT_COMPLETE '+job['point_id']+' '+str(completed),flush=True)
    write(out/'scenes'/(asset['scene']+'.json'),dict(status='complete',points=[j['point_id'] for j in jobs],pid=os.getpid()))
    return world,camera


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--gpu',type=int,required=True);a=p.parse_args()
    out=a.output.resolve();manifest=json.loads((out/'manifest.json').read_text())
    def stop(*_):raise KeyboardInterrupt('Capture stopped; retained model untouched')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    from isaacsim import SimulationApp
    app=SimulationApp(dict(headless=True,multi_gpu=False,active_gpu=a.gpu,physics_gpu=0,width=640,height=480,renderer='RayTracedLighting'))
    try:
        import numpy as np
        import random
        from isaacsim.core.api import World
        import omni.usd
        random.seed(manifest['render_seed']);np.random.seed(manifest['render_seed'])
        for asset in manifest['scenes']:
            if (out/'scenes'/(asset['scene']+'.json')).exists():continue
            world,camera=render_scene(out,manifest,asset)
            if asset!=manifest['scenes'][-1]:
                world.stop();world.clear();World.clear_instance();del camera,world;gc.collect()
                omni.usd.get_context().new_stage()
        assert len(list((out/'points').glob('*/complete.json')))==manifest['unique_points']
        write(out/'simulator_retained.json',dict(pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().split()[21],completed_points=manifest['unique_points'],time=time.time()))
        while not (out/'simulator_retained.release').exists():time.sleep(1)
    finally:app.close()


if __name__=='__main__':main()
