"""Distance intervention hooks around the unchanged native evaluation loop.

The original evaluator owns warmup, task/scene reset, scoring and shutdown.
No scene patch, alternate episode loop or process lifetime policy is installed.
"""
import os
import json
from pathlib import Path
import time

from core.oracle_crossing import plain, write
from core.oracle_distance_runtime import DistanceOracle
from core.seeding import episode_seed


def check_reset(policy, eid, seed):
    state = policy['state']
    if (policy['episode_id'], policy['step_id'], policy['pending_count']) != (eid, 0, 0):
        raise RuntimeError('Native reset left policy identity/action state')
    if state['episode_seed'] != episode_seed(seed, eid):
        raise RuntimeError('Native reset seed mismatch')
    if any(state[k] != [] for k in ('rgb_list', 'depth_list', 'pose_list', 'intrinsic_list',
                                    'time_ids', 'action_seq', 'pending')):
        raise RuntimeError('Native reset left observation/action history')
    if any(state[k] is not None for k in ('output_ids', 'past_key_values', 'last_image')):
        raise RuntimeError('Native reset left inference cache')
    if state['model_cache'] != [{}] or state['model_curr_t'] != [0]:
        raise RuntimeError('Native reset left model history')


class NativeDistanceHook:
    def __init__(self, evaluator):
        self.e = evaluator
        self.oracle = None
        self.terminal_observation = None
        self.reset = evaluator.reset_seeded_agent
        self.action = evaluator.get_action
        self.step = evaluator.env_step
        self.terminate = evaluator.terminate_ops
        evaluator.reset_seeded_agent = self.after_reset
        evaluator.get_action = self.before_action
        evaluator.env_step = self.step_with_terminal
        evaluator.terminate_ops = self.finish_before_reset

    def after_reset(self, infos, indices):
        self.reset(infos, indices)
        if indices != [0] or len(infos) != 1:
            raise RuntimeError('Distance Oracle requires one native environment')
        eid = infos[0].data['episode_id']
        oracle = DistanceOracle(self.e)
        oracle.begin(self.e, eid)
        proof = oracle.policy(deep=True)
        check_reset(proof, eid, oracle.manifest['seed'])
        self.oracle = oracle
        self.terminal_observation = None
        task = oracle.task(self.e)
        write(oracle.case_root / 'native_reset_proof.json', dict(
            pid=os.getpid(), episode_id=eid, time=time.time(), policy=proof,
            physics_ticks=task.step_count, scene=str(task.config.scene_asset_path),
            reset_owner='VlnPeEvaluator.reset_seeded_agent'))

    def before_action(self, observations, action):
        from vlnverse.evaluator.vln_pe_evaluator import runner_status_code
        oracle = self.oracle
        if oracle is None or self.e.runner_status[0] != runner_status_code.NORMAL:
            return self.action(observations, action)
        ob = observations[0]
        decision = oracle.observe(self.e, ob)
        ob, ended = oracle.automatic_review(self.e, ob, decision)
        corrected = [ob]
        if ended:
            # Correction stabilization can reach a native terminal condition.
            # Hand that exact terminal observation to native scoring without
            # generating/executing an extra policy action or physics step.
            self.terminal_observation = ob
            return corrected, action
        result, actions = self.action(corrected, action)
        oracle.record_action(actions[0][self.e.robot_name])
        return result, actions

    def step_with_terminal(self, action):
        if self.terminal_observation is not None:
            ob = self.terminal_observation
            self.terminal_observation = None
            return [ob], [True]
        return self.step(action)

    def finish_before_reset(self, observations, infos, terminated):
        oracle = self.oracle
        ended = oracle is not None and bool(terminated[0])
        if ended:
            oracle.observe(self.e, observations[0], terminal=True)
            oracle.finish_result(observations[0])
            self.oracle = None
        # Retain original native scoring, RSS check, scene reset and warmup.
        outcome = self.terminate(observations, infos, terminated)
        if ended:
            write(oracle.case_root / 'native_scoring_complete.json', dict(
                episode_id=oracle.active['episode_id'], arm=oracle.arm,
                pid=os.getpid(), finished_at=time.time(),
                metrics=plain(next(iter(observations[0]['metrics'].values()))[0]),
                native_terminate_ops_returned=True))
        return outcome


def install(evaluator):
    if os.environ.get('VLN_DISTANCE_ARM') and not hasattr(evaluator, '_distance_hook'):
        evaluator._distance_hook = NativeDistanceHook(evaluator)
    retain_file = os.environ.get('VLN_SIM_RETAIN_FILE')
    if retain_file and not getattr(evaluator, '_oracle_retention_installed', False):
        # Completion-only retention also works for the unmodified policy arm.
        # It must not install an Oracle action/reset/scoring hook for baseline.
        install_retention(evaluator, Path(retain_file),
                          Path(os.environ['VLN_NATIVE_RESULT_FILE']),
                          int(os.environ['VLN_EXPECTED_EPISODES']))
        evaluator._oracle_retention_installed = True


def install_retention(evaluator, marker, scores, expected):
    """Only opt in when the user requests loaded services after completion.

    Native RSS exits still close/restart the simulator at the original boundary.
    All scoring and resets run unchanged. Final close waits for an explicit
    release file so the same model can be reused by the next authorized run.
    """
    close = evaluator.env.close
    def retained_close():
        complete = scores.exists() and json.loads(scores.read_text()).get('val_unseen', {}).get('Count') == expected
        if complete:
            write(marker, dict(pid=os.getpid(), phase='complete_simulator_retained',
                               completed=expected, time=time.time()))
            print('ORACLE_SIMULATOR_RETAINED ' + str(marker), flush=True)
            while not marker.with_suffix('.release').exists():
                time.sleep(1)
        return close()
    evaluator.env.close = retained_close
