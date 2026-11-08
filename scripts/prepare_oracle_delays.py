"""Prepare four authorized delay arms; this script never starts GPU work."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'outputs/oracle_crossing/seed2_10_multi_20261103'


def main():
    original=json.loads((BASE/'manifest.json').read_text())
    source_hash=hashlib.sha256((BASE/'manifest.json').read_bytes()).hexdigest()
    runtime=None
    prepared=[]
    for distance in (3,5,8,12):
        out=BASE.parent/f'seed2_10_delay{distance}m_20261103'
        if (out/'manifest.json').exists():raise RuntimeError('Preserve already frozen delay arm: '+str(out))
        out.mkdir(parents=True,exist_ok=True)
        m=copy.deepcopy(original);m.pop('oracle',None)
        m.update(created_at=time.time(),deviation_threshold_m=distance,
                 oracle_run_id=f'peng_fine_oracle10_delay{distance}m_20261103',
                 early_intervention_campaign=str(BASE),early_manifest_sha256=source_hash,
                 requires_complete_campaign=str(BASE),
                 delay_protocol='Shortest horizontal distance to full reference polyline. Review at the next native empty action queue after threshold. Assistant must confirm wrong route and explicitly choose the relevant frozen crossing target. Never teleport from distance alone.')
        m['protocol'].update(deviation_threshold_m=distance,confirmation='live assistant at eligible boundary',
                             terminal_rule='Preserve native STOP, fall, stuck and physics budget; retain episodes ending before intervention.')
        for name in ['visualization_control','runs_control']:(out/name).symlink_to((BASE/name).resolve(),target_is_directory=True)
        for name in ['model_fingerprints.json','status_control.json','environment_check.json']:shutil.copy2(BASE/name,out/name)
        path=out/'manifest.json';path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
        if runtime is None:
            subprocess.run([sys.executable,'-B',str(ROOT/'scripts/prepare_oracle_runtime.py'),'--campaign',str(out)],check=True)
            runtime=json.loads(path.read_text())['oracle']
        else:
            conf=copy.deepcopy(runtime);conf['run_id']=m['oracle_run_id']
            conf['runtime_env'].update(VLN_OUTPUT_ROOT=str(out/'runs_oracle'),VLN_SIM_CACHE_ROOT=str(out/'sim_cache_oracle'),
                                      VLN_ORACLE_MANIFEST=str(path),VLN_ORACLE_RECORDS=str(out/'oracle_records'))
            (out/'runs_oracle').mkdir(exist_ok=True)
            (out/'runs_oracle/visualization.json').write_text(json.dumps(dict(schema=1,seeds=[2],output_dir=str(out/'visualization_oracle'))))
            m['oracle']=conf;m['shared_frozen_runtime']=runtime['code_root']
            path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
        prepared.append(dict(threshold_m=distance,campaign=str(out),status='prepared_not_started'))
    (BASE.parent/'delay_experiments_20261103.json').write_text(json.dumps(dict(user_thresholds_m=[3,5,8,12],same_ten_tasks=True,start_after=str(BASE),arms=prepared),indent=2)+'\n')
    print(json.dumps(prepared,indent=2))


if __name__=='__main__':main()
