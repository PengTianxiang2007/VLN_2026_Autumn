"""Export synthetic, causal A/B departure examples for preparation review only."""
import argparse
import json
import math
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.oracle_auto_branch import AutoBranchTrigger


def feed(trigger, positions, start=0):
    return [dict(position=p, action_index=start+i, **trigger.update(p,start+i)) for i,p in enumerate(positions)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    ref=[[0,0],[3,0],[3,4],[8,4]]
    a=[[i/10.,0] for i in range(31)]
    b=a+[[3,i/10.] for i in range(1,41)]
    cases=[]
    for title,points in [('在A走错',a+[[3+i/10.,0] for i in range(1,11)]),
                         ('通过A，在B走错',b+[[3,4+i/10.] for i in range(1,11)])]:
        rows=feed(AutoBranchTrigger({'reference_path':ref}),points)
        first=next(r for r in rows if r['target'])
        cases.append(dict(title=title,reference=ref,observations=rows,
                          first_trigger=first,walked_segments=[points[:first['action_index']+1]],teleport=[]))
    trigger=AutoBranchTrigger({'reference_path':ref})
    first_points=a+[[3+i/10.,0] for i in range(1,9)]
    first_rows=feed(trigger,first_points)
    first=next(r for r in first_rows if r['target'])
    # A reset explicitly labels the hypothetical teleport; its displacement
    # does not enter the walked trajectory used to locate the second departure.
    reset_index=first_rows[-1]['action_index']
    pose=first['target']['target_xy'];trigger.after_correction(pose,reset_index,first['target'])
    points=[[3,pose[1]+(4-pose[1])*i/30] for i in range(1,31)]+[[3,4+i/10.] for i in range(1,11)]
    rows=feed(trigger,points,reset_index+1);second=next(r for r in rows if r['target'])
    cases.append(dict(title='A纠正后，又在B走错',reference=ref,observations=first_rows+rows,
                      first_trigger=second,walked_segments=[first_points,
                                                            [pose]+points[:second['action_index']-reset_index]],
                      teleport=[[first_points[-1],pose]],correction_action_index=reset_index))
    data=dict(scope='Synthetic CPU trajectories; no simulator, policy, actual teleport or navigation score.',
              reference=ref,cases=cases)
    (args.output/'examples.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    font_path=json.loads((ROOT/'core/crossing_visualization_template.json').read_text())['font']
    font=ImageFont.truetype(font_path,24);small=ImageFont.truetype(font_path,18)
    image=Image.new('RGB',(1500,610),'#f6f8fc');draw=ImageDraw.Draw(image)
    draw.text((24,16),'实际从哪里分离，就以哪里为纠正锚点',font=font,fill='#172c42')
    draw.text((24,53),'合成轨迹 / 仅CPU算法验证：不代表真实导航、实际碰撞检查或恢复成功率',font=small,fill='#526071')
    blue='#3877bf';orange='#d67a24';green='#16845d';purple='#8c47b5'
    for index,c in enumerate(cases):
        left=index*500
        def xy(p):return (left+48+p[0]*48,430-p[1]*48)
        draw.rounded_rectangle((left+12,92,left+488,592),radius=14,fill='white',outline='#dae0e9')
        draw.text((left+28,105),c['title'],font=font,fill='#172c42')
        for x in range(9):draw.line([xy([x,0]),xy([x,5.5])],fill='#edf0f5')
        for y in range(6):draw.line([xy([0,y]),xy([8,y])],fill='#edf0f5')
        draw.line([xy(p) for p in ref],fill=blue,width=7)
        for pts in c['walked_segments']:draw.line([xy(p) for p in pts],fill=orange,width=3)
        for p,q in c['teleport']:
            for k in range(0,12,2):
                start=[p[i]+(q[i]-p[i])*k/12 for i in (0,1)]
                end=[p[i]+(q[i]-p[i])*(k+1)/12 for i in (0,1)]
                draw.line([xy(start),xy(end)],fill='#8d96a2',width=2)
        for name,p in [('起点',[0,0]),('A',[3,0]),('B',[3,4]),('终点',[8,4])]:
            u,v=xy(p);draw.text((u-14,v+10),name,font=small,fill='#172c42')
        target=c['first_trigger']['target'];anchor=target['branch_xy'];landing=target['target_xy']
        u,v=xy(anchor);draw.ellipse((u-7,v-7,u+7,v+7),fill=green)
        u,v=xy(landing);draw.ellipse((u-7,v-7,u+7,v+7),fill=purple)
        angle=target['target_yaw_rad'];q=[landing[0]+.65*math.cos(angle),landing[1]+.65*math.sin(angle)]
        qu,qv=xy(q);draw.line([(u,v),(qu,qv)],fill=purple,width=4)
        for delta in [-.5,.5]:
            back=[q[0]-.2*math.cos(angle+delta),q[1]-.2*math.sin(angle+delta)]
            draw.line([(qu,qv),xy(back)],fill=purple,width=3)
        draw.text((left+28,485),'绿色：实际轨迹估计的分离位置',font=small,fill=green)
        draw.text((left+28,514),'紫色：沿正确路线前移1.25米及朝向',font=small,fill=purple)
        draw.text((left+28,548),'蓝色：正确路线　橙色：已走轨迹',font=small,fill='#526071')
    image.save(args.output/'branch_examples.png')
    print(json.dumps(dict(examples=len(cases),image=str(args.output/'branch_examples.png'),simulation_started=False),ensure_ascii=False))


if __name__=='__main__':
    main()
