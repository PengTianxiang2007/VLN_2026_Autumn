# DeepSeek 驱动 H1 实际回退 · 首批三例

2026-11-23 01:28 UTC 完成 3/3。三例均由 DeepSeek 主动判断已到并退出，1/3（33.33%）满足距 A ≤0.35 米的判据，平均退出水平误差 2.267 米。没有技术跳过或物理终止。共 3 次去程总结、19 次回程决策。Isaac 正常退出，本次进程已释放 GPU 1。[逐例原始结果](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_03_deepseek3/summary.json)

| 案例 | 掉头后的动作数 | 回程决策次数 | 退出距 A | 退出朝向差 | 回程动作边界上最近距 A | 达标 |
|---|---:|---:|---:|---:|---:|---|
| C03 | 32 | 9 | 0.318 米 | 5.76° | 0.318 米，第 32 步 | 是 |
| C05 | 16 | 5 | 4.541 米 | 149.72° | 4.520 米，第 14 步 | 否 |
| C07 | 16 | 5 | 1.940 米 | 156.19° | 1.925 米，第 13 步 | 否 |

每例另有 12 次初始左转。C05、C07 在记录的回程动作边界中均未进入位置阈值。C05 的去程描述还写到了在 B 发出 STOP，该例冻结的去程动作中末步为前进，没有 STOP；此次按原协议将模型生成的描述传给回程模型。仅凭本批无法确定这处描述错误对退出判断的影响。

2026-11-23 UTC。按[七帧样本集](../run_20261123_02/README.md)的原始顺序取 C03、C05、C07，seed 2。使用官方 DeepSeek 的 `deepseek-flash`、temperature 0、关闭 thinking，沿用[此前成功的多图调用](../../../agent_recovery/branch_review_v001/run_20261121_03_deepseek2/README.md)。API 凭据从运行时输入。

每例按[去程提示词](outbound_en.txt)和七张图及全部区间动作生成一次描述。在历史 B 位姿和关节状态上重建 H1，根速度置零，先执行 12 个原生左转。随后按[回程提示词](return_en.txt)输入描述、A 前视/中点前视/B 前视/A 反向实拍，以及 R0、前三轮约定的动态回程帧和全部已执行动作。每次只判当前位置是否已到，或顺序提交四个合法动作。触发原生物理终止即结束。0.35 米为退出位置达标线，单列朝向误差；模型的输入不含坐标或阈值判定。整条导航当前版和同批原版均为“暂无，已评分 0 条”。

构建与实验基线为 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`；准备时冻结实际脚本、提示词与数据来源。原始输入索引、模型响应和动作轨迹见[运行目录](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_03_deepseek3/)。从仓库根目录运行：

```bash
.runtime/crossing_vllm27/bin/python -Bu scripts/run_vlm_rollback.py start
```

三例去程请求均已收到 DeepSeek 回答。C07 的原答附有 `"type":"json_object"`，首次严格校验在 GPU 启动前中止。接续时仅移除此包装字段，逐字保留原描述，复用三份原答。实际修订源码与先前状态保存在输出 `source/resume_*/`，本次接续命令为 `.runtime/crossing_vllm27/bin/python -Bu scripts/run_vlm_rollback.py resume`。GPU 1 在剩余 43,475 MiB、利用率 0% 时通过共享准入。[实时状态](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_03_deepseek3/status.json)
