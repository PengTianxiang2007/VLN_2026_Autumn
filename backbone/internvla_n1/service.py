"""Loopback service for the unmodified official InternVLAN1Agent policy."""
import argparse
import base64
import json
import pickle
import signal
import time
import traceback
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

from bootstrap import bootstrap
from checkpoint_compatibility import loading_errors

p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
p.add_argument('--checkpoint', required=True)
p.add_argument('--check-import', action='store_true')
a = p.parse_args()
vendor = bootstrap(a.output)

from vlnverse.agent.base import Agent
from vlnverse.agent import load_agent
from vlnverse.model.basemodel.internvla_n1.internvla_n1 import InternVLAN1ForCausalLM
from vlnverse.configs.agent import AgentCfg
import importlib.util
import numpy as np
spec = importlib.util.spec_from_file_location('n1_official_config', vendor / 'scripts/eval/configs/h1_internvla_n1_cfg_vlnverse_fine_val_unseen.py')
cfg_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cfg_module)
cfg = cfg_module.eval_cfg.agent
cfg.model_settings.update(model_path=a.checkpoint, policy_name='InternVLAN1_Policy', state_encoder=None, vis_debug_path=str(a.output / 'videos'))
load_agent(cfg.model_name)
if not callable(Agent.agents.get(cfg.model_name)):
    raise RuntimeError('Official N1 agent was not registered')
if a.check_import:
    from vlnverse.model import get_policy
    from vlnverse.configs.model.base_encoders import ModelCfg
    get_policy('InternVLAN1_Policy')
    ModelCfg(**cfg.model_settings)
    print('OFFICIAL_N1_IMPORT_OK', flush=True)
    raise SystemExit(0)

a.output.mkdir(parents=True, exist_ok=True)
print('MODEL_STARTUP_BEGIN', flush=True)
original_load = InternVLAN1ForCausalLM.from_pretrained
def checked_load(cls, *args, **kwargs):
    kwargs['output_loading_info'] = True
    model, info = original_load(*args, **kwargs)
    (a.output / 'checkpoint_loading_info.json').write_text(json.dumps(info, indent=2, default=str))
    if any(loading_errors(info).values()):
        raise RuntimeError('Checkpoint/model mismatch; inspect checkpoint_loading_info.json')
    return model
InternVLAN1ForCausalLM.from_pretrained = classmethod(checked_load)
agent = Agent.init(cfg)
# Surface exceptions swallowed by the upstream inference thread. Successful
# inference, prompts, precision and action queues are unchanged.
original_s2 = agent.policy.s2_step
def checked_s2(*args, **kwargs):
    try:
        return original_s2(*args, **kwargs)
    except Exception:
        (a.output / 'inference_error.txt').write_text(traceback.format_exc())
        raise
agent.policy.s2_step = checked_s2
print('MODEL_STARTUP_COMPLETE', flush=True)
reset_number = 0
step_number = 0

def json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value).__name__)

def shutdown(signum, frame):
    if agent.vis_debug:
        agent.fps_writer.close()
        agent.fps_writer2.close()
    raise SystemExit(0)

signal.signal(signal.SIGTERM, shutdown)

class Handler(BaseHTTPRequestHandler):
    def respond(self, value, status=200):
        data = json.dumps(value, default=json_default).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.respond({'ready': True, 'seed': 0})

    def do_POST(self):
        global reset_number, step_number
        try:
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if self.path == '/agent/init':
                self.respond({'status': 'success', 'agent_name': 'internvla_n1'}, 201)
            elif self.path.endswith('/reset'):
                agent.reset(body.get('reset_index'))
                reset_number += 1
                step_number = 0
                self.respond({'status': 'success'})
            elif self.path.endswith('/step'):
                obs = pickle.loads(base64.b64decode(body['observation']))
                started = time.time()
                action = agent.step(obs)
                if (a.output / 'inference_error.txt').exists():
                    raise RuntimeError('Upstream inference failed; refusing to score fallback STOP as navigation.')
                row = {'reset': reset_number, 'step': step_number, 'action': action,
                       'instruction': obs[0]['instruction'], 'seconds': time.time()-started,
                       'llm_output': agent.policy.llm_output, 'seed': 0}
                with (a.output / 'agent_trace.jsonl').open('a') as f:
                    f.write(json.dumps(row, ensure_ascii=False, default=json_default) + '\n')
                step_number += 1
                self.respond({'action': action})
            else:
                self.respond({'error': 'unknown endpoint'}, 404)
        except Exception:
            error = traceback.format_exc()
            (a.output / 'service_error.txt').write_text(error)
            print(error, flush=True)
            self.respond({'error': error}, 500)

server = HTTPServer(('127.0.0.1', 0), Handler)
(a.output / 'ready.json').write_text(json.dumps({'port': server.server_port, 'seed': 0}))
print('AGENT_READY', server.server_port, flush=True)
server.serve_forever()
