"""CPU-only parameter-name audit; meta tensors allocate no model weights."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from bootstrap import bootstrap
from checkpoint_compatibility import UNUSED_MASK_TOKENS

p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
p.add_argument('--checkpoint', type=Path, required=True)
p.add_argument('--index', default='checkpoint_index.json')
a = p.parse_args()
bootstrap(a.output)

import torch
from accelerate import init_empty_weights
from vlnverse.model.basemodel.internvla_n1.internvla_n1 import InternVLAN1ForCausalLM, InternVLAN1ModelConfig

config = InternVLAN1ModelConfig.from_pretrained(str(a.checkpoint), local_files_only=True)
index = json.loads((a.output / a.index).read_text())

# The source constructor loads the small depth initializer before the full N1
# state dict. For this shapes-only audit, it contributes no parameter values.
def empty_initializer(path, *args, **kwargs):
    if Path(path).name != 'depth_anything_v2_vits.pth':
        raise RuntimeError('Unexpected initializer in meta audit: ' + str(path))
    return {}

with init_empty_weights(), patch.object(torch, 'load', empty_initializer):
    model = InternVLAN1ForCausalLM(config)
state = model.state_dict()
assert all(value.device.type == 'meta' for value in model.parameters()), 'Audit must not allocate real weights'
missing = sorted(set(state) - set(index['weight_map']))
unexpected = sorted(set(index['weight_map']) - set(state))
invalid_unexpected = sorted(set(unexpected) - UNUSED_MASK_TOKENS)
shape_mismatches = {k: {'model': list(v.shape), 'checkpoint': index['shapes'][k]['shape']}
                    for k, v in state.items() if k in index.get('shapes', {})
                    and list(v.shape) != index['shapes'][k]['shape']}
proof = {'kind': 'CPU meta parameter-name audit, not actual weight loading',
         'expected_parameter_keys': len(state), 'checkpoint_parameter_keys': len(index['weight_map']),
         'missing': missing, 'unexpected': unexpected, 'shape_mismatches': shape_mismatches,
         'allowed_unused_mask_tokens': sorted(set(unexpected) & UNUSED_MASK_TOKENS),
         'compatible_names': not missing and not invalid_unexpected, 'source': index.get('source', a.index)}
(a.output / 'checkpoint_schema_audit.json').write_text(json.dumps(proof, indent=2))
print(json.dumps(proof), flush=True)
if missing or invalid_unexpected or shape_mismatches:
    raise SystemExit(1)
