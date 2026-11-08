"""Audit and export a completed Crossing iteration using the default HTML template (CPU only)."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess

from export_crossing_campaign import build as export_report, digest, ROOT


def read(path):
    return json.loads(path.read_text())


def build(output, tag, compare_tags=None, annotations=None, destination=None, audit_python=None):
    output = output.resolve()
    protocol_path = output/'protocol.json'
    if protocol_path.exists() and read(protocol_path).get('kind') == 'crossing_lite':
        from export_crossing_lite import build as export_lite
        protocol = read(protocol_path)
        if tag != protocol['tag'] or compare_tags or annotations:
            raise ValueError('Lite scoring requires its registered tag and native score-only export')
        destination = destination or output/'exports'/('run_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
        return export_lite(output, destination)
    if Path(tag).name != tag:
        raise ValueError('Expected a run tag, not a path')
    scores = read(output/'runs'/tag/'scores.json')
    if not scores['summary']['complete']:
        raise ValueError('Only completed iterations can use the final report template')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
    destination = destination or output/'exports'/tag/('run_'+stamp)
    destination.mkdir(parents=True, exist_ok=False)
    status_path = destination/'status.json'

    def status(phase, **fields):
        status_path.write_text(json.dumps(dict(phase=phase, tag=tag,
            updated_at=datetime.now(timezone.utc).isoformat(), **fields), ensure_ascii=False, indent=2)+'\n')

    status('auditing_existing_results')
    try:
        source = destination/'source'
        source.mkdir()
        for name in ['export_crossing_iteration.py', 'build_crossing_review.py']:
            shutil.copy2(ROOT/'scripts'/name, source/name)
        (source/'git_head.txt').write_text(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True))
        (source/'tracked_worktree.diff').write_text(subprocess.check_output(['git', 'diff', '--',
            'scripts', 'core'], cwd=ROOT, text=True))
        # Include earlier exported versions of this split by default. Never launch another run.
        registered = {}
        for pointer in sorted((output/'runs').glob('*/visualization.json')):
            row = read(pointer)
            if row['tag'] != tag and row['split'] == scores['summary']['split']:
                registered[row['tag']] = row
        if compare_tags is None:
            compare_tags = sorted(registered, key=lambda t: registered[t]['created_at'])
        reports = {}
        for previous in compare_tags:
            if previous == tag:
                continue
            if Path(previous).name != previous:
                raise ValueError('Invalid comparison tag')
            pointer = output/'runs'/previous/'visualization.json'
            report = Path(read(pointer)['audited_report']) if pointer.exists() else (
                output/'reports'/(previous+'_review')/'crossing_dev8_review.html')
            if not report.exists():
                raise ValueError('Missing audited comparison report: '+previous)
            reports[previous] = report
        # Recompute in the original audit environment; Python 3.9 math.dist can differ by one ULP.
        audit_python = audit_python or ROOT/'benchmarks/vlnverse/.venv/bin/python'
        audit_destination = destination/'audited_report'
        subprocess.run([str(audit_python), '-B', str(ROOT/'scripts/build_crossing_review.py'),
                        '--output', str(output), '--tag', tag, '--destination', str(audit_destination)],
                       check=True, timeout=600)
        reports[tag] = audit_destination/'crossing_dev8_review.html'
        status('exporting_template', compared_tags=list(reports))
        exported = export_report(output, destination/'visualization', annotations=annotations,
                                 report_paths=reports)
        report = (destination/'visualization'/exported['report']).resolve()
        registration = dict(tag=tag, split=scores['summary']['split'], created_at=exported['created_at'],
            template_id=exported['template_id'], report=str(report), html_sha256=exported['html_sha256'],
            audited_report=str(reports[tag].resolve()), export_manifest=str((destination/'visualization/export_manifest.json').resolve()),
            compared_tags=list(reports), scores_sha256=digest(output/'runs'/tag/'scores.json'))
        pointer = output/'runs'/tag/'visualization.json'
        temp = pointer.with_suffix('.json.tmp')
        temp.write_text(json.dumps(registration, ensure_ascii=False, indent=2)+'\n')
        temp.replace(pointer)
        status('complete', **{k:v for k,v in registration.items() if k!='tag'})
        print(json.dumps(registration, ensure_ascii=False))
        return registration
    except BaseException as error:
        status('failed', error=f'{type(error).__name__}: {error}')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--compare-tags', nargs='*', help='Explicit previous versions; default: previously exported versions of this split')
    parser.add_argument('--annotations', type=Path)
    parser.add_argument('--destination', type=Path, help='New directory; otherwise use a timestamp under exports/<tag>')
    parser.add_argument('--audit-python', type=Path, help='Original audit interpreter; defaults to benchmarks/vlnverse/.venv/bin/python')
    args = parser.parse_args()
    build(args.output, args.tag, args.compare_tags, args.annotations, args.destination, args.audit_python)
