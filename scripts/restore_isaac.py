"""Restore Isaac 4.5 from the existing verified archive, without downloading it."""
import argparse
from pathlib import Path
import sys
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from core.paths import resource_root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=PROJECT / '.runtime/isaac45')
    args = parser.parse_args()
    root = args.destination.resolve()
    marker = root / '.peng_extraction_complete'
    archive = resource_root() / 'software/VLNVerse/isaac-sim-4.5.0.zip'
    if not marker.exists():
        root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as package:
            for index, entry in enumerate(package.infolist()):
                target = root / entry.filename
                if not target.resolve().is_relative_to(root):
                    raise ValueError('Unsafe archive entry')
                if target.exists():
                    if not entry.is_dir() and target.stat().st_size != entry.file_size:
                        raise ValueError('Conflicting existing file: ' + str(target))
                    continue
                package.extract(entry, root)
                mode = entry.external_attr >> 16
                if mode and not entry.is_dir():
                    target.chmod(mode & 0o777)
                if index % 10000 == 0:
                    print('Extracted entries:', index, flush=True)
        marker.write_text('Isaac Sim 4.5 restored from existing Resource_Peng archive\n')
    link = PROJECT / '.runtime/isaac45'
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() and link.resolve() != root:
        raise ValueError('Conflicting runtime link')
    if not link.exists() and not link.is_symlink():
        link.symlink_to(root, target_is_directory=True)
    print('Runtime ready:', root, flush=True)


if __name__ == '__main__':
    main()
