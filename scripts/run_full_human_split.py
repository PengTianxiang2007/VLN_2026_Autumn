"""Complete all 34 human error points, reusing the frozen ten-case split run."""
import copy,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from PIL import Image,ImageChops
from core.agent_route_choice import read,write,file_hash,digest,payload,validate_inventory,now
from probe_route_inventory_anchor import messages as inventory_messages
from prepare_agent_route_choice import action_name
from run_agent_route_choice import call_model
import batch_split_route_stage2 as split
REG=ROOT/'experiments/agent_route_choice/human_v002/run_20261107_01'
OUT=ROOT/'outputs/agent_route_choice/human_v002/run_20261107_01'
REUSE=ROOT/'outputs/agent_route_choice/human_v002/run_20261106_10'
PREP=ROOT/'outputs/agent_route_choice/human_v001/preparation_20261106_01'
SOURCE=ROOT/'outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001'
OFFSETS=[-4,-2,0,2,4,6,10]

def first_case(c):
 v=copy.deepcopy(c);v['images']=[im for im in v['images'] if 'checkpoint_context' in im['roles']]
 for im in v['images']:im['phase']='before_checkpoint' if im['frame']<v['checkpoint_frame'] else 'current_checkpoint' if im['frame']==v['checkpoint_frame'] else 'after_checkpoint'
 return v

def main():
 OUT.mkdir(parents=True,exist_ok=False);config=read(REUSE/'model.json');service=read(split.SERVICE);assert service['phase']=='ready';write(OUT/'model.json',config);split.OUT=OUT;split.REG=REG
 for n in ['01_inventory_en.txt','01_observed_route_en.txt','02_choose_en.txt']:shutil.copy2(REG/n,OUT/n)
 frozen={c['sample_id']:c for c in read(REUSE/'dataset.json')['cases']};labels={x['sample_id']:x for x in read(PREP/'evaluation_only.json')['labels']};cases=[];input_audit=[]
 for prior in read(PREP/'dataset.json')['cases']:
  sid=prior['sample_id'];f=OUT/'cases'/sid
  if sid in frozen:
   c=copy.deepcopy(frozen[sid]);shutil.copytree(REUSE/'cases'/sid,f)
   for im in c['images']:
    p=OUT/im['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REUSE/im['path'],p);assert file_hash(p)==im['sha256']
   write(f/'reuse_provenance.json',dict(source=str(REUSE/'cases'/sid),model_calls_added=0));input_audit.append(dict(sample_id=sid,reused=True,first_response_unchanged=True));cases.append(c);continue
  event=labels[sid]['event'];eid=event['episode_id'];C=prior['checkpoint_frame'];obs=read(SOURCE/f'inputs/observations/{eid}.json');wanted=[C+d for d in OFFSETS];selected=[i for i in wanted if 0<=i<len(obs) and obs[i]['eligible_for_inference'] and not obs[i]['terminal'] and not obs[i]['rgb_reused']];assert C in selected
  c=dict(sample_id=sid,episode_id=eid,annotation_frame=C,checkpoint_frame=C,images=[],approach_actions=[],following_actions=[],target_anchor_fixed=True,instruction=prior['instruction'],wrong_end_frame=prior['wrong_end_frame'],attempt_actions=prior['attempt_actions'])
  merged={}
  for frame in selected:
   row=obs[frame];src=SOURCE/row['rgb'];assert file_hash(src)==row['rgb_sha256'];rel=f'images/{sid}/F{frame:04d}.png';p=OUT/rel;p.parent.mkdir(parents=True,exist_ok=True)
   with Image.open(src) as image:
    rgb=image.convert('RGB');assert rgb.size==(640,480);rgb.save(p)
    with Image.open(p) as saved:assert ImageChops.difference(rgb,saved.convert('RGB')).getbbox() is None
   merged[frame]=dict(id=f'F{frame:04d}',frame=frame,phase='before_checkpoint' if frame<C else 'current_checkpoint' if frame==C else 'after_checkpoint',path=rel,sha256=file_hash(p),roles=['checkpoint_context'])
  c['context_image_ids']=[im['id'] for im in merged.values()];wrong=[im for im in prior['images'] if im['phase']=='wrong_attempt'];c['wrong_image_ids']=[im['id'] for im in wrong]
  for old in wrong:
   im=copy.deepcopy(old)
   if im['frame'] in merged:
    assert im['sha256']==merged[im['frame']]['sha256'];merged[im['frame']]['roles'].append('wrong_attempt');merged[im['frame']]['phase']='wrong_attempt'
   else:
    im['roles']=['wrong_attempt'];merged[im['frame']]=im;p=OUT/im['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PREP/im['path'],p)
  c['images']=sorted(merged.values(),key=lambda i:i['frame']);assert len(c['images'])<=11
  executed={}
  for row in obs:
   if row['frame']>C+10:break
   for act in row['newly_executed_actions']:
    assert act['frame']<row['frame'] and act['frame'] not in executed;executed[act['frame']]=action_name(act)
  c['approach_actions']=[dict(frame=i,action=a) for i,a in sorted(executed.items()) if max(0,C-32)<=i<C];c['following_actions']=[dict(frame=i,action=a) for i,a in sorted(executed.items()) if C<=i<C+10]
  f.mkdir(parents=True);write(f/'status.json',dict(phase='pending',first_stage_reused=False,first_stage_valid=False,inventory_wrapper_preserved=False));input_audit.append(dict(sample_id=sid,reused=False,requested_context_frames=wanted,actual_context_frames=selected,omitted_unavailable_frames=[i for i in wanted if i not in selected],wrong_frames=[i['frame'] for i in wrong]));cases.append(c)
 assert len(cases)==34;write(OUT/'dataset.json',{'cases':cases});write(OUT/'input_audit.json',dict(passed=True,cases=input_audit,boundary_rule='Omit unavailable target offsets; never move C, duplicate or fabricate frames'))
 hashes={}
 for rel in ['scripts/run_full_human_split.py','scripts/batch_split_route_stage2.py','scripts/split_route_stage2.py','scripts/force_route_stage2.py','scripts/continue_route_stage2.py','scripts/probe_route_inventory_anchor.py','scripts/run_agent_route_choice.py','core/agent_route_choice.py']:
  p=OUT/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p);hashes[rel]=file_hash(p)
 write(OUT/'manifest.json',dict(split_observed_route=True,forced_choice=True,full_human_dataset=True,comparison_run=str(REUSE.relative_to(ROOT)),reused_samples=list(frozen),new_samples=[c['sample_id'] for c in cases if c['sample_id'] not in frozen],git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_hashes=hashes,prompt_hashes={n:file_hash(OUT/n) for n in ['01_inventory_en.txt','01_observed_route_en.txt','02_choose_en.txt']},started_at=now(),max_new_calls=72));(OUT/'workspace_status.txt').write_bytes(subprocess.check_output(['git','status','--short']))
 prompt=(OUT/'01_inventory_en.txt').read_text();completed=10
 for c in cases:
  sid=c['sample_id']
  if sid in frozen:continue
  f=OUT/'cases'/sid;state=read(f/'status.json');write(OUT/'batch_progress.json',dict(completed=completed,total=34,reused=10,sample_id=sid,phase='inventory'))
  try:
   v=first_case(c);wire=payload(inventory_messages(v,OUT,prompt,True),config,sid,1);write(f/'call1_request.json',dict(request_sha256=digest(wire),inventory_sha256=None,parameters={k:v for k,v in wire.items() if k!='messages'},messages_image_hash_preview=inventory_messages(v,OUT,prompt,False)))
   raw=call_model(service['base_url']+'/chat/completions',wire,None,config,f/'call1_transport.jsonl');write(f/'call1_response.json',raw);assert raw['finish_reason']=='stop';inv=json.loads(raw['content'])
   try:validate_inventory(inv,[im['id'] for im in v['images']]);write(f/'call1_answer.json',inv);state['first_stage_valid']=True
   except (ValueError,TypeError,KeyError) as e:
    state['first_stage_error']=str(e);assert isinstance(inv,dict) and 'properties' in inv;validate_inventory(inv['properties'],[im['id'] for im in v['images']]);state['inventory_wrapper_preserved']=True
   write(f/'status.json',state);write(OUT/'batch_progress.json',dict(completed=completed,total=34,reused=10,sample_id=sid,phase='recognition_and_choice'));split.run_case(c,config,service);state.update(phase='complete' if state['first_stage_valid'] else 'complete_with_invalid_first_stage',locked_exclusion=read(f/'locked_exclusion.json')['branch_id'])
  except Exception as e:state.update(phase='incomplete',error=str(e))
  write(f/'status.json',state);completed+=1;write(OUT/'batch_progress.json',dict(completed=completed,total=34,reused=10));print(json.dumps(dict(sample_id=sid,**state)),flush=True)
 summary=dict(samples=34,response_count=0,stage1_responses=0,stage2_responses=0,observed_route_responses=0,new_stage1_calls=0,new_calls=0,reused_samples=10,reused_responses=30,valid_samples=0,selected=0,insufficient=0,no_second=0,stage2_valid=0)
 for c in cases:
  f=OUT/'cases'/c['sample_id']
  for name,key in [('call1','stage1_responses'),('observed_route','observed_route_responses'),('call2','stage2_responses')]:
   if (f/(name+'_response.json')).exists():
    summary[key]+=1;summary['response_count']+=1
    if c['sample_id'] not in frozen:summary['new_calls']+=1;summary['new_stage1_calls']+=name=='call1'
  summary['stage2_valid']+=(f/'call2_answer.json').exists();summary['valid_samples']+=(f/'call1_answer.json').exists() and (f/'call2_answer.json').exists()
  if (f/'call2_response.json').exists():
   try:
    a=json.loads(read(f/'call2_response.json')['content']);summary['selected']+=a.get('status')=='selected';summary['insufficient']+=a.get('status')=='insufficient_evidence'
   except ValueError:pass
  else:summary['no_second']+=1
 write(OUT/'summary.json',summary);write(OUT/'status.json',dict(phase='complete' if summary['stage2_valid']==34 else 'complete_with_incomplete_cases',completed=34,finished_at=now(),service_retained=True,**summary));print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
