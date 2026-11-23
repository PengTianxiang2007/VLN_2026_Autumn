# v006 全部回退点的两组同模型 Recovery

在 47 个相同的有效回退点比较两个阶段都采用 Qwen27B 或两个阶段都采用 DeepSeek Flash 的局部指令。两组共享冻结的 v006 报警、进度和三张节点观测，分别读取各自 v1 第一次调用的原答。支路编号只在对应模型的对应案例内有效。

第二次调用沿用 v001 中文 Prompt，temperature=0、top_p=1、max_tokens=512，关闭思考。Qwen 复用 GPU3 服务，seed=2、top_k=-1、单请求顺序执行 47 例。DeepSeek 沿用官方端点，不指定推理 seed；复用已核对一致的十例，37 例并行。保留有效的双 null 回答。历史导航 seed=2。本次进行离线指令生成。

```bash
.runtime/crossing_vllm27/bin/python -Bu scripts/run_recovery_branch_instruction.py --all --model qwen --output outputs/agent_recovery/branch_instruction_v001/run_20261121_02_paired47/qwen
.runtime/crossing_vllm27/bin/python -Bu scripts/run_recovery_branch_instruction.py --all --model deepseek --reuse outputs/agent_recovery/branch_instruction_v001/run_20261121_01 --output outputs/agent_recovery/branch_instruction_v001/run_20261121_02_paired47/deepseek
```

各组 manifest 记录 Git HEAD、实用源码及哈希、首次调用响应哈希和复用来源。逐例保留请求、响应和输入清单。

## 完成结果

| 两阶段用模 | 本次新增 | 复用 | 有效回答 | 输出指令 | 返回空指令的案例 |
|---|---:|---:|---:|---:|---|
| Qwen27B → Qwen27B | 47 | 0 | 47 | 43 | C11、C28、C33、C50 |
| DeepSeek Flash → DeepSeek Flash | 37 | 10 | 47 | 45 | C11、C28 |

两组全部非空选择都来自各自清单，均排除了各自上次已走的 ID。Qwen 的四个空回答在其第一阶段均只有一条已走支路。DeepSeek 的 C28 也是单支路；C11 在有三条支路时返回双 null，原答未给出原因。指令生成数量不用于衡量选路正确率，未运行导航。

运行时 Git HEAD 为 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`，工作区含未提交改动。DeepSeek 于 12:20:00 UTC 完成，Qwen 于 12:21:15 UTC 完成；保留原先待用的 GPU3 服务。[逐例摘要](summary.json)

## 双语对照回放

[在线查看](http://134.175.18.101/vln/recovery_instruction_v001_paired47_web_20261121_01/index.html) · [下载离线包](http://134.175.18.101/vln/recovery_instruction_v001_paired47_web_20261121_01/recovery_instruction_v001_qwen_deepseek_47_offline.zip)（73,246,522 字节）。勾选 Qwen27B 或 DeepSeek Flash 时，同时切换该模型两阶段原答。共享观察区沿用 RGB 下方的俯视地图及回退按钮。

本地入口 `outputs/visualization_publishing/recovery_instruction_v001_paired47_web_20261121_01/index.html`，SHA256 `14bb0c7693c5418dff7a92a6ae4d99e7f3b74b688049276c4073779eac97059d`。于 2026-11-21T12:29:34.204516+00:00 发布，4,586 个文件的远端哈希校验通过，入口公网 HEAD HTTP 200。发布记录为 `outputs/visualization_publishing/publish_20261121_122837_092782/publication.json`。[定向浏览器检查](check_playback.cjs)覆盖 C50 和 C07、两模型独立勾选、两阶段结果同步、双语及回退帧定位。
