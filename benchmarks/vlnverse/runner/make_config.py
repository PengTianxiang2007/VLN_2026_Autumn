import argparse
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--method', choices=['StreamVLN', 'JanusVLN'], required=True)
parser.add_argument('--port', type=int, required=True)
parser.add_argument('--task-name', required=True)
parser.add_argument('--output', type=Path, required=True)
a = parser.parse_args()
model = 'streamvln_rgb' if a.method == 'StreamVLN' else 'janusvln'
checkpoint = 'StreamVLN_R2R_v1_3' if a.method == 'StreamVLN' else 'JanusVLN_Extra'
a.output.write_text(f"""from vlnverse.configs.agent import AgentCfg
from vlnverse.configs.evaluator import EnvCfg, EvalCfg, EvalDatasetCfg, SceneCfg, TaskCfg
resource = '/mnt/nas/gezuhao/shared_dataset/Resource_Peng'
eval_cfg = EvalCfg(
    agent=AgentCfg(server_host='127.0.0.1', server_port={a.port}, model_name='{model}', ckpt_path=resource+'/models/{checkpoint}', model_settings={{}}),
    env=EnvCfg(env_type='vln_pe', env_settings={{'headless': True, 'use_fabric': False}}),
    task=TaskCfg(task_name='{a.task_name}', task_settings={{'env_num':1, 'proc_num':1, 'use_distributed':False, 'max_step':2000, 'warm_up_step':500}}, scene=SceneCfg(scene_type='kujiale', scene_data_dir=resource+'/assets/VLNVerse/scenes'), robot_name='h1', robot_flash=False, flash_collision=False, robot_usd_path=resource+'/assets/VLNVerse/Embodiments/vln-pe/h1/h1_vln_pointcloud.usd', camera_resolution=[640,480], camera_prim_path='torso_link/h1_pano_camera_0'),
    dataset=EvalDatasetCfg(dataset_type='kujiale', dataset_settings={{'base_data_dir':resource+'/assets/VLNVerse/data/smoke/fine', 'split_data_types':['val_unseen'], 'filter_stairs':False}}),
    eval_settings={{'save_to_json':True, 'vis_output':False}},
)
""")
