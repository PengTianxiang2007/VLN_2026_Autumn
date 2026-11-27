# 0036 GPU1 接续：恢复接口包名冲突修复

最终状态：20:48:45 UTC 在 F28 STOP 末段判定偏航后，恢复服务建立 socket 时因继承的 NAS TMPDIR 路径过长而 OSError 退出；恢复动作 0、正式评分 0。导入修复已生效。后续 [run09 socket 修复](../run_20261126_09_scene0036_gpu1_socketfix/README.md)仅重启 GPU1，本轮证据保留。

2026-11-26 UTC。用户授权持续修复并跟踪到首条正式评分。run05 GPU1 在 `kujiale_0036_32_4` F28 判定偏航、选择 S01/F0 后，导入 recovery 工具失败；本轮仍未正式评分。根因为上游已有普通包 `scripts`，遮住本仓库同名命名空间包，产生 `ModuleNotFoundError: scripts.vlnverse_robot_bridge`。不是 JEV/Codex 请求失败，也未执行恢复动作。

新增 `benchmarks/vlnverse/upstream/scripts/vlnverse_robot_bridge.py` 兼容入口，按明确路径导入现有桥接实现，动作和评分逻辑不变。已用实际仿真解释器及上游优先 PYTHONPATH 复现故障并验证修复。GPU0 保持运行，其延迟导入也可读取此入口；在 run05 输出保存补充源码及时间/哈希，不覆盖原快照。

只重启 GPU1 原 12 条尚未评分任务，seed 2、Codex high、180 移动步和全部保护协议不变。旧轨迹、RGB、偏航会话及失败记录保留，不冒充完整导航结果。运行清单与 `baseline12.csv` 保存同 seed 原版成绩。源码、差异、Git HEAD、兼容入口快照和进程身份保存于同名 outputs 目录。旧保留仿真不动。

```bash
.runtime/crossing_vllm27/bin/python -Bu \
  experiments/serial_recovery/codex_v001/run_20261126_07_scene0036_gpu1_bridgefix/run.py
```

当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。后续 0240 改接本轮正常完成，GPU0 后续 0208 仍接 run05 正常完成；分别保留独立输出。
