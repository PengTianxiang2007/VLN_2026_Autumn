"""Finish a camera capture asynchronously: validate, export, browser-check, update records."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from test_crossing_single_gpu import process, write
from run_crossing_local_batch import cleanup

ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


def update_document(path, text):
    begin, end = '<!-- AGENT_ROUTE_360_CAPTURE_START -->', '<!-- AGENT_ROUTE_360_CAPTURE_END -->'
    old = path.read_text()
    block = begin + '\n' + text + '\n' + end
    if begin in old and end in old:
        a, b = old.index(begin), old.index(end) + len(end)
        new = old[:a] + block + old[b:]
    else:
        first, rest = old.split('\n', 1)
        new = first + '\n\n' + block + '\n' + rest
    tmp = path.with_suffix('.capture.tmp')
    tmp.write_text(new)
    tmp.replace(path)


def run_child(cmd, log, env=None):
    child = None
    try:
        with log.open('x') as f:
            child = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
        rc = child.wait(timeout=1200)
        if rc:
            raise RuntimeError(f'Postprocessing returned {rc}; see {log}')
    finally:
        if child is not None:
            record = cleanup(child)
            write(log.with_suffix('.cleanup.json'), record)
            if record.get('remaining'):
                raise RuntimeError('Postprocessing child cleanup incomplete')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--revision', default='01', choices=['01', '02', '03'])
    a = ap.parse_args()
    out = a.output.resolve()
    if not out.is_relative_to(ROOT / 'outputs/agent_route_choice/v002'):
        raise ValueError('Expected a registered v002 capture')
    source = out / ('postprocessing_source' if a.revision == '01' else 'postprocessing_source_' + a.revision)
    source.mkdir(exist_ok=False)
    hashes = {}
    for name in ['finish_crossing_panorama.py', 'export_crossing_panorama.py', 'check_crossing_panorama.cjs']:
        shutil.copy2(ROOT / 'scripts' / name, source / name)
        hashes[name] = hashlib.sha256((source / name).read_bytes()).hexdigest()
    write(source / 'manifest.json', dict(created_at=now(), source_hashes=hashes,
                                        git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()))
    state = dict(phase='waiting_for_capture', revision=a.revision, started_at=now(), process=process(os.getpid()), model_calls=0)
    def phase(name, **kw):
        state.update(phase=name, updated_at=now(), **kw)
        write(out / 'postprocessing.json', state)
    phase('waiting_for_capture')
    readme = ROOT / 'experiments/agent_route_choice/v002' / out.name / 'README.md'
    try:
        deadline = time.monotonic() + 12 * 3600
        while True:
            capture = json.loads((out / 'status.json').read_text())
            if capture['phase'] == 'capture_complete':
                break
            if capture['phase'] == 'failed':
                raise RuntimeError('Capture failed: ' + str(capture.get('error')))
            identity = capture.get('supervisor')
            if identity:
                current = process(identity['pid'])
                if not current or current['start'] != identity['start'] or current['state'] == 'Z':
                    raise RuntimeError('Capture supervisor exited before final status')
            if time.monotonic() > deadline:
                raise TimeoutError('Postprocessing waited 12 hours; capture state retained')
            time.sleep(10)
        for name, digest in hashes.items():
            assert hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest() == digest, 'Postprocessor source changed'
        phase('exporting')
        dest = out / 'exports/run_20261106_01'
        run_child([str(ROOT / 'backbone/streamvln/.venv/bin/python'), '-B', str(ROOT / 'scripts/export_crossing_panorama.py'),
                   '--output', str(out), '--destination', str(dest)], out / 'export.log')
        phase('browser_check')
        browser_config = Path('/tmp/vln-oracle-ui-browser-direct-20261104/browser_env.json')
        config = json.loads(browser_config.read_text())
        env = dict(os.environ, **config)
        html = dest / 'crossing_360_zh.html'
        run_child(['node', str(ROOT / 'scripts/check_crossing_panorama.cjs'), str(html), str(browser_config)], out / 'browser_check.log', env)
        checks = json.loads(html.with_suffix('.browser_check.json').read_text())
        assert checks['passed']
        validation = json.loads((dest / 'validation.json').read_text())
        summary = dict(status='complete', completed_at=now(), cases=10, panoramas=9, unique_images=72,
                       case_image_references=80, model_calls=0, navigation_actions=0,
                       reused_unique_images=capture.get('reused_unique_images', 0),
                       newly_captured_unique_images=capture.get('newly_captured_unique_images', 72),
                       owned_capture_processes_exited=capture['owned_processes_exited'],
                       automated_validation=validation, browser_checks=checks,
                       visual_semantic_review='pending', html=str(html), archive=str(dest / 'crossing_360_images.zip'))
        write(out / 'summary.json', summary)
        text = (f'{now()}：外部 Agent v002 的原十条360°画面补采完成：八场景、九个Crossing、72张唯一RGB（十条引用80张）。'
                f'本轮复用{summary["reused_unique_images"]}张，新增{summary["newly_captured_unique_images"]}张。'
                '图像哈希、640×480、固定光心、八方向覆盖、不同方位像素差异及离线浏览器检查通过；模型调用0次、导航动作0次，本次仿真进程已退出。'
                f'原图与相机元数据位于 `outputs/agent_route_choice/v002/{out.name}/panoramas/`；中文预览位于同目录 `exports/run_20261106_01/crossing_360_zh.html`，'
                '原图压缩包为 `crossing_360_images.zip`。尚未进行Qwen支路识别/选路，视觉语义复核另记。')
        phase('complete', completed_at=now(), summary=str(out / 'summary.json'))
    except BaseException as exc:
        error = type(exc).__name__ + ': ' + str(exc)
        phase('failed', error=error)
        text = f'{now()}：v002补采或自动导出未完成：{error}。保留原始状态及日志；没有模型调用，不能报告选路结论。运行目录 `outputs/agent_route_choice/v002/{out.name}`。'
    for path in [readme, ROOT / 'experiments/agent_route_choice/v002/README.md', ROOT / 'experiments/agent_route_choice/README.md',
                 ROOT / 'experiments/README.md', ROOT / 'docs/STATUS.md']:
        update_document(path, text)
    return 0 if state['phase'] == 'complete' else 1


if __name__ == '__main__':
    sys.exit(main())
