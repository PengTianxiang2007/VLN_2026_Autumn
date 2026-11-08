"""Finish an authorized checkpoint download and validate it. Never launches inference."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import struct
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]


def write_json(path,value):
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(path)


def process_identity(pid):
    proc=Path('/proc')/str(pid)
    try:
        stat=(proc/'stat').read_text().split(') ',1)[1].split()
        if stat[0]=='Z':return None
        return stat[19],(proc/'cmdline').read_bytes()
    except OSError:return None


def validate(output):
    manifest=json.loads((output/'download_manifest.json').read_text())
    status=json.loads((output/'download_status.json').read_text())
    if status['phase']!='verified':raise ValueError('Download has unverified files')
    if set(status['verified_files'])!={f['Path'] for f in manifest['files']}:
        raise ValueError('Verified file list differs from frozen manifest')
    index=json.loads((output/'model.safetensors.index.json').read_text())
    shards=sorted(set(index['weight_map'].values()))
    headers={}
    total=0
    for name in shards:
        path=output/name
        total+=path.stat().st_size
        with path.open('rb') as stream:
            n=struct.unpack('<Q',stream.read(8))[0]
            if n>16*1024**2:raise ValueError('Oversized safetensors header')
            header=json.loads(stream.read(n))
        tensors={k:v for k,v in header.items() if k!='__metadata__'}
        if 8+n+max(v['data_offsets'][1] for v in tensors.values())!=path.stat().st_size:
            raise ValueError('Safetensors length mismatch: '+name)
        headers[name]=set(tensors)
    for name,shard in index['weight_map'].items():
        if name not in headers[shard]:raise ValueError('Missing indexed tensor: '+name)
    config=json.loads((output/'config.json').read_text())
    result=dict(passed=True,model_id=manifest['model_id'],shards=len(shards),
        tensors=len(index['weight_map']),weight_bytes=total,
        architectures=config.get('architectures'),
        sha256='Every selected file checked against frozen official ModelScope manifest by downloader.',
        structure='Safetensors headers, lengths and tensor index checked.',
        gpu_inference_tested=False,automatic_inference=False,
        verified_at=datetime.now(timezone.utc).isoformat())
    write_json(output/'validation.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--existing-pid',type=int)
    args=parser.parse_args()
    state=dict(phase='waiting_for_existing_download',pid=os.getpid(),model_id=args.model,
               inference_paused=True,automatic_inference=False,attempts=[])
    path=args.output/'supervision_status.json'

    def publish():
        state['updated_at']=datetime.now(timezone.utc).isoformat()
        write_json(path,state)

    publish()
    if args.existing_pid:
        identity=process_identity(args.existing_pid)
        if identity:
            if b'download_modelscope_checkpoint.py' not in identity[1] or str(args.output).encode() not in identity[1]:
                raise ValueError('Existing PID is not this checkpoint downloader')
            state['existing_download_pid']=args.existing_pid;publish()
            while process_identity(args.existing_pid)==identity:
                time.sleep(5)
    env={k:v for k,v in os.environ.items() if 'proxy' not in k.lower()}
    for attempt in range(4):
        status_path=args.output/'download_status.json'
        if status_path.exists() and json.loads(status_path.read_text()).get('phase')=='verified':
            state.update(phase='verified',validation=validate(args.output));publish();return
        state['phase']='resuming_and_validating';publish()
        command=['python3','-B',str(ROOT/'scripts/download_modelscope_checkpoint.py'),
                 '--model',args.model,'--output',str(args.output),'--workers','4']
        with (args.output/'download.log').open('a') as log:
            process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            (args.output/'download.pid').write_text(str(process.pid)+'\n')
            state['active_download_pid']=process.pid;publish()
            code=process.wait()
        state['attempts'].append(dict(attempt=attempt,exit_code=code));publish()
        if code==0:
            state.update(phase='verified',validation=validate(args.output));publish();return
        time.sleep(10)
    state['phase']='download_needs_attention';publish()


if __name__=='__main__':main()
