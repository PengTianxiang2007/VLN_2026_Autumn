# Codex / GPT-6 Astra 原始候选去重接口 v001

范围仅为第一轮候选去重：读取现有 JEV 原始候选，不重新采样，不接偏航判断、回退或导航动作。
参考 Spotter 的 `codex exec` → `codex exec resume <thread_id>` → 解析输出 → 外部程序执行决定。
参考源码：`outputs/references/spotter_20261123_01/Spotter/recovery_explore/judge_driver_v7.sh`，
提交 `7870559354b77e845f7bb72f6f4ea7bddf5e195c`。不沿用其 bypass 或 API fallback。

## 接口与协议

- 入口：`scripts/run_codex_node_dedup.py`；传输：`core/codex_client.py`；去重：`core/codex_node_dedup.py`。
- 默认模型 `gpt-6-astra`，推理强度 `medium`，每轮超时 600 秒。通过指定 Codex CLI 及已有 ChatGPT 登录调用，不直接请求 API。
- 每条轨迹单独创建会话；同一轨迹后续比较显式 resume 同一 thread ID。不同轨迹不共享会话，不使用 `--last`。
- 原始协议来自 `online_sampling_v001/review_snapshot_20261112/node_deduplication/v001_run02_all/`。
  原提示词完整保留，复用原 `validate`、`apply_decision`。每端五帧，偏移 -2…+2；轨迹开始前缺图明确标记。
- 比较最后一个保留的有效节点 A 与当前候选 B；超过 8 动作步直接保留，未超过才调用模型。
  `same` 删除旧 A、保留新 B；`different` / `uncertain` 保留双方。
- 本地程序解析并校验 JSON 后执行去重；模型不操作底层环境。历史保留，但本轮判断证据只限本轮 A/B 附件。
- 格式/引用校验失败记为 `format_error`，按 `uncertain` 保留双方；传输失败停止该轨迹并保留部分状态，其余独立轨迹继续，批次标为 `incomplete`，禁止伪装完成或默默切 API。
- 输出 `final_active_ids`、`effective_nodes`，保留原候选 ID；追加终止节点及后续节点重编号属于下游流程。

## 输入与使用

输入 JSON 包含 `upstream_policy: "existing_raw_sampled_nodes"`、`image_root`、`cases`。
每例包含 `case_number`、`episode_id` 和旧协议格式的 `nodes`（此字段存原始候选）。
候选含 `id/index/ready_at_frame/candidate_id/images`；图像含 `frame/label/path/image_id`（SHA256），缺图用 `missing: true`。
`image_root` 相对路径按仓库根目录解析；图像相对该根目录。
现有 dataset + JEV 数据可调用 `prepare_candidates(case, candidates)` 转换；见本次 [输入清单](run_20261123_01/input.json)。

```bash
.runtime/crossing_vllm27/bin/python scripts/run_codex_node_dedup.py \
  --input experiments/crossing_checkpoint/codex_dedup_v001/run_20261123_01/input.json \
  --output outputs/codex_tasks/checkpoint_dedup/v001/run_YYYYMMDD_NN
```

默认 binary 为 `/mnt/nas/gezuhao/PengTianxiang/codex-bin/codex`，
CODEX_HOME 为 `/mnt/nas/gezuhao/PengTianxiang/.codex`；可通过 `--codex-bin/--codex-home` 显式修改。
`--workers N` 设置轨迹并发数，默认 1。每个工作进程独立运行一条轨迹，同轨迹的比较保持顺序执行。
结果按原 case 顺序汇总；运行期间总状态记录完成数及失败轨迹，逐例状态保存在各自目录。
复用现有 Python 环境的 httpx，仅供导入冻结协议模块；不会调用该模块的 API 函数。
CLI 忽略用户 config（保留该 home 的登录态），使用只读沙箱、禁止审批交互、禁用 shell/apps/plugins/hooks 等任务不需要的能力。
不改共享配置，不启动 GPU 服务，不读取或复制登录凭据。

## 历史记录命名与恢复边界

```text
outputs/codex_tasks/checkpoint_dedup/v001/run_YYYYMMDD_NN/
  input.json, status.json, results.json
  source/                         # 实际源码/原始提示词快照、工作区 diff
  cases/C01_ep837/
    input.json, state.json, decisions.jsonl, result.json
    codex/session.json            # 仅该轨迹的 thread_id、配置、轮数
    codex/turns/turn_0001_S01_S02/
      prompt.txt, schema.json, request.json, images/
      events.jsonl, stderr.log, final.txt, response.json, decision.json
```

日期采用 UTC；NN 在同日递增，每次运行使用新目录，已存在即拒绝。
原生 Codex 历史仍保存在指定 CODEX_HOME；本目录提供逐任务可读的输入/输出、图片、哈希和会话映射。
命令及超时进程信息留档，不记录环境变量、API key 或凭据。
本版支持运行中的会话续接；中断任务保留现场，不自动重放/续跑整个批次。重试应使用新运行号。

## 验证记录

- [run_20261123_02](run_20261123_02/README.md)：用户授权 VLNVerse C01–C10 全部 89 原始候选，
  十条并行，预计 63 次比较，输入仅用五帧前视观测。
- [run_20261123_01](run_20261123_01/README.md)：已完成。RxR episode 837 前三个原始候选，
  两次 GPT-6 Astra 真实比较验证 exec + resume，同一会话、零格式错误，保留三个有效节点。
- 单元检查：`.runtime/crossing_vllm27/bin/python -m unittest tests.test_codex_node_dedup -v`。
