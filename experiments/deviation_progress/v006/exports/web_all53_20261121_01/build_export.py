"""Export all 53 archived v006 cases, including validation failures; no model calls."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
SNAPSHOT = ROOT/'outputs/deviation_progress/v006/all53_20261121_01'
SUMMARY = ROOT/'outputs/deviation_progress/v006_pair_route53_20261121_01/v006_all53.json'
ONLINE = ROOT/'outputs/visualization_publishing/qwen_v006_all53_web_20261121_01'


def read(path):
    return json.loads(path.read_text())


def write(name, data):
    (SNAPSHOT/name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def truncated_display(raw):
    # Presentation-only extraction: never repair, validate or submit this answer.
    decoder = json.JSONDecoder()
    result = {}
    for key in ('previous_id','current_id','verdict','segment_summary','reason','instruction_evidence'):
        match = re.search(r'"'+key+r'"\s*:\s*', raw)
        result[key] = decoder.raw_decode(raw[match.end():])[0]
    match = re.search(r'"visual_evidence"\s*:\s*\[\s*', raw)
    result['visual_evidence'] = [decoder.raw_decode(raw[match.end():])[0]]
    translations = {
        'Note: JSON key must be semantic_progress, fixing typo in thought process if any, but outputting correct key below. Actually, the prompt asks for semantic_progress. I will use the correct key.': '注：JSON 键必须是 semantic_progress，如果思考过程中有拼写错误则修正，但在下方输出正确的键。实际上，提示词要求 semantic_progress。我会使用正确的键。',
        'Wait, I am generating the JSON. I will just output the correct key.': '等等，我正在生成 JSON。我只会输出正确的键。',
        'The thought block is just for me. The output is the JSON.': '思考块仅供我自己使用。输出内容是 JSON。',
        'I will ensure the key is semantic_progress.': '我会确保键为 semantic_progress。',
        'I will not include the typo in the final output.': '我不会在最终输出中包含这个拼写错误。',
        'I will just write the JSON.': '我只会写出 JSON。',
        'I will make sure the JSON is valid.': '我会确保 JSON 有效。',
        'I will not include the thought process in the output.': '我不会在输出中包含思考过程。',
        'I will just output the JSON.': '我只会输出 JSON。',
        'I will': '我会',
    }
    comments = [part.strip() for part in raw.split('//')[1:]]
    result['comments'] = dict(zh='\n'.join('// '+translations[part] for part in comments),
                              en='\n'.join('// '+part for part in comments))
    return result


def main():
    rows = read(SUMMARY)
    assert [row['case_number'] for row in rows] == list(range(1,54))
    runs = list(dict.fromkeys(Path(row['source_run']) for row in rows))
    manifests = [read(run/'manifest.json') for run in runs]
    for manifest in manifests[1:]:
        for key in ('settings','prompt_sha256','dataset_manifest_sha256','frozen_nodes_sha256'):
            assert manifest[key] == manifests[0][key]
    anchors, sources, counts = {}, {}, Counter()
    node_sets = {run:read(run/'retained_nodes_and_terminals.json') for run in runs}
    for row in rows:
        run = Path(row['source_run']); label = f"C{row['case_number']:02d}"
        folder = run/'run/cases'/label
        assert read(folder/'result.json')['stop_reason'] in ('first_deviation','all_nodes_reviewed')
        sources[label] = str(folder)
        anchors[row['episode_id']] = node_sets[run][row['episode_id']]
        counts.update(row['outcomes'])
    SNAPSHOT.mkdir(parents=True, exist_ok=False)
    manifest = {key:manifests[0][key] for key in ('version','settings','trajectory_seed','prompt_sha256','dataset_manifest_sha256','frozen_nodes_sha256')}
    manifest.update(partial=False,cases=list(range(1,54)),source_runs=[str(run.relative_to(ROOT)) for run in runs],
                    created_at=datetime.now(timezone.utc).isoformat(),source_manifests=manifests)
    write('manifest.json',manifest)
    write('status.json',dict(phase='complete',included_cases=53,verdicts=dict(counts),model_calls=sum(row['calls'] for row in rows)))
    write('v006_results.json',rows)
    write('case_sources.json',sources)
    write('retained_nodes_and_terminals.json',anchors)
    response = read(Path(sources['C50'])/'S03.response.json')
    raw = response['response']['choices'][0]['message']['content']
    assert response['error']=='ValueError: Incomplete response: length'
    write('display_overrides.json',{'C50/S03':truncated_display(raw)})
    prompts = Path('source/experiments/deviation_progress/v006')
    (SNAPSHOT/prompts).mkdir(parents=True)
    for lang in ('zh','en'):
        shutil.copy2(runs[0]/prompts/f'prompt_{lang}.txt',SNAPSHOT/prompts)
    write('export_source.json',dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__),ROOT/'scripts/export_deviation_progress_v004_replay.py',ROOT/'core/deviation_progress_v004_review.js')}))
    subprocess.run([sys.executable,'-B',str(ROOT/'scripts/export_deviation_progress_v004_replay.py'),
        '--run',str(SNAPSHOT),
        '--template',str(ROOT/'outputs/deviation_progress/v003/run_20261118_01_qwen27b/exports/terminal53_01/index.html'),
        '--output',str(SNAPSHOT/'exports/web_all53_20261121_01'),
        '--online',str(ONLINE),'--compact-inputs'],cwd=ROOT,check=True)


if __name__=='__main__':
    main()
