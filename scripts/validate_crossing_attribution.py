"""Check a report against the original scores, recordings and prior map annotations."""
import base64
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys

import cv2
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def main():
    output=Path(sys.argv[1]);html=(output/'index.html').read_text()
    d=json.loads(re.search(r'<script id="report-data" type="application/json">(.*?)</script>',html,re.S)[1])
    p=json.loads((output/'provenance.json').read_text());orig={c['episode_id']:c for c in p['cases']}
    campaign=ROOT/'outputs/reproduction/streamvln_scene250_5seeds_20261101_v2'
    with(campaign/'episodes.csv').open()as f:official={c['episode_id']:c for c in csv.DictReader(f)if int(c['run_seed'])==2}
    assert sha(campaign/'episodes.csv')==p['source_scores_sha256']
    assert sha(campaign/'visualization/index.jsonl')==p['source_index_sha256']
    prior_path=ROOT/'outputs/checkpoint_review/seed2_25_20261103/review_data.json'
    assert sha(prior_path)==p['prior_review_sha256']
    prior=json.loads(prior_path.read_text())
    assert d['scenes']==prior['scenes']
    assert d['review_sha256']==sha(output/'attribution_reviews.json')
    assert len(d['cases'])==len({c['episode_id']for c in d['cases']})==250
    assert {c['episode_id']for c in d['cases']}==set(official)
    counts={};snapshots=0;videos=0;min_z=math.inf;max_red=0
    cv2.setNumThreads(1)
    for c in d['cases']:
        oid=c['episode_id'];o=official[oid];src=orig[oid];r=c['review'];counts[r['status']]=counts.get(r['status'],0)+1
        assert int(c['metrics']['success'])==int(float(o['SR'])) and c['fail_reason']==o['fail_reason']
        assert math.isclose(c['metrics']['NE'],float(o['NE']),abs_tol=1e-6)
        assert sha(src['source_case'])==src['source_case_sha256']
        assert sha(src['source_steps'])==src['source_steps_sha256']
        steps=[json.loads(x)for x in Path(src['source_steps']).read_text().splitlines()if x.strip()]
        assert c['steps']==steps and len(steps)==c['frames']
        assert [s['frame']for s in steps]==list(range(c['frames']))
        if r['status']=='crossing':
            assert c['metrics']['success']==0 and c['fail_reason']=='not_reach_goal' and r['rgb_reviewed']
            assert r['crossing_id']in{x['id']for x in d['scenes'][c['scene']]['crossings']}
            h=r['highlight'];assert h['start_frame']==r['frame'];assert h['points'][0]==steps[r['frame']]['position'][:2]
            length=sum(math.dist(a,b)for a,b in zip(h['points'],h['points'][1:]));assert 0<length<=1.200001
            assert math.isclose(length,h['length_m'],abs_tol=1e-5);max_red=max(max_red,length)
            min_z=min(min_z,min(s['position'][2]for s in steps));assert all(s['position'][2]>.35 for s in steps)
            assert 0<=h['start_frame']<h['end_frame']<len(steps)
        else:assert r['highlight']is None
        for s in c['snapshots']:
            assert 0<=s['frame']<c['frames'];im=Image.open(io.BytesIO(base64.b64decode(s['src'].split(',',1)[1])));assert im.size==(480,360);im.verify();snapshots+=1
        if c['video']:
            video=output/c['video'];assert video.is_file();assert sha(video)==sha(src['source_video'])
            cap=cv2.VideoCapture(str(video));assert cap.isOpened()
            assert round(cap.get(cv2.CAP_PROP_FRAME_COUNT))==c['frames']
            assert math.isclose(cap.get(cv2.CAP_PROP_FPS),c['fps'],abs_tol=1e-5)
            assert (round(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),round(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))==(960,640)
            cap.set(cv2.CAP_PROP_POS_FRAMES,c['frames']-1);ok,frame=cap.read();assert ok and frame.shape[:2]==(640,960);cap.release();videos+=1
    s=d['summary'];assert s==json.loads((output/'summary.json').read_text())
    for k,n in counts.items():assert s[k]==n
    assert s['all_tasks']==sum(counts.values())==250 and s['official_failures']==151
    assert s['normal_stop_failures']==sum(counts[k]for k in ['crossing','other','uncertain'])==105
    for key,den in [('pct_all_tasks',250),('pct_official_failures',151),('pct_normal_stop_failures',105)]:assert math.isclose(s[key],100*counts['crossing']/den,abs_tol=1e-6)
    assert sum(x['all_tasks']for x in d['scene_summary'])==250
    for field in ['crossing','uncertain','other','success','excluded']:assert sum(x[field]for x in d['scene_summary'])==counts[field]
    with(output/'attribution.csv').open(encoding='utf-8-sig')as f:rows=list(csv.DictReader(f))
    assert len(rows)==250 and sum(x['status']=='crossing'for x in rows)==counts['crossing']
    assert not re.search(r'(?:src|href)=["\']https?://',html)
    result=dict(passed=True,original_score_and_case_matches=250,source_step_hash_matches=250,
        prior_crossings_unchanged=55,normal_failure_reviews=105,counts=counts,embedded_snapshots=snapshots,
        source_identical_videos_and_last_frames_verified=videos,maximum_red_length_m=round(max_red,6),
        minimum_confirmed_pose_height_m=round(min_z,6),statistics_and_percentages=True,no_external_resources=True,
        limitation='Offline attribution labels require independent human review; checks verify provenance and artifact consistency, not causal truth.')
    (output/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
