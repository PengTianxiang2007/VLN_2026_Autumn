import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run_deviation_progress_v004 as v4
from run_deviation_progress_v004 import review


PROGRESS = {'zh': '已完成：此前路线未确认。\n当前：沿通道前进，到分岔处右转。\n待执行：到达书架。',
            'en': 'Completed: Prior route unconfirmed.\nCurrent: Follow the passage and turn right at the fork.\nPending: Reach the bookcase.'}
REQ = {'previous_id': 'S01', 'current_id': 'S02', 'mode': 'segment',
       'instruction_en': 'Follow the passage and turn right at the fork. Stop by the bookcase.',
       'images': [{'frame': 2}, {'frame': 9}]}


def example(req, verdict):
    return dict(previous_id=req['previous_id'], current_id=req['current_id'], verdict=verdict,
                segment_summary={'zh':'可见通道。','en':'A passage is visible.'},
                reason={'zh':'入口可见。','en':'The entrance is visible.'},
                instruction_evidence=[{'quote_en':'turn right at the fork','quote_zh':'在岔路口右转'}],
                visual_evidence=[{'frames':[req['images'][-1]['frame']],
                                  'description':{'zh':'可见通道。','en':'A passage is visible.'}}],
                semantic_progress=copy.deepcopy(PROGRESS) if verdict == 'consistent' else None, uncertainties=[])


class Contract(unittest.TestCase):
    def test_actual_c47_s04_is_accepted_without_editing_model_evidence(self):
        fixture = json.loads((ROOT/'tests/fixtures/deviation_v004_c47_s04.json').read_text())
        original = fixture['answer']
        answer = v4.validate_v004(original, fixture['request'])
        self.assertEqual(original['type'], 'json_object')
        self.assertEqual(answer, {k:v for k,v in original.items() if k != 'type'})
        self.assertEqual((answer['current_id'], answer['verdict']), ('S04', 'deviated'))

    def test_echoed_format_marker_preserves_raw_and_validates_all_fields(self):
        raw = dict(example(REQ, 'deviated'), type='json_object')
        self.assertEqual(v4.validate_v004(raw, REQ), example(REQ, 'deviated'))
        self.assertEqual(raw['type'], 'json_object')
        for bad in (dict(raw, type='other'), dict(raw, extra=True),
                    dict(raw, instruction_evidence=[]), dict(raw, semantic_progress=PROGRESS),
                    {k:v for k,v in raw.items() if k!='reason'}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                v4.validate_v004(bad, REQ)

    def test_prompts_and_v003_default(self):
        for lang in ('zh', 'en'):
            text = (v4.VERSION / f'prompt_{lang}.txt').read_text()
            for required in (*v4.PROGRESS_HEADINGS['en'], *example(REQ, 'consistent')):
                self.assertIn(required, text)
            self.assertNotRegex(text, r'\bC\d\d\b')
        source = (ROOT / v4.route.PROMPTS['deviation']).read_text()
        self.assertEqual(review.sha(source.encode()), '129ef91051dcb6cc1be8e2e276cb102166bff322a36fdd10661e644de2162cad')
        answer = example(REQ, 'consistent')
        answer['semantic_progress'] = {'zh':'旧版累计进度。','en':'Older cumulative summary.'}
        review.validate(answer, REQ)
        with self.assertRaises(ValueError):
            v4.validate_v004(answer, REQ)

    def test_progress(self):
        a = example(REQ, 'consistent')
        a['semantic_progress']['zh'] += '\n未决：上一个入口的朝向还不清楚。'
        a['semantic_progress']['en'] += '\nUnresolved: The orientation at the previous entrance is unclear.'
        self.assertIs(v4.validate_v004(a, REQ), a)
        for invalid in ('Completed: x\nCurrent: y', 'Pending: z\nCompleted: x\nCurrent: y',
                        'Completed: x\nCurrent: \nPending: z\nUnresolved: u', PROGRESS['en']):
            a['semantic_progress']['en'] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                v4.validate_v004(a, REQ)

    def test_quotes_and_real_frames(self):
        a = example(REQ, 'deviated')
        a['instruction_evidence'].append({'quote_en':'Stop by the bookcase.', 'quote_zh':'停在书架旁。'})
        v4.validate_v004(a, REQ)
        for quote in ('turn right ... Stop by', 'Turn right at the fork', 'turn right Stop by'):
            a['instruction_evidence'][0]['quote_en'] = quote
            with self.subTest(quote=quote), self.assertRaises(ValueError):
                v4.validate_v004(a, REQ)
        a = example(REQ, 'deviated')
        a['visual_evidence'][0]['frames'] = [4]
        with self.assertRaises(ValueError):
            v4.validate_v004(a, REQ)

    def test_init_and_null_protocol(self):
        for verdict in ('uncertain', 'deviated'):
            a = example(REQ, verdict)
            v4.validate_v004(a, REQ)
            with self.assertRaises(ValueError):
                v4.validate_v004(a, dict(REQ, mode='initialization'))
            a['semantic_progress'] = PROGRESS
            with self.assertRaises(ValueError):
                v4.validate_v004(a, REQ)

    def test_sampling(self):
        self.assertEqual(review.uniform_between(0, 12), [1, 3, 6, 9, 11])
        self.assertEqual(review.uniform_between(5, 7), [6])
        self.assertEqual(review.uniform_between(10, 10), [])

    def test_wire_and_state(self):
        with tempfile.TemporaryDirectory() as place:
            site = Path(place)
            frames, paths = [], {}
            for t in range(39):
                data = f'frame{t}'.encode()
                key = review.sha(data)
                path = site / f'f{t}.png'
                path.write_bytes(data)
                frames.append(dict(image=key, frame=t, terminal=t == 38))
                paths[key] = str(path)
            nodes = [dict(id=f'S{i:02d}', index=t, emittedAt=t if t == 38 else t + 5, terminal_node=t == 38)
                     for i,t in enumerate((2, 6, 11, 22, 28, 32, 38), 1)]
            case = dict(case_number=1, case_index=0, nodes=nodes, episode_id='test', real_episode_id='test',
                        scene='test', terminal_frame=38, final_active_ids=[n['id'] for n in nodes],
                        instruction_en=REQ['instruction_en'], frames=frames, image_paths=paths, gt='private')
            original_client = httpx.Client
            wire = []
            verdicts = ['consistent', 'consistent', 'uncertain', 'consistent', 'consistent', 'deviated']
            prompt = (v4.VERSION / 'prompt_zh.txt').read_text()
            def fake(request):
                body = json.loads(request.content)
                system, user = body['messages']
                self.assertEqual(system['content'], prompt)
                parts = user['content']
                req = json.loads(parts[0]['text'])
                self.assertEqual(set(req), {'mode','previous_id','current_id','previous_frame','current_frame',
                                            'instruction_en','prior_semantic_progress','coverage'})
                req['images'] = []
                for label, image in zip(parts[1::2], parts[2::2]):
                    t = int(label['text'].split(' F')[1].strip('。'))
                    self.assertTrue(image['image_url']['url'].startswith('data:image/png;base64,'))
                    req['images'].append({'frame':t})
                reply = example(req, verdicts[len(wire)])
                if reply['verdict'] == 'deviated':
                    reply['type'] = 'json_object'
                if len(wire) == 3:  # An invalid quote after uncertainty must not advance A.
                    reply['instruction_evidence'][0]['quote_en'] = 'turn right ... bookcase'
                wire.append(req)
                return httpx.Response(200, json={'choices':[{'finish_reason':'stop', 'message':{'content':json.dumps(reply)}}]})
            def client(**kwargs):
                return original_client(transport=httpx.MockTransport(fake), **kwargs)
            def model_call(*args):
                return review.call_model(*args, api_base='http://127.0.0.1/v1', validate_answer=v4.validate_v004)
            with patch.object(review.httpx, 'Client', client), contextlib.redirect_stdout(io.StringIO()):
                result = review.run_case(case, str(site), 'local-test', prompt, {}, model_call=model_call)
            audit = v4.audit_case(case, site/'run/cases/C01', v4.validate_v004, prompt, {})
            self.assertEqual(len(wire), 6)
            self.assertEqual([r['previous_frame'] for r in wire], [2, 2, 6, 6, 6, 28])
            self.assertEqual([len(r['images']) for r in wire], [1, 5, 6, 7, 7, 5])
            self.assertTrue(all(r['prior_semantic_progress'] == PROGRESS['zh'] for r in wire[1:]))
            self.assertEqual(result['unreviewed_nodes'], ['S07'])
            self.assertEqual(audit['outcomes'], {'consistent':3, 'uncertain':1, 'format_error':1, 'deviated':1})
            self.assertEqual(audit['first_deviation']['from_frame'], 28)


if __name__ == '__main__':
    unittest.main()
