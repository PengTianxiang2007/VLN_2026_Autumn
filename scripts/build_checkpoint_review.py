"""Build a CPU-only, geometry-backed review set from completed StreamVLN runs."""
import argparse
import base64
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / 'outputs/reproduction/streamvln_scene250_5seeds_20261101_v2'
ASSETS = Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/VLNVerse/scenes')
DEFAULT_OUTPUT = ROOT / 'outputs/checkpoint_review/seed2_25_20261103'
ROOM_CATEGORIES = {'livingroom','bedroom','bathroom','kitchen','diningroom','corridor','hallway',
                   'balcony','entrance','studyroom','storageroom','laundryroom'}
GEOMETRY_VERSION = 2


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def select(output):
    import numpy as np
    source = CAMPAIGN / 'visualization'
    rows = [json.loads(x) for x in (source / 'index.jsonl').read_text().splitlines() if x.strip()]
    groups = defaultdict(lambda: defaultdict(list))
    rejected = Counter()
    audits = []
    for row in rows:
        if row['seed'] != 2:
            continue
        outcome = int(row['metrics']['success'])
        if row['status'] != 'complete' or (outcome, row['fail_reason']) not in [(1, 'success'), (0, 'not_reach_goal')]:
            rejected[row['fail_reason']] += 1
            continue
        steps = [json.loads(x) for x in (source / row['steps']).read_text().splitlines() if x.strip()]
        pos = np.asarray([s['position'] for s in steps], dtype=float)
        actions = [0 if 'stop' in s['action'] else (s['action'].get('move_by_discrete') or [-1])[0] for s in steps if not s['terminal']]
        if len(pos) < 20 or not np.isfinite(pos).all() or not actions or actions[-1] != 0:
            rejected['short_or_no_normal_stop'] += 1
            continue
        movement = np.linalg.norm(np.diff(pos[:, :2], axis=0), axis=1)
        # Flag consecutive forward attempts with negligible actual displacement.
        stall, longest = 0, 0
        forward, ineffective = 0, 0
        for action, distance in zip(actions, movement):
            if action == 1:
                forward += 1
                ineffective += int(distance < .035)
                stall = stall + 1 if distance < .035 else 0
                longest = max(longest, stall)
            elif action == 0:
                stall = 0
        extent = float(np.linalg.norm(np.ptp(pos[:, :2], axis=0)))
        audit = dict(episode_id=row['episode_id'], normal_stop=True, frames=len(steps),
                     min_robot_height=float(pos[:, 2].min()), spatial_extent_m=extent,
                     ineffective_forward_fraction=ineffective / max(forward, 1),
                     longest_ineffective_forward_run=longest)
        if pos[:, 2].min() < .55 or extent < 2 or longest >= 6 or ineffective / max(forward, 1) > .25:
            rejected['height_or_motion_screen'] += 1
            audits.append(dict(audit, accepted=False))
            continue
        audits.append(dict(audit, accepted=True))
        groups[row['scene']][outcome].append((row, steps, audit))
    rng = random.Random(20261103)
    scenes = sorted(groups)
    assert len(scenes) == 10 and all(groups[s][0] and groups[s][1] for s in scenes)
    for scene in scenes:
        for outcome in (0, 1):
            groups[scene][outcome].sort(key=lambda x: x[0]['episode_id'])
            rng.shuffle(groups[scene][outcome])
    chosen = []
    for scene in scenes:
        for outcome in (1, 0):
            chosen.append(groups[scene][outcome].pop())
    extras = scenes.copy()
    rng.shuffle(extras)
    for scene, outcome in zip(extras[:5], [0, 1, 0, 1, 0]):
        chosen.append(groups[scene][outcome].pop())
    chosen.sort(key=lambda x: (x[0]['scene'], -x[0]['metrics']['success'], x[0]['episode_id']))
    assert len(chosen) == len({r[0]['episode_id'] for r in chosen}) == 25
    output.mkdir(parents=True, exist_ok=True)
    cases = []
    for number, (row, steps, audit) in enumerate(chosen, 1):
        case = json.loads((source / row['detail']).read_text())
        assert case['status'] == 'complete' and len(steps) == case['frames']
        assert [s['frame'] for s in steps] == list(range(len(steps)))
        case.pop('directory', None)
        case.update(number=number, steps=steps, selection_audit=audit,
                    source_case=str(source / row['detail']), source_steps=str(source / row['steps']),
                    source_video=str(source / row['video']),
                    source_case_sha256=digest(source / row['detail']),
                    source_steps_sha256=digest(source / row['steps']),
                    source_video_sha256=digest(source / row['video']),
                    video=f'videos/{number:02d}_{row["episode_id"]}.mp4')
        cases.append(case)
    manifest = dict(schema=1, created_at=datetime.now(timezone.utc).isoformat(), seed=2,
                    sampling_seed=20261103, count=25,
                    successes=sum(c['metrics']['success'] == 1 for c in cases),
                    failures=sum(c['metrics']['success'] == 0 for c in cases),
                    scene_counts=dict(Counter(c['scene'] for c in cases)),
                    selection='Stratified deterministic random sample: 1 success + 1 normal failure per scene, then 2 successes + 3 failures in 5 shuffled scenes. Development set, not an unbiased benchmark.',
                    rejection_counts=dict(rejected), screening=audits,
                    screening_rule='Normal STOP; >=20 frames; robot z>=0.55m; XY extent>=2m; <6 consecutive ineffective forward attempts; <=25% ineffective forward (<0.035m) actions.',
                    source_index_sha256=digest(source / 'index.jsonl'), cases=cases)
    write_json(output / 'selection.json', manifest)
    print(json.dumps({k: manifest[k] for k in ['count', 'successes', 'failures', 'scene_counts', 'rejection_counts']}, ensure_ascii=False), flush=True)


def import_usd():
    # The launch command supplies the matching Isaac USD shared-library path.
    for directory in (ROOT / '.runtime/isaac45/extscache').glob('omni.usd.libs-*/pxr'):
        sys.path.insert(0, str(directory.parent))
        break
    from pxr import Usd, UsdGeom
    return Usd, UsdGeom


def category(path):
    for part in path.split('/'):
        match = re.fullmatch(r'(.+)_\d{4}', part)
        if match and match.group(1) not in ROOM_CATEGORIES:
            return match.group(1)
    return 'unknown'


def extract(output, scene, resolution=.035):
    import cv2
    import numpy as np
    from scipy import ndimage as ndi
    Usd, UsdGeom = import_usd()
    started = time.time()
    path = ASSETS / scene / 'start_result_navigation.usd'
    stage = Usd.Stage.Open(str(path))
    assert UsdGeom.GetStageUpAxis(stage) == 'Z' and UsdGeom.GetStageMetersPerUnit(stage) == 1
    transforms = UsdGeom.XformCache()
    meshes, floors, objects = [], [], {}
    furniture_categories = {'bed', 'sofa', 'chair', 'stool', 'table', 'dining_table', 'cabinet', 'shelf',
                            'fridge', 'closestool', 'basin', 'bathtub', 'washing_machine', 'oven',
                            'kitchen_cabinet', 'desk', 'stair', 'stairs', 'unknown'}
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        p = str(prim.GetPath())
        cat = category(p)
        if cat not in furniture_categories | {'floor', 'wall', 'door', 'doorsill', 'window', 'pillar', 'column'}:
            continue
        if UsdGeom.Imageable(prim).ComputeVisibility() == UsdGeom.Tokens.invisible:
            continue
        mesh = UsdGeom.Mesh(prim)
        pts = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)
        if not len(pts):
            continue
        mat = np.asarray(transforms.GetLocalToWorldTransform(prim))
        pts = pts @ mat[:3, :3] + mat[3, :3]
        lo, hi = pts.min(0), pts.max(0)
        if hi[2] < -.2 or lo[2] > 2.1:
            continue
        counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get(), dtype=np.int64)
        indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int64)
        if cat == 'floor' and hi[2] >= -.08 and lo[2] <= .2:
            floors.append(pts[:, :2])
        meshes.append((cat, p, pts.astype(np.float32), counts, indices))
        components = p.split('/')
        obj_index = next((i for i, q in enumerate(components) if re.fullmatch(r'.+_\d{4}', q)
                          and q.rsplit('_',1)[0] not in ROOM_CATEGORIES), len(components)-1)
        key = '/'.join(components[:obj_index+1])
        if key not in objects:
            room = next((q for q in components if q.rsplit('_',1)[0] in ROOM_CATEGORIES and q.rsplit('_',1)[-1].isdigit()), '')
            objects[key] = dict(category=cat, room=room, low=lo, high=hi)
        else:
            objects[key]['low'] = np.minimum(objects[key]['low'], lo)
            objects[key]['high'] = np.maximum(objects[key]['high'], hi)
    assert floors, f'No ground floor in {scene}'
    extent = np.concatenate(floors)
    low, high = extent.min(0) - .6, extent.max(0) + .6
    w, h = np.ceil((high-low) / resolution).astype(int) + 1
    assert w < 5000 and h < 5000, (scene, w, h)
    layers = {k: np.zeros((h, w), np.uint8) for k in ['floor', 'wall', 'furniture', 'doors']}
    def pixels(xy):
        return np.rint(np.column_stack([(xy[:, 0]-low[0])/resolution, (high[1]-xy[:, 1])/resolution])).astype(np.int32)
    counters = Counter()
    for cat, p, pts, counts, indices in meshes:
        target = 'floor' if cat in {'floor', 'doorsill'} else ('wall' if cat in {'wall', 'pillar', 'column', 'window'} else ('doors' if cat == 'door' else 'furniture'))
        lower, upper = (-.08, .18) if target == 'floor' else (.18, 1.65)
        offset = 0
        if len(counts) and np.all(counts == 3):
            tris = pts[indices.reshape(-1,3)]
            zmin,zmax=tris[:,:,2].min(1),tris[:,:,2].max(1)
            keep=(zmax>=lower)&(zmin<=upper)
            inside=keep&(zmin>=lower)&(zmax<=upper)
            bulk=tris[inside]
            if len(bulk):
                polygons=pixels(bulk[:,:,:2].reshape(-1,2)).reshape(-1,3,2)
                for polygon in polygons:
                    cv2.fillConvexPoly(layers[target],polygon,1)
                counters[target]+=len(polygons)
            boundary=indices.reshape(-1,3)[keep&~inside]
            indices=boundary.reshape(-1)
            counts=np.full(len(boundary),3,dtype=np.int64)
        # Orthographic projection of individual mesh faces intersecting the body-height band.
        for n in counts:
            poly = pts[indices[offset:offset+n]]
            offset += n
            if n < 3 or poly[:, 2].max() < lower or poly[:, 2].min() > upper:
                continue
            for bound, keep_above in [(lower, True), (upper, False)]:
                if not len(poly):
                    break
                inside = poly[:, 2] >= bound if keep_above else poly[:, 2] <= bound
                if inside.all():
                    continue
                if not inside.any():
                    poly = np.empty((0, 3)); break
                clipped = []
                for i in range(len(poly)):
                    a, b = poly[i-1], poly[i]
                    if inside[i-1] != inside[i]:
                        clipped.append(a + (bound-a[2])/(b[2]-a[2]) * (b-a))
                    if inside[i]:
                        clipped.append(b)
                poly = np.asarray(clipped)
            if len(poly) >= 3:
                cv2.fillPoly(layers[target], [pixels(poly[:, :2])], 1)
                counters[target] += 1
    # Tiny subpixel seams between adjacent triangles are raster artefacts.
    kernel = np.ones((3, 3), np.uint8)
    for name in ['floor', 'wall', 'furniture', 'doors']:
        layers[name] = cv2.morphologyEx(layers[name], cv2.MORPH_CLOSE, kernel)
    blocked = (layers['wall'] | layers['furniture'] | layers['doors']).astype(bool)
    floor = layers['floor'].astype(bool)
    free = floor & ~blocked
    distance = ndi.distance_transform_edt(free) * resolution
    safe = free & (distance >= .18)
    labels, num = ndi.label(safe)
    sizes = np.bincount(labels.ravel()); sizes[0] = 0
    # Keep every substantial ground-floor component; do not synthesize connections.
    safe &= sizes[labels] >= .7 / resolution**2
    directory = output / 'scenes' / scene
    directory.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(directory / 'geometry.npz', **layers, safe=safe, distance=distance.astype(np.float32))
    data = dict(scene=scene, extraction_version=GEOMETRY_VERSION, source=str(path), source_sha256=digest(path), units='meters', up_axis='Z',
                floor_z=0, resolution=resolution, low=low.tolist(), high=high.tolist(), width=int(w), height=int(h),
                transform='u=(x-low_x)/resolution; v=(high_y-y)/resolution',
                body_height_band=[.18, 1.65], clearance_m=.18,
                extraction='CPU USD world-space mesh faces, clipped to height band and rasterized; visibility respected. Geometry approximation, not simulator collision certification.',
                objects=[dict(key=k, **{a:(b.tolist() if hasattr(b, 'tolist') else b) for a,b in v.items()}) for k,v in objects.items()],
                mesh_count=len(meshes), rasterized_faces=dict(counters), seconds=round(time.time()-started,2))
    write_json(directory / 'geometry.json', data)
    rgb = np.full((h, w, 3), [231,235,239], dtype=np.uint8)
    rgb[layers['floor'] > 0] = [250,248,241]
    rgb[layers['furniture'] > 0] = [157,180,192]
    rgb[layers['wall'] > 0] = [54,65,79]
    rgb[layers['doors'] > 0] = [176,135,88]
    cv2.imwrite(str(directory/'floorplan.png'), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    print(json.dumps(dict(scene=scene, dimensions=[int(w),int(h)], meshes=len(meshes), seconds=data['seconds']),ensure_ascii=False), flush=True)


def angular_groups(mask, max_gap=2):
    """Return substantial circular runs; close only tiny angular sampling gaps."""
    import numpy as np
    mask = mask.copy()
    n = len(mask)
    for _ in range(max_gap):
        mask |= np.roll(mask, 1) & np.roll(mask, -1)
    if mask.all() or not mask.any():
        return []
    starts = np.flatnonzero(mask & ~np.roll(mask, 1))
    runs = []
    for start in starts:
        length = 1
        while length < n and mask[(start+length) % n]:
            length += 1
        if length >= 5:
            runs.append((float((start + (length-1)/2) % n) * 2*math.pi/n, length*2*math.pi/n))
    return runs


def map_scene(output, scene):
    import cv2
    import numpy as np
    from scipy import ndimage as ndi
    directory = output / 'scenes' / scene
    meta = json.loads((directory/'geometry.json').read_text())
    data = np.load(directory/'geometry.npz')
    floor, furniture, doors = (data[k].astype(bool) for k in ['floor','furniture','doors'])
    res = meta['resolution']; h, w = floor.shape
    # Fill narrow interiors between the two projected surfaces of a wall.
    k = int(round(.28/res)) | 1
    wall = cv2.morphologyEx(data['wall'], cv2.MORPH_CLOSE, np.ones((k,k),np.uint8)).astype(bool)
    blocked = wall | furniture | doors
    free = floor & ~blocked
    distance = ndi.distance_transform_edt(free)*res
    safe = free & (distance >= .18)
    labels, _ = ndi.label(safe)
    sizes = np.bincount(labels.ravel()); sizes[0] = 0
    safe &= sizes[labels] * res**2 >= .7
    # Evaluate branching in geometry, without reading task paths or outcomes.
    # A route arm must stay free along a ray and retain a nontrivial angular width.
    angles = np.arange(180)*2*math.pi/180
    radius_sets = [1., 1.4, 1.8]
    offsets = []
    for radius in radius_sets:
        sample_r = np.linspace(.12, radius, 18)
        offsets.append((np.cos(angles)[:,None]*sample_r[None,:]/res,
                        -np.sin(angles)[:,None]*sample_r[None,:]/res))
    candidates = []
    stride = 5
    ys, xs = np.where(safe & (distance >= .26))
    take = (ys % stride == 0) & (xs % stride == 0)
    for y,x in zip(ys[take],xs[take]):
        patterns = []
        for radius, (dx,dy) in zip(radius_sets,offsets):
            xx, yy = np.rint(x+dx).astype(int), np.rint(y+dy).astype(int)
            valid = (xx>=0)&(xx<w)&(yy>=0)&(yy<h)
            visible = np.all(valid & safe[np.clip(yy,0,h-1),np.clip(xx,0,w-1)],axis=1)
            arms = angular_groups(visible)
            patterns.append(arms)
        valid_scales = [i for i,a in enumerate(patterns) if len(a)>=3]
        if len(valid_scales)<2:
            continue
        chosen = valid_scales[-1]
        arms = patterns[chosen]
        widths = [a[1] for a in arms]
        score = len(valid_scales)*5 + min(len(arms),4)*2 + min(widths) + min(distance[y,x],.8)
        candidates.append(dict(pixel=[int(x),int(y)], radius=radius_sets[chosen],
                               directions=[round(a[0],5) for a in arms],
                               angular_widths=[round(a[1],5) for a in arms],
                               scale_counts=[len(a) for a in patterns], score=round(float(score),4),
                               clearance_m=round(float(distance[y,x]),3)))
    selected = []
    for candidate in sorted(candidates,key=lambda c:(-c['score'],c['pixel'])):
        if all(math.dist(candidate['pixel'],other['pixel'])*res >= 1.35 for other in selected):
            selected.append(candidate)
    selected.sort(key=lambda c:(c['pixel'][1],c['pixel'][0]))
    low, high = meta['low'],meta['high']
    for i,c in enumerate(selected,1):
        x,y=c['pixel'];c.update(id=f'C{i:02d}', position=[round(low[0]+x*res,4),round(high[1]-y*res,4)],
                               branch_count=len(c['directions']),status='proposed', match_radius_m=.7,
                               source='static_scene_geometry', review_note='Geometry-derived prior, pending visual review; not an online detector result.')
        c['branches'] = [[round(c['position'][0]+c['radius']*math.cos(a),4),round(c['position'][1]+c['radius']*math.sin(a),4)] for a in c['directions']]
    rgb = np.full((h,w,3),[232,237,242],np.uint8)
    rgb[floor]=[250,248,240];rgb[furniture]=[153,178,191];rgb[wall]=[49,62,79];rgb[doors]=[174,127,76]
    cv2.imwrite(str(directory/'floorplan.png'),cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
    walk=rgb.copy();walk[safe]=(walk[safe].astype(float)*.55+np.array([163,216,191])*.45).astype(np.uint8)
    cv2.imwrite(str(directory/'walkable.png'),cv2.cvtColor(walk,cv2.COLOR_RGB2BGR))
    scale=2
    preview=cv2.resize(rgb,(w*scale,h*scale),interpolation=cv2.INTER_NEAREST)
    for c in selected:
        x,y=[int(v*scale) for v in c['pixel']]
        for a in c['directions']:
            end=(int(x+math.cos(a)*c['radius']/res*scale),int(y-math.sin(a)*c['radius']/res*scale))
            cv2.arrowedLine(preview,(x,y),end,(211,104,20),2,tipLength=.18)
        cv2.circle(preview,(x,y),14,(238,139,40),-1)
        cv2.putText(preview,c['id'],(x+15,y-10),cv2.FONT_HERSHEY_SIMPLEX,.6,(136,54,12),2,cv2.LINE_AA)
    cv2.imwrite(str(directory/'crossings_preview.png'),cv2.cvtColor(preview,cv2.COLOR_RGB2BGR))
    np.savez_compressed(directory/'map_masks.npz',floor=floor,wall=wall,furniture=furniture,doors=doors,safe=safe,distance=distance.astype(np.float32))
    crossings=dict(scene=scene,definition='At least three substantial connected direction arms, so excluding the incoming route leaves at least two choices.',
                   method='World-space geometry only. Candidate rays must remain inside traversable space at >=2 of 1.0/1.4/1.8m scales. Cluster separation 1.35m. Human review required for semantic route equivalence.',
                   status='geometry_prior_for_review',raw_candidate_count=len(candidates),crossings=selected)
    write_json(directory/'crossings.json',crossings)
    print(json.dumps(dict(scene=scene,crossings=len(selected),raw_candidates=len(candidates)),ensure_ascii=False),flush=True)


def curated_maps(output):
    import cv2
    import numpy as np
    decisions=json.loads((output/'review_decisions.json').read_text())
    for scene, decision in decisions['scenes'].items():
        directory=output/'scenes'/scene
        source=json.loads((directory/'crossings.json').read_text())
        lookup={c['id']:c for c in source['crossings']}
        selected=[]
        for item in decision['keep']:
            c=lookup[item['id']].copy()
            c.update(note=item['note'],kind=item.get('kind','route_junction'),status='pending_user_review',
                     prior_id=c['id'],visual_review='Assistant inspected geometry map; user verification pending.')
            if 'position' in item:
                c['position']=item['position']
            if 'directions_deg' in item:
                c['directions']=[math.radians(a) for a in item['directions_deg']]
                c['branch_count']=len(c['directions'])
            if 'branch_labels' in item:
                c['branch_labels']=item['branch_labels']
            selected.append(c)
        meta=json.loads((directory/'geometry.json').read_text())
        res=meta['resolution']
        for i,c in enumerate(selected,1):
            c['id']=f'C{i:02d}'
            c['pixel']=[(c['position'][0]-meta['low'][0])/res,(meta['high'][1]-c['position'][1])/res]
            c['branches']=[[round(c['position'][0]+c['radius']*math.cos(a),4),round(c['position'][1]+c['radius']*math.sin(a),4)] for a in c['directions']]
        curated=dict(source, crossings=selected, assistant_review_note=decision['note'],
                     excluded_ids=[c['id'] for c in source['crossings'] if c['id'] not in {x['id'] for x in decision['keep']}],
                     status='assistant_geometry_reviewed_awaiting_user')
        write_json(directory/'crossings_reviewed.json',curated)
        image=cv2.imread(str(directory/'floorplan.png'))
        image=cv2.resize(image,None,fx=2,fy=2,interpolation=cv2.INTER_NEAREST)
        for c in selected:
            x,y=[int(round(v*2)) for v in c['pixel']]
            cv2.circle(image,(x,y),int(.7/res*2),(193,199,244),1,cv2.LINE_AA)
            for a in c['directions']:
                end=(int(x+math.cos(a)*c['radius']/res*2),int(y-math.sin(a)*c['radius']/res*2))
                cv2.arrowedLine(image,(x,y),end,(31,102,219),2,tipLength=.18)
            cv2.circle(image,(x,y),12,(31,119,235),-1)
            cv2.putText(image,c['id'],(x+14,y-8),cv2.FONT_HERSHEY_SIMPLEX,.6,(23,61,134),2,cv2.LINE_AA)
        cv2.imwrite(str(directory/'crossings_reviewed.png'),image)
        print(scene,'reviewed',len(selected),'of',len(source['crossings']),flush=True)


def data_uri(path, mime='image/png'):
    return 'data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()


def pack(output):
    import cv2
    import numpy as np
    manifest=json.loads((output/'selection.json').read_text())
    scenes={}
    room_names={'livingroom':'客厅','bedroom':'卧室','bathroom':'卫浴','kitchen':'厨房','diningroom':'餐厅',
                'corridor':'走廊','hallway':'走廊','balcony':'阳台','entrance':'入口','studyroom':'书房','storageroom':'储物间'}
    for scene in sorted(manifest['scene_counts']):
        directory=output/'scenes'/scene
        meta=json.loads((directory/'geometry.json').read_text())
        cross=json.loads((directory/'crossings_reviewed.json').read_text())
        rooms=defaultdict(list)
        for obj in meta['objects']:
            if obj['room']:
                rooms[obj['room']].append(obj)
        labels=[]
        for name,objects in sorted(rooms.items()):
            low=np.min([o['low'][:2] for o in objects],axis=0)
            high=np.max([o['high'][:2] for o in objects],axis=0)
            labels.append(dict(name=room_names.get(name.rsplit('_',1)[0],name),source=name,position=((low+high)/2).tolist()))
        scenes[scene]=dict(scene=scene,width=meta['width'],height=meta['height'],low=meta['low'],high=meta['high'],resolution=meta['resolution'],
                           floorplan=data_uri(directory/'floorplan.png'),walkable=data_uri(directory/'walkable.png'),
                           crossings=cross['crossings'],rooms=labels,source_hash=meta['source_sha256'],
                           review_note=cross['assistant_review_note'],raw_count=cross['raw_candidate_count'])
    (output/'videos').mkdir(exist_ok=True)
    (output/'snapshots').mkdir(exist_ok=True)
    cases=[]; validations=[]
    for c in manifest['cases']:
        s=scenes[c['scene']]
        positions=np.asarray([step['position'][:2] for step in c['steps']])
        nonterminal=[st['frame'] for st in c['steps'] if not st['terminal'] and not st['rgb_reused']]
        want={nonterminal[0],nonterminal[len(nonterminal)//2],nonterminal[-1]}
        near=[]
        for crossing in s['crossings']:
            distances=np.linalg.norm(positions-crossing['position'],axis=1)
            frame=min(nonterminal,key=lambda f:distances[f])
            near.append(dict(crossing_id=crossing['id'],frame=int(frame),distance_m=round(float(distances[frame]),3)))
            if distances[frame] <= 3.5:
                want.add(frame)
        capture=cv2.VideoCapture(c['source_video'])
        assert capture.isOpened(),c['episode_id']
        count=int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        assert count==c['frames'],(c['episode_id'],count,c['frames'])
        snapshots=[]
        for frame in sorted(want):
            capture.set(cv2.CAP_PROP_POS_FRAMES,frame)
            ok,rgb=capture.read();assert ok,(c['episode_id'],frame)
            # Only the original first-person image; no reference-path inset or outcome text.
            rgb=cv2.resize(rgb[:480,:640],(480,360),interpolation=cv2.INTER_AREA)
            ok,encoded=cv2.imencode('.jpg',rgb,[cv2.IMWRITE_JPEG_QUALITY,83]);assert ok
            relative=f'snapshots/{c["number"]:02d}_{frame:04d}.jpg'
            (output/relative).write_bytes(encoded.tobytes())
            snapshots.append(dict(frame=frame,src='data:image/jpeg;base64,'+base64.b64encode(encoded).decode(),path=relative))
        capture.release()
        dest=output/c['video']
        if not dest.exists():
            shutil.copyfile(c['source_video'],dest)
        assert digest(dest)==c['source_video_sha256']
        masks=np.load(output/'scenes'/c['scene']/'map_masks.npz')
        xx=np.rint((positions[:,0]-s['low'][0])/s['resolution']).astype(int)
        yy=np.rint((s['high'][1]-positions[:,1])/s['resolution']).astype(int)
        inside=(xx>=0)&(xx<s['width'])&(yy>=0)&(yy<s['height'])
        assert inside.all(),c['episode_id']
        floor_fraction=float(np.mean(masks['floor'][yy,xx]))
        collision_fraction=float(np.mean((masks['wall']|masks['furniture']|masks['doors'])[yy,xx]))
        assert floor_fraction>=.95,(c['episode_id'],floor_fraction)
        validation=dict(episode=c['episode_id'],frames=count,inside_map=True,on_floor_fraction=round(floor_fraction,4),
                        body_band_overlap_fraction=round(collision_fraction,4),video_sha256=digest(dest))
        validations.append(validation)
        case={k:c[k] for k in ['number','seed','scene','episode_id','instruction','reference_path','pred_path','steps','metrics','fail_reason','frames','actions','fps','video','episode_seed','selection_audit']}
        case.update(snapshots=snapshots,near_crossings=near,source_video_sha256=c['source_video_sha256'],map_validation=validation)
        cases.append(case)
        print('Pack',c['number'],c['episode_id'],'frames',count,'snapshots',len(snapshots),'map floor',round(floor_fraction,3),flush=True)
    payload=dict(schema=1,title='Seed 2 · Checkpoint 场景与 crossing 复核',seed=2,selection_count=25,
                 success_count=12,failure_count=13,crossing_count=sum(len(s['crossings']) for s in scenes.values()),
                 scenes=scenes,cases=cases,created_at=datetime.now(timezone.utc).isoformat(),
                 note='This is a development subset and an independent geometry-derived prior. No checkpoint detector or new navigation rollout was run.')
    html=(ROOT/'core/checkpoint_review.html').read_text().replace('__REVIEW_DATA__',json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c'))
    (output/'index.html').write_text(html)
    write_json(output/'review_data.json',payload)
    write_json(output/'validation.json',dict(passed=True,selected_count=25,successes=12,failures=13,scenes=len(scenes),
                crossings=payload['crossing_count'],videos_verified=25,geometry_version=GEOMETRY_VERSION,cases=validations,
                methods=['unique IDs and normal STOP verified','fall/stuck/timeout excluded','motion and height screened',
                         '25 video frame counts and SHA256 verified','map world-to-pixel bounds and floor coverage checked',
                         '10 geometry maps visually inspected; crossing prior awaiting user review']))
    lines=['Seed 2 — 25-sample checkpoint map review','',
           'Open index.html directly. Maps, annotations, trajectories and RGB snapshots are embedded in the HTML.',
           'Keep videos/ beside index.html for complete navigation playback. No web server or network is required.',
           '12 successes + 13 normal-stop navigation failures, covering 10 scenes. Falls/stalls/timeouts excluded.',
           'Crossings are a geometry-derived prior reviewed by the assistant, awaiting user verification; not official ground truth.',
           'Map: world XY in meters, +Y upward. Ground floor z=0. Geometry band z=0.18..1.65m, 0.035m/pixel.',
           'The 0.18m clearance and projected furniture are approximations, not certified robot collision geometry.',
           'Dashed ring: provisional 0.7m inspection region, not an established evaluation tolerance.',
           'Orange points: >=3 route arms including the incoming route; at least 2 outgoing choices remain.',
           'Global positions, reference paths, outcomes and this prior are review-only inputs, not future online detector inputs.',
           'Browser accept/reject/add/note edits can be exported as JSON. No server files are modified by the page.',
           '', 'Rebuild with scripts/build_checkpoint_review.py; source provenance is in selection.json and scenes/*/geometry.json.']
    (output/'README.txt').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(html=str(output/'index.html'),html_bytes=(output/'index.html').stat().st_size,crossings=payload['crossing_count'])),flush=True)


def archive(output):
    target=output.parent/(output.name+'.zip')
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
        for path in sorted(output.rglob('*')):
            if path.is_file() and path.suffix not in {'.npz'}:
                z.write(path,arcname=str(Path(output.name)/path.relative_to(output)),
                        compress_type=zipfile.ZIP_STORED if path.suffix=='.mp4' else zipfile.ZIP_DEFLATED)
    print('Archive',target,target.stat().st_size,flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['select', 'extract', 'maps', 'curate', 'pack', 'archive'])
    p.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    p.add_argument('--scene')
    args = p.parse_args()
    if args.command == 'select':
        select(args.output)
    elif args.command=='curate':
        curated_maps(args.output)
    elif args.command=='pack':
        pack(args.output)
    elif args.command=='archive':
        archive(args.output)
    else:
        scenes = [args.scene] if args.scene else sorted(json.loads((args.output/'selection.json').read_text())['scene_counts'])
        for scene in scenes:
            existing=args.output/'scenes'/scene/'geometry.json'
            if args.command=='extract' and existing.exists() and json.loads(existing.read_text()).get('extraction_version')==GEOMETRY_VERSION:
                print('Reusing completed geometry: '+scene,flush=True)
                continue
            (extract if args.command=='extract' else map_scene)(args.output, scene)


if __name__ == '__main__':
    main()
