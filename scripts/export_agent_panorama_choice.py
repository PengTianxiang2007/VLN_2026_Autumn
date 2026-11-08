"""Export Chinese v002 decisions with actual panoramas, branch cards, and review-only maps."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import file_hash, read, write, digest, now
from core.agent_panorama_choice import verify_prepared


IMMUTABLE = {'id','direction','panorama_view_ids','evidence_ids','incoming','incoming_branch_id','incoming_evidence_ids','coverage',
             'status','wrong_branch_id','wrong_branch_evidence_ids','excluded_branch_ids','selected_branch_id','selected_direction',
             'selected_panorama_view_ids','selection_evidence_ids','confidence'}


def check_translation(original, translated):
    if isinstance(original, dict):
        if not isinstance(translated, dict) or original.keys() != translated.keys(): raise ValueError('Translation fields changed')
        for k, v in original.items():
            if k in IMMUTABLE:
                if translated[k] != v: raise ValueError('Translation changed decision or evidence: ' + k)
            else: check_translation(v, translated[k])
    elif isinstance(original, list):
        if not isinstance(translated, list) or len(original) != len(translated): raise ValueError('Translation array changed')
        for a, b in zip(original, translated): check_translation(a, b)
    elif original is None:
        if translated is not None: raise ValueError('Null translation changed')
    elif isinstance(original, str):
        if not isinstance(translated, str) or (original.strip() and not translated.strip()): raise ValueError('Missing translated text')
    elif original != translated: raise ValueError('Translation scalar changed')


def data_url(path):
    return 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True); p.add_argument('--translations',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--review-audit',type=Path,required=True)
    a=p.parse_args(); run=a.run.resolve(); out=a.output.resolve()
    status=read(run/'status.json'); registration=read(run/'registration.json'); prepared=Path(registration['prepared'])
    review_audit=read(a.review_audit)
    if review_audit['source_registration_sha256'] != file_hash(run/'registration.json'): raise ValueError('Review audit belongs to another run')
    review_cases={r['sample_id']:r for r in review_audit['cases']}
    if status['phase'] not in ('complete_pending_semantic_review','failed'): raise ValueError('Run still active')
    if file_hash(prepared/'manifest.json') != registration['prepared_manifest_sha256']: raise ValueError('Preparation provenance changed')
    cases=verify_prepared(prepared); labels={x['sample_id']:x for x in read(prepared/'evaluation_only.json')['labels']}
    translations=read(a.translations); images={}; maps={}; bundle=[]; audit=[]
    for c in cases:
        sid=c['sample_id']; t=translations['cases'][sid]; folder=run/'cases'/sid
        if t['instruction_source_sha256'] != hashlib.sha256(c['instruction'].encode()).hexdigest(): raise ValueError('Task translation source mismatch')
        calls={}; inventory_transfer=False
        for stage in (1,2):
            rawpath=folder/f'call{stage}_response.json'
            if not rawpath.exists(): continue
            raw=read(rawpath); parsedpath=folder/f'call{stage}_parsed.json'; parsed=read(parsedpath) if parsedpath.exists() else None
            calls[str(stage)]=dict(raw=raw,answer=parsed,source_sha256=file_hash(rawpath))
            if parsed is not None:
                tr=t['calls'][str(stage)]
                if tr['source_response_sha256'] != file_hash(rawpath): raise ValueError('Response translation source mismatch')
                check_translation(parsed,tr['answer_zh'])
        if (folder/'call2_request.json').exists():
            r=read(folder/'call2_request.json'); prev=calls['1']['answer']; meta=json.loads(r['messages_image_hash_preview'][1]['content'][0]['text'])
            inventory_transfer=meta['branch_inventory']==prev and r['inventory_sha256']==digest(prev)
            if not inventory_transfer: raise ValueError('Full inventory transfer mismatch')
        rendered=[]
        for im in c['images']:
            key=im['sha256']; images.setdefault(key,data_url(prepared/im['path'])); rendered.append(dict(im,image_key=key))
        label=labels[sid]; scene=label['scene']
        if scene not in maps:
            base=prepared/'review_maps'/scene; g=read(base/'geometry.json')
            maps[scene]=dict(geometry={k:g[k] for k in ('low','high','resolution','width','height')},image=data_url(base/'floorplan.png'))
        state=read(folder/'status.json') if (folder/'status.json').exists() else dict(phase='not_started',error='本次未获得回答')
        if any(file_hash(folder/name) != sha for name,sha in review_cases[sid]['source_hashes'].items()): raise ValueError('Audited raw response changed')
        bundle.append(dict(c,images=rendered,review=label,translation=t,calls=calls,status=state,review_audit=review_cases[sid],inventory_transfer_verified=inventory_transfer))
        audit.append(dict(sample_id=sid,panoramas=8,history_images=8,branches=len((calls.get('1',{}).get('answer') or {}).get('branches',[])),
                          selected_branch_id=(calls.get('2',{}).get('answer') or {}).get('selected_branch_id'),full_inventory_verified=inventory_transfer))
    data=dict(cases=bundle,images=images,maps=maps,summary=status,review_audit=review_audit,run_hash=file_hash(run/'registration.json'),exported_at=now())
    template=ROOT/'core/agent_panorama_choice_page.html'; script=ROOT/'core/agent_panorama_choice_review.js'
    page=template.read_text().replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')).replace('__SCRIPT__',script.read_text())
    from fontTools import subset
    from fontTools.ttLib import TTFont
    fontcfg=read(ROOT/'core/crossing_visualization_template.json'); font=TTFont(fontcfg['font'],fontNumber=0)
    sub=subset.Subsetter();sub.populate(text=page);sub.subset(font);binary=io.BytesIO();font.save(binary)
    page=page.replace('__FONT__','data:font/ttf;base64,'+base64.b64encode(binary.getvalue()).decode())
    out.mkdir(parents=True,exist_ok=False); html=out/'crossing_v002_qwen27b_zh.html';html.write_text(page)
    shutil.copy2(a.translations,out/'translations_zh.json'); shutil.copy2(fontcfg['font_license'],out/'FONT_LICENSE.txt')
    shutil.copy2(a.review_audit,out/'review_audit.json')
    sources={}
    for rel in ['scripts/export_agent_panorama_choice.py','core/agent_panorama_choice_page.html','core/agent_panorama_choice_review.js']:
        dest=out/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dest);sources[rel]=file_hash(dest)
    write(out/'export_audit.json',dict(created_at=now(),html=str(html),html_sha256=file_hash(html),bytes=html.stat().st_size,
          source_run=str(run),source_registration_sha256=file_hash(run/'registration.json'),translations_sha256=file_hash(a.translations),
          unique_images=len(images),maps=len(maps),cases=audit,source_hashes=sources,semantic_accuracy='pending_review',map_directions='Model discrete headings only; no estimated doorway pixels'))
    print(json.dumps(dict(html=str(html),mib=html.stat().st_size/1024**2,cases=len(bundle),maps=len(maps))))


if __name__=='__main__':main()
