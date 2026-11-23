"""Bounded protocol diagnostics for the user-selected JEV gateway. No navigation."""
import argparse
import base64
import copy
import getpass
import hashlib
import io
import json
from pathlib import Path
import sys
import time

import httpx
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from core.serial_pipeline import save


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--request',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--routes',nargs='+',choices=['direct','proxy7892'],default=['direct','proxy7892'])
    p.add_argument('--image-compatibility',action='store_true')
    p.add_argument('--model-check',action='store_true')
    p.add_argument('--synthetic-image',action='store_true',help='One 320x320 solid-red transport control, unrelated to navigation.')
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    key=getpass.getpass('JEV key: ')
    original=json.loads(a.request.read_text()); ref,asset=next(iter(original['assets'].items()))
    text=dict(model='jev-1.14.0',state='Our payouts have been failing for three days and we launch tomorrow. Please help!',questions={
        'is_urgent':dict(type='noul',instructions='Does the customer express urgency?'),
        'team':dict(type='choice',instructions='Which team should handle this message?',criteria={
            'billing':'Payments, invoices, refunds and payouts','technical':'Bugs, outages and integrations','sales':'Pricing, upgrades and new accounts'}),
        'frustration':dict(type='score',instructions='How frustrated is the customer?',criteria=['Calm','Mildly annoyed','Frustrated','Very angry'])})
    image=dict(model='jev-1.14.0',state={'camera':ref},assets={ref:asset},questions={'probe':dict(type='noul',instructions='Is there a visible doorway in the camera image?')})
    probes=[('document_text',text),('project_image_json',original),('minimal_image_json',image),('minimal_image_multipart',image)]
    if a.image_compatibility:
        jpeg=copy.deepcopy(image); buffer=io.BytesIO()
        Image.open(io.BytesIO(base64.b64decode(asset['data_base64']))).convert('RGB').save(buffer,format='JPEG',quality=90,progressive=False)
        jpeg['assets'][ref]={'type':'image','format':'jpg','data_base64':base64.b64encode(buffer.getvalue()).decode()}
        probes=[('document_text_image_header',text),('minimal_image_jpeg',jpeg),('minimal_image_lowercase_header',image),('minimal_image_no_header',image)]
    if a.model_check:
        # Model aliases are diagnostic only. The experiment stays version-pinned.
        probes=[]
        for model in ['jev-1.14.0','jev-1.13.0','jev-latest','jev-preview']:
            for name,body in [('text',text),('image',image)]:
                body=copy.deepcopy(body); body['model']=model
                probes.append((model+'_'+name,body))
    if a.synthetic_image:
        buffer=io.BytesIO(); Image.new('RGB',(320,320),(255,0,0)).save(buffer,format='PNG')
        control=dict(model='jev-1.14.0',state={'photo':'a3f1c2e8-control'},assets={
            'a3f1c2e8-control':dict(type='image',format='png',data_base64=base64.b64encode(buffer.getvalue()).decode())},
            questions={'is_red':dict(type='noul',instructions='Is the photo predominantly red?')})
        probes=[('synthetic_image',control)]
    results=[]
    for route in a.routes:
      proxy='http://127.0.0.1:7892' if route=='proxy7892' else None
      with httpx.Client(timeout=60,proxies=proxy,trust_env=False,follow_redirects=False) as c:
        for name,body in probes:
            started=time.time()
            headers={'Authorization':'Bearer '+key}
            if ('assets' in body or name=='document_text_image_header') and name!='minimal_image_no_header':
                headers['typesafe-danger-zone-images' if name.endswith('lowercase_header') else 'TypeSafe-Danger-Zone-Images']='true'
            digest=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
            save(a.output/(route+'_'+name+'.request.json'),body)
            print(json.dumps(dict(starting=name,route=route,request_sha256=digest)),flush=True)
            try:
                if name.endswith('multipart'):
                    body=copy.deepcopy(body); body['assets'][ref]={'type':'image','part':'camera'}
                    files=[('request',(None,json.dumps(body),'application/json')),
                           ('camera',('camera.png',base64.b64decode(asset['data_base64']),'image/png'))]
                    response=c.post('https://api.site/v1/systemone',headers=headers,files=files)
                else: response=c.post('https://api.site/v1/systemone',headers=headers,json=body)
                row=dict(probe=name,route=route,request_sha256=digest,http_status=response.status_code,seconds=time.time()-started,
                         body=response.text.replace(key,'[REDACTED]'),
                         request_id=response.headers.get('x-request-id') or response.headers.get('x-typesafe-request-id'))
            except Exception as e: row=dict(probe=name,route=route,request_sha256=digest,error=str(e).replace(key,'[REDACTED]'),seconds=time.time()-started)
            results.append(row); save(a.output/'results.json',results); print(json.dumps(row),flush=True)


if __name__=='__main__':main()
