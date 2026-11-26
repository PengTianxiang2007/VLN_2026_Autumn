"""Add per-version metrics to the verified map viewer and existing online bundle."""
from pathlib import Path
import hashlib
import io
import json
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[5]
OUT=ROOT/'outputs/crossing_checkpoint/online_sampling_v003'/HERE.parents[1].name/'exports'
PUB=ROOT/'outputs/visualization_publishing'
PREVIOUS=PUB/'jev_sampling_astra_map_layers42_web_20261125_01'
DEST=PUB/'jev_sampling_astra_map_metrics42_web_20261125_01'


def transform(html):
    css="""<style>
#samplerMetrics{padding:12px clamp(12px,3vw,36px);background:white;margin:12px auto;color:#203345}
#samplerMetrics h2{margin:0;font-size:18px}#samplerMetrics p{margin:7px 0;font-size:13px}
.metricTitle{display:flex;align-items:center;gap:16px;flex-wrap:wrap}.metricScroll{overflow-x:auto}
#samplerMetrics table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}
#samplerMetrics td,#samplerMetrics th{padding:5px 12px;text-align:right;border-bottom:1px solid #dee5ec;white-space:nowrap}
#samplerMetrics th:first-child{text-align:left}#samplerMetrics thead{background:#edf3f7}
</style>"""
    hook='stop();renderCases();seek(index);\n}'
    for anchor in [hook,'</head>','</body>']:
        assert html.count(anchor)==1,anchor
    return html.replace(hook,hook.replace('\n}',"\n  if ($('samplerMetrics')) renderSamplerMetrics();\n}")).replace(
        '</head>',css+'</head>').replace('</body>','<script>'+ (HERE/'metrics.js').read_text()+'</script></body>')


def write_export(name, source_name, previous, destination, render):
    local=OUT/name
    local.mkdir(exist_ok=False)
    (local/'index.html').write_text(render((OUT/source_name/'index.html').read_text()))
    destination.mkdir(exist_ok=False)
    manifest=json.loads((previous/'online_manifest.json').read_text())
    # Read the verified old archive once. Each unchanged asset keeps its original bytes and hash.
    with zipfile.ZipFile(io.BytesIO((previous/'site.zip').read_bytes())) as old, zipfile.ZipFile(destination/'site.zip','x') as new:
        assert set(old.namelist())==set(manifest['assets'])|{'index.html'}
        for name in old.namelist():
            data=old.read(name)
            if name=='index.html':
                data=render(data.decode()).encode()
                manifest['html_sha256']=hashlib.sha256(data).hexdigest()
            new.writestr(name,data,zipfile.ZIP_DEFLATED if name=='index.html' else zipfile.ZIP_STORED)
    manifest['source']=str(local/'index.html')
    manifest['source_sha256']=hashlib.sha256((local/'index.html').read_bytes()).hexdigest()
    (destination/'online_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    write_export(HERE.name,'map_layers_20261125_01',PREVIOUS,DEST,transform)
