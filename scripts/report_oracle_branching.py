"""Summarize paired outcomes, separating triggered and natural/shared results."""
import argparse
import ast
import csv
import html
import json
from pathlib import Path


def simulation_time_step(out, manifest):
    source=Path(manifest['code_root'])/'benchmarks/vlnverse/upstream/vlnverse/configs/evaluator/default_config.py'
    values=[value for node in ast.walk(ast.parse(source.read_text())) if isinstance(node,ast.Dict)
            for key,value in zip(node.keys,node.values) if isinstance(key,ast.Constant) and key.value=='physics_dt']
    assert len(values)==1
    value=values[0]
    dt=(ast.literal_eval(value.left)/ast.literal_eval(value.right)
        if isinstance(value,ast.BinOp) and isinstance(value.op,ast.Div) else ast.literal_eval(value))
    assert dt>0
    # The generated configs merge with the frozen default; do not silently ignore an override.
    for config in (out/'runs/vlnverse/streamvln/results').glob('*/chunk_*/eval_config.py'):
        assert 'physics_dt' not in config.read_text(),f'Explicit time-step override needs review: {config}'
    return dt,str(source)


def write_review(out, manifest, rows, summary):
    """Small reviewable artifacts; raw metrics and audit records remain authoritative."""
    fields=['episode_id','arm','triggered','success','NE','interventions','actions',
            'first_delay_actions','first_delay_physics_ticks','first_delay_sim_seconds',
            'first_delay_model_batches','first_reference_distance_m',
            'first_semantic_evidence','first_correction_goal_distance_m','post_first_correction_actions',
            'first_error_target_id','first_error_matches_historical_target','first_error_reason',
            'last_correction_goal_distance_m','post_last_correction_actions',
            'last_correction_target_id','last_correction_inside_success_radius',
            'untriggered_reason','untriggered_evidence','shared_terminal_group']
    compact=[]
    for r in rows:
        d={k:r.get(k) for k in fields}
        d.update(success=r['metrics']['success'],NE=r['metrics']['NE'],interventions=len(r['interventions']))
        compact.append(d)
    with (out/'results.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(compact)
    esc=lambda x:html.escape(str(x))
    body=['<!doctype html><html lang="zh"><meta charset="utf-8"><title>Oracle 配对识错延迟</title>',
          '<style>body{font:16px system-ui;max-width:1250px;margin:36px auto;padding:0 20px;color:#172432}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{padding:12px;border:1px solid #d6dce2;text-align:left;vertical-align:top}th{background:#edf2f7}small{color:#536273}.ok{color:#08763d}.fail{color:#b52b2b}</style>',
          '<h1>Oracle 配对识错延迟</h1>',
          f'<p>{len(rows)}/30 个分组结果已完成，其中 {sum(r["triggered"] for r in rows)} 个实际纠正分支。同一任务共用一次实际错误前缀，短／中／长按预先标定的语义阶段识错，随后纠正并保留模型记忆。</p>',
          '<p>动作数和距离是实际观察值，不是触发阈值。未触发分支可能共享同一自然结局；成功沿用原生 3 m 标准。此实验为十条历史失败案例的 Oracle 对照，不能代表自动检测或全集效果。</p>',
          '<table><tr><th>档位</th><th>全部已完成结果</th><th>实际纠正后成功</th><th>未触发</th></tr>']
    for arm,label in [('short','短'),('medium','中'),('long','长')]:
        group=summary[arm]
        corrected_successes=group['successes']-group['untriggered_successes']
        body.append(f'<tr><th>{label}</th><td>{group["successes"]}/{group["completed"]}</td><td>{corrected_successes}/{group["triggered"]}</td><td>{group["completed"]-group["triggered"]}</td></tr>')
    body.append('</table><p>仅实际纠正的各档样本集合可能不同；严格配对比较应使用 summary.json 中 fully_triggered_pairs 的共同任务集合。成功不能单凭本表归因于首次纠正；下表列出多次纠正及成功半径内纠正。</p>')
    body.append('<table><tr><th>任务</th><th>短延迟</th><th>中延迟</th><th>长延迟</th></tr>')
    indexed={(r['episode_id'],r['arm']):r for r in rows}
    cases={c['episode_id']:c for c in manifest['cases']}
    for eid in manifest['episode_ids']:
        first=next((r for r in rows if r['episode_id']==eid and r['interventions']),None)
        target_id=first['interventions'][0]['target_id'] if first else cases[eid]['crossing_id']
        target=next(t for t in cases[eid]['targets'] if t['id']==target_id)
        distance=target['planned_goal_distance_m']
        label='首纠正目标' if first else '预存主目标'
        adaptation='；实际错误与历史主目标不同' if first and target_id!=cases[eid]['crossing_id'] else ''
        body.append('<tr><th>'+esc(eid)+f'<br><small>{label} {esc(target_id)} 距终点 {distance:.2f} m'+('（在成功半径内）' if distance<3 else '')+adaptation+'</small></th>')
        for arm in manifest['arms']:
            r=indexed.get((eid,arm))
            if r is None:body.append('<td>待完成</td>');continue
            success=r['metrics']['success']>0
            label='成功' if success else '失败'
            delay=r.get('first_delay_actions')
            evidence=r.get('first_semantic_evidence',r.get('untriggered_evidence','未触发语义阶段，继承原生结局。'))
            body.append(f'<td><strong class="{"ok" if success else "fail"}">{label}</strong> · NE {r["metrics"]["NE"]:.3f} m<br>纠正 {len(r["interventions"])} 次 · {r["actions"]} 动作<br>')
            if r['interventions']:
                body.append(f'末次纠正 {esc(r["last_correction_target_id"])} 后距终点 {r["last_correction_goal_distance_m"]:.3f} m'
                            + ('（已在成功半径内）' if r['last_correction_inside_success_radius'] else '')
                            + f' · 随后 {r["post_last_correction_actions"]} 动作<br>')
            if delay is not None:
                body.append(f'确认错误后 {delay} 动作 / {r["first_delay_model_batches"]} 批 / {r["first_delay_sim_seconds"]:.2f} 模拟秒 · 参考偏距 {r["first_reference_distance_m"]:.3f} m<br>')
            body.append('<small>'+esc(evidence)+'</small><br><a href="oracle_records/'+esc(eid)+'/'+arm+'/result.json">原始结果</a></td>')
        body.append('</tr>')
    body.extend(['</table><p><a href="results.csv">CSV</a> · <a href="summary.json">汇总与恢复核验</a> · <a href="calibration.json">冻结语义标定</a></p>',
                 '<p>实现采用保存的 policy、任务预算与指标状态，恢复后立即执行统一的姿态纠正；不宣称任意 PhysX 隐藏状态的位级回滚。</p></html>'])
    (out/'index.html').write_text('\n'.join(body))


def main():
    p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);a=p.parse_args()
    out=a.campaign.resolve();m=json.loads((out/'manifest.json').read_text());rows=[];audits=[]
    cases={c['episode_id']:c for c in m['cases']}
    physics_dt,physics_dt_source=simulation_time_step(out,m)
    for eid in m['episode_ids']:
        case=out/'oracle_records'/eid
        for arm in m['arms']:
            path=case/arm/'result.json'
            if not path.exists():continue
            r=json.loads(path.read_text());snap=case/('snapshot_'+arm+'.json')
            if not r['triggered']:
                reviews=[json.loads(p.read_text()) for p in sorted((case/'trunk').glob('review_*/response.json'))]
                onset=next((v for v in reviews if v['stage']=='onset'),None)
                cleared=next((v for v in reviews if v['stage']=='clear'),None)
                r['shared_terminal_group']=eid+':trunk'
                if cleared:
                    r['untriggered_reason']='first_error_resolved_before_stage'
                    r['untriggered_evidence']='首次冻结错误在本档触发前自主解除，继承后续未经干预的主干结局。现场依据：'+cleared['reason']
                elif onset:
                    r['untriggered_reason']='native_terminal_before_stage'
                    r['untriggered_evidence']='首次错误已确认，但原生终止早于本档语义阶段；继承同一主干结局。'
                else:
                    r['untriggered_reason']='no_confirmed_error_before_native_terminal'
                    r['untriggered_evidence']='原生终止前未确认可配对的实际错误，继承同一主干结局。'
            if r['interventions']:
                first=r['interventions'][0]
                r['first_correction_goal_distance_m']=first['goal_distance_m']
                r['post_first_correction_actions']=r['actions']-first['action_index']
                r['first_error_target_id']=first['target_id']
                r['first_error_matches_historical_target']=first['target_id']==cases[eid]['crossing_id']
                r['first_error_reason']=first['event']['reason']
                last=r['interventions'][-1]
                r['last_correction_goal_distance_m']=last['goal_distance_m']
                r['last_correction_target_id']=last['target_id']
                r['last_correction_inside_success_radius']=last['goal_distance_m']<3
                r['post_last_correction_actions']=r['actions']-last['action_index']
            if snap.exists():
                s=json.loads(snap.read_text());r['first_delay_actions']=s['action_index']-s['event']['action_index']
                r['first_delay_physics_ticks']=s['physics_ticks']-s['event']['physics_ticks']
                r['first_delay_sim_seconds']=r['first_delay_physics_ticks']*physics_dt
                review=json.loads((case/'trunk'/f'review_{s["action_index"]:04d}'/'request.json').read_text())
                r['first_delay_model_batches']=review['policy']['calls']-s['event']['calls']
                r['first_reference_distance_m']=s['reference_distance_m'];r['first_semantic_evidence']=s['response']['reason']
                proof=json.loads((case/arm/'restore_proof.json').read_text())
                assert proof['accounting_sha256']==s['accounting_sha256']
                assert proof['shared_prefix_sha256']==s['prefix_sha256']
                assert proof['policy']['content_sha256']==s['policy']['content_sha256']
                audits.append(dict(episode_id=eid,arm=arm,restoration_verified=True))
            for iv in (case/arm).glob('correction_*/memory_proof.json'):
                proof=json.loads(iv.read_text());assert proof['equal'] and proof['before']['sha256']==proof['after']['sha256']
            rows.append(r)
    summary={}
    for arm in m['arms']:
        group=[r for r in rows if r['arm']==arm]
        summary[arm]=dict(completed=len(group),expected=10,successes=sum(r['metrics']['success']>0 for r in group),
                         triggered=sum(r['triggered'] for r in group),interventions=sum(len(r['interventions']) for r in group),
                         untriggered_successes=sum(not r['triggered'] and r['metrics']['success']>0 for r in group))
    paired=[eid for eid in m['episode_ids'] if all(any(r['episode_id']==eid and r['arm']==arm and r['triggered'] for r in rows) for arm in m['arms'])]
    paired_summary=dict(episode_ids=paired,count=len(paired),successes={arm:sum(r['metrics']['success']>0 for r in rows if r['episode_id'] in paired and r['arm']==arm) for arm in m['arms']})
    report=dict(protocol=m['protocol'],complete=len(rows)==30,groups=summary,fully_triggered_pairs=paired_summary,restore_audits=audits,results=rows,
                simulation_time=dict(physics_dt_seconds=physics_dt,source=physics_dt_source,meaning='Simulated elapsed time from confirmed error to saved correction state; excludes wall-clock review and loading waits.'),
                limitations=['Oracle semantic labels, not learned error detection.',
                    'Same actual trunk; state restored immediately into canonical correction, not full PhysX bitwise rollback.',
                    'Selected 10 historical failure cases; no claim of benchmark-wide improvement.',
                    'Untriggered arms may share one natural terminal outcome, not independent trials.',
                    'Three of ten unchanged first-correction targets lie within the native 3 m success radius; success alone does not establish substantial post-correction navigation.',
                    'Later corrections may also place the agent inside the success radius; inspect last-correction distance and subsequent actions, not only the first target.'])
    (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    write_review(out,m,rows,summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
