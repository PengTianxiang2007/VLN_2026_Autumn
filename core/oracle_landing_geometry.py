"""Advisory checks of a computed landing against frozen CPU USD projections.

No scene crossing candidates are read. This evidence never chooses a branch,
changes a target, vetoes an intervention or certifies simulator collision safety.
"""
import hashlib
import json
import math
from pathlib import Path
import shutil

import numpy as np

MODE = 'audit_only'
LAYERS = ('floor', 'wall', 'furniture', 'doors', 'safe', 'distance')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class SceneLandingGeometry:
    def __init__(self, metadata, masks):
        self.metadata = metadata
        if metadata['up_axis'] != 'Z' or metadata['units'] != 'meters':
            raise ValueError('Expected world XY in meters with Z up')
        self.resolution = float(metadata['resolution'])
        self.clearance = float(metadata['clearance_m'])
        if not math.isfinite(self.resolution) or self.resolution <= 0:
            raise ValueError('Invalid raster resolution')
        if not math.isfinite(self.clearance) or self.clearance <= 0:
            raise ValueError('Invalid approximate clearance')
        self.width, self.height = metadata['width'], metadata['height']
        self.masks = {key: np.array(masks[key], copy=True) for key in LAYERS}
        if any(a.shape != (self.height, self.width) for a in self.masks.values()):
            raise ValueError('Geometry shape mismatch')
        if not np.isfinite(self.masks['distance']).all() or (self.masks['distance'] < 0).any():
            raise ValueError('Invalid projected obstacle distance')

    @classmethod
    def load(cls, metadata_path, masks_path):
        with np.load(masks_path, allow_pickle=False) as masks:
            return cls(json.loads(Path(metadata_path).read_text()), masks)

    @classmethod
    def from_manifest(cls, config, scene):
        if config['mode'] != MODE:
            raise ValueError('Geometry audit cannot modify the correction protocol')
        root = Path(config['root'])
        entry = config['scenes'][scene]
        for name in ('metadata', 'masks'):
            relative = entry[name]
            if digest(root / relative) != config['files_sha256'][relative]:
                raise RuntimeError('Frozen geometry changed: ' + relative)
        result = cls.load(root / entry['metadata'], root / entry['masks'])
        if result.metadata['scene'] != scene:
            raise ValueError('Geometry scene identity mismatch')
        return result

    def check_xy(self, point):
        x, y = map(float, point[:2])
        if not all(map(math.isfinite, [x, y])):
            raise ValueError('Nonfinite landing coordinate')
        u = int(round((x-self.metadata['low'][0])/self.resolution))
        v = int(round((self.metadata['high'][1]-y)/self.resolution))
        inside = 0 <= u < self.width and 0 <= v < self.height
        result = dict(xy=[x, y], pixel=[u, v], inside_raster=inside)
        if not inside:
            return dict(result, assessment='outside_map', on_projected_floor=None,
                        overlapping_layers=[], projected_clearance_m=None, in_approximate_safe_mask=False)
        floor = bool(self.masks['floor'][v, u])
        overlap = [key for key in ('wall', 'furniture', 'doors') if self.masks[key][v, u]]
        distance = float(self.masks['distance'][v, u])
        safe = bool(self.masks['safe'][v, u])
        if not floor:
            assessment = 'off_projected_floor'
        elif overlap:
            assessment = 'projected_obstacle_overlap'
        elif distance < self.clearance:
            assessment = 'low_projected_clearance'
        elif not safe:
            assessment = 'excluded_small_free_component'
        else:
            assessment = 'clear_in_projection'
        return dict(result, assessment=assessment, on_projected_floor=floor,
                    overlapping_layers=overlap, projected_clearance_m=distance,
                    in_approximate_safe_mask=safe)

    def check_target(self, target):
        point = target['target_xy']
        yaw = float(target['target_yaw_rad'])
        if not math.isfinite(yaw):
            raise ValueError('Nonfinite landing heading')
        # These are diagnostic samples in the chosen heading, not a commanded
        # action or a substitute reference route, especially around corners.
        forward = [[point[0]+d*math.cos(yaw), point[1]+d*math.sin(yaw)] for d in (.125, .25)]
        return dict(mode=MODE, scene=self.metadata['scene'], target=self.check_xy(point),
                    heading_probe_distances_m=[.125, .25], heading_probes=[self.check_xy(p) for p in forward],
                    body_height_band_m=self.metadata['body_height_band'],
                    approximate_clearance_m=self.clearance, raster_resolution_m=self.resolution,
                    target_modified=False, intervention_vetoed=False, collision_certified=False)


def freeze_scene_geometry(source_root, scenes, destination):
    source_root, destination = Path(source_root).resolve(), Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    entries, hashes, sources = {}, {}, {}
    for scene in sorted(set(scenes)):
        if Path(scene).name != scene:
            raise ValueError('Invalid scene ID')
        src = source_root / 'scenes' / scene
        audit = SceneLandingGeometry.load(src/'geometry.json', src/'map_masks.npz')
        if audit.metadata['scene'] != scene:
            raise ValueError('Geometry scene identity mismatch')
        (destination / scene).mkdir()
        entry = {}
        for name, filename in [('metadata', 'geometry.json'), ('masks', 'map_masks.npz')]:
            path = src / filename
            relative = scene + '/' + filename
            expected = digest(path)
            shutil.copy2(path, destination / relative)
            if digest(destination / relative) != expected:
                raise RuntimeError('Geometry changed while freezing')
            hashes[relative] = expected
            sources[str(path)] = expected
            entry[name] = relative
        entries[scene] = entry
    return dict(mode=MODE, root=str(destination), scenes=entries, files_sha256=hashes,
                source_sha256=sources, static_crossing_annotations_used=False,
                interpretation='Visible USD mesh projection, advisory only; does not change targets or triggers.')
