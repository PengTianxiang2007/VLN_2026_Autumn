"""Build the local JEV sampling viewer from an existing HTML or site ZIP.

Standard library only. No model calls, downloads or server publishing.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
ASSET_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.ttf', '.woff', '.woff2', '.otf'}


def asset_path(value):
    path = PurePosixPath(value)
    if (not value or '\\' in value or path.is_absolute() or '..' in path.parts
            or path.parts[0] != 'assets' or path.suffix.lower() not in ASSET_SUFFIXES
            or ':' in value or '?' in value or '#' in value):
        raise ValueError('Expected a relative static asset under assets/: ' + value)
    return path


def extract_payload(html):
    match = re.search(r'<script\b[^>]*\bid=["\']payload["\'][^>]*>(.*?)</script>', html, re.S)
    if not match:
        raise ValueError('Source HTML has no payload script')
    payload = json.loads(match.group(1))
    for key in ['cases', 'summary', 'images', 'maps', 'prompt_en', 'prompt_zh']:
        if key not in payload:
            raise ValueError('Missing payload field: ' + key)
    if not payload['cases']:
        raise ValueError('Source has no trajectories')
    for case in payload['cases']:
        case.setdefault('real_episode_id', case['episode_id'].split(' · ')[0])
        if not case['frames']:
            raise ValueError('Empty trajectory: ' + case['episode_id'])
        for i, frame in enumerate(case['frames']):
            if frame['frame'] != i:
                raise ValueError('Expected consecutive zero-based observation frames')
            frame.pop('qwen', None)
    for key in ['qwen_mean_score', 'qwen_score_histogram', 'comparison']:
        payload['summary'].pop(key, None)
    payload['tag'] = 'jev_sampling_lab_20261112'
    return payload


def export(source, destination, html_entry=None):
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError('Choose a new destination; existing exports are preserved: ' + str(destination))
    template = (ROOT / 'core/jev_sampling_lab/template.html').read_text(encoding='utf-8')
    if template.count('@@PAYLOAD_JSON@@') != 1:
        raise ValueError('Expected one template payload placeholder')
    with ExitStack() as stack:
        if source.suffix.lower() == '.zip':
            archive = stack.enter_context(ZipFile(source))
            entries = [n for n in archive.namelist() if n.lower().endswith('.html')]
            if html_entry is None:
                if len(entries) != 1:
                    raise ValueError('ZIP must have one HTML entry, or use --html-entry')
                html_entry = entries[0]
            if html_entry not in entries:
                raise ValueError('HTML entry is not in the ZIP')
            source_bytes = archive.read(html_entry)
            parent = PurePosixPath(html_entry).parent

            def read_asset(relative):
                return archive.read((parent / asset_path(relative)).as_posix())

            def check_asset(relative):
                archive.getinfo((parent / asset_path(relative)).as_posix())
        else:
            if source.suffix.lower() not in {'.html', '.htm'}:
                raise ValueError('Expected an HTML file or site ZIP')
            source_bytes = source.read_bytes()
            parent = source.parent

            def local_asset(relative):
                path = (parent / asset_path(relative)).resolve()
                if not path.is_relative_to(parent) or not path.is_file():
                    raise ValueError('Missing asset or asset outside source folder: ' + relative)
                return path

            def read_asset(relative):
                return local_asset(relative).read_bytes()

            def check_asset(relative):
                local_asset(relative)

        payload = extract_payload(source_bytes.decode('utf-8-sig'))
        # Keep inline images if the supplied HTML already contains them.
        assets = {v for v in payload['images'].values() if not v.startswith('data:image/')}
        assets.update(re.findall(r'url\((assets/[^)]+)\)', template))
        for relative in assets:
            check_asset(relative)
        destination.mkdir(parents=True, exist_ok=False)
        for relative in sorted(assets):
            target = destination / asset_path(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(read_asset(relative))

    serialized = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).replace('</', '<\/')
    (destination / 'index.html').write_text(template.replace('@@PAYLOAD_JSON@@', serialized), encoding='utf-8', newline='\n')
    for original, name in [
        ('core/jev_sampling_lab/app.js', 'app.js'),
        ('core/jev_online_filter_v001.js', 'online_filter.js'),
        ('core/jev_online_sampler_v001.js', 'online_sampler_v001.js'),
    ]:
        shutil.copyfile(ROOT / original, destination / name)
    files = ['index.html', 'app.js', 'online_filter.js', 'online_sampler_v001.js', *sorted(assets)]
    manifest = {
        'entry': 'index.html', 'local_only': True, 'source_name': source.name,
        'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
        'sampling_versions': ['v001'], 'sampling_default': False,
        'curves_default': {'raw': True, 'filtered': True},
        'display_mode': 'full_recording', 'sampling_input_mode': 'current_prefix',
        'cases': len(payload['cases']), 'assets': len(assets),
        'files': [{'path': name, 'sha256': hashlib.sha256((destination / name).read_bytes()).hexdigest()}
                  for name in files],
    }
    (destination / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path, help='Existing full-wave site ZIP, or HTML with adjacent assets')
    parser.add_argument('--destination', required=True, type=Path, help='A new local output folder')
    parser.add_argument('--html-entry', help='HTML member name when the ZIP contains several pages')
    args = parser.parse_args()
    result = export(args.source, args.destination, args.html_entry)
    print(json.dumps({'entry': str(args.destination / 'index.html'), 'cases': result['cases'],
                      'assets': result['assets'], 'local_only': True}, ensure_ascii=False))


if __name__ == '__main__':
    main()
