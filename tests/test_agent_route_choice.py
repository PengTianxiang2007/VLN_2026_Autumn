"""CPU-only protocol tests. Fake responses live only in temporary directories."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.agent_route_choice import (build_messages, digest, file_hash, payload, read,
    validate_case, validate_choice, validate_inventory, write)
from scripts.prepare_agent_route_choice import choose_rows
from scripts.report_agent_route_choice import create_review, score
from scripts.export_agent_route_choice import check_translation
from scripts.run_agent_route_choice import (call_model, cleanup_case_workers, main, read_stream, run_case,
                                            start_case_workers, wait_case_workers)


def sample(root, sid='sample_01'):
    images = []
    for frame in (2, 5, 6, 8):
        path = root / 'images' / sid / ('F%04d.png' % frame)
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'fake-test-png-' + str(frame).encode())
        images.append({'id': 'F%04d' % frame, 'frame': frame,
                       'phase': 'checkpoint_context' if frame <= 5 else 'wrong_attempt',
                       'path': str(path.relative_to(root)), 'sha256': file_hash(path)})
    return {'sample_id': sid, 'instruction': 'Turn left into the kitchen.', 'checkpoint_frame': 5, 'wrong_end_frame': 8,
            'images': images, 'approach_actions': [{'frame': 4, 'action': 'FORWARD'}],
            'attempt_actions': [{'frame': n, 'action': 'FORWARD'} for n in (5, 6, 7)]}


def inventory():
    return {'view_summary': 'Two openings', 'branches': [
        {'id': 'B1', 'direction': 'left', 'landmark': 'open doorway', 'destination_hypothesis': 'kitchen-like room', 'incoming': 'no', 'evidence_ids': ['F0005']},
        {'id': 'B2', 'direction': 'front', 'landmark': 'corridor', 'destination_hypothesis': 'hall', 'incoming': 'no', 'evidence_ids': ['F0005']}],
        'coverage': 'partial', 'uncertainties': ['The far room is partially occluded.']}


def choice():
    return {'status': 'selected', 'wrong_branch_id': 'B2', 'wrong_branch_evidence_ids': ['F0008'],
            'error_reason': 'Entered corridor instead of left doorway.', 'instruction_evidence': ['Turn left'],
            'excluded_branch_ids': ['B2'], 'selected_branch_id': 'B1', 'selected_direction': 'left',
            'route_description': 'Enter the left doorway', 'selection_evidence_ids': ['F0005'],
            'confidence': 'medium', 'uncertainties': []}


class InputBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.case = sample(self.root)

    def test_first_call_never_receives_task_or_error(self):
        messages = build_messages(self.case, self.root, 1, 'inventory prompt')
        metadata = json.loads(messages[1]['content'][0]['text'])
        self.assertNotIn('instruction', metadata)
        self.assertNotIn('branch_inventory', metadata)
        self.assertEqual([i['frame'] for i in metadata['image_order']], [2, 5])
        self.assertEqual([m['role'] for m in messages], ['system', 'user'])
        self.assertNotIn(self.case['instruction'], json.dumps(messages))

    def test_second_call_explicitly_receives_same_model_inventory(self):
        messages = build_messages(self.case, self.root, 2, 'choose prompt', inventory())
        metadata = json.loads(messages[1]['content'][0]['text'])
        self.assertEqual(metadata['branch_inventory'], inventory())
        self.assertEqual(metadata['instruction'], self.case['instruction'])
        self.assertEqual(metadata['current_view_id'], 'F0005')
        self.assertEqual([m['role'] for m in messages], ['system', 'user'])

    def test_evaluation_fields_are_rejected(self):
        for key in ('reference_path', 'expected_route', 'position', 'review', 'final_success'):
            c = copy.deepcopy(self.case); c[key] = 'secret evaluator label'
            with self.assertRaises(ValueError):
                build_messages(c, self.root, 1, 'prompt')

    def test_later_image_cannot_be_labelled_checkpoint_context(self):
        c = copy.deepcopy(self.case); c['images'][-1]['phase'] = 'checkpoint_context'
        with self.assertRaises(ValueError): validate_case(c)

    def test_pending_checkpoint_action_is_excluded_from_first_call(self):
        c = copy.deepcopy(self.case); c['approach_actions'].append({'frame': 5, 'action': 'LEFT'})
        with self.assertRaises(ValueError): validate_case(c)

    def test_action_at_error_endpoint_is_not_yet_executed(self):
        c = copy.deepcopy(self.case); c['attempt_actions'].append({'frame': 8, 'action': 'LEFT'})
        with self.assertRaises(ValueError): validate_case(c)

    def test_image_hash_change_is_rejected(self):
        (self.root / self.case['images'][0]['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError): build_messages(self.case, self.root, 1, 'prompt')

    def test_terminal_reused_frames_not_used_to_fill_missing_evidence(self):
        rows = [{'frame': i, 'terminal': i == 9, 'rgb_reused': i == 8} for i in range(10)]
        context, attempt = choose_rows(rows, {'review': {'decision_frame': '5', 'highlight_end_frame': '9'}},
                                       {'context_window_observations': 16, 'checkpoint_context_images': 4, 'wrong_attempt_images': 4})
        self.assertEqual(context[-1]['frame'], 5)
        self.assertEqual([r['frame'] for r in attempt], [6, 7])


class OutputProtocolTests(unittest.TestCase):
    def test_translation_keeps_an_invalid_original_decision(self):
        original = choice(); original.update(selected_branch_id='B2', selected_direction='front')
        translated = copy.deepcopy(original); translated['error_reason'] = '模型原始错误原因的中文译文。'
        self.assertEqual(check_translation(original, translated, 2)['selected_branch_id'], 'B2')
        translated['selected_branch_id'] = 'B1'
        with self.assertRaises(ValueError): check_translation(original, translated, 2)

    def test_translation_cannot_change_inventory_evidence_or_orientation(self):
        original = inventory()
        for key, value in [('direction', 'right'), ('evidence_ids', ['F0008']), ('incoming', 'yes')]:
            translated = copy.deepcopy(original); translated['branches'][0][key] = value
            with self.assertRaises(ValueError): check_translation(original, translated, 1)

    def test_wrong_branch_cannot_be_selected(self):
        c = choice(); c.update(selected_branch_id='B2', selected_direction='front')
        with self.assertRaises(ValueError): validate_choice(c, inventory(), ['F0005', 'F0008'], 'Turn left into the kitchen.')

    def test_unknown_branch_or_changed_orientation_rejected(self):
        for field, value in [('selected_branch_id', 'B3'), ('selected_direction', 'right')]:
            c = choice(); c[field] = value
            with self.assertRaises(ValueError): validate_choice(c, inventory(), ['F0005', 'F0008'], 'Turn left into the kitchen.')

    def test_evidence_cannot_cite_unseen_images(self):
        inv = inventory(); inv['branches'][0]['evidence_ids'] = ['F0099']
        with self.assertRaises(ValueError): validate_inventory(inv, ['F0005'])

    def test_task_quotes_cannot_be_invented(self):
        c = choice(); c['instruction_evidence'] = ['Turn right']
        with self.assertRaises(ValueError): validate_choice(c, inventory(), ['F0005', 'F0008'], 'Turn left into the kitchen.')

    def test_insufficient_view_can_abstain(self):
        c = choice(); c.update(status='insufficient_evidence', selected_branch_id=None, selected_direction=None,
                               selection_evidence_ids=[], uncertainties=['Correct entrance is not visible.'])
        self.assertEqual(validate_choice(c, inventory(), ['F0005', 'F0008'], 'Turn left into the kitchen.'), c)

    def test_backend_specific_settings_do_not_change_messages(self):
        messages = [{'role': 'system', 'content': 'same task'}]
        glm = payload(messages, {'backend': 'glm', 'model': 'glm', 'max_tokens': 32768, 'reasoning_effort': 'low'}, 's', 1)
        qwen = payload(messages, {'backend': 'qwen_local', 'model': 'q', 'max_tokens': 8192, 'seed': 2}, 's', 1)
        self.assertEqual(glm['messages'], qwen['messages'])
        self.assertNotIn('seed', glm)
        self.assertEqual(qwen['chat_template_kwargs'], {'enable_thinking': False})


class OrchestrationTests(unittest.TestCase):
    def test_rate_limit_waits_and_records_redacted_provider_reason(self):
        import urllib.error
        key = 'synthetic-test-secret'
        error = urllib.error.HTTPError('https://open.bigmodel.cn/api/paas/v4/chat/completions', 429,
            'rate limited', {'Retry-After': '40'}, io.BytesIO(json.dumps(
                {'error': {'code': 'rate-limit', 'message': 'Rejected ' + key}}).encode()))
        response = io.BytesIO(b'data: {"choices":[{"delta":{"content":"{}"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n')
        config = {'backend': 'glm', 'request_deadline_seconds': 1200, 'request_timeout_seconds': 60,
                  'max_network_attempts': 2, 'retry_backoff_base_seconds': 30,
                  'retry_backoff_cap_seconds': 120, 'retry_jitter_seconds': 10}
        with tempfile.TemporaryDirectory() as tmp, \
             patch('scripts.run_agent_route_choice.urllib.request.build_opener') as opener, \
             patch('scripts.run_agent_route_choice.time.sleep') as sleep, \
             patch('scripts.run_agent_route_choice.random.SystemRandom.uniform', return_value=2):
            opener.return_value.open.side_effect = [error, response]
            log = Path(tmp) / 'transport.jsonl'
            result = call_model('https://open.bigmodel.cn/api/paas/v4/chat/completions', {}, key, config, log)
            self.assertEqual(result['content'], '{}')
            sleep.assert_called_once_with(42)
            records = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(records[0]['provider_error']['code'], 'rate-limit')
            self.assertNotIn(key, log.read_text())

    def test_ten_processes_isolate_one_case_failure(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = [{'sample_id': 'sample_%02d' % i} for i in range(1, 11)]
            def fake_case(case, prepared, output, config, endpoint, key):
                self.assertEqual(key, 'synthetic-in-memory-test-key')
                write(output / 'cases' / case['sample_id'] / 'test_pid.json', {'pid': os.getpid()})
                if case['sample_id'] == 'sample_03':
                    raise ValueError('Synthetic case failure')
                write(output / 'cases' / case['sample_id'] / 'status.json', {'phase': 'complete_pending_semantic_review'})
            updates = []
            with patch('scripts.run_agent_route_choice.run_case', side_effect=fake_case):
                workers = start_case_workers(cases, root, root, {'concurrency': 10}, 'no-network', 'synthetic-in-memory-test-key')
                try:
                    failures = wait_case_workers(workers, root, lambda **kw: updates.append(kw), 20)
                finally:
                    cleaned = cleanup_case_workers(workers)
            self.assertEqual(len({p.pid for _, p in workers}), 10)
            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0]['sample_id'], 'sample_03')
            self.assertEqual(updates[-1]['completed_samples'], 9)
            self.assertTrue(all(not r['alive'] for r in cleaned))
            self.assertNotIn(os.getpid(), {read(root / 'cases' / c['sample_id'] / 'test_pid.json')['pid'] for c in cases})

    def test_32b_requires_two_gpus_before_launch(self):
        with patch('scripts.run_agent_route_choice.verify_prepared', return_value={'cases': [{}] * 10}), \
             patch('scripts.run_agent_route_choice.read', return_value={'qwen32b': {'backend': 'qwen_local', 'tensor_parallel_size': 2}}), \
             patch('scripts.run_agent_route_choice.start_local', side_effect=AssertionError('must reject before launch')), \
             patch('sys.stderr', new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as ctx:
                main(['--prepared', '/tmp/not_real', '--model', 'qwen32b', '--output', '/tmp/not_created', '--gpus', '0', '--execute'])
            self.assertEqual(ctx.exception.code, 2)

    def test_default_dry_run_never_requests_key_network_or_gpu(self):
        with patch('scripts.run_agent_route_choice.verify_prepared', return_value={'cases': [{}] * 10}), \
             patch('scripts.run_agent_route_choice.read', return_value={'glm': {}}), \
             patch('scripts.run_agent_route_choice.call_model', side_effect=AssertionError('network forbidden')), \
             patch('scripts.run_agent_route_choice.start_local', side_effect=AssertionError('GPU forbidden')), \
             patch('scripts.run_agent_route_choice.getpass.getpass', side_effect=AssertionError('credential forbidden')), \
             patch('sys.stdout', new_callable=io.StringIO) as capture:
            self.assertEqual(main(['--prepared', '/tmp/not_real', '--model', 'glm']), 0)
            self.assertEqual(json.loads(capture.getvalue())['model_calls'], 0)

    def test_two_calls_are_separate_and_second_uses_actual_first_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); prepared = root / 'prepared'; prepared.mkdir(); c = sample(prepared)
            (prepared / 'prompts').mkdir()
            for name in ('01_inventory_en.txt', '02_choose_en.txt'): (prepared / 'prompts' / name).write_text('test prompt')
            requests = []
            def fake(endpoint, wire, key, config, log):
                requests.append(wire)
                return {'content': json.dumps(inventory() if len(requests) == 1 else choice()), 'finish_reason': 'stop'}
            config = {'backend': 'glm', 'model': 'test', 'max_tokens': 100, 'reasoning_effort': 'low'}
            run_case(c, prepared, root / 'run', config, 'not-a-network-address', None, request_fn=fake)
            self.assertEqual(len(requests), 2)
            self.assertEqual(json.loads(requests[1]['messages'][1]['content'][0]['text'])['branch_inventory'], inventory())
            self.assertEqual([m['role'] for m in requests[1]['messages']], ['system', 'user'])

    def test_truncated_first_response_does_not_trigger_second_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); c = sample(root); (root / 'prompts').mkdir()
            (root / 'prompts/01_inventory_en.txt').write_text('test')
            with patch('scripts.run_agent_route_choice.call_model') as unused:
                calls = []
                def fake(*args): calls.append(1); return {'content': '{}', 'finish_reason': 'length'}
                with self.assertRaises(ValueError):
                    run_case(c, root, root / 'run', {'backend': 'glm', 'model': 'test', 'max_tokens': 100, 'reasoning_effort': 'low'}, 'test', None, request_fn=fake)
                self.assertEqual(calls, [1]); unused.assert_not_called()

    def test_stream_requires_finish_and_discards_reasoning_text(self):
        chunks = [b'data: {"choices":[{"delta":{"reasoning_content":"private reasoning","content":"{}"},"finish_reason":"stop"}]}\n', b'data: [DONE]\n']
        result = read_stream(chunks, float('inf'))
        self.assertEqual(result['content'], '{}')
        self.assertNotIn('private reasoning', json.dumps(result))
        with self.assertRaises(ConnectionError): read_stream([b'data: [DONE]\n'], float('inf'))


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name); self.prepared = root / 'prepared'; self.run = root / 'run'
        self.prepared.mkdir(); self.run.mkdir()
        cases = [sample(self.prepared, 'sample_%02d' % i) for i in range(1, 11)]
        write(self.prepared / 'manifest.json', {'fixture': 'synthetic test only'})
        write(self.prepared / 'dataset.json', {'cases': cases})
        write(self.prepared / 'evaluation_only.json', {'labels': [{'sample_id': c['sample_id'], 'episode_id': c['sample_id'], 'expected_route': 'kitchen', 'wrong_route': 'hall'} for c in cases]})
        write(self.prepared / 'manifest.json', {'files_sha256': {name: file_hash(self.prepared / name) for name in ('dataset.json', 'evaluation_only.json')}})
        write(self.run / 'manifest.json', {'sample_order': [c['sample_id'] for c in cases], 'prepared_manifest_sha256': file_hash(self.prepared / 'manifest.json')})
        for c in cases:
            folder = self.run / 'cases' / c['sample_id']
            write(folder / 'call1_answer.json', inventory()); write(folder / 'call2_answer.json', choice())
            write(folder / 'status.json', {'phase': 'complete_pending_semantic_review'})
        self.review = root / 'review.json'; create_review(self.prepared, self.run, self.review)

    def test_valid_json_alone_never_becomes_semantic_success(self):
        result = score(self.prepared, self.run, self.review, self.run / 'summary.json')
        self.assertEqual(result['phase'], 'review_incomplete')
        self.assertIsNone(result['all_ten_rates'])

    def test_explicit_semantic_mapping_produces_all_ten_rate(self):
        grades = read(self.review)
        for g in grades['cases']:
            g.update(reviewed=True, reviewer='unit-test', evidence_ids=['F0005', 'F0008'], notes='Synthetic visual match',
                     branch_matches={'B1': 'expected_route', 'B2': 'wrong_route'}, error_reason_supported=True)
        write(self.review, grades)
        result = score(self.prepared, self.run, self.review, self.run / 'summary.json')
        self.assertEqual(result['all_ten_rates']['chosen_branch_correct'], 1.0)

    def test_reviews_are_bound_to_actual_answer_hashes(self):
        altered = choice(); altered['error_reason'] = 'changed after review'
        write(self.run / 'cases/sample_01/call2_answer.json', altered)
        with self.assertRaises(ValueError): score(self.prepared, self.run, self.review, self.run / 'summary.json')

    def test_evaluation_labels_cannot_change_after_freezing(self):
        labels = read(self.prepared / 'evaluation_only.json'); labels['labels'][0]['expected_route'] = 'altered label'
        write(self.prepared / 'evaluation_only.json', labels)
        with self.assertRaises(ValueError): score(self.prepared, self.run, self.review, self.run / 'summary.json')


if __name__ == '__main__':
    unittest.main()
