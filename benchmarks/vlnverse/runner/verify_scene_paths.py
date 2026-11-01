"""Verify scene entries and restore known HDR relative paths without changing USD files."""
import json,re,hashlib
from pathlib import Path
ROOT=Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/VLNVerse')
manifest=json.loads((ROOT/'fine_val_unseen_scene_manifest.json').read_text())
canonical=ROOT/'scenes/kujiale_0272/Materials/Textures/limpopo_golf_course_4k.hdr'
assert canonical.is_file()
fixed=[]; missing=[]; checked=[]
for entry in manifest:
    scene=ROOT/'scenes'/entry['folder']
    candidates=[scene/'start_result_navigation.usd',scene/(entry['folder']+'.usda'),scene/(entry['folder'].replace('_fix','')+'.usda')]
    usd=next((p for p in candidates if p.is_file()),None)
    if usd is None:
        missing.append({'scene':entry['folder'],'reason':'entry_missing'}); continue
    # Exported scene entry files are USDA text, even when their extension is .usd.
    text=usd.read_text()
    refs=re.findall(r'@([^@]+)@',text)
    for ref in sorted(set(refs)):
        if ref.startswith('/Game/') or ref.startswith('/Engine/') or '://' in ref: continue
        if ref in ('OmniGlass.mdl','OmniSurface.mdl','OmniPBR.mdl'): continue # Isaac built-in MDL modules.
        if not ref.lower().endswith(('.usd','.usda','.usdc','.png','.jpg','.jpeg','.hdr','.exr','.mdl')): continue
        target=usd.parent/ref
        if target.exists(): continue
        if Path(ref).name=='limpopo_golf_course_4k.hdr' and ref in ('./limpopo_golf_course_4k.hdr','limpopo_golf_course_4k.hdr'):
            local=scene/'Materials/Textures/limpopo_golf_course_4k.hdr'
            source=local if local.is_file() else canonical
            if target.is_symlink(): raise RuntimeError('Preserving conflicting broken symlink: '+str(target))
            target.symlink_to(source)
            fixed.append({'scene':entry['folder'],'path':str(target),'source':str(source)})
        else: missing.append({'scene':entry['folder'],'reference':ref})
    checked.append(entry['folder'])
report={'entry_scenes_checked':checked,'added_hdr_links':fixed,'missing_entry_references':missing,'usd_files_modified':False}
(ROOT/'scene_paths_verified.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'checked':len(checked),'hdr_links':len(fixed),'missing':missing},indent=2))
if missing: raise SystemExit(1)
