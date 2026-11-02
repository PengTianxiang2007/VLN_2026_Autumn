import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock
from core.vlnverse_runtime import (placement, retry_delay, failure_kind, RuntimeFailure,
    failure_record, worker_failure, needs_separate_gpus, wait_for_model_ready, OOMLogMonitor, log_tail)

class RuntimeTests(unittest.TestCase):
    def test_large_scene_separates_gpus_and_reserves_simulator_headroom(self):
        rows=[dict(index=0,free_mib=42000,utilization=0),dict(index=3,free_mib=48500,utilization=0)]
        self.assertEqual(placement(rows,[3,0],set(),True),(0,3))
        self.assertIsNone(placement(rows,[3,0],{0},True))
        self.assertIsNone(placement(rows,[3],set(),True))
        rows[1]['utilization']=100
        self.assertIsNone(placement(rows,[3,0],set(),True))

    def test_normal_scene_respects_busy_cards_and_free_memory(self):
        rows=[dict(index=0,free_mib=42000,utilization=0),dict(index=3,free_mib=33000,utilization=0)]
        self.assertEqual(placement(rows,[3,0],set()),(0,0))
        self.assertIsNone(placement(rows,[3,0],{0}))

    def test_retry_only_infrastructure_errors_with_finite_budget(self):
        self.assertEqual(failure_kind('VkResult: ERROR_OUT_OF_DEVICE_MEMORY'),'gpu_oom')
        self.assertEqual(failure_kind('Model loading timeout'),'model_startup_timeout')
        for kind in ('gpu_oom','model_startup_timeout','gpu_admission'):
            self.assertEqual([retry_delay(kind,n) for n in (1,2,3,4)],[60,120,240,None])
        self.assertIsNone(retry_delay(failure_kind('Invalid episode ID'),1))
        self.assertIsNone(retry_delay(failure_kind("TypeError: NoneType memory"),1))

    def test_model_startup_exit_retains_child_oom_and_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            chunk=Path(directory)
            with (chunk/'agent.log').open('w') as log:
                process=subprocess.Popen([sys.executable,'-c',
                    "raise RuntimeError('CUDA out of memory. Tried to allocate 130.00 MiB')"],
                    stdout=log,stderr=subprocess.STDOUT)
                process.wait(timeout=10)
            with self.assertRaises(RuntimeFailure) as raised:
                wait_for_model_ready(process,chunk)
            record=failure_record(raised.exception)
            self.assertEqual((record['kind'],record['phase'],record['returncode']),
                             ('gpu_oom','model_startup',1))
            self.assertIn('130.00 MiB',record['log_tail'])
            self.assertFalse(needs_separate_gpus(record))
            self.assertEqual(retry_delay(record['kind'],1),60)

    def test_startup_unknown_error_is_not_retried_or_disguised(self):
        with tempfile.TemporaryDirectory() as directory:
            chunk=Path(directory)
            (chunk/'agent.log').write_text("TypeError: 'NoneType' object is not subscriptable")
            with self.assertRaises(RuntimeFailure) as raised:
                wait_for_model_ready(Mock(poll=lambda:1),chunk)
            record=failure_record(raised.exception)
            self.assertEqual(record['kind'],'unclassified')
            self.assertIsNone(retry_delay(record['kind'],1))
            self.assertIn('NoneType',record['log_tail'])

    def test_readiness_and_timeout_keep_existing_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            chunk=Path(directory)
            process=Mock(poll=lambda:None)
            with self.assertRaises(RuntimeFailure) as raised:
                wait_for_model_ready(process,chunk,timeout=0)
            self.assertEqual(raised.exception.record['kind'],'model_startup_timeout')
            (chunk/'ready.json').write_text('{"port":12345}')
            self.assertEqual(wait_for_model_ready(process,chunk),{'port':12345})

    def test_admission_error_without_run_directory_uses_launch_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); log=root/'launch.log'
            log.write_text('RuntimeError: GPU 3 has 2000 MiB free; require 32000 MiB.')
            record=worker_failure(root/'missing_run/failure.json',log,1)
            self.assertEqual(record['kind'],'gpu_admission')
            self.assertFalse((root/'missing_run').exists())
            self.assertFalse(needs_separate_gpus(record))

    def test_oom_monitor_checks_final_output_and_split_markers(self):
        with tempfile.TemporaryDirectory() as directory:
            log=Path(directory)/'evaluator.log'; log.write_text('normal output\n')
            monitor=OOMLogMonitor(log,'simulator'); monitor.check(); monitor.check()
            with log.open('a') as stream: stream.write('ERROR_OUT_OF_DEVICE_')
            monitor.check()
            with log.open('a') as stream: stream.write('MEMORY\n')
            with self.assertRaises(RuntimeFailure) as raised: monitor.check()
            self.assertTrue(needs_separate_gpus(raised.exception.record))
            model=OOMLogMonitor(log,'model_inference')
            with self.assertRaises(RuntimeFailure) as raised: model.check()
            self.assertFalse(needs_separate_gpus(raised.exception.record))

    def test_log_tail_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            log=Path(directory)/'large.log'
            log.write_text('ignored prefix\n'+'x'*100000+'CUDA out of memory')
            self.assertEqual(len(log_tail(log)),65536)
            self.assertTrue(log_tail(log).endswith('CUDA out of memory'))
            self.assertNotIn('ignored prefix',log_tail(log))
