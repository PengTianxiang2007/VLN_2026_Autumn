import base64
from collections import Counter
from contextlib import ExitStack, redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run_deviation_progress_v004 as runner
import run_deviation_progress_v004_deepseek as deepseek
from test_deviation_progress_v004 import PROGRESS, REQ, example


PROMPTS = ROOT / 'experiments/deviation_progress/v005'
ARCHIVE = ROOT / 'outputs/deviation_progress/v004'
ARCHIVED_SIX = [
    (ARCHIVE / 'run_20261120_01/qwen_gpu2_01', 35, 20),
    (ARCHIVE / 'run_20261120_03_contract_replay', 29, 7),
]


class BinaryReview(unittest.TestCase):
    def test_prompts_offer_two_verdicts_and_keep_uncertainties(self):
        for lang, choices in [('zh', 'verdict：consistent 或 deviated。'),
                              ('en', 'verdict: consistent or deviated.')]:
            with self.subTest(lang=lang):
                prompt = (PROMPTS / f'prompt_{lang}.txt').read_text()
                self.assertIn(choices, prompt.splitlines())
                self.assertNotRegex(prompt, r'\buncertain\b')
                self.assertIn('uncertainties', prompt)
                self.assertIn('uncertain', (runner.VERSION / f'prompt_{lang}.txt').read_text())

    def test_contract_keeps_progress_and_original_c47_alarm(self):
        valid = example(REQ, 'consistent')
        valid['uncertainties'] = [{'zh': '入口不清楚。', 'en': 'The entrance is unclear.'}]
        self.assertEqual(runner.validate_v005(valid, REQ), valid)
        fixture = runner.read(ROOT / 'tests/fixtures/deviation_v004_c47_s04.json')
        raw, req = fixture['answer'], fixture['request']
        self.assertEqual(runner.validate_v005(raw, req), runner.validate_v004(raw, req))
        self.assertEqual(raw['type'], 'json_object')
        for bad, request in ((dict(raw, semantic_progress=PROGRESS), req),
                             (dict(raw, instruction_evidence=[]), req),
                             (dict(valid, semantic_progress=None), REQ),
                             (dict(valid, verdict='unknown'), REQ)):
            with self.subTest(bad=bad['verdict']), self.assertRaises(ValueError):
                runner.validate_v005(bad, request)
        with self.assertRaises(ValueError):
            runner.validate_v005(raw, dict(req, mode='initialization'))

    def test_model_entries_reject_third_verdict_without_advancing(self):
        prompt = (PROMPTS / 'prompt_zh.txt').read_text()
        original_client = httpx.Client
        for model in ('qwen', 'deepseek'):
            with self.subTest(model=model), tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
                out = Path(tmp)
                image = out / 'front.png'
                image.write_bytes(base64.b64decode(
                    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jZV0AAAAASUVORK5CYII='))
                image_id = runner.file_hash(image)
                nodes = [dict(id=f'S{i:02d}', index=t, emittedAt=t if t == 30 else t + 5,
                              terminal_node=t == 30) for i, t in enumerate((2, 9, 15, 24, 30), 1)]
                case = dict(case_number=1, case_index=0, episode_id='test', real_episode_id='test',
                            scene='test', instruction_en=REQ['instruction_en'], nodes=nodes,
                            frames=[{'image': image_id, 'terminal': t == 30} for t in range(31)],
                            image_paths={image_id: str(image)}, terminal_frame=30,
                            final_active_ids=[node['id'] for node in nodes])
                # S02 adds no milestone. S03 deliberately violates the output contract.
                replies = iter(['consistent', 'consistent', 'uncertain', 'deviated'])
                def respond(request):
                    system, user = json.loads(request.content)['messages']
                    self.assertEqual(system['content'], prompt)
                    req = json.loads(user['content'][0]['text'])
                    req['images'] = [{'frame': req['current_frame']}]
                    answer = example(req, next(replies))
                    if answer['verdict'] == 'deviated':
                        answer['type'] = 'json_object'
                    return httpx.Response(200, json={'choices': [
                        {'finish_reason': 'stop', 'message': {'content': json.dumps(answer)}}]})

                transport = httpx.MockTransport(respond)
                stack.enter_context(patch.object(httpx, 'Client',
                                                 lambda **kw: original_client(transport=transport, **kw)))
                stack.enter_context(redirect_stdout(io.StringIO()))
                if model == 'deepseek':
                    audit = deepseek.worker(case, out, 'test-key', prompt, {}, 'v005')
                else:
                    stack.enter_context(patch.dict(os.environ))
                    stack.enter_context(patch.object(runner.signal, 'signal'))
                    stack.enter_context(patch('run_human_route_choice.start_local',
                                              return_value=(SimpleNamespace(pid=1), 'http://localhost/v1')))
                    stack.enter_context(patch('run_agent_route_choice.wait_local'))
                    stack.enter_context(patch('run_crossing_local_batch.cleanup', return_value=[]))
                    stack.enter_context(patch('test_crossing_single_gpu.gpu_snapshot', return_value=[]))
                    audit, = runner.run_local(out, [case], prompt, {'model': 'test'}, {}, 0, False, version='v005')
                    self.assertEqual(runner.read(out / 'v005_results.json'), [audit])
                self.assertEqual(audit['outcomes'], {'consistent': 2, 'format_error': 1, 'deviated': 1})
                self.assertEqual([r['previous'] for r in audit['rounds']], ['S01', 'S01', 'S02', 'S02'])
                folder = out / 'run/cases/C01'
                rejected = runner.read(folder / 'S03.response.json')
                self.assertEqual(rejected['parsed_original']['verdict'], 'uncertain')
                self.assertNotIn('answer', rejected)
                result = runner.read(folder / 'result.json')
                self.assertEqual(result['reviews'][-1]['rollback_target'],
                                 {'node_id': 'S02', 'frame': 9, 'progress': PROGRESS})
                self.assertEqual(result['unreviewed_nodes'], ['S05'])

    @unittest.skipUnless(all((path / 'v004_results.json').is_file() for path, _, _ in ARCHIVED_SIX),
                         'requires the frozen six-case v004 archives')
    def test_six_case_archives_preserve_binary_answers_and_reject_uncertain(self):
        for path, rounds, uncertain in ARCHIVED_SIX:
            counts = Counter()
            for number in (7, 11, 19, 30, 47, 50):
                folder = path / f'run/cases/C{number:02d}'
                for item in runner.read(folder / 'result.json')['reviews']:
                    stem = folder / item['node_id']
                    req = runner.read(stem.with_suffix('.request.json'))
                    response = runner.read(stem.with_suffix('.response.json'))
                    raw = json.loads(response['response']['choices'][0]['message']['content'])
                    if raw['verdict'] == 'uncertain':
                        with self.assertRaisesRegex(ValueError, 'v005 verdict'):
                            runner.validate_v005(raw, req)
                    else:
                        self.assertEqual(runner.validate_v005(raw, req), item['answer'])
                    counts[raw['verdict']] += 1
            self.assertEqual((sum(counts.values()), counts['uncertain']), (rounds, uncertain))
