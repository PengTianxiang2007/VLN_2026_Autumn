# 本地 JEV 滤波与采样网页源码

从仓库根目录执行：

```bash
python scripts/export_jev_sampling_lab.py --source /path/to/wrong_choices34_fullwave_site_20261109_05.zip --destination outputs/jev_sampling_lab_run_01
```

直接打开输出目录的index.html，保留相邻JS和assets。源HTML及相邻assets也可作为输入。导出不联网、不调用模型、不发布到服务器；不会覆盖已有目录。

`template.html`仅保存结构和样式；`@@PAYLOAD_JSON@@`由本地记录填充。`app.js`默认显示原始与滤波曲线，采样版本默认不勾选。注册表`SAMPLING_VERSIONS`为后续版本入口；添加版本时同时更新模板脚本依赖和导出文件清单。

完整波形通过独立`fullCurve()`回放缓存绘制，地图路线始终完整显示。采样器仍仅消费当前进度前缀，未勾选时不运行；已勾选版本的同一候选列表绘制在地图和波形上。

接手入口：[docs/JEV_SAMPLING_HANDOFF.md](../../docs/JEV_SAMPLING_HANDOFF.md)。
