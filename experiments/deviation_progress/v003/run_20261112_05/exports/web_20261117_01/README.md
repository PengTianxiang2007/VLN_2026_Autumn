# v003 / 34 案例网页发布 20261117_01

状态：已完成发布。

用户于 2026-11-17 明确要求将此前仅本地展示的网页发布到指定服务器；本次授权仅针对该历史结果可视化。复用 2026-11-12 run05 冻结网页与原资源包，保留 34 案例、33 轨迹、9 场景、199 节点及全部原始判断。没有新模型请求或导航，seed 沿用历史未指定记录。

- 当前导出 Git HEAD：`7ce5f9fee30686bae304425bc84c36b3fbedc39c`；不作为历史模型运行版本。
- 导出工作区差异及源文件哈希：`outputs/deviation_progress/v003/run_20261112_05/exports/web_20261117_01/preparation.json`、`tracked_before.patch`、`git_status_before.txt`。
- 本地完整网页：`outputs/deviation_progress/v003/run_20261112_05/exports/web_20261117_01/offline/index.html`。
- 在线目录：`outputs/visualization_publishing/jev_deviation_progress_v003_34cases_web_20261117_01/`。
- 发布名：`jev_deviation_progress_v003_34cases_web_20261117_01`。

恢复命令：

```bash
python3 -B scripts/export_deviation_progress_snapshot.py --source outputs/visualization_publishing/wrong_choices34_fullwave_download_20261109_01/wrong_choices34_fullwave_site_20261109_05.zip --destination outputs/deviation_progress/v003/run_20261112_05/exports/web_20261117_01/offline
```

在线版采用现有 prepare_online_visualization.py 和 publish_visualization.py，显式包含页面需要的 JS/CSS、图片字体以及原始请求/响应 JSON；发布前检查两种语言、地图红线、节点回退信息、RGB 与双进度条。完成后补充网址、SHA256 和实际验证范围。红线是模型的区间偏航判定，不是逐帧真值；本轮未执行真实回退。

## 本地验证与显示修复

- `browser_final/validation.json`：34 案例、199 节点、114 次历史请求，106 份有效回答的中文/英文全文均与原数据一致；切换语言不改变案例或帧。逐案检查首末 RGB、偏航证据图、回退目标、红线开关及双进度条，移动端无横向溢出，页面无脚本错误或意外请求失败。
- 初次截图发现旧字体子集缺少本版新增的 278 个汉字。复用仓库配置的文泉驿字体重新生成子集，覆盖全部 782 个所需汉字，并使提示词 pre 块使用该字体。字体来源、许可与哈希见输出 `font_fix.json`；本地初次截图及修复后截图均保留。
- 仅修复导出页面字体与浏览器标题；冻结 snapshot 不变。`source_integrity.json` 验证 237 个发布用原始脚本/结果文件及 HTML payload 与冻结快照完全一致。
- 在线入口约 1.44 MB，图片已外置按需加载；显式清单含 3287 个依赖，含字体许可和原始请求/响应链接。仅发布清单内文件，不上传运行脚本、日志、环境或凭据。

发布命令（已有在线目录；首次运行，不覆盖远端版本）：

```python
import json, sys
from pathlib import Path
folder = Path('outputs/visualization_publishing/jev_deviation_progress_v003_34cases_web_20261117_01')
manifest = json.loads((folder / 'online_manifest.json').read_text())
sys.path.insert(0, str(Path('scripts').resolve()))
import publish_visualization
sys.argv = ['publish_visualization', '--html', str(folder / manifest['html']), '--name', manifest['release']]
for asset in manifest['assets']:
    sys.argv.extend(['--asset', asset])
publish_visualization.main()
```

## 已发布

- 网址：http://134.175.18.101/vln/jev_deviation_progress_v003_34cases_web_20261117_01/index.html
- 发布时间（UTC）：`2026-11-17T04:09:26.734534+00:00`。
- 本地源：`outputs/deviation_progress/v003/run_20261112_05/exports/web_20261117_01/offline/index.html`。
- 在线 HTML SHA256：`94317e5ddb6da414ad958c95d1015b3d9c3d8547c95155f6c837738132992446`。
- 发布记录：`outputs/visualization_publishing/publish_20261117_040903_605545/publication.json`。
- 3288 个文件全部通过远端 SHA256 校验；公网入口 HEAD 返回 HTTP 200，类型 `text/html`，大小 1443737 字节。采用默认快速验证，未执行全量公网下载或公网浏览器检查。
- 本地浏览器验证通过；全部原判断与数据保持不变，修复了字体缺字。没有新模型或导航任务。
