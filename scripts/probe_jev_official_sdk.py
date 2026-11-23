"""Audit official TypeSafe SDK serialization against an existing JEV request.

Use the isolated SDK environment. Credentials are read without echo and never
saved. Only the user-selected relay is contacted; no credential goes upstream.
"""
import argparse
import base64
from email import policy
from email.parser import BytesParser
import getpass
import hashlib
import importlib.metadata
import json
from pathlib import Path
import resource
import shutil
import time
from urllib.parse import urlsplit

import httpx2
from typesafe_sdk import Image, Noul, RetryPolicy, TypeSafeClient


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='https://api.site')
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--base64-only',action='store_true',help='Use the documented extra_body option for JSON/base64 instead of Image multipart.')
    args=parser.parse_args()
    if urlsplit(args.base_url).scheme!='https': raise ValueError('HTTPS is required')
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    out=args.output; out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(__file__,out/Path(__file__).name)
    original=json.loads(args.request.read_text())
    images={ref:base64.b64decode(asset['data_base64'],validate=True) for ref,asset in original['assets'].items()}
    save(out/'environment.json',dict(base_url=args.base_url,model=original['model'],
         versions={name:importlib.metadata.version(name) for name in ('typesafe-sdk','httpx2','pydantic')},
         compression=False,retries=0,credentials_on_disk=False))
    key=getpass.getpass('JEV key: ')
    current={}

    def request_hook(request):
        body=request.read()
        if key.encode() in body: raise RuntimeError('Credential unexpectedly present in request body')
        folder=out/current['name']; folder.mkdir(exist_ok=True)
        (folder/'wire_body.bin').write_bytes(body)
        headers={name:request.headers[name] for name in ('content-type','content-length',
                 'typesafe-danger-zone-images','content-encoding','accept','user-agent') if name in request.headers}
        meta=dict(url=str(request.url),headers=headers,body_bytes=len(body),body_sha256=digest(body))
        content_type=request.headers.get('content-type','')
        if content_type.startswith('multipart/form-data'):
            message=BytesParser(policy=policy.default).parsebytes(
                ('Content-Type: '+content_type+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+body)
            parts=[]; document=None; image_hashes=[]
            for part in message.iter_parts():
                name=part.get_param('name',header='content-disposition'); data=part.get_payload(decode=True)
                parts.append(dict(name=name,content_type=part.get_content_type(),bytes=len(data),sha256=digest(data)))
                if name=='request': document=json.loads(data)
                else: image_hashes.append(digest(data))
            meta['parts']=parts
            meta['first_part_is_request']=bool(parts and parts[0]['name']=='request')
            meta['image_bytes_match_original']=sorted(image_hashes)==sorted(digest(b) for b in images.values())
            if document is not None:
                save(folder/'sdk_request.json',document)
                meta['same_model_state_questions']=all(document[k]==original[k] for k in ('model','state','questions'))
        elif content_type.startswith('application/json'):
            document=json.loads(body); save(folder/'sdk_request.json',document)
            if document.get('assets'):
                meta['same_model_state_questions']=all(document[k]==original[k] for k in ('model','state','questions'))
                image_hashes=[digest(base64.b64decode(a['data_base64'],validate=True)) for a in document['assets'].values()]
                meta['image_bytes_match_original']=sorted(image_hashes)==sorted(digest(b) for b in images.values())
                meta['entire_json_matches_original']=document==original
        save(folder/'request_audit.json',meta)
        current['request']=meta

    def response_hook(response):
        body=response.read().decode('utf-8',errors='replace').replace(key,'[REDACTED]')
        result=dict(status=response.status_code,body=body,request_id=response.headers.get('x-request-id'))
        save(out/current['name']/'response.json',result)
        current['response']=result

    transport=httpx2.Client(timeout=60,trust_env=False,follow_redirects=False,
                            event_hooks={'request':[request_hook],'response':[response_hook]})
    results=[]
    with TypeSafeClient(api_key=key,base_url=args.base_url,model=original['model'],
                        headers={'TypeSafe-Danger-Zone-Images':'true'},compression=False,
                        retry=RetryPolicy(max_retries=0),http_client=transport) as client:
        probes=[('text_control',dict(state='The status is ready.',questions={
                    'ready':Noul(instructions='Is the status ready?')})),
                ('historical_three_images',dict(state=original['state'],questions=original['questions'],
                    assets={ref:Image(data) for ref,data in images.items()}))]
        if args.base64_only:
            probes=[('historical_three_images_base64',dict(state=original['state'],questions=original['questions'],
                     extra_body={'assets':original['assets']}))]
        for name,kwargs in probes:
            current.clear(); current['name']=name; started=time.time()
            print('SDK_PROBE '+name,flush=True)
            try:
                answer=client.system_one(**kwargs)
                save(out/name/'answer.json',answer.model_dump(mode='json'))
                result=dict(name=name,valid_answer=True)
            except Exception as error:
                result=dict(name=name,valid_answer=False,error_type=type(error).__name__,
                            error=str(error).replace(key,'[REDACTED]'))
            result.update(seconds=time.time()-started,http_status=current.get('response',{}).get('status'),
                          content_type=current.get('request',{}).get('headers',{}).get('content-type'))
            results.append(result); save(out/'results.json',results)
            print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__': main()
