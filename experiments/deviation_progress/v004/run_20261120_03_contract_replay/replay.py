"""Replay the original six trajectories with the current validator, without an API."""
from collections import Counter
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'scripts'))
import run_deviation_progress_v004 as v4


def main(out):
    old = ROOT/'outputs/deviation_progress/v004/run_20261120_02_deepseek6'
    manifest = v4.read(old/'manifest.json')
    out.mkdir(parents=True, exist_ok=False)
    prompt_dir = Path('source/experiments/deviation_progress/v004')
    (out/prompt_dir).mkdir(parents=True)
    for name in ('prompt_zh.txt', 'prompt_en.txt'):
        shutil.copyfile(old/prompt_dir/name, out/prompt_dir/name)
    prompt = (out/prompt_dir/'prompt_zh.txt').read_text()
    settings = manifest['settings']
    v4.write(out/'manifest.json', dict(manifest, mode='cached_response_revalidation',
             original_run=old.name, original_rounds=v4.read(old/'status.json')['calls_in_completed_cases'],
             validator_sha256=v4.file_hash(v4.__file__), replay_sha256=v4.file_hash(__file__)))
    shutil.copyfile(old/'retained_nodes_and_terminals.json',out/'retained_nodes_and_terminals.json')
    totals, cases = Counter(), []
    def cached(request, site, key, prompt, settings, stem):
        source = old/stem.relative_to(out)
        req = v4.read(source.with_suffix('.request.json'))
        for k,v in request.items():
            if k=='images':
                assert [{name:im[name] for name in ('frame','role','path','image_id')} for im in req[k]] == v
            else:
                assert req[k] == v, f'Archived request differs at {source.name}: {k}'
        assert req['settings']==settings and req['prompt_sha256']==v4.review.sha(prompt.encode())
        result = v4.read(source.with_suffix('.response.json'))
        assert result['http_status']==200
        choice = result['response']['choices'][0]
        assert choice['finish_reason']=='stop'
        answer = json.loads(choice['message']['content'])
        assert answer == result['parsed_original']
        try:
            result['answer'] = v4.validate_v004(answer, req)
        except ValueError as error:
            result.pop('answer',None)
            result.update(status='error',error='ValueError: '+str(error))
        else:
            result.pop('error',None)
            result['status']='ok'
        shutil.copyfile(source.with_suffix('.request.json'),stem.with_suffix('.request.json'))
        v4.write(stem.with_suffix('.response.json'),result)
        return req,result
    for case in v4.load_cases(manifest['cases']):
        v4.review.run_case(case, str(out), None, prompt, settings, model_call=cached)
        folder = out/f"run/cases/C{case['case_number']:02d}"
        data = v4.audit_case(case,folder,v4.validate_v004,prompt,settings)
        totals.update(data['outcomes'])
        cases.append(data)
    v4.write(out/'v004_results.json',cases)
    v4.write(out/'status.json',dict(phase='complete',completed_case_verdicts=dict(totals),
                                   new_model_calls=0, replayed_rounds=sum(totals.values())))


if __name__=='__main__':
    main(Path(sys.argv[1]).resolve())
