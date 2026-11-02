"""Export scored failures, optionally requiring failure in every requested seed."""
import argparse
import base64
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def joint_failure_ids(scores, required_seeds):
    """Keep the same episode only when every requested seed has a normal failure."""
    common = set.intersection(*(set(scores[seed]) for seed in required_seeds))
    return {episode for episode in common if all(
        float(scores[seed][episode]['info']['success']) == 0 and
        scores[seed][episode]['fail_reason'] == 'not_reach_goal'
        for seed in required_seeds)}


def select_diverse_cases(eligible, count=25):
    groups = defaultdict(list)
    for row in eligible.values(): groups[row['scene']].append(row)
    if len(eligible) < count: raise ValueError(f'Only {len(eligible)} eligible tasks; need {count}')
    quota = {s:min(2,len(g)) for s,g in groups.items()}
    if sum(quota.values()) > count: raise ValueError('Too many scenes for the requested coverage')
    order = sorted(groups, key=lambda s:(-len(groups[s]),s))
    while sum(quota.values()) < count:
        for scene in order:
            if quota[scene] < len(groups[scene]): quota[scene] += 1
            if sum(quota.values()) == count: break
    selected = []
    for scene in sorted(groups):
        remaining = sorted(groups[scene], key=lambda r:(r['metrics']['NE'],r['episode_id']))
        passed_goal = [r for r in remaining if r['metrics']['osr'] == 1]
        first = passed_goal[-1] if passed_goal else remaining[0]
        remaining.remove(first); chosen = [first]
        if quota[scene] >= 2:
            not_passed = [r for r in remaining if r['metrics']['osr'] == 0]
            second = not_passed[0] if passed_goal and not_passed else remaining[-1]
            remaining.remove(second); chosen.append(second)
        while len(chosen) < quota[scene]: chosen.append(remaining.pop(len(remaining)//2))
        selected.extend(chosen)
    return selected


def prepare(campaign, output, required_seeds=(0,1,2)):
    import lmdb
    import msgpack_numpy

    required_seeds = sorted(set(required_seeds))
    if 2 not in required_seeds: raise ValueError('The recorded video seed 2 must be included')
    campaign_manifest = json.loads((campaign/'manifest.json').read_text())
    scores = {seed:{} for seed in required_seeds}
    runs = {}
    for unit in campaign_manifest['units']:
        seed = unit['seed']
        if seed not in scores: continue
        run = campaign/'runs/vlnverse/streamvln/results'/unit['run_id']
        if not (run/'result.json').exists(): continue
        assert json.loads((run/'result.json').read_text())['status'] == 'complete'
        assert json.loads((run/'validation.json').read_text())['passed']
        meta = json.loads((run/'run.json').read_text())
        assert meta['seed'] == seed
        runs[(seed, unit['scene'])] = (run, meta)
        database = lmdb.open(str(run/'storage/samples/sample_data.lmdb'),readonly=True,lock=False)
        try:
            with database.begin() as txn:
                for key,value in txn.cursor():
                    if key in (b'timestamp_',b'eval_rank_0'): continue
                    record = msgpack_numpy.unpackb(value); info = record['info']
                    assert info['reproduction_run_seed'] == seed
                    episode = info['episode_id']
                    assert episode in meta['episode_ids'] and episode not in scores[seed]
                    record['_source'] = dict(run_id=unit['run_id'],scene=unit['scene'],lmdb=str(run/'storage/samples/sample_data.lmdb'),
                        key=key.decode(),record_sha256=hashlib.sha256(value).hexdigest(),dataset_sha256=meta['dataset_sha256'])
                    scores[seed][episode] = record
        finally: database.close()
    qualifying = joint_failure_ids(scores,required_seeds)
    source = campaign / 'visualization'
    index_bytes = (source/'index.jsonl').read_bytes()
    rows = [json.loads(line) for line in index_bytes.splitlines() if line.strip()]
    eligible = {r['episode_id']: r for r in rows if r['episode_id'] in qualifying and r['seed'] == 2 and r['status'] == 'complete'
                and r['fail_reason'] == 'not_reach_goal' and r['metrics']['success'] == 0}
    selected = select_diverse_cases(eligible)
    assert len(selected) == len({r['episode_id'] for r in selected}) == 25
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    trace_cache = {}
    def episode_trace(run, episode):
        if run not in trace_cache:
            by_episode = {}
            for tracefile in sorted((run/'storage/chunks').glob('*/agent_trace.jsonl'),reverse=True):
                chunk_traces = defaultdict(list)
                for line in tracefile.read_text().splitlines():
                    if line:
                        t = json.loads(line); chunk_traces[t['episode_id']].append(t)
                for identity, trace in chunk_traces.items():
                    if identity not in by_episode: by_episode[identity] = (trace,tracefile)
            trace_cache[run] = by_episode
        return trace_cache[run][episode]
    for number, row in enumerate(selected, 1):
        directory = output/'cases'/f'{number:02d}_{row["episode_id"]}'
        directory.mkdir(parents=True)
        original = source/row['detail']
        case = json.loads(original.read_text())
        steps = [json.loads(line) for line in (source/row['steps']).read_text().splitlines() if line]
        assert case['status'] == 'complete' and len(steps) == case['frames']
        assert [s['frame'] for s in steps] == list(range(case['frames']))
        run = campaign/'runs/vlnverse/streamvln/results'/row['run_id']
        official = scores[2][row['episode_id']]
        info = official['info']
        assert info['reproduction_run_seed'] == 2 and float(info['success']) == 0
        assert official['fail_reason'] == 'not_reach_goal'
        assert info['reproduction_episode_seed'] == case['episode_seed']
        for key, value in case['metrics'].items():
            assert math.isclose(float(info[key]), value, abs_tol=1e-6), (case['episode_id'], key)
        assert float(info['success_distance']) == 3
        seed_results = {}
        for seed in required_seeds:
            record = scores[seed][case['episode_id']]; seed_info = record['info']
            seed_run, meta = runs[(seed,case['scene'])]
            trace, tracefile = episode_trace(seed_run,case['episode_id'])
            assert trace and [t['step'] for t in trace] == list(range(len(trace)))
            assert all(t['run_seed']==seed and t['episode_seed']==seed_info['reproduction_episode_seed']
                       and not t['forced_smoke_stop'] for t in trace)
            assert trace[-1]['action'] == 0
            assert record['fail_reason']=='not_reach_goal' and float(seed_info['success'])==0
            # The simulator lifts annotation Z=0 to robot height (1.05 m).
            # Navigation scoring and the review map use XY; compare that plane.
            assert len(seed_info['reference_path']) == len(case['reference_path'])
            assert all(math.dist(a[:2],b[:2]) < 1e-6
                       for a,b in zip(seed_info['reference_path'],case['reference_path']))
            assert record['_source']['dataset_sha256'] == official['_source']['dataset_sha256']
            seed_results[str(seed)] = dict(seed=seed,success=float(seed_info['success']),
                NE=float(seed_info['NE']),OS=float(seed_info['osr']),SPL=float(seed_info['spl']),
                TL=float(seed_info['TL']),fail_reason=record['fail_reason'],
                episode_seed=int(seed_info['reproduction_episode_seed']),actions=len(trace),last_model_action=trace[-1]['action'],
                pred_path=seed_info['pred_path'],source_trace=str(tracefile),source=record['_source'])
            if seed == 2:
                assert len(trace) == case['actions']
                model_actions = [t['action'] for t in trace]
                generations = [dict(step=t['step'], output=t.get('output'), seconds=t.get('generation_seconds'))
                               for t in trace if t.get('generated')]
                trace_source = str(tracefile)
        goal = case['reference_path'][-1][:2]
        for step in steps:
            action = step['action']
            code = 0 if 'stop' in action else (action.get('move_by_discrete') or action.get('move_by_flash') or [-1])[0]
            step['action_code'] = code
            step['distance_xy'] = math.dist(step['position'][:2], goal) if step['position'] else None
        closest = min((s for s in steps if s['distance_xy'] is not None), key=lambda s: s['distance_xy'])
        if case['metrics']['osr'] == 1:
            category, tag = 'left_goal', '曾到目标范围后离开'
        elif case['metrics']['NE'] < 5:
            category, tag = 'near_goal', '接近目标但未到达'
        else:
            category, tag = 'missed_goal', '未进入目标范围'
        case.update(number=number, category=category, tag=tag,required_seeds=required_seeds,seed_results=seed_results,
                    closest_frame=closest['frame'], closest_recorded_distance=closest['distance_xy'],
                    turn_fraction=sum(a in (2,3) for a in model_actions)/len(model_actions),
                    steps=steps, generations=generations,
                    source_video=str(source/row['video']), source_case=str(original), source_trace=trace_source,
                    source_video_sha256=sha256(source/row['video']),
                    video=str((directory/'navigation.mp4').relative_to(output)),
                    poster=str((directory/'poster.jpg').relative_to(output)),
                    detail=str((directory/'case.json').relative_to(output)))
        # The full instruction is preserved, never truncated in the export.
        shutil.copy2(original, directory/'source_case.json')
        shutil.copy2(source/row['steps'], directory/'source_steps.jsonl')
        write_json(directory/'case.json', case)
        cases.append(case)
    manifest = dict(created_at=datetime.now(timezone.utc).isoformat(), campaign=str(campaign), seed=2,video_seed=2,
        required_seeds=required_seeds,scored_counts={s:len(v) for s,v in scores.items()},qualifying_episode_ids=sorted(qualifying),
        candidate_count=len(eligible), selected_count=25, scene_counts=dict(Counter(c['scene'] for c in cases)),
        category_counts=dict(Counter(c['tag'] for c in cases)),
        selection='Cover all eligible scenes, start with two per scene; allocate remaining slots by candidate count; diversify video-seed OS/NE. Not a random sample.',
        filter=dict(required_seeds=required_seeds,video_seed=2,status='complete',success_in_every_seed=0,fail_reason_in_every_seed='not_reach_goal'),
        source_index_sha256=hashlib.sha256(index_bytes).hexdigest(),
        fps=6, note='One recorded action observation per frame; playback is not real-time physics.',
        cases=cases)
    write_json(output/'selection.json', manifest)
    print(json.dumps(dict(output=str(output), count=25, scenes=manifest['scene_counts'],
                         categories=manifest['category_counts']),ensure_ascii=False),flush=True)
    for case in cases:
        print(f"{case['number']:02d} {case['episode_id']} NE={case['metrics']['NE']:.2f} OS={case['metrics']['osr']} actions={case['actions']}\n{case['instruction']}",flush=True)


def wrap_pixels(text, font, width):
    lines, line = [], ''
    for word in text.split():
        candidate = (line+' '+word).strip()
        if font.getlength(candidate) > width and line:
            lines.append(line); line = word
        else: line = candidate
    if line: lines.append(line)
    return lines


def render(output):
    import imageio_ffmpeg
    from PIL import Image, ImageDraw, ImageFont

    manifest = json.loads((output/'selection.json').read_text())
    font_dir = ROOT/'.runtime/isaac45/kit/resources/fonts'
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    english_tags = {'left_goal':'ENTERED GOAL RANGE, THEN LEFT', 'near_goal':'STOPPED NEAR THE GOAL',
                    'missed_goal':'DID NOT ENTER GOAL RANGE'}
    receipts = []
    for case in manifest['cases']:
        destination = output/case['video']
        directory = destination.parent
        banner = Image.new('RGBA',(1280,1040),(15,22,34,255))
        draw = ImageDraw.Draw(banner)
        draw.rectangle((0,80,1279,719),fill=(0,0,0,0))
        bold = ImageFont.truetype(str(font_dir/'NVIDIASans_Bd.ttf'),25)
        regular = ImageFont.truetype(str(font_dir/'NVIDIASans_Rg.ttf'),21)
        small = ImageFont.truetype(str(font_dir/'NVIDIASans_Rg.ttf'),18)
        draw.text((25,14),f"CASE {case['number']:02d} / 25  |  SEED 2  |  {case['episode_id']}",font=bold,fill='#f0f5fa')
        if len(case.get('required_seeds',[2])) > 1:
            distances = ' / '.join(f"S{s} {case['seed_results'][str(s)]['NE']:.2f}m" for s in case['required_seeds'])
            label = f'ALL {len(case["required_seeds"])} SEEDS FAILED, NORMAL STOP  |  NE: '+distances+'  |  VIDEO: SEED 2'
        else:
            label = f"NOT REACHED  |  NE {case['metrics']['NE']:.2f} m  |  OS {int(case['metrics']['osr'])}  |  {case['actions']} actions"
        assert small.getlength(label)<=1230
        draw.text((25,49),label,font=small,fill='#ffbc78')
        draw.text((25,739),'TASK / ORIGINAL INSTRUCTION',font=bold,fill='#73d9cb')
        lines = wrap_pixels(case['instruction'],regular,1230)
        assert len(lines)<=8,(case['episode_id'],len(lines))
        for index,line in enumerate(lines):
            draw.text((25,780+index*25),line,font=regular,fill='#e8edf4')
        draw.text((25,1010),'VIDEO SEED 2: '+english_tags[case['category']]+'  |  6 action frames/s; not real-time speed',font=small,fill='#9cacc1')
        overlay = directory/'video_labels.png'; banner.save(overlay)
        command = [ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-y','-threads','1',
            '-i',case['source_video'],'-i',str(overlay),'-filter_complex_threads','1',
            '-filter_complex','[0:v]crop=960:480:0:0,scale=1280:640,pad=1280:1040:0:80:color=0x0f1622[base];[base][1:v]overlay=0:0:format=auto[out]',
            '-map','[out]','-an','-c:v','libx264','-preset','veryfast','-crf','22','-threads','1',
            '-pix_fmt','yuv420p','-movflags','+faststart',str(destination)]
        with (directory/'export.log').open('w') as log:
            subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT)
        # Full CPU decode checks every exported frame and reports exact dimensions/count.
        result = subprocess.run([ffmpeg,'-v','error','-threads','1','-i',str(destination),
            '-map','0:v:0','-f','framemd5','-'],check=True,capture_output=True,text=True)
        records = [line for line in result.stdout.splitlines() if line and not line.startswith('#')]
        assert len(records)==case['frames'],(case['episode_id'],len(records),case['frames'])
        assert '#dimensions 0: 1280x1040' in result.stdout
        subprocess.run([ffmpeg,'-v','error','-nostdin','-y','-threads','1','-i',str(destination),
            '-frames:v','1','-threads','1',str(output/case['poster'])],check=True)
        shutil.copy2(output/case['poster'],directory/'first_frame.jpg')
        case['video_sha256'] = sha256(destination)
        case['video_bytes'] = destination.stat().st_size
        write_json(output/case['detail'],case)
        receipts.append(dict(number=case['number'],episode_id=case['episode_id'],frames=len(records),
            dimensions=[1280,1040],bytes=case['video_bytes'],sha256=case['video_sha256'],decode_passed=True))
        print(json.dumps(receipts[-1]),flush=True)
    write_json(output/'selection.json',manifest)
    write_json(output/'video_validation.json',dict(passed=True,count=len(receipts),videos=receipts))


def build_html(output):
    from PIL import Image

    manifest = json.loads((output/'selection.json').read_text())
    annotations = json.loads((output/'annotations.zh.json').read_text())
    validation = json.loads((output/'video_validation.json').read_text())
    assert validation['passed'] and validation['count'] == 25
    assert set(annotations) == {c['episode_id'] for c in manifest['cases']}
    payload = []
    keys = ['number','episode_id','scene','instruction','fps','frames','actions','metrics','category','tag',
            'reference_path','pred_path','steps','generations','closest_frame','closest_recorded_distance',
            'turn_fraction','video','detail','seed_results','required_seeds']
    for case in manifest['cases']:
        assert case['fail_reason'] == 'not_reach_goal' and case['metrics']['success'] == 0
        case.update(annotations[case['episode_id']])
        write_json(output/case['detail'],case)
        row = {key:case[key] for key in keys}
        row.update(annotations[case['episode_id']])
        with Image.open(output/case['poster']) as poster:
            poster.thumbnail((260,212))
            stream = io.BytesIO(); poster.convert('RGB').save(stream,format='JPEG',quality=80)
        row['thumbnail'] = 'data:image/jpeg;base64,'+base64.b64encode(stream.getvalue()).decode()
        payload.append(row)
    bundle_id = hashlib.sha256((str(manifest['required_seeds'])+'\n'+'\n'.join(c['episode_id'] for c in manifest['cases'])).encode()).hexdigest()[:16]
    data = dict(bundle_id=bundle_id,created_at=datetime.now(timezone.utc).isoformat(),
                candidate_count=manifest['candidate_count'],required_seeds=manifest['required_seeds'],video_seed=2,cases=payload)
    template = (ROOT/'core/failure_cases_review.html').read_text()
    embedded = json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    (output/'index.html').write_text(template.replace('__CASE_DATA__',embedded))
    fields=['case','scene','episode_id','video_seed','phenomenon_seed2','NE_seed2_m','OS_seed2','actions_seed2','task_title','instruction_zh','instruction_en','video']
    with (output/'cases.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields); writer.writeheader()
        for c in manifest['cases']:
            writer.writerow(dict(case=c['number'],scene=c['scene'],episode_id=c['episode_id'],video_seed=2,phenomenon_seed2=c['tag'],
                NE_seed2_m=c['metrics']['NE'],OS_seed2=c['metrics']['osr'],actions_seed2=c['actions'],task_title=c['task_title'],
                instruction_zh=c['instruction_zh'],instruction_en=c['instruction'],video=c['video']))
    comparison_fields=['case','episode_id','scene','seed','success','NE','OS','SPL','TL','fail_reason','actions','last_model_action','episode_seed']
    with (output/'three_seed_scores.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=comparison_fields,extrasaction='ignore'); writer.writeheader()
        for case in manifest['cases']:
            for result in case['seed_results'].values():
                writer.writerow(dict(result,case=case['number'],episode_id=case['episode_id'],scene=case['scene']))
    readme = '''StreamVLN / VLNVerse：seed 2 的 25 个失败案例

打开方式
1. 解压整个压缩包，保留 index.html 与 cases/ 的相对位置。
2. 用浏览器直接打开 index.html，无需服务器、端口或联网。
3. 25 个独立标注视频位于 cases/编号_episode/navigation.mp4。
   每个视频全程显示案例编号、完整英文任务、终点距离和动作数；相机画面旁附原轨迹示意。

如何复盘
- 左栏按 scene、现象、任务文字筛选，可按终点距离或动作数量排序。
- 视频、轨迹、距离曲线与动作条同步。点击曲线/动作条可定位。
- “最接近目标”和“结束”按钮可快速查看关键位置；方向键逐帧，J/K 切换案例。
- 提供中文任务释义、原始英文任务及模型生成的动作文本。
- 人工判断与笔记保存在本浏览器；请导出笔记 JSON 备份。可重新导入同一案例包的笔记。
- “只显示尚未标记的案例”支持逐条完成复盘。

选择与评分口径
全部为已完成的 seed 2 任务，官方 success=0，fail_reason=not_reach_goal，模型最终动作是 STOP。
排除了摔倒、卡住、超时、未完成任务。每个 scene 至少 2 条，共 10 个 scene、25 条。
按场景和 OS/NE 的差异挑选，属于定性分析样本，不是随机抽样，不用于估计失败率。
8 条曾进入目标范围后离开、9 条接近目标但未到达、8 条未进入目标范围。
这些是指标描述，不是已经确认的错误原因；具体原因需结合指令、画面和动作判断。

时间和轨迹
录像按每个动作观测一帧记录，以 6 fps 回放，不代表仿真真实时间。
当前帧是该动作发出前的观测；终止帧可能复用最后一张 RGB。
XY 图不是平面地图，不包含墙壁/障碍/可通行性。目标为原始 reference_path 的最后一点。
距离曲线根据记录帧计算，官方 OS 在动作完成时采样，两者采样时刻可能不同。
中文释义只用于阅读，模型输入保持原始英文。

文件
index.html：离线交互页面（任务、轨迹、缩略图已内嵌；播放视频需保留 cases/）。
cases.csv：25 条案例清单，可用表格软件打开。
selection.json：冻结选取列表、过滤条件、原始来源和文件哈希。
annotations.zh.json：中文任务标题与释义。
video_validation.json：25 个视频的完整解码、帧数、尺寸及 SHA256 校验。
cases/*/case.json：完整案例、逐帧位置和动作、模型生成与原始来源。
cases/*/source_case.json、source_steps.jsonl：导出时复制的原始可视化记录。
生成过程只读取已完成录像和评分；没有改动实验代码、原始录像、模型或数据集，也没有重跑导航。
'''
    scope='、'.join(str(s) for s in manifest['required_seeds'])
    readme=readme.replace('seed 2 的 25 个失败案例',f'seed {scope} 共同失败的 25 个任务（视频来自 seed 2）')
    readme=readme.replace('全部为已完成的 seed 2 任务，官方 success=0，fail_reason=not_reach_goal，模型最终动作是 STOP。',
        f'每个任务在 seed {scope} 中均已完成，且每次官方 success=0、fail_reason=not_reach_goal、模型最终动作都是 STOP。')
    readme=readme.replace('每个 scene 至少 2 条，共 10 个 scene、25 条。',f"本次覆盖 {len(manifest['scene_counts'])} 个有合格候选的 scene，共 25 个任务。")
    readme=readme.replace('8 条曾进入目标范围后离开、9 条接近目标但未到达、8 条未进入目标范围。',
        '视频 seed 2 的现象分布：'+'，'.join(f'{n} 条{tag}' for tag,n in manifest['category_counts'].items())+'。')
    readme+=f'\n各 seed 核验\nthree_seed_scores.csv 保存 25 个任务 × {len(manifest["required_seeds"])} 个 seed 的逐次结果。\nHTML 可对照各 seed 的完整轨迹；只有 seed 2 的位置随视频时间更新。\nseed 0、1 当时没有录制视频，本包的全部录像来自 seed 2。\n'
    (output/'README.txt').write_text(readme)
    manifest.update(bundle_id=bundle_id,html_created_at=data['created_at'])
    write_json(output/'selection.json',manifest)
    print(json.dumps(dict(html=str(output/'index.html'),bytes=(output/'index.html').stat().st_size,
                         videos=len(payload),bundle_id=bundle_id)),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','render','html'])
    parser.add_argument('--campaign',type=Path)
    parser.add_argument('--require-seeds',type=int,nargs='+',default=[0,1,2],help='Every listed seed must have SR=0 and normal STOP')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.action=='prepare':
        if not args.campaign: parser.error('--campaign required for prepare')
        prepare(args.campaign.resolve(),args.output.resolve(),args.require_seeds)
    elif args.action=='render': render(args.output.resolve())
    else: build_html(args.output.resolve())


if __name__=='__main__': main()
