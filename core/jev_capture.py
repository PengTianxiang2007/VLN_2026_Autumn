"""Pure geometry for fresh simulator observations at frozen offline JEV nodes."""
import math


def wrap(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def action(row):
    value = row.get('action_after_observation') or {}
    if 'move_by_discrete' in value:
        return int(value['move_by_discrete'][0])
    if not value or set(value) <= {'stop', 'stand_still'}:
        return 0
    raise ValueError('Unknown recorded action: ' + str(value))


def estimate_headings(frames, start_rotation, visual_motion=None):
    """Pose F_i precedes action F_i. Use only motions completed before F_i.

    Integrate native 15-degree turns, with a 0.5 circular correction from the
    most recent <=6 consecutive forward actions when displacement >=0.20m.
    Reject direction residuals >60 degrees (possible collisions/side slips).
    This is an estimate, never a recovered physical orientation.
    """
    w,x,y,z = start_rotation
    yaw = math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))
    last_anchor = None
    result = []
    for i,row in enumerate(frames):
        if row['frame'] != i:
            raise ValueError('Non-contiguous source frames')
        visual=visual_motion[i] if visual_motion is not None else None
        if i:
            delta={2:math.pi/12,3:-math.pi/12}.get(action(frames[i-1]),0)
            if visual and visual['valid']:
                delta=math.radians(visual['delta_yaw_deg'])
            yaw = wrap(yaw + delta)
        prior = yaw
        anchor = None
        j = i
        while j>max(0,i-6) and action(frames[j-1])==1:
            j -= 1
        if j<i:
            dx = row['position'][0]-frames[j]['position'][0]
            dy = row['position'][1]-frames[j]['position'][1]
            distance = math.hypot(dx,dy)
            if distance>=.20:
                observed = math.atan2(dy,dx); residual = wrap(observed-yaw)
                accepted = abs(residual)<=math.pi/3
                anchor = dict(start_frame=j,end_frame=i,distance_m=distance,
                              bearing_deg=math.degrees(observed),residual_deg=math.degrees(residual),accepted=accepted)
                if accepted:
                    yaw = wrap(yaw+.5*residual);last_anchor=i
        result.append(dict(frame=i,base_yaw_deg=math.degrees(yaw)%360,
                           action_prior_yaw_deg=math.degrees(prior)%360,
                           displacement_check=anchor,last_displacement_anchor=last_anchor,
                           visual_motion=visual,
                           source='estimated_start_rotation_rgb_motion_turns_and_forward_displacement',
                           historical_orientation_recorded=False))
    return result


def estimate_visual_motion(image_paths):
    """Robust bearing shift of ORB matches; missing/ambiguous images fall back.

    Native horizontal FOV is 90 degrees. Homography RANSAC selects consistent
    matches; median ray-bearing difference estimates yaw (positive = left).
    This approximation can include parallax and is recorded as uncertain.
    """
    import cv2
    import numpy as np
    cv2.setNumThreads(2);cv2.setRNGSeed(20261115)
    orb=cv2.ORB_create(nfeatures=1800);matcher=cv2.BFMatcher(cv2.NORM_HAMMING)
    previous=None;result=[]
    for i,path in enumerate(image_paths):
        im=cv2.imread(str(path),cv2.IMREAD_GRAYSCALE)
        if im is None:raise ValueError('Missing recorded RGB: '+str(path))
        kp,des=orb.detectAndCompute(im,None);row=dict(frame=i,valid=False,reason='no_previous_image' if i==0 else 'insufficient_matches')
        if previous and des is not None and previous[1] is not None:
            pk,pd,width=previous
            if width!=im.shape[1]:raise ValueError('Image widths changed')
            pairs=matcher.knnMatch(pd,des,k=2)
            matches=[a for pair in pairs if len(pair)==2 for a,b in [pair] if a.distance<.75*b.distance]
            if len(matches)>=12:
                src=np.float32([pk[m.queryIdx].pt for m in matches]);dst=np.float32([kp[m.trainIdx].pt for m in matches])
                hom,mask=cv2.findHomography(src,dst,cv2.RANSAC,3)
                if hom is not None:
                    src=src[mask.ravel()>0];dst=dst[mask.ravel()>0]
                    if len(src)>=8:
                        differences=np.degrees(np.arctan((dst[:,0]-width/2)/(width/2))-np.arctan((src[:,0]-width/2)/(width/2)))
                        delta=float(np.median(differences));mad=float(np.median(np.abs(differences-delta)))
                        row.update(delta_yaw_deg=delta,mad_deg=mad,inliers=len(src),matches=len(matches),
                                   valid=abs(delta)<=35 and mad<=6,reason='robust_rgb_bearing_shift')
        result.append(row);previous=kp,des,im.shape[1]
    return result


def camera_position(root, yaw_deg, offset):
    yaw = math.radians(yaw_deg);x,y,z = offset
    return [root[0]+x*math.cos(yaw)-y*math.sin(yaw),
            root[1]+x*math.sin(yaw)+y*math.cos(yaw),root[2]+z]


VIEW_OFFSETS = [0,45,90,135,180,225,270,315]
VIEW_SETS = {'180': [7,0,1], '360': list(range(8))}


def align_reference(reference_path, candidates):
    """Estimate absolute yaw by matching old node RGB to fresh known-yaw views.

    Require spatially spread RANSAC inliers; competing strong matches must
    agree. Return evidence and a reject reason instead of inventing a heading.
    """
    import cv2
    import numpy as np
    cv2.setNumThreads(2);cv2.setRNGSeed(20261115)
    orb=cv2.ORB_create(nfeatures=2400);matcher=cv2.BFMatcher(cv2.NORM_HAMMING)
    ref=cv2.imread(str(reference_path),0)
    if ref is None:raise ValueError('Missing source RGB')
    ka,da=orb.detectAndCompute(ref,None);reports=[]
    for c in candidates:
        im=cv2.imread(str(c['path']),0);kb,db=orb.detectAndCompute(im,None)
        if da is None or db is None:continue
        matches=[a for pair in matcher.knnMatch(da,db,k=2) if len(pair)==2 for a,b in [pair] if a.distance<.75*b.distance]
        if len(matches)<20:continue
        src=np.float32([ka[m.queryIdx].pt for m in matches]);dst=np.float32([kb[m.trainIdx].pt for m in matches])
        h,mask=cv2.findHomography(src,dst,cv2.RANSAC,3)
        if h is None:continue
        src=src[mask.ravel()>0];dst=dst[mask.ravel()>0]
        if len(src)<20:continue
        coverage=float(cv2.contourArea(cv2.convexHull(src)))/(ref.shape[0]*ref.shape[1])
        if coverage<.05 or len(src)/len(matches)<.35:continue
        delta=np.degrees(np.arctan((dst[:,0]-im.shape[1]/2)/(im.shape[1]/2))-np.arctan((src[:,0]-ref.shape[1]/2)/(ref.shape[1]/2)))
        median=float(np.median(delta));mad=float(np.median(np.abs(delta-median)))
        if mad>6:continue
        reports.append(dict(view_id=c['id'],inliers=len(src),coverage=coverage,mad_deg=mad,
                            base_yaw_deg=(c['world_yaw_deg']-median)%360))
    reports.sort(key=lambda r:r['inliers'],reverse=True)
    if not reports:return dict(accepted=False,reason='insufficient_cross_render_matches',candidates=[])
    best=reports[0]
    if any(abs((r['base_yaw_deg']-best['base_yaw_deg']+180)%360-180)>20 for r in reports[1:] if r['inliers']>=.7*best['inliers']):
        return dict(accepted=False,reason='ambiguous_strong_matches',candidates=reports)
    return dict(accepted=True,reason='reference_rgb_to_fresh_render_alignment',base_yaw_deg=best['base_yaw_deg'],candidates=reports,
                estimated_not_measured=True)
