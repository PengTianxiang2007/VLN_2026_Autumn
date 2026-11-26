# C25、C09、C05 同会话纯文本偏航评审

2026-11-25 准备，VLNVerse 冻结 seed 2 轨迹。只取 C25（5 个原始候选）、C09（6 个）和 C05（10 个）。目的是观察已有前视图和 A 处进度能否支持相邻有效节点间的路线判定。上游使用 v006.1，GPT-6 Astra medium 常规档，每例一个新会话，三例并发。仅偏航轮零图片；筛选轮发送既有观测。首次偏航结束该例。历史 53 例会话已包含后续观测，故本轮按轨迹顺序重新建立会话。代理 127.0.0.1:17982，本轮用户已确认。使用远端 Codex，无本地 GPU 负载。

Git 基线 `e40d9a821ee72516261ee819284e36be7be2eff1`，实际工作区代码、差异、清单哈希和运行时参数分别随输出保存在 `source/` 和 `status.json`。冻结输入见 [input.json](input.json)。case 的节点来自上一轮 Astra 常规档 53 例清单，指令取本 episode 的原始 task.json。

从仓库根目录启动：

```bash
.runtime/crossing_vllm27/bin/python -Bu scripts/run_codex_node_dedup.py \
  --input experiments/deviation_progress/codex_memory_v001/run_20261125_01/input.json \
  --output outputs/codex_tasks/deviation_progress/codex_memory_v001/run_20261125_01 \
  --model gpt-6-astra --reasoning-effort medium --workers 3 --timeout 1800 \
  --codex-bin /mnt/nas/gezuhao/PengTianxiang/codex-bin/codex \
  --codex-home /mnt/nas/gezuhao/PengTianxiang/.codex --proxy-url http://127.0.0.1:17982
```

输出位于 `outputs/codex_tasks/deviation_progress/codex_memory_v001/run_20261125_01`。各例保存节点判定、偏航原答、传入进度、历史帧清单和回退目标。两组导航 SR、平均 SPL 均为暂无，已评分 0 条。

13:23:11 UTC 三个独立工作进程已进入各自会话初始化，主管 PID 1229260。初始化之前的针对性检查覆盖单帧初始化、替换后选择 A、区间历史帧引用以及偏航轮的零附件。

## 实际结果

[打开三例双语回放](http://134.175.18.101/vln/codex_memory_deviation_three_web_20261125_01/index.html) · [离线 ZIP](http://134.175.18.101/vln/codex_memory_deviation_three_web_20261125_01/replay.zip) · [发布记录](exports/replay_01/README.md)

13:39:03 UTC 完成 3/3，耗时 15 分 52 秒，技术失败 0 例。21 个原始候选中处理 19 个，C05 首次报警后剩余两个按协议停审。14 轮偏航评审包含 6 轮单帧初始化和 8 轮实际区间判断。逐轮请求记录确认 14 轮均复用各自轨迹的筛选会话，新增图像附件为 0。模型报警 1 例。

| 案例 | 偏航轮数 | 模型结果 | 既有离线错选归因 |
| --- | ---: | --- | --- |
| C25 | 4 | 未报警。最后一次评审 F37→F54，已接近书房门槛。 | F56–F59 漏转并直行进书房。最后有效节点早于这个区间。 |
| C09 | 2 | 未报警。F0→F5 识别出左转，能否确认选门仍有疑点。之后四个原始候选均未保留。 | F19–F23 选错厨房门。对应时段没有触发偏航评审。 |
| C05 | 8 | F26→F46 报偏航，回退目标 S07/F26；可引用帧为 26、28、44、46。模型判断已经沿走廊经过右侧客厅入口，走向凳子和柜体。 | F10–F26 漏转去客厅；错误类型相符，本轮在更晚的节点报警。 |

参考区间来自既有多视角事后归因，仅用于运行后对照。三例均为预选历史失败轨迹，不估计总体准确率。两组均无新导航评分：当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。没有实际回退或续走。

[完整请求与三例结果](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v001/run_20261125_01/results.json) · [最终状态](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v001/run_20261125_01/status.json)
