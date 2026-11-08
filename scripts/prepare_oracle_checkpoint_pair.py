"""Freeze an isolated checkpoint action pair run from the completed Oracle runtime."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    prior=ROOT/'outputs/oracle_crossing/seed2_10_multi_20261103/manifest.json'
    m=json.loads(prior.read_text());base=Path(m['oracle']['code_root']);code=out/'code'
    for name,h in m['oracle']['code_sha256'].items():
        src=base/name
        if sha(src)!=h:raise RuntimeError('Historical runtime changed: '+name)
        dest=code/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    for name in ['core/oracle_checkpoint_pair.py','core/oracle_branching.py','core/oracle_branch_policy.py','core/oracle_crossing.py','core/oracle_policy_state.py']:
        shutil.copy2(ROOT/name,code/name)
    service=code/'benchmarks/vlnverse/runner/service.py';s=service.read_text()
    before="            if self.path == '/agent/init':"
    after="""            if self.path == '/branch/checkpoint':
                from core.oracle_branch_policy import checkpoint
                result, resets, steps = checkpoint(agent, resets, steps, body)
                self.respond(result)
            elif self.path == '/agent/init':"""
    assert s.count(before)==1;s=s.replace(before,after);service.write_text(s)
    evaluator=code/'benchmarks/vlnverse/upstream/vlnverse/evaluator/vln_pe_evaluator.py';s=evaluator.read_text()
    before="    def eval(self):\n"
    after="    def eval(self):\n        if os.environ.get('VLN_BRANCH_ROOT'):\n            from core.oracle_checkpoint_pair import run\n            return run(self)\n"
    assert s.count(before)==1;s=s.replace(before,after);evaluator.write_text(s)
    for p in [service,evaluator,code/'core/oracle_branching.py',code/'core/oracle_branch_policy.py']:ast.parse(p.read_text())
    env=dict(m['oracle']['runtime_env'])
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    env.update(VLN_BRANCH_ROOT=str(out),VLN_ORACLE_MANIFEST=str(out/'manifest.json'),
               VLN_ORACLE_RECORDS=str(out/'oracle_records'),VLN_OUTPUT_ROOT=str(out/'runs'),
               VLN_SIM_CACHE_ROOT=str(out/'sim_cache'),VLN_CODE_COMMIT=head)
    files={str(p.relative_to(code)):sha(p) for p in code.rglob('*') if p.is_file()}
    manifest=dict(schema=1,protocol='actual_checkpoint_action_pair_v1',seed=2,cases=m['cases'],
                  arms=['streamvln','oracle_actions'],multi_intervention=False,
                  historical_source=str(prior),historical_source_sha256=sha(prior),git_head=head,
                  code_root=str(code),code_sha256=files,runtime_env=env,
                  episode_ids=[c['episode_id'] for c in m['cases']],
                  interpretation='Two arms from actual saved root pose. Oracle executes actions only. Canonical stance stabilization, not bitwise physics rollback. Use oracle_records/*/{streamvln,oracle_actions}/result.json.')
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    shutil.copy2(ROOT/'experiments/oracle_recovery/paired_delay10/calibration.json',out/'calibration.json')
    shutil.copy2(ROOT/'experiments/oracle_recovery/checkpoint_action10/README.md',out/'protocol.md')
    (out/'git_status.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True))
    (out/'git_diff.patch').write_bytes(subprocess.check_output(['git','diff','HEAD'],cwd=ROOT))
    (out/'source_entrypoints').mkdir()
    for name in ['prepare_oracle_checkpoint_pair.py','run_oracle_checkpoint_pair.py','run_oracle_branch_launcher.py']:
        if (ROOT/'scripts'/name).exists():shutil.copy2(ROOT/'scripts'/name,out/'source_entrypoints'/name)
    print(out)

if __name__=='__main__':main()
