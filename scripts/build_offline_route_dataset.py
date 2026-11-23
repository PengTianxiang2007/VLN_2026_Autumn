"""Package explicitly reviewed route-choice failures; never run navigation.

Semantic decisions come only from the reviewed TSV, not distance thresholds.
Images are hardlinked, never modified. SHA256 for auxiliary images is inherited
from the completed source audit, with source mtime and inode checks at packaging.
Native-front images and new metadata are hashed during packaging.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import copy
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Lock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.offline_route_dataset import OfflineRouteDataset

STRICT = {'missed_turn', 'wrong_doorway', 'wrong_branch'}
NAMES = dict(missed_turn='漏掉应有转弯', wrong_doorway='选错房门',
             wrong_branch='选择错误通路分支', wrong_open_area_direction='开放区域方向错误',
             wrong_initial_direction='初始行进方向错误')


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def wrap(angle):
    return (angle + 180) % 360 - 180


def reference_direction(case, record, lookahead=1.25):
    """Evaluation-only reference geometry, not a validated feasible action."""
    step = record['step']; points = case['reference_path']
    arc = case['nearest_reference_arc_m'][step]
    target_arc = min(arc + lookahead, case['features']['reference_length_m'])
    traversed = 0.; target = points[-1]
    for a, b in zip(points, points[1:]):
        length = math.hypot(b[0]-a[0], b[1]-a[1])
        if length > 1e-10 and traversed + length >= target_arc:
            t = (target_arc - traversed)/length
            target = [x + t*(y-x) for x, y in zip(a, b)]
            break
        traversed += length
    position = record['robot_pose']['position_world_m']
    dx, dy = target[0]-position[0], target[1]-position[1]
    bearing = math.degrees(math.atan2(dy, dx)) if math.hypot(dx, dy) > 1e-8 else None
    relative = wrap(bearing-record['robot_pose']['heading_deg']) if bearing is not None else None
    return dict(definition='bearing from recorded robot XY to reference arc+1.25m',
                reference_projection_arc_m=arc, lookahead_m=lookahead, target_arc_m=target_arc,
                target_world_m=target, world_heading_deg=bearing, relative_to_current_robot_deg=relative,
                nearest_360_view_id=min(range(8), key=lambda i: abs(wrap(relative-i*45))) if relative is not None else None,
                feasible_action_validated=False)


def annotate(cases, notes, evidence):
    by_number = {int(x['number']): x for x in notes}
    assert len(by_number) == len(notes) == len(cases) == 69
    assert set(by_number) == set(range(1,70))
    result=[]
    for c in cases:
        n=by_number[c['number']]; assert n['decision'] in ('include','exclude','uncertain')
        records=[json.loads(x) for x in Path(c['steps_source']).read_text().splitlines()]
        visual=evidence[c['episode_id']]; viewed=sorted({s for v in visual for s in v['steps']})
        events=[]
        if n['events_lower_anchor_confirm'] != '-':
            for k,item in enumerate(n['events_lower_anchor_confirm'].split(';'),1):
                lower,anchor,confirm=map(int,item.split(','))
                assert 0 <= lower <= anchor < confirm < len(records)
                assert anchor in viewed and confirm in viewed, (c['episode_id'],anchor,confirm,viewed)
                a,b=records[anchor],records[confirm]
                delta=[y-x for x,y in zip(a['robot_pose']['position_world_m'],b['robot_pose']['position_world_m'])]
                displacement=math.hypot(*delta[:2]);assert displacement > .1
                actual=math.degrees(math.atan2(delta[1],delta[0]))
                events.append(dict(event_id=f"{c['episode_id']}:e{k:02d}",
                    event_index=k,decision_step_estimate=anchor,decision_interval_steps=[lower,confirm],
                    confirmed_wrong_step=confirm,interval_is_uncertainty=True,
                    decision_robot_pose=a['robot_pose'],decision_native_camera_pose=a['native_camera_pose'],
                    confirmation_robot_pose=b['robot_pose'],confirmation_native_camera_pose=b['native_camera_pose'],
                    decision_simulation_time_s=a['simulation_time_s'],confirmation_simulation_time_s=b['simulation_time_s'],
                    reference_direction=reference_direction(c,a),
                    actual_departure=dict(from_step=anchor,to_step=confirm,displacement_xy_m=displacement,
                        world_heading_deg=actual,relative_to_decision_robot_deg=wrap(actual-a['robot_pose']['heading_deg'])),
                    confidence=n['confidence'],subtype=n['subtype'],
                    failure_association='supported_offline_association' if n['decision']=='include' else 'uncertain',
                    reason_zh=n['reason_zh']))
        if n['decision']=='include':assert events
        result.append(dict(number=c['number'],episode_id=c['episode_id'],scene=c['scene'],source_batch=c['source_batch'],
            decision=n['decision'],selected=n['decision']=='include',
            subset=('branch_core' if n['subtype'] in STRICT else 'direction_extension') if n['decision']=='include' else n['decision'],
            subtype=n['subtype'],subtype_zh=NAMES.get(n['subtype'],n['subtype']),confidence=n['confidence'],
            reason_zh=n['reason_zh'],native_termination=c['score']['fail_reason'],native_metrics=c['score'],
            annotation_author='Codex',annotation_method='offline_trajectory_and_keyframe_review',
            human_consensus=False,counterfactual_causality_proven=False,
            reviewed_observation_steps=viewed,visual_evidence=visual,map='review/'+c['map'],events=events))
    return result


class Bundle:
    def __init__(self, root, proof_mtime_ns):
        self.root=root;self.proof_mtime_ns=proof_mtime_ns
        self.hashes={};self.counts=Counter();self.unique_sizes={}
        self.lock=Lock();self.pool=ThreadPoolExecutor(max_workers=8)

    def text(self, relative, text):
        p=self.root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
        self.hashes[relative]=sha(p)

    def json(self, relative, value):
        self.text(relative,json.dumps(value,ensure_ascii=False,indent=2)+'\n')

    def jsonl(self, relative, values):
        self.text(relative,''.join(json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n' for v in values))

    def copy(self, source, relative):
        p=self.root/relative;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,p)
        self.hashes[relative]=sha(p)

    def image(self, source, relative, expected_sha=None, kind='auxiliary', alias_of=None):
        source=Path(source);stat=source.stat()
        assert stat.st_mtime_ns <= self.proof_mtime_ns, ('modified after source validation',source)
        if alias_of is not None:
            alias_stat=Path(alias_of).stat()
            assert (stat.st_dev,stat.st_ino)==(alias_stat.st_dev,alias_stat.st_ino)
        p=self.root/relative
        try:
            os.link(source,p)  # successful link(2) establishes identical inode atomically
        except FileExistsError:
            other=p.stat();assert (stat.st_dev,stat.st_ino)==(other.st_dev,other.st_ino)
        digest=expected_sha or sha(p)
        with self.lock:
            self.hashes[relative]=digest
            self.counts[kind]+=1;self.counts['image_path_bytes']+=stat.st_size
            self.unique_sizes[(stat.st_dev,stat.st_ino)]=stat.st_size
        return digest

    def images(self,jobs):
        list(self.pool.map(lambda job:self.image(**job),jobs))


def build(analysis, notes_path, source, resume=False):
    cases=read(analysis/'cases.json');audit=read(analysis/'source_audit.json')
    proof=read(source/'capture_validation.json');assert proof['passed']
    source_manifest=read(source/'manifest.json');source_cases={c['episode_id']:c for c in source_manifest['cases']}
    evidence={c['episode_id']:[] for c in cases}
    for filename in ('visual_evidence.json','refine_evidence.json'):
        for e in read(analysis/filename):
            # These cards were inspected in the recorded assistant review turn.
            value=copy.deepcopy(e);value['file']='review/visual/'+Path(e['file']).name
            evidence[e['episode_id']].append(value)
    with notes_path.open() as f:notes=list(csv.DictReader(f,delimiter='\t'))
    labels=annotate(cases,notes,evidence);selected=[x for x in labels if x['selected']]
    signature=dict(notes_sha256=sha(notes_path),cases_sha256=sha(analysis/'cases.json'),
        source_validation_sha256=sha(source/'capture_validation.json'),source_manifest_sha256=sha(source/'manifest.json'))
    target=analysis/'dataset';building=analysis/'dataset.building'
    if target.exists():raise FileExistsError('Completed bundle already exists; use a new run')
    if building.exists():
        if not resume or read(building/'BUILDING.json') != signature:raise FileExistsError('Partial bundle signature mismatch or --resume missing')
    else:
        building.mkdir();(building/'BUILDING.json').write_text(json.dumps(signature,indent=2)+'\n')
    bundle=Bundle(building,(source/'capture_validation.json').stat().st_mtime_ns)
    cases_by_id={c['episode_id']:c for c in cases};checks=[];steps_total=0
    # Reconfirm all reviewed source metadata against the initial read-only audit.
    for c in cases:
        assert sha(c['steps_source'])==audit['files_sha256'][c['steps_source']]
    for label in selected:
        eid=label['episode_id'];c=cases_by_id[eid]
        records=[json.loads(s) for s in Path(c['steps_source']).read_text().splitlines()]
        assert len(records)==c['features']['actions']+1 and records[-1]['terminal']
        assert all(r['step']==i and r['terminal']==(i==len(records)-1) for i,r in enumerate(records))
        inputs=[];actions=[];capture=[]
        for t,r in enumerate(records):
            assert r['frozen_state_verified'] and r['physics_ticks_during_capture']==0
            assert r['auxiliary_visibility']['restored']
            assert r['physical_state_before']==r['physical_state_after']
            assert r['robot_pose']['position_world_m']==c['pred_path'][t]
            assert r['robot_pose']['heading_deg']==c['headings_deg'][t]
            assert len(r['views_360'])==8 and len(r['views_180'])==3
            assert [v['view_id'] for v in r['views_180']]==[1,0,7]
            prefix=f'observations/{eid}/{t:06d}'
            for suffix in ('360','180'):
                (building/prefix/suffix).mkdir(parents=True,exist_ok=True)
            directory=Path(r['frame_directory']);views=[]
            jobs=[]
            for i,v in enumerate(r['views_360']):
                assert v['view_id']==i and abs(wrap(v['relative_yaw_deg']-45*i))<1e-8
                assert abs(wrap(v['camera_pose']['heading_deg']-r['robot_pose']['heading_deg']-v['relative_yaw_deg']))<.001
                name=prefix+'/'+v['image']
                jobs.append(dict(source=directory/v['image'],relative=name,expected_sha=v['sha256']))
                views.append({**v,'image':name})
            front_name=prefix+'/'+r['front_image']
            jobs.append(dict(source=directory/r['front_image'],relative=front_name,kind='native_front'))
            half=[]
            for v in r['views_180']:
                same=views[v['view_id']];name=prefix+'/'+v['image']
                jobs.append(dict(source=directory/v['image'],relative=name,expected_sha=same['sha256'],kind='alias_180',
                    alias_of=directory/r['views_360'][v['view_id']]['image']))
                half.append({**same,'image':name})
            bundle.images(jobs)
            front=dict(image=front_name,sha256=bundle.hashes[front_name],camera_pose=r['native_camera_pose'],
                relative_yaw_deg=wrap(r['native_camera_pose']['heading_deg']-r['robot_pose']['heading_deg']))
            inputs.append(dict(episode_id=eid,step=t,simulation_time_s=r['simulation_time_s'],
                episode_elapsed_s=r['simulation_time_s']-records[0]['simulation_time_s'],
                physics_ticks=r['physics_ticks'],robot_pose=r['robot_pose'],native_camera_pose=r['native_camera_pose'],
                calibration=r['calibration'],previous_action=records[t-1]['action'] if t else None,
                native_front=front,views_180=half,views_360=views))
            actions.append(dict(step=t,action=r['action'],terminal=r['terminal']))
            raw=copy.deepcopy(r);raw['frame_directory']=prefix
            capture.append(raw)
        task={k:source_cases[eid][k] for k in ('episode_id','scene','seed','episode_seed')}
        task['instruction']=c['instruction']
        bundle.json(f'inputs/{eid}/task.json',task)
        bundle.jsonl(f'inputs/{eid}/observations.jsonl',inputs)
        bundle.jsonl(f'evaluation/actions/{eid}.jsonl',actions)
        bundle.jsonl(f'provenance/capture_records/{eid}.jsonl',capture)
        bundle.json(f'evaluation/episodes/{eid}.json',dict(annotation=label,reference_path=c['reference_path'],
            actual_path=c['pred_path'],route_distances_m=c['route_distances_m'],
            nearest_reference_arc_m=c['nearest_reference_arc_m'],goal_distances_m=c['goal_distances_m']))
        # Reader checks across the whole episode catch current/future-action leakage.
        reader=OfflineRouteDataset(building)
        for t in sorted({0,len(records)-1,*[e['decision_step_estimate'] for e in label['events']]}):
            context=reader.context(eid,t,'180');assert len(context['observations'])==t+1
            last=context['observations'][-1];assert last['step']==t
            assert last['previous_action']==(records[t-1]['action'] if t else None)
            assert 'action' not in last and 'reference_path' not in last
            assert [v['relative_yaw_deg'] for v in last['views']]==[45,0,-45]
        steps_total+=len(records)
        checks.append(dict(episode_id=eid,observations=len(records),pose_and_heading_equal=True,
            source_capture_metadata_sha256=sha(c['steps_source']),frozen_physics=True,relative_views_correct=True,
            portable_paths_and_hardlink_identity=True,causal_reader_checked=True))
        print(f"PACKAGED {len(checks)}/{len(selected)} {eid} {len(records)} steps",flush=True)
    bundle.pool.shutdown(wait=True)
    # All 69 classifications remain reviewable, including exclusions and uncertainty.
    bundle.json('evaluation/all69_classifications.json',labels)
    all_geometry=[{k:c[k] for k in ('number','episode_id','scene','instruction','pred_path','reference_path',
        'headings_deg','features','candidate_events')} for c in cases]
    bundle.json('evaluation/all69_geometry.json',all_geometry)
    table=io.StringIO();writer=csv.writer(table)
    writer.writerow(['number','episode_id','source_batch','decision','subset','subtype','confidence','native_termination','events','reason_zh'])
    for x in labels:writer.writerow([x[k] for k in ('number','episode_id','source_batch','decision','subset','subtype','confidence','native_termination')]+[len(x['events']),x['reason_zh']])
    bundle.text('evaluation/classification.csv',table.getvalue())
    for c in cases:
        bundle.copy(analysis/c['map'],'review/'+c['map'])
        for e in evidence[c['episode_id']]:bundle.copy(analysis/'visual'/Path(e['file']).name,e['file'])
    bundle.copy(notes_path,'provenance/review_notes.tsv')
    bundle.copy(analysis/'source_audit.json','provenance/source_audit.json')
    bundle.copy(source/'capture_validation.json','provenance/original_capture_validation.json')
    bundle.copy(source/'manifest.json','provenance/original_run_manifest.json')
    for p in [Path(__file__),ROOT/'core/offline_route_dataset.py',ROOT/'scripts/prepare_multiview_failure_review.py',
              ROOT/'scripts/analyze_oracle_baseline_failures.py',ROOT/'tests/test_offline_route_dataset.py']:
        bundle.copy(p,'code/'+p.name)
    # Reader is also importable directly from a moved standalone directory.
    bundle.copy(ROOT/'core/offline_route_dataset.py','offline_route_dataset.py')
    strict=[x['episode_id'] for x in selected if x['subset']=='branch_core']
    extension=[x['episode_id'] for x in selected if x['subset']=='direction_extension']
    for name,ids in [('all_selected',[x['episode_id'] for x in selected]),('branch_core',strict),('direction_extension',extension)]:
        bundle.text('subsets/'+name+'.txt',''.join(x+'\n' for x in ids))
    summary=dict(reviewed_failures=len(labels),selected=len(selected),excluded=sum(x['decision']=='exclude' for x in labels),
        uncertain=sum(x['decision']=='uncertain' for x in labels),branch_core=len(strict),direction_extension=len(extension),
        selected_events=sum(len(x['events']) for x in selected),scenes=len({x['scene'] for x in selected}),
        selected_by_source_batch=dict(Counter(x['source_batch'] for x in selected)),
        selected_by_subtype=dict(Counter(x['subtype'] for x in selected)),
        observations=steps_total,navigation_actions=steps_total-len(selected),
        multiview_unique_png=bundle.counts['auxiliary'],native_front_png=bundle.counts['native_front'],
        aliases_180=bundle.counts['alias_180'],unique_png_files=len(bundle.unique_sizes),
        unique_png_bytes=sum(bundle.unique_sizes.values()),logical_png_paths=sum(bundle.counts[k] for k in ('auxiliary','native_front','alias_180')),
        logical_png_path_bytes=bundle.counts['image_path_bytes'])
    manifest=dict(schema_version='offline_route_choice_v1',created_at=datetime.now(timezone.utc).isoformat(),
        dataset_id='route_choice_multiview53_seed2_20261118_v001',summary=summary,source_signature=signature,
        source_run='multiview_capture/v001/run_20261117_03',source_capture_git_head=source_manifest['git_head'],
        packaging_git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        packaging_worktree_dirty=True,annotation_author='Codex',human_annotation=False,
        annotation_scope='all 69 full XY trajectories plus selected native-front and auxiliary keyframes; not every RGB frame',
        historical_labels_used_as_answers=False,new_navigation_runs=0,new_model_calls=0,
        data_split=None,coordinate_convention=dict(world='+Z up; horizontal XY; meters',quaternion_order='wxyz',
            robot_forward='+X',camera_forward='-Z (USD)',heading='atan2(forward_y,forward_x), degrees',
            view_offset='relative to measured robot heading; positive left',
            view_360_offsets_deg=[0,45,90,135,-180,-135,-90,-45],view_180_offsets_deg=[45,0,-45],
            resolution=[640,480],horizontal_fov_deg=90),
        policy_input_at_capture='native front only',auxiliary_robot_visibility='robot visual geometry hidden, then restored',
        behavior_equivalent_to_capture_disabled_proven=False,
        observation_boundary='t is before action a_t; final t=N is terminal after a_(N-1)',
        reference_direction_is_executable_oracle=False,
        paths=dict(inputs='inputs/',images='observations/',evaluation='evaluation/',review='review/',
            provenance='provenance/',checksums='SHA256SUMS',validation='validation.json'),
        image_storage='hardlinks to immutable source; preserve links when archiving, never edit PNGs in place',
        image_hash_verification='auxiliary: inherited complete source SHA256 proof + mtime + inode identity; native fronts: freshly hashed')
    bundle.json('manifest.json',manifest)
    validation=dict(passed=True,checks=checks,summary=summary,all69_metadata_matches_initial_audit=True,
        all_selected_decision_and_confirmation_frames_were_reviewed=True,
        original_capture_validation_passed=True,auxiliary_png_content_rehashed_this_run=False,
        auxiliary_verification='source complete hash validation, unchanged mtime, same source/destination inode',
        native_front_content_rehashed_this_run=True,
        no_model_or_simulator_access=True,completed_at=datetime.now(timezone.utc).isoformat())
    bundle.json('validation.json',validation)
    readme=f'''# 选路错误离线数据集 v001

本轮104条重采集任务中35条成功、69条失败。本包对69条失败逐条审核，纳入53条（早期48来源25条、新56来源28条），排除13条，归因不确定3条。人工33条标注集没有参与本次筛选。

53条分为两个可单独使用的子集：明确门口/走廊分支及漏转弯43条，开放区域/初始方向错误10条。主集共有54个标定事件；事件不等于独立任务。所有标签为Codex事后离线审核，非人工共识、非干预后的因果证明；逐条查看完整轨迹和关键帧，未逐帧审阅全部RGB。

## 数据与入口

- `manifest.json`：协议、坐标约定、来源、计数。
- `subsets/all_selected.txt`、`branch_core.txt`、`direction_extension.txt`：53/43/10条索引。
- `inputs/<episode_id>/task.json`：原始英文指令、场景和seed，原文未改写。
- `inputs/<episode_id>/observations.jsonl`：全部{steps_total}个动作边界观测（含初始和终止）、真实机器人与相机XYZ/完整wxyz四元数/朝向、仿真时间，以及上一步动作。
- `observations/<episode_id>/<step>/`：原生前视、360度八视图、180度三视图，均为原始PNG。
- `evaluation/`：69条分类/排除理由、每条入选任务的参考路线、轨迹、当前动作及事件标签。
- `review/`：全部69条轨迹图与关键帧审核图；`provenance/`保留原始采集元数据、来源审计和审核笔记。
- `validation.json`、`SHA256SUMS`：完整性检查和迁移后校验清单。

## 观测、位姿和时间

世界坐标为XY水平面、Z向上，单位米；机器人+X向前，相机USD坐标-Z向前、+Y向上。heading由前向向量在世界XY平面的atan2计算，单位度，不能拿相机欧拉yaw替代heading。完整四元数按wxyz顺序保存。

360度视图相对该step真实机器人朝向依次为0、45、90、135、-180、-135、-90、-45度；180度按左前/正前/右前排列，为45、0、-45度。每张水平视场90度、640×480；180度与360度是独立透视图集合，没有拼接或拉伸，三视图复用八视图对应PNG。原生前视与辅助0度视图分别保存，原生相机朝向可与机器人有小差异。

step t在动作a_t前；最后一条t=N是执行a_(N-1)后的终止观测。输入只包含previous_action=a_(t-1)，t=0为空；当前及未来动作在evaluation中。仿真时间原值与每任务相对秒数均保留，不能拿采集墙钟耗时当导航物理耗时。

## 离线读取

在本目录下用标准Python即可，无需模型、仿真或网络：

```python
from offline_route_dataset import OfflineRouteDataset
ds = OfflineRouteDataset('.')
eid = ds.episode_ids()[0]
context = ds.context(eid, step=10, mode='180')  # 可选front/180/360
assert context['observations'][-1]['step'] == 10
```

读取器只访问inputs，不加载evaluation/provenance；每次仅返回0至t的指定视图与过去动作。不要把evaluation中的未来轨迹、参考路线、事件答案作为在线方法输入。无预设训练/验证划分，同场景多指令共享几何；以后划分应显式记录协议。

## 标定口径

纳入有轨迹和视觉证据的错误门、错误分支、漏转弯、开放区域/初始方向错误；终止方式单列。单纯回返、局部无效动作、未走完停止、无选路证据的跌倒/卡住排除。3条待复核为0036_43_0（局部转动与方向错误难分）、0159_50_0（错误进入后回正再卡住）、0285_2_3（末段偏离与失稳交织）；ID均有kujiale_前缀。

每个事件有代表性decision_step_estimate、包含不确定性的decision_interval_steps、已能确认错误的confirmed_wrong_step和相应完整位姿/朝向。区间不是逐帧精确真值。几何距离0.75米仅用于提出审阅窗口，不是自动标签。reference_direction是从记录位置朝参考路径投影弧长再前移1.25米点的方位估计，含相对当前朝向角；它没有经过碰撞/可达性验证，不是可直接执行的Oracle动作。actual_departure为决策帧至确认帧的实际水平位移方向。

## 存储与核验

本包共{summary['unique_png_files']}张独立PNG（{summary['multiview_unique_png']}张多视角、{summary['native_front_png']}张前视），另有{summary['aliases_180']}个180度路径别名。PNG独立内容合计{summary['unique_png_bytes']/1024**3:.3f} GiB；忽略硬链接复制所有路径时PNG为{summary['logical_png_path_bytes']/1024**3:.3f} GiB，另加元数据与审核图。

当前目录以硬链接复用已完成校验的原图，未压缩/改写图片；不依赖外部软链接，完整复制本目录即可搬迁。不得原位改写PNG（会影响共享原图）；要加工请先复制成新文件。归档建议使用保留硬链接的tar，迁移后在本目录运行`sha256sum -c SHA256SUMS`。

辅助图复用原运行全量SHA256验证，并逐图检查未晚于该验证的修改时间及与源文件inode一致；本次没有再次全量读回辅助PNG。原生前视和本次元数据重新计算SHA256。所有入选step检查图像路径、位姿、相对角度、180/360对应、物理冻结和因果读取边界。

## 来源与限制

原采集运行：multiview_capture/v001/run_20261117_03，seed=2，原版StreamVLN仅用前视、无Oracle干预。本包是该轮新的在线多视角采集轨迹，不能视为旧失败轨迹的重建。辅助采集没有推进物理状态，且隐藏机器人外观后恢复，但与模型前视共用渲染流程；尚未证明与完全关闭辅助采集的导航行为等价。输入图片可能含遮挡、过曝、贴墙或跌倒帧，全部保留。

历史归因只用于追溯两批样本来源，没有直接继承为本轮答案。没有启动模型评测、导航或纠正实验，没有操作保留模型/仿真。绝对历史路径只出现在provenance审计中，读取本包不依赖这些路径。
'''
    bundle.text('README.md',readme)
    bundle.text('SHA256SUMS',''.join(f'{digest}  {name}\n' for name,digest in sorted(bundle.hashes.items())))
    # Ensure the source proofs did not change while packaging.
    assert sha(source/'capture_validation.json')==signature['source_validation_sha256']
    assert sha(notes_path)==signature['notes_sha256']
    (building/'BUILDING.json').unlink()  # only our own temporary sentinel
    building.rename(target)
    (analysis/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(dataset=str(target),summary=summary),ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis',type=Path,required=True);p.add_argument('--notes',type=Path,required=True)
    p.add_argument('--source',type=Path,default=ROOT/'outputs/multiview_capture/v001/run_20261117_03')
    p.add_argument('--resume',action='store_true');a=p.parse_args()
    build(a.analysis.resolve(),a.notes.resolve(),a.source.resolve(),a.resume)
