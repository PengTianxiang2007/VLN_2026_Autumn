"""CPU-only imports, source-origin checks, dataset loading and checkpoint metadata."""
import argparse
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from core.paths import ensure_data_links, model_environment, model_python, model_root, resource_root


def check(name):
    import torch
    import transformers
    import flash_attn
    import habitat
    import habitat_sim
    import habitat_baselines
    from habitat_baselines.config.default import get_config
    from transformers import AutoConfig, AutoTokenizer
    if name == 'streamvln':
        modules = ['llava', 'model.stream_video_vln', 'streamvln_eval', 'streamvln_eval_rxr']
        checkpoint = 'StreamVLN_R2R_v1_3'
    else:
        modules = ['qwen_vl.model.modeling_qwen2_5_vl', 'evaluation']
        checkpoint = 'JanusVLN_Extra'
    imports = {}
    for module_name in modules:
        module = importlib.import_module(module_name)
        file = Path(module.__file__).resolve()
        if PROJECT not in file.parents:
            raise RuntimeError('Imported old source: ' + str(file))
        imports[module_name] = str(file.relative_to(PROJECT))
    for module in [habitat, habitat_baselines]:
        file = Path(module.__file__).resolve()
        if PROJECT not in file.parents:
            raise RuntimeError('Imported old Habitat source: ' + str(file))
        imports[module.__name__] = str(file.relative_to(PROJECT))
    adapter_path = model_root(name) / 'vlnverse/adapter.py'
    spec = importlib.util.spec_from_file_location('validation_vlnverse_adapter', adapter_path)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    assert callable(adapter.NavigationAgent)
    datasets = {}
    for benchmark, expected in [('r2r', 1839), ('rxr', 3669)]:
        config = get_config('config/vln_' + benchmark + '.yaml')
        with habitat.config.read_write(config):
            config.habitat.dataset.split = 'val_unseen'
        data = habitat.make_dataset(config.habitat.dataset.type, config=config.habitat.dataset)
        assert len(data.episodes) == expected, (benchmark, len(data.episodes))
        scenes = sorted({episode.scene_id for episode in data.episodes})
        for scene in scenes:
            assert Path(scene).is_file(), scene
            assert Path(scene).with_suffix('.navmesh').is_file(), scene
        datasets[benchmark] = dict(episodes=len(data.episodes), scenes=len(scenes))
    path = resource_root() / 'models' / checkpoint
    config = AutoConfig.from_pretrained(path, local_files_only=True)
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
    index = json.loads((path / 'model.safetensors.index.json').read_text())
    shards = sorted(set(index['weight_map'].values()))
    for shard in shards:
        assert (path / shard).is_file(), shard
    return dict(passed=True, backbone=name, python=sys.version, torch=torch.__version__,
                transformers=transformers.__version__, flash_attention=flash_attn.__version__,
                habitat=habitat.__version__, habitat_sim=habitat_sim.__version__,
                source_imports=imports, datasets=datasets, vlnverse_adapter_import=True,
                checkpoint=dict(path=str(path), model_type=config.model_type,
                                tokenizer_size=len(tokenizer), shards=len(shards)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backbone', choices=['streamvln', 'janusvln'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.output = args.output.resolve()
    if not args.worker:
        ensure_data_links(args.backbone)
        env = model_environment(args.backbone)
        env['CUDA_VISIBLE_DEVICES'] = ''
        subprocess.run([str(model_python(args.backbone)), str(Path(__file__).resolve()),
                        '--backbone', args.backbone, '--output', str(args.output), '--worker'],
                       cwd=model_root(args.backbone), env=env, check=True)
        return
    result = check(args.backbone)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
