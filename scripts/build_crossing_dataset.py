"""Freeze the user's nonempty Crossing annotations into a portable offline dataset."""
import argparse
import base64
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
UPLOAD = ROOT / 'outputs/crossing_annotation/seed2_69/crossing_annotation_69_zh_annotated.html'
TRUSTED = ROOT / 'outputs/crossing_annotation/seed2_69/run_20261106_02'
EXP = ROOT / 'experiments/crossing_dataset/seed2_human_v001'
NAME = 'crossing_seed2_human_v001'


def now():
    return datetime.now(timezone.utc).isoformat()


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def jsonl(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(''.join(compact(row) + '\n' for row in rows))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def script(page, name):
    match = re.search(r'<script id="' + re.escape(name) + r'"[^>]*>([\s\S]*?)</script>', page)
    if not match:
        raise ValueError('Missing embedded data: ' + name)
    return match.group(1)


def build(out):
    out.mkdir(parents=True, exist_ok=False)
    write(out / 'status.json', dict(phase='validating_upload', created_at=now(), gpu_used=False))
    try:
        uploaded_hash = sha(UPLOAD)
        page = UPLOAD.read_text()
        data, annotations = json.loads(script(page, 'data')), json.loads(script(page, 'annotations'))
        trusted = json.loads((TRUSTED / 'data.json').read_text())
        if data != trusted:
            raise ValueError('Uploaded source data differs from the trusted annotation export')
        assert annotations['schema'] == 'crossing-human-annotations-v1'
        assert annotations['dataset_id'] == data['dataset_id']
        assert set(annotations['cases']) == {c['episode_id'] for c in data['cases']}
        seen_ids = set()
        for c in data['cases']:
            seen_frames = set()
            for m in annotations['cases'][c['episode_id']]['marks']:
                uuid.UUID(m['id'])
                assert m['id'] not in seen_ids and m['frame'] not in seen_frames
                seen_ids.add(m['id']); seen_frames.add(m['frame'])
                assert type(m['frame']) is int and 0 <= m['frame'] < len(c['frames'])
                f = c['frames'][m['frame']]
                assert m['episode_id'] == c['episode_id'] and m['scene'] == c['scene'] and m['seed'] == 2
                assert m['type'] in ('crossing', 'wrong_choice') and not f['rgb_reused']
                for key in ('position', 'action_index', 'image_sha256', 'video_time_s'):
                    assert m[key] == f[key], (c['episode_id'], m['frame'], key)
                assert m['heading'] is None and m['heading_source'] == 'not_recorded'
        retained = [c for c in data['cases'] if annotations['cases'][c['episode_id']]['marks']]
        excluded = [dict(episode_id=c['episode_id'], scene=c['scene'], group=c['group'], reason='zero_human_annotations') for c in data['cases'] if not annotations['cases'][c['episode_id']]['marks']]
        assert len(retained) == 61 and len(excluded) == 8 and len(seen_ids) == 128
        frozen_id = NAME + '-' + uploaded_hash[:16]
        package = out / NAME
        package.mkdir()
        inputs, evaluation, events, viewer_cases, source_checks = [], [], [], [], []
        for i, c in enumerate(retained):
            eid = c['episode_id']
            for kind, relative in c['source'].items():
                assert sha(ROOT / relative) == c['source_sha256'][kind], (eid, kind)
            original_steps = [json.loads(line) for line in (ROOT / c['source']['steps']).read_text().splitlines() if line]
            assert len(original_steps) == len(c['frames'])
            urls = json.loads(script(page, 'media-' + eid))
            assert len(urls) == len(c['frames'])
            rgb_dir = package / 'rgb' / eid
            rgb_dir.mkdir(parents=True)
            frame_inputs, frame_evaluation = [], []
            for index, (f, original, url) in enumerate(zip(c['frames'], original_steps, urls)):
                assert f['frame'] == index
                assert all(f[key] == original[key] for key in original)
                assert url.startswith('data:image/webp;base64,')
                raw = base64.b64decode(url.split(',', 1)[1], validate=True)
                assert hashlib.sha256(raw).hexdigest() == f['image_sha256']
                assert raw[:4] == b'RIFF' and raw[8:12] == b'WEBP'
                relative = f'rgb/{eid}/F{index:04d}.webp'
                (package / relative).write_bytes(raw)
                previous = c['frames'][index - 1] if index else None
                newly_executed = [dict(frame=previous['frame'], action_index=previous['action_index'], action=previous['action'])] if previous and previous['action'] and not previous['terminal'] else []
                frame_inputs.append(dict(frame=index, action_index=f['action_index'], video_time_s=f['video_time_s'], rgb=relative,
                                         rgb_sha256=f['image_sha256'], rgb_reused=f['rgb_reused'], terminal=f['terminal'],
                                         eligible_for_inference=not f['rgb_reused'] and not f['terminal'], newly_executed_actions=newly_executed))
                frame_evaluation.append(dict(frame=index, position=f['position'], heading=None, action_after_observation=f['action']))
            observation_path = f'inputs/observations/{eid}.json'
            geometry_path = f'evaluation/trajectories/{eid}.json'
            write(package / observation_path, frame_inputs)
            write(package / geometry_path, dict(episode_id=eid, reference_path=c['reference_path'], frames=frame_evaluation))
            inputs.append(dict(episode_id=eid, seed=2, instruction=c['instruction'], instruction_zh=c['instruction_zh'], fps=c['fps'], observations=observation_path,
                               frame_count=len(frame_inputs), eligible_observation_count=sum(f['eligible_for_inference'] for f in frame_inputs)))
            marks = sorted(annotations['cases'][eid]['marks'], key=lambda m: m['frame'])
            episode_events = []
            for m in marks:
                event = dict(m, is_crossing=True, wrong_choice_marked=m['type'] == 'wrong_choice',
                             branch_choice_correctness='wrong' if m['type'] == 'wrong_choice' else 'unspecified',
                             rgb=frame_inputs[m['frame']]['rgb'], annotation_source='user_uploaded_html')
                episode_events.append(event)
                events.append(event)
            evaluation.append(dict(episode_id=eid, scene=c['scene'], group=c['group'], seed=2, episode_seed=c['episode_seed'],
                                   original_success=c['group'] == 'success', failed_seeds=c['failed_seeds'], trajectory=geometry_path,
                                   event_ids=[e['id'] for e in episode_events], crossing_count=len(marks), wrong_choice_count=sum(m['type'] == 'wrong_choice' for m in marks),
                                   source_completed_checkbox=annotations['cases'][eid]['completed'], accepted_basis='user_final_submission_and_nonempty_annotations'))
            viewer_cases.append(dict(episode_id=eid, scene=c['scene'], group=c['group'], instruction=c['instruction'], instruction_zh=c['instruction_zh'], reference_path=c['reference_path'], frames=c['frames'], events=episode_events))
            source_checks.append(dict(episode_id=eid, original_source=c['source'], original_source_sha256=c['source_sha256'], media_frames=len(urls)))
            write(out / 'status.json', dict(phase='extracting', completed=i+1, total=len(retained), gpu_used=False))
            if (i + 1) % 10 == 0:
                print(json.dumps(dict(episodes_written=i+1,total=len(retained))),flush=True)
        jsonl(package / 'inputs/episodes.jsonl', inputs)
        jsonl(package / 'evaluation/episodes.jsonl', evaluation)
        jsonl(package / 'evaluation/events.jsonl', events)
        write(package / 'evaluation/selection.json', dict(included=[c['episode_id'] for c in retained], excluded=excluded, rule='keep iff human mark count > 0'))
        maps = {}
        for scene, m in data['maps'].items():
            raw = base64.b64decode(m['image'].split(',',1)[1],validate=True)
            dest = package / 'evaluation/maps' / (scene + '.png')
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
            maps[scene] = dict(geometry=m['geometry'], image=str(dest.relative_to(package)), sha256=sha(dest))
        write(package / 'evaluation/maps.json', maps)
        write(package / 'provenance/annotation_snapshot.json', dict(annotations, cases={c['episode_id']:annotations['cases'][c['episode_id']] for c in retained}))
        write(package / 'provenance/sources.json', dict(upload_path=str(UPLOAD.relative_to(ROOT)), upload_sha256=uploaded_hash,
                                                      original_dataset_id=data['dataset_id'], source_export_manifest_sha256=sha(TRUSTED / 'manifest.json'), cases=source_checks))
        summary = dict(episodes=len(retained), failure_episodes=sum(c['group']=='failure' for c in retained), success_episodes=sum(c['group']=='success' for c in retained),
                       scenes=len({c['scene'] for c in retained}), crossing_events=len(events), ordinary_crossing_events=sum(e['type']=='crossing' for e in events),
                       wrong_choice_events=sum(e['type']=='wrong_choice' for e in events), episodes_with_wrong_choice=sum(e['wrong_choice_count']>0 for e in evaluation),
                       frames=sum(c['frame_count'] for c in inputs), eligible_observations=sum(c['eligible_observation_count'] for c in inputs),
                       excluded_episodes=len(excluded), frame_zero_events=sum(e['frame']==0 for e in events))
        write(package / 'summary.json', summary)
        with (package / 'evaluation/events.csv').open('w',encoding='utf-8-sig',newline='') as f:
            fields=['episode_id','frame','type','position_x','position_y','position_z','rgb','id'];writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
            for e in events:writer.writerow({**{k:e[k] for k in ('episode_id','frame','type','rgb','id')},**dict(zip(['position_x','position_y','position_z'],e['position']))})
        write(package / 'dataset.json', dict(schema='crossing-human-offline-v1', dataset_id=frozen_id, dataset_version='v001', created_at=now(), summary=summary,
                                            input_index='inputs/episodes.jsonl', event_labels='evaluation/events.jsonl', evaluation_index='evaluation/episodes.jsonl',
                                            input_rgb=dict(format='WebP',width=640,height=480,source='exact bytes displayed by the annotation HTML',reencoded=False),
                                            label_policy=dict(annotation_level='human-selected point events', wrong_choice_is_crossing=True, unmarked_frames='unlabeled, not automatically negative',
                                                              ordinary_crossing_branch_correctness='unspecified', completed_checkbox_is_filter=False, preserve_revisited_points=True),
                                            temporal_policy='Images <= current frame; executed actions < current frame. Recorded timestamps are replay time at 6fps, not physical time.',
                                            evaluation_only='Ground-truth annotations, maps, positions, reference paths and outcomes; never include these in detector inputs.',
                                            train_dev_test_split=None, matching_tolerance=None, source_upload_sha256=uploaded_hash))
        shutil.copy2(ROOT / 'core/offline_crossing_dataset.py', package / 'offline_dataset.py')
        shutil.copy2(ROOT / 'scripts/verify_crossing_dataset.py', package / 'verify_dataset.py')
        viewer = dict(dataset_id=frozen_id, dataset_version='v001', summary=summary, cases=viewer_cases, maps=data['maps'], font_license=data['font_license'])
        template = (ROOT / 'core/crossing_dataset_review.html').read_text()
        controller = (ROOT / 'core/crossing_dataset_review.js').read_text()
        # Rebuild the Chinese font subset to cover this viewer's captions as well as all instructions.
        font_cfg = json.loads((ROOT / 'core/crossing_visualization_template.json').read_text())
        chars = out / 'font_characters.txt';chars.write_text(''.join(sorted(set(template + controller + compact(viewer)))))
        font = out / 'review_font.ttf'
        code = 'from fontTools import subset; from fontTools.ttLib import TTFont; from pathlib import Path; import sys; f=TTFont(sys.argv[1],fontNumber=0); s=subset.Subsetter(); s.populate(text=Path(sys.argv[2]).read_text()); s.subset(f); f.save(sys.argv[3])'
        subprocess.run([str(ROOT/'backbone/streamvln/.venv/bin/python'),'-c',code,font_cfg['font'],str(chars),str(font)],check=True)
        html = template.replace('__FONT__','data:font/ttf;base64,'+base64.b64encode(font.read_bytes()).decode()).replace('__DATA__',compact(viewer)).replace('__SCRIPT__',controller)
        head,tail=html.split('__MEDIA__');viewer_path=package/(NAME+'_offline.html')
        with viewer_path.open('w') as f:
            f.write(head)
            for c in retained:f.write('<script id="media-'+c['episode_id']+'" type="application/json">'+script(page,'media-'+c['episode_id'])+'</script>\n')
            f.write(tail)
        readme = f'''# Crossing 人工标注离线数据集 v001

本数据集来自用户提交的seed2标注。按“零标注剔除”收录{summary['episodes']}条（{summary['failure_episodes']}失败、{summary['success_episodes']}成功），剔除{summary['excluded_episodes']}条。
共{summary['crossing_events']}个Crossing点，其中{summary['ordinary_crossing_events']}个普通Crossing、{summary['wrong_choice_events']}个错误选择Crossing；错误选择也属于Crossing。完整录像序列{summary['frames']}帧，可推理观测{summary['eligible_observations']}帧。

## 离线查看

直接用Chrome或Edge打开 `{NAME}_offline.html`。图片、中文指令、地图和人工点全部内嵌。该文件只读，点击标注点或按钮即可跳到用户标定帧；不需要网络、模型或服务器。

## 文件

- `inputs/episodes.jsonl`：61条任务的英文原指令、中文译文与相对路径。
- `inputs/observations/*.json`：逐帧RGB索引、终止/复用标记，以及在当前帧之前刚刚执行的动作。
- `rgb/<episode>/F0000.webp`：用户标注时实际看到的640×480图像，逐字节复用，不再次压缩。来自原始H.264录像解码裁剪后的WebP质量90，不是原传感器无损图。
- `evaluation/events.jsonl`、`events.csv`：128个人工点，保留原UUID、帧号、坐标、类型和图像哈希。
- `evaluation/episodes.jsonl`、`trajectories/`、`maps/`：仅用于评估的成功/失败、参考路线、真实轨迹和俯视图。
- `evaluation/selection.json`：保留清单和8条零标注的排除记录，不包含排除任务的图像。
- `provenance/`：用户原始标签快照、来源路径和SHA256；原HTML保存在服务器原位置。
- `dataset.json`、`summary.json`、`checksums.json`：版本、标签口径、统计与文件校验。

## 读取（Python标准库即可）

在本目录运行：

```python
from offline_dataset import episodes, iter_observations
root = "."
episode = episodes(root)[0]
for sample in iter_observations(root, episode["episode_id"], image_history=8, action_history=32):
    # sample包含当前与过去图像路径、严格早于当前观测的动作、中英指令。
    print(sample["frame"], sample["images"][-1]["path"])
```

历史窗口是调用方参数，不是本数据集强制的算法配置。模型输入不能携带evaluation下的标签、GPS、地图、参考路线、最终结果或未来画面。帧0的标注照常保留，不伪造此前历史。

## 标签与使用范围

以用户提交为准；不吸附旧地图点，不按空间距离合并多次经过。页面completed复选框均未勾选，用户已明确提交完成，因此按有无标注收录，原复选框值留在provenance中。
未标帧保持未标注，不自动生成负类；普通Crossing未标错误也不等于已明确确认选路正确。匹配容差和train/dev/test划分尚未设定，不将旧几何标签的1米口径自动套用到人工点。
数据覆盖10个既有复现场景，不能声称是与历史开发集场景独立的验证集。轨迹坐标为原始world x/y/z（水平面x/y，单位米）；原档案未保存朝向，heading=null。时间是6fps回放时间，不是物理仿真时长。

## 完整性校验

在数据集目录运行 `python verify_dataset.py --dataset .`；无需模型、GPU、网络或第三方Python包。
本次只制作数据集，没有运行测评或产生方法分数。
'''
        (package/'README.md').write_text(readme)
        assert sha(UPLOAD)==uploaded_hash,'User upload changed while building'
        source_hashes={}
        for rel in ['scripts/build_crossing_dataset.py','scripts/verify_crossing_dataset.py','core/offline_crossing_dataset.py','core/crossing_dataset_review.html','core/crossing_dataset_review.js','experiments/crossing_dataset/seed2_human_v001/README.md']:
            dest=out/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dest);source_hashes[rel]=sha(dest)
        (out/'workspace_status.txt').write_bytes(subprocess.check_output(['git','status','--short'],cwd=ROOT));(out/'workspace_diff.patch').write_bytes(subprocess.check_output(['git','diff','HEAD','--binary'],cwd=ROOT))
        write(package/'manifest.json',dict(dataset_id=frozen_id,created_at=now(),source_upload_sha256=uploaded_hash,source_export_manifest_sha256=sha(TRUSTED/'manifest.json'),
                                          export_git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_sha256=source_hashes,summary=summary))
        write(package/'checksums.json',{str(p.relative_to(package)):sha(p) for p in sorted(package.rglob('*')) if p.is_file()})
        archive=out/(NAME+'.zip')
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for p in sorted(package.rglob('*')):
                if p.is_file():z.write(p,str(Path(NAME)/p.relative_to(package)))
        write(out/'archive.json',dict(path=archive.name,sha256=sha(archive),bytes=archive.stat().st_size,dataset_id=frozen_id))
        write(out/'summary.json',summary);write(EXP/'summary.json',summary);write(EXP/'selection.json',dict(included=[c['episode_id'] for c in retained],excluded=excluded))
        write(out/'status.json',dict(phase='built_pending_validation',finished_at=now(),summary=summary,gpu_used=False,model_calls=0))
        print(json.dumps(dict(package=str(package),html=str(viewer_path),zip=str(archive),**summary),ensure_ascii=False),flush=True)
    except BaseException as exc:
        write(out/'status.json',dict(phase='failed',error=str(exc),updated_at=now(),gpu_used=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    build(parser.parse_args().output.resolve())
