"""Causal divergence-point estimation from walked and reference trajectories.

No annotated crossings, future observations, simulator imports or model calls.
"""
import bisect
import copy
import math

from core.oracle_distance import positive, project_reference, route_segments, xy

PROTOCOL = 'auto_branch_oracle_v001'
DEFAULTS = dict(shared_distance_m=.35, fit_window_m=8., resample_m=.05,
                min_motion_m=.03, min_fit_span_m=.5, min_tail_m=.3,
                max_fit_rmse_m=.12, projection_slack_m=.1,
                projection_motion_factor=1.5, min_departure_slope=.05)


def validate_settings(settings, threshold_m=.75):
    if set(settings) != set(DEFAULTS):
        raise ValueError('Unexpected branch estimator settings')
    config = {k: positive(v, k) for k, v in settings.items()}
    if not (config['shared_distance_m'] < positive(threshold_m, 'threshold') and
            config['resample_m'] < config['min_fit_span_m'] <= config['fit_window_m'] and
            config['min_tail_m'] <= config['min_fit_span_m'] and
            config['min_departure_slope'] < 1.25):
        raise ValueError('Inconsistent branch estimator settings')
    return config


class ReferenceGeometry:
    def __init__(self, reference):
        self.reference = reference
        self.segments = list(route_segments(reference))
        if not self.segments:
            raise ValueError('Reference route needs a nonzero horizontal segment')
        self.length = self.segments[-1][2] + self.segments[-1][3]

    def at(self, arc):
        if not math.isfinite(arc) or not 0 <= arc <= self.length + 1e-8:
            raise ValueError('Reference arc outside route')
        for i, (a, b, start, length) in enumerate(self.segments):
            if arc < start + length - 1e-9 or i == len(self.segments)-1:
                t = min(1., max(0., (arc-start)/length))
                return [a[k]+t*(b[k]-a[k]) for k in (0, 1)], math.atan2(b[1]-a[1], b[0]-a[0])
        raise RuntimeError('Missing reference interpolation')

    def project(self, position, previous_arc, reach):
        p = xy(position)
        lo, hi = max(0., previous_arc-reach), min(self.length, previous_arc+reach)
        candidates = []
        for a, b, start, length in self.segments:
            left, right = max(lo, start), min(hi, start+length)
            if left > right:
                continue
            delta = [b[k]-a[k] for k in (0, 1)]
            fraction = sum((p[k]-a[k])*delta[k] for k in (0, 1))/length**2
            arc = min(right, max(left, start+fraction*length))
            point = [a[k]+(arc-start)/length*delta[k] for k in (0, 1)]
            candidates.append(dict(point=point, arc_m=arc, distance_m=math.dist(p, point)))
        if not candidates:
            raise RuntimeError('Empty continuous reference projection interval')
        # Round only the comparison key: preserve exact output coordinates.
        return min(candidates, key=lambda c: (round(c['distance_m'], 10),
                                              abs(c['arc_m']-previous_arc), c['arc_m']))

    def landing(self, branch_arc, offset):
        offset = positive(offset, 'landing offset')
        anchor, _ = self.at(branch_arc)
        arc = min(self.length, branch_arc+offset)
        point, yaw = self.at(arc)
        actual = arc-branch_arc
        goal_distance = math.dist(point, xy(self.reference[-1]))
        return dict(source='walked_reference_divergence', branch_xy=anchor,
                    branch_reference_arc_m=branch_arc, target_xy=point, target_yaw_rad=yaw,
                    reference_arc_m=arc, reference_length_m=self.length,
                    requested_offset_m=offset, actual_offset_m=actual,
                    clamped_to_route_end=actual < offset-1e-9,
                    planned_goal_distance_m=goal_distance, near_goal_3m=goal_distance < 3.)


def interpolate_history(history, distance):
    index = bisect.bisect_right([r['s'] for r in history], distance)
    if index == 0:
        return copy.deepcopy(history[0])
    if index >= len(history):
        return copy.deepcopy(history[-1])
    a, b = history[index-1], history[index]
    fraction = (distance-a['s'])/(b['s']-a['s'])
    return dict(s=distance,
                position=[a['position'][k]+fraction*(b['position'][k]-a['position'][k]) for k in (0, 1)],
                arc=a['arc']+fraction*(b['arc']-a['arc']),
                distance=a['distance']+fraction*(b['distance']-a['distance']),
                action_index=a['action_index']+fraction*(b['action_index']-a['action_index']),
                action_interval=[a['action_index'], b['action_index']])


def estimate_branch(history, geometry, config):
    if len(history) < 3:
        return None, 'insufficient_motion_observations'
    end = history[-1]['s']
    start = max(history[0]['s'], end-config['fit_window_m'])
    if sum(start <= r['s'] <= end for r in history) < 3:
        return None, 'insufficient_motion_observations_in_window'
    if end-start < config['min_fit_span_m']:
        return None, 'insufficient_walked_span'
    count = int(math.ceil((end-start)/config['resample_m']))
    samples = [interpolate_history(history, start+(end-start)*i/count) for i in range(count+1)]
    if not any(r['distance'] <= config['shared_distance_m'] for r in samples):
        return None, 'no_shared_route_prefix_in_window'
    xs = [r['s']-start for r in samples]
    ys = [r['distance'] for r in samples]
    n, sy, syy = len(xs), sum(ys), sum(y*y for y in ys)
    candidates = []
    for z in xs:
        if xs[-1]-z < config['min_tail_m']:
            continue
        if not any(x <= z+1e-9 and y <= config['shared_distance_m'] for x, y in zip(xs, ys)):
            continue
        hs = [max(0., x-z) for x in xs]
        sh, shh, shy = sum(hs), sum(h*h for h in hs), sum(h*y for h, y in zip(hs, ys))
        if shh <= 1e-12:
            continue
        low, high, bmax = config['min_departure_slope'], 1.25, config['shared_distance_m']
        clip_k = lambda value: min(high, max(low, value))
        clip_b = lambda value: min(bmax, max(0., value))
        fits = [(b, clip_k((shy-b*sh)/shh)) for b in (0., bmax)]
        fits += [(clip_b((sy-k*sh)/n), k) for k in (low, high)]
        den = n*shh-sh*sh
        if den > 1e-12:
            k = (n*shy-sh*sy)/den
            b = (sy-k*sh)/n
            if low <= k <= high and 0 <= b <= bmax:
                fits.append((b, k))
        for b, k in fits:
            loss = max(0., syy+n*b*b+k*k*shh+2*b*k*sh-2*b*sy-2*k*shy)
            candidates.append((loss, z, b, k))
    if not candidates:
        return None, 'no_supported_change_point'
    loss, z, baseline, slope = min(candidates)
    rmse = math.sqrt(loss/n)
    if rmse > config['max_fit_rmse_m']:
        return None, 'divergence_fit_residual_too_large'
    if start > history[0]['s']+1e-8 and z <= config['resample_m']:
        return None, 'branch_outside_history_window'
    row = interpolate_history(history, start+z)
    anchor, _ = geometry.at(row['arc'])
    if math.dist(anchor, row['position']) > config['shared_distance_m']+config['max_fit_rmse_m']:
        return None, 'estimated_branch_not_on_shared_prefix'
    return dict(reference_arc_m=row['arc'], reference_xy=anchor,
                walked_xy=row['position'], walked_arc_m=row['s'],
                estimated_action_index=row['action_index'],
                action_interval=row.get('action_interval', [row['action_index'], row['action_index']]),
                fit_rmse_m=rmse, fitted_prefix_offset_m=baseline, fitted_departure_slope=slope,
                fit_window_walked_arc_m=[start, end], resample_resolution_m=(end-start)/count,
                raw_motion_observations=sum(start <= r['s'] <= end for r in history),
                fit_samples=n, estimator='bounded_hinge_distance_v001'), None


class AutoBranchTrigger:
    def __init__(self, case, threshold_m=.75, offset_m=1.25, settings=None):
        self.reference = case['reference_path']
        self.geometry = ReferenceGeometry(self.reference)
        self.threshold = positive(threshold_m, 'threshold')
        self.offset = positive(offset_m, 'landing offset')
        self.config = validate_settings(DEFAULTS if settings is None else settings, self.threshold)
        self.history = []
        self.progress = 0.
        self.serial = 0
        self.segment = 0
        self.event = None
        self.was_away = False

    def _append(self, position, action_index):
        p = xy(position)
        motion = math.dist(p, self.history[-1]['position']) if self.history else math.dist(p, xy(self.reference[0]))
        if self.history and motion < self.config['min_motion_m']:
            return self.geometry.project(p, self.progress, self.config['projection_slack_m'])
        reach = motion*self.config['projection_motion_factor']+self.config['projection_slack_m']
        projection = self.geometry.project(p, self.progress, reach)
        total = self.history[-1]['s']+motion if self.history else 0.
        self.progress = projection['arc_m']
        self.history.append(dict(s=total, position=p, arc=self.progress,
                                 distance=projection['distance_m'], action_index=action_index))
        return projection

    def update(self, position, action_index):
        distance = project_reference(position, self.reference)['distance_m']
        projection = self._append(position, action_index)
        relocalized = False
        if self.was_away and distance <= self.config['shared_distance_m']:
            if projection['distance_m'] > self.config['shared_distance_m']:
                # A detour can rejoin a different part of the reference without
                # traversing its intervening arc. End the old excursion and
                # record an explicit correspondence reset, not a walked jump.
                projection = self.geometry.project(position, self.progress, self.geometry.length)
                relocalized = True
            self.event = None
            self.was_away = False
            self.segment += 1
            self.history = [dict(s=0., position=xy(position), arc=projection['arc_m'],
                                 distance=projection['distance_m'], action_index=action_index)]
            self.progress = projection['arc_m']
        target = None
        reason = None
        if distance >= self.threshold:
            self.was_away = True
            if self.event is None:
                branch, reason = estimate_branch(self.history, self.geometry, self.config)
                if branch is not None:
                    self.serial += 1
                    self.event = dict(excursion=self.serial, target_id='auto_branch_%06d' % self.serial,
                                      onset_action_index=action_index, onset_distance_m=distance,
                                      history_segment=self.segment, branch=branch)
            if self.event is not None:
                target = self.geometry.landing(self.event['branch']['reference_arc_m'], self.offset)
                target.update(id=self.event['target_id'], computed_at_action_index=action_index,
                              branch_evidence=copy.deepcopy(self.event['branch']))
        return dict(distance_m=distance, matched_reference_distance_m=projection['distance_m'],
                    matched_reference_arc_m=projection['arc_m'], threshold_reached=distance >= self.threshold,
                    event=copy.deepcopy(self.event), target=target,
                    branch_unresolved_reason=reason, history_segment=self.segment,
                    reference_relocalized_on_rejoin=relocalized)

    def after_correction(self, position, action_index, target):
        """A teleport is a new trajectory origin, never a walked history segment."""
        self.segment += 1
        self.event = None
        self.was_away = False
        self.progress = target['reference_arc_m']
        projection = self.geometry.project(position, self.progress, .5)
        self.progress = projection['arc_m']
        self.history = [dict(s=0., position=xy(position), arc=self.progress,
                             distance=projection['distance_m'], action_index=action_index)]
