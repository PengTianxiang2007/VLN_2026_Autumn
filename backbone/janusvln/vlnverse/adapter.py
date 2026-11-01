"""Adapter using the unchanged local JanusVLN inference and history sampling."""
import sys
from pathlib import Path
import numpy as np
import torch
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / 'src'), str(REPO)]
from evaluation import JanusVLN_Inference, set_seed

class NavigationAgent:
    def __init__(self, checkpoint):
        self.checkpoint = checkpoint
        set_seed(42)
        self.inference = JanusVLN_Inference(checkpoint, device='cuda:0')
        self.calls = 0
        self.reset()

    def reset(self):
        self.images = []
        self.step_id = 0
        self.inference.model.past_key_values_vggt = None
        assert self.inference.model.past_key_values_vggt is None

    def step(self, rgb, instruction):
        self.images.append(Image.fromarray(rgb).convert('RGB'))
        history_len = len(self.images) - 1
        if history_len <= 8:
            images = self.images[:history_len] + [self.images[-1]]
        else:
            indices = np.linspace(0, history_len, 9, dtype=int)
            images = [self.images[i] for i in indices]
        with torch.inference_mode():
            output = self.inference.call_model(images, instruction, self.step_id)[0]
        action = {'STOP': 0, 'MOVE_FORWARD': 1, 'TURN_LEFT': 2, 'TURN_RIGHT': 3}.get(output, 0)
        self.step_id += 1
        self.calls += 1
        return action, {'generated': True, 'output': output, 'source': 'src/evaluation.py:JanusVLN_Inference', 'input_modalities': ['rgb'], 'history_frames': len(images)}
