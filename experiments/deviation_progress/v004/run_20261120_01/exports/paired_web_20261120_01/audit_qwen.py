"""Check both versions of the validator against every archived Qwen completion."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT))
import run_deviation_progress_v004 as fixed
from core.agent_route_choice import file_hash, read


def main(output):
    run = ROOT / 'outputs/deviation_progress/v004/run_20261120_01/qwen_gpu2_01'
    scripts = run / 'source/scripts'
    old_path = scripts / 'run_deviation_progress_v004.py'
    # Both validators import the same unchanged nine-field base validator.
    assert file_hash(scripts / 'run_deviation_progress_review.py') == file_hash(Path(fixed.review.__file__))
    spec = importlib.util.spec_from_file_location('qwen_at_inference', old_path)
    frozen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frozen)
    rows = []
    for case in read(run / 'v004_results.json'):
        label = f"C{case['case_number']:02d}"
        folder = run / 'run/cases' / label
        recorded = {r['node_id']: r for r in read(folder / 'result.json')['reviews']}
        files = sorted(folder.glob('S*.response.json'))
        assert {p.name.split('.')[0] for p in files} == set(recorded)
        for path in files:
            node = path.name.split('.')[0]
            request = read(folder / (node+'.request.json'))
            response = read(path)
            choice = response['response']['choices'][0]
            raw = choice['message']['content']
            answer = json.loads(raw)
            assert choice['finish_reason'] == 'stop' and response['http_status'] == 200
            assert response['status'] == recorded[node]['status'] == 'ok'
            assert frozen.validate_v004(answer, request) == fixed.validate_v004(answer, request)
            assert answer == response['parsed_original'] == response['answer'] == recorded[node]['answer']
            rows.append(dict(case=label, node=node, from_frame=request['previous_frame'],
                             to_frame=request['current_frame'], verdict=answer['verdict'],
                             top_level_type_present='type' in answer,
                             raw_sha256=hashlib.sha256(raw.encode()).hexdigest()))
    counts = dict(Counter(r['verdict'] for r in rows))
    assert counts == read(run / 'status.json')['verdicts']
    result = dict(cases=len({r['case'] for r in rows}), raw_responses=len(rows),
                  previous_validator_accepted=len(rows), fixed_validator_accepted=len(rows),
                  previously_rejected_alarms=0, with_top_level_type=sum(r['top_level_type_present'] for r in rows),
                  verdicts=counts, original_validator_sha256=file_hash(old_path),
                  fixed_validator_sha256=file_hash(Path(fixed.__file__)), rounds=rows)
    with output.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print({k:v for k,v in result.items() if k != 'rounds'})


if __name__ == '__main__':
    main(Path(sys.argv[1]))
