"""Fork C01 at the S04 boundary and issue exactly one candidate judgment."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from core.codex_checkpoint_review import DIRECTIONAL_PROMPT, candidate_input, review_schema, validate_review
from core.codex_client import CodexConfig, CodexSession, save

BASE = ROOT / 'outputs/codex_tasks/deviation_progress/codex_memory_v002'
SOURCE = BASE / 'run_20261125_02_random5'
CASE = SOURCE / 'cases/C01_epkujiale_0036_0_0'
TURN = CASE / 'codex/turns/turn_0005_S04'
OUT = BASE / Path(__file__).resolve().parent.name


def read(path):
    return json.loads(path.read_text())


def fork_before_s04(config, source_id):
    env = dict(os.environ, CODEX_HOME=config.home)
    with subprocess.Popen([config.binary, 'app-server'], env=env, stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=(OUT / 'fork.stderr').open('w'), text=True) as rpc:
        def send(req):
            rpc.stdin.write(json.dumps(req) + '\n')
            rpc.stdin.flush()

        def call(seq, method, params):
            send(dict(id=seq, method=method, params=params))
            for line in rpc.stdout:
                msg = json.loads(line)
                if msg.get('id') == seq:
                    if 'error' in msg:
                        raise ValueError(str(msg['error']))
                    return msg['result']
            raise RuntimeError('Codex app-server closed')

        try:
            call(1, 'initialize', {'clientInfo': {'name':'vln_single_candidate','version':'1.0'},
                                   'capabilities': {'experimentalApi': True}})
            send({'method':'initialized'})
            turns = call(2, 'thread/read', {'threadId':source_id,'includeTurns':True})['thread']['turns']
            old_prompt = (TURN / 'prompt.txt').read_text().strip()
            matches = [i for i,t in enumerate(turns) if any(
                item['type']=='userMessage' and any(x.get('text','').strip()==old_prompt for x in item['content'])
                for item in t['items'])]
            if matches != [4]:
                raise ValueError(f'Expected S04 at turn five, got {matches}')
            stop = turns[4]['id']
            fork = call(3, 'thread/fork', {'threadId':source_id,'beforeTurnId':stop,
                                           'model':config.model,'sandbox':'read-only','approvalPolicy':'never'})
            tid = fork['thread']['id']
            if tid==source_id:
                raise ValueError('Expected separate thread')
            prefix = call(4, 'thread/read', {'threadId':tid,'includeTurns':True})['thread']['turns']
            def user_texts(rows):
                return [[x['text'] for i in t['items'] if i['type']=='userMessage'
                         for x in i['content'] if x['type']=='text'] for t in rows]
            if len(prefix)!=4 or user_texts(prefix)!=user_texts(turns[:4]):
                raise ValueError('Fork does not contain the expected four-turn prefix')
            save(OUT/'fork.json',dict(source_thread_id=source_id,thread_id=tid,before_turn_id=stop,prior_turns=4))
            return tid
        finally:
            rpc.stdin.close()
            rpc.terminate()


def main():
    OUT.mkdir(exist_ok=False)
    manifest = read(SOURCE/'input.json')
    case = next(c for c in manifest['cases'] if c['case_number']==1)
    node = next(n for n in case['nodes'] if n['id']=='S04')
    source_session = read(CASE/'codex/session.json')
    config = CodexConfig(**source_session['config'])
    prompt, images, metadata = candidate_input(None, node, ROOT/manifest['image_root'],
        case['observation_offsets'], binary=True, template=DIRECTIONAL_PROMPT)
    old = (TURN/'prompt.txt').read_text()
    rule = 'When the field of view is limited, count a route-choice opportunity if even a small amount of visible evidence supports another locally available route that could lead to a different spatial area.'
    assert prompt.count(rule)==1 and prompt.replace(' '+rule,'')==old
    assert read(TURN/'schema.json')==review_schema(True)
    assert read(TURN/'request.json')['metadata']==metadata
    assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in images]==[r['sha256'] for r in read(TURN/'request.json')['images']]
    shutil.copy2(DIRECTIONAL_PROMPT,OUT/DIRECTIONAL_PROMPT.name)
    shutil.copy2(__file__,OUT/'replay.py')
    tid = fork_before_s04(config,source_session['thread_id'])
    session = CodexSession(OUT/'codex',config,thread_id=tid,turn_count=4)
    reply = session.ask(prompt,images,review_schema(True),label='S04',metadata=metadata)
    answer = validate_review(json.loads(reply['text']),None,node,True)
    save(OUT/'result.json',dict(case='C01',candidate=node['candidate_id'],original=read(TURN/'final.txt')['eligibility'],
         answer=answer,action='append_current' if answer['eligibility']=='eligible' else 'reject_current',
         model_calls=1,thread_id=tid,git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
    print(reply['text'])

if __name__=='__main__':
    main()
