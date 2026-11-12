"""Local offline node review. API key is read from stdin/environment, never saved.

Reuses frozen node-establishment and deduplication events. Six independent case
processes; each case is sequential and stops on its first explicit deviation.
"""
from __future__ import annotations
import argparse, base64, concurrent.futures, copy, getpass, hashlib, json, os, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
import httpx

API = 'https://api.deepseek.com'

def now(): return datetime.now(timezone.utc).isoformat()
def sha(data): return hashlib.sha256(data).hexdigest()
def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temporary.replace(path)

def uniform_between(a, b):
    values = list(range(a+1, b))
    if len(values) <= 5: return values
    return [values[round(i*(len(values)-1)/4)] for i in range(5)]

def image_refs(case, a, b):
    indices = sorted(set([a['index'], *uniform_between(a['index'], b['index']), b['index']]))
    images=[]
    for frame in indices:
        record=case['frames'][frame]
        if not record.get('image'): raise ValueError('Missing observation image')
        if record.get('terminal') and not (b.get('terminal_node') and frame==b['index']==len(case['frames'])-1): raise ValueError('Terminal image is allowed only at the final node endpoint')
        role='A=B' if a['index']==b['index'] else 'A' if frame==a['index'] else 'B' if frame==b['index'] else 'history'
        images.append({'frame':frame,'role':role,'image_id':record['image']})
    assert len(images)<=7 and all(a['index']<=im['frame']<=b['index'] for im in images)
    return images

def bilingual(value):
    return isinstance(value,dict) and all(isinstance(value.get(k),str) and value[k].strip() for k in ('zh','en'))

def validate(answer, request):
    if not isinstance(answer,dict): raise ValueError('Answer is not an object')
    required={'previous_id','current_id','verdict','segment_summary','reason','instruction_evidence','visual_evidence','semantic_progress','uncertainties'}
    if set(answer)!=required: raise ValueError('Unexpected/missing answer fields: '+str(sorted(set(answer)^required)))
    if answer['previous_id']!=request['previous_id'] or answer['current_id']!=request['current_id']: raise ValueError('Endpoint ID mismatch')
    verdict=answer['verdict']
    if verdict not in ('consistent','deviated','uncertain'): raise ValueError('Invalid verdict')
    if request['mode']=='initialization' and verdict!='consistent': raise ValueError('Initialization is not a traversed interval')
    for key in ('segment_summary','reason'):
        if not bilingual(answer[key]): raise ValueError('Missing bilingual '+key)
    if verdict=='consistent':
        if not bilingual(answer['semantic_progress']): raise ValueError('Missing semantic progress')
    elif answer['semantic_progress'] is not None: raise ValueError('Unverified progress was advanced')
    if not isinstance(answer['uncertainties'],list) or any(not bilingual(x) for x in answer['uncertainties']): raise ValueError('Invalid uncertainties')
    quotes=answer['instruction_evidence']
    if not isinstance(quotes,list) or len(quotes)>3 or (verdict=='deviated' and not quotes): raise ValueError('Missing instruction evidence')
    for q in quotes:
        if not isinstance(q,dict) or not isinstance(q.get('quote_en'),str) or not q['quote_en'].strip() or q['quote_en'] not in request['instruction_en'] or not isinstance(q.get('quote_zh'),str) or not q['quote_zh'].strip(): raise ValueError('Instruction quote is not an exact supplied excerpt')
    evidence=answer['visual_evidence']; allowed={im['frame'] for im in request['images']}
    if not isinstance(evidence,list) or not 1<=len(evidence)<=3: raise ValueError('Invalid visual evidence')
    for item in evidence:
        if not isinstance(item,dict) or not bilingual(item.get('description')) or not isinstance(item.get('frames'),list) or not item['frames'] or any(type(f) is not int or f not in allowed for f in item['frames']): raise ValueError('Evidence references an unsupplied frame')
    return answer

def call_model(request, site, key, prompt, settings, folder):
    content=[{'type':'text','text':json.dumps({k:v for k,v in request.items() if k not in ('images',)},ensure_ascii=False)}]
    refs=[]
    for im in request['images']:
        path=site / im['path']; data=path.read_bytes()
        if sha(data)!=im['image_id']: raise ValueError('Input image hash mismatch')
        refs.append({**im,'sha256':sha(data),'bytes':len(data)})
        content.extend([{'type':'text','text':f"角色 {im['role']}；实际观测帧 F{im['frame']}。"},
                        {'type':'image_url','image_url':{'url':'data:image/webp;base64,'+base64.b64encode(data).decode(),'detail':'high'}}])
    body={**settings,'messages':[{'role':'system','content':prompt},{'role':'user','content':content}]}
    started=now(); start=time.perf_counter()
    meta={**request,'images':refs,'settings':settings,'prompt_sha256':sha(prompt.encode()),'request_sha256':sha(json.dumps(body,ensure_ascii=False,sort_keys=True).encode()),'started_at':started,'worker_pid':os.getpid()}
    save(folder.with_suffix('.request.json'),meta)
    result={'started_at':started,'worker_pid':os.getpid(),'status':'error'}
    try:
        # One application-level request. No retry based on semantic content or invalid JSON.
        with httpx.Client(timeout=httpx.Timeout(300,connect=30),follow_redirects=False) as client:
            response=client.post(API+'/chat/completions',headers={'Authorization':'Bearer '+key},json=body)
        result['http_status']=response.status_code
        response.raise_for_status()
        raw=response.json(); result['response']=raw
        choice=raw['choices'][0]
        if choice.get('finish_reason')!='stop': raise ValueError('Incomplete response: '+str(choice.get('finish_reason')))
        answer=json.loads(choice['message']['content'])
        result['parsed_original']=answer
        result['answer']=validate(answer,request);result['status']='ok'
    except Exception as error:
        result['error']=(type(error).__name__+': '+str(error)).replace(key,'[redacted]')[:1500]
    result['completed_at']=now();result['elapsed_seconds']=round(time.perf_counter()-start,3)
    save(folder.with_suffix('.response.json'),result)
    return meta,result

def run_case(case, site_string, key, prompt, settings):
    site=Path(site_string); folder=site/'run'/'cases'/f"C{case['case_number']:02d}"
    folder.mkdir(parents=True,exist_ok=True)
    if (folder/'result.json').exists(): return json.loads((folder/'result.json').read_text(encoding='utf-8'))
    if (folder/'events.jsonl').exists(): raise RuntimeError('Incomplete existing case; refusing silent replay')
    anchor=copy.deepcopy(case['nodes'][0])
    progress={'zh':'首次有效节点：尚未确认此前完成了哪些导航要求。','en':'First retained node: prior completion of navigation requirements is unconfirmed.'}
    reviews=[];stop_node=None;started=now()
    def event(kind,**data):
        with (folder/'events.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps({'at':now(),'pid':os.getpid(),'kind':kind,**data},ensure_ascii=False)+'\n')
    event('case_started',case_number=case['case_number'])
    for node in case['nodes']:
        if stop_node: break
        refs=image_refs(case,anchor,node)
        for im in refs: im['path']=case['image_paths'][im['image_id']]
        request={'mode':'initialization' if not reviews else 'segment',
                 'previous_id':anchor['id'],'current_id':node['id'],
                 'previous_frame':anchor['index'],'current_frame':node['index'],
                 'instruction_en':case['instruction_en'],'prior_semantic_progress':progress['zh'],
                 'coverage':'Endpoint observations plus up to five uniformly sampled intermediate observations. Frames are not necessarily consecutive. Review ends at B.',
                 'images':refs}
        event('request_started',node=node['id'],from_frame=anchor['index'],to_frame=node['index'],image_count=len(refs))
        meta,response=call_model(request,site,key,prompt,settings,folder/node['id'])
        item={'node_id':node['id'],'node_frame':node['index'],'available_at_frame':node['emittedAt'],'terminal_node':node.get('terminal_node',False),
              'mode':request['mode'],'previous_id':anchor['id'],'from_frame':anchor['index'],'to_frame':node['index'],
              'prior_progress':copy.deepcopy(progress),'images':refs,
              'status':response['status'],'elapsed_seconds':response['elapsed_seconds'],'started_at':response['started_at'],
              'completed_at':response['completed_at'],'worker_pid':os.getpid(),
              'request_file':str((folder/(node['id']+'.request.json')).relative_to(site)).replace('\\','/'),
              'response_file':str((folder/(node['id']+'.response.json')).relative_to(site)).replace('\\','/'),
              'usage':response.get('response',{}).get('usage',{})}
        if response['status']=='ok':
            answer=response['answer'];item['answer']=answer
            if answer['verdict']=='consistent':
                progress=copy.deepcopy(answer['semantic_progress']);anchor=copy.deepcopy(node)
            elif answer['verdict']=='deviated':
                stop_node=node['id'];item['rollback_target']={'node_id':anchor['id'],'frame':anchor['index'],'progress':copy.deepcopy(progress)}
        else: item['error']=response['error']
        item['committed_progress']=copy.deepcopy(progress)
        item['progress_anchor']={'id':anchor['id'],'frame':anchor['index']}
        reviews.append(item)
        event('request_completed',node=node['id'],status=item['status'],verdict=item.get('answer',{}).get('verdict','error'))
        save(folder/'state.json',{'case_number':case['case_number'],'pid':os.getpid(),'reviews':reviews,'stop_node':stop_node})
        print(json.dumps({'case':case['case_number'],'node':node['id'],'status':item['status'],'verdict':item.get('answer',{}).get('verdict','error')},ensure_ascii=False),flush=True)
        # Authentication / billing failures should not generate more requests.
        if response.get('http_status') in (401,402,403): break
    result={'case_number':case['case_number'],'case_index':case['case_index'],'episode_id':case['episode_id'],
            'real_episode_id':case['real_episode_id'],'scene':case['scene'],'worker_pid':os.getpid(),
            'started_at':started,'completed_at':now(),'reviews':reviews,'stop_node':stop_node,
            'stop_reason':'first_deviation' if stop_node else 'all_nodes_reviewed' if len(reviews)==len(case['nodes']) else 'request_failure',
            'terminal_frame':case['terminal_frame'],'raw_node_count':len(case['nodes']),'retained_node_count':len(case['final_active_ids']),
            'unreviewed_nodes':[n['id'] for n in case['nodes'] if n['id'] not in {x['node_id'] for x in reviews}]}
    save(folder/'result.json',result);event('case_completed',stop_reason=result['stop_reason'])
    return result

def pack(site,manifest,results):
    reviews=[r for c in results for r in c['reviews']]
    summary={'cases':len(results),'scenes':len({c['scene'] for c in results}),'calls':len(reviews),
             'valid':sum(r['status']=='ok' for r in reviews),'errors':sum(r['status']!='ok' for r in reviews),
             'initializations':sum(r['mode']=='initialization' for r in reviews),
             'consistent_segments':sum(r['mode']!='initialization' and r.get('answer',{}).get('verdict')=='consistent' for r in reviews),
             'deviations':sum(r.get('answer',{}).get('verdict')=='deviated' for r in reviews),
             'uncertain':sum(r.get('answer',{}).get('verdict')=='uncertain' for r in reviews),
             'terminal_nodes_reviewed':sum(r.get('terminal_node',False) for r in reviews),'cached_nodes':sum(c['raw_node_count'] for c in results),'cached_retained_nodes':sum(c['retained_node_count'] for c in results),
             'unreviewed_after_stop':sum(len(c['unreviewed_nodes']) for c in results),
             'total_tokens':sum(r.get('usage',{}).get('total_tokens',0) for r in reviews)}
    events=sorted([(r['started_at'],1) for r in reviews]+[(r['completed_at'],-1) for r in reviews])
    inflight=peak=0
    for _,delta in events: inflight+=delta;peak=max(peak,inflight)
    summary['peak_inflight_requests']=peak;summary['worker_processes']=len({c['worker_pid'] for c in results})
    fresh=[r for c in results if c['case_number'] in manifest['new_case_numbers'] for r in c['reviews']]
    summary['new_calls']=len(fresh);summary['reused_calls']=len(reviews)-len(fresh)
    summary['new_valid']=sum(r['status']=='ok' for r in fresh);summary['new_errors']=sum(r['status']!='ok' for r in fresh)
    summary['new_tokens']=sum(r.get('usage',{}).get('total_tokens',0) for r in fresh)
    summary['new_worker_processes']=len({r['worker_pid'] for r in fresh})
    summary['new_cases']=len(manifest['new_case_numbers']);summary['reused_cases']=len(manifest['reused_case_numbers'])
    data={'version':'v003','model':manifest['settings']['model'],'summary':summary,'cases':results,
          'prompt_zh':(site/'run'/'prompt_zh.txt').read_text(encoding='utf-8'),
          'prompt_en':(site/'run'/'prompt_en.txt').read_text(encoding='utf-8'),
          'protocol':manifest['protocol'],'new_case_numbers':manifest['new_case_numbers'],'reused_case_numbers':manifest['reused_case_numbers'],'created_at':now()}
    save(site/'run'/'results.json',data)
    encoded=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    (site/'audit_results.js').write_text('window.JEV_GUARD_DATA='+encoded+';\n',encoding='utf-8')
    return summary

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--site',type=Path,required=True);parser.add_argument('--key-stdin',action='store_true');parser.add_argument('--pack-only',action='store_true');args=parser.parse_args()
    site=args.site.resolve();manifest=json.loads((site/'run'/'manifest.json').read_text(encoding='utf-8'))
    if args.pack_only:
        results=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((site/'run'/'cases').glob('C*/result.json'))]
        print(json.dumps(pack(site,manifest,results),ensure_ascii=False));return
    print('Waiting for API key on stdin.' if args.key_stdin else 'Reading API key from environment.',flush=True)
    key=(getpass.getpass('API key (hidden): ').strip() if sys.stdin.isatty() else sys.stdin.readline().strip()) if args.key_stdin else os.environ.get('DEEPSEEK_API_KEY','')
    if not key: raise SystemExit('Missing API key')
    try:
        with httpx.Client(timeout=30,follow_redirects=False) as client:
            catalog_response=client.get(API+'/models',headers={'Authorization':'Bearer '+key})
        catalog_response.raise_for_status();catalog=catalog_response.json()
        model=next(x for x in catalog['data'] if x['id']==manifest['settings']['model'])
        if model.get('input_modalities') and 'image' not in model['input_modalities']: raise ValueError('Selected model does not advertise image input')
        save(site/'run'/'model_catalog.json',catalog)
        prompt=(site/'run'/'prompt_zh.txt').read_text(encoding='utf-8')
        if sha(prompt.encode())!=manifest['prompt_sha256']: raise ValueError('Prompt changed after preparation')
        cases=[c for c in json.loads((site/'run'/'inputs.json').read_text(encoding='utf-8')) if c['case_number'] in manifest['new_case_numbers']]
        save(site/'run'/'status.json',{'phase':'running','started_at':now(),'supervisor_pid':os.getpid(),'case_numbers':[c['case_number'] for c in cases],'workers':6})
        print('Model catalog verified. Starting six independent case processes.',flush=True)
        results=[json.loads((site/'run'/'cases'/f'C{n:02d}'/'result.json').read_text(encoding='utf-8')) for n in manifest['reused_case_numbers']]
        with concurrent.futures.ProcessPoolExecutor(max_workers=6) as pool:
            futures=[pool.submit(run_case,c,str(site),key,prompt,manifest['settings']) for c in cases]
            for future in concurrent.futures.as_completed(futures):
                result=future.result();results.append(result)
                print(json.dumps({'case_complete':result['case_number'],'reviews':len(result['reviews']),'stop_reason':result['stop_reason']},ensure_ascii=False),flush=True)
        results.sort(key=lambda c:c['case_number']);summary=pack(site,manifest,results)
        save(site/'run'/'status.json',{'phase':'complete','completed_at':now(),'summary':summary,'workers_exited':True})
        print(json.dumps({'complete':summary},ensure_ascii=False),flush=True)
    except Exception as error:
        message=(type(error).__name__+': '+str(error)).replace(key,'[redacted]')[:1600]
        save(site/'run'/'status.json',{'phase':'failed','at':now(),'error':message})
        print(message,flush=True);raise SystemExit(1)

if __name__=='__main__': main()
