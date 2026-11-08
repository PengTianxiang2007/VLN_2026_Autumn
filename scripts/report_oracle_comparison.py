"""Compare the fixed ten tasks across the live Oracle intervention distances."""
import csv
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'outputs/oracle_crossing'
GROUPS = [('early', '确认走错后尽早纠正', 'seed2_10_multi_20261103')] + [
    (str(d), f'偏移 {d} 米后纠正', f'seed2_10_delay{d}m_20261103') for d in (3, 5, 8, 12)
]


def build():
    manifest = json.loads((BASE / GROUPS[0][2] / 'manifest.json').read_text())
    ids = [c['episode_id'] for c in manifest['cases']]
    groups = []
    for key, label, folder in GROUPS:
        path = BASE / folder
        current = json.loads((path / 'manifest.json').read_text())
        assert current['cases'] == manifest['cases'], 'Cohort/targets changed'
        source = path / 'report/results.json'
        report = json.loads(source.read_text()) if source.exists() else None
        state = path / 'status_oracle.json'
        phase = json.loads(state.read_text())['phase'] if state.exists() else 'not_started'
        groups.append(dict(key=key, label=label, folder=folder, phase=phase,
                           summary=report['summary'] if report else None,
                           cases={c['episode_id']: c for c in report['cases']} if report else {}))
    out = BASE / 'comparison_20261103'
    out.mkdir(exist_ok=True)
    rows = []
    for eid in ids:
        for g in groups:
            c = g['cases'].get(eid, {})
            oracle = c.get('oracle')
            ivs = c.get('interventions', [])
            rows.append(dict(episode_id=eid, group=g['key'], complete=bool(oracle),
                             SR=oracle['metrics']['success'] if oracle else None,
                             fail_reason=oracle['fail_reason'] if oracle else None,
                             corrections=len(ivs) if oracle else None,
                             max_deviation_m=c.get('max_reference_distance_m'),
                             trigger_distances_m=[iv['trigger_reference_distance_m'] for iv in ivs],
                             memory_equal=all(iv['memory_unchanged'] for iv in ivs) if ivs else None,
                             near_goal_handover=any(iv['inside_success_radius_at_handover'] for iv in ivs),
                             local_contact=bool(c.get('analysis', {}).get('local_obstacle_contact_during_recovery'))))
    (out / 'results.json').write_text(json.dumps(dict(groups=[{k: v for k, v in g.items() if k != 'cases'} for g in groups], cases=rows), ensure_ascii=False, indent=2))
    with (out / 'results.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    summary_rows = []
    for g in groups:
        s = g['summary']
        cells = ([f"{s['oracle_complete']}/10", f"{s['oracle_success']}/{s['oracle_complete']} 已完成", str(s['unintervened_success']), str(s['interventions']), f"{s['intervened_success']}/{s['interventions']}" if s['interventions'] else '不适用（无干预）', str(s['correction_events']), str(s.get('ended_without_reaching_threshold', '—')), str(s.get('threshold_reached_without_intervention', '—')), str(s['oracle_falls'])] if s else ['—'] * 9)
        link = f'<a href="../{g["folder"]}/report/index.html">{html.escape(g["label"])}</a>' if s else html.escape(g['label'])
        summary_rows.append('<tr><td>' + link + '</td><td>' + html.escape(g['phase']) + '</td>' + ''.join('<td>' + html.escape(x) + '</td>' for x in cells) + '</tr>')
    task_rows = []
    for eid in ids:
        cells = []
        for g in groups:
            r = next(r for r in rows if r['episode_id'] == eid and r['group'] == g['key'])
            text = '待完成'
            if r['complete']:
                text = ('成功' if r['SR'] else '失败') + f"；纠正 {r['corrections']} 次；{r['fail_reason']}"
                if r['max_deviation_m'] is not None: text += f"；最大偏移 {r['max_deviation_m']:.2f}m"
                if r['near_goal_handover']: text += '；含成功半径内落点'
                if r['local_contact']: text += '；含局部碰撞恢复'
            cells.append('<td>' + html.escape(text) + '</td>')
        task_rows.append('<tr><td>' + html.escape(eid) + '</td>' + ''.join(cells) + '</tr>')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Oracle 偏移程度对照实验</title>
<style>body{font:16px/1.6 system-ui;margin:28px;color:#213047}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{border:1px solid #ccd4df;padding:9px;text-align:left}th{background:#edf2f7}a{color:#1764a0}.scroll{overflow:auto}p{max-width:1100px}</style>
<h1>同样十条任务：纠正时机对照</h1>
<p>无干预对照已完成：0/10 成功，9 条未到目标、1 条跌倒。各组固定 seed2、相同任务、相同 crossing 落点；允许多次纠正，每次保留 policy memory。距离为到完整参考折线的最短水平距离。</p>
<p>“尽早纠正”指确认已经走错分支后尽早接管；接近 crossing 时只启动审阅，不预先替模型选路。地图 crossing 圆心表示决策区域，不是必须跨过的精确触发线。</p>
<p>尚未完成的组不报告全组成功率。未达到阈值就停止、跌倒、卡住或耗尽预算的任务保留原结果；无干预成功单列，不归因于纠正。落点已在成功半径内及局部碰撞恢复的案例应分开分析。该样本经过错误筛选，结果不代表完整 benchmark 提升；带瞬移的 SPL/TL 不作原生复现成绩。</p>
<p>同一 seed 的独立运行并非逐动作完全一致：首条任务的 3 米组与 5 米组，在首次干预前的共同记录中最大水平位置差约 0.228 米，第 52 个动作开始出现动作差异。因此不能把全部组间差异归因于阈值。<a href="prefix_variation.json">查看已核查的前缀差异记录</a>。</p>
<div class="scroll"><table><thead><tr><th>组别 / 详细可视化</th><th>运行状态</th><th>完成</th><th>成功</th><th>其中无干预成功</th><th>干预任务数</th><th>干预后成功 / 实际干预</th><th>纠正次数</th><th>终止前未达阈值</th><th>达阈值但未干预</th><th>跌倒</th></tr></thead><tbody>__SUMMARY__</tbody></table></div>
<h2>逐任务对照</h2><div class="scroll"><table><thead><tr><th>任务</th>__HEADERS__</tr></thead><tbody>__TASKS__</tbody></table></div>
<p><a href="results.csv">下载 CSV</a> · <a href="results.json">完整汇总 JSON</a>。详细报告链接依赖各组 report 目录；下载时应保留目录相对位置。</p></html>'''
    page = page.replace('__SUMMARY__', ''.join(summary_rows)).replace('__HEADERS__', ''.join('<th>' + html.escape(g['label']) + '</th>' for g in groups)).replace('__TASKS__', ''.join(task_rows))
    (out / 'index.html').write_text(page)
    print(json.dumps({g['key']: dict(phase=g['phase'], complete=g['summary']['oracle_complete'] if g['summary'] else 0) for g in groups}, ensure_ascii=False))


if __name__ == '__main__':
    build()
