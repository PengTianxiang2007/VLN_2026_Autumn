"""Machine resources are reused; source and outputs belong to this project."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resource_root():
    return Path(os.environ.get('VLN_RESOURCE_ROOT', '/mnt/nas/gezuhao/shared_dataset/Resource_Peng')).resolve()


def output_root():
    return Path(os.environ.get('VLN_OUTPUT_ROOT', PROJECT_ROOT / 'outputs')).resolve()


def model_root(name):
    if name not in ('streamvln', 'janusvln'):
        raise ValueError('Unknown backbone: ' + name)
    return PROJECT_ROOT / 'backbone' / name


def model_python(name):
    # Do not resolve the python symlink: its venv determines site-packages.
    return Path(os.environ.get(name.upper() + '_VENV', model_root(name) / '.venv')) / 'bin/python'


def simulation_python():
    return Path(os.environ.get('VLNVERSE_VENV', PROJECT_ROOT / 'benchmarks/vlnverse/.venv')) / 'bin/python'


def isaac_root():
    return Path(os.environ.get('PENG_ISAAC_ROOT', PROJECT_ROOT / '.runtime/isaac45'))


def model_environment(name, gpu=None):
    root = model_root(name)
    habitat = PROJECT_ROOT / 'benchmarks/habitat_ce/habitat-lab-v0.2.4'
    paths = [root / ('streamvln' if name == 'streamvln' else 'src'), root,
             habitat / 'habitat-lab', habitat / 'habitat-baselines', PROJECT_ROOT]
    env = os.environ.copy()
    env.update(PYTHONPATH=os.pathsep.join(map(str, paths)), PYTHONDONTWRITEBYTECODE='1',
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', OMP_NUM_THREADS='2',
               OPENBLAS_NUM_THREADS='2', MAGNUM_LOG='quiet', HABITAT_SIM_LOG='quiet',
               PYTHONUNBUFFERED='1', NUMBA_CACHE_DIR=str(PROJECT_ROOT / '.runtime/numba' / name),
               VLN_RESOURCE_ROOT=str(resource_root()), VLN_OUTPUT_ROOT=str(output_root()),
               VLNVERSE_VENV=str(simulation_python().parent.parent), PENG_ISAAC_ROOT=str(isaac_root()))
    env[name.upper() + '_VENV'] = str(model_python(name).parent.parent)
    if gpu is not None:
        env['CUDA_VISIBLE_DEVICES'] = str(gpu)
    return env


def ensure_data_links(name):
    for relative, asset in {
        'data/datasets/r2r': 'assets/StreamVLN/r2r',
        'data/datasets/rxr': 'assets/StreamVLN/rxr',
        'data/scene_datasets/mp3d': 'assets/StreamVLN/mp3d',
    }.items():
        link, target = model_root(name) / relative, resource_root() / asset
        if not target.is_dir():
            raise FileNotFoundError('Required existing resource: ' + str(target))
        if link.is_symlink():
            if link.resolve() != target.resolve():
                raise ValueError('Conflicting resource link: ' + str(link))
        elif link.exists():
            raise ValueError('Preserving existing directory: ' + str(link))
        else:
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(target, target_is_directory=True)


if __name__ == '__main__':
    for model in ('streamvln', 'janusvln'):
        ensure_data_links(model)
    print('Dataset links ready.')
