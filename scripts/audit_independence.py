"""Verify local interpreters, environment hooks and symlinks do not use an old project."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forbid-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    forbidden = str(args.forbid_root.resolve())
    errors = []
    interpreters = {}
    environments = [
        ('streamvln', ROOT / 'backbone/streamvln/.venv', '3.9'),
        ('janusvln', ROOT / 'backbone/janusvln/.venv', '3.9'),
        ('vlnverse', ROOT / 'benchmarks/vlnverse/.venv', '3.10'),
    ]
    for model, env, version in environments:
        if env.is_symlink():
            errors.append('Environment must be an independent directory: ' + str(env))
        pending = [env]
        while pending:
            with os.scandir(pending.pop()) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    if entry.is_symlink():
                        resolved = str(path.resolve())
                        if forbidden in resolved:
                            errors.append('Old symlink: ' + str(path))
                        if resolved.startswith('/tmp/'):
                            errors.append('Temporary runtime dependency: ' + str(path))
                        if not path.exists():
                            errors.append('Broken environment symlink: ' + str(path))
                    elif entry.is_dir(follow_symlinks=False) and entry.name != '__pycache__':
                        pending.append(path)
        site = env / ('lib/python' + version + '/site-packages')
        paths = [env / 'pyvenv.cfg', *list((env / 'bin').iterdir())]
        for pattern in ['*.pth', '*.egg-link', '__editable__*finder.py', '*.dist-info/direct_url.json']:
            paths.extend(site.glob(pattern))
        for path in paths:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
                continue
            data = path.read_bytes()
            if b'\0' not in data and forbidden.encode() in data:
                errors.append('Old environment configuration: ' + str(path))
        code = 'import sys,json; print(json.dumps(dict(executable=sys.executable,prefix=sys.prefix,base_prefix=sys.base_prefix,path=sys.path)))'
        info = json.loads(subprocess.check_output([str(env / 'bin/python'), '-c', code], text=True,
                                                  env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH='')))
        if forbidden in json.dumps(info):
            errors.append('Interpreter still depends on old project: ' + model)
        if not Path(info['base_prefix']).is_relative_to(ROOT):
            errors.append('Base Python is outside the project: ' + model)
        interpreters[model] = info
    report = dict(passed=not errors, forbidden_root=forbidden, interpreters=interpreters, errors=errors)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
