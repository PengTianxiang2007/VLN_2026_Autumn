"""Add the two binary v006 runs to the frozen selected-nine checkpoint replay."""
import json
from pathlib import Path

from export_codex_dedup_comparison import (
    ROOT, answer_texts, memory_prompt_zh, package_replay, payload,
    read, replace_once, save, sha256, translate_memory_decision,
)

V006 = ROOT / 'outputs/codex_tasks/checkpoint_dedup/v006'
RUN = V006 / 'run_20261124_03_terra_fast_remaining7'
RECORD = ROOT / 'experiments/crossing_checkpoint/codex_dedup_v006' / RUN.name / 'exports/selected9_01'
BASE = ROOT / 'outputs/codex_tasks/checkpoint_dedup/v003/selected9_20261124_01/exports/selected9/index.html'
OFFLINE = RUN / 'selected9/exports/terra_selected9_v2'
ONLINE = ROOT / 'outputs/visualization_publishing/terra_fast_v006_selected9_web_20261124_02'
CONTRACT = ('请返回符合输出结构要求的 JSON 对象。自然语言字段使用英文。eligibility 取 eligible 或 not_eligible，在 eligibility_reason 中解释可用支路。'
            '仅在没有上一回退点或资格为 not_eligible 时使用 not_compared。有上一回退点且当前候选符合资格时，选择 same 或 different。'
            '对于 same，在 matched_branches 中列出相对应的支路，a_only 和 b_only 留空。对于 not_compared，matched_branches 和 a_only 留空，在 b_only 中描述当前支路。'
            'previous_id 使用指定的完整编号或 null，current_id 使用当前候选的完整编号。在 matched_branches 中 A 代表指定的历史回退点，B 代表当前候选。'
            '分别通过 A-2、A0、A+2 和 B-2、B0、B+2 引用它们的图像。若判断为 same，程序以当前候选替换上一回退点，并在下一轮引用当前候选。资格为 not_eligible 的候选会被排除。')


def build_model(name, model_id, run, prompt_source, bundle, translations,
                revision="local_route_choice_v006", prompt_file="codex_checkpoint_candidate_binary_en.txt",
                reference_model="memory"):
    results = read(run / 'results.json')
    assert not results['failures']
    prompt = (prompt_source / prompt_file).read_text()
    strings = dict(candidate='\n\n'.join(translations[t] for t in prompt.strip().split('\n\n')), contract=CONTRACT)
    inverse = {}
    history = {c['episode_id']: c for c in bundle['modelReviews'][reference_model]['cases']}
    cases = []
    for case in results['cases']:
        reference = history[case['episode_id']]
        for node in case['nodes']:
            for im in node['images']:
                im.pop('path', None)
        assert case['nodes'] == reference['nodes'] and case['prompt_revision']==revision
        for decision in case['decisions']:
            folder = Path(decision.pop('response_directory'))
            current = next(n for n in case['nodes'] if n['id']==decision['current_id'])
            raw = (folder / 'final.txt').read_text()
            decision.update(raw_text=raw, elapsed_seconds=read(folder / 'response.json')['elapsed_seconds'],
                            prompt_en=(folder / 'prompt.txt').read_text(),
                            prompt_zh=memory_prompt_zh(read(folder / 'request.json'), current, strings))
            assert prompt.strip().format(candidate_id=current['candidate_id'],previous_checkpoint_id=decision['answer']['previous_id'] or 'NONE (no retained checkpoint yet)') in decision['prompt_en']
            for en in answer_texts(decision['answer']):
                zh = translations[en]
                while zh in inverse and inverse[zh]!=en:
                    zh += '（同义译文）'
                inverse[zh] = en
            translate_memory_decision(decision,inverse)
        case['case_index']=reference['case_index']
        cases.append({k:case[k] for k in ('case_number','case_index','episode_id','real_episode_id','nodes','final_active_ids','summary','decisions')})
    return dict(model=model_id, display_model=name, model_detail=name, source_language='en', mode='checkpoint_memory_v003',
                source_tag=ONLINE.name, observation_offsets=[-2,0,2], cases=cases, coverage=len(cases), summary=results['summary'],
                prompt_en=prompt,prompt_zh=strings['candidate'],translations=inverse,
                initialization_en=(prompt_source/'codex_checkpoint_initialization_en.txt').read_text(),
                initialization_zh=bundle['modelReviews']['memory']['initialization_zh'])


def main(astra_run=None, record=RECORD, offline=OFFLINE, online=ONLINE):
    html=BASE.read_text()
    match,bundle=payload(html)
    translations=read(record/'translations.json')
    sources=[('terra6','GPT-6.1 Terra Fast v006','gpt-6.1-terra',RUN/'selected9',RUN),
             ('astra6','GPT-6 Astra v006','gpt-6-astra',astra_run or V006/'run_20261124_01',V006/'run_20261124_01')]
    models={key:build_model(label,model,run,origin/'source/core',bundle,translations)
            for key,label,model,run,origin in sources}
    bundle['modelReviews']={**models,**bundle['modelReviews']}
    for model in bundle['modelReviews'].values():
        model['source_tag']=online.name
    primary=models['terra6']
    # The base sampler expects the same sampling metadata as historical exports.
    for model in models.values():
        for k in ('sampler_version','sampler_config','phase_note_zh','phase_note_en'):
            model[k]=bundle['dedup'][k] if k.startswith('sampler') else (f"{model['coverage']} 条已完成" if k.endswith('zh') else f"{model['coverage']} trajectories completed")
    bundle.update(primaryModel='terra6',tag=online.name,dedup=primary)
    bundle['summary'].update(retained=primary['summary']['retained'],comparisons=primary['summary']['model_calls'])
    content=json.dumps(bundle,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    html=html[:match.start(1)]+content+html[match.end(1):]
    start=html.index('// Display-only filters over frozen model results.')
    end=html.index('</script>',start)
    js=ROOT/'core/codex_dedup_comparison.js'
    html=html[:start]+js.read_text()+'\n'+html[end:]
    archive=package_replay(html,bundle['images'],BASE.parent,offline,online)
    save(record/'snapshot.json',dict(models={k:{'coverage':v['coverage'],'summary':v['summary']} for k,v in bundle['modelReviews'].items()},
        source_sha256={str(p.relative_to(ROOT)):sha256(p) for p in (BASE,js,Path(__file__).resolve(),record/'translations.json',*(run/'results.json' for _,_,_,run,_ in sources))},
        offline=str(offline.relative_to(ROOT)),html_sha256=sha256(offline/'index.html'),zip=archive.name,zip_sha256=sha256(archive)))
    print(online)

if __name__=='__main__':
    main()
