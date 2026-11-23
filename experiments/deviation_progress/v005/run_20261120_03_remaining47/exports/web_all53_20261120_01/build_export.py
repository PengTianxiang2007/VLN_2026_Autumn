"""Assemble the two completed v005 runs and export the full 53-case replay."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[6]
SNAPSHOT = ROOT / 'outputs/deviation_progress/v005/all53_20261120_01'
RUNS = [ROOT / 'outputs/deviation_progress/v005' / name for name in
        ('run_20261120_02_qwen_gpu3', 'run_20261120_03_remaining47')]


def read(path):
    return json.loads(path.read_text())


def write(name, value):
    (SNAPSHOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    rows, sources, anchors, manifests = [], {}, {}, []
    for run in RUNS:
        assert read(run / 'status.json')['phase'] == 'complete'
        manifest = read(run / 'manifest.json')
        manifests.append(manifest)
        results = read(run / 'v005_results.json')
        nodes = read(run / 'retained_nodes_and_terminals.json')
        for row in results:
            label = f"C{row['case_number']:02d}"
            assert label not in sources
            sources[label] = str(run / 'run/cases' / label)
            anchors[row['episode_id']] = nodes[row['episode_id']]
            rows.append(row)
    rows.sort(key=lambda row: row['case_number'])
    assert [row['case_number'] for row in rows] == list(range(1, 54))
    for key in ('settings', 'prompt_sha256', 'dataset_manifest_sha256', 'frozen_nodes_sha256'):
        assert manifests[0][key] == manifests[1][key]
    counts = Counter()
    for row in rows:
        counts.update(row['outcomes'])
    SNAPSHOT.mkdir(parents=True, exist_ok=False)
    manifest = {key: manifests[0][key] for key in
                ('version', 'settings', 'trajectory_seed', 'prompt_sha256',
                 'dataset_manifest_sha256', 'frozen_nodes_sha256')}
    manifest.update(partial=False, cases=list(range(1, 54)),
                    source_runs=[str(run.relative_to(ROOT)) for run in RUNS],
                    created_at=datetime.now(timezone.utc).isoformat())
    write('manifest.json', manifest)
    write('status.json', dict(phase='complete', partial=False, included_cases=53,
                             verdicts=dict(counts), model_calls=sum(row['calls'] for row in rows)))
    write('v005_results.json', rows)
    write('case_sources.json', sources)
    write('retained_nodes_and_terminals.json', anchors)
    prompts = Path('source/experiments/deviation_progress/v005')
    (SNAPSHOT / prompts).mkdir(parents=True)
    for lang in ('zh', 'en'):
        shutil.copy2(RUNS[0] / prompts / f'prompt_{lang}.txt', SNAPSHOT / prompts)
    subprocess.run([
        sys.executable, '-B', str(ROOT / 'scripts/export_deviation_progress_v004_replay.py'),
        '--run', str(SNAPSHOT),
        '--template', str(ROOT / 'outputs/deviation_progress/v003/run_20261118_01_qwen27b/exports/terminal53_01/index.html'),
        '--output', str(SNAPSHOT / 'exports/web_all53_20261120_01'),
        '--online', str(ROOT / 'outputs/visualization_publishing/qwen_v005_all53_web_20261120_01'),
    ], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
