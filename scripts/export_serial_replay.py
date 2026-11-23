"""Read completed serial recovery evidence and export a bilingual offline replay."""
import argparse
import copy
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from export_oracle_distance_replay import Media, add_font, action_code, sha, yaw

ROOT = Path(__file__).resolve().parents[1]


def read(p):
    return json.loads(Path(p).read_text())


def rows(p):
    return [json.loads(s) for s in Path(p).read_text().splitlines() if s]


def bilingual(value, translations):
    if isinstance(value, str) and re.search('[\u3400-\u9fff]', value):
        if value not in translations:
            raise ValueError('Missing faithful English translation: '+value)
        return {'zh': value, 'en': translations[value]}
    if isinstance(value, list):
        return [bilingual(v, translations) for v in value]
    if isinstance(value, dict):
        return {k: bilingual(v, translations) for k, v in value.items()}
    return value


def build(campaign, output, cohort_path):
    campaign=campaign.resolve(); output=output.resolve()
    if output.exists(): raise FileExistsError(output)
    status=read(campaign/'status.json'); validation=read(campaign/'validation.json')
    assert status['completed']==status['expected']==1 and validation['native_scoring_complete']
    candidates=[p.parent for p in (campaign/'episodes').glob('*/attempt_*/result.json')]
    assert len(candidates)==1, 'Select one unambiguous completed attempt'
    attempt=candidates[0]; result=read(attempt/'result.json'); events=rows(attempt/'events.jsonl')
    observations=rows(attempt/'observations.jsonl'); config=read(campaign/'config.json')
    # This first export deliberately rejects unsupported recovery records instead of
    # silently misaligning frame IDs across legs or fabricating intervention views.
    assert result['recoveries']==result['handoffs']==0
    assert all(f['leg']==0 and not f['local'] for f in observations)
    assert all(f['index']==i==f['sequence'] for i,f in enumerate(observations))
    cohort=read(cohort_path); dataset=Path(cohort['dataset'])
    case=next(c for c in cohort['cases'] if c['episode_id']==result['episode_id'])
    historical=next(r for r in rows(dataset/'inputs/episodes.jsonl') if r['episode_id']==result['episode_id'])
    original=read(dataset/'evaluation/trajectories'/(result['episode_id']+'.json'))
    instruction=next(e['instruction'] for e in events if e['kind']=='episode_started')
    assert instruction==historical['instruction']==case['instruction']
    assert [p[:2] for p in result['metrics']['reference_path']]==[p[:2] for p in original['reference_path']]
    media=Media(); source_files={}
    def audit(path):
        path=Path(path).resolve(); source_files[str(path.relative_to(ROOT))]=sha(path)
    for p in [campaign/'status.json',campaign/'validation.json',campaign/'config.json',campaign/'manifest.json',campaign/'official_result.json',attempt/'events.jsonl',attempt/'observations.jsonl',attempt/'result.json',cohort_path,dataset/'evaluation/trajectories'/(result['episode_id']+'.json'),dataset/'inputs/episodes.jsonl',dataset/'evaluation/maps.json']:
        audit(p)
    action_events=[e for e in events if e['kind']=='action']; jevs=[e for e in events if e['kind']=='jev']
    assert len(action_events)==len(jevs)==len(observations)==result['actions']
    frames=[]
    for i,(obs,act,j) in enumerate(zip(observations,action_events,jevs)):
        assert act['action_count']==j['frame']==i and sha(obs['path'])==obs['sha256']
        audit(obs['path'])
        frames.append(dict(index=i,image=media.add(obs['path'],640),position=obs['position'],yaw=yaw(obs['rotation']),
                           physics_ticks=obs['physics_ticks'],sha256=obs['sha256'],action=action_code(act['action']),
                           action_time=act['time'],probability=j['probability'],filtered=j.get('filtered')))
    translation_path=ROOT/'core/serial_replay_translations.json'; translations=read(translation_path)
    spec=importlib.util.spec_from_file_location('frozen_jev',campaign/'code/core/jev_node.py')
    frozen=importlib.util.module_from_spec(spec); spec.loader.exec_module(frozen)
    node_events=[e for e in events if e['kind']=='node']; deviation_events=[e for e in events if e['kind']=='deviation']
    nodes=[]; retained=[]
    for e,review in zip(node_events,deviation_events):
        n=copy.deepcopy(e['node']); assert n['id']==review['node'] and n['emittedAt']==e['action_count']
        previous=retained[-1] if retained else None
        replaced=retained.pop() if e['relation']=='same' else None
        retained.append(n['id'])
        n.update(relation=e['relation'],previous_candidate=previous,replaced=replaced,retained_after=list(retained),
                 verdict=review['answer']['verdict'],review_previous=review['previous'],answer=review['answer'])
        nodes.append(n)
    by_id={n['id']:n for n in nodes}; calls=[]; prompts={}; jev_index=0
    for directory in sorted((attempt/'requests').iterdir()):
        if not directory.is_dir(): continue
        stage=directory.name.split('_',1)[1]; request=read(directory/'request.json')
        assert stage in ('jev','dedup','deviation'), stage
        for p in directory.glob('*.json'): audit(p)
        if stage=='jev':
            answer=read(directory/'result.json'); image_audit=read(directory/'images.json')
            images=[dict(frame=x['frame'],label='F'+str(x['frame']),sha256=x['source_sha256']) for x in image_audit]
            frame=images[-1]['frame']; assert frame==jev_index; jev_index+=1
            assert answer['answer']['probability_yes']==frames[frame]['probability']
            assert request['state']['context']==frozen.COMPACT_FALLBACK_CONTEXT_EN
            assert request['questions']['fallback_point']['instructions']==frozen.COMPACT_FALLBACK_INSTRUCTIONS_EN
            assert request['questions']['fallback_point']['criteria']==frozen.COMPACT_FALLBACK_CRITERIA_EN
            raw_answer=read(directory/'response.json'); metadata=request['state']
            displayed=answer['answer']; seconds=answer['latency_seconds']; transport=answer['transport']
            prompts['jev']={lang:dict(context=getattr(frozen,'COMPACT_FALLBACK_CONTEXT_'+lang.upper()),
                instructions=getattr(frozen,'COMPACT_FALLBACK_INSTRUCTIONS_'+lang.upper()),criteria=getattr(frozen,'COMPACT_FALLBACK_CRITERIA_'+lang.upper())) for lang in ['zh','en']}
        else:
            metadata=request['metadata']; images=request['images']; raw_answer=read(directory/'answer.json')
            n=by_id[metadata['current_id']]; frame=n['emittedAt']
            displayed=bilingual(raw_answer,translations) if stage=='dedup' else raw_answer
            if stage=='deviation': assert raw_answer==n['answer']; n['mode']=metadata['mode']
            n[stage+'_request']=len(calls)
            transport=read(directory/'transport.json'); seconds=transport['seconds']
            en_path=(ROOT/'core/serial_replay_dedup_prompt_en.txt') if stage=='dedup' else ROOT/'experiments/deviation_progress/v003/run_20261112_05/snapshot/run/prompt_en.txt'
            if stage=='deviation':
                # Display translations were not copied into the simulation bundle.
                # Verify the paired Chinese prompt before reusing the source English.
                assert en_path.with_name('prompt_zh.txt').read_text()==request['prompt']
                audit(en_path.with_name('prompt_zh.txt'))
            audit(en_path); candidate=dict(zh=request['prompt'],en=en_path.read_text())
            if stage in prompts: assert prompts[stage]==candidate
            prompts[stage]=candidate
        for image in images:
            assert image['sha256']==frames[image['frame']]['sha256']
            image['image']=frames[image['frame']]['image']
        call=dict(id=directory.name,stage=stage,frame=frame,images=[{k:x[k] for k in ['frame','label','sha256','image']} for x in images],
                  metadata=metadata,answer=displayed,raw_request=request,raw_answer=raw_answer,
                  latency_seconds=seconds,transport=transport,source=str(directory.relative_to(ROOT)))
        calls.append(call)
        if stage=='jev': frames[frame]['request']=len(calls)-1
    assert jev_index==len(frames)
    prior_translations={'尚未确认此前完成了哪些导航要求。': 'Prior completion of navigation requirements is unconfirmed.'}
    for n in nodes:
        progress=n['answer'].get('semantic_progress')
        if progress: prior_translations[progress['zh']]=progress['en']
    for call in calls:
        if call['stage']=='deviation':
            prior=call['metadata']['prior_semantic_progress']
            call['prior_progress']={'zh':prior,'en':prior_translations[prior]}
    maps=read(dataset/'evaluation/maps.json'); scene_map=maps[case['scene']]
    assert sha(dataset/scene_map['image'])==scene_map['sha256']; audit(dataset/scene_map['image'])
    metrics={k:v for k,v in result['metrics'].items() if k not in ('reference_path','pred_path')}
    summary=dict(frames=len(frames),actions=len(action_events),jev=len(jevs),candidates=len(nodes),retained=len(retained),
                 dedup=sum(c['stage']=='dedup' for c in calls),reviews=len(deviation_events),
                 initialization=sum(n['mode']=='initialization' for n in nodes),
                 verdicts=dict(Counter(n['verdict'] for n in nodes)),recoveries=result['recoveries'],handoffs=result['handoffs'],
                 full_chain_observed=validation['full_chain_observed'])
    data=dict(version='serial_monocular_v001',run=campaign.name,id=result['episode_id'],scene=case['scene'],seed=config['seed'],
              instruction={'zh':historical['instruction_zh'],'en':instruction},frames=frames,nodes=nodes,requests=calls,prompts=prompts,
              summary=summary,metrics=metrics,reference=result['metrics']['reference_path'],official_path=result['metrics']['pred_path'],
              historical=[f['position'] for f in original['frames']],historical_seed=historical['seed'],
              annotations=[dict(id='C%02d'%(i+1),position=t['crossing_position'],frame=t['annotation_frame']) for i,t in enumerate(case['targets'])],
              map=dict(geometry=scene_map['geometry'],image=media.add(dataset/scene_map['image'],0)),
              final_retained=retained,images=media.encode(),source=str(campaign.relative_to(ROOT)))
    assert not summary['full_chain_observed'] and summary['recoveries']==0
    output.mkdir(parents=True); template=ROOT/'core/serial_replay.html'
    html=output/'serial_pipeline_replay.html'
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    html.write_text(template.read_text().replace('__DATA__',payload))
    font=add_font(html)
    sources=[Path(__file__),template,translation_path,ROOT/'core/serial_replay_dedup_prompt_en.txt',ROOT/'scripts/export_oracle_distance_replay.py']
    for p in sources: audit(p); shutil.copy2(p,output/p.name)
    git=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    audit_data=dict(created_at=datetime.now(timezone.utc).isoformat(),git_head=git,summary=summary,metrics=metrics,
                    source_hashes=source_files,html_sha256=sha(html),html_bytes=html.stat().st_size,font=font,
                    media=len(data['images']),full_frame_image_hashes_verified=True,model_calls=0,
                    scope='Completed one-leg serial navigation without recovery; native terminal RGB was not recorded.',
                    data_uses_reference_only_for_offline_display=True)
    (output/'build.json').write_text(json.dumps(audit_data,ensure_ascii=False,indent=2)+'\n')
    (output/'summary.json').write_text(json.dumps(dict(summary=summary,metrics=metrics),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(html=str(html),summary=summary,media=len(data['images']),bytes=html.stat().st_size),ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--campaign',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cohort',type=Path,default=ROOT/'outputs/oracle_crossing/distance_v001/run_20261115_05/cohort.json')
    args=parser.parse_args(); build(args.campaign,args.output,args.cohort)
