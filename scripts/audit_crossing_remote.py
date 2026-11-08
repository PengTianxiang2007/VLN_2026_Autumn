"""Verify provider payload hashes against causal RGB reconstruction; needs no API key."""
import argparse,json,re
from pathlib import Path
import preview_crossing_checkpoint as preview

def main(output,tag):
    run=output/'runs'/tag;manifest=preview.read_json(run/'manifest.json');reg=preview.read_json(output/'registration.json')
    core=preview.frozen_core(run,manifest);canonical=core.canonical_hash
    maps=preview.read_json(output/'evaluation/maps.json');inputs=preview.read_json(output/'inputs.json');private=preview.read_json(output/'evaluation/cases.json')
    replies={}
    for f in (run/'cases').glob('*/attempts.jsonl'):
        for row in preview.load_records(f):
            if row.get('ok'):replies[row['request_sha256']]=row['reply']
    checked=set()
    def audit_hash(payload):
        h=canonical(payload)
        if isinstance(payload,dict) and 'model' in payload and 'messages' in payload:
            reply=replies[h]
            budget=int(re.search(r'actual output budget (\d+)',reply['_transport_adapter']).group(1))
            wire={k:v for k,v in payload.items() if k not in ['seed','chat_template_kwargs','response_format']}
            wire.update(thinking={'type':'enabled'},reasoning_effort=reg['reasoning_effort'],response_format={'type':'json_object'},stream=True,max_tokens=budget)
            if canonical(wire)!=reply['_provider_request_sha256']:raise ValueError('Provider payload hash mismatch: '+h)
            checked.add(h)
        return h
    core.canonical_hash=audit_hash
    for eid in manifest['episodes']:
        records=preview.load_records(run/'cases'/eid/'predictions.jsonl')
        preview.prefix_case(eid,inputs[eid],private[eid],records,core,manifest['inference'],maps[private[eid]['scene']]['crossings'])
    if len(checked)!=reg['expected_model_calls']:raise ValueError('Incomplete provider audit')
    result=dict(passed=True,verified_requests=len(checked),reasoning_effort=reg['reasoning_effort'],credential_required=False)
    (output/'remote_request_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--tag',required=True);a=p.parse_args();main(a.output,a.tag)
