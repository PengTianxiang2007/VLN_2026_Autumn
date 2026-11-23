"""Pool two existing StreamVLN seed2 cohorts without changing source labels."""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'outputs/checkpoint_review/seed2_crossing_attribution_20261103'
NEW = ROOT / 'experiments/oracle_recovery/auto_branch_v001/run_20261117_04_pair200'
SOURCES = {
    'old_scores': ROOT / 'outputs/reproduction/streamvln_scene250_5seeds_20261101_v2/episodes.csv',
    'old_attribution': OLD / 'attribution.csv',
    'old_reviews': OLD / 'attribution_reviews.json',
    'old_remaining': OLD / 'remaining_failure_cases.csv',
    'old_breakdown': OLD / 'remaining_failure_breakdown.json',
    'new_scores': ROOT / 'outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200/baseline/runs/vlnverse/streamvln/results/peng_fine_baseline200_20261117_04/episodes.jsonl',
    'new_comparison': NEW / 'comparison.csv',
    'new_classification': NEW / 'analysis/baseline_failure_20261117_01/classification.csv',
}
CATEGORIES = {
    'route_selection': ('选错路／漏转弯／起步方向错误', 'Wrong route / turn / initial direction'),
    'backtracking': ('反向回返／原路往返', 'Reversal / backtracking'),
    'incomplete_progress': ('路线未完成即停止／局部无效移动', 'Incomplete progress / local motion'),
    'goal_overshoot': ('目标区域附近未停并走过头', 'Goal-area overshoot'),
    'fall_without_route_evidence': ('无明确选路偏航的跌倒（含预热）', 'Falls without route-error evidence'),
    'stuck_without_route_evidence': ('无明确选路偏航的卡住', 'Stuck without route-error evidence'),
    'termination_only_unreviewed': ('历史跌倒／卡住，路线原因未复核', 'Historical fall/stuck: route unreviewed'),
    'uncertain': ('证据不足／混合现象不确定', 'Uncertain / mixed evidence'),
}
OLD_MAP = {
    'crossing': 'route_selection', 'initial_orientation': 'route_selection',
    'backtracking': 'backtracking', 'early_stop': 'incomplete_progress',
    'local_motion': 'incomplete_progress', 'fall': 'termination_only_unreviewed',
    'stuck': 'termination_only_unreviewed', 'mixed_motion': 'uncertain',
    'mixed_backtracking': 'uncertain', 'reference_ambiguity': 'uncertain',
    'alternative_or_stop': 'uncertain',
}
NEW_MAP = {
    'route_choice': 'route_selection', 'route_backtrack': 'backtracking',
    'stop_incomplete': 'incomplete_progress', 'goal_overshoot': 'goal_overshoot',
    'fall_onroute': 'fall_without_route_evidence',
    'warmup_fall': 'fall_without_route_evidence',
    'stuck_onroute': 'stuck_without_route_evidence', 'uncertain': 'uncertain',
}
METRICS = ('SR', 'SPL', 'NE', 'OS', 'TL', 'FR', 'StR')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def keyed(rows):
    result = {r['episode_id']: r for r in rows}
    require(len(result) == len(rows), 'Duplicate source episode IDs')
    return result


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write_csv(path, rows):
    require(bool(rows), 'Cannot export empty table: ' + str(path))
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def metrics(rows):
    return {k: sum(r[k] for r in rows) / len(rows) for k in METRICS}


def build_rows():
    old = [r for r in read_csv(SOURCES['old_scores']) if r['run_seed'] == '2']
    new = [json.loads(line) for line in SOURCES['new_scores'].read_text().splitlines() if line.strip()]
    require(len(old) == 250 and len(new) == 200, 'Incorrect cohort sizes')
    old_ids, new_ids = set(keyed(old)), set(keyed(new))
    require(not old_ids & new_ids, 'Cohorts overlap')
    old_attr = keyed(read_csv(SOURCES['old_attribution']))
    old_remaining = keyed(read_csv(SOURCES['old_remaining']))
    old_reviews = keyed(json.loads(SOURCES['old_reviews'].read_text()))
    new_attr = keyed(read_csv(SOURCES['new_classification']))
    comparisons = keyed(read_csv(SOURCES['new_comparison']))
    require(set(old_attr) == old_ids, 'Old attribution does not cover old cohort')
    require(set(comparisons) == new_ids, 'New native IDs mismatch comparison')
    rows = []
    for cohort, source_rows in [('old250', old), ('new200', new)]:
        for source in source_rows:
            eid = source['episode_id']
            success = float(source['SR']) == 1
            require(float(source['SR']) in (0, 1), 'Nonbinary SR')
            require(int(source['run_seed']) == 2, 'Unexpected seed')
            row = {
                'episode_id': eid, 'scene': source['scene'], 'cohort': cohort,
                'seed': 2, 'episode_seed': int(source['episode_seed']),
                **{k: float(source[k]) for k in METRICS},
                'steps': int(source['steps']), 'termination': source['fail_reason'],
                'category': 'success', 'category_zh': '官方成功',
                'source_status': '', 'source_subtype': '', 'source_group': '',
                'evidence_level': 'official_scoring', 'confidence_original': '',
                'rgb_reviewed_original': '', 'full_navigation_rgb_original': '',
                'expected_original': '', 'actual_original': '', 'reason_original': '',
                'review_basis_original': '', 'evidence_map_original': '',
                'evidence_trace_original': '', 'source_scores': '', 'source_classification': '',
            }
            if cohort == 'old250':
                a = old_attr[eid]
                for key in ('SR', 'NE', 'OS'):
                    require(math.isclose(float(a[key]), row[key], abs_tol=1e-8), 'Old metric mismatch ' + eid)
                require(a['fail_reason'] == row['termination'], 'Old termination mismatch')
                require((a['status'] == 'success') == success, 'Old success label mismatch')
                remaining = old_remaining.get(eid, {})
                group = remaining.get('remaining_group', a['status'])
                review = old_reviews.get(eid)
                if not success:
                    row['category'] = OLD_MAP[group]
                    row['evidence_level'] = 'per_case_review' if review else 'official_termination_only'
                row.update({
                    'source_status': a['status'], 'source_subtype': a.get('subtype', ''),
                    'source_group': group, 'rgb_reviewed_original': a.get('rgb_reviewed', ''),
                    'expected_original': a.get('expected', ''), 'actual_original': a.get('actual', ''),
                    'reason_original': a.get('rationale', ''),
                    'review_basis_original': json.dumps(review.get('review_basis', []), ensure_ascii=False) if review else '',
                    'source_scores': str(SOURCES['old_scores'].relative_to(ROOT)),
                    'source_classification': str((SOURCES['old_remaining'] if remaining else SOURCES['old_attribution']).relative_to(ROOT)),
                })
            else:
                cmp = comparisons[eid]
                require(cmp['scene'] == row['scene'] and int(cmp['episode_seed']) == row['episode_seed'], 'New identity mismatch')
                for key in ('SR', 'SPL', 'NE'):
                    require(math.isclose(float(cmp['baseline_' + key]), row[key], abs_tol=1e-8), 'New metric mismatch ' + eid)
                require(cmp['baseline_fail_reason'] == row['termination'], 'New termination mismatch')
                a = new_attr.get(eid)
                require((a is None) == success, 'New failure classification coverage mismatch')
                if a:
                    require(float(a['baseline_SR']) == row['SR'], 'New classification SR mismatch')
                    require(math.isclose(float(a['baseline_NE_m']), row['NE'], abs_tol=1e-8), 'New classification NE mismatch')
                    require(a['termination'] == row['termination'], 'New classification termination mismatch')
                    row.update({
                        'category': NEW_MAP[a['category']], 'source_status': 'failure',
                        'source_group': a['category'], 'source_subtype': a['category'],
                        'evidence_level': 'per_case_review', 'confidence_original': a['confidence'],
                        'full_navigation_rgb_original': a['full_navigation_rgb'],
                        'reason_original': a['reason_zh'], 'evidence_map_original': a['evidence_map'],
                        'evidence_trace_original': a['evidence_trace'],
                    })
                else:
                    row.update(source_status='success', source_group='success')
                row.update({
                    'source_scores': str(SOURCES['new_scores'].relative_to(ROOT)),
                    'source_classification': str(SOURCES['new_classification'].relative_to(ROOT)) if a else '',
                })
            if not success:
                row['category_zh'] = CATEGORIES[row['category']][0]
            require(all(math.isfinite(row[k]) for k in METRICS), 'Nonfinite score')
            rows.append(row)
    rows.sort(key=lambda r: (r['scene'], r['episode_id']))
    failures = [r for r in rows if r['SR'] == 0]
    require(len(rows) == len(keyed(rows)) == 450, 'Merged IDs invalid')
    require(len(failures) == 253, 'Failure total mismatch')
    require(len(old_reviews) == 105 and len(new_attr) == 102, 'Review count mismatch')
    require(set(old_reviews) <= {r['episode_id'] for r in old if float(r['SR']) == 0}, 'Old reviews contain nonfailures')
    require(len(old_remaining) == 103, 'Old remaining count mismatch')
    require(sum(r['evidence_level'] == 'per_case_review' for r in failures) == 207, 'Review coverage mismatch')
    return rows


def summarize(rows):
    failures = [r for r in rows if r['SR'] == 0]
    categories = []
    for cat, (label, _) in CATEGORIES.items():
        selected = [r for r in failures if r['category'] == cat]
        categories.append({
            'category': cat, 'category_zh': label, 'count': len(selected),
            'pct_failures': 100 * len(selected) / len(failures),
            'pct_all': 100 * len(selected) / len(rows),
            'old250': sum(r['cohort'] == 'old250' for r in selected),
            'new200': sum(r['cohort'] == 'new200' for r in selected),
        })
    scenes = []
    for scene in sorted({r['scene'] for r in rows}):
        selected = [r for r in rows if r['scene'] == scene]
        scenes.append({
            'scene': scene, 'cohort': selected[0]['cohort'], 'episodes': len(selected),
            'successes': sum(r['SR'] == 1 for r in selected),
            'failures': sum(r['SR'] == 0 for r in selected),
            **metrics(selected),
            **{c: sum(r['category'] == c for r in selected) for c in CATEGORIES},
        })
    terminations = []
    for cat, (label, _) in CATEGORIES.items():
        for term in sorted({r['termination'] for r in failures}):
            selected = [r for r in failures if r['category'] == cat and r['termination'] == term]
            terminations.append({'category': cat, 'category_zh': label, 'termination': term, 'count': len(selected)})
    cohort_stats = {}
    for cohort in ('old250', 'new200'):
        selected = [r for r in rows if r['cohort'] == cohort]
        cohort_stats[cohort] = {'episodes': len(selected), 'scenes': len({r['scene'] for r in selected}),
                                'successes': sum(r['SR'] == 1 for r in selected), 'metrics': metrics(selected)}
    subgroup = Counter((r['cohort'], r['source_group'], r['category']) for r in failures)
    mapping_counts = [{'cohort': c, 'source_group': g, 'category': cat, 'count': n} for (c, g, cat), n in sorted(subgroup.items())]
    summary = {
        'episodes': len(rows), 'scenes': len(scenes), 'seed': 2,
        'successes': len(rows) - len(failures), 'failures': len(failures), 'metrics': metrics(rows),
        'cohorts': cohort_stats, 'categories': categories,
        'evidence_counts': dict(Counter(r['evidence_level'] for r in failures)),
        'failure_terminations': dict(Counter(r['termination'] for r in failures)),
        'all_terminations': dict(Counter(r['termination'] for r in rows)),
        'uncertain_cases': 24, 'historical_route_unreviewed_cases': 46,
        'source_candidate_set': {'old_crossing': 48, 'new_route_choice': 56, 'total': 104},
        'route_selection_plus_backtracking': {
            'count': 120, 'pct_failures': 120 / 253 * 100, 'pct_all': 120 / 450 * 100,
            'interpretation': 'Descriptive existing route/direction/backtracking labels; not 120 confirmed Crossing errors or recoverable cases.'},
        'scope': 'Original baseline scores only; existing-label harmonization, no new per-frame reannotation or intervention evaluation.',
        'limitations_zh': [
            '本次合并既有标签，不宣称重新逐帧审阅全部253条失败。',
            '早期46条跌倒/卡住缺少同口径的失败前路线归因，不能认定全为纯物理错误。',
            '107条含3条起步方向错误；13条回返中旧5条为现象描述，不等同于明确错选支路。',
            '24条不确定维持原结论，不并入确认选路错误。',
            '两批场景和历史执行版本不同，合并为描述性样本池，不外推为825条全集指标或版本提升。',
            '新200条原版没有全程RGB；旧批仅部分逐例查看关键RGB，证据深度不同。',
            '未合并Oracle成功率；已确认的Oracle收益只属于另行评测的200条独立运行对照。',
        ],
    }
    require(sum(c['count'] for c in categories) == 253, 'Partition mismatch')
    require(sum(s['episodes'] for s in scenes) == 450, 'Scene totals mismatch')
    require(sum(t['count'] for t in terminations) == 253, 'Termination totals mismatch')
    require(sum(c['count'] for c in categories if c['category'] in ('route_selection', 'backtracking')) == 120, 'Route union mismatch')
    require(len(scenes) == 21, 'Scene count mismatch')
    return summary, categories, scenes, terminations, mapping_counts


def plot(output, summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    ordered = sorted(summary['categories'], key=lambda r: r['count'], reverse=True)
    fig, ax = plt.subplots(figsize=(12, 6.5))
    colors = ['#31688e' if r['category'] not in ('uncertain', 'termination_only_unreviewed') else '#9b9b9b' for r in ordered]
    ax.barh(range(len(ordered)), [r['count'] for r in ordered], color=colors)
    ax.set_yticks(range(len(ordered)))
    ax.set_yticklabels([CATEGORIES[r['category']][1] for r in ordered], fontsize=10)
    ax.invert_yaxis()
    ax.set_xlim(0, 132)
    for i, r in enumerate(ordered):
        ax.text(r['count'] + 1, i, '{} ({:.2f}%)'.format(r['count'], r['pct_failures']), va='center', fontsize=10)
    ax.set_xlabel('Failure cases (percentages use 253 failures)')
    ax.set_title('Pooled StreamVLN baseline: 450 cases / 21 scenes / seed 2\n197 successes (43.78%) | 253 failures (56.22%)', loc='left')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.xaxis.grid(True, alpha=.15)
    ax.set_axisbelow(True)
    fig.text(.02, .015, 'Existing-label harmonization; historical fall/stuck cases lack route review. No new navigation or causal recovery claim.', fontsize=8)
    fig.tight_layout(rect=(0, .04, 1, 1))
    for suffix in ('png', 'pdf'):
        fig.savefig(output / ('failure_distribution.' + suffix), dpi=180, bbox_inches='tight')
    plt.close(fig)


def report(summary):
    lines = [
        '# 450条原版任务合并错误分析', '',
        '状态：完成。合并早期250条seed2与新200条seed2原版结果；450个唯一任务、21场景。', '',
        '成功197/450（43.78%），失败253/450（56.22%）。逐任务加权SPL {:.2f}%，NE {:.4f}米。'.format(summary['metrics']['SPL'] * 100, summary['metrics']['NE']), '',
        '| 合并类别 | 数量 | 占253条失败 | 占450条全部 | 旧250来源 | 新200来源 |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for r in sorted(summary['categories'], key=lambda r: r['count'], reverse=True):
        lines.append('| {} | {} | {:.2f}% | {:.2f}% | {} | {} |'.format(r['category_zh'], r['count'], r['pct_failures'], r['pct_all'], r['old250'], r['new200']))
    lines += ['', '## 解释', '',
        '- 选错路/漏转弯/起步方向错误107条，是最大的单一已分组问题。它包括原48条Crossing候选、新56条选路候选，以及旧other中的3条起步方向错误；不等于107条已证实拓扑分叉错误。',
        '- 回返/往返13条保持独立：旧5条记录明确未见选择新错误支路，新8条按路线进度与方向审阅为反向回返。与107条合计120条（失败47.43%、全体26.67%），只表示路线/方向/回返相关现象。',
        '- 路线未完成或局部无效移动45条（失败17.79%），需要与选路问题区分；现有标签不能证明其全为错误STOP判断。',
        '- 旧46条异常终止没有失败前路线归因。另17条由新一轮审阅归入无明确选路偏航的跌倒/卡住，不能把这两组63条一概认定为纯物理失败。',
        '- 不确定24条保留混合现象和证据不足结论。优先补查旧46条与这24条，可提升70条的分类证据；这不是授权启动重跑。',
        '- 104条现有候选集只是48+56；不因本次合并新增或修改正在运行的多视角采集清单。', '',
        '## 来源与限制', '', *['- ' + s for s in summary['limitations_zh']], '',
        '源终止方式与合并类别分别保存，可在`termination_cross.csv`核对；不得把fall/stuck与方向错误重复计数。', '',
        '## 文件', '',
        '- `merged450.csv`：全部任务、原生成绩、互斥合并类别、原标签/理由/证据与来源。',
        '- `failures253.csv`：失败子集。',
        '- `category_summary.csv`、`mapping_counts.csv`：类别统计及每个原始子类的映射。',
        '- `scene_summary.csv`、`termination_cross.csv`：21场景及失败终止方式交叉统计。',
        '- `summary.json`、`manifest.json`、`validation.json`：汇总、版本/输入哈希和检查。',
        '- 输出目录保留`failure_distribution.png/.pdf`与分析源码快照。', '',
        '## 命令与版本', '',
        '```bash',
        'backbone/streamvln/.venv/bin/python -B scripts/analyze_pooled450_failures.py \\',
        '  --output outputs/checkpoint_review/pooled450_v001/run_20261117_01 \\',
        '  --record experiments/crossing_analysis/pooled450_v001/run_20261117_01',
        '```', '',
        '本次仅CPU离线合并。实际Git HEAD、工作区状态、脚本及输入哈希见manifest；不替换历史运行版本。原结果无改动，无新API、模型或仿真调用，未生成HTML。', '',
    ]
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Use a new output directory')
    require(not (args.record / 'summary.json').exists(), 'Do not overwrite an existing result')
    hashes = {name: sha(path) for name, path in SOURCES.items()}
    rows = build_rows()
    summary, cats, scenes, terms, mappings = summarize(rows)
    args.output.mkdir(parents=True)
    args.record.mkdir(parents=True, exist_ok=True)
    for name, data in [('merged450.csv', rows), ('failures253.csv', [r for r in rows if r['SR'] == 0]),
                       ('category_summary.csv', cats), ('scene_summary.csv', scenes),
                       ('termination_cross.csv', terms), ('mapping_counts.csv', mappings)]:
        write_csv(args.output / name, data)
    plot(args.output, summary)
    write_json(args.output / 'summary.json', summary)
    write_json(args.output / 'mapping.json', {'old': OLD_MAP, 'new': NEW_MAP, 'category_labels': CATEGORIES})
    (args.output / 'README.md').write_text(report(summary), encoding='utf-8')
    shutil.copy2(__file__, args.output / 'analysis_source.py')
    validation = {
        'passed': True, 'unique_ids': 450, 'scenes': 21, 'seed': 2,
        'successes': 197, 'failures': 253, 'per_case_reviews': 207,
        'official_termination_only': 46, 'cohort_overlap': 0,
        'native_metric_crosschecks': True, 'all_failures_exactly_one_category': True,
        'source_hashes_unchanged': all(sha(path) == hashes[name] for name, path in SOURCES.items()),
        'source_scores_modified': False, 'navigation_started': False,
    }
    require(validation['source_hashes_unchanged'], 'Input changed during analysis')
    write_json(args.output / 'validation.json', validation)
    manifest = {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'analysis_git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'workspace_status': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines(),
        'analysis_source_sha256': sha(Path(__file__)),
        'inputs': {name: {'path': str(path.relative_to(ROOT)), 'sha256': hashes[name]} for name, path in SOURCES.items()},
        'outputs': {p.name: sha(p) for p in sorted(args.output.iterdir()) if p.is_file()},
        'historical_versions': 'Source-run versions unchanged; this HEAD identifies the aggregation only.',
    }
    write_json(args.output / 'manifest.json', manifest)
    for p in args.output.iterdir():
        if p.suffix in ('.csv', '.json') or p.name == 'README.md':
            shutil.copy2(p, args.record / p.name)
    print(json.dumps({'output': str(args.output), 'record': str(args.record),
                      'summary': summary, 'validation': validation}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
