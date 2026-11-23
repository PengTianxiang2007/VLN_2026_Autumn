"""Review and associate static Oracle scene anchors; no navigation is launched."""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build_oracle_scene_annotations import read, write, now, sha


def boards(out):
    from PIL import Image, ImageDraw, ImageFont
    tasks = read(out / 'tasks.json')
    groups = defaultdict(list)
    for t in tasks:
        groups[t['scan']].append(t)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
    small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
    directory = out / 'review_boards'
    directory.mkdir(exist_ok=True)
    for scene, ts in sorted(groups.items()):
        base = out / 'scenes' / scene
        g = read(base / 'geometry.json')
        cs = read(base / 'crossings.json')['crossings']
        factor = min(720/g['width'], 760/g['height'])
        w, h = round(g['width']*factor), round(g['height']*factor)
        panels = []
        for route in [False, True]:
            im = Image.open(base / 'floorplan.png').convert('RGB').resize((w,h))
            d = ImageDraw.Draw(im, 'RGBA')
            def xy(p):
                return ((p[0]-g['low'][0])/g['resolution']*factor,
                        (g['high'][1]-p[1])/g['resolution']*factor)
            if route:
                for t in ts:
                    d.line([xy(p) for p in t['reference_path']], fill=(15,130,180,95), width=2)
            for x in range(math.ceil(g['low'][0]), math.floor(g['high'][0])+1):
                u, _ = xy([x,0])
                d.line([(u,0),(u,h)], fill=(110,110,110,45))
                d.text((u+2,0),str(x),font=small,fill=(60,60,60,255))
            for y in range(math.ceil(g['low'][1]), math.floor(g['high'][1])+1):
                _,v = xy([0,y])
                d.line([(0,v),(w,v)],fill=(110,110,110,45))
                d.text((0,v+1),str(y),font=small,fill=(60,60,60,255))
            for c in cs:
                p = xy(c['position']); r = 6
                for b in c['branches']:
                    d.line([p,xy(b)],fill=(218,100,15,220),width=2)
                d.ellipse((p[0]-r,p[1]-r,p[0]+r,p[1]+r),fill=(235,110,20,255))
                d.text((p[0]+7,p[1]-20),c['id'],font=font,fill=(135,45,0,255),stroke_width=1,stroke_fill='white')
            panels.append(im)
        board = Image.new('RGB',(2*w+28,h+65),'white')
        board.paste(panels[0],(0,55));board.paste(panels[1],(w+28,55))
        d=ImageDraw.Draw(board)
        d.text((10,8),f'{scene}  |  {len(cs)} geometry proposals  |  {len(ts)} reference routes  |  XY meters',font=font,fill='black')
        board.save(directory / (scene+'.png'))
    write(out/'review_boards.json',dict(created_at=now(),images={s:sha(directory/(s+'.png')) for s in sorted(groups)}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=['boards'])
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    boards(args.output)


if __name__=='__main__':
    main()
