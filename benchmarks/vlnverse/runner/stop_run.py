"""Stop only a recorded, identity-verified evaluator launcher owned by this setup."""
import argparse,json,os,signal
from pathlib import Path
ap=argparse.ArgumentParser()
ap.add_argument('--method',choices=['StreamVLN','JanusVLN'],required=True)
ap.add_argument('--run-id',required=True)
a=ap.parse_args()
if not a.run_id.startswith('peng_fine_') or '/' in a.run_id: ap.error('Invalid run ID')
import sys
PROJECT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(PROJECT))
from core.paths import output_root
root=output_root()/"vlnverse"/a.method.lower()/"results"/a.run_id
info=json.loads((root/'owned_processes.json').read_text())
if info.get('status')=='stopped':
    print('Already stopped'); raise SystemExit(0)
pid=info['launcher_pid']; proc=Path('/proc')/str(pid)
if not proc.exists():
    print('Recorded launcher no longer exists'); raise SystemExit(0)
if proc.joinpath('stat').read_text().split()[21]!=info['launcher_start_ticks']: raise RuntimeError('PID identity changed; refusing to signal')
args=proc.joinpath('cmdline').read_bytes().split(b'\0')
if str(Path(__file__).resolve().parent/"run_full.py").encode() not in args: raise RuntimeError('Command identity changed; refusing to signal')
idx=args.index(b'--method')
if args[idx+1]!=a.method.encode(): raise RuntimeError('Method identity mismatch; refusing to signal')
os.kill(pid,signal.SIGTERM)
print('SIGTERM sent to verified launcher',pid,'; its own cleanup stops its child processes.')
