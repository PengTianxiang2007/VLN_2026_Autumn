"""Externalize embedded media for incremental loading; preserve original bytes."""
import argparse,base64,hashlib,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--html',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args()
a.destination.mkdir(parents=True,exist_ok=False);(a.destination/'assets').mkdir()
s=a.html.read_text();assets={}
def extract(m):
    mime,encoded=m.groups();raw=base64.b64decode(encoded);h=hashlib.sha256(raw).hexdigest()
    ext={'image/webp':'webp','image/png':'png','image/jpeg':'jpg','font/woff2':'woff2','font/ttf':'ttf','font/otf':'otf','application/font-woff':'woff'}.get(mime,mime.split('/')[-1].split(';')[0])
    assert re.fullmatch('[A-Za-z0-9-]+',ext),ext
    name='assets/'+h+'.'+ext
    if name not in assets:(a.destination/name).write_bytes(raw);assets[name]=h
    return name
s=re.sub(r'data:((?:image|font|application/font)[^;,\s"\x27)]*);base64,([A-Za-z0-9+/=]+)',extract,s)
s=s.replace('本文件完全离线；','在线版：图片按需加载；').replace('三帧五级评分离线复核','三帧五级评分在线复核')
(a.destination/a.html.name).write_text(s)
(a.destination/'online_manifest.json').write_text(json.dumps({'source':str(a.html),'source_sha256':hashlib.sha256(a.html.read_bytes()).hexdigest(),'html':a.html.name,'assets':assets},indent=2))
print(json.dumps({'html_bytes':len(s.encode()),'assets':len(assets)}))
