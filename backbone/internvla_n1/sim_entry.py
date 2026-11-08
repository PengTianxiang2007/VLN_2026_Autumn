import os
import runpy
import json
import sys
from pathlib import Path
from bootstrap import bootstrap

vendor = bootstrap(os.environ['N1_RUN_ROOT'])
if os.environ.get('N1_CONFIG_CHECK') == '1':
    from vlnverse.configs.evaluator.default_config import get_config
    config = get_config(runpy.run_path(sys.argv[2])['eval_cfg'])
    assert config.task.robot_flash is True
    assert config.task.task_settings['max_step'] == 400
    assert config.task.task_settings['warm_up_step'] == 500
    assert config.dataset.dataset_settings['filter_stairs'] is False
    assert config.agent.model_settings['policy_name'] == 'InternVLAN1_Policy'
    Path(os.environ['N1_RUN_ROOT'], 'resolved_config.json').write_text(
        json.dumps(config.model_dump(), indent=2, default=lambda value: value.tolist()))
    print('SIMULATION_CONFIG_CHECK_OK', flush=True)
else:
    runpy.run_path(str(vendor / 'scripts/eval/eval.py'), run_name='__main__')
