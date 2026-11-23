"""Render one scored snapshot in the published two-call Recovery template."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

from PIL import Image
from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]



def load(path):
    return json.loads(path.read_bytes())


def read_call(folder):
    text = load(folder/'response.json')['choices'][0]['message']['content']
    error_file = folder/'validation_error.json'
    answer_file = folder/'answer.json'
    call = dict(id=folder.name, raw=text, answer=load(answer_file) if answer_file.exists() else None,
                error=load(error_file)['error'] if error_file.exists() else None)
    if not answer_file.exists():
        # The snapshot contains one truncated response. Show only the text actually received.
        chunks = text.partition('// Note:')
        if not chunks[1]:
            if call['error'] and folder.name.endswith(('_branch_review','_branch_instruction')):
                return call
            raise ValueError(f'Missing translation for truncated response at {folder.name}')
        fields = re.findall(r'"(zh|en|quote_zh|quote_en)"\s*:\s*("(?:[^"\\]|\\.)*")', chunks[0])
        note = '注：我会在最终输出里按模式把键名改为 semantic_progress，但保留内容逻辑。等等，提示要求的是 semantic_progress。我会使用这个名字。上面的思考过程在草稿里写错了键名，我会在最终 JSON 中修正。内容是：已完成：进入客厅。当前：停在茶几和沙发前。待执行：无。未解决：还看不到茶几。// 其实，看看先前的进度，“'
        call['partial'] = {}
        for lang, tail in [('zh', note), ('en', 'Note:' + chunks[2].strip())]:
            excerpt = [json.loads(v) for k,v in fields if k in (lang,'quote_'+lang)]
            call['partial'][lang] = '\n\n'.join([*excerpt, tail])
    return call


def branch_answer_en(answer, translations):
    branches = [dict(b, entrance_description=translations[b['entrance_description']],
                     current_choice_basis=translations[b['current_choice_basis']]) for b in answer['branches']]
    previous = answer['previous_attempt']
    return dict(branches=branches, previous_attempt=dict(previous, reason=translations[previous['reason']]),
                uncertainties=[translations[u] for u in answer['uncertainties']])


def action_code(event):
    cmd=event['action']
    return 0 if 'stop' in cmd else cmd['move_by_discrete'][0]


def case_outputs(attempt, case, dest, translations, local_zh):
    events=[json.loads(line) for line in (attempt/'events.jsonl').read_text().splitlines()]
    folders=iter(sorted(f for f in (attempt/'requests').iterdir()
                        if f.name.split('_',1)[-1] in ('deviation','branch_review','branch_instruction')))
    reviews=[]; pending=None
    restored={(e['leg'], e['action']):e for e in case['events'] if e['type']=='rollback'}
    reviewed=iter(e for e in case['events'] if e['type'] in ('deviation','deviation_gate'))
    all_actions=[e for e in events if e['kind']=='action']
    frame_actions = {(e['leg'], e['frame']): e['action_count'] for e in events if e['kind']=='jev'}
    obs = [json.loads(line) for line in (attempt/'observations.jsonl').read_text().splitlines()]
    projections = case['current']['points']

    def take(stage):
        folder=next(folders)
        if folder.name.split('_',1)[1]!=stage: raise ValueError(f'Cannot align {attempt} with {stage} at {folder.name}')
        return folder,read_call(folder),load(folder/'request.json')

    def execution(event):
        leg=event['leg']
        rollback=restored.get((leg,event['action_count']))
        if rollback is None:
            return {}
        return dict(rollback=rollback,
                    handoff=next((h for h in case['events'] if h['type']=='handoff' and h['leg']==leg), None),
                    localActions=[[a['action_count'],action_code(a)] for a in all_actions if a['controller']=='local' and a['leg']==leg],
                    resumedActions=[[a['action_count'],action_code(a)] for a in all_actions if a['controller']=='original' and a['leg']==leg+1],
                    localStop=any(a['kind']=='local_stop' and a['leg']==leg for a in events))

    for e in events:
        kind=e['kind']
        if kind in ('deviation','deviation_gate'):
            folder,call,req=take('deviation')
            aligned=next(reviewed)
            assert (aligned['leg'],aligned['action'],aligned['type'])==(e['leg'],e['action_count'],kind)
            assert (e['answer'] is None)==bool(call['error'])
            if e['answer'] is not None: assert e['answer']==call['answer']
            meta=req['metadata']
            call.update(inputs=[int(Path(im['path']).stem) for im in req['images']],
                        previous=meta['previous_id'],node=meta['current_id'],leg=e['leg'],
                        action=e['action_count'],seq=aligned['seq'],terminal=aligned['terminal'],kind=kind)
            start, end = call['inputs'][0], call['inputs'][-1]
            assert obs[start]['leg'] == obs[end]['leg'] == e['leg']
            first_action = frame_actions.get((e['leg'], obs[start]['index']), e['action_count'])
            last_action = frame_actions.get((e['leg'], obs[end]['index']), e['action_count'])
            moves = [action_code(a) for a in all_actions if a['leg']==e['leg'] and
                     a['controller']=='original' and first_action<=a['action_count']<last_action]
            start_xy = projections[start]
            call['motion'] = dict(actions=[moves.count(code) for code in range(4)],
                                  maxOffset=max(((x-start_xy[0])**2+(y-start_xy[1])**2)**.5
                                                for x,y in projections[start:end+1]))
            if kind=='deviation':
                reviews.append(dict(review=call))
                if (e.get('answer') or {}).get('verdict')=='deviated':
                    if pending is not None: pending['outcome']='superseded'
                    pending=reviews[-1]
                    if call['terminal']:pending['outcome']='terminal';pending=None
            else:
                assert pending is not None
                pending['gate']=call
                if (e.get('answer') or {}).get('verdict')!='deviated':
                    pending['outcome']='gateCleared' if e.get('answer') else 'gateInvalid'
                    pending=None
        elif kind=='pending_alarm_superseded' and pending is not None:
            pending['outcome']='superseded';pending=None
        elif kind=='rollback' and e['ended'] and pending is not None:
            pending['outcome']='terminal_during_restore'
            pending['recovery']=dict(status=pending['outcome'],images=[],**execution(e))
            pending=None
        elif kind in ('route_selected','route_unresolved'):
            assert pending is not None
            selected=e['selection']
            result=dict(start=e['action_count'],status=selected['status'],images=[],**execution(e))
            pending.update(recovery=result,outcome=selected['status'])
            pending=None
            if selected['status']=='input_incomplete':
                continue
            first_f,first,req1=take('branch_review')
            result['first']=first
            if first['error']:
                assert selected['status']=='invalid_answer' and selected['stage']=='branch_review'
                continue
            second_f,second,req2=take('branch_instruction')
            assert [im['sha256'] for im in req1['images'][:3]]==[im['sha256'] for im in req2['images']]
            assert len(req1['images'])==7
            first['english']=branch_answer_en(first['answer'],translations)
            instruction=(second['answer'] or {}).get('recovery_instruction_en')
            second['zh']=local_zh[instruction] if instruction else None
            images=[]
            for im in req1['images']:
                path=Path(im['path']).resolve()
                assert path.is_relative_to(attempt)
                camera=im['label'].split(' |')[0]
                seq=int(path.parent.name) if path.parent.parent.name=='checkpoint_views' else int(path.stem)
                name=f'{first_f.name}_{camera}.jpg'
                with Image.open(path) as rgb:rgb.convert('RGB').save(dest/name,quality=86)
                images.append(dict(camera=camera,seq=seq,legFrame=im['frame'],file=name))
            result.update(second=second,images=images)
            if kind=='route_selected':
                n=result['rollback']
                assert n['target']==images[0]['seq'] and n['instruction']['en']==instruction
        elif kind in ('terminal_review','terminal_no_takeover','episode_finished') and pending is not None:
            pending['outcome']='terminal';pending=None
    assert next(folders,None) is None and next(reviewed,None) is None
    assert sum('rollback' in x.get('recovery',{}) for x in reviews)==case['rollbacks']
    return reviews


def export(out, record, prior):
    snap=load(out/'snapshot.json');campaign=out.parent.parent
    source=(out/'data.js').read_text()
    data=json.loads(source.removeprefix('const DATA = ').removesuffix(';\n'))
    tr=load(record/'branch_translations.json');local_zh=load(prior/'translations.json')['recovery']
    local_zh.update({'Continue straight ahead down the hallway, keeping the four framed artworks on your right.':'沿走廊径直向前，让四幅装框艺术品位于右侧。',
                     'Turn right into the bright hallway opening.':'右转进入明亮的走廊开口。'})
    cases={c['id']:c for c in data['cases']}; per_case={}
    for rel in snap['attempts']:
        attempt=(campaign/rel).resolve();key=attempt.parent.name
        per_case[key]=case_outputs(attempt,cases[key],out/'media'/key,tr,local_zh)
    totals=Counter()
    for group in per_case.values():
        for r in group:
            totals['review']+=1;totals['gate']+=int('gate' in r)
            totals['twoStage']+=int('second' in r.get('recovery',{}))
            if r['review']['answer'] and not r['review']['error'] and r['review']['answer'].get('verdict')=='deviated':totals['alarms']+=1
            if 'recovery' in r:totals[r['outcome']]+=1
    report=dict(totals=totals,cases=per_case)
    (out/'answers.json').write_text(json.dumps(report,ensure_ascii=False,separators=(',',':')))
    (out/'answers.js').write_text('const ANSWERS = '+(out/'answers.json').read_text()+';\n')
    write_site(out)


def write_site(out):
    source=(out/'data.js').read_text()
    style=(ROOT/'core/serial_recovery_answers.css').read_text()
    html=(ROOT/'core/serial_recovery_answers.html').read_text().replace('/* REPLAY_STYLE */',style)
    (out/'index.html').write_text(html);shutil.copyfile(ROOT/'core/serial_recovery_answers.js',out/'player.js')
    font=load(ROOT/'core/crossing_visualization_template.json')
    with TTFont(font['font'],fontNumber=0) as f:
        sub=subset.Subsetter();sub.populate(text=''.join(sorted(set(html+source+(out/'answers.js').read_text()+(out/'player.js').read_text()))))
        sub.subset(f);f.save(out/'replay.ttf')
    (out/'font_license.json').write_text(json.dumps({'license':Path(font['font_license']).read_text()},ensure_ascii=False))
    assets=['data.js','answers.js','answers.json','player.js','paired_results.zip','replay.ttf','font_license.json']
    assets.extend(str(p.relative_to(out)) for folder in ('media','maps') for p in sorted((out/folder).rglob('*')) if p.is_file())
    with ZipFile(out/'replay_offline.zip','w',ZIP_DEFLATED,compresslevel=1) as z:
        for name in ['index.html','paired_results.csv',*assets]:z.write(out/name,name)
    assets.append('replay_offline.zip')
    (out/'online_manifest.json').write_text(json.dumps(dict(html='index.html',assets=assets),indent=2)+'\n')
    print(load(out/'answers.json')['totals'],len(assets))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for arg in ('output','record','previous_record'):ap.add_argument(arg,type=Path)
    ap.add_argument('--reuse-answers', action='store_true', help='Rebuild the interface for an existing frozen answer export.')
    args=ap.parse_args()
    if args.reuse_answers:
        write_site(args.output.resolve())
    else:
        export(args.output.resolve(),args.record.resolve(),args.previous_record.resolve())
