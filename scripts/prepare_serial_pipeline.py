"""Prepare and freeze a new serial-pipeline simulator run without loading models."""
import argparse
import ast
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from core.paths import isaac_root, model_python, resource_root, simulation_python
from core.serial_pipeline import PROMPTS, DEDUP, save, sha
from scripts.prepare_oracle_distance import source_files, replace_once, patch_runtime
from core.serial_batch import batch_progress, record_episode_failure, write_retry_manifest


def patch_evaluator(source, stop_after_cycle=False):
    wrapper='''    def eval(self):
        hook = None
        try:
            from core.serial_runtime import install
            hook = install(self)
            return self._serial_native_eval()
        except BaseException as error:
            if hook is not None:
                hook.failed(error)
            else:
                import json, os
                from pathlib import Path
                (Path(os.environ['VLN_SERIAL_OUTPUT'])/'runtime_failure.json').write_text(json.dumps({'error': repr(error), 'phase': 'hook_import'}))
            import traceback
            traceback.print_exc()
            raise

    def _serial_native_eval(self):
'''
    patched=replace_once(source,'    def eval(self):\n',wrapper)
    patched=replace_once(patched,'        episodes = generate_episode(self.dataloader, config)',
        '        from core.serial_batch import exclude_failed_tasks\n'
        '        exclude_failed_tasks(self.dataloader)\n'
        '        episodes = generate_episode(self.dataloader, config)')
    patched=replace_once(patched,'                obs = obs_ls[env_id]\n',
        '                if getattr(self, "_serial_hook", None) and self._serial_hook.consume_failed_episode(reset_infos[env_id]):\n'
        '                    self.runner_status[env_id] = runner_status_code.NOT_RESET\n'
        '                    self._completed_this_run += 1\n'
        '                    continue  # Technical failure: no LMDB metric or scored STOP.\n'
        '                obs = obs_ls[env_id]\n')
    if stop_after_cycle:
        boundary = '                self.result_logger.write_now_result()\n'
        patched = replace_once(patched, boundary, boundary +
            '                if self._serial_hook.stop_at_scored_cycle():\n'
            '                    return True, reset_infos\n')
    ast.parse(patched); return patched


def serial_source_files():
    files=set(source_files())
    files.update(['core/serial_pipeline.py','core/serial_runtime.py','core/serial_batch.py','core/jev_online_sampler_v001.js',
                  'scripts/jev_sampler_stdio.cjs','scripts/run_serial_pipeline.py','scripts/prepare_serial_pipeline.py',
                  'scripts/check_serial_qwen.py','scripts/serve_qwen27b_standby.py','scripts/queue_serial_qwen.py',
                  'scripts/run_deviation_progress_review.py','scripts/split_route_stage2.py','scripts/force_route_stage2.py',
                  'scripts/continue_route_stage2.py','scripts/run_agent_route_choice.py','scripts/run_crossing_remote.py',
                  'scripts/run_oracle_existing_model.py','tests/test_serial_pipeline.py',
                  'tests/fixtures/serial_deviation_single_uncertainty.json',
                  'tests/fixtures/serial_deviation_parallel_uncertainties.json',DEDUP+'/run_dedup.py',*PROMPTS.values()])
    return files


def inherit_previous_run(output, previous):
    """Copy stopped-run evidence and native progress, leaving its files untouched."""
    previous=Path(previous).resolve()
    state=json.loads((previous/'status.json').read_text())
    if state['phase']!='failed': raise ValueError('Continuation requires a stopped failed run')
    pid=state.get('simulator_pid')
    if pid and Path('/proc',str(pid)).exists(): raise RuntimeError('Previous simulator is still present')
    old=json.loads((previous/'config.json').read_text()); new=json.loads((output/'config.json').read_text())
    excluded={'response_normalization','error_handling'}
    if {k:v for k,v in old.items() if k not in excluded}!={k:v for k,v in new.items() if k not in excluded}:
        raise ValueError('Continuation changed the cohort or navigation protocol')
    shutil.copytree(previous/'episodes',output/'episodes')
    shutil.copytree(previous/'storage/samples',output/'storage/samples')
    if (previous/'failures').exists(): shutil.copytree(previous/'failures',output/'failures')
    launch=json.loads((previous/'launch.json').read_text())
    score=Path(json.loads((previous/'manifest.json').read_text())['code_root'])/'benchmarks/vlnverse/upstream/logs'/launch['run_id']/'kujiale_result.json'
    score_data=json.loads(score.read_text()) if score.exists() else {}
    save(output/'initial_score.json',score_data)
    progress=batch_progress(output)
    if score_data.get('val_unseen',{}).get('Count',0)!=progress['completed']:
        raise RuntimeError('Previous native scoring and episode results disagree')
    live=json.loads((previous/'live.json').read_text())
    eid=live['episode_id']
    if eid not in progress['completed_ids']+progress['skipped_ids']:
        attempts=sorted((output/'episodes'/eid).glob('attempt_*'))
        failure=json.loads((previous/'runtime_failure.json').read_text())
        record_episode_failure(output,eid,attempts[-1],failure['error'],'inherited_failure',
                               source_campaign=str(previous),action_count=live.get('action_count'))
    hashes={str(p.relative_to(output)):sha(p) for p in (output/'episodes').rglob('*') if p.is_file()}
    save(output/'inherited_sha256.json',hashes)
    progress=write_retry_manifest(output)
    save(output/'continuation.json',dict(source=str(previous),source_status_sha256=sha(previous/'status.json'),
         source_manifest_sha256=sha(previous/'manifest.json'),completed_result_sha256={
             str(p.relative_to(output)):sha(p) for p in (output/'episodes').glob('*/attempt_*/result.json')},
         initial_progress=progress,source_unchanged=True))


def prepare(output, episodes, jev_endpoint='https://api.site/v1/systemone', semantic_service=None, cohort=None, continue_from=None,
            protocol='legacy', stop_after_cycle=False):
    output=Path(output).resolve()
    if output.exists(): raise FileExistsError('Use a new run directory')
    cohort_data=json.loads(Path(cohort).read_text()) if cohort else None
    if cohort_data:
        if episodes: raise ValueError('Choose episodes or cohort, not both')
        episodes=[c['episode_id'] for c in cohort_data['cases']]
    if not episodes or len(set(episodes))!=len(episodes): raise ValueError('Expected unique episode IDs')
    service=json.loads(Path(semantic_service).read_text()) if semantic_service else None
    if protocol == 'v006' and (not service or service['phase'] not in ('running', 'ready')):
        raise ValueError('v006 requires a running local Qwen service')
    if protocol != 'v006' and service and (service['phase']!='ready' or not service.get('smoke_passed')):
        raise ValueError('Qwen service must pass real-image inference before preparation')
    if service:
        from scripts.run_oracle_existing_model import identity
        service['supervisor_identity']=identity(service['supervisor_pid'])
        service['server_identity']=identity(service['server_pid'])
        service['source_service_json']=str(Path(semantic_service).resolve())
    with gzip.open(resource_root()/'assets/VLNVerse/data/raw_data/final_splits/fine_val_unseen.json.gz','rt') as f:
        selected=[e for e in json.load(f)['episodes'] if e['episode_id'] in episodes]
    if set(episodes)!={e['episode_id'] for e in selected}: raise ValueError('Unknown episode')
    output.mkdir(parents=True); code=output/'code'; files=serial_source_files()
    prompts = PROMPTS
    if protocol == 'v006':
        from core.serial_v006 import BRANCH_DIR, V006_PROMPTS
        prompts = V006_PROMPTS
        files.update([*prompts.values(), BRANCH_DIR+'/output_schema.json', BRANCH_DIR+'/protocol.json',
                      'core/serial_v006.py','core/serial_v006_runtime.py','core/step_multiview.py',
                      'scripts/run_recovery_branch_review.py','scripts/run_recovery_branch_instruction.py',
                      'scripts/run_serial_v006.py','tests/test_serial_v006.py'])
    original={}
    for name in sorted(files):
        source=ROOT/name; original[name]=sha(source)
        dest=code/name; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,dest)
    evaluator=code/'benchmarks/vlnverse/upstream/vlnverse/evaluator/vln_pe_evaluator.py'
    evaluator.write_text(patch_evaluator(evaluator.read_text(), stop_after_cycle))
    if protocol == 'v006':
        server = code/'benchmarks/vlnverse/runner/service.py'
        server.write_text(patch_runtime(str(server), server.read_text()))
    config=dict(version='serial_monocular_v001',episode_ids=episodes,seed=2,
                jev_endpoint=jev_endpoint,jev_model='jev-1.14.0',
                deepseek_endpoint='https://api.deepseek.com',deepseek_model='deepseek-flash',
                local_action_budget=40,main_memory='save_before_takeover_restore_on_handoff',
                sampler='jev_online_sampler_v001',dedup='v001',deviation='v003',
                route_choice='human_v002_three_calls_monocular',correction='r2r_v007',
                physics_budget='native_25000_ticks_including_recovery_no_budget_rewind',
                trigger='semantic_deviation_only_no_reference_distance',seed_scope='native_per_episode')
    config['response_normalization']='deviation_complete_bilingual_object_or_equal_length_language_arrays_to_items; original_response_preserved'
    config['error_handling']='defer_failed_episode_continue_native_loop; separate_retry_manifest; no_automatic_rerun'
    if service:
        config.pop('deepseek_endpoint'); config.pop('deepseek_model')
        config.update(version='serial_monocular_qwen27b_v001',semantic_provider='qwen_local',
                      semantic_endpoint=service['base_url'],semantic_model=service['model'],semantic_seed=2,
                      semantic_generation='nonthinking_temperature0_max8192_correction512')
        save(output/'semantic_service.json',service)
    if protocol == 'v006':
        config.update(version='serial_recovery_v002', deviation='v006', route_choice='branch_review_v001',
                      correction='branch_instruction_v001', node_review='after_dedup_finalization',
                      terminal='review_main_stop_before_execution_rollback_on_deviation',
                      semantic_generation='qwen_seed2_nonthinking_8192_4096_512',
                      response_normalization='frozen_v006_validator',
                      takeover='interrupt_queue_and_rollback_before_route_selection',
                      main_memory='save_at_alarm_without_unexecuted_actions_restore_on_handoff',
                      missing_views='resume_original_at_restored_checkpoint',
                      navigation_model='owned_or_borrowed', simulator_retained=False)
    if stop_after_cycle:
        config['stop_after_scored_cycle'] = True
    if cohort_data:
        save(output/'cohort.json',cohort_data)
        config['cohort_scope']=dict(episodes=len(episodes),events=sum(len(c['targets']) for c in cohort_data['cases']),
                                   human_annotations_used_by_online_decisions=False)
    config['native_dataset_order']=[e['episode_id'] for e in selected]
    save(output/'config.json',config)
    dataset=output/'dataset/fine/val_unseen/val_unseen.json.gz'; dataset.parent.mkdir(parents=True)
    with gzip.open(dataset,'wt') as f: json.dump(dict(episodes=selected),f)
    if continue_from: inherit_previous_run(output,continue_from)
    runtime=dict(STREAMVLN_VENV=str(model_python('streamvln').parent.parent),VLNVERSE_VENV=str(simulation_python().parent.parent),
                 PENG_ISAAC_ROOT=str(isaac_root()),VLN_RESOURCE_ROOT=str(resource_root()),
                 VLN_OUTPUT_ROOT=str(output/'runs'))
    manifest=dict(created_at=time.time(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  code_root=str(code),original_sha256=original,code_sha256={n:sha(code/n) for n in sorted(files)},
                  config_sha256=sha(output/'config.json'),dataset_sha256=sha(dataset),runtime_env=runtime,
                  episode_ids=episodes,prompt_sha256={k:sha(code/v) for k,v in prompts.items()},
                  inherited_model_code='Existing retained service remains immutable; save/reset/restore RPC reused.')
    if protocol == 'v006':
        manifest['model_service_source'] = 'frozen service.py with project save/reset/restore RPC'
        del manifest['inherited_model_code']
    manifest['additional_sha256']={name:sha(output/name) for name in (
        'cohort.json','semantic_service.json','continuation.json','inherited_sha256.json','initial_score.json',
        'storage/samples/sample_data.lmdb/data.mdb') if (output/name).exists()}
    save(output/'manifest.json',manifest)
    (output/'workspace_status.txt').write_bytes(subprocess.check_output(['git','status','--short'],cwd=ROOT))
    (output/'workspace.patch').write_bytes(subprocess.check_output(['git','diff','HEAD'],cwd=ROOT))
    save(output/'status.json',dict(phase='prepared',simulation_started=False,episodes=episodes))
    print(json.dumps(dict(output=str(output),episodes=episodes,source_files=len(files))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',type=Path,required=True)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--episodes',nargs='+'); group.add_argument('--cohort',type=Path)
    p.add_argument('--jev-endpoint',default='https://api.site/v1/systemone')
    p.add_argument('--semantic-service',type=Path)
    p.add_argument('--protocol', choices=('legacy','v006'), default='legacy')
    p.add_argument('--stop-after-cycle', action='store_true', help='Stop at the first formally scored physical recovery cycle')
    p.add_argument('--continue-from',type=Path,help='Copy completed evidence and defer the interrupted episode; source stays immutable')
    a=p.parse_args()
    if a.stop_after_cycle and a.protocol != 'v006':
        p.error('--stop-after-cycle requires --protocol v006')
    prepare(a.output,a.episodes,a.jev_endpoint,a.semantic_service,a.cohort,a.continue_from,a.protocol,a.stop_after_cycle)
