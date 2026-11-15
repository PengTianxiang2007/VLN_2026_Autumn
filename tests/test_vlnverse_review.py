import gzip
import ast
from enum import Enum
import importlib.util
import json
from pathlib import Path
import random
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from core.seeding import episode_seed
from core.vlnverse_review import EpisodeReview, review_settings, write_review_index


class ReviewPolicyTests(unittest.TestCase):
    def test_run_config_records_existing_sensors_without_topdown_camera(self):
        from benchmarks.vlnverse.runner.run_full import write_config
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'config.py'
            write_config(path,'StreamVLN',1234,'test',Path(directory),'physical',dict(seed=2))
            tree=ast.parse(path.read_text())
            assignment=next(node for node in tree.body if isinstance(node,ast.Assign) and node.targets[0].id=='eval_cfg')
            settings=ast.literal_eval(next(k.value for k in assignment.value.keywords if k.arg=='eval_settings'))
            self.assertFalse(settings['vis_output'])
            self.assertEqual(settings['review_output'],{'seed':2})

    def test_only_selected_future_seeds_are_enabled(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); runs=root/'runs'; runs.mkdir()
            self.assertIsNone(review_settings(runs,2,'StreamVLN'))
            (runs/'visualization.json').write_text(json.dumps(dict(schema=1,seeds=[2,3],output_dir=str(root/'visualization'))))
            enabled=[s for s in range(5) if review_settings(runs,s,'StreamVLN')]
            self.assertEqual(enabled,[2,3])
            self.assertIsNone(review_settings(runs,2,'JanusVLN'))
            self.assertIsNone(review_settings(runs,None,'StreamVLN'))

    def test_empty_review_index_and_escaped_instruction(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            write_review_index(root,[])
            self.assertIn('const rows=[]',(root/'index.html').read_text())
            write_review_index(root,[dict(instruction='</script><script>alert(1)</script>')])
            self.assertNotIn('</script><script>alert(1)',(root/'index.html').read_text())


@unittest.skipUnless(all(importlib.util.find_spec(n) for n in ('cv2','numpy','imageio_ffmpeg')),
                     'Requires the existing VLNVerse Python')
class ReviewVideoTests(unittest.TestCase):
    def test_terminal_observation_is_recorded_before_episode_reset(self):
        import numpy as np
        source=Path(__file__).resolve().parents[1]/'benchmarks/vlnverse/upstream/vlnverse/evaluator/vln_pe_evaluator.py'
        tree=ast.parse(source.read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='VlnPeEvaluator')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='eval')
        Status=Enum('Status',dict(NORMAL=0,WARM_UP=1,NOT_RESET=3,TERMINATED=2,STOP=4))
        scope=dict(np=np,os=__import__('os'),runner_status_code=Status,log=Mock(),progress_log_multi_util=Mock())
        exec(compile(ast.Module(body=[method],type_ignores=[]),str(source),'exec'),scope)
        events=[];info=SimpleNamespace(data=dict(path_key='t_a_e_a'))
        observation=dict(rgb=np.zeros((480,640,3),dtype=np.uint8),globalgps=[0,0,0])
        terminal=dict(globalgps=[1,0,0])
        review=SimpleNamespace(start=lambda key:events.append(('start',key)),
            observe=lambda key,ob,action,terminal=False:events.append(('terminal' if terminal else 'action',key,ob)))
        obj=SimpleNamespace(review=review,jev_live=None,vis_output=False,run_seed=None,env_num=1,proc_num=1,robot_name='h1',
            env=SimpleNamespace(reset=lambda:([{'h1':observation}],[info]),is_running=lambda:True,close=lambda:None),
            now_path_key=lambda value:value.data['path_key'],warm_up=lambda:[{'h1':observation}],
            _obs_remove_robot_name=lambda obs:[x['h1'] for x in obs],
            get_action=lambda obs,action:(obs,[{'h1':{'move_by_discrete':[1]}}]),
            env_step=lambda action:([terminal],[True]))
        def terminate(obs,infos,ended):
            events.append(('finish','t_a_e_a'));infos[0].data['path_key']='t_b_e_b';return True,infos
        obj.terminate_ops=terminate
        scope['eval'](obj)
        self.assertEqual([x[:2] for x in events],[('start','t_a_e_a'),('action','t_a_e_a'),('terminal','t_a_e_a'),('finish','t_a_e_a')])
        self.assertIs(events[1][2],observation);self.assertIs(events[2][2],terminal)

    def test_h264_video_actions_terminal_frame_and_rng_isolation(self):
        import cv2
        import numpy as np
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);dataset=root/'dataset';(dataset/'val_unseen').mkdir(parents=True)
            episodes=[dict(episode_id=f'e_{n}',trajectory_id=f't_{n}',scan='scene_a',
                instruction={'instruction_text':'Walk forward, then stop.'},reference_path=[[0,0,0],[1,0,0]]) for n in ('a','b')]
            with gzip.open(dataset/'val_unseen/val_unseen.json.gz','wt') as stream:json.dump(dict(episodes=episodes),stream)
            review=EpisodeReview(dict(output_dir=str(root/'review'),seed=2,fps=6,crf=26),'test_run',dataset)
            python_state=random.getstate();numpy_state=np.random.get_state()
            rgb=np.zeros((480,640,3),dtype=np.uint8);rgb[:,:,0]=np.arange(640,dtype=np.uint16)%255;rgb[:,:,1]=120
            original=rgb.copy()
            for n in ('a','b'):
                key=f't_{n}_e_{n}';review.start(key)
                for index in range(15):review.observe(key,dict(rgb=rgb,globalgps=[index/10,0,0]),{'move_by_discrete':[1]})
                review.observe(key,dict(globalgps=[1.5,0,0]),{},terminal=True)
                metrics=dict(episode_id=f'e_{n}',success=int(n=='b'),spl=.5 if n=='b' else 0.,NE=1. if n=='b' else 4.,
                    osr=1.,TL=1.5,steps=751,fail_reason='success' if n=='b' else 'fall',pred_path=[[0,0,0],[1.5,0,0]],
                    reproduction_run_seed=2,reproduction_episode_seed=episode_seed(2,f'e_{n}'))
                review.finish(key,metrics)
            rows=[json.loads(line) for line in (root/'review/index.jsonl').read_text().splitlines()]
            self.assertEqual([r['episode_id'] for r in rows],['e_a','e_b'])
            self.assertTrue(all(r['status']=='complete' and r['frames']==16 for r in rows))
            for row in rows:
                video=root/'review'/row['video'];cap=cv2.VideoCapture(str(video));count=0
                while True:
                    ok,frame=cap.read()
                    if not ok:break
                    count+=1;self.assertEqual(frame.shape,(640,960,3))
                cap.release();self.assertEqual(count,16)
                steps=[json.loads(line) for line in (root/'review'/row['steps']).read_text().splitlines()]
                self.assertEqual(sum(not s['terminal'] for s in steps),15)
                self.assertTrue(steps[-1]['terminal']);self.assertTrue(steps[-1]['rgb_reused'])
                self.assertTrue((root/'review'/row['trajectory']).exists())
            np.testing.assert_array_equal(rgb,original)
            self.assertEqual(random.getstate(),python_state)
            after=np.random.get_state();self.assertEqual(after[0],numpy_state[0]);np.testing.assert_array_equal(after[1],numpy_state[1]);self.assertEqual(after[2:],numpy_state[2:])


if __name__=='__main__':
    unittest.main()
