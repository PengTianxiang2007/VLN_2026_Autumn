"""Publish the complete, validated DeepSeek RxR static export."""
import json
from pathlib import Path
import sys
folder=Path("outputs/deviation_progress/rxr30_v006/run_20261123_03_mistral30/exports/full_20261123_01")
manifest=json.loads((folder/"online_manifest.json").read_text())
sys.path.insert(0,str(Path("scripts").resolve()))
import publish_visualization
sys.argv=["publish_visualization","--html",str(folder/manifest["html"]),"--name","rxr30_deepseek_full_web_20261123_01"]
for asset in manifest["assets"]:
    sys.argv.extend(["--asset",asset])
publish_visualization.main()
