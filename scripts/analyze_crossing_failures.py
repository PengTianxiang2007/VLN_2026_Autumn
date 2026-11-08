"""Evidence assembly for offline, case-level crossing failure attribution.

Geometry scores below only nominate review locations. Final attribution requires
an explicit per-episode review; proximity or reference-path disagreement alone
is never automatically counted as a crossing-caused failure.
"""
import argparse
import base64
from collections import Counter,defaultdict
import csv
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import textwrap
import zipfile

ROOT=Path(__file__).resolve().parents[1]
CAMPAIGN=ROOT/'outputs/reproduction/streamvln_scene250_5seeds_20261101_v2'
PRIOR=ROOT/'outputs/checkpoint_review/seed2_25_20261103'
OUTPUT=ROOT/'outputs/checkpoint_review/seed2_crossing_attribution_20261103'


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()


def dense_path(points,spacing=.1):
    import numpy as np
    p=np.asarray(points,dtype=float)[:,:2]
    d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    keep=np.r_[True,np.diff(d)>1e-6];p,d=p[keep],d[keep]
    if len(d)<2:return p,d
    along=np.r_[np.arange(0,d[-1],spacing),d[-1]]
    return np.column_stack([np.interp(along,d,p[:,k]) for k in range(2)]),along


def candidates(case,scene):
    import numpy as np
    actual=np.asarray([s['position'][:2] for s in case['steps']],dtype=float)
    ref,arc=dense_path(case['reference_path'])
    distances=np.linalg.norm(actual[:,None,:]-ref[None,:,:],axis=2)
    nearest=distances.argmin(1);off=distances.min(1)
    traveled=np.r_[0,np.cumsum(np.linalg.norm(np.diff(actual,axis=0),axis=1))]
    movement=np.diff(traveled)
    actions=[0 if 'stop'in s['action'] else(s['action'].get('move_by_discrete')or[-1])[0] for s in case['steps']]
    stall=longest=ineffective=forward=0
    for a,d in zip(actions,movement):
        if a==1:
            forward+=1;ineffective+=int(d<.035);stall=stall+1 if d<.035 else 0;longest=max(longest,stall)
        elif a==0:stall=0
    # Segments outside a tolerance nominate divergence; they do not define errors.
    departures=[];inside=off<=.7;i=0
    while i<len(actual):
        if off[i]<=.9:i+=1;continue
        start=i;j=i
        while j+1<len(actual) and off[j+1]>.7:j+=1
        back=start
        while back>0 and off[back]>.6:back-=1
        if traveled[j]-traveled[back]>=.7:
            crossings=sorted(scene['crossings'],key=lambda c:np.linalg.norm(actual[back]-c['position']))
            cross=crossings[0]
            ri=int(nearest[back]);target=min(len(ref)-1,ri+int(1.6/.1))
            dep=dict(frame=int(back),out_frame=int(start),end_frame=int(j),
                     position=actual[back].round(4).tolist(),crossing_id=cross['id'],
                     crossing_distance=round(float(np.linalg.norm(actual[back]-cross['position'])),3),
                     reference_progress_m=round(float(arc[ri]),3),reference_remaining_m=round(float(arc[-1]-arc[ri]),3),
                     excursion_length_m=round(float(traveled[j]-traveled[back]),3),
                     max_distance_to_reference=round(float(off[start:j+1].max()),3),
                     recovered_to_reference=bool(j<len(actual)-1),
                     expected_point=ref[target].round(4).tolist(),actual_point=actual[min(j,back+15)].round(4).tolist())
            departures.append(dep)
        i=j+1
    # Also expose encounters when the actual path stayed near the reference but
    # traversed it backwards or stopped before a required branch.
    encounters=[]
    for c in scene['crossings']:
        d=np.linalg.norm(actual-c['position'],axis=1)
        frame=int(d.argmin())
        if d[frame]<1.6:
            encounters.append(dict(crossing_id=c['id'],frame=frame,distance_m=round(float(d[frame]),3),
                                   reference_distance_m=round(float(np.linalg.norm(ref-c['position'],axis=1).min()),3)))
    encounters.sort(key=lambda e:e['frame'])
    near=np.flatnonzero(off<=.7)
    case['geometry_review']=dict(departures=departures,encounters=encounters,
        final_distance_to_reference=round(float(off[-1]),3),max_distance_to_reference=round(float(off.max()),3),
        last_near_reference_frame=int(near[-1]) if len(near) else None,
        final_nearest_reference_progress_m=round(float(arc[nearest[-1]]),3),
        reference_length_m=round(float(arc[-1]),3),actual_recorded_length_m=round(float(traveled[-1]),3),
        min_recorded_goal_distance_m=round(float(np.linalg.norm(actual-ref[-1],axis=1).min()),3),
        ineffective_forward_fraction=round(ineffective/max(forward,1),4),longest_ineffective_forward_run=longest,
        raw_distances_to_reference=off.round(3).tolist(),nearest_reference_arc_m=arc[nearest].round(3).tolist())
    return case


def prepare(output):
    import numpy as np
    source=CAMPAIGN/'visualization'
    index=source/'index.jsonl'
    rows=[json.loads(x) for x in index.read_text().splitlines() if x.strip()]
    rows=sorted([r for r in rows if r['seed']==2],key=lambda r:(r['scene'],r['episode_id']))
    assert len(rows)==len({r['episode_id'] for r in rows})==250
    with(CAMPAIGN/'episodes.csv').open()as f:
        official={r['episode_id']:r for r in csv.DictReader(f) if int(r['run_seed'])==2}
    prior=json.loads((PRIOR/'review_data.json').read_text())
    scenes=prior['scenes'];cases=[];review_number=0
    for number,row in enumerate(rows,1):
        c=json.loads((source/row['detail']).read_text());c.pop('directory',None)
        steps=[json.loads(x) for x in (source/row['steps']).read_text().splitlines() if x.strip()]
        assert c['status']=='complete' and len(steps)==c['frames']
        assert [s['frame'] for s in steps]==list(range(len(steps)))
        score=official[c['episode_id']]
        assert score['fail_reason']==c['fail_reason']
        for a,b in [('SR','success'),('NE','NE'),('OS','osr'),('TL','TL'),('SPL','spl')]:
            assert math.isclose(float(score[a]),float(c['metrics'][b]),abs_tol=1e-6)
        normal_failure=c['metrics']['success']==0 and c['fail_reason']=='not_reach_goal'
        if normal_failure:review_number+=1
        c.update(number=number,review_number=review_number if normal_failure else None,steps=steps,
                 normal_failure=normal_failure,source_case=str(source/row['detail']),source_steps=str(source/row['steps']),
                 source_video=str(source/row['video']),source_case_sha256=digest(source/row['detail']),
                 source_steps_sha256=digest(source/row['steps']),video=f'videos/{c["episode_id"]}.mp4')
        candidates(c,scenes[c['scene']]);cases.append(c)
    assert review_number==105
    data=dict(schema=1,created_at=datetime.now(timezone.utc).isoformat(),seed=2,scenes=scenes,cases=cases,
              source_index_sha256=digest(index),source_scores_sha256=digest(CAMPAIGN/'episodes.csv'),
              prior_sha256=digest(PRIOR/'review_data.json'),
              denominators=dict(all_tasks=250,official_successes=99,official_failures=151,
                                normal_stop_failures=105,abnormal_failures=46,abnormal_successes=8),
              protocol='Offline evidence review; no navigation reruns. Reference geometry only nominates events. Final attribution comes from per-case instruction/path/observation review, with uncertain cases separate.')
    write_json(output/'evidence.json',data)
    summaries=[]
    for c in cases:
        if not c['normal_failure']:continue
        g=c['geometry_review']
        summaries.append(dict(id=c['episode_id'],review_number=c['review_number'],scene=c['scene'],instruction=c['instruction'],
            frames=c['frames'],NE=c['metrics']['NE'],OS=c['metrics']['osr'],TL=c['metrics']['TL'],
            **{k:v for k,v in g.items() if k not in ['raw_distances_to_reference','nearest_reference_arc_m']}))
    write_json(output/'review_queue.json',summaries)
    print(json.dumps(dict(cases=len(cases),normal_failures=review_number,denominators=data['denominators'])),flush=True)


def fonts(size):
    from PIL import ImageFont
    return ImageFont.truetype(str(ROOT/'.runtime/isaac45/kit/resources/fonts/NVIDIASans_Rg.ttf'),size)


def map_panel(case,scene,size=570):
    import numpy as np
    from PIL import Image,ImageDraw
    image=Image.open(PRIOR/'scenes'/case['scene']/'floorplan.png').convert('RGB')
    scale=min(size/image.width,size/image.height)
    image=image.resize((round(image.width*scale),round(image.height*scale)))
    out=Image.new('RGB',(size,size+65),'#f7f9fb');offset=((size-image.width)//2,40+(size-image.height)//2)
    out.paste(image,offset);draw=ImageDraw.Draw(out)
    def xy(p):return((p[0]-scene['low'][0])/scene['resolution']*scale+offset[0],(scene['high'][1]-p[1])/scene['resolution']*scale+offset[1])
    rp=[xy(p)for p in case['reference_path']];ap=[xy(s['position'])for s in case['steps']]
    if len(rp)>1:draw.line(rp,fill='#14815d',width=4)
    if len(ap)>1:draw.line(ap,fill='#2079d4',width=3)
    for i in range(0,len(ap),max(10,len(ap)//12)):
        x,y=ap[i];draw.ellipse((x-2,y-2,x+2,y+2),fill='#2079d4');draw.text((x+3,y+2),str(i),font=fonts(11),fill='#14558f',stroke_width=1,stroke_fill='white')
    for c in scene['crossings']:
        x,y=xy(c['position']);draw.ellipse((x-4,y-4,x+4,y+4),outline='#d67923',width=2)
        draw.text((x+4,y-13),c['id'],font=fonts(13),fill='#a55416',stroke_width=1,stroke_fill='white')
    x,y=ap[0];draw.ellipse((x-5,y-5,x+5,y+5),fill='white',outline='#2079d4',width=2);draw.text((x+6,y),'S',font=fonts(17),fill='#1a508d',stroke_width=1,stroke_fill='white')
    x,y=ap[-1];draw.ellipse((x-5,y-5,x+5,y+5),fill='#c74b48');draw.text((x+6,y),'END',font=fonts(14),fill='#a63230',stroke_width=1,stroke_fill='white')
    x,y=rp[-1];draw.rectangle((x-5,y-5,x+5,y+5),fill='#14815d');draw.text((x+6,y),'GOAL',font=fonts(14),fill='#086546',stroke_width=1,stroke_fill='white')
    title=f"F{case['review_number']:03d} {case['episode_id']} | NE {case['metrics']['NE']:.1f} OS {int(case['metrics']['osr'])}"
    draw.text((8,5),title,font=fonts(18),fill='#1c3046')
    g=case['geometry_review'];notes=f"{case['frames']} frames | stall={g['longest_ineffective_forward_run']} | off-ref end={g['final_distance_to_reference']:.1f}m"
    draw.text((8,size+44),notes,font=fonts(14),fill='#596f85')
    return out


def sheets(output):
    from PIL import Image,ImageDraw
    data=json.loads((output/'evidence.json').read_text());groups=defaultdict(list)
    for c in data['cases']:
        if c['normal_failure']:groups[c['scene']].append(c)
    target=output/'review_sheets';target.mkdir(exist_ok=True)
    for scene,cases in groups.items():
        for page in range((len(cases)+3)//4):
            batch=cases[page*4:page*4+4];canvas=Image.new('RGB',(1140,1270),'#edf1f5')
            for i,c in enumerate(batch):canvas.paste(map_panel(c,data['scenes'][scene]),((i%2)*570,(i//2)*635))
            path=target/f'{scene}_{page+1:02d}.jpg';canvas.save(path,quality=92)
            print(path.name,[c['review_number']for c in batch],flush=True)


def frames(output,ids=None):
    import cv2
    from PIL import Image,ImageDraw
    cv2.setNumThreads(1)
    data=json.loads((output/'evidence.json').read_text())
    chosen=[c for c in data['cases']if c['normal_failure'] and(not ids or c['review_number']in ids)]
    target=output/'observation_sheets';target.mkdir(exist_ok=True)
    for c in chosen:
        g=c['geometry_review'];want={0,max(0,c['frames']-2)}
        for event in g['departures'][:3]:
            want.update([max(0,event['frame']-4),event['frame'],min(c['frames']-2,event['out_frame']+5)])
        if len(want)<4:want.update([c['frames']//3,2*c['frames']//3])
        want=sorted(want)
        canvas=Image.new('RGB',(960,280*((len(want)+2)//3)+55),'white');draw=ImageDraw.Draw(canvas)
        draw.text((12,8),f"F{c['review_number']:03d} {c['episode_id']}",font=fonts(24),fill='#162f44')
        cap=cv2.VideoCapture(c['source_video']);assert cap.isOpened()
        for i,frame in enumerate(want):
            cap.set(cv2.CAP_PROP_POS_FRAMES,frame);ok,im=cap.read();assert ok
            image=Image.fromarray(cv2.cvtColor(im[:480,:640],cv2.COLOR_BGR2RGB)).resize((320,240))
            x=(i%3)*320;y=55+(i//3)*280;canvas.paste(image,(x,y))
            pos=c['steps'][frame]['position'];draw.text((x+5,y+242),f"Frame {frame} | XY {pos[0]:.1f},{pos[1]:.1f}",font=fonts(16),fill='#29465e')
        cap.release();canvas.save(target/f"F{c['review_number']:03d}_{c['episode_id']}.jpg",quality=90)
        print('observations',c['review_number'],want,flush=True)


def load_reviews(output):
    reviews=[r for f in sorted((output/'reviews').glob('*.json')) for r in json.loads(f.read_text())]
    assert len(reviews)==105 and len({r['episode_id'] for r in reviews})==105
    return {r['episode_id']:r for r in reviews}


def review_frames(output):
    """Extract observation evidence at manually chosen decision frames, CPU only."""
    import cv2
    from PIL import Image,ImageDraw
    cv2.setNumThreads(1)
    data=json.loads((output/'evidence.json').read_text());reviews=load_reviews(output)
    target=output/'review_frames';target.mkdir(exist_ok=True)
    sheets_dir=output/'decision_sheets';sheets_dir.mkdir(exist_ok=True)
    panels=[];manifest={}
    for c in data['cases']:
        if not c['normal_failure']:continue
        r=reviews[c['episode_id']];n=c['frames'];anchor=r['frame']
        want=sorted({0,n-2,n//2} if anchor is None else {0,max(0,anchor-4),anchor,min(n-2,anchor+10),n-2})
        cap=cv2.VideoCapture(c['source_video']);assert cap.isOpened()
        images={}
        for f in want:
            cap.set(cv2.CAP_PROP_POS_FRAMES,f);ok,im=cap.read();assert ok
            rgb=Image.fromarray(cv2.cvtColor(im[:480,:640],cv2.COLOR_BGR2RGB))
            path=target/f'{c["episode_id"]}_f{f:04d}.jpg';rgb.resize((480,360)).save(path,quality=80)
            images[f]=rgb.resize((320,240))
        cap.release();manifest[c['episode_id']]=want
        if anchor is not None:
            panel=Image.new('RGB',(960,285),'white');draw=ImageDraw.Draw(panel)
            draw.text((8,3),f'F{c["review_number"]:03d} {c["episode_id"]} | {r["status"]} {r["crossing_id"]}',font=fonts(18),fill='#173149')
            selected=[max(0,anchor-4),min(n-2,anchor+10),n-2]
            for i,f in enumerate(selected):
                panel.paste(images[f],(i*320,27));draw.text((i*320+6,268),f'frame {f}',font=fonts(14),fill='#23455b')
            panels.append(panel)
    for i in range(0,len(panels),4):
        sheet=Image.new('RGB',(960,1140),'#eaf0f3')
        for j,panel in enumerate(panels[i:i+4]):sheet.paste(panel,(0,j*285))
        path=sheets_dir/f'page_{i//4+1:02d}.jpg';sheet.save(path,quality=90);print(path.name,flush=True)
    write_json(output/'frame_manifest.json',manifest)


def short_segment(steps,frame,length=1.2):
    """A bounded arc-length overlay, never the entire remaining trajectory."""
    points=[list(steps[frame]['position'][:2])];traveled=0.;end=frame
    for i in range(frame+1,len(steps)):
        p=list(steps[i]['position'][:2]);last=points[-1]
        d=math.dist(last,p)
        if d<1e-7:continue
        remain=length-traveled
        if d>=remain:
            points.append([last[k]+(p[k]-last[k])*remain/d for k in range(2)])
            traveled=length;end=i;break
        points.append(p);traveled+=d;end=i
    return dict(start_frame=frame,end_frame=end,length_m=round(traveled,6),points=points)


def build_report(output):
    data=json.loads((output/'evidence.json').read_text());reviews=load_reviews(output)
    manifest=json.loads((output/'frame_manifest.json').read_text())
    assert set(reviews)=={c['episode_id'] for c in data['cases'] if c['normal_failure']}
    video_dir=output/'videos';video_dir.mkdir(exist_ok=True)
    scenes=data['scenes'];cases=[];rows=[];source_rows=[]
    for c in data['cases']:
        cid=c['episode_id'];review=reviews.get(cid)
        if review:
            review=dict(review);review.setdefault('subtype','wrong_branch' if review['status']=='crossing' else 'mixed_evidence')
            review['highlight']=None
            if review['crossing_id']:
                cross=next(x for x in scenes[c['scene']]['crossings'] if x['id']==review['crossing_id'])
                assert 0<=review['frame']<c['frames']
                review['crossing_distance_m']=round(math.dist(c['steps'][review['frame']]['position'][:2],cross['position']),4)
            if review['status']=='crossing':
                assert review['rgb_reviewed'] and review['crossing_id']
                review['highlight']=short_segment(c['steps'],review['frame'])
                assert .1<review['highlight']['length_m']<=1.20001
            snapshots=[]
            for f in manifest[cid]:
                path=output/'review_frames'/f'{cid}_f{f:04d}.jpg'
                snapshots.append(dict(frame=f,src='data:image/jpeg;base64,'+base64.b64encode(path.read_bytes()).decode()))
            video=c['video'];dest=output/video
            if not dest.exists():shutil.copy2(c['source_video'],dest)
            assert dest.stat().st_size==Path(c['source_video']).stat().st_size
            review['review_level']='instruction_full_trajectory_geometry_and_keyframes' if review['rgb_reviewed'] else 'instruction_full_trajectory_geometry'
        else:
            success=bool(c['metrics']['success'])
            review=dict(status='success' if success else 'excluded',crossing_id=None,frame=None,highlight=None,rgb_reviewed=False,
                subtype='official_success' if success else c['fail_reason'],
                rationale='官方 SR=1，保留原始成功标签，不做失败归因。' if success else f'官方失败且以 {c["fail_reason"]} 结束，排除 crossing 主因归类；仍保留在 151 条失败分母中。',
                review_level='official_score_only')
            snapshots=[];video=None
        out={k:c[k] for k in ['number','review_number','seed','scene','episode_id','instruction','reference_path','steps','metrics','fail_reason','frames','actions','fps','normal_failure']}
        out.update(review=review,snapshots=snapshots,video=video);cases.append(out)
        rows.append(dict(number=c['number'],review_number=c['review_number'],scene=c['scene'],episode_id=cid,
            seed=2,SR=c['metrics']['success'],NE=c['metrics']['NE'],OS=c['metrics']['osr'],fail_reason=c['fail_reason'],
            status=review['status'],crossing_id=review['crossing_id'],decision_frame=review['frame'],
            highlight_end_frame=review['highlight']['end_frame'] if review['highlight'] else None,
            highlight_length_m=review['highlight']['length_m'] if review['highlight'] else None,
            expected=review.get('expected',''),actual=review.get('actual',''),rationale=review['rationale'],
            subtype=review['subtype'],rgb_reviewed=review['rgb_reviewed']))
        source_rows.append({k:c[k] for k in ['episode_id','source_case','source_steps','source_video','source_case_sha256','source_steps_sha256']})
    counts=Counter(c['review']['status'] for c in cases)
    summary={**data['denominators'],**counts,
        'pct_all_tasks':round(100*counts['crossing']/250,6),
        'pct_official_failures':round(100*counts['crossing']/151,6),
        'pct_normal_stop_failures':round(100*counts['crossing']/105,6),
        'attribution_scope':'Offline assisted evidence attribution; not independent human gold labels or intervention-confirmed causal effects.',
        'excluded_failure_reasons':dict(Counter(c['fail_reason'] for c in cases if c['review']['status']=='excluded')),
        'rgb_decision_cases_reviewed':sum(bool(c['review']['rgb_reviewed'])for c in cases)}
    assert sum(counts.values())==250 and counts['success']==99 and counts['excluded']==46
    assert sum(counts[k]for k in ['crossing','uncertain','other'])==105
    scene_summary=[]
    for sid in scenes:
        cs=[c for c in cases if c['scene']==sid];cc=Counter(c['review']['status'] for c in cs)
        scene_summary.append(dict(scene=sid,all_tasks=len(cs),official_failures=sum(not c['metrics']['success']for c in cs),
            normal_stop_failures=sum(c['normal_failure']for c in cs),**{s:cc[s]for s in ['crossing','uncertain','other','success','excluded']}))
    ordered_reviews=[reviews[c['episode_id']] for c in cases if c['normal_failure']]
    write_json(output/'attribution_reviews.json',ordered_reviews)
    report=dict(schema=1,created_at=datetime.now(timezone.utc).isoformat(),seed=2,summary=summary,scene_summary=scene_summary,
        scenes=scenes,cases=cases,example_id='kujiale_0259_55_0',review_sha256=digest(output/'attribution_reviews.json'))
    write_json(output/'summary.json',summary);write_json(output/'scene_summary.json',scene_summary)
    for name,values in [('attribution.csv',rows),('scene_summary.csv',scene_summary)]:
        with (output/name).open('w',encoding='utf-8-sig',newline='')as f:
            w=csv.DictWriter(f,fieldnames=list(values[0]));w.writeheader();w.writerows(values)
    write_json(output/'provenance.json',dict(source_index_sha256=data['source_index_sha256'],
        source_scores_sha256=data['source_scores_sha256'],prior_review_sha256=data['prior_sha256'],
        review_sha256=report['review_sha256'],cases=source_rows))
    template=ROOT/'core/crossing_attribution.html'
    payload=json.dumps(report,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    html=template.read_text().replace('__REPORT_DATA__',payload)
    (output/'index.html').write_text(html)
    text=(f'Seed 2 crossing 错误归因离线审阅\n\n'
        f'全部 250 条；官方成功 99、失败 151。失败中 fall=41、stuck=5，共 46 条排除归因。\n'
        f'105 条正常停止失败：明确 crossing {counts["crossing"]}；待确认 {counts["uncertain"]}；其他原因 {counts["other"]}。\n'
        f'明确归因占全部任务 {summary["pct_all_tasks"]:.2f}%；占全部失败 {summary["pct_official_failures"]:.2f}%；占正常停止失败 {summary["pct_normal_stop_failures"]:.2f}%。\n\n'
        '双击 index.html。地图与关键帧已内嵌，可单独使用；完整视频需保留 videos 文件夹。\n'
        '红色仅为指定分叉帧之后最多 1.2 米的实际轨迹；参考为绿色、实际为蓝色。\n'
        '待确认案例仅用橙色定位，不计明确归因。顶部结果冻结；复核意见可以导出 JSON。\n'
        '105 条均检查指令与完整坐标轨迹；64 条明确/疑似案例另核对 RGB 关键帧，未声称逐帧观看所有视频。\n'
        '全部资料来自已经完成的 seed 2，没有重跑导航。Crossing 复用此前 55 个场景几何初稿，尚非官方金标准。\n'
        '本轮是辅助审阅而非独立双人标注；没有干预实验，不能推断 checkpoint 可以挽回相同比例失败。\n\n'
        'summary.json / scene_summary.csv：统计；attribution.csv：250 条标签与理由；\n'
        'attribution_reviews.json / reviews/：105 条逐例审阅；provenance.json：原始数据哈希；\n'
        'videos/：105 条正常停止失败原始完整录像；source/：生成代码与 HTML 模板；validation*.json：检查记录。\n')
    (output/'README.txt').write_text(text)
    source=output/'source';source.mkdir(exist_ok=True)
    shutil.copy2(Path(__file__),source/Path(__file__).name);shutil.copy2(template,source/template.name)
    for name in ['check_crossing_report.cjs','validate_crossing_attribution.py']:
        shutil.copy2(ROOT/'scripts'/name,source/name)
    print(json.dumps(summary,ensure_ascii=False),flush=True)
    print('HTML MiB',round((output/'index.html').stat().st_size/2**20,2),flush=True)


def package_report(output):
    archive=output/(output.name+'.zip')
    for name in ['validation.json','validation_ui.json']:
        assert json.loads((output/name).read_text())['passed'],name
    files=[output/'index.html',output/'README.txt']
    files += [output/n for n in ['overview.png','example_map.svg'] if(output/n).exists()]
    files+=list(output.glob('*.csv'))
    files += [output/n for n in ['summary.json','scene_summary.json','attribution_reviews.json','provenance.json','validation.json','validation_ui.json','frame_manifest.json'] if(output/n).exists()]
    for directory in ['reviews','source','videos']:
        files.extend(sorted((output/directory).glob('*')))
    write_json(output/'file_manifest.json',{str(f.relative_to(output)):dict(bytes=f.stat().st_size,sha256=digest(f))for f in files})
    files.append(output/'file_manifest.json')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=5)as z:
        for f in files:
            z.write(f,str(Path(output.name)/f.relative_to(output)),compress_type=zipfile.ZIP_STORED if f.suffix=='.mp4' else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(archive)as z:assert z.testzip()is None
    print('ZIP MiB',round(archive.stat().st_size/2**20,2),'files',len(files),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','sheets','frames','review-frames','build','package']);p.add_argument('--output',type=Path,default=OUTPUT);p.add_argument('--ids',nargs='*',type=int)
    a=p.parse_args()
    if a.command=='prepare':prepare(a.output)
    elif a.command=='sheets':sheets(a.output)
    elif a.command=='frames':frames(a.output,a.ids)
    elif a.command=='review-frames':review_frames(a.output)
    elif a.command=='build':build_report(a.output)
    elif a.command=='package':package_report(a.output)


if __name__=='__main__':main()
