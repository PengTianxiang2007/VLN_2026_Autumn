"""Causal node commitment and the v006 to two-stage Recovery interface."""
import copy
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from core.oracle_branch_policy import checkpoint, FIELDS
from core.serial_v006 import BRANCH_DIR, NODE_VIEWS, ROOT, V006API, V006Decisions
from core.serial_v006_runtime import V006Hook
from core.serial_runtime import action_id


PROGRESS = dict(zh='已完成：无\n当前：穿过门口\n待执行：转弯',
                en='Completed: none\nCurrent: Go through the doorway\nPending: Turn')


class LiveRecoveryTests(TestCase):
    def test_main_stop_waits_for_verdict_and_only_executed_action_is_counted(self):
        native = SimpleNamespace(runner_status_code=SimpleNamespace(NORMAL='normal'))
        for verdict in ('consistent', 'deviated', None):
            with self.subTest(verdict=verdict), patch.dict(sys.modules, {'vlnverse.evaluator.vln_pe_evaluator': native}):
                hook = object.__new__(V006Hook)
                hook.active, hook.local, hook.pending, hook.action_count = True, False, None, 5
                hook.instruction = 'Enter the small room.'
                hook.e = SimpleNamespace(robot_name='h1', runner_status=['normal'])
                hook.config = {'local_action_budget': 40}
                hook.event = Mock()
                api, sampler = Mock(), Mock()
                sampler.push.return_value = {}
                hook.engine = V006Decisions(api, hook.instruction, hook.event, sampler=sampler)
                hook.engine.frames = [dict(index=0)]
                hook.engine.anchor = dict(index=0, id='S01')
                hook.engine.nodes.append(hook.engine.anchor)
                api.deviation.return_value = dict(verdict=verdict, semantic_progress=PROGRESS) if verdict else None
                hook.frame = Mock(return_value=dict(index=1))
                stop = [{'h1': {'stop': []}}]
                forward = [{'h1': {'move_by_discrete': [1]}}]
                hook.action = Mock(side_effect=[(['original'], stop), (['local'], forward)])
                def recover(ob):
                    self.assertEqual(hook.pending['target'], hook.engine.anchor)
                    hook.local, hook.local_steps, hook.local_instruction = True, 0, 'Turn left.'
                    return {'rgb': 'landing'}, False
                hook.recover = Mock(side_effect=recover)
                if verdict is None:
                    with self.assertRaisesRegex(ValueError, 'proposed STOP'):
                        hook._before_action([{'rgb': 'window'}], [])
                    self.assertEqual(hook.action_count, 5)
                else:
                    _, actions = hook._before_action([{'rgb': 'window'}], [])
                    self.assertEqual(action_id(actions, 'h1'), 0 if verdict == 'consistent' else 1)
                    self.assertEqual(hook.action_count, 6)
                self.assertEqual(hook.recover.call_count, int(verdict == 'deviated'))
                api.deviation.assert_called_once()
                self.assertEqual([f['index'] for f in api.deviation.call_args.args[2]], [0, 1])

    def test_alarm_interrupts_queued_actions_before_selection_and_handoff(self):
        for status in ('selected', 'no_alternative'):
            with self.subTest(status=status), TemporaryDirectory() as tmp, patch.dict(os.environ, VLN_BRANCH_ROOT=tmp):
                evaluator = SimpleNamespace(**dict.fromkeys(FIELDS))
                evaluator.step_id = 33
                evaluator.rgb_list = ['prior frame']
                evaluator.model = SimpleNamespace(cache=None,curr_t=0)
                agent = SimpleNamespace(evaluator=evaluator,pending=[3,1,2],calls=11,
                                        current_episode_id='test',current_episode_seed=2)
                hook = object.__new__(V006Hook)
                hook.folder=Path(tmp); hook.recoveries=0; hook.handoffs=0
                hook.eid='test'; hook.config={'seed':2}; hook.local=False
                hook.e=SimpleNamespace(agent=agent); hook.initial_joints=[]
                hook.task=Mock(return_value=SimpleNamespace(env_offset=[0,0,0],step_count=100))
                hook.engine=SimpleNamespace(frames=[dict(index=0,world_position=[1,2,1],
                                                         world_orientation=[1,0,0,0])])
                hook.pending=dict(target=dict(id='S01',index=0),progress=PROGRESS,detected_at=33)
                hook.rpc=lambda op,key:checkpoint(agent,1,33,dict(operation=op,key=key))[0]
                hook.frame=Mock(return_value={'path':'landing.png'})
                hook.event=Mock(); hook.new_leg=Mock(); hook.after_handoff=Mock()
                hook.api=Mock()
                landing=dict(globalgps=[1,2,1],globalrotation=[1,0,0,0])
                def restore_pose(*args):
                    self.assertEqual(agent.pending,[])
                    self.assertEqual(evaluator.step_id,33)
                    return landing,False
                def choose(pending):
                    hook.event.assert_called_with('rollback',target='S01',frame=0,ended=False)
                    return dict(status=status,recovery_instruction_en='Turn left.' if status=='selected' else None)
                hook.select_route=choose
                def reset(*args,**kwargs):
                    evaluator.step_id=0
                    evaluator.rgb_list=[]
                agent.reset=Mock(side_effect=reset)
                hook.policy=Mock(return_value=dict(step_id=0,pending_count=0,history_images=0))
                with patch('core.serial_runtime.CheckpointPair.restore_pose',side_effect=restore_pose):
                    self.assertEqual(hook.recover({}), (landing,False))
                hook.api.deviation.assert_not_called()
                if status=='selected':
                    agent.reset.assert_called_once()
                    self.assertTrue(hook.local)
                    hook.handoff('local_stop')
                else:
                    agent.reset.assert_not_called()
                    hook.after_handoff.assert_called_once_with(landing)
                proof=json.loads((hook.folder/'recovery_001/memory_save.json').read_text())
                self.assertEqual(proof['discarded_actions'],[3,1,2])
                self.assertEqual((agent.pending,evaluator.step_id,evaluator.rgb_list),([],33,['prior frame']))

    def test_replaced_candidate_never_reviewed_and_terminal_only_reports(self):
        api = Mock()
        api.dedup.return_value = 'same'
        api.deviation.side_effect = [dict(verdict='consistent', semantic_progress=PROGRESS),
                                     dict(verdict='deviated', semantic_progress=None)]
        sampler = Mock()
        sampler.push.side_effect = lambda _, i: dict(node={
            5: dict(id='S01', index=0, emittedAt=5),
            13: dict(id='S02', index=8, emittedAt=13),
        }.get(i))
        decisions = V006Decisions(api, 'Go through the doorway.', Mock(), sampler=sampler)
        for i in range(22):
            self.assertIsNone(decisions.observe(dict(index=i)))
        self.assertEqual([(n['id'], n['source_id'], n['index']) for n in decisions.nodes],
                         [('S01', 'S02', 8)])
        alarm = decisions.terminal(dict(index=22))
        self.assertEqual(alarm['target']['index'], 8)
        self.assertTrue(alarm['alarm_node']['terminal_node'])
        self.assertEqual(alarm['progress'], PROGRESS)
        self.assertEqual(api.jev.call_count, 22)

    def test_seven_causal_images_and_progress_then_selection_or_abstention(self):
        api = object.__new__(V006API)
        api.config = dict(semantic_provider='qwen_local', semantic_model='qwen')
        api.branch_schema = json.loads((ROOT / BRANCH_DIR / 'output_schema.json').read_text())
        frames = [dict(index=i) for i in range(18)]
        views = Mock(return_value=[dict(image_id=name, index=7, view_label=label)
                                   for name, _, label in NODE_VIEWS])
        target = dict(index=7)
        result = api.recovery(target, frames[:-1], 'Original task', PROGRESS, views)
        self.assertEqual(result['status'], 'input_incomplete')
        views.assert_not_called()
        review = dict(branches=[dict(id=bid, direction=direction, entrance_description='入口',
                                     current_choice_basis='可直接到达', evidence_image_ids=['C_front'])
                                for bid, direction in [('B1','left'), ('B2','right')]],
                      previous_attempt=dict(status='identified', branch_id='B1',
                                            reason='进入左门', evidence_image_ids=['C_plus2']),
                      uncertainties=[])
        api.invalid_answer = Mock()
        for branch_id, line, status in [('B2', 'Turn right.', 'selected'),
                                        (None, None, 'no_alternative'),
                                        ('B1', 'Turn left.', 'invalid_answer')]:
            api.ask = Mock(side_effect=[copy.deepcopy(review),
                                       dict(selected_branch_id=branch_id, recovery_instruction_en=line)])
            result = api.recovery(target, frames, 'Original task', PROGRESS, views)
            self.assertEqual(result['status'], status, result)
            first, second = api.ask.call_args_list
            self.assertEqual([f['index'] for f,_ in first.args[2]], [7,7,7,9,12,15,17])
            self.assertNotIn('Original task', first.args[1])
            self.assertEqual(second.args[1]['Current'], '穿过门口')
            self.assertEqual(second.args[1]['instruction_en'], 'Original task')
            self.assertEqual(len(second.args[2]), 3)
