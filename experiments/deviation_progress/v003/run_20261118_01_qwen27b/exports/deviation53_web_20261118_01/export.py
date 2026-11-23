"""Extend the terminal-complete replay with the final Qwen results."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path('scripts').resolve()))
from export_route53_deepseek_deviation_comparison import QWEN, RECORD, reviewed, read, write, file_hash, now

audit = Path(__file__).resolve().parent
prior = read(RECORD / 'snapshot.json')
anchors = read(QWEN / 'retained_nodes_and_terminals.json')
assert read(QWEN / 'status.json')['phase'] == 'complete'
files = {}
for kind, info in prior['files'].items():
    src = Path(info['export'])
    assert file_hash(src) == info['sha256']
    html = src.read_text()
    payload = re.search(r'<script id="payload" type="application/json">(.*?)</script>', html, re.S)
    bundle = json.loads(payload[1])
    assert len(bundle['cases']) == 53 and len(bundle['deviationReviews']) == 29
    assert bundle['deepseekReviews'] == prior['layers']['deepseek']
    layers = {}
    digests = {}
    for number, case in enumerate(bundle['cases'], 1):
        eid = case['episode_id']
        layers[eid], digests[eid] = reviewed(QWEN, eid, number, anchors[eid])
        interval = layers[eid]['interval']
        marks = [interval] if interval else []
        if number <= 29:
            assert [{k: m[k] for k in ('from_frame','to_frame')} for m in bundle['deviationReviews'][eid]] == marks
        else:
            bundle['deviationReviews'][eid] = marks
    assert len(layers) == 53 and sum(bool(v['interval']) for v in layers.values()) == 36
    data = json.dumps(bundle, ensure_ascii=False, separators=(',', ':')).replace('</', r'<\/')
    dst = src.with_name('index_qwen53_deepseek29.html')
    with dst.open('x') as f:
        f.write(html[:payload.start(1)] + data + html[payload.end(1):])
    files[kind] = dict(source=str(src), export=str(dst), sha256=file_hash(dst))
write(audit/'snapshot.json', dict(files=files, layers=dict(qwen=layers, deepseek=prior['layers']['deepseek']), qwen_results_sha256=digests, frozen_at=now()))
for i,(eid,v) in enumerate(layers.items(),1):
    if i>=30: print(f'C{i:02}', v['interval'])
