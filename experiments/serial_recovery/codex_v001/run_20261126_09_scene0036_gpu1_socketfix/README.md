# 0036 GPU1 接续：原生 TMPDIR 下的恢复 socket 修复

最终状态：21:05:06 UTC，F28 普通 STOP 的末段评审结束，STOP terminated=true；随后因终止观测不含 RGB、记录层仍强制要求而退出，正式评分未提交。本轮没有进入 recovery。该公共问题已在 [run11](../run_20261126_11_scene0036_terminal_rgbfix/README.md)修复并双路接续，旧证据保留。

2026-11-26 UTC。用户授权持续修复并跟踪到首条正式评分。run07 GPU1 在 F28 STOP 末段评审后判定偏航，已越过工具导入，但在建立恢复服务时 OSError 退出；恢复动作 0、正式评分 0。原因：原生 run_full 将 TMPDIR/TEMP/TMP 指向长 NAS 输出路径，默认 TemporaryDirectory 随之产生过长的 AF_UNIX socket 地址。旧离线控制器的 TMPDIR 为 /tmp，未暴露此问题。

修复仅将 `scripts/vlnverse_robot_bridge.py` 的 socket 私有临时目录显式指定 `dir="/tmp"`，其余动作、恢复提示词、180 步和评分不变。在实际仿真解释器、上游 scripts 包与超过 Unix socket 限长的 TMPDIR 下完成真实 socket 请求/响应验证（`tests.test_codex_bridge_native_env`，1 项通过）。未运行全量测试、未新增依赖。

GPU0 run05 保持运行，尚未导入的恢复接口读取修复版。其原源码/清单保留，新增明确源码修订存于输出及 gpu0/serial 的 `source_updates/socket_tmp_20261126/`，`before_manifest.json` 保存原版本；当前清单指向完整的新快照，不混写旧源文件。本修订防止后续原生 chunk 重启误判为未登记源码变化。

本轮仅重跑 GPU1 原 12 条未评分任务，seed 2、Codex high、180 移动步、全部原生规则和故障保护不变。run07 的 RGB、偏航会话及错误证据保留。清单、原版逐条 `baseline12.csv`、实际 Git HEAD、差异、源码/提示词与启动 PID 保存在本轮目录及同名 outputs。

```bash
.runtime/crossing_vllm27/bin/python -Bu \
  experiments/serial_recovery/codex_v001/run_20261126_09_scene0036_gpu1_socketfix/run.py
```

当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条；技术中断不计作正式失败。后续 0240 接本轮，0208 仍接 GPU0 run05。
