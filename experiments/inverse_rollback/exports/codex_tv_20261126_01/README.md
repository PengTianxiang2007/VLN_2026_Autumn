# 从 F38 到电视前的动作与观测回放

2026-11-26。离线导出 [Codex 电视前导航](../../codex_tools_v001/run_20261126_03_tv/README.md) 的全部 28 次机器人工具调用。场景任务为 `kujiale_0036_0_0`，seed 2。使用已有场景的可通行栅格、调用后的机身位姿与原生前视 PNG。动作回图与主动观察分别标注，模型响应编号和图像转交标记取自本轮已对齐的日志。Git 基线 `d551421e95c72a1dd2305e31f308016c7d188e67`，模板沿用 H1 实走回放的地图、RGB 及双进度条布局和 roundtrip 样式。

从项目根目录生成独立 HTML。

```bash
backbone/streamvln/.venv/bin/python -B scripts/export_codex_tv_replay.py outputs/inverse_rollback/exports/codex_tv_20261126_01
```

## 导出与发布

2026-11-26 12:29 UTC 已发布。[在线回放](http://134.175.18.101/vln/codex_tv_f38_h1_20261126_01/index.html) · [离线单文件](../../../../outputs/inverse_rollback/exports/codex_tv_20261126_01/index.html) · [在线版拆分清单](../../../../outputs/visualization_publishing/codex_tv_f38_h1_20261126_01/online_manifest.json) · [发布回执](../../../../outputs/visualization_publishing/publish_20261126_122910_961018/publication.json)

底图采用 kujiale_0036 的 356×379 可通行栅格，分辨率 0.035 米，使用历史回放的世界 XY 投影。电视、电视柜取本轮仿真场景物体边界。全部 28 张原生 PNG 按回执 SHA256 核对。浏览器检查了逐调用同步、主动观察与自动回图标记、22 张进入模型上下文的图、双语切换保留当前帧、图层、播放和模型响应跳转。[导出来源与哈希](../../../../outputs/inverse_rollback/exports/codex_tv_20261126_01/export.json) · [本地交互检查](../../../../outputs/inverse_rollback/exports/codex_tv_20261126_01/browser-check.json)

离线 HTML SHA256 为 `97a5ba67f6f95a5c68588911f1963613827aa9b0343286c793cc00914d95348d`。在线入口 SHA256 为 `e1dc804ae1f587eb425f5d7eceb05c5ca4a35eacbf8ebe9eaf23505bbd51312c`。远端入口与 30 个静态资源均通过 SHA256 核对，公网入口 HEAD 返回 HTTP 200。
