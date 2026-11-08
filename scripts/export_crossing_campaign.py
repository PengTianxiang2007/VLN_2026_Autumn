"""Export audited Crossing iterations with the default standalone visualization template."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import html as html_module
import io
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_CONFIG = ROOT/'core/crossing_visualization_template.json'
DEFAULTS = json.loads(TEMPLATE_CONFIG.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Unexpected frozen template: ' + old[:70])
    return text.replace(old, new, 1)


def build(campaign, destination, annotations=None, font_path=None, font_license=None,
          tags=None, report_paths=None, filename='crossing_review_offline.html'):
    if destination.exists():
        raise ValueError('Use a new export directory; existing exports are immutable')
    if Path(filename).name != filename or not filename.endswith('.html'):
        raise ValueError('Expected an HTML basename')
    font_path = font_path or Path(DEFAULTS['font'])
    font_license = font_license or Path(DEFAULTS['font_license'])
    if report_paths is None:
        if tags is None:
            tags = [p.parent.name.removesuffix('_review') for p in
                    sorted((campaign/'reports').glob('*_review/crossing_dev8_review.html'))]
        report_paths = {tag: campaign/'reports'/(tag+'_review')/'crossing_dev8_review.html'
                        for tag in tags}
    if not report_paths:
        raise ValueError('No audited completed reports selected')
    runs, sources, original_hashes = {}, {}, {}
    for tag, report in report_paths.items():
        report = Path(report)
        audit = json.loads(report.with_name('verification.json').read_text())
        assert digest(report) == audit['html_sha256']
        data = json.loads(re.search(r'<script id="payload" type="application/json">(.*?)</script>',
                                   report.read_text(), re.S).group(1))
        assert data['tag'] == tag and data['summary']['complete']
        assert data['summary']['metrics'] == audit['metrics']
        assert len(data['cases']) == audit['cases'] > 0
        assert sum(len(c['snapshots']) for c in data['cases'].values()) == audit['verified_causal_requests']
        runs[tag] = data
        original_hashes[tag] = canonical(data)
        sources[tag] = dict(path=str(report), sha256=digest(report), payload_sha256=original_hashes[tag])
    images, image_ids = [], {}
    def intern(value):
        assert value.startswith('data:image/')
        if value not in image_ids:
            image_ids[value] = len(images)
            images.append(value)
        return image_ids[value]
    for data in runs.values():
        for case in data['cases'].values():
            for row in case['snapshots']:
                row['image'] = intern(row['image'])
            if 'history_images' in case:
                case['history_images'] = {f: intern(value) for f, value in case['history_images'].items()}
        for scene in data['maps'].values():
            scene['floorplan'] = intern(scene['floorplan'])
    # Verify lossless expansion of the compact payload against each audited report.
    for tag, data in runs.items():
        restored = json.loads(json.dumps(data))
        for case in restored['cases'].values():
            for row in case['snapshots']:
                row['image'] = images[row['image']]
            if 'history_images' in case:
                case['history_images'] = {f: images[value] for f, value in case['history_images'].items()}
        for scene in restored['maps'].values():
            scene['floorplan'] = images[scene['floorplan']]
        assert canonical(restored) == original_hashes[tag]
    supplied = json.loads(annotations.read_text()) if annotations else {}
    notes = dict(labels={tag: supplied.get('labels', {}).get(tag, tag) for tag in runs},
                 descriptions={tag: supplied.get('descriptions', {}).get(tag,
                     f"{tag} · {'独立验证' if data['summary']['split']=='validation' else '开发'} · "
                     f"{len(data['cases'])} 条轨迹 / {data['summary']['processed']} 个观测。结果与复核证据见下方。")
                     for tag, data in runs.items()},
                 bookmarks=[b for b in supplied.get('bookmarks', []) if b['tag'] in runs],
                 case_notes={tag: rows for tag, rows in supplied.get('case_notes', {}).items() if tag in runs})
    for bookmark in notes['bookmarks']:
        case = runs[bookmark['tag']]['cases'][bookmark['episode']]
        assert bookmark['frame'] in {r['frame'] for r in case['snapshots']}
    for tag, cases in notes['case_notes'].items():
        for episode, row in cases.items():
            frames = {s['frame'] for s in runs[tag]['cases'][episode]['snapshots']}
            assert set(row['frames']) <= frames
    initial = next((tag for tag, data in reversed(list(runs.items()))
                    if data['summary']['split']=='validation'), next(reversed(runs)))
    campaign_id = campaign.name+'_'+hashlib.sha256(str(campaign.resolve()).encode()).hexdigest()[:10]
    bundle = dict(campaign_id=campaign_id, initial=initial,
                  exported_at=datetime.now(timezone.utc).isoformat(), runs=runs, images=images, **notes)
    template_path = ROOT/DEFAULTS['template']
    template = template_path.read_text()
    panel_path = ROOT/DEFAULTS['panel']
    controller_path = ROOT/DEFAULTS['controller']
    template = replace_once(template, '__PANEL__', panel_path.read_text())
    template = replace_once(template, '__CONTROLLER__', controller_path.read_text())
    html = replace_once(template, '__DATA__', json.dumps(bundle, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c'))
    font_metadata = None
    font_bytes = None
    license_text = None
    if font_path is not None:
        from fontTools import subset
        from fontTools.ttLib import TTFont
        assert font_license is not None
        license_text = ('Embedded WenQuanYi Micro Hei subset, distributed under Apache-2.0. '
                        'Modified for this export by keeping only the required glyphs; outlines unchanged.\n\n'
                        + font_license.read_text() + '\n\n'
                        + Path('/usr/share/common-licenses/Apache-2.0').read_text())
        html = replace_once(html, '</body>', '<details class="audit"><summary>内嵌字体与许可</summary><pre>'
                            + html_module.escape(license_text) + '</pre></details></body>')
        font = TTFont(font_path, fontNumber=0)
        cmap = font.getBestCmap()
        needed = {ord(c) for c in html if not c.isspace()}
        missing_han = sorted(cp for cp in needed if (0x3400 <= cp <= 0x9fff or 0xf900 <= cp <= 0xfaff) and cp not in cmap)
        assert not missing_han, 'Font is missing Chinese characters: '+''.join(map(chr, missing_han))
        options = subset.Options();options.name_IDs = ['*'];options.name_languages = ['*']
        subsetter = subset.Subsetter(options=options);subsetter.populate(unicodes=needed & cmap.keys());subsetter.subset(font)
        stream = io.BytesIO();font.save(stream);font_bytes = stream.getvalue()
        font_css = "<style>@font-face{font-family:CrossingSans;src:url(data:font/ttf;base64,"+base64.b64encode(font_bytes).decode()+") format('truetype');font-style:normal;font-weight:400;font-display:block}body,button,select,input,textarea{font-family:CrossingSans,system-ui,sans-serif}pre{font-family:ui-monospace,Consolas,CrossingSans,monospace}</style>"
        html = replace_once(html, '</head>', font_css+'</head>')
        html = html.replace('px sans-serif', 'px CrossingSans, sans-serif')
        font_metadata = dict(source=str(font_path), source_sha256=digest(font_path),
                             subset_sha256=hashlib.sha256(font_bytes).hexdigest(), subset_bytes=len(font_bytes),
                             required_han_count=sum(0x3400 <= cp <= 0x9fff or 0xf900 <= cp <= 0xfaff for cp in needed),
                             missing_han=[], license='Apache-2.0', license_sha256=digest(font_license))
    assert not re.search(r'<script[^>]+src=|<link[^>]+href=|<video\b', html, re.I)
    destination.mkdir(parents=True)
    target = destination/filename
    target.write_text(html)
    source_dir = destination/'source';source_dir.mkdir()
    source_hashes = {}
    for path in [Path(__file__), panel_path, controller_path, template_path, TEMPLATE_CONFIG,
                 *([annotations] if annotations else [])]:
        saved = source_dir/path.name
        assert not saved.exists()
        saved.write_bytes(path.read_bytes());source_hashes[path.name] = digest(saved)
    if font_bytes is not None:
        (source_dir/'wqy_microhei_subset.ttf').write_bytes(font_bytes)
        (source_dir/'font_license.txt').write_text(license_text)
    manifest = dict(created_at=bundle['exported_at'], report=target.name, bytes=target.stat().st_size,
                    html_sha256=digest(target), sources=sources, source_hashes=source_hashes,
                    git_head_at_export=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    original_payload_hashes=original_hashes, image_pool_round_trip_verified=True,
                    images=len(images), run_count=len(runs),
                    unique_episodes=len({episode for data in runs.values() for episode in data['cases']}),
                    case_version_views=sum(len(data['cases']) for data in runs.values()),
                    observations=sum(len(c['snapshots']) for data in runs.values() for c in data['cases'].values()),
                    template_id=DEFAULTS['template_id'], template_reference_sha256=DEFAULTS['reference_sha256'],
                    initial_run=bundle['initial'], model_or_simulation_started=False,
                    inference_and_scores_unchanged=True, external_dependencies=False, embedded_font=font_metadata)
    (destination/'export_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(path=str(target), **manifest), ensure_ascii=False))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--annotations', type=Path)
    parser.add_argument('--tags', nargs='+', help='Completed audited versions to include, in display order')
    parser.add_argument('--filename', default='crossing_review_offline.html')
    parser.add_argument('--font', type=Path)
    parser.add_argument('--font-license', type=Path)
    args = parser.parse_args()
    build(args.campaign, args.destination, args.annotations, args.font, args.font_license,
          tags=args.tags, filename=args.filename)
