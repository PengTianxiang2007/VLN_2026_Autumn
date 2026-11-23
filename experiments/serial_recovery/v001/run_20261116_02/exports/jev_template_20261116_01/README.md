# 串行联调02：复用原JEV采样模板

更新时间：2026-11-16 UTC。状态：已完成并发布。

## 目的与协议

用户要求沿用之前JEV版本模板，提供完整概率波形、波形采样、俯视地图回退点显示开关和去重开关。直接复用`core/jev_sampling_lab/template.html`、`app.js`和冻结滤波/采样器；新增独立数据适配器，不重写原采样或图形交互，不覆盖旧页面。

本次是串行仿真实验的结果导出，沿用该实验已授权的服务器发布；不是恢复2026-11-12要求仅本地进行的算法迭代。无新模型调用、无新导航、无GPU进程操作。

## 数据与实现

数据来自已核验的`exports/replay_20261116_02/serial_pipeline_replay.html`及其源文件哈希。40帧、7个原始候选、6次去重后2个保留点S05/S07；显示开关只改变画面，使用本次保存的去重原答。默认沿用原模板：原始/滤波曲线打开，采样及去重关闭。N=7、D=5固定为本次实际参数。地图上方另设“显示回退点”快捷勾选，与原模板采样勾选同步，地图与波形采用同一节点列表。

入口：`scripts/export_serial_jev_template.py`；适配器：`core/serial_jev_template_adapter.js`。保留双语提示词、去重原答和7次偏航评审详情；5次初始化consistent不作为路线通过证明，实际纠错0次。

## 验证与发布

浏览器检查通过：原模板波形绘制路径在F0/F39保持完整一致；7个候选与运行日志的ID、位置帧、确认帧、类型、概率逐项匹配；地图与波形标签同步验证0→7→2→0→2→7；原始/滤波曲线可独立隐藏且不改变采样。7条建立/去重记录（含首点直接建立）、7次偏航评审中英文逐条一致，40帧图片与分数、两条进度条同步、53次请求导出、本地复核意见和移动端均通过；无JS错误、无外部请求。截图和报告见输出`browser/`。

入口代码中原模板`app.js`未经修改，模板布局和滤波/采样脚本直接内嵌复用；`build.json`记录原脚本SHA256、数据来源及本次适配器。原始模板和历史实验记录保持不变。

```bash
backbone/streamvln/.venv/bin/python -B scripts/export_serial_jev_template.py --source outputs/serial_recovery/v001/run_20261116_02/exports/replay_20261116_02/serial_pipeline_replay.html --output outputs/serial_recovery/v001/run_20261116_02/exports/jev_template_20261116_01
node scripts/check_serial_jev_template.cjs outputs/serial_recovery/v001/run_20261116_02/exports/jev_template_20261116_01/serial_jev_replay.html outputs/serial_recovery/v001/run_20261116_02/exports/jev_template_20261116_01/browser
```

网址：[http://134.175.18.101/vln/serial_jev_template_run02_web_20261116_01/serial_jev_replay.html](http://134.175.18.101/vln/serial_jev_template_run02_web_20261116_01/serial_jev_replay.html)

离线源HTML：`outputs/serial_recovery/v001/run_20261116_02/exports/jev_template_20261116_01/serial_jev_replay.html`；SHA256：`b89ce77f4661d3cffb9ae7d2c6580d25002d34f389601e86cb49a5ea4fad7f38`。在线目录：`outputs/visualization_publishing/serial_jev_template_run02_web_20261116_01/`。发布时间以`outputs/visualization_publishing/publish_20261116_072358_767100/publication.json`为准（本次核验UTC 2026-11-16T07:24:57.995238+00:00）。入口、41张图片、字体和许可证ZIP共44文件远端哈希通过，公网入口HTTP200；未另做在线浏览器检查。
