"""Reuse Isaac's exact ML libraries inside this project without downloading them."""
from pathlib import Path
import shutil
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from core.paths import isaac_root, simulation_python


def reuse(source, site):
    target = site / source.name
    if source.name.endswith('.dist-info'):
        # uv deliberately ignores symlinked distribution metadata.
        if target.is_symlink():
            if target.resolve() != source.resolve():
                raise ValueError('Conflicting distribution metadata: ' + str(target))
            target.unlink()
        if not target.exists():
            shutil.copytree(source, target)
    elif not target.exists() and not target.is_symlink():
        target.symlink_to(source, target_is_directory=source.is_dir())


def main():
    bundle = isaac_root() / 'exts/omni.isaac.ml_archive/pip_prebundle'
    site = simulation_python().parent.parent / 'lib/python3.10/site-packages'
    if not (bundle / 'torch-2.5.1+cu118.dist-info/METADATA').is_file():
        raise FileNotFoundError('Expected Isaac 4.5 bundled Torch 2.5.1+cu118')
    site.mkdir(parents=True, exist_ok=True)
    for source in bundle.iterdir():
        name = source.name
        if name in {'__pycache__', 'bin', 'share', 'torchaudio', 'torio'} or name.startswith('torchaudio-'):
            continue
        reuse(source, site)
    compute = isaac_root() / 'exts/omni.pip.compute/pip_prebundle'
    for name in ['cv2', 'opencv_python_headless.libs', 'opencv_python_headless-4.9.0.80.dist-info']:
        source = compute / name
        if not source.exists():
            raise FileNotFoundError('Expected bundled OpenCV 4.9.0.80: ' + str(source))
        reuse(source, site)
    print('Isaac Torch/CUDA and OpenCV libraries reused; package metadata installed locally.')


if __name__ == '__main__':
    main()
