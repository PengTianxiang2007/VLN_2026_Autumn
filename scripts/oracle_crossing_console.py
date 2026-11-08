"""Render the live Oracle request or send an explicit reviewed response."""
import argparse
import json
import math
from pathlib import Path
import sys
import textwrap
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.oracle_crossing import validate_response,write

CAMPAIGN=ROOT/'outputs/oracle_crossing/seed2_10_multi_20261103'


def render(request):
    from PIL import Image,ImageDraw,ImageFont
    r=json.loads(request.read_text());p=request.parent
    m=json.loads((CAMPAIGN/'manifest.json').read_text());c=next(c for c in m['cases'] if c['episode_id']==r['episode_id'])
    src=ROOT/'outputs/checkpoint_review/seed2_25_20261103/scenes'/c['scene']
    g=json.loads((src/'geometry.json').read_text())
    font=ImageFont.truetype(str(ROOT/'.runtime/isaac45/kit/resources/fonts/NVIDIASans_Rg.ttf'),17)
    im=Image.new('RGB',(1280,790),'#f6f8fb');d=ImageDraw.Draw(im)
    im.paste(Image.open(p/'before.png').convert('RGB').resize((640,480)),(0,40))
    floor=Image.open(src/'floorplan.png').convert('RGB');scale=min(620/floor.width,470/floor.height)
    floor=floor.resize((round(floor.width*scale),round(floor.height*scale)));im.paste(floor,(650,40))
    def xy(point):return(650+(point[0]-g['low'][0])/g['resolution']*scale,40+(g['high'][1]-point[1])/g['resolution']*scale)
    d.line([xy(p)for p in c['reference_path']],fill='#179454',width=4)
    obs=[json.loads(l)for l in (Path(r['case_directory'])/'observations.jsonl').read_text().splitlines()]
    for count in sorted({z.get('intervention_count',0) for z in obs}):
        segment=[z['position'] for z in obs if z.get('intervention_count',0)==count]
        if count:
            segment.insert(0,r['previous_interventions'][count-1]['after_position'])
        if len(segment)>1:d.line([xy(p)for p in segment],fill='#276ce0',width=3)
    for iv in r.get('previous_interventions',[]):
        b=xy(iv['before_position']);e=xy(iv['after_position'])
        for t in range(0,10,2):
            d.line([(b[0]+(e[0]-b[0])*t/10,b[1]+(e[1]-b[1])*t/10),(b[0]+(e[0]-b[0])*(t+1)/10,b[1]+(e[1]-b[1])*(t+1)/10)],fill='#9229bd',width=2)
    targets=r.get('targets',[dict(id=c['crossing_id'],crossing_position=c['crossing']['position'],target_xy=c['target_xy'],target_yaw_rad=c['target_yaw_rad'])])
    for t in targets:
        x,y=xy(t['crossing_position']);d.ellipse((x-9,y-9,x+9,y+9),outline='#cf8022',width=3);d.text((x+10,y-18),t['id'],font=font,fill='#995500')
        x,y=xy(t['target_xy']);d.rectangle((x-4,y-4,x+4,y+4),fill='#9229bd')
        d.line([(x,y),(x+20*math.cos(t['target_yaw_rad']),y-20*math.sin(t['target_yaw_rad']))],fill='#9229bd',width=3)
    x,y=xy(r['position']);d.ellipse((x-6,y-6,x+6,y+6),fill='#d73531')
    w,qx,qy,qz=r['rotation'];yaw=math.atan2(2*(w*qz+qx*qy),1-2*(qy*qy+qz*qz))
    d.line([(x,y),(x+30*math.cos(yaw),y-30*math.sin(yaw))],fill='#d73531',width=4)
    d.text((8,8),f'{r["episode_id"]} | action {r["action_index"]} | corrections {r.get("intervention_count",0)} | initial {r["crossing_id"]} {r["crossing_distance_m"]:.2f} m',font=font,fill='black')
    d.text((650,525),'Green reference; Blue actual; Red robot; Purple target',font=font,fill='black')
    for i,line in enumerate(textwrap.wrap(c['instruction'],width=130)):
        d.text((8,553+i*22),line,font=font,fill='black')
    for i,h in enumerate(r['history'][-6:]):
        f=Path(r['case_directory'])/h['frame']
        if f.exists():im.paste(Image.open(f).resize((160,120)),(i*210,650))
        d.text((i*210,773),str(h['action_index']),font=font,fill='black')
    target=p/'review.jpg';im.save(target,quality=91)
    print(json.dumps(dict(request=str(request),review=str(target),targets=targets,intervention_count=r.get('intervention_count',0),**{k:r[k]for k in ['episode_id','action_index','position','rotation','instruction','expected','original_error','target_xy','target_yaw_rad']}),ensure_ascii=False))


def main():
    global CAMPAIGN
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command',choices=['show','respond'])
    ap.add_argument('--request',type=Path)
    ap.add_argument('--campaign',type=Path,default=CAMPAIGN)
    ap.add_argument('--target',help='Frozen crossing ID; required for a multi-intervention teleport')
    ap.add_argument('--decision',choices=['continue','teleport','abort'])
    ap.add_argument('--reason')
    ap.add_argument('--skip-actions',type=int,default=4)
    a=ap.parse_args()
    CAMPAIGN=a.campaign.resolve()
    pending_file=CAMPAIGN/'oracle_records/pending.json'
    pending=json.loads(pending_file.read_text()) if pending_file.exists() else dict(status='initializing')
    if a.request is None:
        if a.command=='show' and pending['status']!='waiting':
            print(json.dumps(pending,ensure_ascii=False));return
        assert pending['status']=='waiting',pending
        a.request=Path(pending['request'])
    r=json.loads(a.request.read_text())
    if a.command=='show':render(a.request);return
    assert pending['status']=='waiting' and pending['request']==str(a.request)
    response=dict(request_id=r['request_id'],decision=a.decision,reason=a.reason,
                  skip_actions=a.skip_actions,reviewer='assistant_oracle',responded_at=time.time())
    if a.target:response['target_id']=a.target
    validate_response(response,r)
    target=a.request.parent/'response.json'
    assert not target.exists()
    write(target,response);print(json.dumps(response,ensure_ascii=False))


if __name__=='__main__':main()
