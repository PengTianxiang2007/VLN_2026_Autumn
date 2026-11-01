"""Download official ModelScope files directly, resume partials and verify SHA256."""
import hashlib, json, os, subprocess, urllib.request, fcntl
from pathlib import Path
from urllib.parse import urlencode
import argparse
p=argparse.ArgumentParser(); p.add_argument('--model',choices=['Base','Extra'],default='Extra'); a=p.parse_args()
name='JanusVLN_'+a.model
root=Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models')/name
root.mkdir(parents=True,exist_ok=True)
lock=(root/'.download.lock').open('a')
try:
 fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:
 raise SystemExit('A checkpoint download is already running in '+str(root))
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
url='https://modelscope.cn/api/v1/models/misstl/'+name+'/repo/files?Revision=master&Recursive=true'
with opener.open(url,timeout=60) as f: manifest=json.load(f)
(root/'download_manifest.json').write_text(json.dumps(manifest,indent=2))
env=os.environ.copy()
for key in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']: env.pop(key,None)
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(16*1024*1024),b''): h.update(b)
 return h.hexdigest()
for item in manifest['Data']['Files']:
 rel=item['Path']
 if item['Type']!='blob' or rel.startswith('.') or rel in ('train.log','trainer_state.json','training_args.bin'): continue
 path=root/rel; path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():
  if path.stat().st_size==item['Size'] and digest(path)==item['Sha256']:
   print('Verified existing',rel,flush=True); continue
  raise RuntimeError('Existing file differs; preserve and inspect: '+str(path))
 partial=path.with_name(path.name+'.part')
 query=urlencode({'Revision':item['Revision'],'FilePath':rel})
 source='https://modelscope.cn/api/v1/models/misstl/'+name+'/repo?'+query
 print('Downloading',rel,item['Size'],flush=True)
 subprocess.run(['curl','--noproxy','*','-fL','--retry','5','--retry-delay','3','--connect-timeout','30','--speed-time','120','--speed-limit','1024','-C','-','-o',str(partial),source],env=env,check=True)
 if partial.stat().st_size!=item['Size'] or digest(partial)!=item['Sha256']: raise RuntimeError('Checksum mismatch: '+rel)
 partial.rename(path); print('Verified',rel,flush=True)
(root/'download_verified.json').write_text(json.dumps({'model': name, 'files': [item['Path'] for item in manifest['Data']['Files'] if item['Type'] == 'blob' and not item['Path'].startswith('.') and item['Path'] not in ('train.log','trainer_state.json','training_args.bin')]} ,indent=2))
print('Checkpoint complete',root,flush=True)
