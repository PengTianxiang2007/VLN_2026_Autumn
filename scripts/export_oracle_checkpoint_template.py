"""Export complete wrong -> saved-pose restore -> continuation timelines, CPU only."""
import argparse
import base64
import hashlib
import io
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMS = ('trunk', 'streamvln', 'oracle_actions')


def read_json(path):
    return json.loads(path.read_text()) if path.exists() else None


def build_timeline(case, arm):
    """Keep the entire error-producing trunk; discard only the copied arm prefix."""
    trunk = case['arms']['trunk']['frames']
    rows = [dict(f, source_arm='trunk', source_index=i, phase='trunk') for i, f in enumerate(trunk)]
    events = []
    checkpoint, error = case['checkpoint'], case['actual_error']
    if checkpoint:
        cp_index = next(i for i, f in enumerate(trunk) if f['action_index'] == checkpoint['action_index'])
        events.append(dict(kind='checkpoint', label='保存真实存档', index=cp_index))
    if error:
        error_index = next(i for i, f in enumerate(trunk) if f['action_index'] == error['action_index'])
        assert error_index == len(trunk) - 1
        rows[error_index]['phase'] = 'error'
        events.append(dict(kind='error', label='首次确认走错', index=error_index))
    restore_index = None
    branch = case['arms'][arm]
    if arm != 'trunk' and branch['result'] and branch['result']['triggered']:
        proof = branch['restore_proof']
        assert checkpoint and error and proof
        # Restore writes the saved common prefix, followed by one NEW observation
        # at the same checkpoint action number. Never select by action number alone.
        prefix_count = cp_index + 1
        assert branch['frames'][:prefix_count] == trunk[:prefix_count]
        tail = branch['frames'][prefix_count:]
        assert tail and tail[0]['action_index'] == checkpoint['action_index']
        assert tail[0]['position'] == proof['actual_position']
        assert tail[0]['physics_ticks'] == proof['physics_ticks_after']
        restore_index = len(rows)
        choice = branch['result']['local_choice']
        for offset, f in enumerate(tail):
            phase = 'retry' if arm == 'streamvln' else ('oracle' if f['action_index'] <= choice['action_index'] else 'handoff')
            rows.append(dict(f, source_arm=arm, source_index=prefix_count + offset,
                             phase='restore' if offset == 0 else phase))
        events.append(dict(kind='restore', label='复位到真实存档', index=restore_index))
        local_index = next(i for i in range(restore_index, len(rows)) if rows[i]['action_index'] == choice['action_index'])
        label = ('再次选错' if choice['choice'] == 'wrong' else '自主选对') if arm == 'streamvln' else 'Oracle 选对，交回 StreamVLN'
        events.append(dict(kind='choice', label=label, index=local_index))
    if rows and rows[-1]['terminal']:
        events.append(dict(kind='terminal', label='自然结束', index=len(rows) - 1))
    return dict(frames=rows, events=events, restore_index=restore_index)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, default=ROOT/'outputs/oracle_crossing/checkpoint_action10/run_20261105_01')
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    out, dest = args.campaign.resolve(), args.destination.resolve()
    dest.mkdir(parents=True, exist_ok=False)
    manifest = read_json(out/'manifest.json')
    images, cached_images, cases, sources = {}, {}, [], {}

    def image_id(path):
        if str(path) in cached_images:
            return cached_images[str(path)]
        raw = path.read_bytes()
        key = hashlib.sha256(raw).hexdigest()
        if key not in images:
            from PIL import Image
            im = Image.open(io.BytesIO(raw)).convert('RGB')
            im.thumbnail((480, 360))
            buf = io.BytesIO()
            im.save(buf, format='JPEG', quality=55)
            images[key] = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()
        cached_images[str(path)] = key
        return key

    for m in manifest['cases']:
        d = out/'oracle_records'/m['episode_id']
        c = dict(episode_id=m['episode_id'], instruction=m['instruction'], reference=m['reference_path'],
                 scene=m['scene'], crossing=m.get('crossing'), arms={}, checkpoint=read_json(d/'snapshot_checkpoint.json'),
                 actual_error=read_json(d/'actual_error.json'), technical_failure=read_json(d/'technical_failure.json'))
        for arm in ARMS:
            folder = d/arm
            path = folder/'observations.jsonl'
            frames = []
            if path.exists():
                sources[str(path.relative_to(out))] = hashlib.sha256(path.read_bytes()).hexdigest()
                for line in path.read_text().splitlines():
                    f = json.loads(line)
                    image_path = Path(f.pop('frame'))
                    if image_path.is_file():
                        f['image_id'] = image_id(image_path)
                    else:
                        assert f['terminal'] and frames, f'Missing nonterminal frame: {image_path}'
                        f['image_id'] = frames[-1]['image_id']
                        f['image_missing'] = True
                        f['image_source_action'] = frames[-1]['action_index']
                    frames.append(f)
            reviews = []
            for q in sorted(folder.glob('review_*/request.json')):
                request = read_json(q)
                reviews.append(dict(action=request['action_index'], request=request, response=read_json(q.parent/'response.json')))
            c['arms'][arm] = dict(frames=frames, reviews=reviews, result=read_json(folder/'result.json'),
                                  restore_proof=read_json(folder/'restore_proof.json'))
        c['paired'] = all(c['arms'][arm]['result'] and c['arms'][arm]['result']['triggered'] for arm in ARMS[1:])
        c['audit'] = {}
        if c['paired']:
            proofs = [c['arms'][arm]['restore_proof'] for arm in ARMS[1:]]
            c['audit'] = dict(same_saved_pose=proofs[0]['saved_world_pose'] == proofs[1]['saved_world_pose'],
                              same_policy_hash=proofs[0]['policy']['content_sha256'] == proofs[1]['policy']['content_sha256'],
                              stabilized_pair_gap_m=math.dist(proofs[0]['actual_position'][:2], proofs[1]['actual_position'][:2]))
            assert c['audit']['same_saved_pose'] and c['audit']['same_policy_hash']
        c['timelines'] = {arm: build_timeline(c, arm) for arm in ARMS}
        cases.append(c)

    paired = [c for c in cases if c['paired']]
    counts = dict(requested_cases=len(cases), valid_pairs=len(paired),
                  technical_failures=sum(bool(c['technical_failure']) for c in cases),
                  untriggered=sum(not c['paired'] and not c['technical_failure'] for c in cases),
                  paired_final_success={arm: sum(bool(c['arms'][arm]['result']['metrics']['success']) for c in paired) for arm in ARMS[1:]},
                  paired_local_correct={arm: sum(c['arms'][arm]['result']['local_choice']['choice'] == 'correct' for c in paired) for arm in ARMS[1:]})
    scenes = {}
    for c in cases:
        s = c['scene']
        if s not in scenes:
            p = ROOT/'outputs/checkpoint_review/seed2_25_20261103/scenes'/s
            scenes[s] = dict(geometry=read_json(p/'geometry.json'), image='data:image/png;base64,'+base64.b64encode((p/'floorplan.png').read_bytes()).decode())
    template = (ROOT/'core/crossing_campaign_template.html').read_text()
    page = template.split('<script id="payload"')[0]
    panel = (ROOT/'core/crossing_campaign_panel.html').read_text().split('<section class="campaign"')[0]
    panel += '''<section class="campaign"><h2>完整过程：先走错 → 复位到存档 → 再走</h2>
<p>选择一个恢复组即可连续播放全过程。两个恢复组共用首次走错记录、各自独立复位；不是一条任务连续接受两次救援。</p>
<div id="armChoices" class="runChoices"></div><p id="runDescription"></p></section>'''
    page = page.replace('__PANEL__', panel).replace('Crossing · 迭代离线复核', 'Oracle · 走错与复位全过程')
    page = re.sub(r'<div class="notice">.*?</div>', '<div class="notice">红线：存档后首次走错的实际路线；橙色虚线箭头：复位跳转，不是行走；绿线／紫线：复位后的实际动作。两条进度条按完整回放帧前进，日志动作编号在复位时回退。</div>', page, flags=re.S)
    page = page.replace('<canvas id="map"', '<div id="phaseBanner" role="status"></div><div id="timelineEvents" class="controls"></div><canvas id="map"')
    page = page.replace('<div class="legend">', '<div id="restoreEvidence"></div><div class="legend">', 1)
    page = page.replace('当前观测与模型判断', '当前实际 RGB 与 Oracle 审阅').replace('展开本次输入的历史画面与动作', '展开本次实际审阅的历史画面')
    page = page.replace('缩略图只包含本次实际输入的画面，点击可跳到相应时刻。', '缩略图仅来自当前审阅的历史请求；点击查看对应记录。')
    css = '''<style>[hidden]{display:none!important}.stats{grid-template-columns:repeat(6,1fr)}
#phaseBanner{padding:10px 12px;font-weight:700;background:#eef4fc;border-left:5px solid #2377bb;margin:8px 0;white-space:pre-line}
#phaseBanner.error{background:#fff0f1;border-color:#d64045}#phaseBanner.restore{background:#fff4df;border-color:#d48107}
#timelineEvents button{font-size:12px}#timelineEvents button.active{border:2px solid #2377bb}
#restoreEvidence{border:2px solid #d48107;border-radius:8px;padding:10px;background:#fffaf0;margin:12px 0}
.restorePair{display:grid;grid-template-columns:1fr 40px 1fr;align-items:center;gap:6px}.restorePair button{padding:5px;font-size:12px;text-align:left}.restorePair img{display:block;width:100%;aspect-ratio:4/3;object-fit:contain}.restoreArrow{font-size:26px;text-align:center;color:#ba6c00}
#restoreEvidence p{font-size:12px}.runChoice{white-space:pre-line}button:disabled{opacity:.5;cursor:default}#playError{background:#fff0dc;border-color:#d48107;font-weight:700}
@media(max-width:900px){.stats{grid-template-columns:repeat(3,1fr)}}
</style>'''
    page = page.replace('</head>', css+'</head>')
    page = page.replace('<button id="prev">', '<button id="playError">播放走错 → 复位 → 续走</button><button id="prev">')
    js = (ROOT/'core/oracle_checkpoint_template.js').read_text()
    data = dict(cases=cases, images=images, scenes=scenes, counts=counts, format='oracle-checkpoint-chronological-v2')
    page += '<script>const B='+json.dumps(data, ensure_ascii=False).replace('</', '<\\/')+';'+js+'</script></body></html>'
    from fontTools import subset
    from fontTools.ttLib import TTFont
    cfg = read_json(ROOT/'core/crossing_visualization_template.json')
    font = TTFont(cfg['font'], fontNumber=0)
    sub = subset.Subsetter()
    sub.populate(text=page)
    sub.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    font_css = '<style>@font-face{font-family:ReviewSans;src:url(data:font/ttf;base64,'+base64.b64encode(buf.getvalue()).decode()+')}body,button,input,textarea,select,pre{font-family:ReviewSans,system-ui,sans-serif}</style>'
    page = page.replace('</head>', font_css+'</head>')
    (dest/'oracle_checkpoint_timeline.html').write_text(page)
    (dest/'font_license.txt').write_text(Path(cfg['font_license']).read_text())
    (dest/'controller_source.js').write_text(js)
    (dest/'export_source.py').write_text(Path(__file__).read_text())
    audit = dict(counts=counts, source_observations_sha256=sources, cases=[])
    for c in cases:
        audit['cases'].append(dict(episode_id=c['episode_id'], paired=c['paired'], timelines={
            arm: dict(frames=len(t['frames']), events=t['events'], restore_index=t['restore_index']) for arm, t in c['timelines'].items()}))
    (dest/'timeline_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2))
    (dest/'manifest.json').write_text(json.dumps(dict(template='crossing-review-v1 chronological Oracle adapter v2',
        cases=len(cases), source_template_sha256=hashlib.sha256(template.encode()).hexdigest(),
        html_sha256=hashlib.sha256(page.encode()).hexdigest(), navigation_rerun=False, git_head_record='Original experiment version unchanged; visualization source snapshots included.'), indent=2))
    print(json.dumps(dict(destination=str(dest), bytes=len(page.encode()), counts=counts), ensure_ascii=False))


if __name__ == '__main__':
    main()
