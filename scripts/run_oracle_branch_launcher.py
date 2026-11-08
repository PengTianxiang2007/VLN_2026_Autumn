"""Extend only model startup waiting around an unchanged frozen native runner."""
import argparse
from pathlib import Path
import runpy
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code-root',type=Path,required=True)
    parser.add_argument('--model-startup-timeout',type=int,required=True)
    parser.add_argument('native_args',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    if not 900<=args.model_startup_timeout<=3600:
        parser.error('Startup wait must be between 900 and 3600 seconds')
    code=args.code_root.resolve()
    runner=code/'benchmarks/vlnverse/runner/run_full.py'
    sys.path.insert(0,str(code))
    from core import vlnverse_runtime
    assert Path(vlnverse_runtime.__file__).resolve()==code/'core/vlnverse_runtime.py'
    original_wait=vlnverse_runtime.wait_for_model_ready

    def startup_wait(process,chunk,timeout=900,interval=2):
        return original_wait(process,chunk,timeout=max(timeout,args.model_startup_timeout),interval=interval)

    vlnverse_runtime.wait_for_model_ready=startup_wait
    native=args.native_args[1:] if args.native_args[:1]==['--'] else args.native_args
    sys.argv=[str(runner),*native]
    print(f'MODEL_STARTUP_WAIT_SECONDS={args.model_startup_timeout}; frozen model/navigation/physics sources unchanged',flush=True)
    runpy.run_path(str(runner),run_name='__main__')


if __name__=='__main__':main()
