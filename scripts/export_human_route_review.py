"""Export immutable human-route answers with synchronized offline RGB and maps."""
import argparse,base64,hashlib,io,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.agent_route_choice import read,write,file_hash,digest,now
from scripts.prepare_agent_route_choice import action_name

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);out=p.parse_args().output.resolve();out.mkdir(parents=True,exist_ok=False)
 prep=ROOT/'outputs/agent_route_choice/human_v001/preparation_20261106_01';run=prep.parent/'run_20261106_01/qwen27b'
 source=ROOT/'outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001'
 labels={x['sample_id']:x for x in read(prep/'evaluation_only.json')['labels']};eps={x['episode_id']:x for x in map(json.loads,(source/'inputs/episodes.jsonl').read_text().splitlines())}
 images={};maps={};bundle=[];audit=[]
 def embed(path,expected=None):
  raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
  if expected:assert sha==expected,str(path)
  if sha not in images:images[sha]='data:image/'+('png' if path.suffix=='.png' else 'webp')+';base64,'+base64.b64encode(raw).decode()
  return sha
 for c in read(prep/'dataset.json')['cases']:
  sid=c['sample_id'];label=labels[sid];event=label['event'];eid=event['episode_id'];ep=eps[eid];folder=run/'cases'/sid
  obs=read(source/ep['observations']);traj=read(source/f'evaluation/trajectories/{eid}.json')['frames'];assert len(obs)==len(traj)
  inputs={i['frame']:i for i in c['images']};frames=[]
  for row,o in zip(traj,obs):
   f=row['frame'];assert f==o['frame']==len(frames)
   im=inputs.get(f);key=embed(prep/im['path'],im['sha256']) if im else embed(source/o['rgb'],o['rgb_sha256'])
   action=row.get('action_after_observation');act='TERMINAL' if o['terminal'] else action_name({'action':action}) if action else 'WAIT'
   frames.append(dict(frame=f,position=row['position'],image_key=key,action=act,terminal=o['terminal'],rgb_reused=o['rgb_reused']))
  calls={}
  for stage in (1,2):
   f=folder/f'call{stage}_response.json';raw=read(f) if f.exists() else None;answer=json.loads(raw['content']) if raw else None
   defaults=dict(view_summary='',branches=[],uncertainties=[]) if stage==1 else dict(status='not_called',wrong_branch_id=None,excluded_branch_ids=[],selected_branch_id=None,instruction_evidence=[],wrong_branch_evidence_ids=[],selection_evidence_ids=[],uncertainties=[],route_description=None,error_reason=None,confidence=None)
   display={**defaults,**(answer or {})}
   calls[stage]=dict(answer=answer,display=display,raw_content=raw['content'] if raw else None,validated=(folder/f'call{stage}_answer.json').exists(),response_sha256=file_hash(f) if raw else None)
  transfer=False
  if calls[2]['answer'] is not None:
   req=read(folder/'call2_request.json');meta=json.loads(req['messages_image_hash_preview'][1]['content'][0]['text']);assert meta['branch_inventory']==calls[1]['answer'];assert req['inventory_sha256']==digest(calls[1]['answer']);transfer=True
  scene=event['scene'];cp=c['checkpoint_frame'];assert frames[cp]['position']==event['position']
  review=dict(scene=scene,episode_id=eid,crossing_id=event['id'],crossing={'position':event['position']},checkpoint_position=event['position'],reference_path=label['reference_path'])
  bundle.append(dict(c,frames=frames,review=review,instruction_zh=ep.get('instruction_zh',c['instruction']),calls=calls,status=read(folder/'status.json'),crossing_distance_m=0,inventory_transfer_verified=transfer))
  audit.append(dict(sample_id=sid,episode_id=eid,frames=len(frames),response_sha256={k:v['response_sha256'] for k,v in calls.items()},inventory_transfer_verified=transfer))
 for scene in {c['review']['scene'] for c in bundle}:
  m=read(source/'evaluation/maps.json')[scene];key=embed(source/m['image'],m['sha256']);maps[scene]=dict(geometry=m['geometry'],image=images[key])
 rs=read(run/'summary.json');summary=dict(samples=len(bundle),response_count=rs['saved_responses'],valid_samples=rs['protocol_valid_samples'],selected=rs['raw_selected'],insufficient=rs['raw_insufficient'],no_second=len(bundle)-rs['samples_with_two_responses'],replay_frames=sum(len(c['frames']) for c in bundle),model_calls=0)
 data=dict(cases=bundle,images=images,maps=maps,summary=summary,run_hash=file_hash(run/'manifest.json'),exported_at=now())
 style=(ROOT/'core/agent_panorama_choice_page.html').read_text().split('<style>',1)[1].split('</style>',1)[0]
 page=(ROOT/'core/human_route_review_page.html').read_text().replace('__SHARED_STYLE__',style).replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')).replace('__SCRIPT__',(ROOT/'core/human_route_review.js').read_text())
 from fontTools import subset
 from fontTools.ttLib import TTFont
 cfg=read(ROOT/'core/crossing_visualization_template.json');font=TTFont(cfg['font'],fontNumber=0);sub=subset.Subsetter();sub.populate(text=page);sub.subset(font);buf=io.BytesIO();font.save(buf)
 page=page.replace('__FONT__','data:font/ttf;base64,'+base64.b64encode(buf.getvalue()).decode());html=out/'human_qwen27b_review.html';html.write_text(page);shutil.copy2(cfg['font_license'],out/'FONT_LICENSE.txt')
 hashes={}
 for rel in ['scripts/export_human_route_review.py','core/human_route_review_page.html','core/human_route_review.js','core/agent_panorama_choice_page.html']:
  dest=out/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dest);hashes[rel]=file_hash(dest)
 (out/'workspace_status.txt').write_bytes(subprocess.check_output(['git','status','--short'],cwd=ROOT))
 write(out/'export_audit.json',dict(summary=summary,cases=audit,html_sha256=file_hash(html),source_run=str(run),run_manifest_sha256=data['run_hash'],prepared_manifest_sha256=file_hash(prep/'manifest.json'),source_hashes=hashes,git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),created_at=now()))
 print(json.dumps(dict(html=str(html),mib=html.stat().st_size/1024**2,summary=summary)))
if __name__=='__main__':main()
