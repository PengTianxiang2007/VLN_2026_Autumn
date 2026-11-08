"""Run exactly one authorized development case with a preserved prompt revision."""
import argparse,copy,difflib,json,shutil,subprocess,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from core.agent_route_choice import read,write,file_hash,digest,payload,validate_inventory,now
from probe_route_inventory_anchor import messages
from run_agent_route_choice import call_model

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--prompt',type=Path,required=True);ap.add_argument('--registration',type=Path,required=True);a=ap.parse_args()
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);base=ROOT/'outputs/agent_route_choice/human_v002/run_20261106_04';sid='sample_01';c=copy.deepcopy(next(c for c in read(base/'dataset.json')['cases'] if c['sample_id']==sid));reg=read(a.registration)
 service=read(ROOT/'outputs/model_services/qwen27b_gpu0_20261106_01/service.json');config=read(base/'model.json');assert service['model']==config['model']
 baseline=(base/'01_inventory_en.txt').read_text();prompt=a.prompt.read_text();assert prompt!=baseline
 oldwire=payload(messages(c,base,baseline,True),config,sid,1);assert digest(oldwire)==read(base/'cases'/sid/'call1_request.json')['request_sha256']
 for im in c['images']:
  dest=out/im['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(base/im['path'],dest);assert file_hash(dest)==im['sha256']
 wire=payload(messages(c,out,prompt,True),config,sid,1);assert wire['messages'][1]==oldwire['messages'][1];assert {k:v for k,v in wire.items() if k!='messages'}=={k:v for k,v in oldwire.items() if k!='messages'}
 write(out/'dataset.json',{'cases':[c]});write(out/'model.json',config);(out/'01_inventory_en.txt').write_text(prompt)
 (out/'prompt.diff').write_text(''.join(difflib.unified_diff(baseline.splitlines(True),prompt.splitlines(True),fromfile='preserved_previous',tofile=str(a.prompt))))
 write(out/'input_audit.json',{'passed':True,'only_system_prompt_changed':True,'current_frame':c['checkpoint_frame'],'offsets':[i['frame']-c['annotation_frame'] for i in c['images']],'seed_unchanged':True,'image_hashes':[i['sha256'] for i in c['images']]})
 folder=out/'cases'/sid;folder.mkdir(parents=True);write(folder/'call1_request.json',{'request_sha256':digest(wire),'parameters':{k:v for k,v in wire.items() if k!='messages'},'messages_image_hash_preview':messages(c,out,prompt,False),'inventory_sha256':None})
 hashes={}
 for rel in ['scripts/tune_route_inventory_prompt.py','scripts/probe_route_inventory_anchor.py','scripts/run_agent_route_choice.py','core/agent_route_choice.py']:
  p=out/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p);hashes[rel]=file_hash(p)
 write(out/'manifest.json',{'registration':reg,'source_code_sha256':hashes,'prompt_sha256':file_hash(a.prompt),'baseline_prompt_sha256':file_hash(base/'01_inventory_en.txt'),'comparison_run':str(base.relative_to(ROOT)),'git_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'started_at':now()})
 (out/'workspace_status.txt').write_bytes(subprocess.check_output(['git','status','--short'],cwd=ROOT))
 write(out/'status.json',{'phase':'running','sample_id':sid,'stage':1})
 try:
  raw=call_model(service['base_url']+'/chat/completions',wire,None,config,folder/'call1_transport.jsonl');write(folder/'call1_response.json',raw);assert raw['finish_reason']=='stop';answer=json.loads(raw['content']);validate_inventory(answer,[i['id'] for i in c['images']]);write(folder/'call1_answer.json',answer);result={'sample_id':sid,'phase':'complete_pending_semantic_review','branches':len(answer['branches']),'coverage':answer['coverage']}
 except Exception as e:result={'sample_id':sid,'phase':'failed','error':str(e)}
 write(folder/'status.json',result);write(out/'summary.json',{'samples':1,'responses':int((folder/'call1_response.json').exists()),'stage':1,'cases':[result],'stage2_calls':0,'service_retained':True,'semantic_accuracy':'development_case_not_generalization'})
 write(out/'status.json',dict(result,finished_at=now()));print(json.dumps(result));print((folder/'call1_response.json').read_text())
if __name__=='__main__':main()
