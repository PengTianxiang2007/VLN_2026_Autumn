"""Reference-route Oracle without annotated crossings; geometry only, no GPU."""
import copy
import math

from core.oracle_distance import positive, project_reference, route_segments, xy

PROTOCOL = 'auto_route_oracle_v001'


def automatic_target(position, reference, offset_m=1.25):
    """Project the current pose, then advance by arc length along the reference.

    Equal-distance overlaps keep the first reference occurrence, as in the
    original distance calculation. This is not a semantic progress estimator.
    """
    offset = positive(offset_m, 'landing offset')
    projection = project_reference(position, reference)
    segments = list(route_segments(reference))
    if not segments:
        raise ValueError('Cannot derive heading from a zero-length reference route')
    total = segments[-1][2] + segments[-1][3]
    arc = min(total, projection['arc_m'] + offset)
    for i, (a, b, start, length) in enumerate(segments):
        if arc < start + length - 1e-9 or i == len(segments) - 1:
            fraction = min(1., max(0., (arc - start) / length))
            point = [a[k] + fraction * (b[k] - a[k]) for k in (0, 1)]
            actual = arc - projection['arc_m']
            goal_distance = math.dist(point, xy(reference[-1]))
            return dict(source='current_pose_reference_projection',
                        source_position_xy=xy(position),
                        projection_xy=projection['point'],
                        projection_distance_m=projection['distance_m'],
                        projection_reference_arc_m=projection['arc_m'],
                        target_xy=point,
                        target_yaw_rad=math.atan2(b[1]-a[1], b[0]-a[0]),
                        reference_arc_m=arc, reference_length_m=total,
                        requested_offset_m=offset, actual_offset_m=actual,
                        clamped_to_route_end=actual < offset - 1e-9,
                        planned_goal_distance_m=goal_distance, near_goal_3m=goal_distance < 3.)
    raise RuntimeError('Reference interpolation failed')


class AutoRouteTrigger:
    """Track geometric excursions; recompute the target on every current pose."""
    def __init__(self, case, threshold_m=.75, offset_m=1.25):
        self.reference = case['reference_path']
        self.threshold = positive(threshold_m, 'threshold')
        self.offset = positive(offset_m, 'landing offset')
        automatic_target(self.reference[0], self.reference, self.offset)
        self.serial = 0
        self.event = None

    def update(self, position, action_index):
        projection = project_reference(position, self.reference)
        distance = projection['distance_m']
        target = None
        if distance < self.threshold:
            self.event = None
        else:
            if self.event is None:
                self.serial += 1
                self.event = dict(excursion=self.serial,
                                  target_id='auto_excursion_%06d' % self.serial,
                                  onset_action_index=action_index,
                                  onset_distance_m=distance)
            target = automatic_target(position, self.reference, self.offset)
            target.update(id=self.event['target_id'], computed_at_action_index=action_index)
        return dict(distance_m=distance, threshold_reached=distance >= self.threshold,
                    event=dict(self.event) if self.event else None, target=target)


def build_auto_cohort(episodes, episode_ids, seed=2):
    """Use only official task fields. No historical outcomes or crossing labels."""
    if type(seed) is not int or not 0 <= seed < 2**31:
        raise ValueError('Invalid seed')
    if not episode_ids or any(not isinstance(e, str) or not e for e in episode_ids):
        raise ValueError('Expected a nonempty episode-ID list')
    if len(set(episode_ids)) != len(episode_ids):
        raise ValueError('Duplicate requested episode IDs')
    official = {e['episode_id']: e for e in episodes}
    if len(official) != len(episodes):
        raise ValueError('Duplicate official episode IDs')
    unknown = set(episode_ids) - set(official)
    if unknown:
        raise ValueError('Unknown episode IDs: ' + ', '.join(sorted(unknown)))
    # The native launcher preserves official split order; both arms use it.
    selected = set(episode_ids)
    cases = []
    for episode in episodes:
        if episode['episode_id'] not in selected:
            continue
        reference = episode['reference_path']
        if not reference:
            raise ValueError('Empty reference route: ' + episode['episode_id'])
        automatic_target(reference[0], reference)
        instruction = episode['instruction']['instruction_text']
        if not isinstance(instruction, str) or not instruction.strip():
            raise ValueError('Missing official instruction')
        cases.append(dict(episode_id=episode['episode_id'], scene=episode['scan'],
                          instruction=instruction, seed=seed,
                          reference_path=copy.deepcopy(reference)))
    return dict(schema=1, protocol=PROTOCOL, episodes=len(cases), events=0,
                event_scope='No annotated events; runtime excursions are recorded separately.',
                cases=cases, annotation_required=False)
