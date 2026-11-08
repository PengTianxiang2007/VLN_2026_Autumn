"""CPU checks for human-event boundaries and unchanged v001 request isolation."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from core.agent_route_choice import build_messages, file_hash, validate_case
from scripts.prepare_human_route_choice import build_case


class HumanEventInputs(unittest.TestCase):
    def source(self, cp=0):
        obs = [dict(frame=i, terminal=i==10, rgb_reused=i==10, eligible_for_inference=i!=10,
                    newly_executed_actions=[] if i==0 else [dict(frame=i-1,action={'move_by_discrete':[1]})]) for i in range(11)]
        trajectory=dict(frames=[dict(frame=i,position=[i*.2,0,1]) for i in range(11)])
        event=dict(frame=cp,id='human_uuid',episode_id='episode')
        protocol=dict(context_window_observations=16,checkpoint_context_images=4,wrong_attempt_images=4,approach_action_limit=32)
        return event,dict(instruction='Go through the left door.'),obs,trajectory,protocol

    def test_first_frame_keeps_one_real_image_and_no_fabricated_history(self):
        case,selected,audit=build_case(*self.source(), 'sample_01')
        self.assertEqual(audit['call1_frames'],[0]);self.assertEqual(case['approach_actions'],[])
        self.assertGreater(case['wrong_end_frame'],0)
        self.assertEqual(case['checkpoint_frame'],0)

    def test_same_episode_events_remain_independent(self):
        first=build_case(*self.source(0),'sample_01')
        second=build_case(*self.source(3),'sample_02')
        self.assertEqual(first[0]['checkpoint_frame'],0)
        self.assertEqual(second[0]['checkpoint_frame'],3)
        self.assertNotEqual(first[0]['wrong_end_frame'],second[0]['wrong_end_frame'])

    def test_endpoint_action_is_not_yet_executed(self):
        case,_,_=build_case(*self.source(3),'sample_01')
        self.assertTrue(all(a['frame']<3 for a in case['approach_actions']))
        self.assertTrue(all(3<=a['frame']<case['wrong_end_frame'] for a in case['attempt_actions']))

    def test_no_terminal_or_reused_rgb_in_context_or_attempt(self):
        args=list(self.source(7));args[2][8].update(rgb_reused=True,eligible_for_inference=False)
        case,selected,_=build_case(*args,'sample_01')
        self.assertNotIn(8,[f['frame'] for f in selected]);self.assertNotIn(10,[f['frame'] for f in selected])
        self.assertEqual(case['wrong_end_frame'],9)

    def test_future_action_source_is_rejected(self):
        args=list(self.source());args[2][1]['newly_executed_actions'][0]['frame']=1
        with self.assertRaises(ValueError):build_case(*args,'sample_01')

    def test_request_contract_excludes_labels_coordinates_and_later_attempt(self):
        case,selected,_=build_case(*self.source(2),'sample_01')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for f in selected:
                rel='F%04d.png'%f['frame'];(root/rel).write_bytes(b'CPU fixture only')
                case['images'].append(dict(id='F%04d'%f['frame'],frame=f['frame'],
                    phase='checkpoint_context' if f['frame']<=2 else 'wrong_attempt',path=rel,sha256=file_hash(root/rel)))
            validate_case(case)
            messages=build_messages(case,root,1,'original prompt',embed_images=False)
            metadata=json.loads(messages[1]['content'][0]['text'])
            self.assertNotIn('instruction',metadata);self.assertNotIn('position',metadata)
            self.assertTrue(all(im['frame']<=2 for im in metadata['image_order']))
            bad=copy.deepcopy(case);bad['annotation_label']='wrong'
            with self.assertRaises(ValueError):build_messages(bad,root,1,'prompt')

    def test_shared_gpu_requires_explicit_flag_and_memory_headroom(self):
        from scripts.run_human_route_choice import admitted
        row=dict(used_mib=4000,free_mib=44000,utilization=0,compute_process_present=True)
        config=dict(gpu_memory_utilization=.75)
        self.assertFalse(admitted(row,49140,config,False))
        self.assertTrue(admitted(row,49140,config,True))
        self.assertFalse(admitted(dict(row,utilization=90),49140,config,True))
        self.assertFalse(admitted(dict(row,free_mib=38000),49140,config,True))


if __name__=='__main__':unittest.main()
