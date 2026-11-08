import copy
import importlib.util
import json
from pathlib import Path
import unittest

from core.crossing_checkpoint import (CheckpointTracker, build_messages, evaluate_events,
    map_encounters, response_schema, select_history, validate_response)


def prediction(frame=0, status='crossing', location='here', same='yes'):
    return dict(status=status, location=location, same_place=same, confidence='high',
        incoming_route='behind',description='T junction',reason='two open routes',
        evidence_frames=[frame],branches=[dict(direction='left',landmark='corridor',evidence_frame=frame),
                                         dict(direction='right',landmark='doorway',evidence_frame=frame)])


def step(frame,x,y=0):
    return dict(frame=frame,terminal=False,position=[x,y,1])


class CausalProtocolTests(unittest.TestCase):
    def test_current_or_future_action_is_rejected(self):
        images=[dict(frame=3,data_url='data:image/png;base64,AA==',sha256='test')]
        for index in [3,4]:
            with self.assertRaises(ValueError):
                build_messages(images,[dict(index=index,name='LEFT')])
        messages=build_messages(images,[dict(index=2,name='FORWARD')])
        self.assertIn('current_observation',messages[1]['content'][0]['text'])

    def test_history_never_peeks_ahead(self):
        self.assertEqual(select_history(4,list(range(20)),3),[2,3,4])
        with self.assertRaises(ValueError):select_history(4,[0,1,2])

    def test_future_evidence_is_rejected(self):
        value=prediction(7)
        with self.assertRaises(ValueError):validate_response(value,[3,4,5])
        value=prediction(5);value['branches'][0]['evidence_frame']=7
        with self.assertRaises(ValueError):validate_response(value,[3,4,5])

    def test_memory_does_not_expand_current_evidence_window(self):
        tracker=CheckpointTracker()
        tracker.update(0,prediction(0));tracker.update(1,prediction(1))
        memory=tracker.prompt_memory()
        images=[dict(frame=i,data_url='data:image/png;base64,AA==',sha256='test') for i in range(2,10)]
        messages=build_messages(images,[],memory)
        schema=json.loads(messages[1]['content'][-1]['text'].split('Output JSON with this schema: ',1)[1])
        self.assertEqual(schema,response_schema(list(range(2,10))))
        self.assertEqual(schema['properties']['evidence_frames']['items']['enum'],list(range(2,10)))
        self.assertEqual(schema['properties']['branches']['items']['properties']['evidence_frame']['enum'],list(range(2,10)))
        with self.assertRaises(ValueError):validate_response(prediction(1),list(range(2,10)))
        validate_response(prediction(9),list(range(2,10)))

    def test_evidence_schema_does_not_mutate_other_requests(self):
        first=response_schema([0,1]);second=response_schema([10,11])
        self.assertEqual(first['properties']['evidence_frames']['items']['enum'],[0,1])
        self.assertEqual(second['properties']['evidence_frames']['items']['enum'],[10,11])
        for ids in [[],[1,1],[2,1],[-1],[False]]:
            with self.assertRaises(ValueError):response_schema(ids)

    def test_noninteger_evidence_is_not_an_alias_for_an_image_id(self):
        for invalid in [True,1.0,'1',[]]:
            value=prediction(1);value['evidence_frames']=[invalid]
            with self.assertRaises(ValueError):validate_response(value,[1])
            value=prediction(1);value['branches'][0]['evidence_frame']=invalid
            with self.assertRaises(ValueError):validate_response(value,[1])

    def test_one_route_cannot_be_a_crossing(self):
        value=prediction(0);value['branches']=value['branches'][:1]
        with self.assertRaises(ValueError):validate_response(value,[0])

    def test_confirmation_not_backdated(self):
        tracker=CheckpointTracker()
        self.assertIsNone(tracker.update(3,prediction(3)))
        event=tracker.update(4,prediction(4))
        self.assertEqual(event['first_seen_frame'],3)
        self.assertEqual(event['confirmation_frame'],4)
        tracker.update(5,prediction(5))
        events=tracker.finish()
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['confirmation_frame'],4)
        self.assertNotIn('position',tracker.prompt_memory() or {})

    def test_ahead_is_candidate_not_reached_checkpoint(self):
        tracker=CheckpointTracker()
        for i in range(4):self.assertIsNone(tracker.update(i,prediction(i,location='ahead')))
        self.assertIsNone(tracker.finish()[0]['confirmation_frame'])

    def test_tracker_cannot_go_backward(self):
        tracker=CheckpointTracker();tracker.update(5,prediction(5))
        with self.assertRaises(ValueError):tracker.update(4,prediction(4))

    def test_turns_do_not_automatically_create_duplicates(self):
        tracker=CheckpointTracker()
        for i in range(8):tracker.update(i,prediction(i,same='yes'))
        self.assertEqual(len(tracker.finish()),1)


class MapEvaluationTests(unittest.TestCase):
    def test_only_encountered_map_crossings_count(self):
        steps=[step(i,x) for i,x in enumerate([-2,-1,0,1,2])]
        refs=[dict(id='C01',position=[0,0]),dict(id='C02',position=[10,10])]
        result=map_encounters(steps,refs)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['crossing_id'],'C01')

    def test_return_visits_are_distinct(self):
        steps=[step(i,x) for i,x in enumerate([-2,0,2,0,-2])]
        encounters=map_encounters(steps,[dict(id='C01',position=[0,0])])
        self.assertEqual(len(encounters),2)

    def test_duplicate_predictions_penalized(self):
        steps=[step(i,x) for i,x in enumerate([-2,-.3,0,.3,2])]
        refs=map_encounters(steps,[dict(id='C01',position=[0,0])])
        events=[dict(id='P1',confirmation_frame=1),dict(id='P2',confirmation_frame=2)]
        metrics=evaluate_events(events,steps,refs)
        self.assertEqual((metrics['tp'],metrics['fp'],metrics['fn']),(1,1,0))
        self.assertEqual(metrics['duplicate_predictions'],1)

    def test_matching_is_one_to_one_and_maximum_cardinality(self):
        steps=[step(1,.4),step(2,0)]
        refs=[dict(id='C1:visit1',crossing_id='C1',position=[0,0],approach_frame=0,exit_frame=3,closest_frame=2),
              dict(id='C2:visit1',crossing_id='C2',position=[.8,0],approach_frame=0,exit_frame=3,closest_frame=1)]
        events=[dict(id='P1',confirmation_frame=1),dict(id='P2',confirmation_frame=2)]
        metrics=evaluate_events(events,steps,refs,radius=.6)
        self.assertEqual((metrics['tp'],metrics['fp'],metrics['fn']),(2,0,0))

    def test_no_events_is_not_reported_as_perfect_accuracy(self):
        metrics=evaluate_events([],[],[])
        self.assertIsNone(metrics['precision']);self.assertIsNone(metrics['recall'])


if __name__=='__main__':unittest.main()
