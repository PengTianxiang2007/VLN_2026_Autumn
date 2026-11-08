"""Apply the frozen isolated route-recognition protocol to the original ten cases."""
import base64,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from core.agent_route_choice import read,write,file_hash,digest,payload,now
from force_route_stage2 import forced_schema,validate_forced,messages,SERVICE
from split_route_stage2 import recognition_schema,check_recognition
from run_agent_route_choice import call_model
REG=ROOT/'experiments/agent_route_choice/human_v002/run_20261106_10'
OUT=ROOT/'outputs/agent_route_choice/human_v002/run_20261106_10'
BASE=ROOT/'outputs/agent_route_choice/human_v002/run_20261106_07'

def run_case(c,config,service):
 f=OUT/'cases'/c['sample_id'];inv=json.loads(read(f/'call1_response.json')['content']);norm=inv if 'branches' in inv else inv['properties']
 images=[im for im in c['images'] if c['checkpoint_frame']<=im['frame']<=c['wrong_end_frame']]
 meta=dict(current_view_id=f"F{c['checkpoint_frame']:04d}",branch_inventory=inv,image_order=[dict(id=im['id'],frame=im['frame'],phase='reference' if im['frame']==c['checkpoint_frame'] else 'subsequent_observation') for im in images],orientation='All directions refer to the reference image, not the final image.')
 def visual_messages(embed):
  content=[dict(type='text',text=json.dumps(meta))]
  for im in images:
   p=OUT/im['path'];assert file_hash(p)==im['sha256'];url='data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode() if embed else 'PREVIEW_ONLY:image_sha256:'+im['sha256'];content.extend([dict(type='text',text=f"Image {im['id']}"),dict(type='image_url',image_url={'url':url})])
  content.append(dict(type='text',text='Return only JSON matching this schema: '+json.dumps(recognition_schema(norm))))
  return [dict(role='system',content=(REG/'01_observed_route_en.txt').read_text()),dict(role='user',content=content)]
 preview=visual_messages(False);serial=json.dumps(preview);assert c['instruction'] not in serial
 for forbidden in ['wrong_attempt','wrong_branch','previous_attempt_action_commands','approach_action_commands','FORWARD','RIGHT','LEFT']:
  assert forbidden not in serial,forbidden
 wire=payload(visual_messages(True),config,c['sample_id'],20);write(f/'observed_route_request.json',dict(request_sha256=digest(wire),parameters={k:v for k,v in wire.items() if k!='messages'},messages_image_hash_preview=preview,inventory_sha256=digest(inv)));write(OUT/'status.json',{'phase':'recognizing_actual_route'})
 raw=call_model(service['base_url']+'/chat/completions',wire,None,config,f/'observed_route_transport.jsonl');write(f/'observed_route_response.json',raw);assert raw['finish_reason']=='stop';obs=check_recognition(json.loads(raw['content']),norm,[im['id'] for im in images]);write(f/'observed_route_answer.json',obs);print('OBSERVED '+json.dumps(obs),flush=True)
 if obs['observed_branch_id'] is None:
  write(OUT/'status.json',dict(phase='blocked_by_unidentified_route',model_calls=1));raise RuntimeError('No branch identified; no fabricated exclusion or replacement call')
 locked=dict(branch_id=obs['observed_branch_id'],direction=obs['observed_direction'],evidence_ids=obs['evidence_ids'],visual_description=obs['visual_description'],recognition_response_sha256=file_hash(f/'observed_route_response.json'));write(f/'locked_exclusion.json',locked)
 if not any(b['id']!=locked['branch_id'] for b in norm['branches']):raise RuntimeError('No remaining candidate after locked exclusion; replacement call skipped')
 prompt=(REG/'02_choose_en.txt').read_text();m=messages(c,OUT,prompt,inv,True);preview=messages(c,OUT,prompt,inv,False)
 choice_schema=forced_schema();choice_schema['properties']['wrong_branch_id']={'enum':[locked['branch_id']]};choice_schema['properties']['excluded_branch_ids']={'type':'array','items':{'enum':[locked['branch_id']]},'minItems':1,'maxItems':1}
 for ms in [m,preview]:
  metadata=json.loads(ms[1]['content'][0]['text']);metadata['locked_observed_route']=locked;metadata['locked_excluded_branch_ids']=[locked['branch_id']];metadata['event']='An independent visual-only call identified the physically taken route. This experiment marks that abandoned choice as wrong. Its ID is locked and excluded by the program; do not identify or revise it again.';ms[1]['content'][0]['text']=json.dumps(metadata);ms[1]['content'][-1]['text']='Return only JSON matching this schema: '+json.dumps(choice_schema)
 wire=payload(m,config,c['sample_id'],2);write(f/'call2_request.json',dict(request_sha256=digest(wire),parameters={k:v for k,v in wire.items() if k!='messages'},messages_image_hash_preview=preview,inventory_sha256=digest(inv)));write(OUT/'status.json',{'phase':'choosing_replacement','locked_exclusion':locked['branch_id']})
 raw=call_model(service['base_url']+'/chat/completions',wire,None,config,f/'call2_transport.jsonl');write(f/'call2_response.json',raw);assert raw['finish_reason']=='stop';answer=json.loads(raw['content']);validate_forced(answer,norm,[im['id'] for im in c['images']],c['instruction']);assert answer['wrong_branch_id']==locked['branch_id'];assert answer['excluded_branch_ids']==[locked['branch_id']];assert answer['selected_branch_id']!=locked['branch_id'];write(f/'call2_answer.json',answer)


def main():
 OUT.mkdir(parents=True,exist_ok=False);cases=read(BASE/'dataset.json')['cases'];assert len(cases)==10;config=read(BASE/'model.json');service=read(SERVICE);assert service['phase']=='ready'
 write(OUT/'dataset.json',{'cases':cases});write(OUT/'model.json',config)
 for name in ['01_observed_route_en.txt','02_choose_en.txt']:shutil.copy2(REG/name,OUT/name)
 hashes={}
 for rel in ['scripts/batch_split_route_stage2.py','scripts/split_route_stage2.py','scripts/force_route_stage2.py','scripts/continue_route_stage2.py','scripts/run_agent_route_choice.py','core/agent_route_choice.py']:
  p=OUT/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p);hashes[rel]=file_hash(p)
 write(OUT/'manifest.json',dict(split_observed_route=True,forced_choice=True,comparison_run=str(BASE.relative_to(ROOT)),protocol_source='experiments/agent_route_choice/human_v002/run_20261106_09',git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_hashes=hashes,started_at=now(),new_stage1_calls=0));(OUT/'workspace_status.txt').write_bytes(subprocess.check_output(['git','status','--short']))
 for c in cases:
  f=OUT/'cases'/c['sample_id'];f.mkdir(parents=True)
  for im in c['images']:
   p=OUT/im['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/im['path'],p);assert file_hash(p)==im['sha256']
  for p in (BASE/'cases'/c['sample_id']).glob('call1*'):shutil.copy2(p,f/p.name)
  write(f/'status.json',dict(phase='pending',first_stage_reused=True,first_stage_valid=(f/'call1_answer.json').exists(),inventory_wrapper_preserved=not(f/'call1_answer.json').exists()))
 for n,c in enumerate(cases):
  f=OUT/'cases'/c['sample_id'];state=read(f/'status.json');write(OUT/'batch_progress.json',dict(completed=n,total=10,sample_id=c['sample_id']))
  try:
   run_case(c,config,service);state.update(phase='complete' if state['first_stage_valid'] else 'complete_with_invalid_first_stage',locked_exclusion=read(f/'locked_exclusion.json')['branch_id'])
  except Exception as e:state.update(phase='unidentified_or_failed',error=str(e))
  write(f/'status.json',state);print(json.dumps(dict(sample_id=c['sample_id'],**state)),flush=True)
 summary=dict(samples=10,response_count=10,stage2_responses=0,observed_route_responses=0,new_stage1_calls=0,new_calls=0,valid_samples=0,selected=0,insufficient=0,no_second=0,stage2_valid=0)
 for c in cases:
  f=OUT/'cases'/c['sample_id'];summary['observed_route_responses']+=(f/'observed_route_response.json').exists();summary['stage2_valid']+=(f/'call2_answer.json').exists();summary['valid_samples']+=(f/'call1_answer.json').exists() and (f/'call2_answer.json').exists()
  if (f/'call2_response.json').exists():
   summary['stage2_responses']+=1
   try:
    a=json.loads(read(f/'call2_response.json')['content']);summary['selected']+=a.get('status')=='selected';summary['insufficient']+=a.get('status')=='insufficient_evidence'
   except ValueError:pass
  else:summary['no_second']+=1
 summary['new_calls']=summary['stage2_responses']+summary['observed_route_responses'];summary['response_count']+=summary['new_calls'];write(OUT/'summary.json',summary);write(OUT/'status.json',dict(phase='complete' if summary['stage2_valid']==10 else 'complete_with_incomplete_cases',completed=10,service_retained=True,finished_at=now(),**summary));write(OUT/'batch_progress.json',dict(completed=10,total=10));print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
