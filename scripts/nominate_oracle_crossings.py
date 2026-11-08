from pathlib import Path
import json,csv,sys,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from scripts.analyze_crossing_failures import dense_path
S=P/'outputs/reproduction/streamvln_scene250_5seeds_20261101_v2'; A=P/'outputs/checkpoint_review/seed2_crossing_attribution_20261103'
E=json.loads((A/'evidence.json').read_text()); cases={x['episode_id']:x for x in E['cases']}
rows=list(csv.DictReader((A/'attribution.csv').open()));scores=list(csv.DictReader((S/'episodes.csv').open()))
index=[json.loads(l) for l in (S/'visualization/index.jsonl').read_text().splitlines()]; index={(x['seed'],x['episode_id']):x for x in index}
out=P/'outputs/oracle_crossing/seed2_10_20261103'
if (out/'manifest.json').exists():raise RuntimeError('Cohort already frozen; preserve its candidate evidence')
out.mkdir(parents=True,exist_ok=True)
rank=[]
for r in rows:
 if r['status']!='crossing':continue
 eid=r['episode_id']; c=cases[eid];v=index[3,eid]
 if v['metrics']['success'] or v['fail_reason']!='not_reach_goal':continue
 s3=[json.loads(l) for l in (S/'visualization'/v['steps']).read_text().splitlines()]
 cross=next(x for x in E['scenes'][r['scene']]['crossings'] if x['id']==r['crossing_id'])
 p=np.array(cross['position']);a=np.array([x['position'][:2] for x in c['steps']]);b=np.array([x['position'][:2] for x in s3]);f=int(r['decision_frame'])
 # Find a matching outgoing segment in seed3. Nomination only; visual review required.
 end=f
 while end+1<len(a) and np.linalg.norm(a[end]-a[f])<1.4:end+=1
 direction=a[end]-a[f];norm=np.linalg.norm(direction)
 best=None
 for j in range(len(b)-1):
  if np.linalg.norm(b[j]-a[f])>1.0:continue
  k=j
  while k+1<len(b) and np.linalg.norm(b[k]-b[j])<max(norm,0.9):k+=1
  d=b[k]-b[j];cos=float(np.dot(d,direction)/max(np.linalg.norm(d)*norm,1e-8))
  error=float(np.linalg.norm(b[k]-a[end]));cost=error+float(np.linalg.norm(b[j]-a[f]))
  if cos>.7 and (best is None or cost<best['cost']):best=dict(frame=j,end=k,cos=cos,cost=cost,endpoint_error=error)
 fails=[int(x['run_seed']) for x in scores if x['episode_id']==eid and float(x['SR'])==0 and x['fail_reason']=='not_reach_goal']
 if best is not None:rank.append(dict(episode_id=eid,scene=r['scene'],crossing_id=r['crossing_id'],review=r,seed3=best,failed_seeds=fails,seed2_end=end))
rank.sort(key=lambda x:(-len(x['failed_seeds']),x['seed3']['cost'],x['episode_id']))
(out/'candidate_ranking.json').write_text(json.dumps(rank,ensure_ascii=False,indent=2))
font=ImageFont.truetype(str(P/'.runtime/isaac45/kit/resources/fonts/NVIDIASans_Rg.ttf'),14)
for page in range((len(rank)+5)//6):
 canvas=Image.new('RGB',(1500,1060),'white');dr=ImageDraw.Draw(canvas)
 for i,r in enumerate(rank[page*6:page*6+6]):
  c=cases[r['episode_id']];scene=E['scenes'][r['scene']];v=index[3,r['episode_id']];s3=[json.loads(l) for l in (S/'visualization'/v['steps']).read_text().splitlines()]
  im=Image.open(P/'outputs/checkpoint_review/seed2_25_20261103/scenes'/r['scene']/'floorplan.png').convert('RGB');scale=min(480/im.width,440/im.height);im=im.resize((round(im.width*scale),round(im.height*scale)))
  ox=(i%3)*500;oy=(i//3)*530;canvas.paste(im,(ox,oy+55))
  def xy(p):return(ox+(p[0]-scene['low'][0])/scene['resolution']*scale,oy+55+(scene['high'][1]-p[1])/scene['resolution']*scale)
  for pts,col in [(c['reference_path'],'#119944'),([s['position'] for s in c['steps']],'#2266dd'),([s['position'] for s in s3],'#dd9900')]:dr.line([xy(p) for p in pts],fill=col,width=2)
  for cr in scene['crossings']:
   x,y=xy(cr['position']);dr.ellipse((x-5,y-5,x+5,y+5),outline='red',width=2);dr.text((x+5,y),cr['id'],fill='red',font=font)
  f=int(r['review']['decision_frame']);x,y=xy(c['steps'][f]['position']);dr.ellipse((x-7,y-7,x+7,y+7),outline='blue',width=3)
  dr.text((ox+5,oy+3),f'{page*6+i+1}: {r["episode_id"]} {r["crossing_id"]}',fill='black',font=font)
  dr.text((ox+5,oy+23),f'fail seeds {r["failed_seeds"]}; 2f{f}, 3f{r["seed3"]["frame"]}',fill='black',font=font)
 canvas.save(out/f'candidate_page_{page}.jpg')
for i,r in enumerate(rank):print(i+1,r['episode_id'],r['crossing_id'],r['failed_seeds'],r['seed3'])
