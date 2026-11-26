"""Run the immutable evaluator with each predeclared rule in an isolated workspace."""
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

here = Path(__file__).resolve().parent
root = here.parents[3]
protocol = json.loads((here / 'protocol.json').read_text())
record = here.with_name(protocol['parent']).relative_to(root)
output = Path('outputs/crossing_checkpoint/online_sampling_v002') / record.name
dest = root / output.with_name(here.name)
first = json.loads((root / output / 'validation.json').read_text())
design = json.loads((root / output / 'design.json').read_text())
results = {'baseline': first['summary']['baseline'], 'near': first['summary']['near']}

for mode in protocol['modes']:
    if mode in results:
        continue
    with TemporaryDirectory(prefix='jev-sampling-') as folder:
        work = Path(folder)
        for file in protocol['sha256']:
            (work/file).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root/file, work/file)
        # Input data are shared read-only; evaluator output paths are isolated.
        for source in ['outputs/codex_tasks', 'outputs/crossing_checkpoint/online_sampling_v001']:
            (work/source).parent.mkdir(parents=True, exist_ok=True)
            (work/source).symlink_to(root/source, target_is_directory=True)
        (work/output).mkdir(parents=True)
        (work/record/'selection.json').write_text(json.dumps({
            'selected':mode, 'sha256':protocol['sha256'], 'basis':'prespecified alternative'}))
        subprocess.run(['node', 'scripts/evaluate_jev_sampling_v002.cjs', 'validation'],
                       cwd=work, check=True)
        with (dest/f'{mode}.json').open('x') as target:
            target.write((work/output/'validation.json').read_text())
        trial = json.loads((dest/f'{mode}.json').read_text())
        assert trial['summary']['baseline'] == results['baseline']
        for prior, row in zip(first['cases'], trial['cases'], strict=True):
            assert (prior['episode'],prior['reference']) == (row['episode'],row['reference'])
            prior['rows'][mode] = row['rows'][mode]
        results[mode] = trial['summary'][mode]

first['summary'] = results
with (dest/'validation.json').open('x') as f:
    json.dump(first, f, indent=2)
with (here/'summary.json').open('x') as f:
    json.dump({'design':design['summary'], 'validation':results}, f, indent=2)
print(json.dumps(results))
