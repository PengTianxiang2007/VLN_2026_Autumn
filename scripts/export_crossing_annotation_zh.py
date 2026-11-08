"""Add the reviewed Chinese instructions to the existing standalone annotation file."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'outputs/crossing_annotation/seed2_69/run_20261106_01'
TRANSLATIONS = ROOT / 'experiments/crossing_analysis/seed2_annotation69/instructions_zh.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compact(data):
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def script_content(page, name):
    match = re.search(r'<script id="' + re.escape(name) + r'"[^>]*>([\s\S]*?)</script>', page)
    if not match:
        raise ValueError('Missing script: ' + name)
    return match


def replace_script(page, name, content):
    match = script_content(page, name)
    return page[:match.start(1)] + content + page[match.end(1):]


def export(out):
    out.mkdir(parents=True, exist_ok=False)
    write(out / 'status.json', dict(phase='exporting', gpu_used=False))
    original = SOURCE / 'crossing_annotation_69.html'
    source_hash = sha(original)
    page = original.read_text()
    data = json.loads(script_content(page, 'data').group(1))
    before_data = json.loads(script_content(page, 'data').group(1))
    translations = json.loads(TRANSLATIONS.read_text())
    assert translations['source_data_sha256'] == sha(SOURCE / 'data.json')
    assert set(translations['cases']) == {c['episode_id'] for c in data['cases']}
    for c in data['cases']:
        eid = c['episode_id']
        assert hashlib.sha256(c['instruction'].encode()).hexdigest() == translations['source_instruction_sha256'][eid]
        c['instruction_zh'] = translations['cases'][eid]
        assert re.search('[\u4e00-\u9fff]', c['instruction_zh'])
    data['instruction_language'] = 'zh-CN'
    data['instruction_translation'] = dict(source_sha256=sha(TRANSLATIONS), exported_at=datetime.now(timezone.utc).isoformat(), method=translations['translation_method'])
    controller = (ROOT / 'core/crossing_annotation.js').read_text()
    page = replace_script(page, 'data', compact(data))
    page = replace_script(page, 'controller', controller)
    config = json.loads((ROOT / 'core/crossing_visualization_template.json').read_text())
    characters = out / 'font_characters.txt'
    characters.write_text(''.join(sorted(set((ROOT / 'core/crossing_annotation_page.html').read_text() + controller + compact(data)))))
    font = out / 'annotation_font.ttf'
    code = 'from fontTools import subset; from fontTools.ttLib import TTFont; from pathlib import Path; import sys; f=TTFont(sys.argv[1],fontNumber=0); s=subset.Subsetter(); s.populate(text=Path(sys.argv[2]).read_text()); s.subset(f); f.save(sys.argv[3])'
    subprocess.run([str(ROOT / 'backbone/streamvln/.venv/bin/python'), '-c', code, config['font'], str(characters), str(font)], check=True)
    page, font_replacements = re.subn(r'data:font/ttf;base64,[A-Za-z0-9+/=]+', 'data:font/ttf;base64,' + base64.b64encode(font.read_bytes()).decode(), page, count=1)
    assert font_replacements == 1
    html = out / 'crossing_annotation_69_zh.html'
    html.write_text(page)
    write(out / 'data.json', data)
    # Only presentation fields may differ; all source instructions, frames, maps and labels are preserved.
    after = json.loads(script_content(page, 'data').group(1))
    for c in after['cases']:
        del c['instruction_zh']
    del after['instruction_language']
    del after['instruction_translation']
    assert after == before_data
    original_page = original.read_text()
    assert script_content(page, 'annotations').group(1) == script_content(original_page, 'annotations').group(1)
    media_checks = []
    for c in data['cases']:
        name = 'media-' + c['episode_id']
        content = script_content(page, name).group(1)
        assert content == script_content(original_page, name).group(1)
        media_checks.append(dict(episode_id=c['episode_id'],sha256=hashlib.sha256(content.encode()).hexdigest(),frames=len(c['frames'])))
    assert sha(original) == source_hash
    source_hashes = {}
    for rel in ['scripts/export_crossing_annotation_zh.py', 'core/crossing_annotation.js', 'scripts/check_crossing_annotation.cjs', str(TRANSLATIONS.relative_to(ROOT))]:
        dest = out / 'source' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dest)
        source_hashes[rel] = sha(dest)
    (out / 'workspace_status.txt').write_bytes(subprocess.check_output(['git', 'status', '--short'], cwd=ROOT))
    (out / 'workspace_diff.patch').write_bytes(subprocess.check_output(['git', 'diff', 'HEAD', '--binary'], cwd=ROOT))
    summary = dict(data['summary'], translated_instructions=69, instruction_language='zh-CN')
    write(out / 'summary.json', summary)
    write(out / 'manifest.json', dict(created_at=datetime.now(timezone.utc).isoformat(), dataset_id=data['dataset_id'], source_html=str(original.relative_to(ROOT)), source_html_sha256=source_hash,
                                      source_export_manifest_sha256=sha(SOURCE / 'manifest.json'), translation_sha256=sha(TRANSLATIONS), source_sha256=source_hashes,
                                      export_git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                                      original_english_preserved=True, original_annotation_state_preserved=True, media_preserved=media_checks,
                                      html_bytes=html.stat().st_size, html_sha256=sha(html), summary=summary))
    write(out / 'status.json', dict(phase='exported_pending_browser_check', summary=summary, gpu_used=False))
    print(json.dumps(dict(html=str(html), mib=round(html.stat().st_size/1024**2,2), **summary),ensure_ascii=False),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    export(parser.parse_args().output.resolve())
