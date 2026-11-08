"""Validate new camera captures and export a Chinese offline image review, without inference."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile


PAGE = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Crossing 360°画面补采</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#edf1f7;color:#16253b;font:16px/1.65 "Microsoft YaHei","Noto Sans CJK SC",sans-serif}
header{background:#12243e;color:white;padding:25px 4vw}h1{font-size:26px;margin:0 0 6px}header p{margin:3px 0;color:#dae4f3}
main{max-width:1500px;margin:auto;padding:24px}section{background:white;border-radius:12px;padding:22px;margin-bottom:20px;box-shadow:0 2px 12px #12243e0a}
h2{font-size:21px;margin:0 0 12px}h3{margin:0 0 8px;font-size:17px}select,button{font:inherit;padding:7px 12px;border:1px solid #acb9cc;border-radius:7px;background:white;color:#16253b}
label{display:inline-flex;align-items:center;gap:12px}select{max-width:100%}.note{color:#4f6178;margin:8px 0}.badge{display:inline-block;padding:5px 12px;border-radius:7px;background:#fff3c9;color:#70520d}
.summary{display:grid;grid-template-columns:420px 1fr;gap:26px;align-items:start}.summary img{width:100%;border-radius:7px}.info p{margin:8px 0}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}figure{margin:0;border:1px solid #d4dfed;border-radius:10px;overflow:hidden;background:#f5f8fc}
figure button{padding:0;border:0;background:transparent;width:100%;display:block;cursor:zoom-in}figure img{display:block;width:100%;aspect-ratio:4/3;object-fit:contain}
figcaption{padding:10px 12px;font-weight:600}.sub{font-size:13px;font-weight:400;color:#52637a}.legend{background:#eff5ff;padding:13px;border-radius:8px}
dialog{max-width:min(1100px,96vw);padding:15px;border:0;border-radius:12px}dialog::backdrop{background:#07101de0}dialog img{display:block;max-width:100%;max-height:77vh;margin:auto}dialog p{margin:0 0 8px}dialog button{float:right}
code{font-size:13px;word-break:break-all}details{margin-top:15px}footer{font-size:13px;color:#52637a;padding:0 24px 25px}
@media(max-width:1050px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.summary{grid-template-columns:1fr 1fr}}
@media(max-width:650px){.grid,.summary{grid-template-columns:1fr}main{padding:12px}section{padding:14px}select{width:100%}label{display:block}}
</style></head><body><header><h1>Crossing 360°画面补采 · 原十条任务</h1>
<p>10条任务 · 8个场景 · 9个不同Crossing · 72张新画面 · 每点8个方向</p>
<p>当前阶段：只完成画面采集。支路有哪些、应该选哪条，尚未让模型判断。</p></header>
<main><section><label for="case">选择任务 <select id="case"></select></label><p class="note" id="shared"></p></section>
<section><h2 id="caseTitle"></h2><div class="summary"><div><h3>旧版判断时看到的原帧</h3><img id="original" alt="原判断帧"><p class="note" id="frame"></p></div>
<div class="info"><span class="badge">支路识别与选路：待模型判断</span><p id="position"></p><p id="offset"></p>
<p>下方八张图是在标定点新采集的周围观察；光心固定，只旋转相机。原录像未保存相机朝向，故这里采用固定的世界坐标方位编号。</p>
<p class="legend">0°＝场景+X；90°＝+Y；180°＝−X；270°＝−Y。角度按俯视逆时针递增。编号V0–V7表示画面，不表示支路。实际支路可同时出现在相邻多张图中。</p>
<p>每张640×480，水平视场90°，相邻中心相差45°，俯视15°。点击图片可放大。</p>
<details><summary>原始任务指令（英文）</summary><p id="instruction"></p></details></div></div></section>
<section><h2>该Crossing周围360°画面</h2><div id="views" class="grid"></div></section></main>
<footer>原轨迹seed=2；Isaac Sim 4.5直接读取原场景资产。静态补采不包含模型推理、导航执行或成功率评测。第9、10条共用同一Crossing的8张图，各自原录像仍独立保留。</footer>
<dialog id="zoom"><button id="close">关闭</button><p id="zoomTitle"></p><img id="large" alt="放大的Crossing画面"></dialog>
<script id="payload" type="application/json">__DATA__</script><script>
const data=JSON.parse(document.getElementById('payload').textContent),select=document.getElementById('case');
for(const c of data.cases){const o=document.createElement('option');o.value=c.sample_id;o.textContent=`${c.sample_id} · ${c.episode_id} · ${c.crossing_id}`;select.append(o)}
const directions={0:'+X',45:'+X / +Y',90:'+Y',135:'−X / +Y',180:'−X',225:'−X / −Y',270:'−Y',315:'+X / −Y'};
function render(){const c=data.cases.find(x=>x.sample_id===select.value),p=data.panoramas[c.panorama_id];
 document.getElementById('caseTitle').textContent=`${c.sample_id} · ${c.scene} · ${c.crossing_id}`;
 document.getElementById('original').src=data.images[c.checkpoint_image];
 document.getElementById('frame').textContent=`旧版判断帧：F${String(c.checkpoint_frame).padStart(4,'0')}。`;
 document.getElementById('position').textContent=`新采集点：X=${p.position[0].toFixed(4)}m，Y=${p.position[1].toFixed(4)}m，相机Z=${p.position[2].toFixed(3)}m。`;
 document.getElementById('offset').textContent=`旧判断帧机器人位置距标定点：${c.checkpoint_to_crossing_distance_m.toFixed(3)}m。`;
 document.getElementById('instruction').textContent=c.instruction;
 const shared=data.cases.filter(x=>x.panorama_id===c.panorama_id).map(x=>x.sample_id);
 document.getElementById('shared').textContent=shared.length>1?`共用该Crossing画面的任务：${shared.join('、')}；两条任务的旧判断帧不同。`:'该Crossing对应本条任务。';
 const grid=document.getElementById('views');grid.replaceChildren();
 for(const v of p.views){const fig=document.createElement('figure'),b=document.createElement('button'),im=document.createElement('img'),cap=document.createElement('figcaption');
 im.src=data.images[v.path];im.alt=`${v.view_id}，${v.yaw_deg}度`;b.append(im);
 cap.textContent=`${v.view_id} · ${v.yaw_deg}° · ${directions[v.yaw_deg]}`;
 b.onclick=()=>{document.getElementById('large').src=im.src;document.getElementById('zoomTitle').textContent=`${c.sample_id} / ${c.crossing_id} — ${cap.textContent}`;document.getElementById('zoom').showModal()};
 fig.append(b,cap);grid.append(fig)}}
select.onchange=render;document.getElementById('close').onclick=()=>document.getElementById('zoom').close();render();
</script></body></html>'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--destination', type=Path, required=True)
    args = ap.parse_args()
    out, dest = args.output.resolve(), args.destination.resolve()
    manifest = json.loads((out / 'manifest.json').read_text())
    status = json.loads((out / 'status.json').read_text())
    assert status['phase'] == 'capture_complete' and status['owned_processes_exited']
    dest.mkdir(parents=True, exist_ok=False)
    from PIL import Image, ImageDraw
    import numpy as np
    images, panoramas, cases, warnings = {}, {}, [], []
    seen = set()
    def add_image(key, path, expected):
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected, path
        images[key] = 'data:image/png;base64,' + base64.b64encode(raw).decode()
    for job in manifest['panoramas']:
        meta = json.loads((out / 'panoramas' / job['panorama_id'] / 'metadata.json').read_text())
        assert [v['yaw_deg'] for v in meta['views']] == list(range(0, 360, 45))
        assert meta['model_calls'] == 0 and meta['navigation_actions'] == 0
        # Isaac's ReferenceTime numerator is not an independent render counter.
        # It remains zero when delta_time=0; freshness is checked via distinct RGB
        # plus recorded camera poses and the explicit awaited render in the worker.
        assert len(meta['views']) == 8
        sheet = Image.new('RGB', (1280, 540), 'white')
        draw = ImageDraw.Draw(sheet)
        for i, v in enumerate(meta['views']):
            assert math.dist(v['position'], job['position']) < 1e-5
            assert abs((v['actual_yaw_deg'] - v['yaw_deg'] + 180) % 360 - 180) < 1e-3
            assert abs(v['pitch_down_deg'] - 15) < 1e-3
            assert v['sha256'] not in seen
            seen.add(v['sha256'])
            path = out / v['path']
            with Image.open(path) as im:
                assert im.size == (640, 480) and im.mode == 'RGB'
                rgb = np.asarray(im)
                assert float(rgb.std()) >= 2
                sheet.paste(im.resize((320, 240)), ((i % 4) * 320, (i // 4) * 270 + 30))
            draw.text(((i % 4) * 320 + 8, (i // 4) * 270 + 8), f'{job["crossing_id"]}  {v["view_id"]} / {v["yaw_deg"]} deg', fill='black')
            if v['dark_fraction'] > .6 or v['white_fraction'] > .6:
                warnings.append(dict(path=v['path'], dark_fraction=v['dark_fraction'], white_fraction=v['white_fraction']))
            add_image(v['path'], path, v['sha256'])
        sheet.save(dest / (job['panorama_id'] + '.jpg'), quality=90)
        panoramas[job['panorama_id']] = meta
    for c in manifest['cases']:
        old = next(i for i in c['original_images'] if i['frame'] == c['checkpoint_frame'])
        key = c['sample_id'] + '_original'
        add_image(key, Path(old['path']), old['sha256'])
        cases.append(dict(c, checkpoint_image=key))
    assert len(seen) == 72 and len(cases) == 10 and len(panoramas) == 9
    payload = json.dumps(dict(cases=cases, panoramas=panoramas, images=images), ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    html = dest / 'crossing_360_zh.html'
    page = PAGE.replace('__DATA__', payload)
    # Reuse the licensed local font so the offline review also works without CJK system fonts.
    from fontTools import subset
    from fontTools.ttLib import TTFont
    root = Path(__file__).resolve().parents[1]
    fonts = json.loads((root / 'core/crossing_visualization_template.json').read_text())
    font = TTFont(fonts['font'], fontNumber=0)
    sub = subset.Subsetter()
    sub.populate(text=PAGE + json.dumps(cases, ensure_ascii=False))
    sub.subset(font)
    buffer = io.BytesIO()
    font.save(buffer)
    css = '<style>@font-face{font-family:PanoramaSans;src:url(data:font/ttf;base64,' + base64.b64encode(buffer.getvalue()).decode() + ") format('truetype')}body,button,select{font-family:PanoramaSans,sans-serif}</style>"
    page = page.replace('</head>', css + '</head>')
    license_text = Path(fonts['font_license']).read_text()
    page = page.replace('</body>', '<script type="text/plain" id="font-license">' + license_text.replace('</', '<\\/') + '</script></body>')
    html.write_text(page)
    validation = dict(status='passed_automated', unique_images=72, cases=10, panoramas=9, case_image_references=80,
                       source_images_verified=10, fixed_optical_centers=True, yaw_coverage_deg=360,
                       horizontal_fov_deg=90, adjacent_yaw_step_deg=45, no_duplicate_rgb=True,
                       static_render_reference_time_may_repeat=True, model_calls=0, gpu_processes_exited=True,
                       exposure_review_flags=warnings, visual_review='pending',
                       exported_at=datetime.now(timezone.utc).isoformat(), html_sha256=hashlib.sha256(html.read_bytes()).hexdigest())
    (dest / 'validation.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2) + '\n')
    with zipfile.ZipFile(dest / 'crossing_360_images.zip', 'x', zipfile.ZIP_DEFLATED, compresslevel=3) as z:
        z.write(out / 'manifest.json', 'manifest.json')
        for path in sorted((out / 'panoramas').rglob('*')):
            if path.is_file():
                z.write(path, str(path.relative_to(out)))
        z.writestr('README.txt', 'Crossing v002 capture: 10 cases, 9 unique points, 8 views each.\n'
                   'Yaw: 0=world+X, 90=+Y, 180=-X, 270=-Y. Optical center fixed per point.\n'
                   'No route-choice inference performed. Original trajectory context paths in manifest are server references.\n')
    print(json.dumps(dict(validation=validation, html=str(html), bytes=html.stat().st_size), ensure_ascii=False))


if __name__ == '__main__':
    main()
