"""Offline contracts for the new serial composition; no API/model/GPU calls."""
import copy
import ast
import os
from enum import Enum
import json
from pathlib import Path
import sys
import tempfile
import subprocess
from types import SimpleNamespace as NS, ModuleType
import unittest
from unittest.mock import Mock, patch

import numpy as np
import httpx

from core.serial_pipeline import SerialDecisions, Sampler, SerialAPI, semantic_settings, save, normalize_deviation_container, validate_deviation
from core.serial_runtime import SerialHook, action_id, has_recovery_cycle
from scripts.prepare_serial_pipeline import patch_evaluator, inherit_previous_run
from scripts.run_serial_pipeline import validate_run, admit_simulator_gpu
from scripts.queue_serial_qwen import admissible
from core.serial_batch import batch_progress, record_episode_failure, exclude_failed_tasks


def verdict(kind='consistent',progress='progress'):
    return dict(verdict=kind,semantic_progress={'zh':progress,'en':progress} if kind=='consistent' else None)


class DecisionsTests(unittest.TestCase):
    def test_actual_parallel_language_lists_preserve_order_and_every_word(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/serial_deviation_parallel_uncertainties.json').read_text())
        original=copy.deepcopy(fixture['answer'])
        with self.assertRaisesRegex(ValueError,'Invalid uncertainties'):
            validate_deviation(original,fixture['request'])
        normalized,changed=normalize_deviation_container(original)
        self.assertTrue(changed); validate_deviation(normalized,fixture['request'])
        for lang in ('zh','en'):
            self.assertEqual([x[lang] for x in normalized['uncertainties']],original['uncertainties'][lang])
        self.assertEqual(original,fixture['answer'])
        self.assertEqual({k:v for k,v in normalized.items() if k!='uncertainties'},
                         {k:v for k,v in original.items() if k!='uncertainties'})
        for value in ({'zh':['a','b'],'en':['A']},{'zh':['a'],'en':[None]},
                      {'zh':['a'],'en':'A'},{'zh':['a'],'en':['A'],'extra':1}):
            bad=dict(original,uncertainties=value);n,c=normalize_deviation_container(bad)
            self.assertFalse(c)
            with self.assertRaises(ValueError): validate_deviation(n,fixture['request'])

    def test_actual_failed_deviation_keeps_verdict_and_all_words(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/serial_deviation_single_uncertainty.json').read_text())
        original=copy.deepcopy(fixture['answer'])
        with self.assertRaisesRegex(ValueError,'Invalid uncertainties'):
            validate_deviation(original,fixture['request'])
        with tempfile.TemporaryDirectory() as tmp:
            api=object.__new__(SerialAPI);api.directory=Path(tmp);api.sequence=1;api.ask=Mock(return_value=original)
            node=dict(id=fixture['request']['previous_id'],index=0)
            answer=api.deviation(node,node,[{'index':0}],fixture['request']['instruction_en'],{'zh':'prior'},initialization=True)
            self.assertEqual(answer['uncertainties'],[fixture['answer']['uncertainties']])
            self.assertEqual({k:v for k,v in answer.items() if k!='uncertainties'},
                             {k:v for k,v in original.items() if k!='uncertainties'})
            self.assertEqual(original,fixture['answer']);api.ask.assert_called_once()
            folder=Path(tmp)/'requests/00001_deviation'
            self.assertEqual(json.loads((folder/'normalized_answer.json').read_text()),answer)
            self.assertTrue(json.loads((folder/'normalization.json').read_text())['original_answer_preserved'])

    def test_normalization_does_not_supply_missing_translation_or_relax_decisions(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/serial_deviation_single_uncertainty.json').read_text())
        for value in (None,'unknown',{'zh':'未决'}, {'zh':'未决','en':''}):
            bad=dict(fixture['answer'],uncertainties=value);normalized,changed=normalize_deviation_container(bad)
            self.assertFalse(changed)
            with self.assertRaises(ValueError):validate_deviation(normalized,fixture['request'])
        bad=dict(fixture['answer'],verdict='invented');normalized,changed=normalize_deviation_container(bad)
        self.assertTrue(changed)
        with self.assertRaisesRegex(ValueError,'Invalid verdict'):validate_deviation(normalized,fixture['request'])
        valid=dict(fixture['answer'],uncertainties=[])
        self.assertEqual(normalize_deviation_container(valid),(valid,False))

    def test_real_frozen_sampler_transport(self):
        s=Sampler()
        try:
            rows=[s.push(.8,i) for i in range(12)]
            nodes=[r['node'] for r in rows if r.get('node')]
            self.assertTrue(nodes)
            for n in nodes: self.assertEqual(n['emittedAt']-n['index'],5)
        finally: s.close()

    def test_replacement_rewinds_progress_before_reviewing_new_node(self):
        api=Mock(); api.deviation.side_effect=[verdict(progress='old'),verdict(progress='new')]; api.dedup.return_value='same'
        d=SerialDecisions(api,'task',Mock(),sampler=Mock()); d.frames=[{}]*12
        d.node(dict(id='S01',index=3,emittedAt=8)); d.node(dict(id='S02',index=6,emittedAt=11))
        self.assertEqual(len(d.nodes),1); self.assertEqual(d.anchor['id'],'S02')
        args,kw=api.deviation.call_args
        self.assertTrue(kw['initialization']); self.assertNotEqual(args[4]['zh'],'old')

    def test_uncertain_keeps_trusted_anchor_and_deviation_requests_that_pose(self):
        api=Mock(); api.deviation.side_effect=[verdict(),verdict('uncertain'),verdict('deviated')]; api.dedup.return_value='different'
        d=SerialDecisions(api,'task',Mock(),sampler=Mock()); d.frames=[{}]*31
        for i in [0,10]: self.assertIsNone(d.node(dict(id='S%d'%i,index=i,emittedAt=i+5)))
        result=d.node(dict(id='S20',index=20,emittedAt=25))
        self.assertEqual(result['target']['index'],0); self.assertEqual(d.progress['zh'],'progress')

    def test_api_reviewer_receives_only_endpoint_interval(self):
        api=object.__new__(SerialAPI); api.ask=Mock(return_value={})
        frames=[dict(index=i,path='fake',sha256='fake',position=[99,99],reference_path=['forbidden']) for i in range(20)]
        with patch('core.serial_pipeline.validate_deviation',return_value={}):
            api.deviation(dict(id='a',index=2),dict(id='b',index=10),frames,'task',{'zh':'prior'})
        stage,request,images=api.ask.call_args.args
        self.assertEqual(stage,'deviation'); self.assertTrue(all(2<=f['index']<=10 for f,_ in images))
        self.assertNotIn('position',json.dumps(request)); self.assertNotIn('reference_path',json.dumps(request))

    def test_dedup_large_gap_requires_no_model(self):
        api=object.__new__(SerialAPI); api.ask=Mock()
        self.assertEqual(api.dedup(dict(index=0),dict(index=9),[]),'different'); api.ask.assert_not_called()

    def test_dedup_keeps_both_on_bad_json_but_transport_failure_is_fatal(self):
        api=object.__new__(SerialAPI); api.ask=Mock(side_effect=ValueError('invalid JSON'))
        nodes=[dict(id='S1',index=2),dict(id='S2',index=4)]; frames=[{}]*7
        self.assertEqual(api.dedup(*nodes,frames),'uncertain')
        api.ask.side_effect=RuntimeError('HTTP 401')
        with self.assertRaises(RuntimeError): api.dedup(*nodes,frames)


class ProviderTests(unittest.TestCase):
    config=dict(semantic_provider='qwen_local',semantic_endpoint='http://127.0.0.1:12345/v1',semantic_model='test-qwen')

    def test_all_six_stages_use_local_settings_and_never_send_cloud_key(self):
        calls=[]
        def respond(request):
            body=json.loads(request.content); calls.append((request,body))
            text='Turn left.' if body.get('response_format') is None else '{"valid":true}'
            return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':text}}]})
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'JEV_API_KEY':'test-jev-secret','DEEPSEEK_API_KEY':'must-not-send'},clear=True):
            api=SerialAPI(tmp,self.config); api.client.close()
            api.client=httpx.Client(transport=httpx.MockTransport(respond))
            try:
                for stage in ('dedup','deviation','inventory','recognition','choice','correction'):
                    api.ask(stage,{},[],json_output=stage!='correction')
            finally: api.close()
        self.assertEqual(len(calls),6)
        for request,body in calls:
            self.assertEqual(str(request.url),'http://127.0.0.1:12345/v1/chat/completions')
            self.assertNotIn('authorization',request.headers)
            self.assertEqual(body['model'],'test-qwen'); self.assertEqual(body['chat_template_kwargs'],{'enable_thinking':False})
            self.assertNotIn('thinking',body); self.assertNotIn('reasoning_effort',body)
        self.assertEqual(calls[-1][1]['max_tokens'],512)

    def test_local_credentials_and_transport_error_redaction(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'JEV_API_KEY':'test-jev-secret'},clear=True):
            api=SerialAPI(tmp,self.config)
            api.client.post=Mock(side_effect=RuntimeError('test-jev-secret failed'))
            try:
                with self.assertRaisesRegex(RuntimeError,r'\[REDACTED\] failed'):
                    api.ask('deviation',{},[])
            finally: api.close()

    def test_local_endpoint_rejects_remote_or_embedded_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            for endpoint in ('https://example.com/v1','http://secret@127.0.0.1/v1'):
                with self.assertRaises(ValueError): SerialAPI(tmp,dict(self.config,semantic_endpoint=endpoint))

    def test_legacy_deepseek_protocol_preserved(self):
        settings=semantic_settings({'deepseek_model':'deepseek-flash'},'deviation')
        self.assertEqual(settings['thinking'],{'type':'enabled'}); self.assertEqual(settings['max_tokens'],32768)
        self.assertEqual(settings['reasoning_effort'],'high'); self.assertNotIn('chat_template_kwargs',settings)

    def test_batch_full_chain_means_observed_recovery_not_every_task_triggered(self):
        with tempfile.TemporaryDirectory() as tmp, patch('scripts.run_serial_pipeline.assert_model'):
            out=Path(tmp); save(out/'config.json',{'episode_ids':['a','b']})
            for eid,full in [('a',True),('b',False)]:
                save(out/'episodes'/eid/'attempt_1/result.json',{'episode_id':eid,'full_chain_observed':full})
            score=out/'score.json'; save(score,{'val_unseen':{'Count':2}})
            result=validate_run(out,score,{})
            self.assertTrue(result['full_chain_observed']); self.assertEqual(result['episodes_with_full_recovery'],1)
            self.assertFalse(result['all_episodes_had_full_recovery'])


class QueueTests(unittest.TestCase):
    def test_continuation_preserves_completed_result_and_defers_interrupted_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            old=Path(tmp)/'old';new=Path(tmp)/'new'
            config={'episode_ids':['done','bad','next'],'seed':2}
            save(old/'config.json',config);save(new/'config.json',dict(config,error_handling='defer'))
            save(old/'status.json',{'phase':'failed'})
            save(old/'manifest.json',{'code_root':str(old/'code')})
            save(old/'launch.json',{'run_id':'old'})
            result=old/'episodes/done/attempt_1/result.json';save(result,{'episode_id':'done','full_chain_observed':False})
            (old/'episodes/bad/attempt_2').mkdir(parents=True)
            save(old/'live.json',{'episode_id':'bad','action_count':5})
            save(old/'runtime_failure.json',{'error':'Invalid uncertainties'})
            save(old/'code/benchmarks/vlnverse/upstream/logs/old/kujiale_result.json',{'val_unseen':{'Count':1}})
            db=old/'storage/samples/sample_data.lmdb/data.mdb';db.parent.mkdir(parents=True);db.write_bytes(b'native-progress')
            original=result.read_bytes()
            inherit_previous_run(new,old)
            self.assertEqual(result.read_bytes(),original)
            self.assertEqual((new/'episodes/done/attempt_1/result.json').read_bytes(),original)
            self.assertEqual((new/'storage/samples/sample_data.lmdb/data.mdb').read_bytes(),db.read_bytes())
            self.assertFalse((old/'episodes/bad/attempt_2/failure.json').exists())
            progress=batch_progress(new)
            self.assertEqual((progress['completed'],progress['skipped'],progress['pending']),(1,1,1))
            self.assertEqual(progress['skipped_ids'],['bad'])

    def test_explicit_busy_gpu_sharing_preserves_memory_admission(self):
        with patch('scripts.run_serial_pipeline.check_gpu',return_value={'free_mib':28000}) as check, patch('scripts.run_serial_pipeline.subprocess.check_output',return_value='100\n'):
            with self.assertRaises(RuntimeError): admit_simulator_gpu(2)
            self.assertTrue(admit_simulator_gpu(2,True)['allow_active_shared'])
            check.assert_called_with(2,12000,allow_shared=True)
            check.side_effect=RuntimeError('Insufficient free memory')
            with self.assertRaisesRegex(RuntimeError,'Insufficient'): admit_simulator_gpu(2,True)

    def test_resource_wait_respects_foreign_tasks_on_either_gpu(self):
        snap=dict(gpus={2:dict(used=5,free=48515,utilization=0),3:dict(used=38760,free=9760,utilization=0)},
                  host_available_kib=128*1024**2)
        self.assertTrue(admissible(snap,True)); self.assertFalse(admissible(snap,False))
        for gpu in (2,3):
            busy=copy.deepcopy(snap); busy['gpus'][gpu]['utilization']=99
            self.assertFalse(admissible(busy,True))
        busy=copy.deepcopy(snap); busy['gpus'][2]['used']=14753
        self.assertFalse(admissible(busy,True))
        busy=copy.deepcopy(snap); busy['gpus'][3]['free']=3055
        self.assertFalse(admissible(busy,True))
        snap['gpus'][3]['free']=14827
        self.assertTrue(admissible(snap,False))
        snap['host_available_kib']=60*1024**2
        self.assertFalse(admissible(snap,False))


class RuntimeTests(unittest.TestCase):
    def test_schema_failure_defers_task_without_sending_stop_or_scoring(self):
        with tempfile.TemporaryDirectory() as tmp:
            h=object.__new__(SerialHook); h.output=Path(tmp); h.eid='bad'
            save(h.output/'config.json',{'episode_ids':['bad','next']})
            h.folder=h.output/'episodes/bad/attempt_1'; h.folder.mkdir(parents=True)
            h.active=True; h.action_count=5; h.saved=None; h.skipping=False; h.skip_observation=None
            h.event=Mock(); h.restore_main=Mock(); h.close_decisions=Mock();h.step=Mock()
            h._before_action=Mock(side_effect=ValueError('Invalid uncertainties'))
            ob={'rgb':'fresh','finish_action':True}
            h.before_action([ob],[])
            self.assertEqual(h.step_with_terminal([]),([ob],[True]));h.step.assert_not_called()
            self.assertFalse(h.active);self.assertTrue(h.skipping)
            progress=batch_progress(h.output)
            self.assertEqual((progress['completed'],progress['skipped'],progress['pending']),(0,1,1))
            self.assertFalse((h.folder/'result.json').exists())
            self.assertEqual(json.loads((h.output/'retry_manifest.json').read_text())['episode_ids'],['bad'])
            self.assertTrue(h.consume_failed_episode(NS(data={'episode_id':'bad'})))

    def test_native_skip_resets_same_engine_and_does_not_write_metrics(self):
        root=Path(__file__).resolve().parents[1]
        tree=ast.parse(patch_evaluator((root/'benchmarks/vlnverse/upstream/vlnverse/evaluator/vln_pe_evaluator.py').read_text()))
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='VlnPeEvaluator')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='terminate_ops')
        class Status(Enum): NORMAL=0;WARM_UP=1;NOT_RESET=3;TERMINATED=2
        context=dict(np=np,runner_status_code=Status,log=Mock(),progress_log_multi_util=Mock())
        exec(compile(ast.Module(body=[method],type_ignores=[]),'native_skip_test','exec'),context)
        next_info=NS(data={'episode_id':'next'})
        e=NS(runner_status=np.array([Status.NORMAL]),_serial_hook=NS(consume_failed_episode=Mock(return_value=True)),
             _completed_this_run=0,_rss_budget=0,_need_reset=lambda ended:True,
             env=NS(reset=Mock(return_value=([],[next_info]))),data_collector=Mock(),result_logger=Mock(),
             review=None,jev_live=None,vis_output=False,now_path_key=lambda info:info.data['episode_id'])
        ended,infos=context['terminate_ops'](e,[{'finish_action':True}],[NS(data={'episode_id':'bad'})],[True])
        self.assertFalse(ended);self.assertEqual(infos,[next_info]);e.env.reset.assert_called_once_with([0])
        e.data_collector.save_eval_result.assert_not_called();e.result_logger.write_now_result_json.assert_not_called()
        self.assertEqual(e.runner_status[0],Status.WARM_UP)

    def test_deferred_tasks_stay_skipped_across_restart_and_never_count_as_scores(self):
        with tempfile.TemporaryDirectory() as tmp, patch('scripts.run_serial_pipeline.assert_model'):
            out=Path(tmp);save(out/'config.json',{'episode_ids':['done','bad','next']})
            for eid in ('done','next'):
                save(out/'episodes'/eid/'attempt_1/result.json',{'episode_id':eid,'full_chain_observed':False})
            record_episode_failure(out,'bad',out/'episodes/bad/attempt_1','schema error','deviation')
            loader=NS(resumed_path_key_list=['a','b','c'],path_key_data={
                'a':{'episode_id':'done'},'b':{'episode_id':'bad'},'c':{'episode_id':'next'}})
            with patch.dict(os.environ,{'VLN_SERIAL_OUTPUT':str(out)}):exclude_failed_tasks(loader)
            self.assertEqual(loader.resumed_path_key_list,['a','c'])
            score=out/'score.json';save(score,{'val_unseen':{'Count':2}})
            evidence=validate_run(out,score,{})
            self.assertEqual(evidence['episode_count'],2);self.assertEqual(evidence['skipped_episode_ids'],['bad'])
            self.assertFalse(evidence['all_requested_scored'])
            save(score,{'val_unseen':{'Count':3}})
            with self.assertRaisesRegex(RuntimeError,'scoring'):validate_run(out,score,{})

    def test_full_chain_requires_local_motion_and_original_resumption(self):
        start=[dict(kind='rollback'),dict(kind='correction_started')]
        handoff=dict(kind='handoff')
        original=dict(kind='action',controller='original',action={'move_by_discrete':[1]})
        local=dict(kind='action',controller='local',action={'move_by_discrete':[2]})
        self.assertFalse(has_recovery_cycle(start+[handoff,original]))
        self.assertFalse(has_recovery_cycle(start+[local,handoff]))
        self.assertTrue(has_recovery_cycle(start+[local,handoff,original]))

    def test_import_survives_upstream_scripts_package_collision(self):
        root=Path(__file__).resolve().parents[1]
        command="import sys,types; sys.path.insert(0,%r); m=types.ModuleType('scripts'); m.__path__=[]; sys.modules['scripts']=m; import core.serial_pipeline; print('ok')"%str(root)
        result=subprocess.run([sys.executable,'-B','-c',command],text=True,capture_output=True,check=True)
        self.assertIn('ok',result.stdout)

    def test_native_eval_body_is_unmodified(self):
        root=Path(__file__).resolve().parents[1]
        original=(root/'benchmarks/vlnverse/upstream/vlnverse/evaluator/vln_pe_evaluator.py').read_text()
        new=patch_evaluator(original)
        self.assertEqual(new.split('    def _serial_native_eval(self):\n')[1],original.split('    def eval(self):\n')[1])

    def test_action_stop_and_move_decoding(self):
        self.assertEqual(action_id([{'h1':{'stop':[]}}],'h1'),0)
        self.assertEqual(action_id([{'h1':{'move_by_discrete':[2]}}],'h1'),2)

    def test_local_stop_restores_memory_and_generates_original_action_before_env_step(self):
        module=ModuleType('vlnverse.evaluator.vln_pe_evaluator')
        class Status(Enum): NORMAL=1
        module.runner_status_code=Status
        h=object.__new__(SerialHook); h.active=True; h.local=True; h.local_steps=2
        h.local_instruction='Turn left.'; h.instruction='Original task.'; h.config={'local_action_budget':40}
        h.e=NS(robot_name='h1',runner_status=[Status.NORMAL]); h.frame=Mock(); h.event=Mock(); h.action_count=5; h.engine=NS(frames=[])
        h.action=Mock(side_effect=[(['local'],[{'h1':{'stop':[]}}]),(['original'],[{'h1':{'move_by_discrete':[1]}}])])
        order=[]
        def handoff(reason): order.append(reason); h.local=False
        h.handoff=handoff
        with patch.dict(sys.modules,{'vlnverse.evaluator.vln_pe_evaluator':module}):
            result,actions=h.before_action([{'rgb':'rgb','instruction':'Original task.'}],[])
        self.assertEqual(order,['local_stop']); self.assertEqual(action_id(actions,'h1'),1)
        self.assertEqual(h.action.call_args_list[0].args[0][0]['instruction'],'Turn left.')
        self.assertEqual(h.action.call_args_list[1].args[0][0]['instruction'],'Original task.')
        self.assertEqual(h.action_count,6)

    def test_takeover_waits_for_complete_action_queue(self):
        h=object.__new__(SerialHook); h.pending={'target':{'id':'S1'}}; h.policy=lambda:{'pending_count':2}
        h.api=Mock(); ob={'rgb':'rgb'}
        self.assertEqual(h.recover(ob),(ob,False)); h.api.choose.assert_not_called()

    def test_restore_checks_content_proof(self):
        h=object.__new__(SerialHook)
        with tempfile.TemporaryDirectory() as tmp:
            h.saved=dict(key='k',proof={'content_sha256':'same'},directory=Path(tmp))
            h.rpc=Mock(return_value={'content_sha256':'different'})
            with self.assertRaises(RuntimeError): h.restore_main('handoff')
            self.assertIsNotNone(h.saved)
            h.rpc.return_value={'content_sha256':'same'}; h.restore_main('handoff')
            self.assertIsNone(h.saved); self.assertTrue(json.loads((Path(tmp)/'memory_restore.json').read_text())['equal'])


if __name__=='__main__': unittest.main()
