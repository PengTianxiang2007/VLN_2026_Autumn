"""Local, offline Transformers endpoint for causal crossing development while vLLM installs."""
import argparse
import base64
import fcntl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.metadata
import io
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from serve_crossing_vlm import gpu_rows, idle, now, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--gpus', type=int, nargs='+', required=True)
    parser.add_argument('--model', type=Path, default=ROOT / '.runtime/models/Qwen3.8-27B-FP8')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for key in list(os.environ):
        if 'proxy' in key.lower():
            os.environ.pop(key)
    cache = ROOT / '.runtime/crossing_transformers27/cache'
    os.environ.update(CUDA_VISIBLE_DEVICES=','.join(map(str, args.gpus)),
        HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1',
        HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1', TOKENIZERS_PARALLELISM='false',
        PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4',
        OPENBLAS_NUM_THREADS='4', HF_HOME=str(cache / 'huggingface'),
        XDG_CACHE_HOME=str(cache), TORCHINDUCTOR_CACHE_DIR=str(cache / 'torchinductor'),
        TRITON_CACHE_DIR=str(cache / 'triton'))
    sys.path.insert(0, str(ROOT / '.runtime/crossing_transformers27/overlay'))
    locks = []
    for gpu in sorted(set(args.gpus)):
        for prefix in ['peng_vlnverse_gpu_', 'vln_2026_gpu_']:
            handle = Path('/tmp', prefix + str(gpu) + '.lock').open('a')
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locks.append(handle)
    for sample in range(2):
        rows = gpu_rows()
        if any(not idle(next(r for r in rows if r['index'] == g)) for g in args.gpus):
            raise RuntimeError('Selected GPUs no longer satisfy idle admission')
        if sample == 0:
            time.sleep(5)
    state = dict(schema=1, phase='loading', backend='transformers', created_at=now(),
        supervisor_pid=os.getpid(), server_pid=os.getpid(), model_path=str(args.model.resolve()),
        served_model='crossing-qwen27b-transformers', gpus=args.gpus,
        quantization_override='official_FP8_weights_dequantized_to_BF16', dtype='bfloat16',
        cpu_offload_gb=0, command=[sys.executable, *sys.argv], gpu_admission=rows, offline=True,
        structured_output='Prompt schema + strict post-parse validation; no constrained decoder.')
    write_json(args.output / 'service.json', state)
    try:
        import torch
        from PIL import Image
        from transformers import AutoModelForImageTextToText, AutoProcessor, FineGrainedFP8Config
        state['environment_versions'] = {p: importlib.metadata.version(p)
            for p in ['torch', 'transformers', 'accelerate', 'huggingface-hub', 'tokenizers']}
        write_json(args.output / 'service.json', state)
        torch.set_num_threads(4)
        processor = AutoProcessor.from_pretrained(str(args.model), local_files_only=True,
                                                 max_pixels=307200)
        model = AutoModelForImageTextToText.from_pretrained(str(args.model),
            local_files_only=True, dtype=torch.bfloat16, device_map='balanced',
            max_memory={i: '38GiB' for i in range(len(args.gpus))},
            quantization_config=FineGrainedFP8Config(dequantize=True),
            attn_implementation='sdpa').eval()
        state['device_map'] = {k: str(v) for k, v in model.hf_device_map.items()}
        if any(v in ['cpu', 'disk'] for v in state['device_map'].values()):
            raise RuntimeError('Unexpected CPU/disk offload; refusing to disguise slow fallback')
        first_device = model.get_input_embeddings().weight.device
        generation_lock = threading.Lock()

        def infer(payload):
            if payload.get('model') != state['served_model']:
                raise ValueError('Unknown local model')
            messages = []
            image_count = 0
            for message in payload['messages']:
                content = message['content']
                if isinstance(content, list):
                    converted = []
                    for item in content:
                        if item['type'] == 'text':
                            converted.append(item)
                        elif item['type'] == 'image_url':
                            url = item['image_url']['url']
                            if not url.startswith('data:image/png;base64,'):
                                raise ValueError('Only in-memory local PNG images are accepted')
                            im = Image.open(io.BytesIO(base64.b64decode(url.split(',', 1)[1]))).convert('RGB')
                            if im.size != (640, 480):
                                raise ValueError('Unexpected RGB dimensions')
                            image_count += 1
                            converted.append(dict(type='image', image=im))
                        else:
                            raise ValueError('Unsupported input type')
                    content = converted
                messages.append(dict(role=message['role'], content=content))
            if not 1 <= image_count <= 8:
                raise ValueError('Expected one to eight causal images')
            with generation_lock, torch.inference_mode():
                torch.manual_seed(payload['seed'])
                inputs = processor.apply_chat_template(messages, tokenize=True,
                    add_generation_prompt=True, return_dict=True, return_tensors='pt',
                    enable_thinking=payload.get('chat_template_kwargs', {}).get('enable_thinking', False))
                inputs = inputs.to(first_device)
                prompt_tokens = inputs['input_ids'].shape[-1]
                max_tokens = int(payload['max_tokens'])
                if prompt_tokens + max_tokens > 32768:
                    raise ValueError('Context limit exceeded')
                started = time.monotonic()
                output = model.generate(**inputs, max_new_tokens=max_tokens,
                                        do_sample=False, use_cache=True)
                tokens = output[0, prompt_tokens:]
                raw = processor.tokenizer.decode(tokens, skip_special_tokens=False)
                reasoning, separator, final = raw.partition('</think>')
                if not separator:
                    final, reasoning = raw, None
                for token in ['<|im_end|>', '<|endoftext|>']:
                    final = final.replace(token, '')
                eos = model.generation_config.eos_token_id
                eos = eos if isinstance(eos, list) else [eos]
                stopped = len(tokens) < max_tokens or int(tokens[-1]) in eos
                state.update(last_request_at=now(), last_generation_seconds=time.monotonic()-started,
                             last_prompt_tokens=prompt_tokens, last_completion_tokens=len(tokens))
                write_json(args.output / 'service.json', state)
                return dict(model=state['served_model'], choices=[dict(index=0,
                    finish_reason='stop' if stopped else 'length', message=dict(role='assistant',
                    content=final.strip(), reasoning=reasoning))],
                    usage=dict(prompt_tokens=prompt_tokens, completion_tokens=len(tokens),
                               total_tokens=prompt_tokens+len(tokens)))

        class Handler(BaseHTTPRequestHandler):
            def respond(self, status, body):
                encoded = json.dumps(body, ensure_ascii=False).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def do_GET(self):
                if self.path == '/v1/models':
                    self.respond(200, dict(data=[dict(id=state['served_model'])]))
                else:
                    self.respond(404, dict(error='Unknown endpoint'))

            def do_POST(self):
                if self.path != '/v1/chat/completions':
                    self.respond(404, dict(error='Unknown endpoint'))
                    return
                try:
                    count = int(self.headers.get('Content-Length', 0))
                    if not 0 < count < 30 * 1024 * 1024:
                        raise ValueError('Invalid request size')
                    self.respond(200, infer(json.loads(self.rfile.read(count))))
                except Exception as error:
                    import traceback
                    traceback.print_exc()
                    self.respond(500, dict(error=type(error).__name__ + ': ' + str(error)))

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        state.update(phase='ready', ready_at=now(), port=server.server_port,
                     base_url=f'http://127.0.0.1:{server.server_port}/v1')
        write_json(args.output / 'service.json', state)
        print(json.dumps(dict(phase='ready', base_url=state['base_url'])), flush=True)

        def stop(signum, frame):
            state.update(phase='stopped', finished_at=now())
            write_json(args.output / 'service.json', state)
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        server.serve_forever()
    except Exception as error:
        state.update(phase='failed', error=type(error).__name__ + ': ' + str(error), finished_at=now())
        write_json(args.output / 'service.json', state)
        raise


if __name__ == '__main__':
    main()
