"""Forced stage-two choice, with unknown wrong-branch identity allowed."""
import argparse,copy,difflib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from core.agent_route_choice import read,write,digest,file_hash,payload,schema,DIRECTIONS,exact_keys,string_list,text,now
from continue_route_stage2 import messages,SERVICE
from run_agent_route_choice import call_model

def forced_schema():
 s=schema(2);s['properties']['status']={'enum':['selected']};s['properties']['selected_branch_id']={'type':'string'};s['properties']['selected_direction']={'enum':list(DIRECTIONS)};return s

def validate_forced(a,inventory,image_ids,instruction):
 exact_keys(a,forced_schema()['properties']);branches={b['id']:b for b in inventory['branches']}
 if a['status']!='selected' or not isinstance(a['selected_branch_id'],str) or a['selected_branch_id'] not in branches:raise ValueError('Must select an existing branch')
 if a['selected_direction']!=branches[a['selected_branch_id']]['direction']:raise ValueError('Direction must match inventory')
 wrong=a['wrong_branch_id']
 if wrong is not None and (not isinstance(wrong,str) or wrong not in branches):raise ValueError('Unknown wrong branch ID')
 if a['excluded_branch_ids']!=([wrong] if wrong is not None else []) or a['selected_branch_id'] in a['excluded_branch_ids']:raise ValueError('Invalid exclusion or selected excluded branch')
 string_list(a['wrong_branch_evidence_ids'],image_ids,nonempty=wrong is not None);string_list(a['selection_evidence_ids'],image_ids,nonempty=True);string_list(a['instruction_evidence'],nonempty=True)
 if any(q not in instruction for q in a['instruction_evidence']):raise ValueError('Instruction quote must be exact')
 text(a['error_reason']);text(a['route_description']);string_list(a['uncertainties'])
 if a['confidence'] not in ('high','medium','low'):raise ValueError('Invalid confidence')
 return a

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--prompt',type=Path,required=True);ap.add_argument('--base',type=Path,default=ROOT/'outputs/agent_route_choice/human_v002/run_20261106_06');ap.add_argument('--sample-id');a=ap.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);base=a.base.resolve();cases=read(base/'dataset.json')['cases'];cases=[c for c in cases if not a.sample_id or c['sample_id']==a.sample_id];assert cases;config=read(base/'model.json');prompt=a.prompt.read_text();service=read(SERVICE);assert service['phase']=='ready'
 for c in cases:
  assert len(c['images'])<=11
  for im in c['images']:
   dest=out/im['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(base/im['path'],dest)
  dest=out/'cases'/c['sample_id'];dest.mkdir(parents=True)
  for p in (base/'cases'/c['sample_id']).glob('call1*'):shutil.copy2(p,dest/p.name)
 write(out/'dataset.json',{'cases':cases});write(out/'model.json',config);(out/'02_choose_en.txt').write_text(prompt);(out/'prompt.diff').write_text(''.join(difflib.unified_diff((base/'02_choose_en.txt').read_text().splitlines(True),prompt.splitlines(True),fromfile='previous',tofile='forced')))
 hashes={}
 for rel in ['scripts/force_route_stage2.py','scripts/continue_route_stage2.py','scripts/run_agent_route_choice.py','core/agent_route_choice.py']:
  dest=out/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dest);hashes[rel]=file_hash(dest)
 write(out/'manifest.json',dict(forced_choice=True,comparison_run=str(base.relative_to(ROOT)),stage1_source='outputs/agent_route_choice/human_v002/run_20261106_04',started_at=now(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_hashes=hashes,prompt_sha256=file_hash(out/'02_choose_en.txt'),new_stage1_calls=0));(out/'workspace_status.txt').write_bytes(subprocess.check_output(['git','status','--short']))
 audits=[]
 for n,c in enumerate(cases):
  sid=c['sample_id'];f=out/'cases'/sid;inv=json.loads(read(f/'call1_response.json')['content']);norm=inv if 'branches' in inv else inv['properties'];assert norm['branches']
  m=messages(c,out,prompt,inv,True);m[1]['content'][-1]['text']='Return only JSON matching this schema: '+json.dumps(forced_schema());wire=payload(m,config,sid,2)
  preview=messages(c,out,prompt,inv,False);preview[1]['content'][-1]=m[1]['content'][-1];old=read(base/'cases'/sid/'call2_request.json');assert preview[1]['content'][:-1]==old['messages_image_hash_preview'][1]['content'][:-1];assert {k:v for k,v in wire.items() if k!='messages'}==old['parameters']
  write(f/'call2_request.json',dict(request_sha256=digest(wire),inventory_sha256=digest(inv),parameters={k:v for k,v in wire.items() if k!='messages'},messages_image_hash_preview=preview));state=dict(phase='running',first_stage_reused=True,first_stage_valid=(f/'call1_answer.json').exists(),inventory_wrapper_preserved='branches' not in inv);write(out/'status.json',dict(phase='running',completed=n,total=len(cases),sample_id=sid))
  try:
   raw=call_model(service['base_url']+'/chat/completions',wire,None,config,f/'call2_transport.jsonl');write(f/'call2_response.json',raw);assert raw['finish_reason']=='stop';answer=json.loads(raw['content']);validate_forced(answer,norm,[i['id'] for i in c['images']],c['instruction']);write(f/'call2_answer.json',answer);state.update(phase='complete' if state['first_stage_valid'] else 'complete_with_invalid_first_stage')
  except Exception as e:state.update(phase='invalid_or_failed',error=str(e))
  write(f/'status.json',state);audits.append(dict(sample_id=sid,passed=True,images_metadata_inventory_parameters_unchanged=True,only_prompt_and_choice_schema_changed=True));print(json.dumps(dict(sample_id=sid,**state)),flush=True)
 summary=dict(samples=len(cases),response_count=len(cases),valid_samples=0,stage2_valid=0,selected=0,insufficient=0,no_second=0,new_stage1_calls=0,stage2_responses=0)
 for c in cases:
  f=out/'cases'/c['sample_id']
  if (f/'call2_response.json').exists():
   summary['stage2_responses']+=1;summary['response_count']+=1
   try:
    ans=json.loads(read(f/'call2_response.json')['content']);summary['selected']+=ans.get('status')=='selected';summary['insufficient']+=ans.get('status')=='insufficient_evidence'
   except ValueError:pass
  else:summary['no_second']+=1
  summary['stage2_valid']+=(f/'call2_answer.json').exists();summary['valid_samples']+=(f/'call1_answer.json').exists() and (f/'call2_answer.json').exists()
 write(out/'request_audit.json',dict(passed=True,cases=audits));write(out/'summary.json',summary);write(out/'status.json',dict(phase='complete_with_invalid_first_stage' if summary['stage2_valid']==len(cases) else 'complete_with_invalid_samples',completed=len(cases),finished_at=now(),service_retained=True,**summary));print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
