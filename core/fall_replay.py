"""Experimental action-prefix replay. No claim of historical physics-state restoration.

The native policy runs on the *new* observations throughout replay. Its proposed
actions are logged, then overridden by the historical prefix until the release
index. Policy memory/queues are left intact. This reconstructs a new observation
history, not the missing original model cache or exact original RGB.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import time


def plain(value):
    return value.tolist() if hasattr(value, 'tolist') else value


def xy_distance(a, b):
    if a is None or b is None:
        return None
    distance = math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))
    if not math.isfinite(distance):
        raise ValueError('Nonfinite replay position')
    return distance


class FallReplay:
    def __init__(self, manifest, directory):
        data = json.loads(Path(manifest).read_text())
        self.cases = {r['episode_id']: r for r in data['cases'] if r['rollback_eligible']}
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.active = None

    @classmethod
    def from_environment(cls):
        path = os.environ.get('VLN_FALL_REPLAY_MANIFEST')
        return cls(path, os.environ['VLN_FALL_REPLAY_RECORD_DIR']) if path else None

    def _start(self, episode_id):
        if self.active is not None:
            if self.active['episode_id'] != episode_id:
                raise RuntimeError('New replay episode started before prior finish')
            return
        case = self.cases[episode_id]
        source = Path(case['source_steps']).read_bytes()
        if hashlib.sha256(source).hexdigest() != case['source_steps_sha256']:
            raise ValueError('Original action evidence changed')
        frames = [json.loads(line) for line in source.decode().splitlines()]
        original = [r for r in frames if not r['terminal']]
        target = case['rollback_action_index']
        if target is None or len(original) - target != 10:
            raise ValueError('Replay requires exactly ten original actions after release')
        if [r['action']['move_by_discrete'][0] for r in original] != case['original_actions']:
            raise ValueError('Action manifest differs from original evidence')
        path = self.directory / episode_id / f'attempt_{time.time_ns()}'
        path.mkdir(parents=True, exist_ok=False)
        self.active = dict(episode_id=episode_id, case=case, original=original,
                           old_terminal=frames[-1]['position'], target=target, index=0,
                           proposed_action_mismatches=0, max_prefix_xy_error_m=0.0,
                           checkpoint=None, directory=path)

    def choose(self, episode_id, observation, proposed):
        self._start(episode_id)
        state = self.active
        index, target = state['index'], state['target']
        position = plain(observation.get('globalgps'))
        orientation = plain(observation.get('globalrotation'))
        if position is None:
            raise ValueError('Cannot validate replay without current position')
        historical_position = state['original'][index]['position'] if index <= target else None
        error = xy_distance(position, historical_position)
        if error is not None:
            state['max_prefix_xy_error_m'] = max(state['max_prefix_xy_error_m'], error)
        forced = index < target
        executed = state['original'][index]['action'] if forced else proposed
        mismatch = forced and proposed != executed
        state['proposed_action_mismatches'] += int(mismatch)
        if index == target:
            state['checkpoint'] = dict(action_index=index, position=position, orientation=orientation,
                                       original_position=historical_position, xy_error_m=error,
                                       within_0_5m=error <= 0.5,
                                       original_orientation_available=False)
            (state['directory'] / 'checkpoint.json').write_text(json.dumps(state['checkpoint'], indent=2))
            print('FALL_REPLAY_CHECKPOINT ' + json.dumps(dict(episode_id=episode_id, **state['checkpoint'])), flush=True)
        record = dict(action_index=index, phase='original_action_replay' if forced else 'native_policy',
                      proposed=proposed, executed=executed, overridden=forced,
                      proposed_action_mismatch=bool(mismatch), position=position, orientation=orientation,
                      original_position=historical_position, prefix_xy_error_m=error)
        with (state['directory'] / 'actions.jsonl').open('a') as stream:
            stream.write(json.dumps(record) + '\n')
        state['index'] += 1
        return executed

    def finish(self, episode_id, observation, metrics):
        # Covers warm-up falls: a terminal score can arrive before choose().
        self._start(episode_id)
        state = self.active
        reason = metrics['fail_reason']
        reached = state['checkpoint'] is not None
        fallen = reason == 'fall'
        position = plain(observation.get('globalgps'))
        result = dict(episode_id=episode_id, status='complete', condition='original_action_prefix_replay',
                      run_seed=metrics['reproduction_run_seed'], episode_seed=metrics['reproduction_episode_seed'],
                      release_action_index=state['target'], actions_executed=state['index'],
                      checkpoint_reached=reached, checkpoint=state['checkpoint'],
                      outcome='fall_before_checkpoint' if fallen and not reached else
                              'terminated_before_checkpoint' if not reached else
                              'fall_after_checkpoint' if fallen else 'completed_without_fall',
                      actions_after_checkpoint=state['index'] - state['target'] if reached else None,
                      fall_within_10_actions_after_checkpoint=(state['index'] - state['target'] <= 10)
                      if reached and fallen else False if reached else None,
                      proposed_action_mismatches_in_prefix=state['proposed_action_mismatches'],
                      max_prefix_xy_error_m=state['max_prefix_xy_error_m'],
                      fail_reason=reason, SR=float(metrics['success']), NE=float(metrics['NE']),
                      terminal_position=position, original_fall_position=state['old_terminal'],
                      terminal_xy_distance_from_original_fall_m=xy_distance(position, state['old_terminal']),
                      model_history='native policy on new replay observations; original-action overrides are external',
                      exact_original_state_restored=False,
                      source_steps_sha256=state['case']['source_steps_sha256'])
        target = state['directory'] / 'result.json'
        temporary = target.with_suffix('.tmp')
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(target)
        print('FALL_REPLAY_FINISH ' + json.dumps(result), flush=True)
        self.active = None
        return result
