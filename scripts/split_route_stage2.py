"""Isolate visual route recognition from instruction-conditioned replacement choice."""
import base64,copy,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from core.agent_route_choice import read,write,file_hash,digest,payload,exact_keys,string_list,text,now
from force_route_stage2 import forced_schema,validate_forced,messages,SERVICE
from run_agent_route_choice import call_model
REG=ROOT/'experiments/agent_route_choice/human_v002/run_20261106_09'
OUT=ROOT/'outputs/agent_route_choice/human_v002/run_20261106_09'
BASE=ROOT/'outputs/agent_route_choice/human_v002/run_20261106_08'

def recognition_schema(inv):
 props=dict(observed_branch_id={'enum':[b['id'] for b in inv['branches']]+[None]},observed_direction={'type':['string','null']},evidence_ids={'type':'array','items':{'type':'string'}},visual_description={'type':'string'},confidence={'enum':['high','medium','low']},uncertainties={'type':'array','items':{'type':'string'}})
 return dict(type='object',properties=props,required=list(props),additionalProperties=False)

def check_recognition(a,inv,ids):
 exact_keys(a,recognition_schema(inv)['properties']);branches={b['id']:b for b in inv['branches']};bid=a['observed_branch_id']
 if bid is not None and (bid not in branches or a['observed_direction']!=branches[bid]['direction']):raise ValueError('Recognition must match existing branch and direction')
 if bid is None and a['observed_direction'] is not None:raise ValueError('Unknown route must have null direction')
 string_list(a['evidence_ids'],ids,nonempty=bid is not None);text(a['visual_description']);string_list(a['uncertainties']);assert a['confidence'] in ['high','medium','low']
 return a

def main():
 OUT.mkdir(parents=True,exist_ok=False);c=read(BASE/'dataset.json')['cases'][0];assert c['sample_id']=='sample_08';f=OUT/'cases/sample_08';f.mkdir(parents=True)
 for im in c['images']:
  p=OUT/im['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/im['path'],p)
 for p in (BASE/'cases/sample_08').glob('call1*'):shutil.copy2(p,f/p.name)
 inv=json.loads(read(f/'call1_response.json')['content']);config=read(BASE/'model.json');service=read(SERVICE);assert service['phase']=='ready';write(OUT/'dataset.json',{'cases':[c]});write(OUT/'model.json',config)
 for name in ['01_observed_route_en.txt','02_choose_en.txt']:shutil.copy2(REG/name,OUT/name)
 hashes={}
 for rel in ['scripts/split_route_stage2.py','scripts/force_route_stage2.py','scripts/continue_route_stage2.py','scripts/run_agent_route_choice.py','core/agent_route_choice.py']:
  p=OUT/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p);hashes[rel]=file_hash(p)
 write(OUT/'manifest.json',dict(split_observed_route=True,forced_choice=True,comparison_run=str(BASE.relative_to(ROOT)),git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_hashes=hashes,started_at=now(),new_stage1_calls=0));(OUT/'workspace_status.txt').write_bytes(subprocess.check_output(['git','status','--short']))
 images=[im for im in c['images'] if c['checkpoint_frame']<=im['frame']<=c['wrong_end_frame']]
 meta=dict(current_view_id=f"F{c['checkpoint_frame']:04d}",branch_inventory=inv,image_order=[dict(id=im['id'],frame=im['frame'],phase='reference' if im['frame']==c['checkpoint_frame'] else 'subsequent_observation') for im in images],orientation='All directions refer to the reference image, not the final image.')
 def visual_messages(embed):
  content=[dict(type='text',text=json.dumps(meta))]
  for im in images:
   p=OUT/im['path'];assert file_hash(p)==im['sha256'];url='data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode() if embed else 'PREVIEW_ONLY:image_sha256:'+im['sha256'];content.extend([dict(type='text',text=f"Image {im['id']}"),dict(type='image_url',image_url={'url':url})])
  content.append(dict(type='text',text='Return only JSON matching this schema: '+json.dumps(recognition_schema(inv))))
  return [dict(role='system',content=(REG/'01_observed_route_en.txt').read_text()),dict(role='user',content=content)]
 preview=visual_messages(False);serial=json.dumps(preview);assert c['instruction'] not in serial
 for forbidden in ['wrong_attempt','wrong_branch','previous_attempt_action_commands','approach_action_commands','FORWARD','RIGHT','LEFT']:
  assert forbidden not in serial,forbidden
 wire=payload(visual_messages(True),config,c['sample_id'],20);write(f/'observed_route_request.json',dict(request_sha256=digest(wire),parameters={k:v for k,v in wire.items() if k!='messages'},messages_image_hash_preview=preview,inventory_sha256=digest(inv)));write(OUT/'status.json',{'phase':'recognizing_actual_route'})
 raw=call_model(service['base_url']+'/chat/completions',wire,None,config,f/'observed_route_transport.jsonl');write(f/'observed_route_response.json',raw);assert raw['finish_reason']=='stop';obs=check_recognition(json.loads(raw['content']),inv,[im['id'] for im in images]);write(f/'observed_route_answer.json',obs);print('OBSERVED '+json.dumps(obs),flush=True)
 if obs['observed_branch_id'] is None:
  write(OUT/'status.json',dict(phase='blocked_by_unidentified_route',model_calls=1));raise RuntimeError('No branch identified; no fabricated exclusion or replacement call')
 locked=dict(branch_id=obs['observed_branch_id'],direction=obs['observed_direction'],evidence_ids=obs['evidence_ids'],visual_description=obs['visual_description'],recognition_response_sha256=file_hash(f/'observed_route_response.json'));write(f/'locked_exclusion.json',locked)
 prompt=(REG/'02_choose_en.txt').read_text();m=messages(c,OUT,prompt,inv,True);preview=messages(c,OUT,prompt,inv,False)
 choice_schema=forced_schema();choice_schema['properties']['wrong_branch_id']={'enum':[locked['branch_id']]};choice_schema['properties']['excluded_branch_ids']={'type':'array','items':{'enum':[locked['branch_id']]},'minItems':1,'maxItems':1}
 for ms in [m,preview]:
  metadata=json.loads(ms[1]['content'][0]['text']);metadata['locked_observed_route']=locked;metadata['locked_excluded_branch_ids']=[locked['branch_id']];metadata['event']='An independent visual-only call identified the physically taken route. This experiment marks that abandoned choice as wrong. Its ID is locked and excluded by the program; do not identify or revise it again.';ms[1]['content'][0]['text']=json.dumps(metadata);ms[1]['content'][-1]['text']='Return only JSON matching this schema: '+json.dumps(choice_schema)
 wire=payload(m,config,c['sample_id'],2);write(f/'call2_request.json',dict(request_sha256=digest(wire),parameters={k:v for k,v in wire.items() if k!='messages'},messages_image_hash_preview=preview,inventory_sha256=digest(inv)));write(OUT/'status.json',{'phase':'choosing_replacement','locked_exclusion':locked['branch_id']})
 raw=call_model(service['base_url']+'/chat/completions',wire,None,config,f/'call2_transport.jsonl');write(f/'call2_response.json',raw);assert raw['finish_reason']=='stop';answer=json.loads(raw['content']);validate_forced(answer,inv,[im['id'] for im in c['images']],c['instruction']);assert answer['wrong_branch_id']==locked['branch_id'];assert answer['excluded_branch_ids']==[locked['branch_id']];assert answer['selected_branch_id']!=locked['branch_id'];write(f/'call2_answer.json',answer)
 write(f/'status.json',dict(phase='complete',first_stage_reused=True,first_stage_valid=True,inventory_wrapper_preserved=False,locked_exclusion=locked['branch_id']));summary=dict(samples=1,response_count=3,stage2_responses=1,observed_route_responses=1,new_stage1_calls=0,new_calls=2,valid_samples=1,selected=1,insufficient=0,no_second=0);write(OUT/'summary.json',summary);write(OUT/'status.json',dict(phase='complete',service_retained=True,finished_at=now(),**summary));write(OUT/'isolation_audit.json',dict(passed=True,recognition_no_instruction=True,recognition_no_actions=True,recognition_no_error_label=True,recognition_frames=[im['frame'] for im in images],inventory_unchanged=True,locked_exclusion=locked,selection_obeyed_lock=True));print('CHOICE '+json.dumps(answer),flush=True)
if __name__=='__main__':main()
