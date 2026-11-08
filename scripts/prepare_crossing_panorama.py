"""Freeze the original ten-case cohort and a camera-only 360-degree capture plan."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
RESOURCE = Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/VLNVerse')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda: f.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def calibration():
    usd_lib = next((ROOT / '.runtime/isaac45/extscache').glob('omni.usd.libs-*'))
    env = dict(os.environ, PYTHONPATH=str(usd_lib), LD_LIBRARY_PATH=str(usd_lib / 'bin'), PYTHONDONTWRITEBYTECODE='1')
    code = '''
import json, math
from pxr import Usd, UsdGeom, Gf
s=Usd.Stage.Open(ASSET)
p=s.GetPrimAtPath('/h1_description/torso_link/h1_pano_camera_0')
c=UsdGeom.Camera(p)
t=UsdGeom.Xformable(p).GetLocalTransformation()
forward=t.TransformDir(Gf.Vec3d(0,0,-1))
f=float(c.GetFocalLengthAttr().Get()); h=float(c.GetHorizontalApertureAttr().Get())
print(json.dumps(dict(source_asset=ASSET, source_prim=str(p.GetPath()), focal_length_usd=f,
 horizontal_aperture_usd=h, source_vertical_aperture_usd=float(c.GetVerticalApertureAttr().Get()),
 source_clipping_range=list(c.GetClippingRangeAttr().Get()), local_translation=list(t.ExtractTranslation()),
 local_forward=list(forward), pitch_down_deg=math.degrees(math.asin(-forward[2])),
 horizontal_fov_deg=math.degrees(2*math.atan(h/(2*f))))))
'''
    asset = RESOURCE / 'Embodiments/vln-pe/h1/h1_vln_pointcloud.usd'
    result = json.loads(subprocess.check_output([str(ROOT / 'benchmarks/vlnverse/.venv/bin/python'), '-B', '-c',
                                                'ASSET=' + repr(str(asset)) + '\n' + code], env=env, text=True))
    result['source_asset_sha256'] = sha(asset)
    assert abs(result['horizontal_fov_deg'] - 90) < 1e-4
    assert abs(result['pitch_down_deg'] - 15) < 1e-4
    assert abs(result['local_translation'][2] - .72) < 1e-6
    result.update(resolution=[640, 480], vertical_aperture_usd=result['horizontal_aperture_usd'] * .75,
                  vertical_fov_deg=math.degrees(2 * math.atan(.75)), clipping_range_m=[.01, 1000.0],
                  origin_policy='Optical center directly above annotated Crossing XY; no 0.2m forward offset.',
                  height_policy='Mean original checkpoint root Z for this Crossing + native static camera offset Z.',
                  vertical_aperture_policy='Match 640x480 aspect ratio explicitly; native horizontal FOV retained.')
    return result


def reuse_completed(previous, out, manifest):
    """Copy only complete, byte-verified scenes with identical capture settings."""
    previous = previous.resolve()
    old = json.loads((previous / 'manifest.json').read_text())
    state = json.loads((previous / 'status.json').read_text())
    if state['phase'] not in ['failed', 'capture_complete'] or not state.get('owned_processes_exited'):
        raise ValueError('Reuse requires a finished source run with owned processes exited')
    for key in ['camera', 'cases', 'panoramas', 'scenes', 'render_seed', 'lighting', 'angle_convention']:
        if old[key] != manifest[key]:
            raise ValueError('Capture protocol differs: ' + key)
    completed, records = [], []
    for asset in manifest['scenes']:
        scene_file = previous / 'scenes' / (asset['scene'] + '.json')
        if not scene_file.exists():
            continue
        scene = json.loads(scene_file.read_text())
        if scene['status'] != 'complete' or scene['model_calls'] != 0:
            raise ValueError('Invalid source scene completion')
        jobs = [p for p in manifest['panoramas'] if p['scene'] == asset['scene']]
        assert sorted(p['panorama_id'] for p in scene['results']) == sorted(p['panorama_id'] for p in jobs)
        for job in jobs:
            pano = previous / 'panoramas' / job['panorama_id']
            metadata = json.loads((pano / 'metadata.json').read_text())
            assert metadata['position'] == job['position']
            assert metadata['model_calls'] == 0 and metadata['navigation_actions'] == 0
            assert [v['yaw_deg'] for v in metadata['views']] == job['yaw_degrees']
            assert len({v['sha256'] for v in metadata['views']}) == 8
            for view in metadata['views']:
                path = (previous / view['path']).resolve()
                assert path.is_relative_to(pano.resolve())
                assert sha(path) == view['sha256']
                assert (view['width'], view['height']) == (640, 480)
                assert math.dist(view['position'], job['position']) < 1e-5
                assert abs((view['actual_yaw_deg'] - view['yaw_deg'] + 180) % 360 - 180) < 1e-3
                assert abs(view['pitch_down_deg'] - manifest['camera']['pitch_down_deg']) < 1e-3
            shutil.copytree(pano, out / 'panoramas' / job['panorama_id'])
            for view in metadata['views']:
                assert sha(out / view['path']) == view['sha256']
            records.append(dict(panorama_id=job['panorama_id'], images=8,
                                original_capture_at=metadata['captured_at'],
                                source_metadata=str(pano / 'metadata.json'), metadata_sha256=sha(pano / 'metadata.json')))
        shutil.copy2(scene_file, out / 'scenes' / scene_file.name)
        completed.append(asset['scene'])
    manifest['reused_completed_scenes'] = completed
    manifest['reused_unique_images'] = sum(p['images'] for p in records)
    write(out / 'reuse.json', dict(source=str(previous), source_manifest_sha256=sha(previous / 'manifest.json'),
                                  source_status_sha256=sha(previous / 'status.json'), protocol_identical=True,
                                  scenes=completed, panoramas=records, unique_images=manifest['reused_unique_images']))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--reuse-completed-from', type=Path, help='Verify and copy completed scenes into a new immutable run')
    args = ap.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise FileExistsError('Use a new capture directory; existing runs are immutable.')
    source = ROOT / 'outputs/oracle_crossing/checkpoint_action10/run_20261105_01/manifest.json'
    cohort = ROOT / 'experiments/agent_route_choice/v001/cohort.json'
    prep = ROOT / 'outputs/agent_route_choice/v001/preparation_20261106_04'
    ids = json.loads(cohort.read_text())['episode_ids']
    source_cases = {x['episode_id']: x for x in json.loads(source.read_text())['cases']}
    old_inputs = json.loads((prep / 'dataset.json').read_text())['cases']
    camera = calibration()
    cases, groups, provenance = [], {}, []
    for i, eid in enumerate(ids):
        c = source_cases[eid]
        frame = int(c['review']['decision_frame'])
        step_path = Path(c['source_steps'])
        assert sha(step_path) == c['source_steps_sha256']
        step = next(x for x in map(json.loads, step_path.read_text().splitlines()) if x['frame'] == frame)
        xy = c['crossing']['position']
        key = c['scene'] + '__' + c['crossing_id']
        group = groups.setdefault(key, dict(panorama_id=key, scene=c['scene'], crossing_id=c['crossing_id'],
                                            crossing_xy=xy, samples=[], root_z_values=[]))
        assert group['crossing_xy'] == xy
        sample = f'sample_{i + 1:02d}'
        group['samples'].append(sample)
        group['root_z_values'].append(step['position'][2])
        old = old_inputs[i]
        assert old['sample_id'] == sample and old['checkpoint_frame'] == frame
        images = []
        for im in old['images']:
            p = prep / im['path']
            assert sha(p) == im['sha256']
            images.append(dict(im, path=str(p)))
        cases.append(dict(sample_id=sample, episode_id=eid, scene=c['scene'], crossing_id=c['crossing_id'],
                          panorama_id=key, checkpoint_frame=frame, original_checkpoint_position=step['position'],
                          crossing_xy=xy, checkpoint_to_crossing_distance_m=math.dist(xy, step['position'][:2]),
                          instruction=old['instruction'], original_images=images,
                          approach_actions=old['approach_actions'], attempt_actions=old['attempt_actions']))
        provenance.append(dict(sample_id=sample, source_steps=str(step_path), source_steps_sha256=sha(step_path),
                               source_video=c['source_video'], crossing_annotation=c['crossing']))
    scenes = []
    for g in groups.values():
        g['position'] = g['crossing_xy'] + [statistics.mean(g['root_z_values']) + camera['local_translation'][2]]
        g['yaw_degrees'] = list(range(0, 360, 45))
        if g['scene'] not in scenes:
            scenes.append(g['scene'])
    assert len(cases) == 10 and len(groups) == 9 and len(scenes) == 8
    assets = []
    for scene in scenes:
        p = RESOURCE / 'scenes' / scene / 'start_result_navigation.usd'
        if not p.is_file():
            raise FileNotFoundError(p)
        assets.append(dict(scene=scene, path=str(p), sha256=sha(p), bytes=p.stat().st_size))
    out.mkdir(parents=True)
    for name in ['source', 'logs', 'panoramas', 'scenes']:
        (out / name).mkdir()
    source_files = ['scripts/prepare_crossing_panorama.py', 'scripts/render_crossing_panorama.py',
                    'scripts/run_crossing_panorama.py', 'scripts/run_crossing_panorama_isaac.sh',
                    'scripts/export_crossing_panorama.py', 'scripts/check_crossing_panorama.cjs',
                    'scripts/test_crossing_single_gpu.py', 'scripts/run_crossing_local_batch.py',
                    'core/crossing_checkpoint.py', 'experiments/agent_route_choice/v001/cohort.json',
                    'experiments/agent_route_choice/v002/README.md',
                    f'experiments/agent_route_choice/v002/{out.name}/README.md']
    hashes = {}
    for rel in source_files:
        dest = out / 'source' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dest)
        hashes[rel] = sha(dest)
    git_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    (out / 'source/git_status.txt').write_bytes(subprocess.check_output(['git', 'status', '--short'], cwd=ROOT))
    (out / 'source/tracked.diff').write_bytes(subprocess.check_output(['git', 'diff', 'HEAD', '--binary'], cwd=ROOT))
    manifest = dict(schema=1, version='agent_route_choice_v002_camera_capture', created_at=datetime.now(timezone.utc).isoformat(),
                    original_navigation_seed=2, render_seed=20261106, model_calls=0, navigation_actions=0,
                    angle_convention='0=world +X, 90=world +Y, 180=-X, 270=-Y; positive yaw counterclockwise viewed from above.',
                    not_original_camera_replay=True, camera=camera, cases=cases, panoramas=list(groups.values()),
                    scenes=assets, lighting='Native VLNEvalTask distant1000 + up/down disk5000 radius50, centered at Crossing root position.',
                    expected_unique_images=72, expected_case_image_references=80)
    if args.reuse_completed_from:
        reuse_completed(args.reuse_completed_from, out, manifest)
    write(out / 'manifest.json', manifest)
    write(out / 'provenance.json', dict(git_head=git_head, source_hashes=hashes, source_manifest=str(source),
                                      source_manifest_sha256=sha(source), cohort_sha256=sha(cohort),
                                      original_preparation=str(prep), cases=provenance,
                                      warning='Provenance contains geometry annotations; never pass it to the route-choice model.'))
    write(out / 'status.json', dict(phase='prepared', model_calls=0, expected_unique_images=72,
                                    completed_unique_images=manifest.get('reused_unique_images', 0)))
    print(json.dumps(dict(output=str(out), cases=10, panoramas=9, scenes=8, expected_images=72,
                         reused_images=manifest.get('reused_unique_images', 0))))


if __name__ == '__main__':
    main()
