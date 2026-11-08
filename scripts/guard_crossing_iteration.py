"""Deterministic limits and final validation scheduling; never invents method changes."""
import argparse
from datetime import datetime,timezone
import json
import hashlib
import os
from pathlib import Path
import signal
import time


def read(p):return json.loads(p.read_text())


def write(p,v):
    q=p.with_suffix(p.suffix+'.tmp');q.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');q.replace(p)


def now():return datetime.now(timezone.utc).isoformat()


def process_identity(pid):
    p=Path('/proc')/str(pid)
    try:
        fields=(p/'stat').read_text().rsplit(')',1)[1].split()
        return dict(pid=pid,start=fields[19],ppid=int(fields[1]),pgrp=int(fields[2]),session=int(fields[3]),
                    cwd=os.readlink(p/'cwd'),
                    argv=[s.decode() for s in (p/'cmdline').read_bytes().split(b'\0') if s])
    except (OSError,ValueError):
        return None


def same_identity(current,expected):
    return current is not None and all(current[k]==expected[k] for k in
                                      ['pid','start','pgrp','session','cwd','argv'])


def argument_path(process,flag):
    path=Path(process['argv'][process['argv'].index(flag)+1])
    return (path if path.is_absolute() else Path(process['cwd'])/path).resolve()


def register_supervisor_identity(root,service,state):
    current=process_identity(state['supervisor_pid']);repo=Path(__file__).resolve().parents[1]
    if current is None or Path(current['cwd'])!=repo:
        raise ValueError('Supervisor does not belong to this repository')
    scripts=[a for a in current['argv'] if Path(a).name=='test_crossing_single_gpu.py']
    if len(scripts)!=1 or (repo/scripts[0]).resolve()!=repo/'scripts/test_crossing_single_gpu.py':
        raise ValueError('Unexpected campaign supervisor command')
    if argument_path(current,'--output')!=service or argument_path(current,'--campaign')!=root:
        raise ValueError('Supervisor output/campaign scope differs')
    write(root/'supervisor_identity.json',current)


def stop_failed_replay(root,state):
    # Stop the verified private replay group. Its supervisor then performs normal error cleanup.
    expected=read(root/'supervisor_identity.json')
    if expected['pid']!=state['supervisor_pid']:
        raise ValueError('Supervisor PID differs from registered owner')
    current=process_identity(expected['pid'])
    if current is None:return 'already_exited'
    if not same_identity(current,expected):
        raise ValueError('Supervisor identity changed; refusing to signal descendants')
    candidates=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        child=process_identity(int(path.name))
        if child is None or child['ppid']!=expected['pid'] or child['cwd']!=expected['cwd']:continue
        argv=child['argv']
        scripts=[a for a in argv if Path(a).name=='replay_crossing_checkpoint.py']
        if len(scripts)!=1 or not (Path(child['cwd'])/scripts[0]).resolve().is_relative_to(root):continue
        if '--tag' not in argv or argv[argv.index('--tag')+1]!=state['tag']:continue
        if argument_path(child,'--output')!=root:continue
        if child['pgrp']!=child['pid'] or child['session']!=child['pid']:
            raise ValueError('Replay does not have its own private process group')
        candidates.append(child)
    if not candidates:return 'replay_already_exited; supervisor_will_reap_it'
    if len(candidates)!=1:raise ValueError('Ambiguous replay ownership')
    child=candidates[0]
    if not same_identity(process_identity(child['pid']),child):
        raise ValueError('Replay identity changed before signal')
    os.killpg(child['pid'],signal.SIGTERM)
    return dict(action='sent_SIGTERM_to_verified_replay_group',identity=child)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--campaign',type=Path,required=True);args=ap.parse_args()
    root=args.campaign.resolve();protocol=read(root/'protocol.json');queue=root/'queue'
    while True:
        if (root/'session_complete.json').exists():return
        if not (root/'session.json').exists():time.sleep(5);continue
        session=read(root/'session.json');service=Path(session['service']);state=read(service/'status.json')
        if state['phase']=='failed':
            write(root/'guard_status.json',dict(phase='blocked_runtime_error',reason=state.get('error'),updated_at=now()));return
        if not (root/'supervisor_identity.json').exists():
            register_supervisor_identity(root,service,state)
        case_states=[read(p) for p in (root/'runs'/state.get('tag','')/'cases').glob('*/status.json')]
        failed=[s for s in case_states if s['phase']=='failed']
        run_status=root/'runs'/state.get('tag','')/'status.json'
        reported=read(run_status).get('failures',{}) if run_status.exists() else {}
        if not failed and reported:failed=[dict(episode_id=k,error=v,phase='failed') for k,v in reported.items()]
        if failed:
            evidence=dict(tag=state.get('tag'),failed_cases=failed,detected_at=now())
            write(root/'case_failure_abort.json',evidence)
            try:
                evidence['action']=stop_failed_replay(root,state)
                phase='aborting_failed_replay'
            except (OSError,ValueError,KeyError) as error:
                evidence['action']='refused_unverified_signal';evidence['error']=str(error)
                phase='blocked_unverified_supervisor'
            write(root/'case_failure_abort.json',evidence)
            write(root/'guard_status.json',dict(phase=phase,reason=evidence,updated_at=now()));return
        jobs=[(p,read(p)) for p in sorted(queue.glob('*.json'))]
        dev=[]
        for p,j in jobs:
            score=root/'runs'/j['tag']/'scores.json'
            if j['split']=='development' and p.with_suffix('.done').exists() and score.exists():
                summary=read(score)['summary']
                if summary['complete']:dev.append((j,summary['metrics']['1.0']))
        if not dev:time.sleep(5);continue
        if not (root/'selection_decision.json').exists():
            best=max(dev,key=lambda jm:((jm[1]['f1'] or 0),(jm[1]['precision'] or 0),(jm[1]['recall'] or 0)))
            significant=dev[0][1]['f1'] or 0;plateau=0
            for _,m in dev[1:]:
                if (m['f1'] or 0)>=significant+.02:significant=m['f1'];plateau=0
                else:plateau+=1
            timings=[];rates={}
            for j,_ in dev:
                version_timings=[]
                for p in (root/'runs'/j['tag']/'cases').glob('*/predictions.jsonl'):
                    version_timings += [json.loads(line)['elapsed_seconds'] for line in p.read_text().splitlines()]
                timings += version_timings
                if version_timings:rates[j['tag']]=sum(version_timings)/len(version_timings)
            # A slower selected method must not inherit an optimistic average from faster versions.
            seconds=max(sum(timings)/len(timings) if timings else 20,
                        rates.get(best[0]['tag'],20))
            # User requested one final run of the selected version on fifteen held-out cases.
            observations=read(root/'registration.json')['validation_observations']
            reserve=observations*seconds*1.3+600
            reason=None;m=best[1]
            if (m['precision'] or 0)>=.85 and (m['recall'] or 0)>=.80:reason='development_target_reached'
            elif len(dev)-1>=6:reason='maximum_six_modifications'
            elif plateau>=3:reason='three_round_plateau'
            elif time.time()+reserve>=session['deadline_epoch']:reason='reserve_time_for_validation'
            explicit=root/'finish_development.json'
            if explicit.exists():reason=read(explicit)['reason']
            write(root/'guard_status.json',dict(phase='development',completed_versions=len(dev),best=best[0]['tag'],
                  metrics=m,plateau=plateau,seconds_per_observation=seconds,version_seconds_per_observation=rates,
                  reserved_validation_seconds=reserve,
                  stop_reason=reason,updated_at=now()))
            active=[j for p,j in jobs if not p.with_suffix('.done').exists()]
            if reason and not active:
                review=root/'reviews'/(best[0]['tag']+'.json')
                score_path=root/'runs'/best[0]['tag']/'scores.json'
                if (not review.exists() or read(review).get('scores_sha256')!=hashlib.sha256(score_path.read_bytes()).hexdigest()):
                    write(root/'guard_status.json',dict(phase='awaiting_result_review',best=best[0]['tag'],
                          stop_reason=reason,updated_at=now()))
                    time.sleep(5);continue
                decision=dict(selected_tag=best[0]['tag'],source=best[0]['source'],metrics=m,reason=reason,
                              completed_development=[j['tag'] for j,_ in dev],created_at=now(),validation_sealed_until=now())
                write(root/'selection_decision.json',decision)
                write(queue/'900_selected_validation.json',dict(tag='selected_validation',split='validation',source=best[0]['source']))
        else:
            progress=read(root/'guard_status.json') if (root/'guard_status.json').exists() else {}
            progress.update(phase='validation',best=read(root/'selection_decision.json')['selected_tag'],
                            completed_cases=sum(s['phase']=='complete' for s in case_states),
                            expected_cases=len(protocol['validation']),updated_at=now())
            write(root/'guard_status.json',progress)
            validation=[(p,j) for p,j in jobs if j['split']=='validation']
            if validation and all(p.with_suffix('.done').exists() for p,j in validation):
                if any(read(p.with_suffix('.done'))['returncode'] for p,j in validation):
                    write(root/'guard_status.json',dict(phase='validation_failed',updated_at=now()));return
                summaries={j['tag']:read(root/'runs'/j['tag']/'scores.json')['summary'] for p,j in validation}
                if all(s['complete'] for s in summaries.values()):
                    write(root/'session_complete.json',dict(phase='complete',selection=read(root/'selection_decision.json'),
                          validation=summaries,finished_at=now()))
                    write(root/'guard_status.json',dict(phase='complete',updated_at=now()));return
        time.sleep(5)


if __name__=='__main__':main()
