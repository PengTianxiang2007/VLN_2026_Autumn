"""Checkpoint navigation memory, optionally interrupting unexecuted actions."""
import hashlib
import json
import random
from pathlib import Path

FIELDS = ('rgb_list','depth_list','pose_list','intrinsic_list','time_ids','action_seq',
          'output_ids','past_key_values','step_id','last_image')


def content_proof(agent, resets):
    from core.oracle_policy_state import audit
    proof = audit(agent, resets, deep=True)
    def strip(x):
        if isinstance(x, dict):
            return {k:strip(v) for k,v in x.items() if k not in ('pointer','version','device')}
        if isinstance(x, list): return [strip(v) for v in x]
        return x
    state = strip(proof['state'])
    return hashlib.sha256(json.dumps(state,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def checkpoint(agent, resets, steps, body):
    import numpy as np
    import torch
    import os
    root = Path(os.environ['VLN_BRANCH_ROOT']).resolve() / 'policy'
    root.mkdir(parents=True, exist_ok=True)
    key = body['key']
    if not key or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in key):
        raise ValueError('Invalid checkpoint key')
    path = root / (key + '.pt')
    operation = body['operation']
    e = agent.evaluator
    extra = {}
    if operation in ('save', 'interrupt_and_save'):
        if operation == 'save' and agent.pending:
            raise ValueError('Checkpoint requires empty action queue')
        with path.open('xb') as output:
            previous_queue = agent.pending
            try:
                if operation == 'interrupt_and_save':
                    extra['discarded_actions'] = list(previous_queue)
                    agent.pending = []
                proof = content_proof(agent,resets)
                payload = dict(evaluator={k:getattr(e,k) for k in FIELDS},
                               cache=e.model.cache,curr_t=e.model.curr_t,
                               agent={k:getattr(agent,k) for k in ('pending','calls','current_episode_id','current_episode_seed')},
                               resets=resets,steps=steps,proof=proof,
                               rng=(random.getstate(),np.random.get_state(),torch.get_rng_state(),torch.cuda.get_rng_state_all()))
                torch.save(payload,output)
                output.flush()
                if content_proof(agent,resets)!=proof: raise RuntimeError('Snapshot mutated policy')
            except BaseException:
                agent.pending = previous_queue
                path.unlink()
                raise
    elif operation == 'restore':
        payload = torch.load(path,weights_only=False)
        if payload['agent']['current_episode_id']!=agent.current_episode_id:
            raise ValueError('Cross-episode restoration forbidden')
        for k,v in payload['evaluator'].items(): setattr(e,k,v)
        e.model.cache=payload['cache'];e.model.curr_t=payload['curr_t']
        for k,v in payload['agent'].items(): setattr(agent,k,v)
        resets=payload['resets'];steps=payload['steps']
        random.setstate(payload['rng'][0]);np.random.set_state(payload['rng'][1])
        torch.set_rng_state(payload['rng'][2]);torch.cuda.set_rng_state_all(payload['rng'][3])
        proof=content_proof(agent,resets)
        if proof!=payload['proof']: raise RuntimeError('Policy restore content mismatch')
    else: raise ValueError('Unknown snapshot operation')
    return dict(operation=operation,key=key,path=str(path),content_sha256=proof,
                step_id=e.step_id,pending_count=len(agent.pending),verified=True,**extra),resets,steps
