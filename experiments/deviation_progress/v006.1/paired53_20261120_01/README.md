# GPU 3 Qwen，v6 与 v6.1 双版本 53 条后台评审

2026-11-21 00:56 UTC，[后台接续](resume_20261121_01/README.md)已启动，PID 619682。v6 从 C50／S03 恢复，复用已完成的 49 条及 C50 前两轮，随后补 C51–C53，再自动运行 v6.1 剩余 51 条。模型已接收请求并正常生成。

2026-11-21 核对时主管 384770 已退出。2026-11-20 20:38:14 UTC，v006 的 C50／S03 在请求发出 300 秒后发生 ReadTimeout，异常终止整个顺序批次。v006 已完成 C01–C49，共 49/53 条（含复用的 C35、C38）。这些完整案例共 239 轮，188 次 consistent、43 次 deviated、8 次格式错误。C50 另保存前两轮 consistent，S03 超时原始记录仍在。v006.1 全量阶段尚未启动，仍只有此前的 C35、C38 两条。GPU 3 模型进程仍在，本次健康接口返回成功。上述计数来自保存的结果和日志。[失败状态](../../../../outputs/deviation_progress/v006_pair_route53_20261120_01/v006/status.json) · [C50 超时记录](../../../../outputs/deviation_progress/v006_pair_route53_20261120_01/v006/run/cases/C50/S03.response.json)

2026-11-20 17:12:00 UTC，已按用户指令在 GPU 3 上启动独立后台进程，PID 384770。先补 v006 的 51 条，再由同一进程自动补 v006.1 的 51 条。两版分别复用各自已完成的 C35、C38。17:12:40 UTC，v006 的 C01／S01 已返回 `consistent` 并通过校验，随后按用户要求结束人工跟踪。[启动清单](../../../../outputs/deviation_progress/v006_pair_route53_20261120_01/plan.json) · [后台日志](../../../../outputs/deviation_progress/v006_pair_route53_20261120_01.log) · [首轮原答](../../../../outputs/deviation_progress/v006_pair_route53_20261120_01/v006/run/cases/C01/S01.response.json)

| 版本 | 复用 | 待评审 | 合计 |
| --- | ---: | ---: | ---: |
| v006 | 2（C35、C38） | 51 | 53 |
| v006.1 | 2（C35、C38） | 51 | 53 |

两个版本共用冻结的 Route53 轨迹、指令、去重后节点、原生前视 RGB、单帧初始化、判定时间和首次有效报警停止协议。从每条轨迹的首节点独立建立本版本的进度。复用 GPU 3 上的 Qwen3.8-27B-FP8（`route53-qwen27b`），轨迹与请求 seed 2，temperature 0，top_p 1，max_tokens 8192，关闭 thinking。各版本复用记录分别指回各自的原始请求和回答。[v006 两例](../../v006/run_20261120_01_qwen_gpu3_c35_c38/README.md) · [v6.1 两例](../run_20261120_01_qwen_gpu3_c35_c38/README.md)

准备时的 Git 基线为 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`。两个实际中文 Prompt 的 SHA256 分别为 `d3fb3fe87b61fa1ff51ba45480721f4d5e20eed2b1c8f1fff0e259f99bbae3ea` 和 `4cc56cc8087ef413c0790cbb7d82efcd9522cae33620f82c0413b480a0394def`。已在 CPU 上读取两种语言的 v6.1 Prompt，用历史 `consistent` 和 `deviated` 回答校验接口，并确认第三个判定会被拒绝。清单核对结果为两组各覆盖 53 个不同案例。正式运行时，原入口将实际源码、Git 提交和模型参数保存至各版本的 `manifest.json`。

在仓库根目录打印清单。

```bash
PYTHONPATH=.:scripts .runtime/crossing_vllm27/bin/python -B experiments/deviation_progress/v006.1/paired53_20261120_01/run_pair.py
```

实际进程使用独立会话启动，标准输入接到 `/dev/null`，标准输出和错误追加到同一日志。下列命令可复现相同的后台评审；重新运行时应指定新的运行目录和日志。运行目录已保存启动时的入口源码。[入口快照](../../../../outputs/deviation_progress/v006_pair_route53_20261120_01/run_pair.py)

```bash
nohup env PYTHONPATH=.:scripts .runtime/crossing_vllm27/bin/python -Bu \
  experiments/deviation_progress/v006.1/paired53_20261120_01/run_pair.py \
  --run-dir outputs/deviation_progress/v006_pair_route53_20261120_01 \
  >> outputs/deviation_progress/v006_pair_route53_20261120_01.log 2>&1 < /dev/null &
```

运行目录中的 `plan.json` 保存案例清单与哈希，各版本的 `status.json` 记录进度。每完成一个版本，根目录会生成该版本的 `*_all53.json`，按案例编号列出每轮判定与实际来源目录。原始请求、模型原答、帧号和累计进度位于相应来源的 `run/cases/`。
# 2026-11-21 完成状态

两版均已完成全 53 条。v6：253 轮、47 条轨迹报警、9 轮格式错误。v6.1：236 轮、45 条轨迹报警、2 轮格式错误，于 2026-11-21 04:00 UTC 完成。以上报警数量不是准确率。完整汇总、来源及接续记录见 [resume_20261121_01/README.md](resume_20261121_01/README.md)。

