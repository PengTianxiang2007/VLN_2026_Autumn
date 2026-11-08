"""CPU fixtures: sparse requests must preserve dense causal inputs and tracker votes."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import replay_crossing_checkpoint as replay
from preview_crossing_checkpoint import prefix_case
from core import crossing_checkpoint as core


class Capture:
    def __init__(self, _): self.index = 0
    def isOpened(self): return True
    def get(self, key): return 960 if key == cv2.CAP_PROP_FRAME_WIDTH else 640
    def read(self):
        value = np.full((640, 960, 3), self.index, dtype=np.uint8)
        self.index += 1
        return True, value
    def release(self): pass


class StrideTests(unittest.TestCase):
    def fixture(self, directory, stride):
        video = directory/'fixture.video';video.write_bytes(b'CPU-only video fixture')
        source = dict(video=str(video), source_video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),
            observations=[dict(frame=f, terminal=f==10, rgb_reused=f==10,
                               action={'move_by_discrete':[1]}) for f in range(11)])
        inference = dict(base_url='http://127.0.0.1:1/v1', served_model='fixture', max_tokens=8192,
                         thinking=False, chat_template_kwargs={'enable_thinking':False})
        if stride != 1: inference['inference_stride'] = stride
        payloads = []
        def model(_, payload):
            payloads.append(payload)
            frame = json.loads(payload['messages'][1]['content'][0]['text'])['current_observation']
            prediction = dict(status='crossing', location='here', same_place='yes', confidence='high',
                incoming_route='来路', description='CPU模拟', reason='两个分支', evidence_frames=[frame],
                branches=[dict(direction='left',landmark='区域甲',evidence_frame=frame),
                          dict(direction='front',landmark='区域乙',evidence_frame=frame)])
            return dict(choices=[dict(finish_reason='stop',message=dict(content=json.dumps(prediction)))])
        private = dict(scene='fixture', instruction='CPU模拟', success=False,
                       steps=[dict(frame=f, position=[float(f),0,1]) for f in range(11)])
        with patch.object(cv2, 'VideoCapture', Capture), patch.object(replay, 'call_model', model):
            result = replay.replay_one((str(directory), 'fixture', 'episode', source, inference))
            rows = [json.loads(x) for x in (directory/'runs/fixture/cases/episode/predictions.jsonl').read_text().splitlines()]
            reviewed = prefix_case('episode',source,private,rows,core,inference,[dict(id='C0',position=[2,0])])
        return source, inference, private, result, rows, reviewed, payloads

    def test_stride_two_retains_intermediate_rgb_actions_and_vote_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, _, result, rows, reviewed, payloads = self.fixture(Path(directory),2)
            self.assertEqual([r['frame'] for r in rows],[0,2,4,6,8])
            self.assertEqual(len(payloads),5)
            self.assertEqual(rows[-1]['image_frames'],list(range(1,9)))
            self.assertEqual([a['index'] for a in rows[-1]['executed_actions']],list(range(8)))
            self.assertEqual(result['events'][0]['confirmation_frame'],2)
            self.assertEqual(result['events'][0]['observation_frames'],[0,2,4,6,8])
            self.assertEqual(reviewed['processed'],reviewed['expected'])
            self.assertEqual(set(reviewed['history_images']),set(map(str,range(10))))
            self.assertEqual(reviewed['steps'][-1]['frame'],9)

    def test_stride_one_keeps_original_dense_behavior(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, _, result, rows, reviewed, payloads = self.fixture(Path(directory),1)
            self.assertEqual([r['frame'] for r in rows],list(range(10)))
            self.assertEqual(len(payloads),10)
            self.assertEqual(result['events'][0]['confirmation_frame'],1)
            self.assertNotIn('history_images',reviewed)

    def test_audit_rejects_missing_scheduled_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            source,inference,private,_,rows,_,_ = self.fixture(Path(directory),2)
            with self.assertRaisesRegex(ValueError,'complete causal prefix'):
                prefix_case('episode',source,private,rows[1:],core,inference,[])


if __name__ == '__main__': unittest.main()
