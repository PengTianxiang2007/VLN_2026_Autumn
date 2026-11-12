"""Consume existing nodes sequentially within each case; five independent processes.

The key is accepted through stdin or environment only. No sampling or timed frame
replay is performed. Original candidates and responses remain immutable.
"""
from __future__ import annotations
import argparse, base64, concurrent.futures, copy, hashlib, json, mimetypes, os, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
import httpx

RUN=Path(__file__).resolve().parent
SITE=RUN.parents[1]
API='https://api.deepseek.com'

def now(): return datetime.now(timezone.utc).isoformat()
def save(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(path)

def evidence(node,group):
    return [{**im,'label':group+im['label'][1:]} for im in node['images']]

def normalize_refs(refs,node,group):
    if not isinstance(refs,list) or not refs: raise ValueError('Missing evidence references')
    supplied={im['label']:im['frame'] for im in evidence(node,group) if not im.get('missing')}
    by_frame={v:k for k,v in supplied.items()}
    result=[]
    for ref in refs:
        label=None
        if isinstance(ref,str):
            ref=ref.strip().replace('−','-')
            if re.fullmatch(r'F(?:0|[+-][12])',ref): ref=group+ref[1:]
            if ref in supplied: label=ref
            pair=re.fullmatch(r'([ABF](?:0|[+-][12]))\s*[:：]\s*(-?\d+)',ref)
            if pair:
                candidate=pair.group(1)
                if candidate.startswith('F'): candidate=group+candidate[1:]
                if supplied.get(candidate)==int(pair.group(2)): label=candidate
        if isinstance(ref,int) and not isinstance(ref,bool) or isinstance(ref,str) and re.fullmatch(r'-?\d+',ref):
            label=by_frame.get(int(ref))
        if label is None: raise ValueError('Evidence references an absent or inconsistent image: '+str(ref))
        result.append(label)
    return result

def validate(answer,a,b):
    answer=copy.deepcopy(answer)
    if not isinstance(answer,dict) or answer.get('previous_id')!=a['candidate_id'] or answer.get('current_id')!=b['candidate_id']: raise ValueError('Node ID mismatch')
    if answer.get('relation') not in ('same','different','uncertain'): raise ValueError('Invalid relation')
    if not isinstance(answer.get('reason'),str) or not answer['reason'].strip(): raise ValueError('Missing reason')
    for key in ('a_only','b_only'):
        if not isinstance(answer.get(key),list) or any(not isinstance(v,str) or not v.strip() for v in answer[key]): raise ValueError('Invalid unique branches')
    if not isinstance(answer.get('matched_branches'),list): raise ValueError('Invalid matches')
    for match in answer['matched_branches']:
        if not isinstance(match,dict) or not isinstance(match.get('description'),str) or not match['description'].strip(): raise ValueError('Missing branch description')
        match['a_frames']=normalize_refs(match.get('a_frames'),a,'A')
        match['b_frames']=normalize_refs(match.get('b_frames'),b,'B')
    if answer['relation']=='same' and (not answer['matched_branches'] or answer['a_only'] or answer['b_only']): raise ValueError('Same verdict lacks complete branch correspondence')
    return answer

def apply_decision(active,b,relation):
    previous=active[-1] if active else None
    if relation=='same':
        if previous is None or not 0<b['index']-previous['index']<=8: raise ValueError('Invalid replacement')
        active.pop()
    active.append(b)
    return previous

def compare(a,b,key,prompt,settings,folder,log):
    start=time.perf_counter()
    result={'started_at':now(),'previous_id':a['id'],'current_id':b['id'],'worker_pid':os.getpid()}
    images=[*evidence(a,'A'),*evidence(b,'B')]
    try:
        content=[{'type':'text','text':f"A 完整编号：{a['candidate_id']}，动作步 {a['index']}。\nB 完整编号：{b['candidate_id']}，动作步 {b['index']}。\n步数差：{b['index']-a['index']}。以下仅提供两个节点各自的局部观测。"}]
        for group,node in [('A',a),('B',b)]:
            for im in evidence(node,group):
                caption=f"{im['label']}：实际动作步 {im['frame']}"
                if im.get('missing'):
                    content.append({'type':'text','text':caption+'，缺失（轨迹尚未开始）。'})
                    continue
                if im['frame']>node['ready_at_frame'] or im['frame']>node['index']+2: raise ValueError('Future evidence leak')
                path=(SITE/im['path']).resolve()
                if not path.is_relative_to(SITE): raise ValueError('Invalid image path')
                data=path.read_bytes()
                if hashlib.sha256(data).hexdigest()!=im['image_id']: raise ValueError('Image hash mismatch')
                mime=mimetypes.guess_type(path.name)[0] or 'image/webp'
                content.extend([{'type':'text','text':caption},{'type':'image_url','image_url':{'url':f'data:{mime};base64,'+base64.b64encode(data).decode('ascii'),'detail':'high'}}])
        request={**settings,'messages':[{'role':'system','content':prompt},{'role':'user','content':content}]}
        meta={**result,'previous_candidate_id':a['candidate_id'],'current_candidate_id':b['candidate_id'],'step_gap':b['index']-a['index'],'images':images,'settings':settings,'request_sha256':hashlib.sha256(json.dumps(request,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest()}
        save(folder/(b['id']+'.request.json'),meta)
        log('comparison_requested',previous_id=a['id'],current_id=b['id'],step_gap=meta['step_gap'])
        with httpx.Client(timeout=httpx.Timeout(240,connect=30),follow_redirects=False) as client:
            response=client.post(API+'/chat/completions',headers={'Authorization':'Bearer '+key},json=request)
        result['http_status']=response.status_code
        response.raise_for_status()
        body=response.json();result['response']=body
        choice=body['choices'][0]
        if choice.get('finish_reason')!='stop': raise ValueError('Incomplete response: '+str(choice.get('finish_reason')))
        raw=json.loads(choice['message']['content']);result['answer']=validate(raw,a,b)
        result['normalized_references']=raw!=result['answer']
        result['status']='ok'
    except Exception as error:
        result['status']='error'
        result['error']=(type(error).__name__+': '+str(error)).replace(key,'[redacted]')[:1500]
    result['completed_at']=now();result['elapsed_seconds']=round(time.perf_counter()-start,3)
    save(folder/(b['id']+'.response.json'),result)
    log('comparison_completed',previous_id=a['id'],current_id=b['id'],status=result['status'],relation=result.get('answer',{}).get('relation','uncertain'),elapsed_seconds=result['elapsed_seconds'])
    return result

def run_case(case,key,prompt,settings):
    folder=RUN/'cases'/f"C{case['case_number']:02d}"
    folder.mkdir(parents=True,exist_ok=True)
    if (folder/'result.json').exists(): return json.loads((folder/'result.json').read_text(encoding='utf-8'))
    if (folder/'events.jsonl').exists(): raise RuntimeError('Incomplete case exists; refusing to replay API calls silently')
    requests=folder/'requests';requests.mkdir(exist_ok=True)
    events=[];active=[];decisions=[];started=now()
    def log(kind,**data):
        event={'seq':len(events)+1,'at':now(),'worker_pid':os.getpid(),'kind':kind,**data}
        events.append(event)
        with (folder/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
    log('case_started',case_number=case['case_number'],candidate_count=len(case['nodes']))
    for b in case['nodes']:
        a=active[-1] if active else None
        before=[n['id'] for n in active]
        gap=b['index']-a['index'] if a else None
        if gap is not None and gap<=0: raise ValueError('Candidates must arrive in increasing step order')
        log('candidate_received',current_id=b['id'],frame=b['index'],previous_id=a['id'] if a else None,active_ids=before)
        needs=a is not None and gap<=8
        response=compare(a,b,key,prompt,settings,requests,log) if needs else None
        relation=response.get('answer',{}).get('relation','uncertain') if needs else 'not_compared'
        reason=response.get('answer',{}).get('reason',response.get('error','')) if needs else ('第一个节点，直接建立。' if a is None else f'相隔 {gap} 步，超过 8 步，直接建立当前节点。')
        apply_decision(active,b,relation)
        decision={'order':len(decisions)+1,'previous_id':a['id'] if a else None,'current_id':b['id'],'previous_frame':a['index'] if a else None,'current_frame':b['index'],'step_gap':gap,'needs_model':needs,'relation':relation,'reason':reason,'action':'replace_previous' if relation=='same' else 'append_current','active_ids_before':before,'active_ids_after':[n['id'] for n in active],'committed_at':now()}
        if response:
            for k in ['status','answer','error','started_at','completed_at','elapsed_seconds','normalized_references']:
                if k in response:decision[k]=response[k]
            decision['usage']=response.get('response',{}).get('usage',{})
        decisions.append(decision)
        log('node_replaced' if relation=='same' else 'node_established',**decision)
        save(folder/'state.json',{'processed':len(decisions),'active_ids':decision['active_ids_after']})
        print(json.dumps({'case':case['case_number'],'node':b['id'],'previous':a['id'] if a else None,'relation':relation,'active':len(active),'status':decision.get('status','skip')},ensure_ascii=False),flush=True)
    log('case_complete',active_ids=[n['id'] for n in active])
    result={**case,'worker_pid':os.getpid(),'started_at':started,'completed_at':now(),'decisions':decisions,'final_active_ids':[n['id'] for n in active],'events':events,'summary':{'candidates':len(case['nodes']),'retained':len(active),'removed':len(case['nodes'])-len(active),'model_calls':sum(d['needs_model'] for d in decisions),'uncertain':sum(d['relation']=='uncertain' for d in decisions),'errors':sum(d.get('status')=='error' for d in decisions)}}
    save(folder/'result.json',result)
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--key-stdin',action='store_true');args=parser.parse_args()
    key=sys.stdin.readline().strip() if args.key_stdin else os.environ.get('DEEPSEEK_API_KEY','')
    if not key:raise SystemExit('Missing API key')
    manifest=json.loads((RUN/'manifest.json').read_text(encoding='utf-8'))
    prompt=(RUN/'prompt_zh.txt').read_text(encoding='utf-8')
    assert hashlib.sha256(prompt.encode()).hexdigest()==manifest['prompt_sha256']
    assert manifest['upstream_policy']=='existing_raw_sampled_nodes'
    with httpx.Client(timeout=30,follow_redirects=False) as client:
        r=client.get(API+'/models',headers={'Authorization':'Bearer '+key});r.raise_for_status();catalog=r.json()
    model=next(m for m in catalog['data'] if m['id']==manifest['model'])
    assert not model.get('input_modalities') or 'image' in model['input_modalities']
    save(RUN/'model_catalog.json',catalog)
    manifest['execution_status']='running';manifest['started_at']=now();save(RUN/'manifest.json',manifest)
    print(json.dumps({'cases':manifest['case_numbers'],'processes':29,'input':'existing sampled nodes','per_case_requests':'sequential'}),flush=True)
    results=[json.loads((RUN/'cases'/f"C{n:02d}"/'result.json').read_text(encoding='utf-8')) for n in manifest['reused_case_numbers']]
    pending=[c for c in manifest['cases'] if c['case_number'] not in manifest['reused_case_numbers']]
    with concurrent.futures.ProcessPoolExecutor(max_workers=29) as pool:
        futures=[pool.submit(run_case,c,key,prompt,manifest['request_settings']) for c in pending]
        for future in concurrent.futures.as_completed(futures):
            result=future.result();results.append(result)
            print(json.dumps({'completed_case':result['case_number'],**result['summary']}),flush=True)
    results.sort(key=lambda c:c['case_number'])
    manifest['execution_status']='complete';manifest['completed_at']=now();save(RUN/'manifest.json',manifest)
    summary={k:sum(c['summary'][k] for c in results) for k in ['candidates','retained','removed','model_calls','uncertain','errors']}
    summary['worker_processes']=len({c['worker_pid'] for c in results})
    data={**manifest,'cases':results,'prompt_zh':prompt,'summary':summary}
    save(RUN/'results.json',data)
    encoded=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    (RUN/'browser_results.js').write_text("'use strict';\nwindow.JEV_NODE_DEDUP_DATA="+encoded+';\n',encoding='utf-8')
    print(json.dumps({'complete':summary}),flush=True)

if __name__=='__main__':main()
