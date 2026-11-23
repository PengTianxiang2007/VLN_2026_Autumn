# v1.1 两例 Qwen 试跑

v006 的 C50（S04/F15）及 C07（S03/F41），依次在现有 GPU3 Qwen3.8-27B-FP8 上各调用一次。seed=2、temperature=0、max_tokens=4096。节点三视图与 +2/+5/+8/+10 原生前视沿用原数据。

命令：

```bash
.runtime/crossing_vllm27/bin/python -Bu scripts/run_recovery_branch_review.py --version v001.1 --cases C50 C07 --output outputs/agent_recovery/branch_review_v001.1/run_20261121_01 --execute
```

2026-11-21T10:50:08.436944+00:00 完成，两例格式和候选分组引用均有效。C50 将 R1 和 F2 合为 B3（正前），保留三条。C07 的 R1 描述混淆了右图开口与前图左侧开口，再与 F1 合为 B1，只保留一条。两例均未把右侧开口列为独立支路。完整原答在输出目录的 cases/。原 v006 队列此前已完成 47/47，试跑前后均为同一 GPU3 服务 PID 994127，运行及等待请求均为 0。

[Qwen / DeepSeek 全量对照网站](http://134.175.18.101/vln/recovery_branch_models_v006_47_web_20261121_02/index.html) · [离线包](http://134.175.18.101/vln/recovery_branch_models_v006_47_web_20261121_02/recovery_qwen_deepseek_v006_47_offline.zip)。
