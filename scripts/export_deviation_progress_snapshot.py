"""Restore the frozen 34-case deviation/progress viewer without model calls.

Use the original site ZIP, an HTML with adjacent assets/, or a site directory.
Only Python's standard library is required. Existing destinations are preserved.
"""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path, PurePosixPath
import re
import shutil
from zipfile import ZipFile

from export_jev_sampling_lab import asset_path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'experiments/deviation_progress/v003/run_20261112_05/snapshot'


def export(source, destination, html_entry=None):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists():
        raise FileExistsError('Choose a new destination: ' + str(destination))
    html = (SNAPSHOT / 'index.html').read_text(encoding='utf-8')
    match = re.search(r'<script id="payload" type="application/json">(.*?)</script>', html, re.S)
    payload = json.loads(match.group(1))
    assets = set(payload['images'].values()) | set(re.findall(r'url\((assets/[^)]+)\)', html))
    for relative in assets:
        asset_path(relative)
    with ExitStack() as stack:
        if source.suffix.lower() == '.zip':
            archive = stack.enter_context(ZipFile(source))
            entries = [name for name in archive.namelist() if name.lower().endswith('.html')]
            if html_entry is None:
                if len(entries) != 1:
                    raise ValueError('ZIP must contain one HTML, or specify --html-entry')
                html_entry = entries[0]
            if html_entry not in entries:
                raise ValueError('HTML entry not found in ZIP')
            parent = PurePosixPath(html_entry).parent
            for relative in assets:
                archive.getinfo((parent / asset_path(relative)).as_posix())

            def read_asset(relative):
                return archive.read((parent / asset_path(relative)).as_posix())
        else:
            parent = source if source.is_dir() else source.parent

            def local_asset(relative):
                path = (parent / asset_path(relative)).resolve()
                if not path.is_relative_to(parent) or not path.is_file():
                    raise ValueError('Missing asset or asset outside source: ' + relative)
                return path

            for relative in assets:
                local_asset(relative)

            def read_asset(relative):
                return local_asset(relative).read_bytes()

        shutil.copytree(SNAPSHOT, destination)
        for relative in sorted(assets):
            target = destination / asset_path(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(read_asset(relative))
    return {'entry': str(destination / 'index.html'), 'cases': len(payload['cases']),
            'assets': len(assets), 'local_only': True, 'model_calls': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--html-entry')
    args = parser.parse_args()
    print(json.dumps(export(args.source, args.destination, args.html_entry), ensure_ascii=False))


if __name__ == '__main__':
    main()
