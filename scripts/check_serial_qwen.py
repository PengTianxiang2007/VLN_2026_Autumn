"""Real-image service/protocol checks only; these are never simulation results."""
import argparse
import getpass
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from core.serial_pipeline import SerialAPI, save, sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--service',type=Path,required=True); p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True); p.add_argument('--keys-stdin',action='store_true')
    a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=False)
    service=json.loads(a.service.read_text())
    if service['phase']!='ready': raise RuntimeError('Service is not ready')
    if a.keys_stdin: os.environ['JEV_API_KEY']=getpass.getpass('JEV key: ')
    config=dict(semantic_provider='qwen_local',semantic_model=service['model'],semantic_endpoint=service['base_url'],
                semantic_seed=2,jev_endpoint='https://api.easyjev.online/v1/systemone',jev_model='jev-1.14.0')
    frames=[json.loads(line) for line in (a.source/'observations.jsonl').read_text().splitlines()]
    if any(f['local'] or f['leg']!=0 for f in frames): raise ValueError('Use an uninterrupted source prefix')
    events=[json.loads(line) for line in (a.source/'events.jsonl').read_text().splitlines()]
    instruction=next(e['instruction'] for e in events if e['kind']=='episode_started')
    for e in events:
        if e['kind']=='action':
            action=e['action']; code=0 if 'stop' in action else action.get('move_by_discrete',[None])[0]
            frames[e['action_count']]['action_after']={0:'STOP',1:'FORWARD',2:'LEFT',3:'RIGHT',None:'WAIT'}[code]
    api=SerialAPI(a.output,config)
    result=dict(kind='real_image_protocol_preflight_only_not_navigation_or_accuracy',config=config,
                source=str(a.source.resolve()),source_sha256=sha(a.source/'observations.jsonl'),checks={})
    try:
        result['checks']['jev_probability']=api.jev(frames[:3])
        result['checks']['dedup']=api.dedup(dict(id='S01',index=10),dict(id='S02',index=15),frames)
        request=next((a.output/'requests').glob('*_dedup'))
        metadata=json.loads((request/'request.json').read_text())['metadata']
        api.dedup_module.validate(json.loads((request/'answer.json').read_text()),metadata['A'],metadata['B'])
        result['checks']['deviation']=api.deviation(dict(id='S01',index=0),dict(id='S02',index=15),frames,
                                                    instruction,{'zh':'尚未提交语义进度。'})
        selection=api.choose(dict(id='S03',index=15),frames,instruction)
        result['checks']['route_choice']=selection
        if selection['status']=='selected':
            result['checks']['correction']=api.correction(selection,frames[15])
        else:
            result['not_exercised']=['choice']
            branches=selection['inventory']['branches']
            if branches:
                result['checks']['correction_fixture']=api.correction({'branch':branches[0]},frames[15])
                result['fixture_note']='First visible branch is used only to test instruction-generation format; no pose/action is changed.'
            else:
                result['not_exercised'].append('correction')
        result['passed']=True
    except Exception as error:
        result['passed']=False; result['error']=type(error).__name__+': '+str(error)
        raise
    finally:
        api.close(); save(a.output/'result.json',result)
        print(json.dumps({k:result[k] for k in ('kind','passed','error') if k in result}),flush=True)


if __name__=='__main__': main()
