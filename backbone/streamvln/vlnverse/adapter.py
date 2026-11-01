"""Adapter around the unchanged local StreamVLN RGB-only evaluator."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import torch

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / 'streamvln'), str(REPO)]
from streamvln.streamvln_agent import VLNEvaluator
from model.stream_video_vln import StreamVLNForCausalLM
import transformers

class NavigationAgent:
    def __init__(self, checkpoint):
        self.checkpoint = checkpoint
        torch.manual_seed(42)
        tokenizer = transformers.AutoTokenizer.from_pretrained(checkpoint, model_max_length=4096, padding_side='right', local_files_only=True)
        config = transformers.AutoConfig.from_pretrained(checkpoint, local_files_only=True)
        model = StreamVLNForCausalLM.from_pretrained(checkpoint, config=config, attn_implementation='flash_attention_2', torch_dtype=torch.bfloat16, low_cpu_mem_usage=False, local_files_only=True)
        model.model.num_history = 8
        model.reset(1)
        model.requires_grad_(False)
        model.to('cuda:0').eval()
        # Same unused intrinsic placeholder as the local RGB-only entry point.
        intrinsic = np.array([[192.,0.,191.42857143,0.],[0.,192.,191.42857143,0.],[0.,0.,1.,0.],[0.,0.,0.,1.]])
        self.evaluator = VLNEvaluator({'camera_intrinsic': intrinsic, 'rgb_height': 1.25}, model=model, tokenizer=tokenizer, args=SimpleNamespace(num_frames=32, num_future_steps=4, num_history=8))
        self.pending = []
        self.calls = 0

    def reset(self):
        self.evaluator.reset_memory()
        self.pending = []
        assert self.evaluator.step_id == 0 and self.evaluator.past_key_values is None

    def step(self, rgb, instruction):
        # Match the local evaluation driver: consume the complete sequence.
        run_model = not self.pending
        with torch.inference_mode():
            actions, seconds, output = self.evaluator.step(0, rgb, instruction, run_model=run_model)
        if run_model:
            self.calls += 1
            self.pending = list(actions)
        action = self.pending.pop(0) if self.pending else 0
        self.evaluator.step_id += 1
        # The RGB entry handles this boundary on observation-only calls.
        # The canonical evaluation driver resets every 32 actions, including
        # when generation itself happens on the last action of the window.
        if self.evaluator.step_id % self.evaluator.num_frames == 0 and self.evaluator.time_ids:
            self.evaluator.model.reset_for_env(0)
            self.evaluator.output_ids = None
            self.evaluator.past_key_values = None
            self.evaluator.time_ids = []
        return int(action), {'generated': run_model, 'generation_seconds': seconds, 'output': output, 'source': 'streamvln/streamvln_agent.py', 'input_modalities': ['rgb']}
