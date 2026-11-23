"""Live simulator-only distance Oracle. No human review files or remote VLM calls."""
import copy
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np

from core.oracle_crossing import OracleCrossing, plain, write
from core.oracle_checkpoint_pair import CheckpointPair
from core.oracle_distance import DistanceTrigger


class DistanceOracle(CheckpointPair):
    def rpc(self, operation, key):
        # A retained service outlives failed simulator attempts. Never overwrite
        # or accidentally restore a previous attempt's saved policy tensors.
        namespace = hashlib.sha256(str(self.case_root.resolve()).encode()).hexdigest()[:20]
        return super().rpc(operation, namespace + '_' + key)

    def __init__(self, evaluator):
        manifest = Path(os.environ['VLN_ORACLE_MANIFEST'])
        self.manifest = json.loads(manifest.read_text())
        OracleCrossing.__init__(self, manifest, os.environ['VLN_ORACLE_RECORDS'], evaluator.agent.base_url)
        self.arm = os.environ['VLN_DISTANCE_ARM']
        self.settings = self.manifest['arms'][self.arm]
        self.threshold = self.settings['threshold_m']
        self.branch_root = Path(os.environ['VLN_BRANCH_ROOT'])

    def begin(self, evaluator, eid):
        OracleCrossing.start(self, eid, evaluator)
        self.case_root = self.active['directory']
        self.mode = self.arm
        self.snapshots = {}
        self.checkpoints = {}
        self.event = None
        self.sequence = 0
        self.executed_actions = 0
        self.completed_interventions = []
        if self.settings['mode'] == 'auto_branch':
            from core.oracle_auto_branch import AutoBranchTrigger
            self.trigger = AutoBranchTrigger(self.cases[eid], self.threshold,
                                              self.settings['landing_offset_m'], self.settings['branch'])
        elif self.settings['mode'] == 'auto_route':
            from core.oracle_auto_route import AutoRouteTrigger
            self.trigger = AutoRouteTrigger(self.cases[eid], self.threshold,
                                            self.settings['landing_offset_m'])
        else:
            self.trigger = DistanceTrigger(self.cases[eid], self.threshold, self.manifest['onset_m'])
        self.maximum_distance = 0.0
        self.seen_events = set()
        self.landing_geometry = None
        if self.settings['mode'] == 'auto_branch' and self.manifest.get('landing_geometry_audit'):
            from core.oracle_landing_geometry import SceneLandingGeometry
            self.landing_geometry = SceneLandingGeometry.from_manifest(
                self.manifest['landing_geometry_audit'], self.cases[eid]['scene'])

    def append(self, filename, row):
        with (self.case_root / filename).open('a') as stream:
            stream.write(json.dumps(plain(row), ensure_ascii=False) + '\n')

    def observe(self, evaluator, ob, terminal=False):
        from PIL import Image
        frame = self.active['directory'] / 'frames' / ('%06d.jpg' % self.sequence)
        if ob.get('rgb') is not None:
            Image.fromarray(np.asarray(ob['rgb'], dtype=np.uint8)).save(frame, quality=90)
        decision = self.trigger.update(ob['globalgps'], self.active['index'])
        if getattr(self, 'landing_geometry', None) is not None and decision.get('target') is not None:
            decision['target']['scene_geometry_audit'] = self.landing_geometry.check_target(decision['target'])
        self.maximum_distance = max(self.maximum_distance, decision['distance_m'])
        row = dict(sequence=self.sequence, action_index=self.active['index'],
                   position=plain(ob['globalgps']), rotation=plain(ob['globalrotation']),
                   frame=str(frame), physics_ticks=self.task(evaluator).step_count,
                   terminal=terminal, **decision)
        self.sequence += 1
        self.active['observations'].append(row)
        self.append('observations.jsonl', row)
        return decision

    def automatic_review(self, evaluator, ob, decision):
        """Called after real observations, before requesting the next policy action."""
        task = self.task(evaluator)
        if task.is_done():
            return ob, True
        returning = self.settings['mode'] == 'checkpoint'
        if returning and self.completed_interventions:
            return ob, False  # Historical checkpoint arm: one return, then native policy.
        case = self.cases[self.active['episode_id']]
        nearby = []
        if returning and decision['distance_m'] < self.manifest['onset_m']:
            import math
            nearby = [t for t in case['targets'] if t['id'] not in self.checkpoints and
                      math.dist(ob['globalgps'][:2], t['crossing_position']) <= self.manifest['checkpoint_capture_radius_m']]
        if not nearby and not decision['threshold_reached']:
            return ob, False
        if self.settings['mode'] == 'auto_branch' and decision['target'] is None:
            self.append('skipped_triggers.jsonl', dict(
                reason=decision['branch_unresolved_reason'], action_index=self.active['index'],
                distance_m=decision['distance_m'], history_segment=decision['history_segment']))
            return ob, False
        policy = self.policy()
        if policy['episode_id'] != self.active['episode_id'] or policy['step_id'] != self.active['index']:
            raise RuntimeError('Policy/Oracle episode or action index mismatch')
        if policy['pending_count']:
            return ob, False  # Never discard or modify a generated action queue.
        for target in nearby:
            key = 'checkpoint_' + target['id']
            self.event = {'target_id': target['id'], 'reason': 'Actual live pose within fixed checkpoint capture radius.'}
            self.capture(evaluator, ob, key, self.event)
            self.checkpoints[target['id']] = self.snapshots[key]
            self.event = None
        if not decision['threshold_reached']:
            return ob, False
        event = decision['event']
        if self.settings['mode'] in ('auto_route', 'auto_branch'):
            target = decision['target']
            if target['computed_at_action_index'] != self.active['index']:
                raise RuntimeError('Automatic landing target is from a stale observation')
        else:
            target = next(t for t in case['targets'] if t['id'] == event['target_id'])
        self.seen_events.add(target['id'])
        if returning and target['id'] not in self.checkpoints:
            self.append('skipped_triggers.jsonl', dict(reason='no_live_checkpoint_for_event', **decision,
                                                     action_index=self.active['index']))
            return ob, False
        directory = self.case_root / ('correction_%03d' % (len(self.completed_interventions) + 1))
        directory.mkdir(exist_ok=False)
        request = dict(event=event, threshold_m=self.threshold, distance_m=decision['distance_m'],
                       action_index=self.active['index'], physics_ticks=task.step_count,
                       before_position=plain(ob['globalgps']), before_rotation=plain(ob['globalrotation']),
                       target=target, mode=self.settings['mode'])
        write(directory / 'trigger.json', request)
        if returning:
            self.checkpoint_path = self.checkpoints[target['id']]
            # Verified existing restore: saved policy/RNG/accounting/root pose + 50 ticks.
            result, ended = CheckpointPair.restore(self, evaluator, 'returned')
            request['restore_proof'] = str(self.active['directory'] / 'restore_proof.json')
            request['memory_rule'] = 'restore_checkpoint'
        else:
            before = self.policy(deep=True)
            result, ended = self.teleport(evaluator, ob, target, directory)
            after = self.policy(deep=True)
            if before['sha256'] != after['sha256']:
                raise RuntimeError('Simulator correction changed StreamVLN policy memory')
            write(directory / 'memory_proof.json', dict(before=before, after=after, equal=True))
            request['memory_rule'] = 'preserve_intervention_time'
        request.update(after_position=plain(result['globalgps']), after_rotation=plain(result['globalrotation']),
                       physics_ticks_after=task.step_count, terminal_during_stabilization=ended,
                       physics_settle_ticks_max=50, completed_at=time.time())
        write(directory / 'intervention.json', request)
        self.completed_interventions.append(request)
        self.active['interventions'] = self.completed_interventions
        self.active['intervention'] = self.completed_interventions[0]
        self.active['teleported'] = True
        write(self.case_root / 'interventions.json', self.completed_interventions)
        from PIL import Image
        if result.get('rgb') is not None:
            Image.fromarray(np.asarray(result['rgb'], dtype=np.uint8)).save(directory / 'after.jpg', quality=90)
        # Process the actual settled pose; do not fabricate a zero reference distance.
        if self.settings['mode'] == 'auto_branch':
            self.trigger.after_correction(result['globalgps'], self.active['index'], target)
        else:
            self.trigger.update(result['globalgps'], self.active['index'])
        print('DISTANCE_ORACLE_CORRECTED ' + json.dumps(plain(request)), flush=True)
        return result, ended

    def record_action(self, action):
        self.append('actions.jsonl', dict(sequence=self.executed_actions,
                                        action_index=self.active['index'], action=plain(action)))
        self.executed_actions += 1
        self.active['index'] += 1

    def finish_result(self, ob):
        if self.settings['mode'] in ('auto_route', 'auto_branch'):
            targets = [{'id': event_id} for event_id in sorted(self.seen_events)]
        else:
            targets = self.cases[self.active['episode_id']]['targets']
        counts = {t['id']: sum(r['event']['target_id'] == t['id'] for r in self.completed_interventions) for t in targets}
        result = dict(protocol=self.manifest.get('protocol', 'distance_oracle_v001'),
                      episode_id=self.active['episode_id'], arm=self.arm,
                      status='complete', threshold_m=self.threshold, max_reference_distance_m=self.maximum_distance,
                      threshold_reached=self.maximum_distance >= self.threshold,
                      triggered=bool(self.completed_interventions), interventions=self.completed_interventions,
                      event_intervention_counts=counts, threshold_event_ids=sorted(self.seen_events),
                      checkpoint_event_ids=sorted(self.checkpoints), executed_actions=self.executed_actions,
                      final_policy_action_index=self.active['index'],
                      metrics=plain(next(iter(ob['metrics'].values()))[0]))
        write(self.case_root / 'result.json', result)
        write(self.root / self.active['episode_id'] / 'result.json', result)
        return result

