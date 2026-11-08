"""CPU-only full-frame v001 review in the v002 layout; original answers remain frozen."""
import argparse
import base64
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.agent_route_choice import read,write,file_hash,digest,now
from scripts.export_agent_route_choice import check_translation
from scripts.prepare_agent_route_choice import action_name
from scripts.report_agent_route_choice import load_run


def url(raw,mime):return f'data:{mime};base64,'+base64.b64encode(raw).decode()


def main():
    import cv2
    import numpy as np
    cv2.setNumThreads(1)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    prepared=ROOT/'outputs/agent_route_choice/v001/preparation_20261106_04'
    run=ROOT/'outputs/agent_route_choice/v001/run_20261106_01/qwen32b'
    translation_path=ROOT/'experiments/agent_route_choice/v001/run_20261106_01/exports/run_20261106_01/translations_zh.json'
    translation=read(translation_path);cases=load_run(prepared,run)
    if translation['source_run_manifest_sha256']!=file_hash(run/'manifest.json'):raise ValueError('Wrong translation run')
    labels={r['sample_id']:r for r in read(prepared/'evaluation_only.json')['labels']}
    sources={r['sample_id']:r for r in read(prepared/'provenance.json')['sources']}
    protected=[ROOT/'outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_01/agent_route_choice_qwen32b_zh.html',
               ROOT/'outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_02/crossing_branches_choice_zh.html',
               ROOT/'outputs/agent_route_choice/v002/run_20261106_01/exports/run_20261106_01/crossing_v002_qwen27b_zh.html']
    before={str(p.relative_to(ROOT)):file_hash(p) for p in protected}
    write(out/'status.json',dict(phase='extracting_original_video',model_calls=0,created_at=now()))
    images={};maps={};bundle=[];audit=[]
    for c in cases:
        sid=c['sample_id'];source=sources[sid];label=labels[sid];t=translation['cases'][sid];folder=run/'cases'/sid
        if hashlib.sha256(c['instruction'].encode()).hexdigest()!=t['instruction_source_sha256']:raise ValueError('Task translation changed')
        for name in ('steps','video'):
            if file_hash(source[name])!=source[name+'_sha256']:raise ValueError('Recorded source changed: '+sid+' '+name)
        rows=[json.loads(line) for line in Path(source['steps']).read_text().splitlines()]
        if [r['frame'] for r in rows]!=list(range(len(rows))):raise ValueError('Noncontiguous source frames')
        if rows[c['checkpoint_frame']]['position']!=label['checkpoint_position']:raise ValueError('Wrong checkpoint position')
        input_frames={im['frame']:im for im in c['images']};frames=[];verified=[]
        cap=cv2.VideoCapture(source['video'])
        try:
            if not cap.isOpened() or [int(cap.get(3)),int(cap.get(4))]!=[960,640]:raise ValueError('Unexpected source-video dimensions')
            if int(cap.get(cv2.CAP_PROP_FRAME_COUNT))!=len(rows):raise ValueError('Video and position count mismatch')
            for row in rows:
                ok,composite=cap.read()
                if not ok:raise ValueError('Video ended before recorded frame')
                crop=composite[:480,:640].copy();frame=row['frame']
                if frame in input_frames:
                    im=input_frames[frame];raw=(prepared/im['path']).read_bytes();key=hashlib.sha256(raw).hexdigest()
                    if key!=im['sha256'] or not np.array_equal(crop,cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_COLOR)):
                        raise ValueError('Original model input differs from this exact video frame')
                    ext='png';mime='image/png';verified.append(frame)
                else:
                    ok,encoded=cv2.imencode('.jpg',crop,[cv2.IMWRITE_JPEG_QUALITY,88])
                    if not ok:raise ValueError('JPEG encoding failed')
                    raw=encoded.tobytes();key=hashlib.sha256(raw).hexdigest();ext='jpg';mime='image/jpeg'
                dest=out/'frames'/sid/f'F{frame:04d}.{ext}';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
                images.setdefault(key,url(raw,mime))
                frames.append(dict(frame=frame,position=row['position'],image_key=key,path=str(dest.relative_to(out)),
                                   action='TERMINAL' if row['terminal'] else action_name(row),terminal=row['terminal'],rgb_reused=row['rgb_reused']))
            if cap.read()[0]:raise ValueError('Extra video frame without position metadata')
        finally:cap.release()
        calls={};request_checks=[]
        cp=input_frames[c['checkpoint_frame']]
        for stage in (1,2):
            response=folder/f'call{stage}_response.json';raw=read(response);answer=json.loads(raw['content']);entry=t['calls'][str(stage)]
            if entry['source_response_sha256']!=file_hash(response):raise ValueError('Response translation source mismatch')
            check_translation(answer,entry['answer_zh'],stage)
            calls[stage]=dict(answer=answer,answer_zh=entry['answer_zh'],response_sha256=file_hash(response),validated=(folder/f'call{stage}_answer.json').exists())
            request=read(folder/f'call{stage}_request.json');msgs=request['messages_image_hash_preview'];meta=json.loads(msgs[1]['content'][0]['text'])
            if meta['current_view_id']!=cp['id'] or not any(x.get('image_url',{}).get('url')=='PREVIEW_ONLY:image_sha256:'+cp['sha256'] for x in msgs[1]['content']):
                raise ValueError('Checkpoint differs from actual model input')
            request_checks.append(stage)
            if stage==2:
                if meta['branch_inventory']!=calls[1]['answer'] or request['inventory_sha256']!=digest(calls[1]['answer']):raise ValueError('First-call inventory transfer changed')
        scene=label['scene']
        if scene not in maps:
            base=ROOT/'outputs/checkpoint_review/seed2_25_20261103/scenes'/scene;g=read(base/'geometry.json')
            maps[scene]=dict(geometry={k:g[k] for k in ('low','high','resolution','width','height')},image=url((base/'floorplan.png').read_bytes(),'image/png'))
        distance=math.dist(label['checkpoint_position'][:2],label['crossing']['position'][:2])
        bundle.append(dict(c,frames=frames,review=label,instruction_zh=t['instruction_zh'],calls=calls,status=read(folder/'status.json'),
                           crossing_distance_m=distance,inventory_transfer_verified=True))
        row=dict(sample_id=sid,episode_id=label['episode_id'],source=source,replay_frames=len(frames),checkpoint_frame=c['checkpoint_frame'],
                 checkpoint_sha256=cp['sha256'],checkpoint_request_checks=request_checks,model_input_frames_verified=verified,
                 branch_count=len(calls[1]['answer']['branches']),selected_branch_id=calls[2]['answer']['selected_branch_id'],
                 response_sha256={str(k):v['response_sha256'] for k,v in calls.items()})
        audit.append(row);print(json.dumps({k:row[k] for k in ('sample_id','replay_frames','checkpoint_frame','model_input_frames_verified')}),flush=True)
    summary=dict(samples=len(bundle),response_count=20,branch_count=sum(x['branch_count'] for x in audit),
                 valid_samples=sum(c['calls'][2]['validated'] for c in bundle),replay_frames=sum(len(c['frames']) for c in bundle),model_calls=0)
    data=dict(cases=bundle,images=images,maps=maps,summary=summary,run_hash=file_hash(run/'manifest.json'),exported_at=now())
    style_source=ROOT/'core/agent_panorama_choice_page.html';template=ROOT/'core/agent_route_timeline_page.html';script=ROOT/'core/agent_route_timeline_review.js'
    shared_style=style_source.read_text().split('<style>',1)[1].split('</style>',1)[0]
    page=template.read_text().replace('__SHARED_STYLE__',shared_style).replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')).replace('__SCRIPT__',script.read_text())
    from fontTools import subset
    from fontTools.ttLib import TTFont
    cfg=read(ROOT/'core/crossing_visualization_template.json');font=TTFont(cfg['font'],fontNumber=0)
    sub=subset.Subsetter();sub.populate(text=page);sub.subset(font);buf=io.BytesIO();font.save(buf)
    page=page.replace('__FONT__','data:font/ttf;base64,'+base64.b64encode(buf.getvalue()).decode())
    html=out/'crossing_v001_timeline_zh.html';html.write_text(page)
    shutil.copy2(translation_path,out/'translations_zh.json');shutil.copy2(cfg['font_license'],out/'FONT_LICENSE.txt')
    source_hashes={}
    for rel in ['scripts/export_agent_route_timeline.py','core/agent_route_timeline_page.html','core/agent_route_timeline_review.js',
                'core/agent_panorama_choice_page.html','scripts/export_agent_route_choice.py','scripts/prepare_agent_route_choice.py','scripts/report_agent_route_choice.py','core/agent_route_choice.py']:
        dest=out/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dest);source_hashes[rel]=file_hash(dest)
    (out/'workspace_status.txt').write_bytes(subprocess.check_output(['git','status','--short'],cwd=ROOT))
    (out/'workspace_diff.patch').write_bytes(subprocess.check_output(['git','diff','HEAD','--binary'],cwd=ROOT))
    for name,sha in before.items():
        if file_hash(ROOT/name)!=sha:raise ValueError('Previous HTML changed')
    write(out/'export_audit.json',dict(created_at=now(),html_sha256=file_hash(html),html_bytes=html.stat().st_size,summary=summary,cases=audit,
          source_run=str(run),source_run_manifest_sha256=file_hash(run/'manifest.json'),prepared_manifest_sha256=file_hash(prepared/'manifest.json'),
          translation_sha256=file_hash(translation_path),source_hashes=source_hashes,previous_html_sha256=before,
          export_git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
          source_note='Current export source snapshot only; historical model version remains in the original run manifests.',
          unique_images=len(images),maps=len(maps),jpeg_quality=88,original_input_png_unchanged=True))
    write(out/'status.json',dict(phase='exported_pending_browser_check',model_calls=0,summary=summary,finished_at=now()))
    print(json.dumps(dict(html=str(html),mib=html.stat().st_size/1024**2,**summary)),flush=True)


if __name__=='__main__':main()
