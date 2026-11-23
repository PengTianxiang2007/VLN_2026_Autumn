"""Background supervisor with retained-model launch and experiment completion notes."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main(plan_path):
    plan=json.loads(plan_path.read_text());campaign=Path(plan['campaign'])
    with (campaign/'navigation_supervisor.log').open('x') as log:
        child=subprocess.Popen(plan['command'],cwd=plan['cwd'],stdout=log,stderr=subprocess.STDOUT)
        rc=child.wait()
    state=json.loads((campaign/'status.json').read_text())
    now=datetime.now(timezone.utc).isoformat()
    note=f"\n\n{now} 后台收尾：状态 `{state['phase']}`，正式评分 {state.get('completed',0)}/104；"
    validation=campaign/'capture_validation.json'
    if validation.exists():
        proof=json.loads(validation.read_text())
        note+=f"采集完整性通过：{proof['observations']}个观测、{proof['unique_multiview_images']}张多方向原图。"
    if state.get('error'):note+='异常：'+state['error']+'。'
    note+='原模型保持加载，进程与结果以输出status.json为准。\n'
    with Path(plan['registration']).open('a') as f:f.write(note)
    project=Path(plan['project_root'])
    relative=Path(plan['registration']).relative_to(project)
    for filename,target in [('docs/STATUS.md','../'+str(relative)),('experiments/README.md',str(relative.relative_to('experiments')))]:
        path=project/filename; text=path.read_text();first,rest=text.split('\n',1)
        path.write_text(first+'\n\n'+now+f'：[104条逐步多视角采集]({target})后台状态`{state["phase"]}`，正式评分{state.get("completed",0)}/104，详见记录。\n'+rest)
    return rc


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True)
    sys.exit(main(p.parse_args().plan))
