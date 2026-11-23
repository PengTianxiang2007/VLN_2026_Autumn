"""Compare the same JEV image body with/without the documented image header.

Curl's verbose output stays in memory. Only an allowlist of non-secret outgoing
headers is saved, never Authorization or full trace output.
"""
import argparse
import getpass
import hashlib
import json
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
from urllib.parse import urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.serial_pipeline import save
from core.jev_node import validate_noul_response


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--request', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--endpoint', default='https://api.site/v1/systemone')
    p.add_argument('--with-header-only', action='store_true')
    p.add_argument('--extra-request', type=Path)
    p.add_argument('--catalog', action='store_true', help='First query the same endpoint origin and API prefix for available JEV models.')
    a = p.parse_args()
    parsed = urlsplit(a.endpoint)
    if parsed.scheme != 'https' or not parsed.hostname or any(c in a.endpoint for c in '\r\n"\\'):
        raise ValueError('Expected an HTTPS inference endpoint')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    a.output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(__file__, a.output / 'probe_jev_header.py')
    body = a.request.read_bytes()
    assert json.loads(body)['assets'], 'Expected an actual image request'
    request_path = (a.output / 'request.json').resolve()
    request_path.write_bytes(body)
    key = getpass.getpass('JEV key: ')
    if any(c in key for c in '\r\n"\\'):
        raise ValueError('Unsupported key characters')
    if a.catalog:
        url=a.endpoint.rsplit('/',1)[0]+'/models'
        try:
            with httpx.Client(timeout=30,trust_env=False,follow_redirects=False) as client:
                response=client.get(url,headers={'Authorization':'Bearer '+key})
            data=response.json()
            rows=data.get('data',data.get('models',[]))
            matches=[r for r in rows if 'jev' in str(r).lower() or 'typesafe' in str(r).lower()]
            catalog=dict(endpoint=url,http_status=response.status_code,total_models=len(rows),jev_models=matches)
            if response.status_code!=200: catalog['error']=response.text.replace(key,'[REDACTED]')
        except Exception as error:
            catalog=dict(endpoint=url,error=str(error).replace(key,'[REDACTED]'))
        save(a.output/'catalog.json',catalog)
        print(json.dumps(catalog,ensure_ascii=False),flush=True)
    results = []
    paths=[a.request]+([a.extra_request] if a.extra_request else [])
    for request_number, source in enumerate(paths):
      body=source.read_bytes()
      assert json.loads(body)['assets'], 'Expected an actual image request'
      request_path=(a.output/('request_%02d.json'%request_number)).resolve()
      request_path.write_bytes(body)
      for enabled in ((True,) if a.with_header_only else (True, False)):
        config = [
            'url = "%s"' % a.endpoint,
            'request = "POST"',
            'header = "Authorization: Bearer %s"' % key,
            'header = "Content-Type: application/json"',
            'header = "Accept: application/json"',
            'data-binary = "@%s"' % request_path,
            'noproxy = "*"', 'http1.1', 'verbose', 'silent', 'show-error',
            'max-time = 60', 'write-out = "__JEV_STATUS__:%{http_code}"',
        ]
        # This is deliberately the only request difference.
        if enabled:
            config.append('header = "TypeSafe-Danger-Zone-Images: true"')
        started = time.time()
        result = subprocess.run(['curl', '--config', '-'], input='\n'.join(config)+'\n',
                                text=True, capture_output=True, timeout=75)
        allowed = ('> POST ', '> Host:', '> Content-Type:', '> Content-Length:',
                   '> TypeSafe-Danger-Zone-Images:')
        headers = [s.strip() for s in result.stderr.splitlines() if s.startswith(allowed)]
        sent = any(s == '> TypeSafe-Danger-Zone-Images: true' for s in headers)
        response, _, status = result.stdout.rpartition('__JEV_STATUS__:')
        row = dict(endpoint=a.endpoint,request_number=request_number,image_header_enabled=enabled, outgoing_headers=headers,
                   image_header_seen_in_curl_trace=sent, curl_exit=result.returncode,
                   status=status, response=response.replace(key, '[REDACTED]'),
                   request_sha256=hashlib.sha256(body).hexdigest(), seconds=time.time()-started)
        if status == '200':
            try: row['validated_answer']=validate_noul_response(json.loads(response))
            except (ValueError,KeyError,TypeError) as error: row['validation_error']=str(error).replace(key,'[REDACTED]')
        results.append(row)
        save(a.output/'results.json', results)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if result.returncode == 0 and sent != enabled:
            raise RuntimeError('Actual outgoing header differs from intended request')


if __name__ == '__main__':
    main()
