"""Check checkpoint metadata, shard tensors and offline processor without GPU allocation."""
import argparse, json, os, struct
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
from transformers import AutoConfig, AutoTokenizer, AutoProcessor
p=argparse.ArgumentParser()
p.add_argument('--model_path',default='/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/JanusVLN_Extra')
a=p.parse_args(); root=Path(a.model_path)
index=json.loads((root/'model.safetensors.index.json').read_text())
weights=index['weight_map']; actual={}
for shard in sorted(set(weights.values())):
 with (root/shard).open('rb') as f:
  count=struct.unpack('<Q',f.read(8))[0]
  header=json.loads(f.read(count))
 for key in header:
  if key=='__metadata__': continue
  assert key not in actual,key
  actual[key]=shard
assert actual==weights, 'Shard/index mismatch'
assert any(k.startswith('vggt.') for k in weights), 'VGGT weights missing'
cfg=AutoConfig.from_pretrained(root,local_files_only=True)
tokenizer=AutoTokenizer.from_pretrained(root,local_files_only=True)
processor=AutoProcessor.from_pretrained(root,local_files_only=True)
assert cfg.model_type=='qwen2_5_vl' and cfg.use_vggt_feature
print('Shards:',len(set(weights.values())),'Tensors:',len(weights),'Tokenizer:',len(tokenizer),'Processor:',type(processor).__name__)
print('CPU checkpoint metadata check passed:',root)
