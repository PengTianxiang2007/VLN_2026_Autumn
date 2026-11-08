"""Deployment-only scene/robot USD check; no navigation or recovery score."""
import json, sys
from pathlib import Path
from isaacsim import SimulationApp
app = SimulationApp(dict(headless=True, multi_gpu=False, active_gpu=0, physics_gpu=0))
try:
    from isaacsim.core.api import World
    from isaacsim.core.utils.stage import add_reference_to_stage
    resource = Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/VLNVerse')
    world = World(stage_units_in_meters=1.0)
    assets = [resource/'scenes/kujiale_0232/start_result_navigation.usd', resource/'Embodiments/vln-pe/h1/h1_vln_pointcloud.usd']
    for i, path in enumerate(assets):
        assert path.is_file(), str(path)
        prim = add_reference_to_stage(str(path), '/World/Asset'+str(i))
        assert prim.IsValid()
    for _ in range(30): app.update()
    Path(sys.argv[1]).write_text(json.dumps(dict(status='passed_asset_load', assets=list(map(str,assets)), navigation_executed=False, checkpoint_restored=False),indent=2))
finally:
    app.close()
