# Codex 候选去重接口：真实两轮连通验证

状态：完成；2026-11-23 21:27 UTC。

## 目的与版本

验证已登录 Codex CLI 调用 GPT-6 Astra、同轨迹显式续接、图像附件、JSON 校验和外部去重动作。
仅验证第一层接口，不推断检测准确率或导航收益。
实际 Git 提交 `e40d9a821ee72516261ee819284e36be7be2eff1` 加本次未提交接口代码；
未提交差异及源文件 SHA256 写入输出 `status.json`；实际执行源码保存在 `source/`。

## 输入与协议

复用 `outputs/deviation_progress/rxr30_v006/run_20261123_01` 的现成 JEV 候选与 dataset，
只取 C01 / episode 837 的 S01、S02、S03（动作步 0、5、10），不重跑采样。
轨迹来源 seed 2；Codex CLI 未提供可固定的采样 seed，不宣称模型调用确定性。
模型 `gpt-6-astra`，reasoning `medium`，超时 600 秒；两次比较后结束。
对照为冻结的原始去重规则；不额外调用其他模型，无导航对照实验。

## 启动命令

```bash
.runtime/crossing_vllm27/bin/python scripts/run_codex_node_dedup.py \
  --input experiments/crossing_checkpoint/codex_dedup_v001/run_20261123_01/input.json \
  --output outputs/codex_tasks/checkpoint_dedup/v001/run_20261123_01
```

使用用户指定 `/mnt/nas/gezuhao/PengTianxiang/codex-bin/codex` 与
`CODEX_HOME=/mnt/nas/gezuhao/PengTianxiang/.codex`，版本 0.164.0，已确认 ChatGPT 登录。
不使用 GPU，不改共享服务或环境。每次子调用在自身进程组内退出清理。

## 结果与产物

7 项局部单元检查全部通过，覆盖 exec/resume 与跨任务隔离、删旧留新、超过 8 步跳过、
无效 JSON/缺失证据保留双方、传输失败不提交候选、图片映射及自身子进程清理。

真实运行 21:25:33–21:27:22 UTC，约 109 秒。两轮 CLI 返回码均为 0，均有 `turn.completed`，
JSON 与冻结协议校验通过，0 格式错误。S01→S02、S02→S03 均判为 `different`，
3 个原始候选保留为 3 个有效节点，删除 0 个；不追加终止节点。
本次真实输入没有触发 `same`，删旧留新分支由局部单元检查验证。

会话 ID：`01a20a4d-0a58-7570-b5d2-f5e38a22613b`。
首轮 exec，第二轮显式 resume 该 ID；各附 8/10 张原始图片。
原生会话的两条 `turn_context` 均确认 `gpt-6-astra / medium`；无工具动作事件。
CLI 因主动禁用 code-mode host 输出能力不可用提示；该提示未导致 turn 失败，两个正式回答均正常完成。
完整提示保留于原始事件及[轻量验证摘要](summary.json)，不将其计为模型格式错误。

输出：`outputs/codex_tasks/checkpoint_dedup/v001/run_20261123_01/`。
`verification.json` 保存逐轮模型标识、续接 ID、附件数、耗时和原始 usage；不对 usage 做跨轮求和。
每轮 `prompt.txt`、图片、`request.json`、`events.jsonl`、`final.txt`、`response.json` 和去重决定均已保存。
当前版本 SR/平均 SPL：暂无，已评分 0 条；配对原版 SR/平均 SPL：暂无，已评分 0 条。
本次为接口连通测试，不启动完整轨迹批次、不生成 HTML。

## 下一步

接口及历史记录已交付；更大候选集运行按后续用户要求开展。本次验证任务已正常退出。
