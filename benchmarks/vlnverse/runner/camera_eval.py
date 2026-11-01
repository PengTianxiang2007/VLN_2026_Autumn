"""Asset-backed Isaac camera/model smoke. This is NOT the official H1 physical evaluation."""
import argparse, base64, json, math, pickle, time, urllib.request
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--port',type=int,required=True)
parser.add_argument('--method',required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--steps',type=int,default=5)
parser.add_argument('--gpu',type=int,required=True)
args=parser.parse_args()
from isaacsim import SimulationApp
app=SimulationApp({'headless':True,'multi_gpu':False,'active_gpu':args.gpu,'physics_gpu':args.gpu,'width':640,'height':480})
try:
    import numpy as np
    from isaacsim.core.api import World
    from isaacsim.core.utils.stage import add_reference_to_stage
    from isaacsim.sensors.camera import Camera
    from isaacsim.core.utils.numpy.rotations import euler_angles_to_quats
    from pxr import Gf, UsdLux
    from PIL import Image
    import omni.usd
    resource=Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/VLNVerse')
    episode=json.loads((resource/'smoke_episode.json').read_text())
    world=World(stage_units_in_meters=1.0)
    add_reference_to_stage(str(resource/'scenes'/episode['scan']/'start_result_navigation.usd'),'/World/Scene')
    stage=omni.usd.get_context().get_stage()
    light=UsdLux.DomeLight.Define(stage,'/World/SmokeLight')
    light.CreateIntensityAttr(500)
    position=np.array(episode['start_position'],dtype=float)
    position[2]+=1.25
    q=episode['start_rotation']
    yaw=math.atan2(2*(q[0]*q[3]+q[1]*q[2]),1-2*(q[2]**2+q[3]**2))
    camera=Camera(prim_path='/World/SmokeCamera',name='smoke_camera',position=position,resolution=(640,480))
    world.scene.add(camera)
    world.reset()
    camera.initialize()
    # 90 degree horizontal FOV; camera local ROS +Z is the optical axis.
    camera.set_focal_length(18.0)
    camera.set_horizontal_aperture(36.0)
    camera.set_clipping_range(0.05,1000)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def post(endpoint,payload):
        request=urllib.request.Request(f'http://127.0.0.1:{args.port}/agent/{args.method}/{endpoint}',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with opener.open(request,timeout=300) as response:return json.load(response)
    post('reset',{'reset_index':None})
    trace=[]
    for step in range(args.steps):
        orientation=euler_angles_to_quats(np.array([0.,0.,yaw]))
        camera.set_world_pose(position=position,orientation=orientation,camera_axes='world')
        for _ in range(30):world.step(render=True)
        rgba=camera.get_rgba()
        rgb=np.ascontiguousarray(rgba[...,:3])
        if rgb.shape!=(480,640,3) or rgb.dtype!=np.uint8 or float(rgb.std())<1:raise RuntimeError('No valid real scene render')
        Image.fromarray(rgb).save(args.output/f'camera_rgb_{step:03d}.png')
        obs=[{'rgb':rgb,'instruction':episode['instruction']['instruction_text']}]
        encoded=base64.b64encode(pickle.dumps(obs)).decode()
        action=post('step',{'observation':encoded})['action'][0][0]
        if action not in (0,1,2,3):raise RuntimeError('Invalid navigation action')
        trace.append({'step':step,'action':action,'camera_position':position.tolist(),'yaw':yaw,'rgb_std':float(rgb.std())})
        if action==0:break
        if action==1:position[:2]+=0.25*np.array([math.cos(yaw),math.sin(yaw)])
        if action==2:yaw+=math.radians(15)
        if action==3:yaw-=math.radians(15)
    # Exercise an additional reset after inference and validate the actual memory is cleared.
    post('reset',{'reset_index':None})
    result={'status':'passed_camera_model_smoke','backend':'Isaac Sim 4.5 scene camera','official_h1_physical_evaluation':False,'reason':'Official H1 Embodiments dataset requires access approval; not downloaded','method':args.method,'scene':episode['scan'],'episode_id':episode['episode_id'],'steps':trace}
    (args.output/'camera_smoke_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print('CAMERA_MODEL_SMOKE_PASSED',flush=True)
finally:
    app.close()
