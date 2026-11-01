"""Stable run/episode seeds, shared by the model service and the simulator."""
import hashlib
import os

SEED_SCHEME = 'sha256-episode-v1'


def configured_seed():
    value = os.environ.get('VLN_EVAL_SEED')
    if value is None:
        return None
    seed = int(value)
    if not 0 <= seed < 2**31:
        raise ValueError('VLN_EVAL_SEED must be in [0, 2**31).')
    return seed


def episode_seed(seed, episode_id):
    if not 0 <= seed < 2**31 or not isinstance(episode_id, str) or not episode_id:
        raise ValueError('A valid run seed and nonempty episode ID are required.')
    value = f'{SEED_SCHEME}:{seed}:{episode_id}'.encode('utf-8')
    return int.from_bytes(hashlib.sha256(value).digest()[:4], 'big') % (2**31 - 1)


def seed_model_libraries(seed):
    import random
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = False
