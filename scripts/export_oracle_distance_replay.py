"""Export completed distance-Oracle results and historical trajectories, CPU only."""
import argparse
import base64
import hashlib
import io
import json
import math
import re
import shutil
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def deviation(p, reference):
    result = float('inf')
    for a, b in zip(reference, reference[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        den = dx * dx + dy * dy
        t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / den)) if den else 0
        result = min(result, math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy))
    return result


def yaw(q):
    if not q:
        return None
    w, x, y, z = q
    return math.atan2(2 * (w*z + x*y), 1 - 2 * (y*y + z*z))


def action_code(action):
    if not action:
        return -1
    return 0 if 'stop' in action else action.get('move_by_discrete', [-1])[0]


def add_font(output):
    """Embed an existing CJK font subset so headless/mobile readers render Chinese."""
    from fontTools import subset
    from fontTools.ttLib import TTFont
    config = read(ROOT/'core/crossing_visualization_template.json')
    html = output.read_text()
    font = TTFont(config['font'], fontNumber=0)
    subsetter = subset.Subsetter()
    subsetter.populate(text=''.join(sorted(set(re.findall(r'[^\x00-\x7f]', html)))) + ''.join(chr(i) for i in range(32,127)))
    subsetter.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    css = '<style id="embedded-font">@font-face{font-family:OracleSans;src:url(data:font/ttf;base64,' + base64.b64encode(buf.getvalue()).decode() + ')}body,button,select,input,svg text{font-family:OracleSans,system-ui,sans-serif}</style>'
    assert 'id="embedded-font"' not in html
    output.write_text(html.replace('</head>',css+'</head>',1))
    shutil.copy2(config['font_license'],output.parent/'FONT_LICENSE.txt')
    return dict(font_source_sha256=sha(config['font']),font_license_sha256=sha(config['font_license']))


class Media:
    def __init__(self):
        self.jobs = []
        self.index = {}

    def add(self, path, width=480):
        path = Path(path).resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        key = (str(path), width)
        if key not in self.index:
            self.index[key] = len(self.jobs)
            self.jobs.append(key)
        return self.index[key]

    def encode(self):
        from PIL import Image

        def convert(job):
            path, width = job
            with Image.open(path) as source:
                image = source.convert('RGB')
                if width:
                    image.thumbnail((width, width), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                image.save(buf, 'WEBP', quality=80 if width else 92, method=3)
            return 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode()

        with ThreadPoolExecutor(max_workers=4) as pool:
            return list(pool.map(convert, self.jobs))


def trace(result_path, case, media, arm='early'):
    result = read(result_path)
    assert result['status'] == 'complete' and result['arm'] == arm
    attempts = [p.parent for p in result_path.parent.glob('attempt_*/result.json') if read(p) == result]
    if len(attempts) != 1:
        raise ValueError(('Ambiguous completed attempt', result_path, attempts))
    attempt = attempts[0]
    checkpoint = arm == 'checkpoint'
    action_rows = rows(attempt/'actions.jsonl')
    actions = {r['sequence'] if checkpoint else r['action_index']: r['action'] for r in action_rows}
    observations = rows(attempt/'observations.jsonl')
    interventions = result['interventions']
    by_action = {v['action_index']: (i, v) for i, v in enumerate(interventions)}
    assert len(by_action) == len(interventions)
    nodes, events, used = [], [], set()
    segment = 0
    for obs in observations:
        a = obs['action_index']
        action = actions.get(obs['sequence'] if checkpoint else a)
        missing_rgb = not Path(obs['frame']).is_file()
        if missing_rgb and (not obs['terminal'] or not nodes):
            raise FileNotFoundError(obs['frame'])
        frame_index = nodes[-1]['image'] if missing_rgb else media.add(obs['frame'])
        node = dict(p=obs['position'], yaw=yaw(obs['rotation']), a=a, ticks=obs['physics_ticks'],
                    image=frame_index, segment=segment,
                    phase='end' if obs['terminal'] else 'walk', action=action_code(action),
                    distance=obs['distance_m'], reused=missing_rgb)
        nodes.append(node)
        if a in by_action and a not in used and not obs['terminal']:
            i, iv = by_action[a]
            assert math.dist(obs['position'], iv['before_position']) < 1e-5
            directory = attempt / ('correction_%03d' % (i+1))
            assert read(directory/'intervention.json') == iv
            if checkpoint:
                proof = read(iv['restore_proof'])
                assert Path(proof['source']).parent.resolve() == attempt.resolve()
                saved = read(Path(proof['source']).with_suffix('.json'))
                assert proof['policy']['verified'] and saved['policy']['verified']
                assert proof['policy']['content_sha256'] == saved['policy']['content_sha256']
                assert proof['accounting_before_sha256'] == saved['accounting_sha256']
                assert math.dist(proof['actual_position'],iv['after_position']) < 1e-6
                memory = proof['policy']['content_sha256']
                target_xy = proof['saved_world_pose'][0][:2]
                after_action = proof['policy']['step_id']
                actual_action = next(r for r in action_rows if r['sequence']==obs['sequence'])
                assert actual_action['action_index'] == after_action
            else:
                proof = read(directory/'memory_proof.json')
                assert proof['equal'] and proof['before']['sha256'] == proof['after']['sha256']
                memory = proof['before']['sha256']
                target_xy = iv['target']['target_xy']
                after_action = a
            before = len(nodes)-1
            node.update(phase='before', action=-1)
            segment += 1
            after = len(nodes)
            after_image = media.add(directory/'after.jpg')
            nodes.append(dict(p=iv['after_position'], yaw=yaw(iv['after_rotation']), a=after_action,
                              ticks=iv['physics_ticks_after'], image=after_image, segment=segment,
                              phase='after', action=action_code(action), reused=False,
                              distance=deviation(iv['after_position'], case['reference_path'])))
            events.append(dict(number=i+1, before=before, after=after, a=a,
                               distance=iv['distance_m'], threshold=iv['threshold_m'],
                               target_id=iv['target']['id'], target=target_xy,after_action=after_action,
                               crossing=iv['target'].get('crossing_position', iv['target'].get('branch_xy')),
                               onset_action=iv['event']['onset_action_index'],
                               translation=math.dist(iv['before_position'][:2],iv['after_position'][:2]),
                               goal_distance=math.dist(iv['after_position'][:2],case['reference_path'][-1][:2]),
                               memory=memory,
                               before_image=node['image'], after_image=after_image))
            if arm == 'auto_branch':
                target = iv['target']
                assert target['source'] == 'walked_reference_divergence'
                assert events[-1]['crossing'] is not None
                events[-1].update(branch_action_interval=target['branch_evidence']['action_interval'],
                                  branch_reference_arc_m=target['branch_reference_arc_m'],
                                  target_reference_arc_m=target['reference_arc_m'],
                                  requested_offset_m=target['requested_offset_m'],
                                  actual_offset_m=target['actual_offset_m'],
                                  clamped_to_route_end=target['clamped_to_route_end'],
                                  target_yaw_rad=target['target_yaw_rad'],
                                  landing_error_m=math.dist(target_xy, iv['after_position'][:2]))
            used.add(a)
    assert len(events) == len(interventions)
    final = result['metrics']['pred_path'][-1]
    if nodes[-1]['phase'] != 'end' or math.dist(nodes[-1]['p'][:2], final[:2]) > 1e-4:
        nodes.append(dict(nodes[-1], p=final, yaw=None, a=result['final_policy_action_index'],
                          action=-1, phase='end', reused=True, distance=deviation(final,case['reference_path'])))
    for e in events:
        assert e['after'] == e['before']+1
        assert nodes[e['after']]['segment'] == nodes[e['before']]['segment']+1
        assert nodes[e['after']]['a'] == e['after_action']
    audit = dict(result=str(result_path.relative_to(ROOT)), result_sha256=sha(result_path),
                 attempt=str(attempt.relative_to(ROOT)), observations_sha256=sha(attempt/'observations.jsonl'),
                 actions_sha256=sha(attempt/'actions.jsonl'), events=len(events), memory_proofs_verified=len(events),
                 exact_jump_boundaries_verified=True, final_rgb_reused=nodes[-1]['reused'])
    return result, nodes, events, audit


def checkpoint_targets(case, attempt):
    """Plot captured live positions, never the unused reference-route landings."""
    observations=rows(attempt/'observations.jsonl')
    targets={t['id']:dict(t,target_xy=None) for t in case['targets']}
    audits=[]
    for path in sorted(attempt.glob('snapshot_checkpoint_*.json')):
        saved=read(path)
        matches=[o for o in observations if o['action_index']==saved['action_index'] and o['physics_ticks']==saved['physics_ticks']]
        assert len(matches)==1
        obs=matches[0]
        targets[saved['target_id']].update(target_xy=obs['position'][:2],capture_action=obs['action_index'],capture_sequence=obs['sequence'])
        audits.append(dict(snapshot=str(path.relative_to(ROOT)),sha256=sha(path),target_id=saved['target_id'],position=obs['position'],sequence=obs['sequence']))
    return list(targets.values()),audits


def build(campaign, output, arm='early'):
    campaign = campaign.resolve()
    if output.exists():
        raise FileExistsError(output)
    cohort = read(campaign/'cohort.json')
    dataset = Path(cohort['dataset'])
    historical = {r['episode_id']: r for r in rows(dataset/'inputs/episodes.jsonl')}
    historical_scores = {r['episode_id']:r for r in rows(dataset/'evaluation/episodes.jsonl')}
    maps = read(dataset/'evaluation/maps.json')
    manifest=read(campaign/'manifest.json');status=read(campaign/'status.json')
    setting=manifest['arms'][arm]
    if setting['mode'] not in ('route','checkpoint'):raise ValueError('Unsupported Oracle mode')
    checkpoint=setting['mode']=='checkpoint'
    verified_rows=None
    if isinstance(status['completed'],list):
        completed = {r['episode_id']:r for r in status['completed'] if r['arm']==arm}
    else:
        assert status['phase']=='complete_services_retained' and status['completed']==33
        run=campaign/'runs/vlnverse/streamvln/results'/status['run_id']
        validation=read(run/'validation.json');assert validation['passed'] and validation['episodes']==33
        verified_rows={r['episode_id']:r for r in rows(run/'episodes.jsonl')}
        completed={eid:dict(episode_id=eid,result=str(campaign/'oracle_records'/arm/eid/'result.json')) for eid in verified_rows}
    assert len(completed) == len(cohort['cases']) == 33
    media = Media()
    offset=manifest['config']['landing_offset_m'];threshold=setting['threshold_m']
    data = dict(cases=[], maps={}, summary={}, images=[], threshold=threshold, seed=manifest['seed'],arm=arm,
                mode=setting['mode'],landing_offset_m=None if checkpoint else offset)
    audits=[]
    for c in cohort['cases']:
        eid=c['episode_id'];entry=completed[eid];hist=historical[eid]
        assert hist['instruction']==c['instruction'] and hist['instruction_zh']
        result_path=Path(entry['result']) if 'result' in entry else campaign/'oracle_records'/arm/eid/'result.json'
        if entry.get('result_sha256'):
            assert sha(result_path)==entry['result_sha256']
        elif verified_rows is None:
            marker=read(campaign/(arm+'_'+eid+'.complete.json'))
            assert sha(result_path)==marker['result_sha256']
        result,nodes,events,audit=trace(result_path,c,media,arm)
        targets=c['targets']
        if checkpoint:
            targets,capture_audit=checkpoint_targets(c,ROOT/audit['attempt'])
            audit['checkpoint_captures']=capture_audit
        if verified_rows is not None:
            official=verified_rows[eid]
            for key,other in [('success','SR'),('NE','NE'),('spl','SPL'),('osr','OS')]:
                assert abs(float(result['metrics'][key])-float(official[other]))<1e-6
            assert result['metrics']['fail_reason']==official['fail_reason']
        for event in events:
            target=next(t for t in targets if t['id']==event['target_id'])
            assert math.dist(event['target'],target['target_xy'])<1e-6
            if not checkpoint: assert target['requested_offset_m']==offset
        original=read(dataset/'evaluation/trajectories'/f'{eid}.json')
        original_obs=read(dataset/hist['observations'])
        assert original['reference_path']==c['reference_path']
        assert len(original['frames'])==len(original_obs)
        old_nodes=[]
        for pose,obs in zip(original['frames'],original_obs):
            assert pose['frame']==obs['frame']
            old_nodes.append(dict(p=pose['position'],a=obs['action_index'],frame=pose['frame'],yaw=None,
                                  action=action_code(pose['action_after_observation']),segment=0,
                                  phase='end' if obs['terminal'] else 'walk',reused=obs['rgb_reused'],
                                  image=media.add(dataset/obs['rgb']),distance=deviation(pose['position'],c['reference_path'])))
        scene=c['scene']
        if scene not in data['maps']:
            assert sha(dataset/maps[scene]['image'])==maps[scene]['sha256']
            data['maps'][scene]=dict(geometry=maps[scene]['geometry'],image=media.add(dataset/maps[scene]['image'],0))
        metrics={k:result['metrics'][k] for k in ['success','NE','spl','osr','fail_reason']}
        data['cases'].append(dict(id=eid,scene=scene,instruction=c['instruction'],instruction_zh=hist['instruction_zh'],
                                 reference=c['reference_path'],targets=targets,nodes=nodes,original=old_nodes,
                                 historical_success=historical_scores[eid]['original_success'],metrics=metrics,
                                 events=events,source_run=result_path.parents[3].name,
                                 max_distance=result['max_reference_distance_m'],actions=result['executed_actions']))
        audits.append(dict(episode_id=eid,historical_trajectory_sha256=sha(dataset/'evaluation/trajectories'/f'{eid}.json'),**audit))
    cases=data['cases']
    data['summary']=dict(tasks=len(cases),annotations=sum(len(c['targets']) for c in cases),
                         success=sum(int(c['metrics']['success']) for c in cases),
                         normal_success=sum(c['metrics']['fail_reason']=='success' for c in cases),
                         triggered=sum(bool(c['events']) for c in cases),events=sum(len(c['events']) for c in cases),
                         mean_spl=sum(c['metrics']['spl'] for c in cases)/len(cases),
                         mean_ne=sum(c['metrics']['NE'] for c in cases)/len(cases),
                         oracle_frames=sum(len(c['nodes']) for c in cases),original_frames=sum(len(c['original']) for c in cases))
    print(json.dumps(data['summary']),flush=True)
    sources=Counter(c['source_run'] for c in cases)
    extra=arm=='early_plus05'
    data['labels']={
        'title':['自动 Oracle · 落点额外前移0.5米' if extra else f'自动 Oracle · {threshold:g}米纠正组',
                 'Automatic Oracle · landing +0.5 m' if extra else f'Automatic Oracle · {threshold:g} m correction'],
        'subtitle':[f'VLNVerse R2R风格 · StreamVLN · seed {data["seed"]} · {len(cases)}条真实仿真 · 偏航阈值{threshold:g}米 · 落点前移共{offset:g}米',
                    f'VLNVerse R2R-style · StreamVLN · seed {data["seed"]} · {len(cases)} simulated episodes · deviation threshold {threshold:g} m · landing offset {offset:g} m'],
        'scope1':[f'以当前位置到完整正确参考折线的最短水平距离检测偏航，阈值{threshold:g}米。等待策略动作队列执行完毕后纠正，实际触发距离可能更大。落点位于关联人工分叉点投影后沿参考路线前移{offset:g}米的位置'+('（比原组额外前移0.5米）' if extra else '')+'。同时纠正朝向，保留策略记忆，允许多次纠正。',
                  f'Deviation is the shortest horizontal distance to the full correct reference polyline, with threshold {threshold:g} m. Correction waits for the policy action queue to empty, so actual trigger distance may be larger. Landing is {offset:g} m along the reference from the projected annotated fork'+(' (0.5 m farther than the original group)' if extra else '')+'. Heading is corrected, policy memory is preserved, and repeated corrections are allowed.'],
        'scope4':[f'{len(cases)}条任务对应{data["summary"]["annotations"]}个人工错误事件，{data["summary"]["events"]}次实际纠正并非独立样本。来源：'+ '；'.join(f'{k}：{v}条' for k,v in sources.items())+'。本页仅导出已有结果，不重跑导航。',
                  f'{len(cases)} episodes contain {data["summary"]["annotations"]} annotated wrong-choice events. The {data["summary"]["events"]} corrections are not independent samples. Sources: '+ '; '.join(f'{k}: {v} episodes' for k,v in sources.items())+'. This page exports existing results without rerunning navigation.']}
    if checkpoint:
        data['labels'].update({
            'title':['实际存档回退 · StreamVLN自主续走','Actual checkpoint rollback · StreamVLN continuation'],
            'subtitle':[f'VLNVerse R2R风格 · StreamVLN · seed {data["seed"]} · 33条真实仿真 · 偏离{threshold:g}米触发 · 每条最多回退一次',
                        f'VLNVerse R2R-style · StreamVLN · seed {data["seed"]} · 33 simulated episodes · {threshold:g} m deviation trigger · at most one rollback per episode'],
            'oracle':['本次回退后自主续走','Current rollback-and-continue run'],
            'oracleShort':['本次回退实验轨迹','Current rollback trajectory'],
            'triggeredOnly':['触发回退','With rollback'],'untriggeredOnly':['未触发回退','Without rollback'],
            'triggered':['触发回退任务','Tasks with rollback'],'count':['实际回退次数','Actual rollbacks'],
            'corrections':['实际存档回退事件','Actual checkpoint rollback events'],
            'noEvent':['本任务未执行回退，保留自然终止结果。','No rollback was executed; the natural terminal result is retained.'],
            'jumpBefore':['跳到回退前','Jump before rollback'],'jumpAfter':['跳到回退后','Jump after rollback'],
            'beforePhase':['回退前','Before rollback'],'afterPhase':['回退后（已站稳）','After rollback (settled)'],
            'event':['回退','Rollback'],'events':['回退次数','Rollbacks'],
            'beforeAction':['即将回退；下一动作从恢复的存档记忆与画面继续生成。','About to roll back; the next action continues from the restored checkpoint memory and observation.'],
            'landing':['实际存档点 T','Actual checkpoint T'],
            'mapHelp':['S 起点 · G 目标 · C 标注分叉点 · T 实际保存的存档点（未存档不画T）· P 当前位置。实线表示导航，紫色虚线箭头表示实际回退，不是正确方向指导。浅蓝色为完整本次轨迹，深蓝色为已回放部分。拖动地图平移，滚轮缩放。',
                       'S: start · G: goal · C: annotated fork · T: actual captured checkpoint (no T without a capture) · P: current position. Solid lines show navigation; purple dashed arrows show actual rollbacks, not correct-branch guidance. Pale blue shows the full current run; dark blue shows the played portion. Drag to pan and scroll to zoom.'],
            'memory':['存档记忆恢复证据','Checkpoint memory restoration evidence'],
            'preserved':['恢复后记忆SHA256与原存档一致；不是保留回退触发时的记忆','Restored memory SHA256 matches the saved checkpoint; it is not the memory at the rollback trigger'],
            'nearNote':['实际回退落点位于目标3米水平半径内，成功不能全部归因于回退后的自主导航。','The settled rollback position is horizontally within 3 m of the goal. Success cannot be attributed entirely to autonomous navigation after rollback.'],
            'scope1':[f'以到完整正确参考折线的最短水平距离检测偏离，阈值{threshold:g}米。首次在人工分叉点1米内、偏距不足0.75米且动作队列为空时保存实际状态；有存档且达到阈值、动作队列为空才回退。恢复存档位置、朝向、策略记忆、RNG及预算，沿用50 tick站稳流程，每条最多一次。之后完全由StreamVLN自主续走，不提供正确分支动作，不使用沿参考路线前移的落点。回退前后策略动作编号和物理时钟会回到存档值；进度条仍按实际观测先后播放。',
                      f'Deviation is the shortest horizontal distance to the full correct reference polyline, with threshold {threshold:g} m. A live state is first captured within 1 m of an annotated fork, below 0.75 m deviation, with an empty action queue. Rollback requires that capture, threshold crossing and an empty queue. Position, heading, policy memory, RNG and budget are restored, followed by the existing 50-tick stabilization, at most once per episode. StreamVLN then continues autonomously, without correct-branch actions or a forward landing on the reference route. Policy action indices and the physics clock rewind to checkpoint values; sliders still follow chronological observations.'],
            'scope3':['官方成功沿用原版终点距离小于3米的评分，实际终止原因另列。底图为既有场景几何投影，T来自实际存档而非未使用的参考路线候选落点。回退前后均为实际记录；缺少新的终止RGB时标注复用。',
                      'Official success follows the original final-distance-below-3-m rule; termination reasons are separate. Floor plans are existing scene geometry projections. T comes from actual captures, not unused candidate landings on the reference route. Before/after views are actual records; missing new terminal RGB is explicitly marked as reused.'],
            'scope4':[f'33条任务对应34个标定事件，{data["summary"]["events"]}次实际回退，{data["summary"]["triggered"]}条触发。来源：运行06及其保留结果的续跑；每条只取与正式结果匹配的已完成attempt。只导出已有结果，不重跑导航。',
                      f'33 episodes contain 34 annotated events, with {data["summary"]["events"]} actual rollbacks in {data["summary"]["triggered"]} episodes. Source: run06 and its resumptions preserving completed results. Each episode uses only the completed attempt matching its official result. Existing results are exported without rerunning navigation.']})
    data['images']=media.encode()
    template=ROOT/'core/oracle_distance_replay.html'
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    html=template.read_text(); assert html.count('__PAYLOAD__')==1
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(html.replace('__PAYLOAD__',payload))
    font_metadata=add_font(output)
    manifest=dict(created_at=datetime.now(timezone.utc).isoformat(),html=str(output),sha256=sha(output),
                  bytes=output.stat().st_size,summary=data['summary'],images=len(data['images']),arm=arm,threshold_m=threshold,landing_offset_m=data['landing_offset_m'],
                  exporter_sha256=sha(Path(__file__)),template_sha256=sha(template),
                  git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  git_dirty=True,cohort_sha256=sha(campaign/'cohort.json'),audits=audits,
                  self_contained=True,no_model_or_simulator_started=True,
                  historical_source=str(dataset),historical_inputs_sha256=sha(dataset/'inputs/episodes.jsonl'),**font_metadata)
    output.with_suffix('.build.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k!='audits'},ensure_ascii=False),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--arm',default='early')
    args=parser.parse_args()
    build(args.campaign,args.output,args.arm)
