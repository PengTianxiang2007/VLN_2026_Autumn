"""Read-only policy-state audit; never resets or edits navigation state."""
import hashlib
import json


def audit(agent, resets, deep=False):
    import numpy as np
    import torch
    def encode(x):
        if x is None or isinstance(x,(str,int,float,bool)):
            return x
        if torch.is_tensor(x):
            v=dict(kind='tensor',shape=list(x.shape),dtype=str(x.dtype),device=str(x.device),pointer=x.data_ptr())
            try:v['version']=x._version
            except RuntimeError:v['version']=None
            if deep:
                raw=x.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes()
                v['sha256']=hashlib.sha256(raw).hexdigest()
            return v
        if isinstance(x,np.ndarray):
            return dict(kind='ndarray',shape=list(x.shape),dtype=str(x.dtype),sha256=hashlib.sha256(x.tobytes()).hexdigest())
        if isinstance(x,dict):return {str(k):encode(v) for k,v in x.items()}
        if isinstance(x,(list,tuple)):return [encode(v) for v in x]
        if hasattr(x,'key_cache') and hasattr(x,'value_cache'):
            return dict(kind=type(x).__name__,keys=encode(x.key_cache),values=encode(x.value_cache),seen=getattr(x,'_seen_tokens',None))
        raise TypeError('Unaudited policy memory object: '+str(type(x)))
    e=agent.evaluator
    fields=['rgb_list','depth_list','pose_list','intrinsic_list','time_ids','action_seq','output_ids','past_key_values','step_id','last_image']
    state={k:encode(getattr(e,k)) for k in fields}
    state.update(model_cache=encode(e.model.cache),model_curr_t=encode(e.model.curr_t),pending=encode(agent.pending),calls=agent.calls,resets=resets,
                 episode_id=agent.current_episode_id,episode_seed=agent.current_episode_seed)
    raw=json.dumps(state,sort_keys=True,separators=(',',':')).encode()
    return dict(episode_id=agent.current_episode_id,step_id=e.step_id,pending_count=len(agent.pending),
                pending=list(agent.pending),calls=agent.calls,resets=resets,history_images=len(e.rgb_list),
                sha256=hashlib.sha256(raw).hexdigest(),deep=deep,state=state if deep else None)
