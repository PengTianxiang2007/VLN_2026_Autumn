"""Serial, causal composition of the existing JEV/dedup/deviation/monocular modules.

No simulator, coordinates, reference route or human annotations enter these API
requests. A frame is an actual monocular observation, not an offline sample index.
"""
import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlparse

import httpx

from core.agent_route_choice import schema, validate_inventory
from core.jev_node import (build_compact_fallback_noul_request, call_api,
                           request_without_images, validate_noul_response)
ROOT = Path(__file__).resolve().parents[1]
# VLNVerse has its own top-level `scripts` package. Import these explicitly from
# the frozen project script directory, not through that colliding package name.
sys.path.insert(0, str(ROOT/'scripts'))
from run_deviation_progress_review import uniform_between, validate as validate_deviation
from split_route_stage2 import recognition_schema, check_recognition
from force_route_stage2 import forced_schema, validate_forced
DEDUP = 'experiments/crossing_checkpoint/online_sampling_v001/review_snapshot_20261112/node_deduplication/v001_run02_all'
PROMPTS = {
    'dedup': DEDUP + '/prompt_zh.txt',
    'deviation': 'experiments/deviation_progress/v003/run_20261112_05/snapshot/run/prompt_zh.txt',
    'inventory': 'experiments/agent_route_choice/human_v002/run_20261107_01/01_inventory_en.txt',
    'recognition': 'experiments/agent_route_choice/human_v002/run_20261107_01/01_observed_route_en.txt',
    'choice': 'experiments/agent_route_choice/human_v002/run_20261107_01/02_choose_en.txt',
    'correction': 'experiments/agent_recovery/r2r_v007/prompt_en.txt',
}


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize_deviation_container(answer):
    """Normalize complete bilingual containers without inventing or editing text."""
    if not isinstance(answer,dict): return answer,False
    value=answer.get('uncertainties')
    if (isinstance(value,dict) and set(value)=={'zh','en'}
            and all(isinstance(value[k],str) and value[k].strip() for k in ('zh','en'))):
        normalized=copy.deepcopy(answer)
        normalized['uncertainties']=[normalized['uncertainties']]
        return normalized,True
    if (isinstance(value,dict) and set(value)=={'zh','en'}
            and all(isinstance(value[k],list) for k in ('zh','en'))
            and len(value['zh'])==len(value['en'])
            and all(isinstance(s,str) and s.strip() for k in ('zh','en') for s in value[k])):
        normalized=copy.deepcopy(answer)
        normalized['uncertainties']=[dict(zh=z,en=e) for z,e in zip(value['zh'],value['en'])]
        return normalized,True
    return answer,False


def semantic_settings(config, stage, json_output=True):
    if config.get('semantic_provider', 'deepseek') == 'qwen_local':
        settings=dict(model=config['semantic_model'],max_tokens=8192,
                      temperature=0,top_p=1,seed=config.get('semantic_seed',2),
                      chat_template_kwargs={'enable_thinking':False})
    else:
        settings=dict(model=config['deepseek_model'],max_tokens=32768 if stage in ('deviation','dedup') else 8192,
                      thinking={'type':'enabled' if stage in ('deviation','dedup') else 'disabled'})
        if stage in ('deviation','dedup'): settings['reasoning_effort']='high'
        else: settings['temperature']=0
    if stage=='correction': settings['max_tokens']=512
    if json_output: settings['response_format']={'type':'json_object'}
    return settings


class Sampler:
    def __init__(self):
        self.p = subprocess.Popen(['node', str(ROOT/'scripts/jev_sampler_stdio.cjs')],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)

    def push(self, value, frame):
        self.p.stdin.write(json.dumps(dict(value=value, frame=frame))+'\n'); self.p.stdin.flush()
        line = self.p.stdout.readline()
        if not line: raise RuntimeError('Frozen sampler transport exited')
        result = json.loads(line)
        if 'error' in result: raise RuntimeError(result['error'])
        return result

    def close(self):
        if self.p.poll() is None:
            self.p.stdin.close()
            try: self.p.wait(timeout=5)
            except subprocess.TimeoutExpired: self.p.terminate(); self.p.wait(timeout=5)
        self.p.stdout.close()


class SerialAPI:
    prompt_paths = PROMPTS
    request_timeout = 300

    def __init__(self, directory, config):
        self.directory=Path(directory); self.config=config; self.sequence=0
        self.prompts={k:(ROOT/v).read_text() for k,v in self.prompt_paths.items()}
        self.provider=config.get('semantic_provider','deepseek')
        if self.provider not in ('deepseek','qwen_local'): raise ValueError('Unknown semantic provider')
        self.key=os.environ.get('DEEPSEEK_API_KEY','') if self.provider=='deepseek' else ''
        self.endpoint=config['deepseek_endpoint'] if self.provider=='deepseek' else config['semantic_endpoint']
        if self.provider=='qwen_local':
            url=urlparse(self.endpoint)
            if url.scheme!='http' or url.hostname not in ('127.0.0.1','localhost') or url.username or url.password:
                raise ValueError('Local Qwen must use an unauthenticated loopback HTTP endpoint')
        self.jev_key=os.environ.get('JEV_API_KEY','')
        if not self.jev_key or (self.provider=='deepseek' and not self.key):
            raise RuntimeError('Runtime API credentials are missing')
        self.client=httpx.Client(timeout=httpx.Timeout(self.request_timeout,connect=30), follow_redirects=False, trust_env=False)
        spec=importlib.util.spec_from_file_location('frozen_dedup',ROOT/DEDUP/'run_dedup.py')
        self.dedup_module=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.dedup_module)

    def folder(self, stage):
        self.sequence+=1
        p=self.directory/'requests'/('%05d_%s'%(self.sequence,stage)); p.mkdir(parents=True)
        print('PIPELINE_API '+str(p),flush=True)
        return p

    def jev(self, frames):
        p=self.folder('jev')
        rows=[dict(frame=f['index'],rgb=f['path'],rgb_sha256=f['sha256']) for f in frames]
        request,audit=build_compact_fallback_noul_request(rows,Path('/'),model=self.config['jev_model'])
        save(p/'request.json',request_without_images(request)); save(p/'images.json',audit)
        raw,latency,transport=call_api(self.config['jev_endpoint'],self.jev_key,request,120,p/'wire.json',attempts=3)
        save(p/'response.json',raw)
        result=validate_noul_response(raw)
        save(p/'result.json',dict(answer=result,latency_seconds=latency,transport=transport))
        return result['probability_yes']

    def ask(self, stage, metadata, images, json_output=True, prompt=None, *, settings=None):
        p=self.folder(stage)
        content=[dict(type='text',text=metadata if isinstance(metadata,str) else json.dumps(metadata,ensure_ascii=False))]
        evidence=[]
        for f,label in images:
            if sha(f['path'])!=f['sha256']: raise ValueError('Live RGB changed')
            content.extend([dict(type='text',text=label),dict(type='image_url',image_url={
                'url':'data:image/png;base64,'+base64.b64encode(Path(f['path']).read_bytes()).decode(), 'detail':'high'})])
            evidence.append(dict(frame=f['index'],label=label,path=f['path'],sha256=f['sha256']))
        prompt=prompt or self.prompts[stage]
        if settings is None:
            settings=semantic_settings(self.config,stage,json_output)
        body=dict(settings,messages=[dict(role='system',content=prompt),dict(role='user',content=content)])
        save(p/'request.json',dict(metadata=metadata,images=evidence,prompt=prompt,settings=settings,
                                   request_sha256=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()))
        started=time.time()
        try:
            response=self.client.post(self.endpoint.rstrip('/')+'/chat/completions',
                                      headers={'Authorization':'Bearer '+self.key} if self.key else {},json=body)
            # Keep bodies for audit, never request headers / credentials.
            save(p/'transport.json',dict(status=response.status_code,seconds=time.time()-started))
            response.raise_for_status(); raw=response.json(); save(p/'response.json',raw)
            choice=raw['choices'][0]
            if choice['finish_reason']!='stop': raise ValueError('Incomplete model response')
            text=choice['message']['content']
            answer=json.loads(text) if json_output else text.strip()
            if not answer: raise ValueError('Empty model response')
            save(p/'answer.json',answer); return answer
        except Exception as e:
            message=str(e)
            for secret in (self.key,self.jev_key):
                if secret: message=message.replace(secret,'[REDACTED]')
            save(p/'error.json',dict(error=type(e).__name__+': '+message))
            if isinstance(e,(ValueError,KeyError,TypeError)):
                raise ValueError(stage+' invalid model response: '+message) from None
            raise RuntimeError(stage+' failed: '+message) from None

    def dedup(self, a, b, frames):
        if b['index']-a['index']>8: return 'different'
        images=[]; nodes=[]
        for group,node in [('A',a),('B',b)]:
            refs=[]
            for offset in [-2,-1,0,1,2]:
                idx=node['index']+offset; label=group+('0' if offset==0 else '%+d'%offset)
                missing=idx<0 or idx>=len(frames)
                refs.append(dict(label=label,frame=idx,missing=missing))
                if not missing: images.append((frames[idx],label+'; actual frame F%d'%idx))
            nodes.append(dict(candidate_id=node['id'],index=node['index'],images=refs))
        metadata=dict(previous_id=a['id'],current_id=b['id'],step_gap=b['index']-a['index'],
                      A=nodes[0],B=nodes[1],rule='Replace A only if all physical branches correspond; otherwise keep both.')
        try:
            answer=self.ask('dedup',metadata,images)
            answer=self.dedup_module.validate(answer,*nodes)
            return answer['relation']
        except (ValueError,KeyError,TypeError):
            # Frozen dedup protocol keeps both on invalid output; original saved above.
            return 'uncertain'

    def deviation(self, a, b, frames, instruction, progress, initialization=False):
        indices=sorted(set([a['index'],*uniform_between(a['index'],b['index']),b['index']]))
        refs=[dict(frame=i,role='A=B' if initialization else 'A' if i==a['index'] else 'B' if i==b['index'] else 'history') for i in indices]
        request=dict(mode='initialization' if initialization else 'segment',previous_id=a['id'],current_id=b['id'],
                     previous_frame=a['index'],current_frame=b['index'],instruction_en=instruction,
                     prior_semantic_progress=progress['zh'],coverage='Endpoints plus up to five uniform intermediate frames; no images after B.',images=refs)
        answer=self.ask('deviation',request,[(frames[r['frame']],r['role']+' F%d'%r['frame']) for r in refs])
        normalized,changed=normalize_deviation_container(answer)
        if changed:
            folder=self.directory/'requests'/('%05d_deviation'%self.sequence)
            operation=('parallel_language_arrays_to_bilingual_items' if isinstance(answer['uncertainties']['zh'],list)
                       else 'complete_bilingual_object_to_singleton_array')
            save(folder/'normalization.json',dict(field='uncertainties',operation=operation,
                                                 original_answer_preserved=True,natural_language_and_verdict_unchanged=True))
            save(folder/'normalized_answer.json',normalized)
        return validate_deviation(normalized,request)

    def choose(self, target, frames, instruction):
        c=target['index']; end=len(frames)-1
        context=[c+d for d in [-4,-2,0,2,4,6,10] if 0<=c+d<=end]
        def fid(i): return 'F%04d'%i
        actions=lambda lo,hi: [dict(frame=i,action=frames[i]['action_after']) for i in range(max(0,lo),min(hi,len(frames))) if frames[i].get('action_after')]
        metadata=dict(current_view_id=fid(c),image_order=[dict(id=fid(i),frame=i,phase='before_checkpoint' if i<c else 'current_checkpoint' if i==c else 'after_checkpoint') for i in context],
                      orientation='Every direction is relative to current_view_id.',
                      approach_action_commands=actions(c-32,c),following_observation_action_commands=actions(c,min(c+10,end)),
                      observation_protocol='Online retrospective monocular history. Only already observed offsets are supplied. Later views explain the SAME checkpoint, never move the decision pose.',
                      schema=schema(1))
        inventory=self.ask('inventory',metadata,[(frames[i],fid(i)) for i in context])
        validate_inventory(inventory,[fid(i) for i in context])
        interval=sorted(set([c,*uniform_between(c,end),end]))
        observed_meta=dict(current_view_id=fid(c),branch_inventory=inventory,
                           image_order=[dict(id=fid(i),frame=i,phase='reference' if i==c else 'subsequent_observation') for i in interval],
                           schema=recognition_schema(inventory))
        observed=self.ask('recognition',observed_meta,[(frames[i],fid(i)) for i in interval])
        check_recognition(observed,inventory,[fid(i) for i in interval])
        excluded=observed['observed_branch_id']
        if excluded is None or not any(b['id']!=excluded for b in inventory['branches']):
            return dict(status='insufficient_evidence',inventory=inventory,observed=observed)
        chosen_schema=forced_schema()
        chosen_schema['properties']['wrong_branch_id']={'enum':[excluded]}
        chosen_schema['properties']['excluded_branch_ids']={'type':'array','items':{'enum':[excluded]},'minItems':1,'maxItems':1}
        images=sorted(set(context+interval))
        metadata=dict(current_view_id=fid(c),instruction=instruction,branch_inventory=inventory,
                      locked_observed_route=observed,locked_excluded_branch_ids=[excluded],
                      image_order=[dict(id=fid(i),frame=i) for i in images],
                      approach_action_commands=actions(c-32,c),previous_attempt_action_commands=actions(c,end),
                      checkpoint_context_image_ids=[fid(i) for i in context],wrong_attempt_image_ids=[fid(i) for i in interval],
                      event='The online deviation reviewer flagged the abandoned interval; this is a model judgment, not ground truth.',
                      schema=chosen_schema)
        answer=self.ask('choice',metadata,[(frames[i],fid(i)) for i in images])
        validate_forced(answer,inventory,[fid(i) for i in images],instruction)
        if answer['wrong_branch_id']!=excluded or answer['excluded_branch_ids']!=[excluded]: raise ValueError('Locked exclusion changed')
        branch=next(b for b in inventory['branches'] if b['id']==answer['selected_branch_id'])
        return dict(status='selected',inventory=inventory,observed=observed,choice=answer,branch=branch)

    def correction(self, selection, restored_frame):
        branch=selection['branch']
        prompt=self.prompts['correction'].format(selected_direction=branch['direction'],selected_entrance_description=branch['landmark'])
        return self.ask('correction',{},[(restored_frame,'Current restored monocular view')],False,prompt)

    def close(self): self.client.close()


class SerialDecisions:
    """One episode leg. Node replacement rolls back its speculative progress commit."""
    def __init__(self, api, instruction, log, prior_progress=None, sampler=None):
        self.api=api; self.instruction=instruction; self.log=log
        self.sampler=sampler or Sampler(); self.frames=[]; self.nodes=[]; self.anchor=None
        self.progress=prior_progress or {'zh':'尚未确认此前完成了哪些导航要求。','en':'Prior completion is unconfirmed.'}

    def sample(self, frame):
        if frame['index']!=len(self.frames): raise ValueError('Frame order changed')
        self.frames.append(frame)
        probability=self.api.jev(self.frames[-3:]); result=self.sampler.push(probability,frame['index'])
        self.log('jev',frame=frame['index'],probability=probability,filtered=result.get('filtered'))
        return result.get('node')

    def observe(self, frame):
        node=self.sample(frame)
        return self.node(node) if node else None

    def node(self, candidate):
        node=copy.deepcopy(candidate)
        if node['index']>=len(self.frames): raise ValueError('Unobserved node')
        if self.nodes and node['index']==self.nodes[-1]['index']: return None
        relation='first'
        if self.nodes:
            relation=self.api.dedup(self.nodes[-1],node,self.frames)
            if relation=='same':
                old=self.nodes.pop()
                self.anchor=old['prior_anchor']; self.progress=old['prior_progress']
        self.log('node',node=node,relation=relation)
        node['prior_anchor']=copy.deepcopy(self.anchor); node['prior_progress']=copy.deepcopy(self.progress)
        previous=self.anchor or node
        answer=self.api.deviation(previous,node,self.frames,self.instruction,self.progress,initialization=self.anchor is None)
        node['verdict']=answer['verdict']; self.nodes.append(node)
        self.log('deviation',previous=previous['id'],node=node['id'],answer=answer)
        if answer['verdict']=='consistent':
            self.anchor={k:v for k,v in node.items() if k not in ('prior_anchor','prior_progress')}
            self.progress=answer['semantic_progress']
        elif answer['verdict']=='deviated':
            return dict(target=copy.deepcopy(self.anchor),progress=copy.deepcopy(self.progress),detected_at=node['emittedAt'],answer=answer)
        return None

    def close(self): self.sampler.close()
