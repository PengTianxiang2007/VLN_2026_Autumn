import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from core.oracle_distance_native import install_retention, install
from core.oracle_distance_runtime import DistanceOracle
from scripts.run_oracle_existing_model import collect_trace, stop_simulator, assert_model, retry_failures, validate_resume, NativeScoreCounter


class ExistingModelTests(unittest.TestCase):
    def test_baseline_retains_only_close_without_oracle_policy_hooks(self):
        e=NS(env=NS(close=Mock()),get_action=Mock(),reset_seeded_agent=Mock(),terminate_ops=Mock())
        originals=(e.get_action,e.reset_seeded_agent,e.terminate_ops)
        with patch.dict('os.environ',{'VLN_SIM_RETAIN_FILE':'/tmp/marker',
                'VLN_NATIVE_RESULT_FILE':'/tmp/score','VLN_EXPECTED_EPISODES':'400'},clear=True), \
                patch('core.oracle_distance_native.NativeDistanceHook') as hook, \
                patch('core.oracle_distance_native.install_retention') as retention:
            install(e);install(e)
            hook.assert_not_called();retention.assert_called_once()
        self.assertEqual(originals,(e.get_action,e.reset_seeded_agent,e.terminate_ops))

    def test_score_polling_tolerates_native_in_place_write_without_losing_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'score.json';count=NativeScoreCounter(path)
            self.assertEqual(count(),0)
            path.write_text('{"val_unseen":{"Count":8}}');self.assertEqual(count(),8)
            for partial in ['', '{"val_unseen":', '{"val_unseen":{"Count":9']:
                path.write_text(partial);self.assertEqual(count(),8)
            path.write_text('{"val_unseen":{"Count":9}}');self.assertEqual(count(),9)
            path.write_text('{"val_unseen":{"Count":8}}')
            with self.assertRaises(RuntimeError):count()

    def test_simulator_retry_counts_only_consecutive_chunks_without_progress(self):
        self.assertEqual(retry_failures(0,8,8),1)
        self.assertEqual(retry_failures(1,8,8),2)
        self.assertEqual(retry_failures(2,8,9),0)
        with self.assertRaises(RuntimeError):retry_failures(2,8,8)

    def test_checkpoint_rpc_keys_are_unique_per_attempt_and_stable_for_restore(self):
        first=DistanceOracle.__new__(DistanceOracle);first.case_root=Path('/tmp/campaign/task/attempt_1')
        second=DistanceOracle.__new__(DistanceOracle);second.case_root=Path('/tmp/campaign/task/attempt_2')
        with patch('core.oracle_branching.BranchOracle.rpc',return_value={}) as rpc:
            first.rpc('save','task_checkpoint');first.rpc('restore','task_checkpoint');second.rpc('save','task_checkpoint')
        calls=rpc.call_args_list
        self.assertEqual(calls[0].args[1],calls[1].args[1])
        self.assertNotEqual(calls[0].args[1],calls[2].args[1])

    def test_resume_preserves_original_evidence_offset_and_rejects_changed_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);trace=base/'trace';trace.write_text('old\nnew\n')
            saved={'pid':123,'start_ticks':'1','command':'test service'}
            meta={'run_id':'run','gpu':3,'borrowed_model_port':40617,'borrowed_model':saved}
            borrowed={'identity':saved,'trace':str(trace),'trace_offset':4}
            (base/'run.json').write_text(json.dumps(meta))
            (base/'borrowed_model.json').write_text(json.dumps(borrowed))
            (base/'owned_processes.json').write_text(json.dumps({'evaluator_pid':999999999}))
            args=NS(run_id='run',gpu=3,port=40617,model_trace=trace)
            with patch('scripts.run_oracle_existing_model.verify_resume'):
                actual,proof=validate_resume(base,{'seed':2},args,saved,[])
                self.assertEqual(actual,meta);self.assertEqual(proof['trace_offset'],4)
                with self.assertRaises(RuntimeError):
                    validate_resume(base,{'seed':2},args,dict(saved,start_ticks='2'),[])
            self.assertEqual(json.loads((base/'borrowed_model.json').read_text()),borrowed)

    def test_native_rss_exit_does_not_retain_incomplete_simulator(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);scores=base/'scores.json';marker=base/'retain.json'
            scores.write_text(json.dumps({'val_unseen':{'Count':2}}))
            close=Mock();e=NS(env=NS(close=close))
            install_retention(e,marker,scores,33);e.env.close()
            close.assert_called_once();self.assertFalse(marker.exists())

    def test_complete_simulator_waits_before_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);scores=base/'scores.json';marker=base/'retain.json'
            scores.write_text(json.dumps({'val_unseen':{'Count':33}}))
            close=Mock();e=NS(env=NS(close=close));install_retention(e,marker,scores,33)
            def release(_):
                self.assertTrue(marker.exists());close.assert_not_called()
                marker.with_suffix('.release').touch()
            with patch('core.oracle_distance_native.time.sleep',side_effect=release):e.env.close()
            close.assert_called_once()

    def test_after_checkpoint_return_policy_never_intervened_again(self):
        o=DistanceOracle.__new__(DistanceOracle)
        o.settings={'mode':'checkpoint'};o.completed_interventions=[{}]
        o.task=lambda e:NS(is_done=lambda:False)
        o.policy=Mock(side_effect=AssertionError('No further Oracle policy request'))
        ob={'globalgps':[99,99,0]}
        result,ended=o.automatic_review(None,ob,{'threshold_reached':True,'distance_m':100})
        self.assertIs(result,ob);self.assertFalse(ended);o.policy.assert_not_called()

    def test_trace_is_sliced_at_retained_service_handover(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);source=p/'source';destination=p/'new'
            old=b'{"episode_id":"cancelled"}\n';new=b'{"episode_id":"new"}\n'
            source.write_bytes(old+new);proof=collect_trace(source,len(old),destination)
            self.assertEqual(destination.read_bytes(),new);self.assertEqual(proof['offset'],len(old))

    def test_cleanup_only_stops_the_owned_simulator(self):
        child=Mock(pid=321);child.poll.return_value=None
        with patch('scripts.run_oracle_existing_model.os.killpg') as kill:
            stop_simulator(child);kill.assert_called_once_with(321,__import__('signal').SIGTERM)
        with patch('scripts.run_oracle_existing_model.identity',return_value={'pid':1,'start_ticks':'new'}):
            with self.assertRaises(RuntimeError):assert_model({'pid':1,'start_ticks':'old'})


if __name__=='__main__':unittest.main()
