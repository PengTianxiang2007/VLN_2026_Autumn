"""Finish C48's two outstanding deduplication comparisons and index all ten cases."""
from collections import Counter
import fcntl
import getpass
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT/'scripts'))
import run_route53_deepseek_subset as batch
from core.agent_route_choice import file_hash, now, read, write

RUN = batch.RUN
OUT = RUN/'dedup_resume_01'
OLD = RUN/'dedup/cases/C48'


def main():
    manifest = read(RUN/'manifest.json')
    cases = batch.selection()
    assert [batch.case_info(c) for c in cases] == manifest['cases']
    assert all(file_hash(ROOT/p) == h for p,h in manifest['sources'].items())
    assert file_hash(batch.route.UPSTREAM/'candidates.json') == manifest['upstream_candidates_sha256']
    case = next(c for c in cases if c['case_number'] == 48)
    assert case['episode_id'] == 'kujiale_0259_55_0'
    assert read(OLD/'state.json') == {'processed':3,'active_ids':['S02','S03']}
    assert read(OLD/'requests/S04.response.json')['status'] == 'error'
    prepare_status = read(RUN/'status.json')
    assert prepare_status['phase'] == 'failed'
    assert not (RUN/'deviation').exists()
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if not (OUT/'original_status.json').exists():
            shutil.copyfile(RUN/'status.json',OUT/'original_status.json')
        results = {}
        for c in cases:
            n = c['case_number']
            if n != 48:
                p = RUN/'dedup/cases'/f'C{n:02d}'/'result.json'
                assert read(p)['episode_id'] == c['episode_id']
                results[n] = p
        engine_path = RUN/'source'/batch.DEDUP.relative_to(ROOT)/'run_dedup.py'
        spec = importlib.util.spec_from_file_location('fixed_dedup',engine_path)
        engine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(engine)
        engine.SITE = batch.route.DATA
        assert engine.API == batch.API
        prompt = (engine_path.parent/'prompt_zh.txt').read_text()
        settings = manifest['settings']
        original = engine.compare
        key = getpass.getpass('DeepSeek API key (hidden): ')
        if not key:
            raise ValueError('Missing credential')
        for var in list(os.environ):
            if 'proxy' in var.lower():
                os.environ.pop(var)
        attempts = OUT/'attempts'
        attempts.mkdir(exist_ok=True)
        # Keep every failed execution and reuse successful per-node responses on a rerun.
        attempt = attempts/f'run_{1+len(list(attempts.glob("run_*"))):02d}'
        attempt.mkdir()
        engine.RUN = attempt
        def compare(a,b,key,prompt,settings,folder,log):
            node = b['id']
            if node not in ('S02','S03','S04','S05'):
                raise ValueError('Unexpected comparison '+node)
            stores = [OLD/'requests'] if node in ('S02','S03') else sorted((OUT/'calls'/node).glob('try_*'))
            for store in stores:
                resp = store/(node+'.response.json')
                if not resp.exists() or read(resp)['status'] != 'ok':
                    continue
                req = read(store/(node+'.request.json'))
                response = read(resp)
                assert req['settings']==settings and req['prompt_sha256']==manifest_prompt
                assert (req['previous_candidate_id'],req['current_candidate_id'])==(a['candidate_id'],b['candidate_id'])
                assert req['images']==engine.evidence(a,'A')+engine.evidence(b,'B')
                assert engine.validate(json.loads(response['response']['choices'][0]['message']['content']),a,b)==response['answer']
                for suffix in ('.request.json','.response.json'):
                    shutil.copyfile(store/(node+suffix),folder/(node+suffix))
                log('comparison_reused',current_id=node,artifact=str(resp.relative_to(RUN)))
                return response
            if node in ('S02','S03'):
                raise ValueError('Cannot reuse previous valid comparison '+node)
            traces = OUT/'calls'/node
            traces.mkdir(parents=True,exist_ok=True)
            for retry in range(3):
                store = traces/f'try_{len(list(traces.glob("try_*")))+1:02d}'
                store.mkdir()
                response = original(a,b,key,prompt,settings,store,log)
                req_name = node+'.request.json'
                if node=='S04' and (store/req_name).exists():
                    assert read(store/req_name)['request_sha256']==read(OLD/'requests'/req_name)['request_sha256']
                if response['status']=='ok':
                    for suffix in ('.request.json','.response.json'):
                        shutil.copyfile(store/(node+suffix),folder/(node+suffix))
                    return response
                status = response.get('http_status')
                transport = status in (429,500,502,503,504) or (status is None and response['error'].startswith(
                    ('ConnectError:', 'ReadError:', 'ReadTimeout:', 'ConnectTimeout:', 'RemoteProtocolError:')))
                if not transport or retry==2:
                    raise RuntimeError(response['error'])
                time.sleep(3*(retry+1))
        manifest_prompt = read(engine_path.parent/'manifest.json')['prompt_sha256']
        engine.compare = compare
        fields = ('case_number','case_index','episode_id','real_episode_id','scene','nodes')
        result = engine.run_case({k:case[k] for k in fields},key,prompt,settings)
        assert result['decisions'][2]['active_ids_after']==read(OLD/'state.json')['active_ids']
        assert result['summary']['model_calls']==4 and result['summary']['errors']==0
        results[48] = attempt/'cases/C48/result.json'
        totals = Counter()
        verdicts = Counter()
        index = {}
        for c in cases:
            path = results[c['case_number']]
            data = read(path)
            totals.update(data['summary'])
            verdicts.update(d['relation'] for d in data['decisions'] if d['needs_model'])
            index[c['episode_id']] = dict(result=str(path.relative_to(RUN)),retained_ids=data['final_active_ids'])
        assert totals['candidates']==93 and totals['model_calls']==67 and totals['errors']==0
        assert totals['retained']+totals['removed']==93 and not (RUN/'deviation').exists()
        summary = dict(completed_at=now(),dedup_completed=len(results),dedup=dict(totals),verdicts=dict(verdicts),
                       deviation_completed=0,deviation_requests=0,case_results=index,source_sha256=file_hash(__file__))
        write(OUT/'summary.json',summary)
        write(Path(__file__).parent/'completion.json',summary)
        write(RUN/'status.json',dict(phase='dedup_complete_deviation_on_hold',updated_at=now(),dedup_completed=10,
              deviation_completed=0,deviation_requests=0,dedup_counts=dict(totals),summary='dedup_resume_01/summary.json',
              original_status='dedup_resume_01/original_status.json'))
        print(json.dumps({'c48':result['final_active_ids'],'dedup':dict(totals),'verdicts':dict(verdicts)}),flush=True)


if __name__=='__main__':
    main()
