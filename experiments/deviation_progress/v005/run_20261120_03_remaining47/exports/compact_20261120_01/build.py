"""Package every v005 review while reusing existing same-frame WebP images."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[6]
SOURCE = ROOT / 'outputs/visualization_publishing/qwen_v005_all53_web_20261120_01'
DEST = ROOT / 'outputs/visualization_publishing/qwen_v005_all53_compact_download_20261120_01'
ARCHIVE = 'qwen_v005_all_53_compact_offline.zip'
ORIGINAL_URL = 'http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/qwen_v005_all_53_offline.zip'


def dump(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def main():
    DEST.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(SOURCE / 'qwen_v005_all_53_offline.zip') as src:
        html = src.read('index.html').decode()
        match = re.search(r'<script id="payload" type="application/json">(.*?)</script>', html, re.S)
        bundle = json.loads(match[1])
        mappings = {}
        for original_sha, original_file in bundle['v4']['originals'].items():
            display = bundle['images'][original_sha]
            assert original_file.endswith('.png') and display.endswith('.webp')
            mappings[original_sha] = dict(original_file=original_file, file=display,
                                         display_sha256=Path(display).stem)
            bundle['v4']['originals'][original_sha] = display

        def display_rows(rows):
            for row in rows:
                for img in row['images']:
                    info = mappings[img['sha256']]
                    assert img['file'] == info['original_file']
                    img.update(info)
            return rows

        for group in bundle['v4']['cases'].values():
            display_rows(group['rounds'])
        bundle['v4']['archiveFile'] = ARCHIVE
        payload = dump(bundle).replace('</', '<\\/')
        html = html[:match.start(1)] + payload + html[match.end(1):]
        notice_zh = '精简离线版：全部帧和文字保留；输入图共用同帧 WebP 展示副本，原始 PNG 哈希见 image_manifest.json。'
        notice_en = 'Compact offline edition: all frames and text are retained. Input images reuse same-frame WebP display copies; original PNG hashes are in image_manifest.json.'
        marker = "const cohortZh="
        assert marker in html
        # Add the disclosure to the existing language-aware notice, preserving the UI.
        html = html.replace("notice:'本次包含 '", "notice:'" + notice_zh + " 本次包含 '")
        html = html.replace("notice:'This release contains '", "notice:'" + notice_en + " This release contains '")
        omitted = {v['original_file'] for v in mappings.values()}
        retained = set(src.namelist()) - omitted
        required = set(bundle['images'].values()) | set(bundle['v4']['originals'].values())
        assert required <= retained
        manifest = dict(cases=53, rounds=272, replay_frames=4890, original_input_images=len(mappings),
                        image_representation='Existing same-frame 640x480 lossy WebP display copy; original PNG bytes excluded',
                        original_archive_url=ORIGINAL_URL, inputs=mappings)
        instructions = (notice_zh + '\n\n解压整个压缩包，双击 index.html。保持 assets 文件夹与页面相邻。\n'
                        '所有 53 条轨迹、272 轮回答、4,890 帧、地图、输入帧清单、累计进度和中英文 Prompt 均保留。\n'
                        'images[].sha256 为模型实际输入 PNG 的哈希；file 为包内 WebP 路径，display_sha256 为展示副本哈希。\n'
                        '模型原答未修改。需要原始 PNG 字节时下载无损包：' + ORIGINAL_URL + '\n\n'
                        + notice_en + '\nExtract the entire archive, then open index.html. Keep assets beside it.\n'
                        'All 53 cases, 272 answers, 4,890 frames, maps, input manifests, progress and bilingual prompts are retained.\n'
                        'images[].sha256 identifies the actual input PNG; file and display_sha256 identify the packaged WebP copy.\n'
                        'Verbatim model answers are unchanged. Original PNG bytes are available in: ' + ORIGINAL_URL + '\n')
        with tempfile.TemporaryDirectory(prefix='vln-v005-compact-', dir='/tmp') as work:
            packed = Path(work) / ARCHIVE
            with zipfile.ZipFile(packed, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as dst:
                for item in src.infolist():
                    name = item.filename
                    if name in omitted:
                        continue
                    if name == 'index.html':
                        data = html.encode()
                    else:
                        data = src.read(name)
                        if name.endswith('_model_returns.json'):
                            data = dump(display_rows(json.loads(data))).encode()
                        elif name == 'all_rounds.jsonl':
                            rows = display_rows([json.loads(line) for line in data.splitlines() if line])
                            data = ''.join(dump(row)+'\n' for row in rows).encode()
                    dst.writestr(name, data)
                dst.writestr('image_manifest.json', dump(manifest))
                dst.writestr('README.txt', instructions)
            shutil.copy2(packed, DEST / ARCHIVE)
        check = Path('/tmp/vln_v005_compact_check_20261120_01')
        check.mkdir(exist_ok=False)
        (check / 'index.html').write_text(html)
        (check / 'assets').symlink_to(SOURCE / 'assets', target_is_directory=True)
    size = (DEST / ARCHIVE).stat().st_size
    page = ('<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>Qwen v005 · 53 条完整离线包 / Complete offline archive</title>'
            '<style>body{max-width:760px;margin:50px auto;padding:20px;font:18px/1.7 system-ui}button{margin-right:10px;padding:8px}a{color:#165fa5}</style>'
            '<button onclick="setLang(\'zh\')">中文</button><button onclick="setLang(\'en\')">English</button>'
            '<section id="zh"><h1>Qwen v005 · 53 条完整离线包</h1>'
            f'<p><a href="{ARCHIVE}" download>下载精简离线包（{size/1e6:.1f} MB）</a></p>'
            '<p>保留全部 53 条、272 轮原答、4,890 帧、地图、输入帧清单、累计进度和中英文 Prompt。</p>'
            '<p>图片共用同帧、同分辨率 WebP 压缩副本；原始 PNG 哈希保留。下载后完整解压，双击 index.html。</p>'
            f'<p><a href="{ORIGINAL_URL}">需要原始 PNG 时下载无损完整包</a></p></section>'
            '<section id="en" hidden><h1>Qwen v005 · Complete 53-case offline archive</h1>'
            f'<p><a href="{ARCHIVE}" download>Download compact archive ({size/1e6:.1f} MB)</a></p>'
            '<p>All 53 cases, 272 verbatim answers, 4,890 frames, maps, input manifests, progress and bilingual prompts are retained.</p>'
            '<p>Images reuse same-frame, same-resolution WebP compressed copies. Original PNG hashes are retained. Extract the whole archive and open index.html.</p>'
            f'<p><a href="{ORIGINAL_URL}">Full archive with original PNG bytes</a></p></section>'
            '<script>function setLang(x){document.getElementById("zh").hidden=x!=="zh";document.getElementById("en").hidden=x!=="en";document.documentElement.lang=x}</script></html>')
    (DEST / 'index.html').write_text(page)
    report = dict(archive=ARCHIVE, bytes=size, source_bytes=(SOURCE/'qwen_v005_all_53_offline.zip').stat().st_size,
                  cases=53, rounds=272, frames=4890, removed_duplicate_png=len(omitted),
                  sha256=hashlib.sha256((DEST/ARCHIVE).read_bytes()).hexdigest(),
                  local_check=str(check/'index.html'))
    (DEST / 'build.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(dump(report), flush=True)


if __name__ == '__main__':
    main()
