"""Agent registry; load baseline implementations only when requested."""
import importlib
from vlnverse.agent.base import Agent
_BASELINES = {'cma': ('cma_agent', 'CmaAgent'), 'rdp': ('rdp_agent', 'RdpAgent'), 'seq2seq': ('seq2seq_agent', 'Seq2SeqAgent'), 'internvla_n1': ('internvla_n1_agent', 'InternVLAN1Agent'), 'cma_clip': ('cma_clip_agent', 'CmaCLIPAgent'), 'seq2seq_clip': ('seq2seq_clip_agent', 'Seq2SeqCLIPAgent')}
def load_agent(name):
    if name in _BASELINES:
        importlib.import_module('vlnverse.agent.' + _BASELINES[name][0])
def __getattr__(name):
    for module, class_name in _BASELINES.values():
        if name == class_name:
            return getattr(importlib.import_module('vlnverse.agent.' + module), name)
    raise AttributeError(name)
__all__ = ['Agent'] + [value[1] for value in _BASELINES.values()]
