"""Fault injection through the real supervisor; no CUDA or model allocation."""
import importlib.util
import json
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('queue_recovery',ROOT/'scripts/reproduce_streamvln_vlnverse.py')
queue=importlib.util.module_from_spec(spec); spec.loader.exec_module(queue)


class QueueRecoveryTests(unittest.TestCase):
    def test_parallel_admission_is_limited_by_ram_and_worker_cap(self):
        self.assertTrue(queue.can_admit_worker(2,8,250000))
        self.assertFalse(queue.can_admit_worker(3,8,250000))
        self.assertFalse(queue.can_admit_worker(2,2,250000))
        self.assertFalse(queue.can_admit_worker(0,8,65535))

    def test_progress_keeps_paused_partial_results_without_double_counting(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            units=[dict(run_id=s,expected=25) for s in ('complete','paused','active')]
            manifest=dict(runtime_env={'VLN_OUTPUT_ROOT':str(root/'runs')},units=units)
            completed=queue.run_path(manifest,units[0]); completed.mkdir(parents=True)
            (completed/'result.json').write_text('{}')
            for run_id,count in [('complete',25),('paused',6),('active',1)]:
                log=root/'benchmarks/vlnverse/upstream/logs'/run_id/'kujiale_result.json'
                log.parent.mkdir(parents=True)
                log.write_text(json.dumps({'val_unseen':{'Count':count}}))
            counts=queue.partial_counts(manifest,root)
            self.assertEqual(counts,{'paused':6,'active':1})
            # A worker can publish result.json just before collect() sees it.
            active=queue.run_path(manifest,units[2]); active.mkdir(parents=True)
            (active/'result.json').write_text('{}')
            self.assertEqual(queue.partial_counts(manifest,root,completed={'complete'}),counts)
            (active/'result.json').unlink()
            log.write_text('{')
            self.assertEqual(queue.partial_counts(manifest,root,counts),counts)
            log.write_text('{"val_unseen":{"Count":26}}')
            with self.assertRaisesRegex(RuntimeError,'Invalid partial'): queue.partial_counts(manifest,root)

    def run_failure(self, kind, phase, persistent=False, early=False):
        with tempfile.TemporaryDirectory() as directory:
            campaign=Path(directory); clock=[0]; attempts=[]; finished=set()
            units=[dict(seed=2,scene=s,expected=1,run_id=s) for s in ('failure','healthy')]
            manifest=dict(code_root=str(campaign),code_sha256={},
                runtime_env={'VLN_OUTPUT_ROOT':str(campaign/'runs')},code_commit='fixture',units=units)
            (campaign/'manifest.json').write_text(json.dumps(manifest))
            (campaign/'model_fingerprints.json').write_text('{"files":[]}')
            (campaign/'first_scene_gate.json').write_text('{}')

            class Process:
                def __init__(self,command,**kwargs):
                    scene=command[command.index('--scenes')+1]
                    self.failed=scene=='failure' and (persistent or scene not in attempts)
                    self.pid=100+len(attempts); self.returncode=None
                    path=queue.run_path(manifest,units[0 if scene=='failure' else 1])
                    if scene=='failure' and early:
                        # No empty run directory may be left by admission recovery.
                        assert not path.exists()
                    attempts.append(scene)
                    if self.failed and early:
                        kwargs['stdout'].write('RuntimeError: GPU 3 has 2000 MiB free; require 32000 MiB.\n')
                    else:
                        path.mkdir(parents=True,exist_ok=True)
                        if self.failed:
                            (path/'failure.json').write_text(json.dumps(dict(kind=kind,phase=phase)))
                        else:
                            (path/'result.json').write_text('{}'); (path/'validation.json').write_text('{}')
                            finished.add(scene)
                def poll(self):
                    self.returncode=1 if self.failed else 0
                    return self.returncode

            def collect(*args):
                return dict(completed_units=len(finished),completed_episode_runs=len(finished),
                            completed_run_ids=list(finished),complete=False)
            def sleep(seconds): clock[0]+=seconds
            handlers={s:signal.getsignal(s) for s in (signal.SIGTERM,signal.SIGHUP)}
            try:
                with patch.object(queue,'collect',collect), \
                     patch.object(queue,'gpu_rows',lambda:[dict(index=i,free_mib=48000,utilization=0) for i in (0,1)]), \
                     patch.object(queue,'available_memory_mib',lambda:100000), \
                     patch.object(queue,'check_gpu',lambda *args:None), \
                     patch.object(queue.subprocess,'Popen',Process), \
                     patch.object(queue.time,'sleep',sleep), \
                     patch.object(queue.time,'monotonic',lambda:clock[0]):
                    with self.assertRaisesRegex(RuntimeError,'Campaign incomplete'):
                        queue.run(campaign,[0,1],2,True)
            finally:
                for signum,handler in handlers.items(): signal.signal(signum,handler)
            recovery=json.loads((campaign/'recovery.json').read_text())
            self.assertIn('healthy',finished)
            self.assertEqual(attempts.count('healthy'),1)
            return recovery,attempts,finished

    def test_loading_oom_retries_and_other_unit_completes(self):
        recovery,attempts,finished=self.run_failure('gpu_oom','model_startup')
        self.assertEqual(attempts,['failure','healthy','failure'])
        self.assertEqual(finished,{'failure','healthy'})
        self.assertEqual(recovery['blocked'],{})
        self.assertNotIn('failure',recovery['separate_scenes'])

    def test_preflight_failure_before_run_creation_can_retry(self):
        recovery,attempts,finished=self.run_failure('gpu_admission','launcher',early=True)
        self.assertEqual(finished,{'failure','healthy'})
        self.assertEqual(attempts.count('failure'),2)

    def test_simulator_oom_alone_changes_scene_placement(self):
        recovery,attempts,finished=self.run_failure('gpu_oom','simulator')
        self.assertIn('failure',recovery['separate_scenes'])
        self.assertEqual(finished,{'failure','healthy'})

    def test_persistent_oom_has_bounded_retry_budget(self):
        recovery,attempts,finished=self.run_failure('gpu_oom','model_startup',persistent=True)
        self.assertEqual(attempts.count('failure'),4)
        self.assertIn('failure',recovery['blocked'])
        self.assertEqual(finished,{'healthy'})

    def test_unknown_model_error_blocks_without_retry(self):
        recovery,attempts,finished=self.run_failure('unclassified','model_startup',persistent=True)
        self.assertEqual(attempts.count('failure'),1)
        self.assertIn('failure',recovery['blocked'])
