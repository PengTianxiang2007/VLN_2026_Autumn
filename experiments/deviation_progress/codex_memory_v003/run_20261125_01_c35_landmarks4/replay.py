"""One C35 landmark-aware fork, with four new frames per reviewed interval."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from core import codex_deviation_review as review
from core.codex_client import CodexConfig, CodexSession, save, sha256
from experiments.deviation_progress.codex_memory_v002.run_20261125_07_c35_conditional import replay as previous

shared = previous.shared
out = shared.BASE.parent / review.LANDMARK_VERSION / HERE.name


def main():
    out.mkdir(parents=True, exist_ok=False)
    template = review.REVIEW_PROMPTS[review.LANDMARK_VERSION]
    assert template==HERE.parent/'prompt_en.txt'
    def prepare(meta):
        prompt = template.read_text().format(**meta, observations=json.dumps(meta['historical_images']))
        return shared.sampled_request(4,prompt,meta,dataset,obs,episode_id=previous.EPISODE)

    first,old_prompt,schema = previous.original(previous.TURNS/'turn_0007_deviation_S04')
    final,_,end_schema = previous.original(previous.TURNS/'turn_0009_deviation_END')
    assert schema==end_schema
    dataset = ROOT/shared.read(shared.SOURCE/'input.json')['image_root']
    obs = [json.loads(l) for l in (dataset/'inputs'/previous.EPISODE/'observations.jsonl').read_text().splitlines()]
    first_input = prepare(first)
    old = previous.OUT/'uniform4/turns/turn_0007_deviation_S04'
    assert [sha256(p) for p in first_input[1]]==[r['sha256'] for r in shared.read(old/'request.json')['images']]
    before,_,after=template.read_text().partition('Use the landmarks named')
    extra='Use the landmarks named'+after.split('\n3. ',1)[0]
    assert first_input[0].replace(extra+'\n','')==(old/'prompt.txt').read_text()
    sources=[Path(__file__),template,Path(previous.__file__),Path(shared.__file__),ROOT/'core/codex_client.py',Path(review.__file__),ROOT/'core/codex_checkpoint_review.py',ROOT/'scripts/run_codex_node_dedup.py']
    for p in sources:
        dest=out/'source'/p.relative_to(ROOT)
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,dest)
    save(out/'protocol.json',dict(episode=previous.EPISODE,version=review.LANDMARK_VERSION,first_frames=first_input[2],
         conditional_end_frames=prepare(final)[2],first_prompt_control=sha256(old/'prompt.txt'),
         git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
         source_hashes={str(p.relative_to(ROOT)):sha256(p) for p in sources}))
    base=shared.read(previous.CASE/'codex/session.json')
    cfg=CodexConfig(**base['config'])
    tid=shared.fork_reviews(cfg,base['thread_id'],old_prompt,['uniform4'],out)['uniform4']
    session=CodexSession(out/'uniform4',cfg,thread_id=tid,turn_count=6)
    stage1=previous.judge(session,'deviation_S04',first_input,first,schema)
    save(out/'first.json',stage1)
    result=dict(first=stage1,terminal_ack_seconds=None,second=None)
    print('first',stage1['verdict'],stage1['elapsed_seconds'],flush=True)
    if stage1['verdict']=='consistent':
        turn=previous.TURNS/'turn_0008_terminal_observation'
        req=shared.read(turn/'request.json')
        rgb=dataset/obs[final['current_frame']]['native_front']['image']
        assert sha256(rgb)==req['images'][0]['sha256']
        ack=session.ask((turn/'prompt.txt').read_text(),[rgb],shared.read(turn/'schema.json'),
                        label='terminal_observation',metadata=req['metadata'])
        if json.loads(ack['text'])!={'ready':True}:
            raise ValueError('Terminal image was not acknowledged')
        final=dict(final,prior_semantic_progress=stage1['semantic_progress']['zh'])
        result['second']=previous.judge(session,'deviation_END',prepare(final),final,schema)
        result['terminal_ack_seconds']=ack['elapsed_seconds']
        print('second',result['second']['verdict'],result['second']['elapsed_seconds'],flush=True)
    save(out/'result.json',result)


if __name__=='__main__':
    main()
