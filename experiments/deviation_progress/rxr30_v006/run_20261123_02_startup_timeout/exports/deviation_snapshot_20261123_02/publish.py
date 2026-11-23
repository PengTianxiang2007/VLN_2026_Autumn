"""Standard publication of this already-separated static export."""
import json
from pathlib import Path
import sys

folder = Path("outputs/deviation_progress/rxr30_v006/run_20261123_02_startup_timeout/exports/deviation_snapshot_20261123_02")
manifest = json.loads((folder / "online_manifest.json").read_text())
sys.path.insert(0, str(Path("scripts").resolve()))
import publish_visualization
sys.argv = ["publish_visualization", "--html", str(folder / manifest["html"]), "--name", "rxr30_deviation_snapshot_web_20261123_02"]
for asset in manifest["assets"]:
    sys.argv.extend(["--asset", asset])
publish_visualization.main()
