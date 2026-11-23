# 原成功JEV脚本再次复测02

状态：完成，仍HTTP400。用户要求“现在再试一次”；配置、样本和方法沿用[复测01](../jev_original_retest_20261116_01/README.md)。原调用脚本不修改，`api.site/v1/systemone`、`jev-1.14.0`，相同F35/F36/F37及本轮原渠道密钥。密钥无回显输入，不落盘。

命令：
```bash
env -u JEV_API_KEY benchmarks/vlnverse/.venv/bin/python -u -B scripts/probe_anyaigc_jev_systemone.py --endpoint https://api.site/v1/systemone --model jev-1.14.0 --tag probe_api_site_prev_retest_20261116_02
```

新产物：`outputs/crossing_checkpoint/jev_noul_v004/wrong_choices34_anyaigc_20261109_01/probe_api_site_prev_retest_20261116_02/`。manifest记录实际UTC时间、Git基线与执行源码哈希，source目录保存执行快照。

本次脚本退出码1，仍为`JEV HTTP 400: TypeSafe rejected the request`；完整请求和图像审计与历史成功版本逐字节相同。错误终端输出与新旧对照保存为terminal_output.txt/comparison.json。没有取得有效概率，没有启动仿真，原模型保持保留。后续需渠道恢复后重试，不能声称问题已解决。
