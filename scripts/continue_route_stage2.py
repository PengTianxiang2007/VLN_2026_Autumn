"""Continue frozen seven-frame inventories with the morning stage-two protocol."""
import argparse,base64,copy,json,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from core.agent_route_choice import read,write,file_hash,digest,payload,schema,validate_choice,now
from run_agent_route_choice import call_model
BASE=ROOT/'outputs/agent_route_choice/human_v002/run_20261106_04'
PREP=ROOT/'outputs/agent_route_choice/human_v001/preparation_20261106_01'
SERVICE=ROOT/'outputs/model_services/qwen27b_gpu0_20261106_02/service.json'

def messages(c,out,prompt,inventory,embed):
 meta=dict(current_view_id=f"F{c['checkpoint_frame']:04d}",instruction=c['instruction'],branch_inventory=inventory,
  image_order=[{k:i[k] for k in ('id','frame','phase','roles')} for i in c['images']],approach_action_commands=c['approach_actions'],previous_attempt_action_commands=c['attempt_actions'],
  checkpoint_context_image_ids=c['context_image_ids'],wrong_attempt_image_ids=c['wrong_image_ids'],wrong_attempt_end_frame=c['wrong_end_frame'],
  orientation='All directions refer to current_view_id after virtual return.',event='The previous attempt took a wrong route. Identify it from the evidence; the current view has returned to the checkpoint.',
  observation_protocol='Offline retrospective review. Checkpoint context includes before, at, and after the annotated checkpoint. Later context only helps understand entrances at that SAME checkpoint. Images with wrong_attempt role and the previous_attempt_action_commands describe the abandoned attempt through wrong_attempt_end_frame. Context images beyond that endpoint are supplementary observations, not part of that abandoned segment. Overlapping images are sent once with both roles. Do not move the current position or orientation to any later image.')
 content=[dict(type='text',text=json.dumps(meta,ensure_ascii=False))]
 for im in c['images']:
  p=out/im['path'];assert file_hash(p)==im['sha256'];url='data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode() if embed else 'PREVIEW_ONLY:image_sha256:'+im['sha256']
  content.extend([dict(type='text',text=f"Image {im['id']} ({im['phase']}; roles: {', '.join(im['roles'])})"),dict(type='image_url',image_url={'url':url})])
 content.append(dict(type='text',text='Return only JSON matching this schema: '+json.dumps(schema(2))))
 return [dict(role='system',content=prompt),dict(role='user',content=content)]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 old={c['sample_id']:c for c in read(PREP/'dataset.json')['cases']};cases=[];audits=[]
 for orig in read(BASE/'dataset.json')['cases']:
  c=copy.deepcopy(orig);sid=c['sample_id'];prior=old[sid];c.update(instruction=prior['instruction'],wrong_end_frame=prior['wrong_end_frame'],attempt_actions=prior['attempt_actions'])
  c['context_image_ids']=[i['id'] for i in c['images']];wrong=[i for i in prior['images'] if i['phase']=='wrong_attempt'];c['wrong_image_ids']=[i['id'] for i in wrong]
  merged={}
  for im in c['images']:
   im['roles']=['checkpoint_context'];merged[im['frame']]=im;dest=out/im['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/im['path'],dest)
  for original in wrong:
   im=copy.deepcopy(original)
   if im['frame'] in merged:assert im['sha256']==merged[im['frame']]['sha256'];merged[im['frame']]['roles'].append('wrong_attempt');merged[im['frame']]['phase']='wrong_attempt'
   else:
    im['roles']=['wrong_attempt'];merged[im['frame']]=im;dest=out/im['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PREP/im['path'],dest)
  c['images']=sorted(merged.values(),key=lambda i:i['frame']);assert len(c['images'])<=11;assert [i['frame']-c['checkpoint_frame'] for i in orig['images']]==[-4,-2,0,2,4,6,10]
  folder=out/'cases'/sid;folder.mkdir(parents=True)
  for f in (BASE/'cases'/sid).glob('call1*'):shutil.copy2(f,folder/f.name)
  write(folder/'status.json',{'phase':'pending_stage2','first_stage_reused':True});cases.append(c)
 write(out/'dataset.json',{'cases':cases});config=read(BASE/'model.json');write(out/'model.json',config)
 prompt=(ROOT/'outputs/agent_route_choice/v001/preparation_20261106_04/prompts/02_choose_en.txt').read_text();(out/'02_choose_en.txt').write_text(prompt)
 hashes={}
 for rel in ['scripts/continue_route_stage2.py','core/agent_route_choice.py','scripts/run_agent_route_choice.py','scripts/run_human_route_choice.py','scripts/serve_qwen27b_standby.py']:
  p=out/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p);hashes[rel]=file_hash(p)
 write(out/'manifest.json',dict(started_at=now(),stage1_source=str(BASE.relative_to(ROOT)),stage1_source_manifest_sha256=file_hash(BASE/'manifest.json'),prompt_sha256=file_hash(out/'02_choose_en.txt'),git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_hashes=hashes,service=str(SERVICE),seed=config['seed'],new_stage1_calls=0,max_unique_images=11))
 (out/'workspace_status.txt').write_bytes(subprocess.check_output(['git','status','--short']))
 write(out/'status.json',{'phase':'waiting_service','completed':0,'total':len(cases)})
 deadline=time.monotonic()+1800
 while True:
  s=read(SERVICE) if SERVICE.exists() else {}
  if s.get('phase')=='ready':break
  if s.get('phase') in ('failed','stopped') or time.monotonic()>deadline:raise RuntimeError('Service unavailable: '+str(s.get('phase')))
  time.sleep(3)
 for index,c in enumerate(cases):
  sid=c['sample_id'];folder=out/'cases'/sid;raw1=read(folder/'call1_response.json');inventory=json.loads(raw1['content']);normalized=inventory if 'branches' in inventory else inventory['properties']
  wire=payload(messages(c,out,prompt,inventory,True),config,sid,2);preview=messages(c,out,prompt,inventory,False)
  assert json.loads(preview[1]['content'][0]['text'])['branch_inventory']==inventory
  write(folder/'call2_request.json',{'request_sha256':digest(wire),'inventory_sha256':digest(inventory),'parameters':{k:v for k,v in wire.items() if k!='messages'},'messages_image_hash_preview':preview})
  state=dict(phase='running',first_stage_reused=True,first_stage_valid=(folder/'call1_answer.json').exists(),inventory_wrapper_preserved='branches' not in inventory)
  write(folder/'status.json',state);write(out/'status.json',dict(phase='running',sample_id=sid,completed=index,total=len(cases)))
  try:
   raw=call_model(s['base_url']+'/chat/completions',wire,None,config,folder/'call2_transport.jsonl');write(folder/'call2_response.json',raw);assert raw['finish_reason']=='stop';answer=json.loads(raw['content']);validate_choice(answer,normalized,[i['id'] for i in c['images']],c['instruction']);write(folder/'call2_answer.json',answer);state.update(phase='complete' if state['first_stage_valid'] else 'complete_with_invalid_first_stage')
  except Exception as e:state.update(phase='invalid_or_failed',error=str(e))
  write(folder/'status.json',state);audits.append(dict(sample_id=sid,passed=True,inventory_transferred_unchanged=True,first_response_sha256=file_hash(folder/'call1_response.json'),images=len(c['images']),image_frames=[i['frame'] for i in c['images']],first_stage_valid=state['first_stage_valid'],result=state))
  print(json.dumps(dict(sample_id=sid,**state)),flush=True)
 summary=dict(samples=len(cases),response_count=10,valid_samples=0,selected=0,insufficient=0,no_second=0,new_stage1_calls=0,stage2_responses=0)
 for c in cases:
  f=out/'cases'/c['sample_id'];r=f/'call2_response.json'
  if r.exists():
   summary['response_count']+=1;summary['stage2_responses']+=1
   try:
    ans=json.loads(read(r)['content']);summary['selected']+=ans.get('status')=='selected';summary['insufficient']+=ans.get('status')=='insufficient_evidence'
   except ValueError:pass
  else:summary['no_second']+=1
  summary['valid_samples']+=(f/'call1_answer.json').exists() and (f/'call2_answer.json').exists()
 write(out/'request_audit.json',{'passed':True,'cases':audits});write(out/'summary.json',summary);write(out/'status.json',dict(phase='complete' if summary['valid_samples']==10 else 'complete_with_invalid_samples',completed=10,finished_at=now(),service_retained=True,**summary));print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
