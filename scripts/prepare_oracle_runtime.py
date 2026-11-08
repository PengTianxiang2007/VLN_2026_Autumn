"""Create the intervention arm from the exact control snapshot, with explicit patches."""
import ast
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/oracle_crossing/seed2_10_multi_20261103'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    global OUT
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--campaign',type=Path,default=OUT)
    args=ap.parse_args();OUT=args.campaign.resolve()
    path=OUT/'manifest.json';m=json.loads(path.read_text())
    if 'oracle' in m:raise RuntimeError('Oracle runtime already frozen')
    control=Path(m['control']['code_root']);code=OUT/'code_oracle'
    for name,h in m['control']['code_sha256'].items():
        assert sha(control/name)==h
        dest=code/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(control/name,dest)
    for name in ['core/oracle_crossing.py','core/oracle_policy_state.py']:
        shutil.copy2(ROOT/name,code/name)
    service=code/'benchmarks/vlnverse/runner/service.py';s=service.read_text()
    before="    def do_GET(self):\n        self.respond({'ready': True, 'method': args.method, 'model_calls': agent.calls})"
    after="""    def do_GET(self):
        if self.path.startswith('/oracle/state'):
            from core.oracle_policy_state import audit
            self.respond(audit(agent, resets, deep='deep=1' in self.path))
            return
        self.respond({'ready': True, 'method': args.method, 'model_calls': agent.calls})"""
    assert s.count(before)==1;s=s.replace(before,after);service.write_text(s)
    evaluator=code/'benchmarks/vlnverse/upstream/vlnverse/evaluator/vln_pe_evaluator.py';s=evaluator.read_text()
    edits=[
      ('        self.data_collector = DataCollector(self.dataloader.lmdb_path)\n',
       '        self.data_collector = DataCollector(self.dataloader.lmdb_path)\n'
       '        from core.oracle_crossing import OracleCrossing\n'
       '        self.oracle = OracleCrossing.from_environment(self)\n'),
      ('                self.data_collector.save_eval_result(\n',
       '                if self.oracle:\n'
       '                    self.oracle.finish(reset_info.data["episode_id"], obs, obs["metrics"][list(obs["metrics"])[0]][0])\n'
       '                self.data_collector.save_eval_result(\n'),
      ('        while self.env.is_running():\n            review_observations = obs if self.review else None\n',
       '        while self.env.is_running():\n'
       '            if self.oracle and self.runner_status[0] == runner_status_code.NORMAL:\n'
       '                obs, injected_terminated = self.oracle.before(self, obs, reset_info)\n'
       '                if injected_terminated:\n'
       '                    if self.review:\n'
       '                        self.review.observe(self.now_path_key(reset_info[0]), obs[0], {}, terminal=True)\n'
       '                    env_term, reset_info = self.terminate_ops(obs, reset_info, injected_terminated)\n'
       '                    if env_term: break\n'
       '                    continue\n'
       '            review_observations = obs if self.review else None\n'),
      ('            obs, action = self.get_action(obs, action)\n',
       '            obs, action = self.get_action(obs, action)\n'
       '            if self.oracle and self.runner_status[0] == runner_status_code.NORMAL:\n'
       '                self.oracle.action(action[0][self.robot_name])\n')]
    for a,b in edits:
        assert s.count(a)==1,a
        s=s.replace(a,b)
    evaluator.write_text(s)
    runner=code/'benchmarks/vlnverse/runner/run_full.py';s=runner.read_text()
    # An API error must not silently retry an interrupted trial.
    a='            if completed<=start_count:\n                failures+=1\n'
    b='            if rc != 0:\n                raise RuntimeError("Oracle evaluator failed; inspect evidence before explicit retry")\n'+a
    assert s.count(a)==1;s=s.replace(a,b);runner.write_text(s)
    a='                if time.time()-newest>900:\n'
    b='                pending_file=Path(os.environ["VLN_ORACLE_RECORDS"])/"pending.json"\n'\
      '                oracle_waiting=pending_file.exists() and json.loads(pending_file.read_text()).get("status")=="waiting"\n'\
      '                if time.time()-newest>900 and not oracle_waiting:\n'
    assert s.count(a)==1;s=s.replace(a,b);runner.write_text(s)
    changed=['core/oracle_crossing.py','core/oracle_policy_state.py',str(service.relative_to(code)),str(evaluator.relative_to(code)),str(runner.relative_to(code))]
    for name in changed:ast.parse((code/name).read_text())
    hashes={name:sha(code/name) for name in [*m['control']['code_sha256'],'core/oracle_crossing.py','core/oracle_policy_state.py']}
    env=dict(m['control']['runtime_env'],VLN_OUTPUT_ROOT=str(OUT/'runs_oracle'),
             VLN_SIM_CACHE_ROOT=str(OUT/'sim_cache_oracle'),VLN_ORACLE_MANIFEST=str(path),VLN_ORACLE_RECORDS=str(OUT/'oracle_records'))
    (OUT/'runs_oracle').mkdir(exist_ok=True)
    (OUT/'runs_oracle/visualization.json').write_text(json.dumps(dict(schema=1,seeds=[2],output_dir=str(OUT/'visualization_oracle'))))
    m['oracle']=dict(code_root=str(code),code_sha256=hashes,runtime_env=env,changed_files=changed,
                     episode_ids=m['control']['episode_ids'],run_id=m.get('oracle_run_id') or ('peng_fine_oracle10_multi_20261103' if m.get('multi_intervention') else 'peng_fine_oracle10_intervention_20261103'))
    path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    print('Oracle runtime frozen:',code)


if __name__=='__main__':main()
