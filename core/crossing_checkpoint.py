"""Causal visual crossing detection and map-only evaluation of completed trajectories.

The detector takes no positions, maps, reference paths, outcome labels or future actions.
Map access is confined to the evaluator after the prediction log has been written.
"""
from collections import deque
import copy
import hashlib
import json
import math


PROMPT_VERSION = 'crossing-v1-schema2'
SYSTEM_PROMPT = """You observe a walking robot's indoor navigation, one action at a time.
Your ONLY task is to detect route-choice locations (crossings) and describe the observable choices.
A crossing is a compact decision area where, EXCLUDING the route the robot arrived from,
at least TWO distinct, physically plausible onward routes are available. A route may be
straight along a corridor, a side corridor, or an open doorway into another room. A room
with multiple exits may contain a crossing. Do not count a single corridor, a forced bend,
a doorway with only one onward route, tiny furniture gaps, mirrors, or closed doors.
A large furniture obstacle CAN form a crossing when it splits the walking space into
two distinct, visibly traversable onward passages; merely seeing different sides of
an object does not establish two routes. Do not invent exits hidden outside observed views.

Images are labelled with navigation-action indices and ordered from past to current. The
last image is the current observation BEFORE the next action. Listed actions have ALREADY
been executed. Past views can establish the incoming route or a temporarily occluded exit,
but an exit already passed is not a choice at the current location. The camera turns with
the robot: interpret left/front/right in the CURRENT view. If evidence is insufficient,
say uncertain. The first frame has no established incoming route; explicitly acknowledge it.

Distinguish a crossing HERE (the robot is at a location where it can choose routes), AHEAD
(visible but not reached), and BEHIND (already passed). Keep tracking the same physical
decision area through turns. Compare against the active visual record, if supplied. A
different view of the same junction is not a new crossing. Only mark same_place=no when
the observations support a different location.

Do not judge instruction progress, navigation success or route correctness. Do not propose
movement, correction or recovery. Return ONLY a JSON object matching the requested schema.
Use concise Chinese descriptions; enum values remain English. List concrete visual evidence
for each route, and cite only image indices actually provided in this request.
"""

RESPONSE_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'properties': {
        'status': {'type': 'string', 'enum': ['crossing', 'not_crossing', 'uncertain']},
        'location': {'type': 'string', 'enum': ['here', 'ahead', 'behind', 'unknown']},
        'same_place': {'type': 'string', 'enum': ['yes', 'no', 'uncertain', 'no_active_record']},
        'confidence': {'type': 'string', 'enum': ['high', 'medium', 'low']},
        'incoming_route': {'type': 'string'},
        'description': {'type': 'string'},
        'reason': {'type': 'string'},
        'evidence_frames': {'type': 'array', 'items': {'type': 'integer'}, 'minItems': 0, 'maxItems': 8},
        'branches': {'type': 'array', 'minItems': 0, 'maxItems': 6, 'items': {
            'type': 'object', 'additionalProperties': False,
            'properties': {
                'direction': {'type': 'string', 'enum': ['left', 'front', 'right', 'back_left', 'back_right', 'unknown']},
                'landmark': {'type': 'string'}, 'evidence_frame': {'type': 'integer'}},
            'required': ['direction', 'landmark', 'evidence_frame']}}},
    'required': ['status', 'location', 'same_place', 'confidence', 'incoming_route',
                 'description', 'reason', 'evidence_frames', 'branches']}


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def action_name(action):
    if 'stop' in action:
        return 'STOP'
    code = (action.get('move_by_discrete') or action.get('move_by_flash') or [-1])[0]
    return {0: 'STOP', 1: 'FORWARD', 2: 'LEFT', 3: 'RIGHT'}.get(code, 'UNKNOWN')


def select_history(current, available, limit=8):
    """Sample only already observed frames. Most context remains near the decision."""
    valid = [i for i in available if i <= current]
    if not valid or valid[-1] != current:
        raise ValueError('Current observation is missing or out of order')
    # The first version deliberately keeps every one of the last eight observations.
    return valid[-limit:]


def response_schema(image_ids):
    """Constrain evidence to images in this request, including after the window slides.

    Visual memory may mention an older frame. That is not permission to present it as
    directly inspected evidence in the current answer. Keep the local validator too.
    """
    ids = list(image_ids)
    if not ids or any(type(i) is not int or i < 0 for i in ids) or ids != sorted(set(ids)):
        raise ValueError('Evidence image IDs must be nonempty, unique and chronological')
    schema = copy.deepcopy(RESPONSE_SCHEMA)
    schema['properties']['evidence_frames']['items']['enum'] = ids
    schema['properties']['branches']['items']['properties']['evidence_frame']['enum'] = ids
    return schema


def build_messages(images, executed_actions, active=None):
    """images: [{frame, data_url, sha256}], actions: [{index, name}] strictly before current."""
    if not images:
        raise ValueError('No current RGB')
    ids = [im['frame'] for im in images]
    if ids != sorted(set(ids)):
        raise ValueError('Image history is not strictly chronological')
    current = ids[-1]
    if any(a['index'] >= current for a in executed_actions):
        raise ValueError('Current or future action leaked into model request')
    text = dict(current_observation=current, executed_actions=executed_actions,
                active_visual_record=active,
                first_observation=current == 0)
    content = [{'type': 'text', 'text': json.dumps(text, ensure_ascii=False)}]
    for im in images:
        content.append({'type': 'text', 'text': f"Observation {im['frame']}"})
        content.append({'type': 'image_url', 'image_url': {'url': im['data_url']}})
    content.append({'type': 'text', 'text': 'Output JSON with this schema: ' + json.dumps(response_schema(ids))})
    return [{'role': 'system', 'content': SYSTEM_PROMPT}, {'role': 'user', 'content': content}]


def validate_response(value, image_ids):
    if not isinstance(value, dict) or set(value) != set(RESPONSE_SCHEMA['required']):
        raise ValueError('Response keys do not match the crossing schema')
    for key in ['status', 'location', 'same_place', 'confidence']:
        if value[key] not in RESPONSE_SCHEMA['properties'][key]['enum']:
            raise ValueError('Invalid enum: ' + key)
    for key in ['description', 'reason', 'incoming_route']:
        if not isinstance(value[key], str) or len(value[key]) > 3000:
            raise ValueError('Invalid description')
    evidence = value['evidence_frames']
    if not isinstance(evidence, list) or len(evidence) > 8 or any(type(i) is not int for i in evidence):
        raise ValueError('Evidence frames must be a list of at most eight integer IDs')
    if not set(evidence).issubset(set(image_ids)):
        raise ValueError(f'Response cites unseen evidence {sorted(set(evidence)-set(image_ids))}; supplied {image_ids}')
    if not isinstance(value['branches'], list) or len(value['branches']) > 6:
        raise ValueError('Invalid branches')
    for branch in value['branches']:
        if set(branch) != {'direction', 'landmark', 'evidence_frame'}:
            raise ValueError('Invalid branch keys')
        if branch['direction'] not in RESPONSE_SCHEMA['properties']['branches']['items']['properties']['direction']['enum']:
            raise ValueError('Invalid branch direction')
        if type(branch['evidence_frame']) is not int or branch['evidence_frame'] not in image_ids or not isinstance(branch['landmark'], str):
            raise ValueError('Branch cites unseen evidence')
    if value['status'] == 'crossing' and len(value['branches']) < 2:
        raise ValueError('Crossing requires at least two described onward choices')
    return value


class CheckpointTracker:
    """Visual-only state machine. Event confirmation time can never be backdated."""
    def __init__(self, confirmations=2, close_after=3):
        self.confirmations = confirmations
        self.close_after = close_after
        self.active = None
        self.events = []
        self.last_frame = -1
        self.next_id = 1
        self.recent = deque(maxlen=3)

    def prompt_memory(self):
        if self.active is None:
            return None
        return {k: copy.deepcopy(self.active[k]) for k in
                ['id', 'first_seen_frame', 'confirmation_frame', 'last_seen_frame',
                 'description', 'branches']}

    def close(self, frame, reason):
        if self.active:
            self.active.update(closed_frame=frame, close_reason=reason)
            self.events.append(copy.deepcopy(self.active))
            self.active = None
        self.recent.clear()

    def update(self, frame, observation):
        if frame <= self.last_frame:
            raise ValueError('Cannot replay a future result backward in time')
        self.last_frame = frame
        present = observation['status'] == 'crossing' and observation['location'] in ['here', 'ahead']
        eligible = present and observation['location'] == 'here' and observation['confidence'] != 'low'
        if present and self.active and observation['same_place'] == 'no':
            self.close(frame, 'different_visual_location')
        if present and self.active is None:
            self.active = dict(id=f'P{self.next_id:03d}', first_seen_frame=frame,
                               confirmation_frame=None, last_seen_frame=frame,
                               description=observation['description'], branches=observation['branches'],
                               evidence_frames=[], observation_frames=[], absent=0)
            self.next_id += 1
        self.recent.append((frame, eligible))
        emitted = None
        if self.active:
            if present:
                self.active.update(last_seen_frame=frame, absent=0,
                                   description=observation['description'], branches=observation['branches'])
                self.active['observation_frames'].append(frame)
                self.active['evidence_frames'] = sorted(set(self.active['evidence_frames']) |
                                                       set(observation['evidence_frames']))
                if eligible and self.active['confirmation_frame'] is None:
                    if sum(ok for _, ok in self.recent) >= self.confirmations:
                        self.active['confirmation_frame'] = frame
                        self.active['confirmation_observation'] = copy.deepcopy(observation)
                        emitted = copy.deepcopy(self.active)
            else:
                self.active['absent'] += 1
                if self.active['absent'] >= self.close_after:
                    self.close(frame, 'left_visual_decision_area')
        return emitted

    def finish(self):
        self.close(self.last_frame, 'end_of_recording')
        return copy.deepcopy(self.events)


def map_encounters(steps, crossings, entry_radius=.7, exit_radius=1.2, approach_radius=1.5):
    """Evaluation-only proximity visits; not visibility-certified ground truth."""
    valid = [s for s in steps if not s['terminal'] and s['position'] is not None]
    result = []
    for crossing in crossings:
        distances = [math.dist(s['position'][:2], crossing['position']) for s in valid]
        i = 0
        visit = 0
        while i < len(valid):
            if distances[i] > entry_radius:
                i += 1
                continue
            start = i
            while i + 1 < len(valid) and distances[i + 1] <= exit_radius:
                i += 1
            end = i
            closest = min(range(start, end + 1), key=distances.__getitem__)
            approach = start
            while approach > 0 and distances[approach - 1] <= approach_radius:
                approach -= 1
            visit += 1
            result.append(dict(id=f"{crossing['id']}:visit{visit}", crossing_id=crossing['id'],
                               approach_frame=valid[approach]['frame'], entry_frame=valid[start]['frame'],
                               closest_frame=valid[closest]['frame'], exit_frame=valid[end]['frame'],
                               min_distance_m=distances[closest], position=crossing['position'],
                               branch_count=crossing.get('branch_count'), visibility='not_manually_certified'))
            i += 1
    return sorted(result, key=lambda e: (e['entry_frame'], e['crossing_id']))


def evaluate_events(events, steps, encounters, radius=1.0):
    """Maximum-cardinality one-to-one matching; extra detections remain false positives."""
    positions = {s['frame']: s['position'] for s in steps}
    predicted = [e for e in events if e['confirmation_frame'] is not None]
    candidates = {}
    for i, event in enumerate(predicted):
        frame = event['confirmation_frame']
        p = positions.get(frame)
        ranked = []
        if p is not None:
            for j, reference in enumerate(encounters):
                distance = math.dist(p[:2], reference['position'])
                if (reference['approach_frame'] <= frame <= reference['exit_frame'] and distance <= radius):
                    ranked.append((distance, abs(frame-reference['closest_frame']), j))
        candidates[i] = [j for _, _, j in sorted(ranked)]
    matched_reference = {}

    def augment(i, seen):
        for j in candidates[i]:
            if j in seen:
                continue
            seen.add(j)
            if j not in matched_reference or augment(matched_reference[j], seen):
                matched_reference[j] = i
                return True
        return False

    for i in sorted(candidates, key=lambda k: (len(candidates[k]), predicted[k]['confirmation_frame'])):
        augment(i, set())
    by_prediction = {i: j for j, i in matched_reference.items()}
    details = []
    for i, event in enumerate(predicted):
        record = dict(prediction_id=event['id'], frame=event['confirmation_frame'],
                      label='matched' if i in by_prediction else 'unmatched_prediction',
                      candidate_encounters=[encounters[j]['id'] for j in candidates[i]])
        if i in by_prediction:
            ref = encounters[by_prediction[i]]
            record.update(encounter_id=ref['id'], crossing_id=ref['crossing_id'],
                          distance_m=math.dist(positions[record['frame']][:2], ref['position']),
                          actions_relative_to_closest=record['frame']-ref['closest_frame'],
                          at_or_before_closest=record['frame'] <= ref['closest_frame'])
        elif candidates[i]:
            record['label'] = 'duplicate_prediction'
        details.append(record)
    tp = len(matched_reference)
    fp = len(predicted)-tp
    fn = len(encounters)-tp
    precision = tp / (tp+fp) if tp+fp else None
    recall = tp / (tp+fn) if tp+fn else None
    return dict(radius_m=radius, tp=tp, fp=fp, fn=fn, precision=precision, recall=recall,
                f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
                duplicate_predictions=sum(d['label']=='duplicate_prediction' for d in details),
                confirmed_predictions=len(predicted), unconfirmed_candidates=len(events)-len(predicted),
                reference_encounters=len(encounters), predictions=details,
                missed_encounters=[e['id'] for j,e in enumerate(encounters) if j not in matched_reference],
                interpretation='Agreement with fixed map proximity events, not visibility-certified detection accuracy.')
