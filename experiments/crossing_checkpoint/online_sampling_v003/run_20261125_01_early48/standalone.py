"""Build a directly openable offline HTML from the relative-asset ZIP."""
import base64
import io
import json
from pathlib import Path
import re
import sys
import zipfile


def embed(dest):
    with zipfile.ZipFile(io.BytesIO((dest/'early48.zip').read_bytes())) as z:
        html=z.read('index.html').decode()
        m=re.search(r'<script id="payload" type="application/json">(.*?)</script>',html,re.S)
        bundle=json.loads(m[1])
        for key,path in list(bundle['images'].items()):
            mime='image/png' if path.endswith('.png') else 'image/webp'
            bundle['images'][key]='data:'+mime+';base64,'+base64.b64encode(z.read(path)).decode()
        data=json.dumps(bundle,ensure_ascii=False,separators=(',',':')).replace('</',r'<\/')
        tmp=dest/'standalone.tmp'
        tmp.write_text(html[:m.start(1)]+data+html[m.end(1):])
        tmp.replace(dest/'index.html')


if __name__=='__main__':embed(Path(sys.argv[1]))
