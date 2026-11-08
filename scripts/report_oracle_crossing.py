"""Build a reviewable report from completed/control and live Oracle artifacts."""
import base64
import argparse
import csv
import hashlib
import html
import json
import math
from pathlib import Path
import shutil
import subprocess
import zipfile
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.oracle_crossing import reference_distance
OUT=ROOT/'outputs/oracle_crossing/seed2_10_multi_20261103'


def uri(path):
    path=Path(path)
    if not path.exists():return None
    mime='image/png' if path.suffix=='.png' else 'image/jpeg'
    return 'data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()


def load_index(arm):
    f=OUT/f'visualization_{arm}/index.jsonl'
    rows=[json.loads(l)for l in f.read_text().splitlines()] if f.exists() else []
    return {r['episode_id']:r for r in rows if r['status']=='complete'}


def annotate_video(source, target, interventions):
    import cv2
    import imageio_ffmpeg
    cv2.setNumThreads(1)
    cap=cv2.VideoCapture(str(source));assert cap.isOpened()
    width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT));fps=cap.get(cv2.CAP_PROP_FPS)
    temporary=target.with_name(target.stem+'.annotating.mp4')
    cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-nostdin','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{width}x{height}','-r',str(fps),'-i','pipe:0','-an','-c:v','libx264','-preset','veryfast','-crf','23','-threads','1','-pix_fmt','yuv420p','-movflags','+faststart',str(temporary)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    frames=0
    try:
        while True:
            ok,frame=cap.read()
            if not ok:break
            elapsed=[iv for iv in interventions if frames>=iv['action_index']]
            if elapsed:
                cv2.rectangle(frame,(0,0),(min(640,width)-1,32),(100,15,75),-1)
                cv2.putText(frame,f'ORACLE #{len(elapsed)} at step {elapsed[-1]["action_index"]} | memory kept',(8,23),cv2.FONT_HERSHEY_SIMPLEX,.55,(255,255,255),1,cv2.LINE_AA)
            proc.stdin.write(frame.tobytes());frames+=1
        proc.stdin.close();assert proc.wait(timeout=60)==0
    finally:
        cap.release()
        if proc.poll() is None:proc.kill();proc.wait()
    temporary.replace(target)
    target.with_suffix('.annotation.json').write_text(json.dumps(dict(frames=frames,fps=fps,intervention_frames=[iv['action_index']for iv in interventions],source=str(source))))


def build():
    m=json.loads((OUT/'manifest.json').read_text());report=OUT/'report';report.mkdir(exist_ok=True)
    notes_path=OUT/'analysis_notes.json';notes=json.loads(notes_path.read_text()) if notes_path.exists() else {}
    (report/'videos').mkdir(exist_ok=True)
    indexes={arm:load_index(arm)for arm in ['control','oracle']}
    data=[]
    for c in m['cases']:
        scene=ROOT/'outputs/checkpoint_review/seed2_25_20261103/scenes'/c['scene']
        g=json.loads((scene/'geometry.json').read_text())
        d=dict(episode_id=c['episode_id'],scene=c['scene'],instruction=c['instruction'],crossing_id=c['crossing_id'],
               crossing=c['crossing']['position'],target=c['target_xy'],target_yaw=c['target_yaw_rad'],
               reference=c['reference_path'],floorplan=uri(scene/'floorplan.png'),geometry=g,
               original_SR=c['original_metrics']['success'],failed_seeds=c['failed_seeds'],
               same_branch_confirmed_seeds=c['same_branch_confirmed_seeds'],targets=c.get('targets',[]),analysis=notes.get(c['episode_id'],{}),
               deviation_threshold_m=m.get('deviation_threshold_m'),max_reference_distance_m=None)
        for arm in ['control','oracle']:
            row=indexes[arm].get(c['episode_id'])
            if row:
                root=OUT/f'visualization_{arm}';details=json.loads((root/row['detail']).read_text())
                video=report/'videos'/f'{c["episode_id"]}_{arm}.mp4'
                if not video.exists():shutil.copy2(root/row['video'],video)
                d[arm]=dict(metrics=row['metrics'],fail_reason=row['fail_reason'],path=details['pred_path'],video='videos/'+video.name,frames=row['frames'])
            else:d[arm]=None
        attempts=sorted((OUT/'oracle_records'/c['episode_id']).glob('attempt_*'))
        completed=[p for p in attempts if (p/'result.json').exists()]
        a=completed[-1] if completed else attempts[-1] if attempts else None
        d['intervention']=None;d['interventions']=[];d['oracle_observations']=[];d['decisions']=[]
        if a:
            f=a/'observations.jsonl'
            if f.exists():d['oracle_observations']=[json.loads(l)for l in f.read_text().splitlines()]
            f=a/'interventions.json';single=a/'intervention.json'
            ivs=json.loads(f.read_text()) if f.exists() else [json.loads(single.read_text())] if single.exists() else []
            for iv in ivs:
                rp=Path(iv['request_directory'])
                proof=json.loads((rp/'memory_proof.json').read_text())
                assert proof['equal'] and proof['before']['sha256']==proof['after']['sha256']
                iv.update(before_image=uri(rp/'before.png'),after_image=uri(rp/'after.png'),
                          memory_sha256=proof['before']['sha256'],history_images=proof['before']['history_images'],
                          before_NE=math.dist(iv['before_position'][:2],c['reference_path'][-1][:2]),
                          handover_NE=math.dist(iv['after_position'][:2],c['reference_path'][-1][:2]))
                iv['trigger_reference_distance_m']=reference_distance(iv['before_position'],c['reference_path'])
                d['interventions'].append(iv)
            d['intervention']=d['interventions'][0] if d['interventions'] else None
            if d['oracle'] and d['interventions']:
                target=report/d['oracle']['video']
                if not target.with_suffix('.annotation.json').exists():
                    annotate_video(OUT/'visualization_oracle'/indexes['oracle'][c['episode_id']]['video'],target,d['interventions'])
            for f in sorted(a.glob('*/response.json')):
                response=json.loads(f.read_text());request=json.loads(f.with_name('request.json').read_text())
                d['decisions'].append(dict(action_index=request['action_index'],**response))
            positions=[o['position']for o in d['oracle_observations']]
            if d['oracle']:positions.extend(d['oracle']['path'])
            d['max_reference_distance_m']=max((reference_distance(p,c['reference_path'])for p in positions),default=None)
        data.append(d)
    paired=[d for d in data if d['control'] and d['oracle']]
    ivs=[d for d in data if d['oracle'] and d['intervention']]
    # Official success radius is read from the actual result, never guessed.
    thresholds={}
    for d in data:
        for f in sorted((OUT/'oracle_records'/d['episode_id']).glob('*/result.json')):
            r=json.loads(f.read_text());thresholds[d['episode_id']]=r['metrics'].get('success_distance')
        for iv in d['interventions']:
            threshold=thresholds.get(d['episode_id'])
            iv['success_distance']=threshold
            iv['inside_success_radius_at_handover']=None if threshold is None else iv['handover_NE']<threshold
            iv['inside_success_radius_before_intervention']=None if threshold is None else iv['before_NE']<threshold
    meaningful=[d for d in ivs if all(iv['inside_success_radius_at_handover'] is False for iv in d['interventions'])]
    summary=dict(tasks=10,control_complete=sum(d['control'] is not None for d in data),oracle_complete=sum(d['oracle'] is not None for d in data),
                 control_success=sum(d['control']['metrics']['success']>0 for d in data if d['control']),
                 oracle_success=sum(d['oracle']['metrics']['success']>0 for d in data if d['oracle']),
                 pairs=len(paired),rescued=sum(d['control']['metrics']['success']==0 and d['oracle']['metrics']['success']>0 for d in paired),
                 harmed=sum(d['control']['metrics']['success']>0 and d['oracle']['metrics']['success']==0 for d in paired),
                 interventions=len(ivs),intervened_success=sum(d['oracle']['metrics']['success']>0 for d in ivs),
                 outside_goal_radius_at_handover=len(meaningful),outside_goal_radius_success=sum(d['oracle']['metrics']['success']>0 for d in meaningful))
    summary.update(control_normal_success=sum(d['control']['fail_reason']=='success' and d['control']['metrics']['success']>0 for d in data if d['control']),
                   oracle_normal_success=sum(d['oracle']['fail_reason']=='success' and d['oracle']['metrics']['success']>0 for d in data if d['oracle']),
                   unstable_interventions=sum(not iv['stable'] for d in ivs for iv in d['interventions']),
                   correction_events=sum(len(d['interventions'])for d in ivs),
                   multiple_correction_tasks=sum(len(d['interventions'])>1 for d in ivs),
                   multi_intervention_protocol=m.get('multi_intervention',False))
    for arm in ('control','oracle'):
        summary[arm+'_falls']=sum(d[arm]['fail_reason']=='fall' for d in data if d[arm])
        summary[arm+'_stuck']=sum(d[arm]['fail_reason']=='stuck' for d in data if d[arm])
    summary['rescued_from_normal_stop_failure']=sum(d['control']['fail_reason']=='not_reach_goal' and d['oracle']['fail_reason']=='success' and d['oracle']['metrics']['success']>0 for d in paired)
    clean=[d for d in meaningful if not d['analysis'].get('local_obstacle_contact_during_recovery')]
    summary.update(local_contact_recovery_tasks=sum(bool(d['analysis'].get('local_obstacle_contact_during_recovery'))for d in ivs),
                   outside_goal_radius_without_contact=len(clean),outside_goal_radius_without_contact_success=sum(d['oracle']['metrics']['success']>0 for d in clean),
                   deviation_threshold_m=m.get('deviation_threshold_m'))
    done=[d for d in data if d['oracle']]
    summary.update(unintervened_complete=sum(not d['interventions']for d in done),
                   unintervened_success=sum(not d['interventions'] and d['oracle']['metrics']['success']>0 for d in done),
                   paired_success_after_intervention=sum(bool(d['interventions']) and d['control']['metrics']['success']==0 and d['oracle']['metrics']['success']>0 for d in paired))
    if m.get('deviation_threshold_m') is not None:
        summary['ended_without_reaching_threshold']=sum(d['max_reference_distance_m'] is None or d['max_reference_distance_m']<m['deviation_threshold_m'] for d in done)
        summary['threshold_reached_without_intervention']=sum(not d['interventions'] and d['max_reference_distance_m'] is not None and d['max_reference_distance_m']>=m['deviation_threshold_m'] for d in done)
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (report/'results.json').write_text(json.dumps(dict(summary=summary,cases=data),ensure_ascii=False))
    template=(ROOT/'core/oracle_crossing_review.html').read_text()
    payload=json.dumps(dict(summary=summary,cases=data),ensure_ascii=False).replace('<','\\u003c')
    (report/'index.html').write_text(template.replace('__DATA__',payload))
    shutil.copy2(ROOT/'docs/ORACLE_CROSSING_PILOT.md',report/'README.md')
    with (report/'results.csv').open('w')as f:
        w=csv.DictWriter(f,fieldnames=['episode_id','control_SR','oracle_SR','corrections','handover_NE_all','memory_unchanged','oracle_fail_reason']);w.writeheader()
        for d in data:w.writerow(dict(episode_id=d['episode_id'],control_SR=d['control']['metrics']['success']if d['control']else'',oracle_SR=d['oracle']['metrics']['success']if d['oracle']else'',corrections=len(d['interventions']),handover_NE_all=';'.join(f'{iv["handover_NE"]:.3f}'for iv in d['interventions']),memory_unchanged=all(iv['memory_unchanged']for iv in d['interventions'])if d['interventions']else'',oracle_fail_reason=d['oracle']['fail_reason']if d['oracle']else''))
    if summary['control_complete']==summary['oracle_complete']==10:
        with zipfile.ZipFile(OUT/'oracle_crossing_10_review.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=1)as z:
            for f in report.rglob('*'):
                if f.is_file():z.write(f,str(Path('oracle_crossing_10_review')/f.relative_to(report)))
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--campaign',type=Path,default=OUT)
    OUT=ap.parse_args().campaign.resolve();build()
