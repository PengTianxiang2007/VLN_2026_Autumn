"""Prepare v002 12/16-image local decisions; maps and labels remain review-only."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import read, write, file_hash, now
from core.agent_panorama_choice import build_messages, schema, validate_case


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args(); out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    source = ROOT / 'outputs/agent_route_choice/v002/capture_20261106_04'
    old = ROOT / 'outputs/agent_route_choice/v001/preparation_20261106_04'
    m = read(source / 'manifest.json'); originals = read(old / 'dataset.json')['cases']
    assert read(source / 'summary.json')['unique_images'] == 72
    prompt = ROOT / 'experiments/agent_route_choice/v002/prompts/draft01'
    shutil.copytree(prompt, out / 'prompts')
    cases = []
    for capture, original in zip(m['cases'], originals):
        assert capture['sample_id'] == original['sample_id']
        case = {k: original[k] for k in ('sample_id', 'instruction', 'checkpoint_frame', 'wrong_end_frame', 'approach_actions', 'attempt_actions')}
        meta = read(source / 'panoramas' / capture['panorama_id'] / 'metadata.json')
        images = []
        for v in meta['views']:
            rel = 'images/panoramas/' + capture['panorama_id'] + '/' + Path(v['path']).name
            dest = out / rel; dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists(): shutil.copy2(source / v['path'], dest)
            assert file_hash(dest) == v['sha256']
            images.append(dict(id=v['view_id'], yaw_deg=v['yaw_deg'], phase='crossing_panorama', path=rel, sha256=v['sha256']))
        for im in original['images']:
            dest = out / im['path']; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(old / im['path'], dest)
            images.append(dict(im, phase='approach_history' if im['phase'] == 'checkpoint_context' else 'wrong_attempt'))
        case['images'] = images; validate_case(case); cases.append(case)
        write(out / 'request_previews' / (case['sample_id'] + '_call1.json'),
              build_messages(case, out, 1, (out / 'prompts/01_inventory_en.txt').read_text(), embed=False))
    write(out / 'dataset.json', dict(schema='agent_panorama_choice_v002', cases=cases))
    labels = read(old / 'evaluation_only.json')
    for label, c in zip(labels['labels'], m['cases']):
        label['panorama_id'] = c['panorama_id']; label['panorama_position'] = next(p['position'] for p in m['panoramas'] if p['panorama_id'] == c['panorama_id'])
        label['checkpoint_to_crossing_distance_m'] = c['checkpoint_to_crossing_distance_m']
    write(out / 'evaluation_only.json', labels)
    for scene in {x['scene'] for x in labels['labels']}:
        d = ROOT / 'outputs/checkpoint_review/seed2_25_20261103/scenes' / scene
        target = out / 'review_maps' / scene; target.mkdir(parents=True)
        for name in ('geometry.json', 'floorplan.png'):
            if not (d / name).is_file(): raise FileNotFoundError(d / name)
            shutil.copy2(d / name, target / name)
    config = read(ROOT / 'experiments/agent_route_choice/v002/run_20261106_01/model.json')
    write(out / 'model.json', config)
    for stage in (1, 2): write(out / f'call{stage}_schema.json', schema(stage))
    write(out / 'input_audit.json', dict(samples=10, panorama_points=9, unique_panorama_images=72,
          call1_image_counts=[12] * 10, call2_image_counts=[16] * 10,
          model_calls=0, maps_in_requests=False, coordinates_in_requests=False, task_in_call1=False,
          call2_inventory='Full actual same-model call1 JSON; not fabricated during preparation.',
          source_capture=str(source), source_capture_manifest_sha256=file_hash(source / 'manifest.json')))
    frozen = out / 'source'; hashes = {}
    for rel in ['core/agent_panorama_choice.py','core/agent_route_choice.py','core/crossing_checkpoint.py',
                'scripts/prepare_agent_panorama_choice.py','scripts/run_agent_panorama_choice.py',
                'scripts/run_agent_route_choice.py','scripts/test_crossing_single_gpu.py','scripts/run_crossing_local_batch.py',
                'scripts/serve_crossing_vlm.py','tests/test_agent_panorama_choice.py']:
        dest = frozen / rel; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / rel, dest); hashes[rel] = file_hash(dest)
    (out / 'workspace_status.txt').write_bytes(subprocess.check_output(['git','status','--short'],cwd=ROOT))
    (out / 'workspace_diff.patch').write_bytes(subprocess.check_output(['git','diff','HEAD','--binary'],cwd=ROOT))
    files = {str(p.relative_to(out)): file_hash(p) for p in out.rglob('*') if p.is_file() and not p.is_relative_to(frozen)}
    write(out / 'manifest.json', dict(created_at=now(), git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                                     files_sha256=files, code_sha256=hashes, source_note='Actual uncommitted source snapshot retained'))
    print(json.dumps(dict(prepared=str(out), samples=10, images_per_call=[12,16])))


if __name__ == '__main__': main()
