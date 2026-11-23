"""Print the Route53 plan, or run both prompts sequentially with --run-dir."""
import argparse
import json
from pathlib import Path
import shutil

import run_deviation_progress_v004 as review


SERVICE = review.ROOT / 'outputs/model_services/qwen27b_gpu3_20261120_02/service.json'
VERSIONS = ('v006', 'v006.1')
PILOTS = {v: review.ROOT / 'outputs/deviation_progress' / v / 'run_20261120_01_qwen_gpu3_c35_c38'
          for v in VERSIONS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, help='start the reviews in a new directory')
    parser.add_argument('--resume-from', type=Path, help='continue an interrupted pair in a new run directory')
    args = parser.parse_args()

    # Each version reuses only its own completed reviews of the two pilot cases.
    reused_ids = [35, 38]
    reused = {}
    hashes = {v: review.file_hash(review.VERSION.parent / v / 'prompt_zh.txt') for v in VERSIONS}
    settings = review.read(review.V003 / 'request_settings.json')['settings']
    for version, pilot in PILOTS.items():
        manifest = review.read(pilot / 'manifest.json')
        completed = review.read(pilot / 'status.json')
        rows = review.read(pilot / f'{version}_results.json')
        if (completed['phase'] != 'complete' or sorted(row['case_number'] for row in rows) != reused_ids or
                manifest['version'] != version or manifest['prompt_sha256'] != hashes[version] or
                manifest['settings'] != settings or manifest['gpu'] != 3):
            raise ValueError(f'The {version} pilot does not match this comparison')
        reused[version] = [dict(row, source_run=str(pilot)) for row in rows]

    if args.resume_from:
        args.resume_from = args.resume_from.resolve()
        old_plan = review.read(args.resume_from / 'plan.json')
        if old_plan['prompt_sha256'] != hashes:
            raise ValueError('The interrupted pair used different prompts')
        for version in VERSIONS:
            by_number = {row['case_number']: row for row in reused[version]}
            for row in old_plan.get('reused_results', {}).get(version, []):
                by_number[row['case_number']] = row
            source = args.resume_from / version
            previous_results = source / f'{version}_results.json'
            if previous_results.exists():
                manifest = review.read(source / 'manifest.json')
                if (manifest['version'] != version or manifest['settings'] != settings or
                        manifest['gpu'] != 3 or manifest['prompt_sha256'] != hashes[version]):
                    raise ValueError(f'The interrupted {version} run does not match')
                for row in review.read(previous_results):
                    by_number[row['case_number']] = dict(row, source_run=str(source))
            reused[version] = sorted(by_number.values(), key=lambda row: row['case_number'])

    planned = {v: [n for n in range(1, 54) if n not in {r['case_number'] for r in reused[v]}]
               for v in VERSIONS}
    plan = dict(gpu=3, service=str(SERVICE), reuse_v006=str(PILOTS['v006']),
                reuse_v006_1=str(PILOTS['v006.1']), reused_cases=reused_ids, new_cases=planned,
                prompt_sha256=hashes, reused_results=reused, transport_retries=3,
                resume_from=str(args.resume_from) if args.resume_from else None)
    if args.run_dir is None:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    if review.read(SERVICE)['gpu'] != 3:
        raise ValueError('Expected the retained GPU 3 Qwen service')
    out = args.run_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    review.write(out / 'plan.json', plan)
    shutil.copyfile(__file__, out / 'run_pair.py')
    for version, numbers in planned.items():
        destination = out / version
        if review.file_hash(review.VERSION.parent / version / 'prompt_zh.txt') != hashes[version]:
            raise ValueError(f'{version} prompt changed after the comparison started')
        rows = list(reused[version])
        if numbers:
            command = ['--version', version, '--cases', *map(str, numbers), '--qwen-service',
                       str(SERVICE), '--output', str(destination), '--transport-retries', '3']
            if args.resume_from and (args.resume_from / version / 'manifest.json').exists():
                command.extend(['--resume-from', str(args.resume_from / version)])
            review.main(command)
            rows.extend(dict(row, source_run=str(destination))
                        for row in review.read(destination / f'{version}_results.json'))
        review.write(out / f'{version}_all53.json', sorted(rows, key=lambda row: row['case_number']))


if __name__ == '__main__':
    main()
