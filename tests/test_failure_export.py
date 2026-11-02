import copy
import unittest
from scripts.export_failure_cases import joint_failure_ids, select_diverse_cases


class FailureExportTests(unittest.TestCase):
    def test_every_seed_must_fail_without_fall_or_stuck(self):
        record=dict(info=dict(success=0),fail_reason='not_reach_goal')
        scores={s:{episode:copy.deepcopy(record) for episode in ['good','one_success','fall','stuck','missing','timeout']} for s in [0,1,2]}
        scores[0]['one_success']['info']['success']=1
        scores[1]['fall']['fail_reason']='fall'
        scores[2]['stuck']['fail_reason']='stuck'
        scores[1]['timeout']['fail_reason']='exceed_total_max_step'
        del scores[0]['missing']
        self.assertEqual(joint_failure_ids(scores,[0,1,2]),{'good'})

    def test_selection_keeps_25_unique_tasks_from_only_eligible_scenes(self):
        eligible={}
        for scene,count in enumerate([2,2,6,6,3,3,12,3,5]):
            for episode in range(count):
                key=f's{scene}_e{episode}'
                eligible[key]=dict(episode_id=key,scene=str(scene),metrics=dict(NE=3+episode,osr=episode%2))
        selected=select_diverse_cases(eligible)
        self.assertEqual(len(selected),25)
        self.assertEqual(len({r['episode_id'] for r in selected}),25)
        self.assertEqual({r['scene'] for r in selected},set(map(str,range(9))))
        with self.assertRaisesRegex(ValueError,'Only'): select_diverse_cases(dict(list(eligible.items())[:24]))
