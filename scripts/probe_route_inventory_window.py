"""Two-case stage-one probe: shift the causal decision window by ten observations."""
import argparse,base64,copy,json,os,shutil,subprocess,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from core.agent_route_choice import read,write,file_hash,digest,now,schema,payload,build_messages,validate_inventory
from scripts.prepare_agent_route_choice import action_name
from scripts.run_agent_route_choice import call_model

SOURCE=ROOT/'outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001'
OLD=ROOT/'outputs/agent_route_choice/human_v001/preparation_20261106_01'
OLD_RUN=OLD.parent/'run_20261106_01/qwen27b'
PROMPT=ROOT/'experiments/agent_route_choice/v001/prompts/frozen_morning_20261106/01_inventory_en.txt'
SIDS=['sample_23','sample_11']

def messages(c,prepared,prompt,embed):
 meta={'current_view_id':'F%04d'%c['checkpoint_frame'],'image_order':[{k:im[k] for k in ('id','frame','phase')} for im in c['images']],
       'approach_action_commands':c['approach_actions'],'orientation':'All branch directions are relative to current_view_id after virtual return.'}
 content=[{'type':'text','text':json.dumps(meta,ensure_ascii=False)}]
 for im in c['images']:
  path=prepared/im['path'];assert file_hash(path)==im['sha256']
  url='data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode() if embed else 'PREVIEW_ONLY:image_sha256:'+im['sha256']
  content.extend([{'type':'text','text':'Image %s (%s)'%(im['id'],im['phase'])},{'type':'image_url','image_url':{'url':url}}])
 content.append({'type':'text','text':'Return only JSON matching this schema: '+json.dumps(schema(1))})
 return [{'role':'system','content':prompt},{'role':'user','content':content}]

def main():
 from PIL import Image,ImageChops,ImageDraw
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--registration',type=Path,required=True);ap.add_argument('--execute',action='store_true');a=ap.parse_args()
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);reg=read(a.registration);assert reg['decision_shift_frames']==10; SIDS=reg['sample_ids']; offsets=reg['sample_offsets_from_annotation']; assert offsets==sorted(set(offsets)) and len(offsets)==4 and offsets[-1]==10
 prompt=PROMPT.read_text();assert prompt==(OLD/'prompts/01_inventory_en.txt').read_text()
 state={'phase':'preparing','model_calls':0,'stage':1,'started_at':now()};write(out/'status.json',state)
 service=read(ROOT/reg['service_state']);assert service['phase']=='ready' and service['keep_alive'];assert (Path('/proc')/str(service['server_pid'])).exists()
 config=read(OLD/'model.json');config['model']=service['model']
 assert config['model_path']==service['model_config']['model_path']
 write(out/'model.json',config);write(out/'01_inventory_en.txt',{'unused':False}) if False else None
 (out/'01_inventory_en.txt').write_bytes(PROMPT.read_bytes())
 oldcases={c['sample_id']:c for c in read(OLD/'dataset.json')['cases']};labels={c['sample_id']:c for c in read(OLD/'evaluation_only.json')['labels']};cases=[];audit=[]
 for sid in SIDS:
  original=oldcases[sid];base=copy.deepcopy(original);base['images']=[im for im in base['images'] if im['phase']=='checkpoint_context']
  assert messages(base,OLD,prompt,False)==build_messages(original,OLD,1,prompt,embed_images=False)
  event=labels[sid]['event'];eid=event['episode_id'];obs_path=SOURCE/f'inputs/observations/{eid}.json';obs=read(obs_path)
  C=event['frame'];P=C+10;selected=[C+d for d in offsets];assert selected[0]>=0
  c={'sample_id':sid,'episode_id':eid,'annotation_frame':C,'checkpoint_frame':P,'images':[],'approach_actions':[]}
  for f in selected:
   row=obs[f];assert row['frame']==f and row['eligible_for_inference'] and not row['terminal'] and not row['rgb_reused']
   src=SOURCE/row['rgb'];assert file_hash(src)==row['rgb_sha256'];rel=f'images/{sid}/F{f:04d}.png';dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True)
   with Image.open(src) as image:
    rgb=image.convert('RGB');assert rgb.size==(640,480);rgb.save(dest)
    with Image.open(dest) as saved:assert ImageChops.difference(rgb,saved.convert('RGB')).getbbox() is None
   c['images'].append(dict(id=f'F{f:04d}',frame=f,phase='checkpoint_context',path=rel,sha256=file_hash(dest)))
  executed={}
  for row in obs:
   if row['frame']>P:break
   for act in row['newly_executed_actions']:
    assert act['frame']<row['frame']<=P and act['frame'] not in executed
    executed[act['frame']]=action_name(act)
  c['approach_actions']=[dict(frame=f,action=x) for f,x in sorted(executed.items()) if max(0,P-32)<=f<P]
  assert all(im['frame']<=P for im in c['images']) and c['images'][-1]['frame']==P
  preview=messages(c,out,prompt,False);wire=payload(messages(c,out,prompt,True),config,sid,1)
  original_req=read(OLD_RUN/'cases'/sid/'call1_request.json');params={k:v for k,v in wire.items() if k not in ('messages','model')};assert params=={k:v for k,v in original_req['parameters'].items() if k!='model'}
  folder=out/'cases'/sid;folder.mkdir(parents=True);write(folder/'call1_request.json',{'request_sha256':digest(wire),'parameters':{k:v for k,v in wire.items() if k!='messages'},'messages_image_hash_preview':preview,'inventory_sha256':None})
  sheet=Image.new('RGB',(1280,270),'white');draw=ImageDraw.Draw(sheet)
  for n,im in enumerate(c['images']):
   with Image.open(out/im['path']) as image:sheet.paste(image.resize((320,240)),(n*320,25))
   draw.text((n*320+5,5),im['id']+(' CURRENT' if im['frame']==P else ' HISTORY'),fill='black')
  sheet.save(out/f'{sid}_inputs.png')
  audit.append({'sample_id':sid,'episode_id':eid,'original_frames':[im['frame'] for im in base['images']],'new_frames':selected,'annotation_frame':C,'old_current':C,'new_current':P,'frames_after_annotation':[f for f in selected if f>C],'source_observations_sha256':file_hash(obs_path),'prompt_unchanged':True,'sampling_parameters_unchanged':True,'same_stage1_builder_verified_on_original':True,'action_count':len(c['approach_actions']),'actions_last_frame':c['approach_actions'][-1]['frame']})
  cases.append(c)
 write(out/'dataset.json',{'cases':cases});write(out/'input_audit.json',{'passed':True,'cases':audit,'scope':'Stage-one only; P moves to C+10. Observations after C are available only at delayed P, not at original C.'})
 files=['scripts/probe_route_inventory_window.py','core/agent_route_choice.py','scripts/run_agent_route_choice.py','scripts/prepare_agent_route_choice.py'];hashes={}
 for rel in files:
  dest=out/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dest);hashes[rel]=file_hash(dest)
 write(out/'manifest.json',{'registration':reg,'service_base':service['base_url'],'source_code_sha256':hashes,'prompt_sha256':file_hash(PROMPT),'source_prepared_manifest_sha256':file_hash(OLD/'manifest.json'),'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'created_at':now()})
 (out/'workspace_status.txt').write_bytes(subprocess.check_output(['git','status','--short'],cwd=ROOT))
 if not a.execute:
  write(out/'status.json',{'phase':'prepared','model_calls':0});return
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with opener.open(service['base_url']+'/models',timeout=5) as r:assert config['model'] in [m['id'] for m in json.load(r)['data']]
 results=[]
 for c in cases:
  sid=c['sample_id'];folder=out/'cases'/sid;write(out/'status.json',dict(phase='running',current_sample=sid,completed=len(results),stage=1,started_at=state['started_at']))
  try:
   wire=payload(messages(c,out,prompt,True),config,sid,1);assert digest(wire)==read(folder/'call1_request.json')['request_sha256']
   raw=call_model(service['base_url']+'/chat/completions',wire,None,config,folder/'call1_transport.jsonl');write(folder/'call1_response.json',raw)
   assert raw['finish_reason']=='stop';answer=json.loads(raw['content']);validate_inventory(answer,[im['id'] for im in c['images']]);write(folder/'call1_answer.json',answer)
   result={'sample_id':sid,'phase':'complete_pending_semantic_review','branches':len(answer['branches']),'coverage':answer['coverage']}
  except Exception as e:result={'sample_id':sid,'phase':'failed','error':type(e).__name__+': '+str(e)}
  write(folder/'status.json',result);results.append(result);print(json.dumps(result),flush=True)
 write(out/'summary.json',{'samples':len(SIDS),'stage':1,'responses':sum((out/'cases'/s/'call1_response.json').exists() for s in SIDS),'cases':results,'semantic_accuracy':'not_scored','stage2_calls':0,'service_retained':True})
 write(out/'status.json',dict(phase='complete' if all(r['phase'].startswith('complete') for r in results) else 'complete_with_failures',stage=1,cases=results,finished_at=now(),service_retained=True))

if __name__=='__main__':main()
