"""Loopback-only stdlib HTTP implementation of the official Agent wire protocol."""
import argparse, base64, importlib.util, json, pickle, time, traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import numpy as np
import torch
from PIL import Image

parser = argparse.ArgumentParser()
parser.add_argument('--method', choices=['StreamVLN', 'JanusVLN'], required=True)
parser.add_argument('--checkpoint', required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--port', type=int, default=0)
parser.add_argument('--smoke-steps', type=int, default=8, help='0 disables smoke action truncation')
parser.add_argument('--compact-trace', action='store_true')
parser.add_argument('--save-rgb', type=int, default=-1, help='-1 all RGB; 0 none; N first N frames per episode')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
adapter = Path(__file__).resolve().parents[3] / "backbone" / args.method.lower() / "vlnverse/adapter.py"
spec = importlib.util.spec_from_file_location('peng_navigation_adapter', adapter)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
agent = module.NavigationAgent(args.checkpoint)
steps = 0
resets = 0
trace = []

class Handler(BaseHTTPRequestHandler):
    def respond(self, payload, status=200):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_GET(self):
        self.respond({'ready': True, 'method': args.method, 'model_calls': agent.calls})
    def do_POST(self):
        global steps, resets
        try:
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if self.path == '/agent/init':
                self.respond({'status': 'success', 'agent_name': body['agent_config']['model_name']}, 201)
            elif self.path.endswith('/reset'):
                agent.reset(); steps = 0; resets += 1
                self.respond({'status': 'success'})
            elif self.path.endswith('/step'):
                observations = pickle.loads(base64.b64decode(body['observation']))
                if len(observations) != 1: raise ValueError('Smoke supports exactly one environment')
                observation = observations[0]
                rgb = np.asarray(observation['rgb'])
                instruction = observation['instruction']
                if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3: raise ValueError('Invalid RGB')
                # Valid dark/uniform observations must reach the original model.
                # Keep RGB statistics in the trace, without rejecting by content.
                if not isinstance(instruction, str) or not instruction: raise ValueError('Missing instruction')
                if args.save_rgb < 0 or steps < args.save_rgb:
                    image_dir = args.output if not args.compact_trace else args.output / f'episode_reset_{resets:04d}'
                    image_dir.mkdir(exist_ok=True)
                    Image.fromarray(rgb).save(image_dir / f'rgb_{steps:03d}.png')
                started = time.time()
                forced_stop = args.smoke_steps > 0 and steps >= args.smoke_steps
                if forced_stop:
                    action, detail = 0, {'generated': False, 'reason': 'smoke_step_limit'}
                else:
                    # Only RGB and language enter the model; no goal/GT/pose/depth.
                    action, detail = agent.step(rgb, instruction)
                if action not in (0,1,2,3): raise ValueError(f'Invalid action {action}')
                record = {'episode_reset': resets, 'step': steps, 'action': action, 'forced_smoke_stop': forced_stop, 'elapsed_seconds': time.time()-started, 'rgb_shape': list(rgb.shape), 'rgb_std': float(rgb.std()), **detail}
                record.update(cuda_allocated_mib=round(torch.cuda.memory_allocated()/1024**2,1),cuda_reserved_mib=round(torch.cuda.memory_reserved()/1024**2,1),cuda_peak_allocated_mib=round(torch.cuda.max_memory_allocated()/1024**2,1))
                trace.append(record)
                if args.compact_trace:
                    with (args.output / 'agent_trace.jsonl').open('a') as f: f.write(json.dumps(record, ensure_ascii=False)+'\n')
                    if len(trace) > 128: del trace[:-128]
                (args.output / 'agent_trace.json').write_text(json.dumps({'method': args.method, 'checkpoint': args.checkpoint, 'model_calls': agent.calls, 'resets': resets, 'steps': trace}, ensure_ascii=False, indent=2))
                print(json.dumps(record, ensure_ascii=False), flush=True)
                steps += 1
                self.respond({'action': [[action]]})
            else: self.respond({'error': 'unknown endpoint'}, 404)
        except Exception:
            error = traceback.format_exc()
            print(error, flush=True)
            self.respond({'error': error}, 500)

server = HTTPServer(('127.0.0.1', args.port), Handler)
(args.output / 'ready.json').write_text(json.dumps({'port': server.server_port, 'method': args.method}))
print(f'AGENT_READY port={server.server_port}', flush=True)
server.serve_forever()
