"""Recheck retained v002 answers after allowing empty route text for abstentions."""
import argparse
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.agent_route_choice import read,write,file_hash,digest,now
from core.agent_panorama_choice import validate_inventory,validate_choice


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run=a.run.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    prepared=Path(read(run/'registration.json')['prepared']);cases=read(prepared/'dataset.json')['cases'];rows=[]
    for case in cases:
        d=run/'cases'/case['sample_id'];inv=read(d/'call1_parsed.json');choice=read(d/'call2_parsed.json');request=read(d/'call2_request.json')
        meta=json.loads(request['messages_image_hash_preview'][1]['content'][0]['text'])
        assert request['inventory_sha256']==digest(inv) and meta['branch_inventory']==inv
        row=dict(sample_id=case['sample_id'],inventory_valid=True,decision_valid_after_empty_route_fix=True,
                 original_status=read(d/'status.json'),model_status=choice['status'],branch_count=len(inv['branches']),
                 wrong_branch_id=choice['wrong_branch_id'],incoming_branch_id=choice['incoming_branch_id'],selected_branch_id=choice['selected_branch_id'],
                 full_inventory_transferred=True,source_hashes={f'call{s}_response.json':file_hash(d/f'call{s}_response.json') for s in (1,2)})
        validate_inventory(inv,case)
        try:validate_choice(choice,inv,case)
        except ValueError as exc:row.update(decision_valid_after_empty_route_fix=False,error=str(exc))
        rows.append(row)
    result=dict(created_at=now(),source_run=str(run),source_registration_sha256=file_hash(run/'registration.json'),model_calls=0,
                change='Only allow empty route_description when status is insufficient_evidence; all raw answers, prompts, selections, and original statuses are unchanged.',
                samples=len(rows),received_responses=20,inventory_valid=sum(r['inventory_valid'] for r in rows),
                original_protocol_valid=0,review_protocol_valid=sum(r['decision_valid_after_empty_route_fix'] for r in rows),
                model_selected=sum(r['selected_branch_id'] is not None for r in rows),model_insufficient=sum(r['model_status']=='insufficient_evidence' for r in rows),
                branch_total=sum(r['branch_count'] for r in rows),semantic_accuracy='not_established',cases=rows)
    write(out/'review_audit.json',result)
    for rel in ['core/agent_panorama_choice.py','tests/test_agent_panorama_choice.py','scripts/audit_agent_panorama_results.py']:
        dest=out/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dest)
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False))


if __name__=='__main__':main()
